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

`--check`: a genuine read-only verification mode. Recomputes expected state and
compares it to the committed artifacts; performs NO writes; exits nonzero on
drift. Use this to re-verify a frozen registry without regenerating it.

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

# The chronology text used to say "before any dataset exists" without
# qualification, imprecise once Phase 10 was briefly generated (from v3.0)
# and fully reverted before v3.1 was frozen. Corrected here (the one
# generator function whose output ends up in both HOLDOUT_FREEZE_v3.md and
# FACT_EXPOSURE_LEDGER_v3.json's "note" field) so both downstream artifacts
# inherit the accurate wording rather than each needing separate fixing.
CHRONOLOGY_NOTE = (
    "v3.0 was frozen before any training dataset existed. Phase 10 "
    "(train_A_cpt_v3.jsonl) was then generated from v3.0 and fully reverted. "
    "v3.1 was frozen after that correction, before any training dataset was "
    "ever built from it. No model training or evaluation ever used "
    "v3.0-derived data.")


class Gate(Exception):
    """A Phase 9 invariant failed. No artifact is written."""


def build():
    for rel, exp in FROZEN_INPUTS.items():
        got = H.sha256_file(ROOT / rel)
        if got != exp:
            raise Gate(f"{rel} drifted: {got}")

    (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
     selected, comp, ent, per_field, registry) = H.build_registry_bundle()

    cost_rows = []
    for f in H.MULTIVALUED:
        band = H.row_band_candidates(rows, f)
        elig = H.eligible_values(rows, f)
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
                # Renamed from removed_* (Phase 9 correction, finding 9D):
                # these are Phase-9-time row-occurrence PROJECTIONS computed
                # before any A/B dataset exists, not measured post-generation
                # outcomes. The est_ prefix says so; the CSV never claims more
                # precision than it has.
                "est_removed_train_items": r_lost,
                "est_removed_A_fields": r_lost,
                "est_removed_B_items": r_lost,
                "est_removed_train_companies": len(train_cos[f][v]),
                "remaining_attribute_coverage": round(
                    100.0 * (tot_rows[f] - r_lost) / tot_rows[f], 2),
            })
    cost_rows.sort(key=lambda d: (d["attribute_type"], d["value"]))

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
        "note": ("initialised at Phase 9. " + CHRONOLOGY_NOTE + " Each dataset "
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


def run_gates():
    """Build the registry and run every Phase 9 gate. Returns
    (checks, artifacts_tuple). Raises Gate on any failed check. Performs NO
    writes -- callers decide whether to persist."""
    (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
     selected, comp, ent, cost_rows, per_field, registry, ledger) = build()

    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    check("frozen_inputs_unchanged", True, "canonical, split and DB hashes match")

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
           "argmax_topk", {"argmax_topk", "group_by"}),
          # The reproduced evasion: a comment splitting the keyword must not
          # defeat detection.
          ("SELECT county, COUNT(*) FROM companies GROUP/**/BY county",
           "group_by", {"group_by"})]
    check("operation_classification_deterministic",
          all(H.classify_operation(s) == e for s, e, _ in fx),
          "one family per task by frozen precedence, including the "
          "GROUP/**/BY evasion attempt")
    check("operation_multi_family_detected",
          H.operation_families_present(fx[4][0]) == {"argmax_topk", "group_by"},
          "a GROUP BY + ORDER BY/LIMIT task is seen as two held-out families and "
          "is excluded from training (fail closed)")
    check("operation_all_three_held_out",
          set(H.HELD_OUT_OPERATIONS) == {"argmax_topk", "group_by", "limit_only"},
          "README Phase 22 requires all three constructs at 0 occurrences")

    # allowed operations per field -- README-required contract, previously absent
    aopf = registry["allowed_operations_per_field"]
    check("allowed_operations_per_field_present",
          "field_semantic_operations" in aopf and "field_training_eligible_operations" in aopf,
          "README:388 'allowed operations per field' contract is frozen in the registry")
    eligible_ops = aopf["field_training_eligible_operations"]
    check("training_eligible_is_semantic_minus_heldout",
          all(set(eligible_ops[f]) == H.FIELD_SEMANTIC_OPERATIONS[f] - H.QUERY_LEVEL_CONSTRUCTS
              for f in H.FIELD_SEMANTIC_OPERATIONS),
          "field_training_eligible_operations[f] == field_semantic_operations[f] "
          "- HELD_OUT_OPERATIONS for every field (exact set equality)")
    check("no_held_out_family_ever_training_eligible",
          all(not (set(v) & set(H.HELD_OUT_OPERATIONS)) for v in eligible_ops.values()),
          "no field's training-eligible set contains a held-out family")
    check("named_field_restrictions_sourced_from_readme",
          set(aopf["field_specific_restrictions"]) == {"primary_oems", "address", "row_id"},
          "Primary OEMs / Address / row_id restrictions frozen verbatim from README")

    # fingerprint -- synthetic, lfp2 (logical_components required)
    leaf_a = {"op": "eq", "field": "certifications", "value": "AS9100"}
    leaf_b = {"op": "eq", "field": "processes", "value": "Refining"}
    t1 = {"operation_family": "filter", "fields_used": ["county"],
          "values_used": ["Hall County"], "target_columns": ["company"],
          "answer_type": "set", "join_arity": 1, "required_constructs": [],
          "entity_dependent": False,
          "logical_components": {"op": "AND", "operands": [leaf_a, leaf_b]}}
    t2 = dict(t1, target_columns=["company"], fields_used=["county"])
    t3 = dict(t1, values_used=["Cobb County"])
    t4 = dict(t1, answer_type="scalar", target_columns=["n"])
    t5 = dict(t1, logical_components={"op": "OR", "operands": [leaf_a, leaf_b]})
    t6 = dict(t1, logical_components={"op": "AND", "operands": [leaf_b, leaf_a]})
    check("fingerprint_same_for_equivalent",
          H.logical_fingerprint(t1) == H.logical_fingerprint(t2),
          "wording/format-insensitive")
    check("fingerprint_differs_on_value",
          H.logical_fingerprint(t1) != H.logical_fingerprint(t3), "values_used differs")
    check("fingerprint_differs_on_answer_type",
          H.logical_fingerprint(t1) != H.logical_fingerprint(t4), "answer_type differs")
    check("fingerprint_differs_on_and_vs_or",
          H.logical_fingerprint(t1) != H.logical_fingerprint(t5),
          "lfp2 correction: AND and OR over the same predicates must differ "
          "(lfp1 collided these)")
    check("fingerprint_same_on_commutative_reorder",
          H.logical_fingerprint(t1) == H.logical_fingerprint(t6),
          "reordered AND operands hash identically (same logical task)")

    def _missing_components():
        H.logical_fingerprint(dict(t1, logical_components=None))
    try:
        _missing_components()
        check("fingerprint_missing_components_fails_closed", False, "*** NOT RAISED ***")
    except H.HoldoutError:
        check("fingerprint_missing_components_fails_closed", True,
              "missing logical_components raises rather than hashing a weaker skeleton")

    check("multi_part_serialization_frozen",
          H.MULTI_PART_SERIALIZATION == "parts_list_v1",
          "explicit parts[]; Phase 7 stand-in could not express multi-operation parts")
    check("multipart_result_representation_frozen",
          H.MULTIPART_RESULT_REPRESENTATION_VERSION == "multipart_result_v1",
          "keyed independent per-part execution results, not a shared "
          "discriminator-column table")

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    artifacts = (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
                selected, comp, ent, cost_rows, per_field, registry, ledger)
    return checks, artifacts


def main() -> int:
    checks, artifacts = run_gates()
    (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
     selected, comp, ent, cost_rows, per_field, registry, ledger) = artifacts

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


def check_only() -> int:
    """Genuine read-only --check: recompute expected state, compare to the
    committed artifacts, report drift, exit nonzero on mismatch. NO writes."""
    reg_path_before = OUT_REG.stat().st_mtime_ns if OUT_REG.is_file() else None
    ledger_path_before = OUT_LEDGER.stat().st_mtime_ns if OUT_LEDGER.is_file() else None
    cost_path_before = OUT_COST.stat().st_mtime_ns if OUT_COST.is_file() else None

    problems = []
    try:
        candidate = H.load_candidate_registry_for_phase9_audit()
        print("  [PASS] registry matches deterministic recomputation from "
              "frozen inputs (recompute-and-compare)")
    except H.HoldoutError as e:
        problems.append(str(e))
        print(f"  [FAIL] registry recomputation check: {e}")

    try:
        checks, _ = run_gates()
        failed = [n for n, ok, _ in checks if not ok]
        if failed:
            problems.append(f"gates failed: {failed}")
        else:
            print(f"  [PASS] all {len(checks)} Phase 9 gates re-verified")
    except Gate as e:
        problems.append(str(e))
        print(f"  [FAIL] gate re-verification: {e}")

    # Prove --check performed no writes.
    reg_path_after = OUT_REG.stat().st_mtime_ns if OUT_REG.is_file() else None
    ledger_path_after = OUT_LEDGER.stat().st_mtime_ns if OUT_LEDGER.is_file() else None
    cost_path_after = OUT_COST.stat().st_mtime_ns if OUT_COST.is_file() else None
    if (reg_path_before, ledger_path_before, cost_path_before) != \
       (reg_path_after, ledger_path_after, cost_path_after):
        problems.append("BUG: --check modified a file's mtime -- it must be read-only")

    if problems:
        print(f"\nPHASE 9 --check FAILED: {len(problems)} problem(s)", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("\nPhase 9 --check: all clear, zero writes performed.")
    return 0


def _audit(reg, cost_rows, per_field, checks, comp, selected):
    aopf = reg["allowed_operations_per_field"]
    L = ["# HOLDOUT_FREEZE_v3\n",
         "Phase 9 — the Holdout Registry and Fact Exposure Ledger. " +
         CHRONOLOGY_NOTE + " README Phase 9: *\"If holdouts are chosen "
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
         "## Phase 9 correction (registry/code hardening, post-v3.1)\n",
         "Independent audit found real gaps in the supporting code and registry "
         "completeness after v3.1 was frozen. **The nine selected values and the "
         "selection algorithm above are unchanged** -- full independent "
         "recomputation (a standalone script importing nothing from "
         "`holdout_v3.py`) confirms the same nine values remain optimal under "
         "the frozen objective. What changed:\n",
         "- " + "\n- ".join(H.PHASE9_CORRECTION["changed"]) + "\n",
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
          "```\n",
          "## Candidate pool (all row-band values, selected and rejected)\n",
          "Every value in the 3-15 row-support band, whether or not it was "
          "selected -- kept so a rejection is auditable rather than invisible. "
          "**This table is the full candidate pool, not the selection** (Phase "
          "9 correction, finding 9A: an earlier version of this document named "
          "this table 'Selected value holdouts', which was misleading since it "
          "listed all candidates). See the next section for the actual 9 "
          "selected values.\n",
          "| attribute | value | selected? | rows | train | dev | test | companies | est. train rows lost | coverage after |",
          "|---|---|:--:|--:|--:|--:|--:|--:|--:|--:|"]
    for r in cost_rows:
        L.append(f"| {r['attribute_type']} | `{r['value']}` | "
                 f"{'**YES**' if r['selected'] else 'no'} | {r['total_support']} | "
                 f"{r['train_support']} | {r['dev_support']} | {r['test_support']} | "
                 f"{r['supporting_companies']} | {r['est_removed_train_items']} | "
                 f"{r['remaining_attribute_coverage']}% |")
    L += ["", "## Selected value holdouts (the actual 9)\n",
          "| attribute | value | rows | train | dev | test | companies |",
          "|---|---|--:|--:|--:|--:|--:|"]
    for r in cost_rows:
        if r["selected"]:
            L.append(f"| {r['attribute_type']} | `{r['value']}` | {r['total_support']} | "
                     f"{r['train_support']} | {r['dev_support']} | {r['test_support']} | "
                     f"{r['supporting_companies']} |")
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
          "**Recorded selection characteristic, corrected (Phase 9 correction, "
          "finding 9B).** An earlier version of this document attributed the "
          "processes/services selection landing in the battery/EV cluster to "
          "\"maximising test support\" -- that was the v3.0 objective, and the "
          "sentence survived describing v3.1 numbers by mistake. The true v3.1 "
          "mechanism: these values are selected because they independently "
          "carry the LOWEST union train-row collateral among eligible "
          "candidates under the frozen minimize-collateral objective. Test "
          "support plays no causal role in v3.1 -- it is eligibility-only. "
          "That the collateral-minimal values also cluster in the battery/EV "
          "domain is a property of this frozen KB (those values happen to have "
          "low train support alongside adequate dev support), not a "
          "consequence of the selection objective.\n",
          "## Operation holdouts\n",
          f"Held out: {', '.join(f'`{o}`' for o in reg['operation_holdouts']['held_out_families'])} — "
          "README Phase 22 requires all three defining constructs to appear **0 times** "
          "in training gold.\n",
          "Exactly one `operation_family` per task by precedence "
          f"({' > '.join(reg['operation_holdouts']['precedence'])}); a task matching "
          "more than one held-out family is **excluded from training entirely** so the "
          "zero-occurrence assertion stays unambiguous. Detection is comment/quote-aware "
          "(Phase 9 correction): comments and string/identifier literals are replaced "
          "with a single space before keyword matching, so a lexical trick like "
          "`GROUP/**/BY` cannot evade it. Validated on synthetic "
          "fixtures — Phase 12 applies this frozen policy to the real task pool.\n",
          "## Allowed operations per field (Phase 9 correction: previously absent)\n",
          "README requires this contract to be frozen at Phase 9; it was missing "
          "until this correction. Four layers: semantic validity (what's meaningful "
          "for a field, including held-out operations where meaningful -- needed by "
          "the Phase 22 operation-heldout probe), the three query-level held-out "
          "constructs, named field-specific restrictions sourced verbatim from "
          "README, and the derived training-eligible set (semantic minus held-out, "
          "a literal set difference). This map is a candidate-generation-time "
          "heuristic; the authoritative training-eligibility gate is always the "
          "real SQL-construct scanner run against a task's actual rendered SQL.\n",
          "```text",
          f"query-level constructs (held out everywhere): {aopf['query_level_constructs']}",
          f"named restrictions: {sorted(aopf['field_specific_restrictions'])}",
          "```\n",
          "## Compositional holdout\n",
          f"Arity {reg['composition_holdouts']['arity']}, one held-out set: "
          f"**{{{', '.join(comp)}}}**, chosen by lowest train support then "
          "lexicographic.\n",
          "**Collateral scope (frozen):** " +
          reg["composition_holdouts"]["collateral_scope"] + "\n",
          "**Multi-part tasks (Phase 9 correction):** " +
          reg["composition_holdouts"]["multipart_note"] + "\n",
          "## Conventions frozen here\n",
          f"- `logical_fingerprint` **{reg['logical_fingerprint']['version']}** over "
          f"{len(reg['logical_fingerprint']['semantic_fields'])} semantic fields "
          "(Phase 9 correction: lfp1 -> lfp2, folds canonicalized "
          "`logical_components` into the hash so AND/OR predicate structure is no "
          "longer invisible to it)\n"
          f"- multi-part serialization **{reg['answer_type_conventions']['multi_part_serialization']}**, "
          f"result representation **{reg['answer_type_conventions']['multipart_result_representation_version']}** "
          "(keyed independent per-part results, not a shared discriminator table)\n"
          f"- few-shot eligibility: fail closed, "
          f"{len(reg['fewshot_eligibility']['conditions'])} conditions\n",
          "## Exposure policy\n",
          f"`exposure_count == 0` for every held-out item across "
          f"{', '.join(reg['exposure_policy']['arms'])}, scanned on "
          f"{reg['exposure_policy']['scan_point']}.\n",
          "**Normalization (Phase 9 correction):** " +
          reg["exposure_policy"]["normalization"] + "\n",
          "**Scope boundary:** " + reg["exposure_policy"]["scope_boundary"] + "\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        L.append(f"| `{n}` | {'PASS' if ok else 'FAIL'} | {d} |")
    L.append("")
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        if "--check" in sys.argv[1:]:
            raise SystemExit(check_only())
        raise SystemExit(main())
    except (Gate, H.HoldoutError) as e:
        print(f"\nPHASE 9 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
