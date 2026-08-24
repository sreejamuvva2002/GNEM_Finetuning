"""Phase 9 gate -- freeze the Holdout Registry and Fact Exposure Ledger.

README Phase 9: "Gate. Registry frozen. **Blocks all dataset generation.**"

Writes HOLDOUT_REGISTRY_v3.json, FACT_EXPOSURE_LEDGER_v3.json and
VALUE_HOLDOUT_COST_v3.csv, then validates that the registry is complete,
internally consistent, and references no value/operation/combination the frozen
KB cannot support at the declared thresholds.

Determinism note on "timestamped" (README:406): the freeze time is the git
commit date, which is external to the file. Embedding a runtime timestamp would
break the determinism gate every phase in this repository is held to, so the
artifacts carry a frozen policy date and input hashes instead.

No dataset, probe, prediction or Q42 content is created or read.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_REG = ROOT / "datasets_v3" / "HOLDOUT_REGISTRY_v3.json"
OUT_LEDGER = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
OUT_COST = ROOT / "validation_v3" / "VALUE_HOLDOUT_COST_v3.csv"
OUT_AUDIT = ROOT / "validation_v3" / "HOLDOUT_FREEZE_v3.md"

FROZEN_INPUTS = {
    "datasets_v3/canonical_records_v3.jsonl":
        "42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488",
    "datasets_v3/company_split_groups_v3.csv":
        "a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701",
    "datasets_v3/gnem_v3.sqlite":
        "7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b",
}
# README Phase 21's published candidate counts, reproduced by ROW support.
README_CANDIDATE_COUNTS = {"processes": 26, "services": 13, "certifications": 8}


class Gate(Exception):
    """A Phase 9 invariant failed. No artifact is written."""


def build():
    for rel, exp in FROZEN_INPUTS.items():
        got = H.sha256_file(ROOT / rel)
        if got != exp:
            raise Gate(f"{rel} drifted: {got}")

    recs, split = H.load_kb()
    rows, cos, train_rows, train_cos = H.support_tables(recs, split)
    tot_rows, tot_cos = H.attribute_totals(recs, split)

    selected = {f: H.select_values(rows, train_rows, tot_rows, f,
                                   train_cos=train_cos)
                for f in H.MULTIVALUED}
    comp = H.select_composition(recs, split)

    # entity holdouts derive from the frozen Phase 3 split -- nothing new decided
    ent = {"train": sorted({r["company"] for r in recs if split[r["row_id"]] == "train"}),
           "dev": sorted({r["company"] for r in recs if split[r["row_id"]] == "dev"}),
           "test": sorted({r["company"] for r in recs if split[r["row_id"]] == "test"})}

    cost_rows, per_field = [], {}
    for f in H.MULTIVALUED:
        lost = set().union(*(train_rows[f][v] for v in selected[f]))
        lost_co = set().union(*(train_cos[f][v] for v in selected[f]))
        cov = 100.0 * (tot_rows[f] - len(lost)) / tot_rows[f]
        cov_co = 100.0 * (tot_cos[f] - len(lost_co)) / tot_cos[f]
        band = H.row_band_candidates(rows, f)
        elig = H.eligible_values(rows, f)
        per_field[f] = {
            "train_rows_total": tot_rows[f], "train_companies_total": tot_cos[f],
            "train_rows_lost": len(lost), "train_companies_lost": len(lost_co),
            "remaining_attribute_coverage_rows_pct": round(cov, 2),
            "remaining_attribute_coverage_companies_pct": round(cov_co, 2),
            # Two clearly distinct stages, never conflated into one number.
            "initial_row_band_candidate_count": len(band),
            "post_split_filter_eligible_count": len(elig),
            "post_split_filter_eligible_values": elig,
        }
        # The ledger keeps EVERY row-band candidate, including those the split
        # minima later reject, so the rejection is auditable rather than invisible.
        for v in band:
            r_lost = len(train_rows[f][v])
            reasons = []
            if rows[f][v]["train"] < H.MIN_TRAIN_SUPPORT:
                reasons.append(f"train<{H.MIN_TRAIN_SUPPORT}")
            if rows[f][v]["dev"] < H.MIN_DEV_SUPPORT:
                reasons.append(f"dev<{H.MIN_DEV_SUPPORT}")
            if rows[f][v]["test"] < H.MIN_TEST_SUPPORT:
                reasons.append(f"test<{H.MIN_TEST_SUPPORT}")
            cost_rows.append({
                "value": v, "attribute_type": f,
                "supporting_companies": len(cos[f][v]["ALL"]),
                "supporting_rows": rows[f][v]["ALL"],
                "total_support": rows[f][v]["ALL"],
                "train_support": rows[f][v]["train"],
                "dev_support": rows[f][v]["dev"],
                "test_support": rows[f][v]["test"],
                "train_companies": len(cos[f][v]["train"]),
                "test_companies": len(cos[f][v]["test"]),
                "in_row_band": True,
                "split_minima_eligible": v in elig,
                "ineligibility_reason": ";".join(reasons),
                "selected": v in selected[f],
                "removed_train_items": r_lost,
                "removed_A_fields": r_lost,
                "removed_B_items": r_lost,
                "removed_train_companies": len(train_cos[f][v]),
                "remaining_attribute_coverage": round(
                    100.0 * (tot_rows[f] - r_lost) / tot_rows[f], 2),
            })
    cost_rows.sort(key=lambda d: (d["attribute_type"], d["value"]))

    registry = {
        "registry": "HOLDOUT_REGISTRY_v3",
        "phase": 9,
        "policy_version": H.POLICY_VERSION,
        "frozen_date": H.FROZEN_DATE,
        "frozen_by": "explicit user authorization after read-only decision analysis",
        "policy_revision": H.POLICY_REVISION,
        "timestamp_note": ("the authoritative freeze timestamp is the git commit "
                           "date; a runtime timestamp is deliberately not embedded "
                           "because it would break the determinism gate"),
        "frozen_inputs": {k: H.sha256_file(ROOT / k) for k in FROZEN_INPUTS},
        "support_unit_provenance": {
            "eligibility_unit": H.SUPPORT_UNIT,
            "readme_initial_row_band_candidate_table": README_CANDIDATE_COUNTS,
            "stage_note": ("README's 26/13/8 is the STAGE-1 row-band pool. The "
                           "post-split-filter eligible pool is smaller and is "
                           "reported separately per attribute; the two are never "
                           "conflated under one name."),
            "reproduced_by": "row-occurrence support (verified cell-by-cell)",
            "supporting_companies_unit": "exact trimmed company names",
            "note": ("README's frozen 26/13/8 table is reproduced by ROW-OCCURRENCE "
                     "support; `supporting_companies` separately reports exact "
                     "trimmed company counts (README:700). The distinction is "
                     "recorded, never hidden."),
        },
        "parameters": {
            "support_band": list(H.SUPPORT_BAND),
            "min_train_support": H.MIN_TRAIN_SUPPORT,
            "min_dev_support": H.MIN_DEV_SUPPORT,
            "min_test_support": H.MIN_TEST_SUPPORT,
            "split_minima_role": ("eligibility ONLY; once a candidate clears the "
                                  "minima, split support plays no part in ranking"),
            "attribute_coverage_floor_pct": H.COVERAGE_FLOOR_PCT,
            "per_value_coverage_threshold_pct": H.PER_VALUE_COVERAGE_THRESHOLD_PCT,
            "holdout_counts": H.HOLDOUT_COUNTS,
            "selection_objective": H.SELECTION_OBJECTIVE,
            "tie_breaks": list(H.SELECTION_TIE_BREAKS),
            "tie2_dev_support_definition": H.TIE2_DEV_SUPPORT_DEFINITION,
            "test_support_role": ("eligibility only -- never an objective and "
                                  "never a tie-break. Optimising selection on "
                                  "test support would tune the pre-registration "
                                  "against test-side properties of the KB; the "
                                  "objective is decided purely on train-side "
                                  "collateral and is test-blind by construction"),
        },
        "entity_holdouts": {
            "source": "frozen Phase 3 split; nothing re-decided here",
            "counts": {k: len(v) for k, v in ent.items()},
            "dev_companies": ent["dev"], "test_companies": ent["test"],
        },
        "value_holdouts": {
            f: {"selected": list(selected[f]), **per_field[f]}
            for f in H.MULTIVALUED
        },
        "operation_holdouts": {
            "held_out_families": list(H.HELD_OUT_OPERATIONS),
            "precedence": list(H.OPERATION_PRECEDENCE),
            "constructs": {k: list(v) for k, v in H.OPERATION_CONSTRUCTS.items()},
            "basis": ("README Phase 22 requires GROUP BY, LIMIT and argmax/top-k to "
                      "appear 0 times in training gold, so all three are held out"),
            "multi_family_rule": ("exactly one operation_family per task by "
                                  "precedence; a task matching more than one "
                                  "HELD-OUT family is excluded from training "
                                  "entirely (fail closed)"),
            "applied_to_real_pool_at": "Phase 12",
        },
        "composition_holdouts": {
            "arity": H.COMPOSITION_ARITY,
            "families": [list(p) for p in H.COMPOSITION_FAMILIES],
            "held_out_sets": [list(comp)],
            "superset_rule": "for held-out H and training set T: assert not H subset-of T",
            "collateral_scope": ("structured-task exclusion only. Individual "
                                 "component literals remain independently "
                                 "train-visible unless separately selected on the "
                                 "VALUE axis. An unseen COMBINATION is not an "
                                 "unseen VALUE."),
            "min_train_rows": H.COMPOSITION_MIN_TRAIN_ROWS,
            "min_test_rows": H.COMPOSITION_MIN_TEST_ROWS,
        },
        "answer_type_conventions": {
            "answer_types": list(H.ANSWER_TYPES),
            "frozen_by": "Phase 7 grade_v3 semantics",
            "target_columns": "non-empty ordered list[str]; scalar requires exactly 1",
            "multi_part_serialization": H.MULTI_PART_SERIALIZATION,
            "multi_part_note": H.MULTI_PART_NOTE,
        },
        "logical_fingerprint": {
            "version": H.FINGERPRINT_VERSION,
            "semantic_fields": list(H.FINGERPRINT_SEMANTIC_FIELDS),
            "excluded": ["question wording", "SQL formatting", "alias spelling",
                         "column order", "example_id", "dataset path", "split",
                         "split_group", "condition", "seed"],
            "canonicalisation": "json sort_keys, separators (,:), lists sorted",
            "construction": "lfp1: + sha256(canonical utf-8)[:32]",
        },
        "fewshot_eligibility": {
            "rule": "fail closed -- unprovable eligibility means ineligible",
            "conditions": [
                "every referenced row is train-side",
                "contains no held-out value literal anywhere",
                "operation_family not held out and no held-out construct present",
                "component set C contains no held-out set H (not H subset-of C)",
                "logical_fingerprint collides with no probe item",
                "no held-out entity literal",
                "any shipped schema text or value catalogue is filtered to "
                "training-visible values",
                "eligibility is checked on FINAL RENDERED chat messages",
            ],
        },
        "exposure_policy": {
            "invariant": "exposure_count == 0 for every held-out item, every arm",
            "arms": ["A", "B", "C", "D", "BC", "BD"],
            "scan_point": ("final rendered strings, after chat-template "
                           "rendering, system-prompt and catalogue insertion, "
                           "few-shot insertion and target rendering"),
            "surfaces": ["cpt_passages", "system_prompts", "user_messages",
                         "assistant_targets", "sql_text", "schema_text",
                         "value_catalogues", "fewshot_text",
                         "combined_renderings", "repeat_renderings"],
            "omit_policy": ("omit the item, never truncate the truth -- A omits the "
                            "whole field from that row's passage, B generates no QA "
                            "for that (company, attribute), C/D emit no structured "
                            "supervision using the value"),
        },
    }
    ledger = {
        "ledger": "FACT_EXPOSURE_LEDGER_v3",
        "phase": 9,
        "policy_version": H.POLICY_VERSION,
        "frozen_date": H.FROZEN_DATE,
        "registry_sha256": None,     # filled after the registry is written
        "held_out_values": {f: list(selected[f]) for f in H.MULTIVALUED},
        "held_out_operations": list(H.HELD_OUT_OPERATIONS),
        "held_out_compositions": [list(comp)],
        "arms": {a: {"scanned": False, "exposure_count": None,
                     "artifact": None, "sha256": None}
                 for a in ["A", "B", "C", "D", "BC", "BD"]},
        "note": ("initialised at Phase 9 before any dataset exists. Each dataset "
                 "phase re-runs the scanner on its final rendered strings and "
                 "updates its arm entry; every arm must reach exposure_count 0."),
    }
    return (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
            selected, comp, ent, cost_rows, per_field, registry, ledger)


def _is_optimal(rows, train_rows, train_cos, tot, f, sel) -> bool:
    """Independently confirm the chosen set is the policy optimum."""
    import itertools
    pool = H.eligible_values(rows, f)
    k = H.HOLDOUT_COUNTS[f]
    best = None
    for c in itertools.combinations(pool, k):
        lost = set().union(*(train_rows[f][v] for v in c))
        if 100.0 * (tot[f] - len(lost)) / tot[f] < H.COVERAGE_FLOOR_PCT:
            continue
        key = (len(lost), len(set().union(*(train_cos[f][v] for v in c))),
               -sum(rows[f][v]["dev"] for v in c), tuple(sorted(c)))
        if best is None or key < best:
            best = key
    return best is not None and best[3] == tuple(sorted(sel))


def main() -> int:
    (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
     selected, comp, ent, cost_rows, per_field, registry, ledger) = build()

    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    check("frozen_inputs_unchanged", True, "canonical, split and DB hashes match")

    # README's published candidate counts must be reproduced by the frozen unit
    for f, exp in README_CANDIDATE_COUNTS.items():
        got = len(H.row_band_candidates(rows, f))
        check(f"initial_row_band_candidate_count_{f}", got == exp,
              f"{got} == {exp} (README stage-1 row-band pool)")
        elig = len(H.eligible_values(rows, f))
        check(f"post_split_filter_eligible_count_{f}", elig <= got,
              f"{elig} eligible after split minima (distinct from the {got} "
              f"row-band candidates)")

    for f in H.MULTIVALUED:
        sel = selected[f]
        check(f"count_{f}", len(sel) == H.HOLDOUT_COUNTS[f],
              f"{len(sel)} == {H.HOLDOUT_COUNTS[f]}: {', '.join(sel)}")
        band_ok = all(H.SUPPORT_BAND[0] <= rows[f][v]["ALL"] <= H.SUPPORT_BAND[1]
                      for v in sel)
        check(f"band_{f}", band_ok, f"all within {H.SUPPORT_BAND}")
        check(f"min_train_support_{f}",
              all(rows[f][v]["train"] >= H.MIN_TRAIN_SUPPORT for v in sel),
              f"all train >= {H.MIN_TRAIN_SUPPORT}")
        check(f"min_dev_support_{f}",
              all(rows[f][v]["dev"] >= H.MIN_DEV_SUPPORT for v in sel),
              f"all dev >= {H.MIN_DEV_SUPPORT} (mandatory)")
        check(f"min_test_support_{f}",
              all(rows[f][v]["test"] >= H.MIN_TEST_SUPPORT for v in sel),
              f"all test >= {H.MIN_TEST_SUPPORT} (eligibility only)")
        check(f"selection_is_collateral_minimal_{f}",
              _is_optimal(rows, train_rows, train_cos, tot_rows, f, sel),
              "no feasible combination has smaller union train-row loss")
        cov = per_field[f]["remaining_attribute_coverage_rows_pct"]
        check(f"coverage_floor_{f}", cov >= H.COVERAGE_FLOOR_PCT,
              f"{cov}% >= {H.COVERAGE_FLOOR_PCT}%")
        check(f"per_value_threshold_{f}",
              all(100.0 * (tot_rows[f] - len(train_rows[f][v])) / tot_rows[f]
                  >= H.PER_VALUE_COVERAGE_THRESHOLD_PCT for v in sel),
              f"every value individually >= {H.PER_VALUE_COVERAGE_THRESHOLD_PCT}%")
        check(f"multi_company_support_{f}",
              all(len(cos[f][v]["ALL"]) >= 2 for v in sel),
              "no held-out value lives in a single company")

    # composition
    check("composition_arity", len(comp) == H.COMPOSITION_ARITY, f"{sorted(comp)}")
    both_visible = all(
        sum(1 for r in recs if split[r["row_id"]] == "train" and H.terms(r[c], c)) > 0
        for c in comp)
    check("composition_components_train_visible", both_visible,
          "each component independently present in training")
    check("composition_collateral_scope_recorded",
          "unseen VALUE" in registry["composition_holdouts"]["collateral_scope"],
          "component literals stay train-visible unless separately value-held-out")

    # operations -- validated on SYNTHETIC fixtures; Phase 12 applies to the real pool
    fx = [("SELECT company FROM companies WHERE county='Hall County'", "filter", set()),
          ("SELECT county, COUNT(*) FROM companies GROUP BY county", "group_by", {"group_by"}),
          ("SELECT company FROM companies ORDER BY employment DESC LIMIT 5",
           "argmax_topk", {"argmax_topk"}),
          ("SELECT company FROM companies LIMIT 3", "limit_only", {"limit_only"}),
          ("SELECT county, COUNT(*) c FROM companies GROUP BY county ORDER BY c DESC LIMIT 1",
           "argmax_topk", {"argmax_topk", "group_by"})]
    check("operation_classification_deterministic",
          all(H.classify_operation(s) == e for s, e, _ in fx),
          "one family per task by frozen precedence")
    check("operation_multi_family_detected",
          H.operation_families_present(fx[4][0]) == {"argmax_topk", "group_by"},
          "a GROUP BY + ORDER BY/LIMIT task is seen as two held-out families and "
          "is excluded from training (fail closed)")
    check("operation_all_three_held_out",
          set(H.HELD_OUT_OPERATIONS) == {"argmax_topk", "group_by", "limit_only"},
          "README Phase 22 requires all three constructs at 0 occurrences")

    # fingerprint -- synthetic
    t1 = {"operation_family": "filter", "fields_used": ["county"],
          "values_used": ["Hall County"], "target_columns": ["company"],
          "answer_type": "set", "join_arity": 1, "required_constructs": [],
          "entity_dependent": False}
    t2 = dict(t1, target_columns=["company"], fields_used=["county"])
    t3 = dict(t1, values_used=["Cobb County"])
    t4 = dict(t1, answer_type="scalar", target_columns=["n"])
    check("fingerprint_same_for_equivalent",
          H.logical_fingerprint(t1) == H.logical_fingerprint(t2),
          "wording/format-insensitive")
    check("fingerprint_differs_on_value",
          H.logical_fingerprint(t1) != H.logical_fingerprint(t3), "values_used differs")
    check("fingerprint_differs_on_answer_type",
          H.logical_fingerprint(t1) != H.logical_fingerprint(t4), "answer_type differs")

    check("multi_part_serialization_frozen",
          H.MULTI_PART_SERIALIZATION == "parts_list_v1",
          "explicit parts[]; Phase 7 stand-in could not express multi-operation parts")

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    # ---- write artifacts -------------------------------------------------
    OUT_REG.parent.mkdir(parents=True, exist_ok=True)
    OUT_COST.parent.mkdir(parents=True, exist_ok=True)
    OUT_REG.write_text(json.dumps(registry, indent=2, sort_keys=True,
                                  ensure_ascii=False) + "\n", encoding="utf-8")
    ledger["registry_sha256"] = H.sha256_file(OUT_REG)
    OUT_LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True,
                                     ensure_ascii=False) + "\n", encoding="utf-8")
    with OUT_COST.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cost_rows[0].keys()))
        w.writeheader()
        w.writerows(cost_rows)
    _audit(registry, cost_rows, per_field, checks, comp, selected)

    print("\nAll Phase 9 gates passed.")
    for f in H.MULTIVALUED:
        print(f"  {f:15} {', '.join(selected[f])}  -> coverage "
              f"{per_field[f]['remaining_attribute_coverage_rows_pct']}%")
    print(f"  composition    {sorted(comp)}")
    print(f"  operations     {', '.join(H.HELD_OUT_OPERATIONS)}")
    return 0


def _audit(reg, cost_rows, per_field, checks, comp, selected):
    L = ["# HOLDOUT_FREEZE_v3\n",
         "Phase 9 — the Holdout Registry and Fact Exposure Ledger, frozen **before "
         "any training dataset exists**. README Phase 9: *\"If holdouts are chosen "
         "after seeing the generated data, the holdout that gets picked is the one "
         "the data happens to support.\"*\n",
         "> Filename is a Phase 9 provenance convention; README names "
         "`HOLDOUT_REGISTRY_v3.json`, `FACT_EXPOSURE_LEDGER_v3.json` and "
         "`VALUE_HOLDOUT_COST_v3.csv`, which are the protocol artifacts.\n",
         "## Policy revision (v3.0 -> v3.1)\n",
         "This registry was first frozen as `holdout_v3.0` and **revised the same "
         "day** after independent review. The earlier version is not hidden.\n",
         "| changed | from | to |", "|---|---|---|",
         "| split minima | train>=2, test>=1 | train>=2, **dev>=1**, test>=1 (all mandatory) |",
         "| objective | maximise total test support | **minimize union of train rows lost** |",
         "| tie-breaks | train rows, dev rows, name | **exact-company union, summed dev support, lexicographic** |",
         "| test support | objective | **eligibility only** |",
         "",
         "**Why.** " + H.POLICY_REVISION["why"] + "\n",
         "**Provenance.** " + H.POLICY_REVISION["provenance_note"] + "\n",
         "## Frozen inputs\n", "```text"]
    for k, v in reg["frozen_inputs"].items():
        L.append(f"{k:44} {v}")
    L += ["```\n", "## Support-unit provenance (frozen interpretation)\n",
          "README Phase 21's published candidate table — **26 process / 13 service / "
          "8 certification** — is reproduced by **row-occurrence** support, verified "
          "cell by cell against the frozen KB. `supporting_companies` separately "
          "reports **exact trimmed company** counts (README:700). Both units appear "
          "in `VALUE_HOLDOUT_COST_v3.csv`; the distinction is never hidden.\n",
          "## Frozen parameters\n", "```text",
          f"support band                 {reg['parameters']['support_band']}",
          f"min train support            {reg['parameters']['min_train_support']}",
          f"min test support             {reg['parameters']['min_test_support']}",
          f"attribute coverage floor     {reg['parameters']['attribute_coverage_floor_pct']}%",
          f"per-value threshold          {reg['parameters']['per_value_coverage_threshold_pct']}%",
          f"holdout counts               {reg['parameters']['holdout_counts']}",
          f"objective                    {reg['parameters']['selection_objective']}",
          f"tie-breaks                   {' -> '.join(reg['parameters']['tie_breaks'])}",
          "```\n", "## Selected value holdouts\n",
          "| attribute | value | rows | train | dev | test | companies | train rows lost | coverage after |",
          "|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    for r in cost_rows:
        L.append(f"| {r['attribute_type']} | `{r['value']}` | {r['total_support']} | "
                 f"{r['train_support']} | {r['dev_support']} | {r['test_support']} | "
                 f"{r['supporting_companies']} | {r['removed_train_items']} | "
                 f"{r['remaining_attribute_coverage']}% |")
    L += ["", "### Cumulative attribute-level floor (union, not sum)\n",
          "| attribute | row-band pool | eligible after minima | train rows | lost | remaining coverage | companies remaining |",
          "|---|--:|--:|--:|--:|--:|--:|"]
    for f, d in per_field.items():
        L.append(f"| {f} | {d['initial_row_band_candidate_count']} | "
                 f"{d['post_split_filter_eligible_count']} | {d['train_rows_total']} | "
                 f"{d['train_rows_lost']} | **{d['remaining_attribute_coverage_rows_pct']}%** | "
                 f"{d['remaining_attribute_coverage_companies_pct']}% |")
    L += ["",
          "A row carrying two held-out values is lost once, so the cumulative cost is "
          "the union of affected rows rather than the sum.\n",
          "**Recorded selection characteristic:** maximising test support "
          "concentrates the processes/services selection in the battery/EV cluster, "
          "because battery values are test-heavy in the frozen split. This is an "
          "artefact of the deterministic objective, not cherry-picking, and it means "
          "the value axis measures slot transfer mostly within one domain. Recorded "
          "here so the final report can state it.\n",
          "## Operation holdouts\n",
          f"Held out: {', '.join(f'`{o}`' for o in reg['operation_holdouts']['held_out_families'])} — "
          "README Phase 22 requires all three defining constructs to appear **0 times** "
          "in training gold.\n",
          "Exactly one `operation_family` per task by precedence "
          f"({' > '.join(reg['operation_holdouts']['precedence'])}); a task matching "
          "more than one held-out family is **excluded from training entirely** so the "
          "zero-occurrence assertion stays unambiguous. Validated on synthetic "
          "fixtures — Phase 12 applies this frozen policy to the real task pool.\n",
          "## Compositional holdout\n",
          f"Arity {reg['composition_holdouts']['arity']}, one held-out set: "
          f"**{{{', '.join(comp)}}}**, chosen by lowest train support then "
          "lexicographic.\n",
          "**Collateral scope (frozen):** " +
          reg["composition_holdouts"]["collateral_scope"] + "\n",
          "## Conventions frozen here\n",
          f"- `logical_fingerprint` **{reg['logical_fingerprint']['version']}** over "
          f"{len(reg['logical_fingerprint']['semantic_fields'])} semantic fields\n"
          f"- multi-part serialization **{reg['answer_type_conventions']['multi_part_serialization']}**\n"
          f"- few-shot eligibility: fail closed, "
          f"{len(reg['fewshot_eligibility']['conditions'])} conditions\n",
          "## Exposure policy\n",
          f"`exposure_count == 0` for every held-out item across "
          f"{', '.join(reg['exposure_policy']['arms'])}, scanned on "
          f"{reg['exposure_policy']['scan_point']}.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        L.append(f"| `{n}` | {'PASS' if ok else 'FAIL'} | {d} |")
    L.append("")
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, H.HoldoutError) as e:
        print(f"\nPHASE 9 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
