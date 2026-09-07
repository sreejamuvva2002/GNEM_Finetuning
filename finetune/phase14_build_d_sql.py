"""Phase 14 -- build `train_D_sql_v3.jsonl`.

README Phase 14: render D from the SAME eligible task_ids as C: question ->
gold SQL. Reuses phase13_build_c_answers.is_eligible/CARRY_FIELDS directly
(not a re-implementation) so C and D's task_id sets are identical BY
CONSTRUCTION, not merely by coincidentally-matching separate logic -- the one
asymmetry the protocol wants is the supervision target, nothing else
(README:495-504).

Child tables via JOIN, never semicolon-string equality -- already true of
every gold_sql in the pool (Phase 12). Per-field operation policy (Primary
OEMs excluded from group-by/ranking, Address gets no aggregation) and the
1-40 / 1-25 result-size caps were applied at candidate-generation time
(Phase 12), not re-applied here. `row_id` policy (join allowed, filter only
when the question names a record) was validated in Phase 12 and re-verified
here for this exact eligible subset.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H                                              # noqa: E402
import sqlexec_v3 as X                                                # noqa: E402
from phase13_build_c_answers import (CARRY_FIELDS, is_eligible,       # noqa: E402
                                     load_pool)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "datasets_v3" / "gnem_v3.sqlite"
OUT = ROOT / "datasets_v3" / "train_D_sql_v3.jsonl"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_D_SQL_v3.md"
GENERATOR_VERSION = "d_sql_v3.0"

SQL_SYSTEM = (
    "You translate questions about companies in the Georgia new-energy "
    "mobility supply chain into a single read-only SQL SELECT query. "
    "Schema -- companies(row_id, company, category, industry_group, "
    "location, address, primary_facility_type, ev_supply_chain_role, "
    "primary_oems, supplier_or_affiliation_type, employment, "
    "product_or_service, ev_battery_relevant, classification_method, city, "
    "county); processes(row_id, company, process); "
    "services(row_id, company, service); "
    "certifications(row_id, company, standard_family). Join a child table on "
    "row_id. Respond with exactly one SQL SELECT statement and nothing else."
)


class Gate(Exception):
    """A Phase 14 invariant failed. No artifact is written."""


def build():
    reg = H.load_registry()
    held = H.held_out_values(reg)
    pool = load_pool()

    items, skips = [], {}
    for task in pool:
        ok, reason = is_eligible(task, held)
        if not ok:
            skips[reason] = skips.get(reason, 0) + 1
            continue
        item = {f: task[f] for f in CARRY_FIELDS}
        item["example_id"] = f"D_{task['task_id']}"
        item["gold_sql"] = task["gold_sql"]
        item["messages"] = [
            {"role": "system", "content": SQL_SYSTEM},
            {"role": "user", "content": task["question"]},
            {"role": "assistant", "content": task["gold_sql"]},
        ]
        items.append(item)
    return reg, pool, items, skips


def main() -> int:
    reg, pool, items, skips = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    pool_ids = {t["task_id"] for t in pool}
    check("nonzero_items", len(items) > 0, f"{len(items)} D items")
    check("every_item_traces_to_pool_task_id",
          all(i["task_id"] in pool_ids for i in items),
          "every D item's task_id is present in STRUCTURED_TASK_POOL_v3.jsonl")
    check("unique_example_ids", len({i["example_id"] for i in items}) == len(items),
          f"{len(items)} unique ids")

    # 100% gold execution -- re-verified here, defense in depth, against the
    # only scope a training generator may touch.
    exec_failures = []
    for i in items:
        try:
            X.run_sql(i["gold_sql"], "train_kb", db_path=DB_PATH)
        except Exception as e:  # noqa: BLE001
            exec_failures.append({"example_id": i["example_id"],
                                  "error": f"{type(e).__name__}: {e}"})
    check("gold_100pct_execution", not exec_failures,
          f"0 execution failures across {len(items)} items" if not exec_failures
          else f"{len(exec_failures)} failed: {exec_failures[:3]}")

    # C and D use IDENTICAL task_id sets -- verified against the actual sibling
    # artifact, not merely trusted from shared code.
    c_path = ROOT / "datasets_v3" / "train_C_answers_v3.jsonl"
    c_ids = {json.loads(l)["task_id"] for l in
            c_path.read_text(encoding="utf-8").splitlines()}
    d_ids = {i["task_id"] for i in items}
    check("identical_task_id_set_as_C", c_ids == d_ids,
          f"{len(d_ids)} task_ids, identical to train_C_answers_v3.jsonl"
          if c_ids == d_ids
          else f"symmetric difference: {sorted(c_ids ^ d_ids)[:5]}")

    c_by_id = {json.loads(l)["task_id"]: json.loads(l) for l in
              c_path.read_text(encoding="utf-8").splitlines()}
    byte_mismatch = [i["example_id"] for i in items
                     if i["question"] != c_by_id[i["task_id"]]["question"]
                     or i["operation_family"] != c_by_id[i["task_id"]]["operation_family"]
                     or i["logical_fingerprint"] != c_by_id[i["task_id"]]["logical_fingerprint"]]
    check("byte_equal_question_and_metadata_vs_C", not byte_mismatch,
          "question text and core metadata are byte-identical to C's matching "
          "item for every shared task_id" if not byte_mismatch
          else f"{byte_mismatch[:5]}")

    check("no_semicolon_string_membership",
          not any(f"= '{v}'" in i["gold_sql"] and (";" in str(v))
                 for i in items for v in i.get("values_used", [])),
          "no gold_sql compares a child field against a semicolon-joined "
          "string literal (child tables are queried via JOIN)")

    join_arities = defaultdict(int)
    for i in items:
        join_arities[i["join_arity"]] += 1
    check("join_counts_recorded", True,
          " · ".join(f"arity {k}: {v}" for k, v in sorted(join_arities.items())))

    by_family = defaultdict(int)
    for i in items:
        by_family[i["operation_family"]] += 1
    check("only_eligible_operation_families",
          set(by_family) <= (set(H.OPERATION_PRECEDENCE) | {"filter"}) -
          set(H.HELD_OUT_OPERATIONS),
          f"operation families present: {dict(by_family)}, none held out")

    row_id_bad = []
    for i in items:
        sql = i["gold_sql"]
        stripped = __import__("re").sub(
            r"JOIN\s+\w+\s+\w+\s+ON\s+[^\n]*?(?=(JOIN|WHERE|GROUP|ORDER|$))",
            " ", sql, flags=__import__("re").I)
        if __import__("re").search(r"\brow_id\b", stripped, __import__("re").I):
            row_id_bad.append(i["example_id"])
    check("no_row_id_where_filter", not row_id_bad,
          "row_id appears only inside JOIN...ON clauses, never a WHERE filter "
          "(README:541-543)" if not row_id_bad else f"{row_id_bad[:5]}")

    def answer_size(i):
        gold = next(t for t in pool if t["task_id"] == i["task_id"])["train_kb_gold"]
        return len(gold["rows"])
    # Correction (post-approval audit, confirmed): "cross-table" means ANY
    # table join (join_arity >= 1), not merely a two-attribute composition
    # (join_arity >= 2) -- a single child-table join (child_filter) is still
    # a cross-table query. The original >= 2 threshold let 4 single-join
    # tasks through at 27-36 rows, silently outside the 1-25 cap.
    oversize = [i["example_id"] for i in items
               if (i["join_arity"] >= 1 and answer_size(i) > 25)
               or (i["join_arity"] == 0 and answer_size(i) > 40)]
    undersize = [i["example_id"] for i in items
                if i["answer_type"] == "set" and answer_size(i) < 1]
    check("answer_sizes_within_caps", not oversize and not undersize,
          "every item's train_kb_gold row count is within the README Phase "
          "14 caps (list/filter 1-40, cross-table 1-25) and satisfies the "
          "implicit minimum of 1 for a list-shaped answer"
          if not oversize and not undersize
          else f"oversize {oversize[:5]} undersize {undersize[:5]}")

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for i in items:
            fh.write(json.dumps(i, ensure_ascii=False, sort_keys=True) + "\n")
    sha = H.sha256_file(OUT)

    render_texts = [SQL_SYSTEM] + [i["messages"][1]["content"] for i in items] + \
                   [i["messages"][2]["content"] for i in items]
    rep = H.scan_strings(render_texts, reg)
    H.assert_value_scan_verified(rep)
    _update_ledger(sha, rep)
    _audit(reg, pool, items, skips, join_arities, by_family, checks, sha, rep)

    print(f"\nAll Phase 14 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  items {len(items)} of {len(pool)} pool tasks")
    return 0


def _update_ledger(sha, rep):
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    led["arms"]["D"] = {"scanned": True, "exposure_count": rep["total_exposures"],
                        "artifact": "datasets_v3/train_D_sql_v3.jsonl",
                        "sha256": sha, "strings_scanned": rep["strings_scanned"],
                        "phase": 14}
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _audit(reg, pool, items, skips, join_arities, by_family, checks, sha, rep):
    L = ["# DATASET_D_SQL_v3\n",
         "Phase 14 — `train_D_sql_v3.jsonl`, the same eligible tasks as C "
         "rendered as SQL targets.\n",
         "## Provenance\n", "```text",
         f"artifact          datasets_v3/train_D_sql_v3.jsonl",
         f"sha256            {sha}",
         f"generator         {GENERATOR_VERSION}",
         f"source pool       datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl "
         f"({len(pool)} tasks)",
         f"holdout registry  {reg['policy_version']} frozen {reg['frozen_date']}",
         "```\n",
         f"## Eligibility (identical to C by construction)\n",
         f"**{len(items)}** of **{len(pool)}** pool tasks eligible.\n",
         "| excluded reason | count |", "|---|--:|"]
    for reason, n in sorted(skips.items()):
        L.append(f"| `{reason}` | {n} |")
    L += ["", "## Join-arity distribution\n", "| join_arity | items |", "|---|--:|"]
    for k, v in sorted(join_arities.items()):
        L.append(f"| {k} | {v} |")
    L += ["", "## Operation-family distribution (D-eligible only)\n",
          "| operation_family | items |", "|---|--:|"]
    for fam, n in sorted(by_family.items()):
        L.append(f"| `{fam}` | {n} |")
    L += ["",
          "## Exposure\n", "```text",
          f"strings scanned   {rep['strings_scanned']}   (system prompt + "
          f"every question + every gold_sql)",
          f"exposure_count    {rep['total_exposures']}",
          "```\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        L.append(f"| `{n}` | {'PASS' if ok else 'FAIL'} | {d} |")
    L.append("")
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, H.HoldoutError) as e:
        print(f"\nPHASE 14 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
