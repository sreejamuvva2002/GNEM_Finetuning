"""Phase 11 -- build `train_B_facts_v3.jsonl`.

README Phase 11: cell-level factual QA over `train_kb`; processes, services and
certifications rendered as SET answers. No `Certification Count` target. No QA
whose answer is a sentinel.

MULTI-ROW CONFLICTS: SKIP, NEVER MERGE (README:456-459, CLAUDE.md #11). Nine
companies in the frozen KB carry more than one canonical row (different
facilities under one company name). Location never disambiguates them --
every multi-row company shares one location across its rows -- but other
attributes (employment, product/service, processes, ...) often genuinely
differ per facility. v2 solved this by concatenating the distinct values
(`"; ".join(uniq)`), which can silently produce incoherent gold like
`Indirect; No` for `ev_battery_relevant`. v3 does the opposite: a
(company, attribute) pair with disagreeing values across that company's rows
is DROPPED entirely, never artificially disambiguated or merged, and recorded
in `MULTIROW_CONFLICTS_v3.csv`.

SENTINELS ARE NOT FACTS. A candidate value equal to a frozen sentinel (scalar:
"Not specified" / "Not applicable"; certifications: "None identified after
search") never becomes a QA target -- the pair is skipped, not asked about.

HELD-OUT VALUES: omit the item, never truncate the truth (same policy as
Phase 10). A multi-valued field whose value contains a held-out term produces
no QA for that (company, attribute) pair at all.
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
GENERATOR_VERSION = "b_facts_v3.0"

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
    "location": "Where in Georgia is {c} located?",
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
    "certifications": "Which certification standards does {c} hold?",
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
    "employment": "{c} employs {v} people.",
    "product_or_service": "{c}'s product or service is {v}.",
    "ev_battery_relevant": "EV or battery relevance for {c} is recorded as {v}.",
    "classification_method": "{c} was classified by {v}.",
}
SET_ANSWER = {
    "processes": "{c}'s recorded processes are: {v}.",
    "services": "{c}'s recorded services are: {v}.",
    "certifications": "{c} holds the following certifications: {v}.",
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
    skipped, never merged.
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


def eligible_value(field: str, value, held: dict) -> tuple[bool, str | None]:
    """Whether this resolved value is a legitimate QA target. Returns
    (ok, skip_reason). A sentinel or a held-out-tainted set is never a QA
    target -- README:454, README:404 (omit the item, never truncate)."""
    if field in SET_FIELDS:
        terms = H.terms(value, field)
        if not terms:
            return False, "sentinel_or_empty"
        if set(terms) & set(held[field]):
            return False, "holdout_value_present"
        return True, None
    if value is None or (isinstance(value, str) and value.strip() in SCALAR_SENTINELS):
        return False, "sentinel_or_empty"
    return True, None


def render_item(company: str, field: str, value) -> dict:
    if field in SET_FIELDS:
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
        values, conflicts = resolve_company_values(train_by_co[co])
        for f in conflicts:
            skips["multirow_conflict"] += 1
        for f in ALL_FIELDS:
            if f not in values:
                continue  # conflict, already counted above
            ok, reason = eligible_value(f, values[f], held)
            if not ok:
                skips[reason] += 1
                continue
            items.append(render_item(co, f, values[f]))
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
    check("no_sentinel_answers", not sentinel_hits,
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
    all_strings = [CLOSED_BOOK_SYSTEM] + render_texts
    rep = H.scan_strings(all_strings, reg)
    H.assert_value_scan_verified(rep)
    check("exposure_count_zero", rep["total_exposures"] == 0,
          f"0 held-out literals across {rep['strings_scanned']} rendered strings")

    check("multirow_conflicts_recorded",
          all(r["action"] == "skipped_company_level_fact" for r in conflict_rows)
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
                                          "row_ids", "split", "action"])
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
          "`multirow_conflict`: the (company, attribute) pair disagreed across that "
          "company's rows and was dropped, never merged (README:456-459). "
          "`sentinel_or_empty`: the resolved value is a frozen sentinel or an empty "
          "set (no QA is ever asked about a sentinel). `holdout_value_present`: a "
          "set field's value contains a held-out term, so the WHOLE field is "
          "omitted for that company (omit the item, never truncate the truth).\n",
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
          f"actually suppress a B item; the other 4 companies are dev/test-"
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
