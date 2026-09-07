"""Phase 13 -- build `train_C_answers_v3.jsonl`.

README Phase 13: render C from the ELIGIBLE subset of
`STRUCTURED_TASK_POOL_v3.jsonl` task_ids: question -> `train_kb_gold`. Never
`full_kb_gold` (README Phase 12's two-gold split exists precisely so a
model-facing training target never embeds a count/answer computed from
held-out or dev-side rows).

ELIGIBILITY (computed here, not baked into the pool -- README:495 and the
registry's own "eligibility for C/D training is a separate Phase 13/14
computation" note in Phase 12's audit doc):
  - `operation_family` must not be one of the three held-out families
    (argmax_topk, group_by, limit_only) -- README Phase 22 requires these at
    zero occurrences in training gold.
  - `values_used` must contain no held-out value literal (omit the item,
    never truncate the truth -- the same policy as every other arm).
  - the composition holdout pair never reaches the pool at all (Phase 12), so
    no separate composition check is needed here.

C carries NO SQL text. Because of that, `operation_family`/`fields_used`/
`values_used`/`logical_components`/`logical_fingerprint`/`join_arity`/
`required_constructs`/`answer_type`/`target_columns` are the ONLY way to
later detect operation leakage in this file -- so every field is carried
through from the pool task, never dropped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H                                  # noqa: E402
import leak_audit_v3 as LA                               # noqa: E402
from phase11_build_b_facts import CLOSED_BOOK_SYSTEM      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POOL = ROOT / "datasets_v3" / "STRUCTURED_TASK_POOL_v3.jsonl"
OUT = ROOT / "datasets_v3" / "train_C_answers_v3.jsonl"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_C_ANSWERS_v3.md"
GENERATOR_VERSION = "c_answers_v3.0"

# C's task metadata fields, carried through verbatim -- everything the pool
# carries EXCEPT gold_sql (README: "C contains no SQL text") and the two
# never-a-training-target golds.
CARRY_FIELDS = ("task_id", "question", "operation_family", "fields_used",
                "values_used", "logical_components", "logical_fingerprint",
                "join_arity", "required_constructs", "answer_type",
                "target_columns", "entity_dependent", "split")


class Gate(Exception):
    """A Phase 13 invariant failed. No artifact is written."""


def load_pool() -> list[dict]:
    return [json.loads(l) for l in POOL.read_text(encoding="utf-8").splitlines()]


def is_eligible(task: dict, held: dict) -> tuple[bool, str | None]:
    if task["operation_family"] in H.HELD_OUT_OPERATIONS:
        return False, f"held_out_operation:{task['operation_family']}"
    for field, vals in held.items():
        touched = set(str(v) for v in task["values_used"])
        if touched & set(vals):
            return False, f"held_out_value:{field}"
    return True, None


def render_answer(task: dict) -> str:
    """A fixed, deterministic prose rendering of train_kb_gold. Eligible tasks
    are all operation_family='filter' (argmax_topk/group_by are held out), so
    only 'set' (company list) and 'scalar' (count) answer_type ever reach
    here -- asserted, not merely assumed, in main()."""
    gold = task["train_kb_gold"]
    rows = gold["rows"]
    if task["answer_type"] == "scalar":
        n = rows[0][0] if rows else 0
        return f"The answer is {n}."
    if task["answer_type"] == "set":
        companies = sorted({r[0] for r in rows})
        if not companies:
            return "No companies match."
        return "The companies are: " + "; ".join(companies) + "."
    raise Gate(f"render_answer: unexpected eligible answer_type "
              f"{task['answer_type']!r} for {task['task_id']} -- eligibility "
              f"should have excluded every non-filter family")


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
        question = task["question"]
        answer = render_answer(task)
        item = {f: task[f] for f in CARRY_FIELDS}
        item["example_id"] = f"C_{task['task_id']}"
        item["gold_value"] = task["train_kb_gold"]
        item["messages"] = [
            {"role": "system", "content": CLOSED_BOOK_SYSTEM},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        items.append(item)
    return reg, pool, items, skips


def main() -> int:
    reg, pool, items, skips = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    pool_ids = {t["task_id"] for t in pool}
    check("nonzero_items", len(items) > 0, f"{len(items)} C items")
    check("every_item_traces_to_pool_task_id",
          all(i["task_id"] in pool_ids for i in items),
          "every C item's task_id is present in STRUCTURED_TASK_POOL_v3.jsonl")
    check("unique_example_ids", len({i["example_id"] for i in items}) == len(items),
          f"{len(items)} unique ids")

    pool_by_id = {t["task_id"]: t for t in pool}
    target_mismatch = [i["example_id"] for i in items
                       if i["gold_value"] != pool_by_id[i["task_id"]]["train_kb_gold"]]
    check("every_target_equals_train_kb_gold", not target_mismatch,
          "every item's gold_value is byte-identical to its pool task's "
          "train_kb_gold" if not target_mismatch else f"{target_mismatch[:5]}")

    full_kb_leak = [i["example_id"] for i in items
                   if i["gold_value"] == pool_by_id[i["task_id"]]["full_kb_gold"]
                   and pool_by_id[i["task_id"]]["entity_dependent"]]
    check("zero_entity_dependent_items_carrying_full_kb_answer", not full_kb_leak,
          "no entity_dependent item's target coincides with full_kb_gold "
          "(train_kb_gold and full_kb_gold differ by definition for these, "
          "so equality here would itself indicate a wiring bug)"
          if not full_kb_leak else f"{full_kb_leak[:5]}")

    held_op_present = [i["example_id"] for i in items
                       if i["operation_family"] in H.HELD_OUT_OPERATIONS]
    check("no_held_out_operation_family_eligible", not held_op_present,
          "no eligible item carries a held-out operation_family "
          "(argmax_topk/group_by/limit_only)" if not held_op_present
          else f"{held_op_present[:5]}")

    held = H.held_out_values(reg)
    held_val_present = [i["example_id"] for i in items
                        if any(set(str(v) for v in i["values_used"]) & set(vals)
                              for vals in held.values())]
    check("no_held_out_value_eligible", not held_val_present,
          "no eligible item's values_used intersects a held-out value"
          if not held_val_present else f"{held_val_present[:5]}")

    bad_answer_type = [i["example_id"] for i in items
                       if i["answer_type"] not in ("set", "scalar")]
    check("only_set_or_scalar_answer_types", not bad_answer_type,
          "every eligible item is answer_type set or scalar (the only types "
          "reachable once argmax_topk/group_by are excluded)"
          if not bad_answer_type else f"{bad_answer_type[:5]}")

    check("no_sql_text_in_items", not any("gold_sql" in i for i in items),
          "no C item carries a gold_sql field")
    check("no_dev_or_test_gold_fields_present",
          not any("full_kb_gold" in i or "train_dev_kb_gold" in i for i in items),
          "no C item carries full_kb_gold or train_dev_kb_gold (README:508)")

    render_texts = [CLOSED_BOOK_SYSTEM] + [i["question"] for i in items] + \
                   [i["messages"][2]["content"] for i in items]
    leaked = LA.companies_leaked_in(render_texts)
    check("zero_heldout_or_dev_companies_present", not leaked,
          f"0 of {len(LA.non_train_companies())} dev/test companies appear in "
          f"rendered C text (train_kb_gold structurally cannot name one)"
          if not leaked else f"LEAKED: {leaked[:5]}")

    rep = H.scan_strings(render_texts, reg)
    H.assert_value_scan_verified(rep)
    check("exposure_count_zero", rep["total_exposures"] == 0,
          f"0 held-out literals across {rep['strings_scanned']} rendered strings")

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

    _update_ledger(sha, rep)
    _audit(reg, pool, items, skips, checks, sha, rep)

    print(f"\nAll Phase 13 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  items {len(items)} of {len(pool)} pool tasks "
         f"({len(pool) - len(items)} ineligible)")
    return 0


def _update_ledger(sha, rep):
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    led["arms"]["C"] = {"scanned": True, "exposure_count": rep["total_exposures"],
                        "artifact": "datasets_v3/train_C_answers_v3.jsonl",
                        "sha256": sha, "strings_scanned": rep["strings_scanned"],
                        "phase": 13}
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _audit(reg, pool, items, skips, checks, sha, rep):
    L = ["# DATASET_C_ANSWERS_v3\n",
         "Phase 13 — `train_C_answers_v3.jsonl`, structured tasks rendered as "
         "direct closed-book answers (train_kb_gold).\n",
         "## Provenance\n", "```text",
         f"artifact          datasets_v3/train_C_answers_v3.jsonl",
         f"sha256            {sha}",
         f"generator         {GENERATOR_VERSION}",
         f"source pool       datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl "
         f"({len(pool)} tasks)",
         f"holdout registry  {reg['policy_version']} frozen {reg['frozen_date']}",
         "```\n",
         f"## Eligibility\n",
         f"**{len(items)}** of **{len(pool)}** pool tasks are C-eligible.\n",
         "| excluded reason | count |", "|---|--:|"]
    for reason, n in sorted(skips.items()):
        L.append(f"| `{reason}` | {n} |")
    L += ["",
          "`held_out_operation:*`: README Phase 22 requires argmax_topk and "
          "group_by at zero training occurrences; these tasks remain in the "
          "pool as Phase 22's own probe source material. `held_out_value:*`: "
          "the task's values_used touches a value-held-out literal — omit "
          "the item, never truncate the truth.\n",
          "## Exposure\n", "```text",
          f"strings scanned   {rep['strings_scanned']}   (system prompt + "
          f"every question + every answer)",
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
        print(f"\nPHASE 13 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
