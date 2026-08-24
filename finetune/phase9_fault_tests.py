"""Phase 9 fault tests -- the holdout policy must fail loudly, not degrade.

Synthetic perturbations only. No dataset, probe, prediction or Q42 content is
created or read.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H          # noqa: E402
import phase9_freeze_holdouts as P9  # noqa: E402


def main() -> int:
    out = []

    def expect(name, fn, exc, detail):
        try:
            fn()
            out.append((name, False, f"*** NOT RAISED *** {detail}"))
        except exc as e:
            out.append((name, True, f"{type(e).__name__}: {str(e)[:58]}"))
        except Exception as e:  # noqa: BLE001
            out.append((name, False, f"wrong error {type(e).__name__}: {e}"))

    recs, split = H.load_kb()
    rows, cos, train_rows = H.support_tables(recs, split)
    tot, _ = H.attribute_totals(recs, split)
    reg = H.load_registry()

    # 1. an impossible coverage floor must fail, not silently relax
    orig = H.COVERAGE_FLOOR_PCT
    def _floor():
        H.COVERAGE_FLOOR_PCT = 99.9
        try:
            H.select_values(rows, train_rows, tot, "processes")
        finally:
            H.COVERAGE_FLOOR_PCT = orig
    expect("impossible_coverage_floor_refused", _floor, H.HoldoutError,
           "floor 99.9% accepted")

    # 2. requesting more holdouts than the pool supports must fail
    origk = dict(H.HOLDOUT_COUNTS)
    def _pool():
        H.HOLDOUT_COUNTS["certifications"] = 99
        try:
            H.select_values(rows, train_rows, tot, "certifications")
        finally:
            H.HOLDOUT_COUNTS.update(origk)
    expect("oversized_holdout_count_refused", _pool, H.HoldoutError, "k=99 accepted")

    # 3. exposure of a held-out literal in ANY rendered string must fail
    hv = H.held_out_values(reg)
    leaked = hv["processes"][0]
    rep = H.scan_strings(["a clean training string",
                          f"system prompt mentioning {leaked} in a catalogue"], reg)
    out.append(("value_exposure_detected_in_rendered_string",
                rep["total_exposures"] == 1,
                f"1 exposure of {leaked!r} found in a system-prompt-like string"))
    expect("exposure_assert_fails_loudly",
           lambda: H.assert_zero_exposure(rep, "A"), H.HoldoutError,
           "non-zero exposure accepted")

    clean = H.scan_strings(["Injection Molding; Machining", "no held-out terms here"], reg)
    out.append(("clean_strings_pass_exposure_scan", clean["total_exposures"] == 0,
                f"0 exposures across {clean['strings_scanned']} strings"))

    # 4. held-out operation constructs must be detected in SQL
    op = H.scan_operations(["SELECT company FROM companies WHERE county='Hall County'",
                            "SELECT county, COUNT(*) FROM companies GROUP BY county"], reg)
    out.append(("operation_exposure_detected", op["total_exposures"] == 1
                and op["operation_exposure_counts"]["group_by"] == 1,
                "GROUP BY detected once; the plain filter is clean"))

    # 5. superset rule: a training set containing the held-out pair must violate
    held = reg["composition_holdouts"]["held_out_sets"][0]
    comp = H.scan_compositions([list(held) + ["county"], ["processes"], ["services"]], reg)
    out.append(("composition_superset_violation_detected",
                comp["composition_violations"] == 1,
                f"H={held} inside a 3-component training set is caught; "
                f"single components are not"))

    # 6. an individual component literal is NOT hidden merely by composition holdout
    out.append(("composition_does_not_hide_component_values",
                "unseen VALUE" in reg["composition_holdouts"]["collateral_scope"]
                and H.scan_strings(["a task about processes and county"], reg)[
                    "total_exposures"] == 0,
                "component-bearing text is clean unless it carries a held-out VALUE"))

    # 7. every selected value must have test support (a probe with no items)
    bad = [v for f in H.MULTIVALUED for v in reg["value_holdouts"][f]["selected"]
           if rows[f][v]["test"] < 1]
    out.append(("no_selected_value_lacks_test_support", not bad,
                f"{len(bad)} selected values with test_support 0"))

    # 8. fingerprint must not depend on non-semantic fields
    base = {"operation_family": "filter", "fields_used": ["county"],
            "values_used": ["Hall County"], "target_columns": ["company"],
            "answer_type": "set", "join_arity": 1, "required_constructs": [],
            "entity_dependent": False}
    noisy = dict(base, example_id="fx999", split="train", seed=7,
                 question="Totally different wording?")
    out.append(("fingerprint_ignores_non_semantic_fields",
                H.logical_fingerprint(base) == H.logical_fingerprint(noisy),
                "example_id/split/seed/question do not change the fingerprint"))

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
