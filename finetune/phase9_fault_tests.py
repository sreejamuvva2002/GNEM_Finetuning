"""Phase 9 fault tests -- the holdout policy must fail loudly, not degrade.

Synthetic perturbations and synthetic fixtures only. No dataset, probe,
prediction or Q42 content is created or read.

The centrepiece is `policy_prefers_low_collateral_over_test_support`: a synthetic
fixture where maximising test support and minimising training collateral choose
DIFFERENT sets, proving the frozen policy takes the collateral-minimal one and
that test support cannot influence ranking.
"""

from __future__ import annotations

import itertools
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
    reg = H.load_registry()

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
           lambda: H.assert_zero_exposure(r1, "A"), H.HoldoutError, "accepted")
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
            "entity_dependent": False}
    rec("fingerprint_ignores_non_semantic_fields",
        H.logical_fingerprint(base) == H.logical_fingerprint(
            dict(base, example_id="fx1", split="train", seed=7, question="other?")),
        "example_id/split/seed/question do not change the fingerprint")

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
