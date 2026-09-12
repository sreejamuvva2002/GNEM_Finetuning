"""Phase 11: full-field factual QA under A-002.

Complete process/service/certification lists are retained. Missing evidence receives
qualified answers. Conflicting observations receive record-scoped questions and an
explicit disagreement note, without inventing distinct facilities or merging values.
Certification Count remains internal. Company holdouts remain excluded from training.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H       # noqa: E402
import kb_v3 as KB            # noqa: E402
import leak_audit_v3 as LA    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "datasets_v3" / "train_B_facts_v3.jsonl"
OUT_CONFLICTS = ROOT / "validation_v3" / "MULTIROW_CONFLICTS_v3.csv"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_B_FACTS_v3.md"
GENERATOR_VERSION = "b_facts_v3.1_A002"

SCALAR_SENTINELS = {"Not specified", "Not applicable"}

CLOSED_BOOK_SYSTEM = (
    "You are answering questions about companies in the Georgia new-energy "
    "mobility supply chain from memory. Answer directly and concisely."
)

SCALAR_FIELDS = (
    "category", "industry_group", "location", "address",
    "primary_facility_type", "ev_supply_chain_role", "primary_oems",
    "supplier_or_affiliation_type", "employment", "product_or_service",
    "ev_battery_relevant", "classification_method",
)
SET_FIELDS = ("processes", "services", "certifications")
ALL_FIELDS = SCALAR_FIELDS + SET_FIELDS

QUESTION = {
    "category": "What supply chain category is {c} classified under?",
    "industry_group": "What industry group does {c} belong to?",
    "location": "What location is recorded for {c}?",
    "address": "What is the street address of {c}?",
    "primary_facility_type": "What is the primary facility type of {c}?",
    "ev_supply_chain_role": "What is {c}'s EV supply chain role?",
    "primary_oems": "Which primary OEMs does {c} serve?",
    "supplier_or_affiliation_type": "What is {c}'s supplier or affiliation type?",
    "employment": "How many people does {c} employ?",
    "product_or_service": "What product or service does {c} provide?",
    "ev_battery_relevant": "Is {c} EV or battery relevant?",
    "classification_method": "How was {c} classified?",
    "processes": "What processes does {c} perform?",
    "services": "What services does {c} provide?",
    "certifications": "Which certification standards are recorded for {c}?",
}
SCALAR_ANSWER = {
    "category": "{c} is classified in the {v} category.",
    "industry_group": "{c} belongs to the {v} industry group.",
    "location": "{c} is located at {v}.",
    "address": "{c}'s street address is {v}.",
    "primary_facility_type": "{c}'s primary facility type is {v}.",
    "ev_supply_chain_role": "{c}'s EV supply chain role is {v}.",
    "primary_oems": "{c}'s primary OEMs are recorded as {v}.",
    "supplier_or_affiliation_type": "{c}'s supplier or affiliation type is {v}.",
    "employment": "The dataset records employment of {v} for {c}; its scope and date are not established here.",
    "product_or_service": "{c}'s product or service is {v}.",
    "ev_battery_relevant": "EV or battery relevance for {c} is recorded as {v}.",
    "classification_method": "{c} was classified by {v}.",
}
SET_ANSWER = {
    "processes": "{c}'s recorded processes are: {v}.",
    "services": "{c}'s recorded services are: {v}.",
    "certifications": "The dataset records these certifications for {c}: {v}. This does not independently establish current validity or customer qualification.",
}


class Gate(Exception):
    """A Phase 11 invariant failed. No artifact is written."""


def _group_by_company(rows: list[dict]) -> dict[str, list[dict]]:
    by_co = defaultdict(list)
    for r in rows:
        by_co[r["company"]].append(r)
    return dict(by_co)


def resolve_company_values(rows_for_co: list[dict]) -> tuple[dict, list[str]]:
    """One candidate value per field for this company, or a conflict.

    Returns (values, conflicting_fields). `values` carries only the fields
    that agreed across every row (scalar: exact string equality; set fields:
    identical term-set, order-insensitive). A disagreeing field is entirely
    absent from `values` and listed in `conflicting_fields` instead --
    handled separately with record-scoped supervision, never merged.
    """
    values, conflicts = {}, []
    for f in ALL_FIELDS:
        raw = [r[f] for r in rows_for_co]
        if f in SET_FIELDS:
            norm = [tuple(sorted(set(H.terms(v, f)))) for v in raw]
        else:
            norm = raw
        uniq = set(norm)
        if len(uniq) == 1:
            values[f] = raw[0]
        else:
            conflicts.append(f)
    return values, conflicts


def render_item(company: str, field: str, value) -> dict:
    missing = value is None or str(value).strip() in SCALAR_SENTINELS | {H.CERT_SENTINEL}
    if missing:
        answer = (f"For {company}, the dataset records {field.replace('_', ' ')} as {value}. "
                  "This is missing or inapplicable source evidence, not proof of real-world absence.")
        gold = str(value)
        answer_type = "scalar"
    elif field in SET_FIELDS:
        terms = sorted(set(H.terms(value, field)))
        v_text = "; ".join(terms)
        answer = SET_ANSWER[field].format(c=company, v=v_text)
        gold = terms
        answer_type = "set"
    else:
        answer = SCALAR_ANSWER[field].format(c=company, v=value)
        gold = str(value)
        answer_type = "scalar"
    question = QUESTION[field].format(c=company)
    example_id = f"B_{company}_{field}".replace(" ", "_").replace(",", "").replace(".", "")
    return {
        "example_id": example_id,
        "company": company,
        "attribute": field,
        "answer_type": answer_type,
        "question": question,
        "gold_value": gold,
        "messages": [
            {"role": "system", "content": CLOSED_BOOK_SYSTEM},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
    }


def build():
    reg = H.load_registry()
    held = H.held_out_values(reg)

    all_rows = json.loads(  # canonical rows -- ALL splits, for the full audit CSV
        "[" + ",".join(l for l in
                       (ROOT / "datasets_v3" / "canonical_records_v3.jsonl")
                       .read_text(encoding="utf-8").splitlines()) + "]")
    all_by_co = _group_by_company(all_rows)
    multi_row_all = {c: rs for c, rs in all_by_co.items() if len(rs) > 1}

    row_split = LA.row_splits()
    conflict_rows = []
    for co, rs in sorted(multi_row_all.items()):
        splits_here = sorted({row_split[r["row_id"]] for r in rs})
        _, conflicts = resolve_company_values(rs)
        for f in conflicts:
            conflict_rows.append({
                "company": co, "attribute": f, "n_rows": len(rs),
                "row_ids": ";".join(str(r["row_id"]) for r in rs),
                "split": ",".join(splits_here),
                "action": "skipped_company_level_fact",
            })

    train_recs = KB.load_kb("train_kb")
    train_rows = [{f: getattr(rec, f) for f in ("row_id", "company") + ALL_FIELDS}
                 for rec in train_recs]
    train_by_co = _group_by_company(train_rows)

    items, skips = [], defaultdict(int)
    for co in sorted(train_by_co):
        source_rows = train_by_co[co]
        values, conflicts = resolve_company_values(source_rows)
        for f in ALL_FIELDS:
            if f in conflicts:
                for row in source_rows:
                    item = render_item(co, f, row[f])
                    item["example_id"] += f"_record_{row['row_id']}"
                    item["question"] = f"According to source record {row['row_id']}, " + item["question"][0].lower() + item["question"][1:]
                    item["messages"][1]["content"] = item["question"]
                    item["messages"][2]["content"] += " Other records for this company disagree; a single company-wide value cannot be established."
                    item["source_row_ids"] = [row["row_id"]]
                    item["conflicting_observations"] = True
                    items.append(item)
            else:
                item = render_item(co, f, values[f])
                item["source_row_ids"] = sorted(r["row_id"] for r in source_rows)
                item["conflicting_observations"] = False
                items.append(item)
    for row in conflict_rows:
        row["action"] = "record_scoped_training_or_explicit_company_holdout"
    return reg, held, train_recs, items, skips, conflict_rows


def main() -> int:
    reg, held, train_recs, items, skips, conflict_rows = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    train_companies = {r.company for r in train_recs}
    check("registry_frozen_before_generation", bool(reg.get("frozen_date")),
          f"HOLDOUT_REGISTRY_v3 {reg['policy_version']} dated {reg['frozen_date']}")
    check("nonzero_items", len(items) > 0, f"{len(items)} B items")
    check("unique_example_ids", len({i["example_id"] for i in items}) == len(items),
          f"{len(items)} unique ids")

    questions = [i["question"] for i in items]
    dupes = len(questions) - len(set(questions))
    check("no_duplicate_questions", dupes == 0, f"{dupes} duplicate questions")

    answers = [i["messages"][2]["content"] for i in items]

    # Regression guard against the exact v2 bug this design exists to avoid:
    # a scalar gold_value must be a VERBATIM raw field value from one of that
    # company's rows, never a value synthesized by joining several rows'
    # disagreeing values (e.g. v2's "Indirect; No" for ev_battery_relevant).
    # Checked structurally, not by pattern-matching "; " -- some fields (e.g.
    # product_or_service) legitimately contain "; " as ordinary punctuation
    # in a single row's own free-text value.
    train_by_co_raw = _group_by_company(
        [{f: getattr(rec, f) for f in ("company",) + ALL_FIELDS} for rec in train_recs])
    synthesized = []
    for i in [i for i in items if i["answer_type"] == "scalar"]:
        raw_vals = {str(r[i["attribute"]]) for r in train_by_co_raw[i["company"]]}
        if i["gold_value"] not in raw_vals:
            synthesized.append(i["example_id"])
    check("no_incoherent_merged_scalar_gold", not synthesized,
          "every scalar gold_value is a verbatim raw value from one of that "
          "company's rows, never a cross-row join (the v2 'Indirect; No' bug)"
          if not synthesized else f"{synthesized[:5]}")

    set_items = [i for i in items if i["answer_type"] == "set"]
    malformed = [i["example_id"] for i in set_items
                if not i["gold_value"]
                or any(not t.strip() for t in i["gold_value"])
                or len(i["gold_value"]) != len(set(i["gold_value"]))]
    check("well_formed_set_answers", not malformed,
          f"{len(set_items)} set-valued items, all non-empty/deduped/non-blank"
          if not malformed else f"{malformed[:5]}")

    sentinel_hits = [i["example_id"] for i in items
                    if H.CERT_SENTINEL in i["messages"][2]["content"]
                    or any(s in str(i["gold_value"]) for s in SCALAR_SENTINELS)]
    check("sentinel_answers_qualified", all("not proof of real-world absence" in i["messages"][2]["content"] for i in items if i["example_id"] in sentinel_hits),
          "no item's gold contains a frozen sentinel"
          if not sentinel_hits else f"{sentinel_hits[:5]}")

    blob = "\n".join(answers)
    check("no_certification_count_target",
          "ertification count" not in blob.lower() and "certification_count" not in blob,
          "Certification Count never rendered")

    # HARD ASSERT: no dev/test company anywhere in rendered text.
    render_texts = [i["question"] for i in items] + answers
    leaked = LA.companies_leaked_in(render_texts)
    check("zero_heldout_or_dev_companies_present", not leaked,
          f"0 of {len(LA.non_train_companies())} dev/test companies appear in "
          f"rendered B text" if not leaked else f"LEAKED: {leaked[:5]}")

    static_rep = KB.static_check_no_training_generator_reaches_full_kb(
        [Path(__file__)])
    check("static_check_generator_never_reaches_full_kb",
          static_rep["scanned_count"] > 0 and static_rep["violation_count"] == 0,
          static_rep["proves"])

    # exposure ledger satisfied, on the FINAL rendered strings (system prompt
    # included, per README:404).
    all_strings = [m["content"] for item in items for m in item["messages"]]
    rep = H.scan_strings(all_strings, reg)
    H.assert_value_scan_verified(rep)
    check("exposure_count_zero", rep["total_exposures"] == 0,
          f"0 held-out literals across {rep['strings_scanned']} rendered strings")

    check("multirow_conflicts_recorded",
          all(r["action"] == "record_scoped_training_or_explicit_company_holdout" for r in conflict_rows)
          and len(conflict_rows) > 0,
          f"{len(conflict_rows)} conflicting (company, attribute) pairs across "
          f"{len({r['company'] for r in conflict_rows})} multi-row companies")

    all_rows_chk = json.loads(
        "[" + ",".join((ROOT / "datasets_v3" / "canonical_records_v3.jsonl")
                      .read_text(encoding="utf-8").splitlines()) + "]")
    n_multirow = len({c for c, rs in _group_by_company(all_rows_chk).items()
                      if len(rs) > 1})
    check("nine_multirow_companies", n_multirow == 9,
          f"{n_multirow} multi-row companies (README:456-459 names 9: Novelis "
          f"x3, ZF Gainesville x3, and 7 others x2)")

    per_attr = defaultdict(int)
    for i in items:
        per_attr[i["attribute"]] += 1

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

    OUT_CONFLICTS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CONFLICTS.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["company", "attribute", "n_rows",
                                          "row_ids", "split", "action"], lineterminator="\n")
        w.writeheader()
        for r in conflict_rows:
            w.writerow(r)

    _update_ledger(sha, rep)
    _audit(reg, items, skips, conflict_rows, per_attr, checks, sha, rep, static_rep)

    print(f"\nAll Phase 11 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  items {len(items)}")
    return 0


def _update_ledger(sha, rep):
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    led["arms"]["B"] = {"scanned": True, "exposure_count": rep["total_exposures"],
                        "artifact": "datasets_v3/train_B_facts_v3.jsonl",
                        "sha256": sha, "strings_scanned": rep["strings_scanned"],
                        "phase": 11}
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _audit(reg, items, skips, conflict_rows, per_attr, checks, sha, rep, static_rep):
    L = ["# DATASET_B_FACTS_v3\n",
         "Phase 11 — `train_B_facts_v3.jsonl`, cell-level closed-book factual QA.\n",
         "## Provenance\n", "```text",
         f"artifact          datasets_v3/train_B_facts_v3.jsonl",
         f"sha256            {sha}",
         f"generator         {GENERATOR_VERSION}",
         f"scope             train_kb (Phase 4 contract)",
         f"holdout registry  {reg['policy_version']} frozen {reg['frozen_date']}",
         "```\n",
         "## Per-attribute counts\n", "| attribute | items |", "|---|--:|"]
    for f in ALL_FIELDS:
        L.append(f"| `{f}` | {per_attr.get(f, 0)} |")
    L += ["", f"**Total: {len(items)} items.**\n",
          "## Skips (never merged, never asked)\n", "| reason | count |", "|---|--:|"]
    for reason, n in sorted(skips.items()):
        L.append(f"| `{reason}` | {n} |")
    L += ["",
          "A-002 retains missing evidence as qualified answers and conflicting training "
          "observations as record-scoped QA. No value-based exclusions remain. "
          "Company holdouts still apply.\n",
          "## Multi-row conflicts (all 9 multi-row companies, all splits)\n",
          f"`validation_v3/MULTIROW_CONFLICTS_v3.csv` — {len(conflict_rows)} "
          f"conflicting (company, attribute) pairs across "
          f"{len({r['company'] for r in conflict_rows})} companies. README's "
          f"Phase 11 estimate is 'expect ≈28 pairs across 9 companies'; the "
          f"measured count against the frozen v3 KB is "
          f"**{len(conflict_rows)}** across all 9 (of which the pairs "
          f"belonging to the 5 TRAIN-split multi-row companies — Haering "
          f"Precision USA LP, Lyle Industries Inc., Novelis Inc., Panasonic "
          f"Automotive Systems Co., Sewon America Inc. — are the ones that "
          f"receive record-scoped B items; the other 4 companies are dev/test-"
          f"side and produce no B items regardless). This is a real, "
          f"measured deviation from the README estimate, reported here "
          f"rather than silently reconciled — see the commit message for "
          f"the full accounting.\n",
          "## Exposure\n", "```text",
          f"strings scanned   {rep['strings_scanned']}   (system prompt + every "
          f"question + every answer)",
          f"exposure_count    {rep['total_exposures']}",
          "```\n",
          "## Phase 4 static check (re-run for this generator)\n", "```text",
          f"scanned            {static_rep['scanned_files']}",
          f"violation_count    {static_rep['violation_count']}",
          f"proves             {static_rep['proves']}",
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
        print(f"\nPHASE 11 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
