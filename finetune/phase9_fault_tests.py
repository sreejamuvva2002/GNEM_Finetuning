"""Phase 9 fault tests -- the holdout policy must fail loudly, not degrade.

Synthetic perturbations and synthetic fixtures only. No dataset, probe,
prediction or Q42 content is created or read.

The centrepiece is `policy_prefers_low_collateral_over_test_support`: a synthetic
fixture where maximising test support and minimising training collateral choose
DIFFERENT sets, proving the frozen policy takes the collateral-minimal one and
that test support cannot influence ranking.

This suite also covers the post-v3.1 correction: registry verification
(candidate vs. approved), the comment/quote-aware SQL construct detector, the
list-only exposure-scanner contract, NFKC exposure normalization, the three
typed exposure assertions, the allowed-operations-per-field contract, and the
multi-part scan wrappers (scan_operations_multipart / scan_compositions_multipart).
"""

from __future__ import annotations

import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H  # noqa: E402

README_ROW_BAND = {"processes": 26, "services": 13, "certifications": 8}


def _synth():
    """Synthetic attribute where the two objectives disagree.

    lowcol_a / lowcol_b share the SAME 2 train rows -> union 2, but little test.
    bigtest_a / bigtest_b sit on 6 disjoint train rows -> union 6, lots of test.
    Maximising test support would take the bigtest pair; the frozen policy must
    take the lowcol pair.
    """
    rows = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    train_rows = defaultdict(lambda: defaultdict(set))
    train_cos = defaultdict(lambda: defaultdict(set))
    f = "synth"
    spec = {
        "lowcol_a": (dict(ALL=6, train=2, dev=1, test=3), {1, 2}, {"C1", "C2"}),
        "lowcol_b": (dict(ALL=6, train=2, dev=1, test=3), {1, 2}, {"C1", "C2"}),
        "bigtest_a": (dict(ALL=12, train=3, dev=1, test=8), {10, 11, 12}, {"D1", "D2", "D3"}),
        "bigtest_b": (dict(ALL=12, train=3, dev=1, test=8), {13, 14, 15}, {"D4", "D5", "D6"}),
    }
    for v, (sup, tr, co) in spec.items():
        for k, n in sup.items():
            rows[f][v][k] = n
        train_rows[f][v] = set(tr)
        train_cos[f][v] = set(co)
    return f, rows, train_rows, train_cos


def main() -> int:
    out = []

    def rec(name, ok, detail):
        out.append((name, bool(ok), detail))

    def expect(name, fn, exc, detail):
        try:
            fn()
            out.append((name, False, f"*** NOT RAISED *** {detail}"))
        except exc as e:
            out.append((name, True, f"{type(e).__name__}: {str(e)[:56]}"))
        except Exception as e:  # noqa: BLE001
            out.append((name, False, f"wrong error {type(e).__name__}: {e}"))

    recs, split = H.load_kb()
    rows, cos, train_rows, train_cos = H.support_tables(recs, split)
    tot, _ = H.attribute_totals(recs, split)
    # Phase 9 is not approved: no PHASE9_APPROVAL.json anchor exists yet, so
    # load_registry() correctly refuses. Fault tests and synthetic validation
    # use the candidate-audit loader.
    reg = H.load_candidate_registry_for_phase9_audit()

    # ---- 1. THE CENTREPIECE: objectives disagree, policy takes low collateral
    f, srows, str_, scos = _synth()
    orig_k = dict(H.HOLDOUT_COUNTS)
    try:
        H.HOLDOUT_COUNTS[f] = 2
        stot = {f: 100}
        chosen = H.select_values(srows, str_, stot, f, train_cos=scos)
        by_test = max(itertools.combinations(sorted(srows[f]), 2),
                      key=lambda c: sum(srows[f][v]["test"] for v in c))
        rec("policy_prefers_low_collateral_over_test_support",
            set(chosen) == {"lowcol_a", "lowcol_b"}
            and set(by_test) == {"bigtest_a", "bigtest_b"},
            f"policy chose {sorted(chosen)} (union 2 train rows); a "
            f"max-test-support rule would have chosen {sorted(by_test)} "
            f"(union 6, test 16). The two genuinely disagree.")
        rec("test_support_cannot_affect_ranking",
            set(chosen) != set(by_test),
            "ranking is decided on train-side collateral only")
    finally:
        H.HOLDOUT_COUNTS.clear()
        H.HOLDOUT_COUNTS.update(orig_k)

    # ---- 2. split minima are each mandatory -----------------------------
    for label, key, lo in (("dev", "dev", H.MIN_DEV_SUPPORT),
                           ("train", "train", H.MIN_TRAIN_SUPPORT),
                           ("test", "test", H.MIN_TEST_SUPPORT)):
        offenders = [v for fld in H.MULTIVALUED
                     for v in H.row_band_candidates(rows, fld)
                     if rows[fld][v][key] < lo and v in H.eligible_values(rows, fld)]
        rec(f"{label}_below_minimum_is_ineligible", not offenders,
            f"0 candidates with {label} < {lo} survive eligibility")

    # the concrete values the old policy wrongly selected
    for v, fld in (("ISO 22301", "certifications"), ("OHSAS 18001", "certifications")):
        rec(f"rejected_dev0_candidate_{v.replace(' ', '_').replace('/', '_')}",
            v not in H.eligible_values(rows, fld)
            and rows[fld][v]["dev"] == 0,
            f"{v}: dev_support 0 -> ineligible (was wrongly selected before)")

    # ---- 3. pool-stage terminology --------------------------------------
    for fld, exp in README_ROW_BAND.items():
        band = len(H.row_band_candidates(rows, fld))
        elig = len(H.eligible_values(rows, fld))
        rec(f"row_band_reproduces_readme_{fld}", band == exp,
            f"stage-1 row-band {band} == README {exp}")
        rec(f"stages_reported_distinctly_{fld}", band != elig,
            f"row-band {band} != post-filter eligible {elig}; both recorded")
        d = reg["value_holdouts"][fld]
        rec(f"registry_records_both_stages_{fld}",
            d["initial_row_band_candidate_count"] == band
            and d["post_split_filter_eligible_count"] == elig,
            "registry carries both counts under unambiguous names")

    # ---- 4. objective and tie-break ordering -----------------------------
    for fld in H.MULTIVALUED:
        sel = tuple(reg["value_holdouts"][fld]["selected"])
        pool = H.eligible_values(rows, fld)
        k = H.HOLDOUT_COUNTS[fld]
        feas = []
        for c in itertools.combinations(pool, k):
            lost = set().union(*(train_rows[fld][v] for v in c))
            if 100.0 * (tot[fld] - len(lost)) / tot[fld] < H.COVERAGE_FLOOR_PCT:
                continue
            feas.append((len(lost),
                         len(set().union(*(train_cos[fld][v] for v in c))),
                         -sum(rows[fld][v]["dev"] for v in c), tuple(sorted(c))))
        feas.sort()
        rec(f"objective_is_union_train_row_loss_{fld}",
            bool(feas) and feas[0][3] == tuple(sorted(sel)),
            f"selected set has the minimum union train-row loss ({feas[0][0]})")
        rec(f"coverage_floor_enforced_{fld}",
            all(100.0 * (tot[fld] - x[0]) / tot[fld] >= H.COVERAGE_FLOOR_PCT
                for x in feas),
            f"every feasible combination retains >= {H.COVERAGE_FLOOR_PCT}%")

    # tie-break ordering, on synthetic ties
    tie = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    tr = defaultdict(lambda: defaultdict(set))
    tc = defaultdict(lambda: defaultdict(set))
    g = "tie"
    for v, (co, dev) in {"aa": ({"X"}, 1), "bb": ({"X"}, 5), "cc": ({"X", "Y"}, 5)}.items():
        for kk, n in dict(ALL=6, train=2, dev=dev, test=2).items():
            tie[g][v][kk] = n
        tr[g][v] = {1, 2}
        tc[g][v] = co
    try:
        H.HOLDOUT_COUNTS[g] = 1
        # all three share the same 2 train rows -> tie on PRIMARY; cc has more
        # companies -> loses TIE1; aa and bb tie there, bb has more dev -> TIE2
        pick = H.select_values(tie, tr, {g: 100}, g, train_cos=tc)
        rec("tie1_exact_company_union", "cc" not in pick,
            "the wider company footprint loses tie-break 1")
        rec("tie2_dev_support_maximised", pick == ("bb",),
            "with equal collateral and companies, higher dev support wins (bb dev=5 > aa dev=1)")
    finally:
        H.HOLDOUT_COUNTS.clear()
        H.HOLDOUT_COUNTS.update(orig_k)

    # final lexicographic tie-break
    lex = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    lr = defaultdict(lambda: defaultdict(set))
    lc = defaultdict(lambda: defaultdict(set))
    g2 = "lex"
    for v in ("zebra", "alpha"):
        for kk, n in dict(ALL=6, train=2, dev=2, test=2).items():
            lex[g2][v][kk] = n
        lr[g2][v] = {1, 2}
        lc[g2][v] = {"X"}
    try:
        H.HOLDOUT_COUNTS[g2] = 1
        rec("tie3_lexicographic_final",
            H.select_values(lex, lr, {g2: 100}, g2, train_cos=lc) == ("alpha",),
            "fully tied candidates resolve to the lexicographically smallest")
    finally:
        H.HOLDOUT_COUNTS.clear()
        H.HOLDOUT_COUNTS.update(orig_k)

    # ---- 5. infeasible configurations refuse ----------------------------
    of = H.COVERAGE_FLOOR_PCT

    def _floor():
        H.COVERAGE_FLOOR_PCT = 99.9
        try:
            H.select_values(rows, train_rows, tot, "certifications", train_cos=train_cos)
        finally:
            H.COVERAGE_FLOOR_PCT = of
    expect("impossible_coverage_floor_refused", _floor, H.HoldoutError, "accepted")

    def _pool():
        H.HOLDOUT_COUNTS["certifications"] = 99
        try:
            H.select_values(rows, train_rows, tot, "certifications", train_cos=train_cos)
        finally:
            H.HOLDOUT_COUNTS.clear()
            H.HOLDOUT_COUNTS.update(orig_k)
    expect("oversized_holdout_count_refused", _pool, H.HoldoutError, "accepted")

    # ---- 6. determinism --------------------------------------------------
    a = {f2: H.select_values(rows, train_rows, tot, f2, train_cos=train_cos)
         for f2 in H.MULTIVALUED}
    b = {f2: H.select_values(rows, train_rows, tot, f2, train_cos=train_cos)
         for f2 in H.MULTIVALUED}
    rec("deterministic_rerun_identical", a == b,
        "repeated optimisation yields identical selected sets")

    # ---- 7. exposure / operation / composition regression ----------------
    hv = H.held_out_values(reg)
    leaked = hv["processes"][0]
    r1 = H.scan_strings(["clean", f"catalogue mentioning {leaked}"], reg)
    rec("value_exposure_detected", r1["total_exposures"] == 1,
        f"1 exposure of {leaked!r} in a catalogue-like string")
    expect("exposure_assert_fails_loudly",
           lambda: H.assert_value_scan_verified(r1), H.HoldoutError, "accepted")
    rec("clean_strings_pass",
        H.scan_strings(["Injection Molding; Machining"], reg)["total_exposures"] == 0,
        "0 exposures on clean text")
    op = H.scan_operations(["SELECT company FROM companies WHERE county='Hall County'",
                            "SELECT county, COUNT(*) FROM companies GROUP BY county",
                            "SELECT company FROM companies ORDER BY employment DESC LIMIT 5",
                            "SELECT company FROM companies LIMIT 3"], reg)
    rec("operation_exposure_all_three_families",
        op["operation_exposure_counts"] == {"argmax_topk": 1, "group_by": 1,
                                            "limit_only": 1},
        "GROUP_BY, LIMIT and ARGMAX_TOPK each detected independently")
    held = reg["composition_holdouts"]["held_out_sets"][0]
    comp = H.scan_compositions([list(held) + ["county"], ["processes"], ["services"]], reg)
    rec("composition_superset_violation_detected", comp["composition_violations"] == 1,
        f"H={held} inside a 3-component set is caught; single components are not")
    rec("composition_does_not_hide_component_values",
        H.scan_strings(["a task about processes and county"], reg)["total_exposures"] == 0,
        "component-bearing text is clean unless it carries a held-out VALUE")

    # ---- 8. fingerprint --------------------------------------------------
    base = {"operation_family": "filter", "fields_used": ["county"],
            "values_used": ["Hall County"], "target_columns": ["company"],
            "answer_type": "set", "join_arity": 1, "required_constructs": [],
            "entity_dependent": False,
            "logical_components": {"op": "eq", "field": "county",
                                   "value": "Hall County"}}
    rec("fingerprint_ignores_non_semantic_fields",
        H.logical_fingerprint(base) == H.logical_fingerprint(
            dict(base, example_id="fx1", split="train", seed=7, question="other?")),
        "example_id/split/seed/question do not change the fingerprint")

    # ======================================================================
    # POST-v3.1 CORRECTION REGRESSION TESTS
    # ======================================================================

    # ---- 9. SQL construct detector: comment/quote-aware, not raw substring
    bypass_cases = [
        ("SELECT county, COUNT(*) FROM companies GROUP/**/BY county",
         "group_by", {"group_by"}),
        ("SELECT county, COUNT(*) FROM companies GROUP\nBY county",
         "group_by", {"group_by"}),
        ("SELECT county, COUNT(*) FROM companies GROUP  BY county",
         "group_by", {"group_by"}),
    ]
    for sql, exp_class, exp_families in bypass_cases:
        rec(f"detect_evasion_{hash(sql) & 0xffff:x}",
            H.classify_operation(sql) == exp_class
            and H.operation_families_present(sql) == exp_families,
            f"comment/whitespace variant of GROUP BY still detected: {sql!r}")

    negative_cases = [
        ("SELECT 'LIMIT' AS x FROM companies", set()),
        ("SELECT \"GROUP BY\" FROM companies", set()),
        ("SELECT `GROUP BY` FROM companies", set()),
        ("SELECT company FROM companies WHERE x = '[GROUP BY]'", set()),
        ("SELECT group_id FROM companies", set()),
    ]
    for sql, exp in negative_cases:
        rec(f"no_false_positive_{hash(sql) & 0xffff:x}",
            H.operation_families_present(sql) == exp,
            f"literal/identifier/plain-word variant NOT falsely detected: {sql!r}")

    rec("escaped_quotes_handled",
        H.operation_families_present("SELECT company FROM t WHERE x = 'it''s a LIMIT'") == set(),
        "an escaped quote inside a string literal does not break literal-span detection")

    # ---- 10. exposure scanner: list-only contract -------------------------
    expect("scan_strings_rejects_bare_string",
           lambda: H.scan_strings("AS9100", reg), TypeError, "accepted")
    expect("scan_strings_rejects_dict",
           lambda: H.scan_strings({"a": "AS9100"}, reg), TypeError, "accepted")
    rec("scan_strings_detects_in_list",
        H.scan_strings(["AS9100"], reg)["total_exposures"] >= 1
        if "AS9100" in hv.get("certifications", ()) else True,
        "list-wrapped scalar-equivalent input is scanned correctly")
    expect("scan_operations_rejects_bare_string",
           lambda: H.scan_operations("SELECT 1", reg), TypeError, "accepted")
    expect("scan_operations_rejects_dict",
           lambda: H.scan_operations({"p": "SELECT 1"}, reg), TypeError, "accepted")
    expect("scan_compositions_rejects_dict",
           lambda: H.scan_compositions({"p": ["processes"]}, reg), TypeError, "accepted")

    # ---- 11. exposure normalization: NFKC, case, whitespace ---------------
    leaked_cert = hv["certifications"][0]
    variants = [leaked_cert, leaked_cert.lower(), f"  {leaked_cert}  ",
                leaked_cert.upper()]
    for v in variants:
        r = H.scan_strings([f"catalogue text {v} more text"], reg)
        rec(f"normalization_detects_{hash(v) & 0xffff:x}",
            r["total_exposures"] >= 1,
            f"case/whitespace variant of {leaked_cert!r} detected: {v!r}")
    rec("normalization_no_false_positive_on_unrelated_text",
        H.scan_strings(["nothing relevant here at all"], reg)["total_exposures"] == 0,
        "unrelated text is not falsely flagged")

    # ---- 12. exposure-report assertion states -----------------------------
    good_report = H.scan_strings(["clean text with no held-out literals"], reg)
    H.assert_value_scan_verified(good_report)  # must not raise
    rec("verified_zero_passes", True, "a real scan with 0 exposures passes")

    empty_report = H.scan_strings([], reg)
    expect("empty_scan_does_not_pass_as_verified_zero",
           lambda: H.assert_value_scan_verified(empty_report), H.HoldoutError,
           "accepted a vacuous scan of 0 strings as a zero-exposure certificate")

    malformed = {"total_exposures": 0}  # missing required keys
    expect("malformed_value_report_rejected",
           lambda: H.assert_value_scan_verified(malformed), H.HoldoutError,
           "accepted a malformed report")

    good_op_report = H.scan_operations(["SELECT company FROM companies"], reg)
    H.assert_operation_scan_verified(good_op_report)
    rec("operation_verified_zero_passes", True, "a real op-scan with 0 exposures passes")
    empty_op_report = H.scan_operations([], reg)
    expect("empty_operation_scan_does_not_pass",
           lambda: H.assert_operation_scan_verified(empty_op_report), H.HoldoutError,
           "accepted a vacuous operation scan")

    good_comp_report = H.scan_compositions([["processes"]], reg)
    H.assert_composition_scan_verified(good_comp_report)
    rec("composition_verified_zero_passes", True,
        "a real composition-scan with 0 violations passes")
    empty_comp_report = H.scan_compositions([], reg)
    expect("empty_composition_scan_does_not_pass",
           lambda: H.assert_composition_scan_verified(empty_comp_report), H.HoldoutError,
           "accepted a vacuous composition scan")

    # ---- 13. multi-part scan wrappers: scan every part, not the dict's keys
    held_process = hv["processes"][0]
    gold_sql_multipart = {
        "count": "SELECT COUNT(*) AS n FROM certifications",
        "companies": "SELECT company FROM companies LIMIT 5",
    }
    # Reproduce the bug directly: passing the dict to scan_operations (if it
    # didn't raise) would scan the KEYS "count"/"companies", not the SQL.
    direct_would_scan_keys = H.operation_families_present("count") | \
        H.operation_families_present("companies")
    rec("multipart_dict_keys_are_not_sql",
        direct_would_scan_keys == set(),
        "confirms WHY the dict-direct call would have silently found nothing")
    mp_op = H.scan_operations_multipart(gold_sql_multipart, reg)
    rec("scan_operations_multipart_finds_real_violation",
        mp_op["operation_exposure_counts"]["limit_only"] == 1,
        "scan_operations_multipart correctly scans .values(), catching the "
        "bare LIMIT in the 'companies' part")
    expect("scan_operations_multipart_rejects_non_dict",
           lambda: H.scan_operations_multipart(["SELECT 1"], reg), TypeError,
           "accepted")

    held_pair = reg["composition_holdouts"]["held_out_sets"][0]
    parts_components = {"part_a": [held_pair[0]], "part_b": [held_pair[1]]}
    per_part = [H.scan_compositions([c], reg)["composition_violations"]
                for c in parts_components.values()]
    rec("composition_per_part_alone_misses_violation",
        sum(per_part) == 0,
        f"checking {list(parts_components.values())} separately reports 0 "
        "violations even though the held-out pair straddles the two parts")
    mp_comp = H.scan_compositions_multipart(parts_components, reg)
    rec("scan_compositions_multipart_catches_split_violation",
        mp_comp["composition_violations"] == 1,
        "the task-level UNION of both parts' components correctly reports "
        "the held-out pair present across the whole task")
    expect("scan_compositions_multipart_rejects_non_dict",
           lambda: H.scan_compositions_multipart([["x"]], reg), TypeError,
           "accepted")

    # ---- 14. registry loader: candidate vs approved, provenance -----------
    rec("candidate_loader_works_pre_approval", reg is not None,
        "load_candidate_registry_for_phase9_audit() succeeds with no "
        "approval anchor present")
    expect("production_loader_refuses_without_approval",
           H.load_registry, H.Phase9NotApproved,
           "load_registry() must raise Phase9NotApproved, not silently serve "
           "an unapproved registry")

    current_text = H.REGISTRY.read_text(encoding="utf-8")
    current_data = json.loads(current_text)

    # stale (mutated) registry: flip one selected value, leave everything
    # else (including upstream hashes) untouched.
    stale = json.loads(current_text)
    stale["value_holdouts"]["certifications"]["selected"] = ["ISO 22301", "OHSAS 18001"]
    expect("mutated_selected_value_rejected",
           lambda: H._load_and_verify_candidate(json.dumps(stale)), H.HoldoutError,
           "a hand-edited selected value, with hashes/policy_version untouched, "
           "must be caught by recompute-and-compare")

    malformed_registry = json.dumps({"registry": "HOLDOUT_REGISTRY_v3"})
    expect("registry_missing_sections_rejected",
           lambda: H._load_and_verify_candidate(malformed_registry), H.HoldoutError,
           "a registry missing required sections must fail closed")

    dup = json.loads(current_text)
    dup["value_holdouts"]["processes"]["selected"] = \
        [dup["value_holdouts"]["processes"]["selected"][0]] * 4
    expect("duplicate_selected_value_rejected",
           lambda: H._load_and_verify_candidate(json.dumps(dup)), H.HoldoutError,
           "duplicate entries in a selected-value list must fail closed")

    not_json = "{not valid json"
    expect("malformed_json_rejected",
           lambda: H._load_and_verify_candidate(not_json), H.HoldoutError,
           "unparseable registry text must fail closed, not crash uncontrolled")

    # deep immutability: mutating a returned section must not corrupt the
    # stored original.
    section = reg["value_holdouts"]
    section["processes"]["selected"].append("INJECTED")
    section2 = reg["value_holdouts"]
    rec("deep_immutability_holds",
        "INJECTED" not in section2["processes"]["selected"],
        "mutating a returned section does not corrupt the registry's stored "
        "canonical text -- each access returns a fresh parse")

    # ---- 15. allowed operations per field ----------------------------------
    aopf = reg["allowed_operations_per_field"]
    rec("allowed_operations_present_in_loaded_registry",
        "field_semantic_operations" in aopf, "contract survives load/verify round-trip")
    rec("primary_oems_restricted",
        not ({"group_by", "argmax_topk"} & set(aopf["field_semantic_operations"]["primary_oems"])),
        "Primary OEMs excludes group_by/argmax_topk at the SEMANTIC layer, "
        "not just training eligibility (README:537-538)")
    rec("address_no_aggregation",
        not ({"aggregation", "group_by"} & set(aopf["field_semantic_operations"]["address"])),
        "Address gets no structured aggregation (README:538)")
    rec("employment_ranking_semantically_valid_but_training_ineligible",
        "argmax_topk" in aopf["field_semantic_operations"]["employment"]
        and "argmax_topk" not in aopf["field_training_eligible_operations"]["employment"],
        "ranking by employment is semantically meaningful (needed by the "
        "Phase 22 operation-heldout probe) but training-ineligible (argmax_topk "
        "is held out everywhere) -- the two layers correctly disagree")
    limit_only_query = "SELECT company FROM companies LIMIT 5"
    rec("limit_only_excluded_regardless_of_field_policy",
        "limit_only" in H.operation_families_present(limit_only_query),
        "limit_only is field-agnostic and caught by the real SQL scanner "
        "independent of any per-field policy lookup")

    # ---- 16. second independent-audit round: reproduced-and-fixed bugs ----
    mutated = reg._data()
    mutated["value_holdouts"]["certifications"]["selected"] = ["AS9100"]
    expect("reg_kwarg_rejects_raw_dict",
                lambda: H.scan_strings(["x"], mutated), TypeError,
                "a raw dict passed as reg= bypassed all registry verification")
    expect("verified_registry_rejects_direct_construction",
                lambda: H.VerifiedCandidateRegistry("{}"), H.HoldoutError,
                "constructing the wrapper directly, bypassing verification, "
                "must be rejected")

    hash_only_approval = json.dumps({"approved_registry_sha256": reg.sha256()})

    def _approval_missing_fields():
        orig_path = H.PHASE9_APPROVAL
        import tempfile as _tf
        with _tf.TemporaryDirectory() as td:
            p = __import__("pathlib").Path(td) / "PHASE9_APPROVAL.json"
            p.write_text(hash_only_approval, encoding="utf-8")
            H.PHASE9_APPROVAL = p
            try:
                H.load_registry()
            finally:
                H.PHASE9_APPROVAL = orig_path
    expect("approval_requires_commit_and_date_not_just_hash",
                _approval_missing_fields, H.HoldoutError,
                "a hash-only approval record (no approved_commit/approved_date) "
                "must be rejected as incomplete")

    r_none = H.scan_strings([None, None, None], reg)
    expect("none_entries_are_not_real_scan_evidence",
                lambda: H.assert_value_scan_verified(r_none), H.HoldoutError,
                "an all-None input must not certify as a real zero-exposure scan")
    r_none_op = H.scan_operations([None, None], reg)
    expect("none_sql_entries_are_not_real_scan_evidence",
                lambda: H.assert_operation_scan_verified(r_none_op), H.HoldoutError,
                "an all-None SQL input must not certify as a real operation scan")

    expect("multipart_composition_scan_rejects_zero_parts",
                lambda: H.scan_compositions_multipart({}, reg), H.HoldoutError,
                "a multi-part task with zero parts cannot yield a genuine "
                "composition-scan certificate")
    expect("multipart_operation_scan_rejects_zero_parts",
                lambda: H.scan_operations_multipart({}, reg), H.HoldoutError,
                "a multi-part task with zero parts cannot yield a genuine "
                "operation-scan certificate")

    fake_hits_mismatch = {"exposure_counts": {"AS9100": 0}, "total_exposures": 0,
                          "strings_scanned": 5,
                          "hits": [{"attribute": "certifications", "value": "AS9100",
                                   "string_index": 0}]}
    expect("hits_nonempty_with_zero_total_is_malformed",
                lambda: H.assert_value_scan_verified(fake_hits_mismatch),
                H.HoldoutError,
                "hits present while total_exposures==0 must be rejected as "
                "internally inconsistent, not accepted as verified-zero")
    fake_violations_mismatch = {"composition_violations": 0,
                                "violations": [{"index": 0, "held_out_set": ["x"],
                                               "training_set": ["x", "y"]}],
                                "sets_scanned": 1}
    expect("violations_nonempty_with_zero_count_is_malformed",
                lambda: H.assert_composition_scan_verified(fake_violations_mismatch),
                H.HoldoutError,
                "violations present while composition_violations==0 must be "
                "rejected as internally inconsistent")

    fp_base_leaf = {"op": "eq", "field": "county", "value": "Hall County"}
    for bad_lc, label in (({}, "empty_dict"), ({"op": "AND"}, "and_no_operands"),
                          ({"op": "eq"}, "leaf_no_content")):
        expect(f"fingerprint_rejects_incomplete_logical_components_{label}",
                    lambda bad_lc=bad_lc: H.logical_fingerprint(
                        dict(base, logical_components=bad_lc)),
                    H.HoldoutError,
                    f"an incomplete logical_components tree ({bad_lc}) must "
                    f"fail closed, not silently produce a fingerprint")
    rec("fingerprint_accepts_well_formed_leaf",
        bool(H.logical_fingerprint(dict(base, logical_components=fp_base_leaf))),
        "a genuinely complete leaf node still produces a fingerprint")

    for n, ok, d in out:
        print(f"  [{'PASS' if ok else 'FAIL'}] fault:{n}: {d}")
    missed = [n for n, ok, _ in out if not ok]
    if missed:
        print(f"\nFAULT SUITE FAILED: {missed}", file=sys.stderr)
        return 1
    print(f"\nAll {len(out)} Phase 9 fault checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
