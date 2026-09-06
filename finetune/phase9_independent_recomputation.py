"""Phase 9 correction, Section F: FULL independent recomputation of the v3.1
value holdouts.

Deliberately does NOT import `holdout_v3.py`. Every computational step --
row-band membership, split-minima eligibility, support counting, the
combinatorial search over ALL feasible k-combinations for every candidate
(not a spot-check of the 9 winners), and the tie-break order -- is
reimplemented from scratch here, reading only the two raw frozen input files
directly. This is a verification tool proving the production selector's
OUTPUT is correct, not a component the production pipeline depends on.

The frozen PARAMETERS below (support band, minima, coverage floor, holdout
counts, tie-break order) are the policy under test, reproduced from
`README.md`/`HOLDOUT_REGISTRY_v3.json` for reference -- reusing them is
correct because this script verifies the SELECTOR's arithmetic, not the
parameters themselves, which are a frozen, user-approved decision (Phase 9,
CLAUDE.md order-of-authority) not re-litigated here.
"""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "datasets_v3" / "canonical_records_v3.jsonl"
SPLITS = ROOT / "datasets_v3" / "company_split_groups_v3.csv"

MULTIVALUED = ("processes", "services", "certifications")
CERT_SENTINEL = "None identified after search"
SUPPORT_BAND = (3, 15)
MIN_TRAIN_SUPPORT = 2
MIN_DEV_SUPPORT = 1
MIN_TEST_SUPPORT = 1
COVERAGE_FLOOR_PCT = 85.0
HOLDOUT_COUNTS = {"processes": 4, "services": 3, "certifications": 2}

FROZEN_SELECTED = {
    "processes": ("Battery Module Assembly", "Battery Pack Assembly",
                 "Battery Recycling Logistics", "Refining"),
    "services": ("Battery Collection", "Battery Repurposing",
                "Circular Economy Consulting"),
    "certifications": ("AS9100", "ISO/IEC 17025"),
}


def terms(value, field) -> list[str]:
    if not value or (field == "certifications" and value == CERT_SENTINEL):
        return []
    return [t for t in value.split("; ") if t]


def load():
    recs = [json.loads(l) for l in CANONICAL.read_text(encoding="utf-8").splitlines()]
    with SPLITS.open(encoding="utf-8") as fh:
        split = {int(r["row_id"]): r["split"] for r in csv.DictReader(fh)}
    return recs, split


def independent_select(recs, split, field) -> dict:
    """Fresh, from-scratch re-derivation for one attribute. Returns a report
    dict with the selected set and enough evidence to audit it."""
    support: dict[str, dict[str, int]] = {}
    train_rows: dict[str, set] = {}
    train_cos: dict[str, set] = {}
    total_train_rows_with_attr = 0

    for r in recs:
        s = split[r["row_id"]]
        vals = set(terms(r.get(field, ""), field))
        if vals and s == "train":
            total_train_rows_with_attr += 1
        for v in vals:
            d = support.setdefault(v, {"ALL": 0, "train": 0, "dev": 0, "test": 0})
            d["ALL"] += 1
            d[s] += 1
            if s == "train":
                train_rows.setdefault(v, set()).add(r["row_id"])
                train_cos.setdefault(v, set()).add(r["company"])

    lo, hi = SUPPORT_BAND
    row_band = sorted(v for v, d in support.items() if lo <= d["ALL"] <= hi)
    eligible = sorted(
        v for v in row_band
        if support[v]["train"] >= MIN_TRAIN_SUPPORT
        and support[v]["dev"] >= MIN_DEV_SUPPORT
        and support[v]["test"] >= MIN_TEST_SUPPORT)

    k = HOLDOUT_COUNTS[field]
    best_key, best_combo = None, None
    all_feasible = []
    for combo in itertools.combinations(eligible, k):
        lost = set()
        for v in combo:
            lost |= train_rows.get(v, set())
        cov = 100.0 * (total_train_rows_with_attr - len(lost)) / total_train_rows_with_attr
        if cov < COVERAGE_FLOOR_PCT:
            continue
        cos = set()
        for v in combo:
            cos |= train_cos.get(v, set())
        key = (len(lost), len(cos), -sum(support[v]["dev"] for v in combo),
              tuple(sorted(combo)))
        all_feasible.append((key, tuple(sorted(combo))))
        if best_key is None or key < best_key:
            best_key, best_combo = key, tuple(sorted(combo))

    if best_key is None:
        raise ValueError(f"{field}: no feasible {k}-combination found")

    no_better_candidate_exists = all(
        key[0] >= best_key[0] for key, combo in all_feasible if combo != best_combo)

    return {
        "field": field,
        "row_band_pool_size": len(row_band),
        "eligible_pool_size": len(eligible),
        "selected": best_combo,
        "union_train_row_loss": best_key[0],
        "feasible_combination_count": len(all_feasible),
        "no_eligible_candidate_beats_selection": no_better_candidate_exists,
    }


def main() -> int:
    recs, split = load()
    all_ok = True
    print("Phase 9 independent recomputation -- no import of holdout_v3.py\n")
    for field in MULTIVALUED:
        report = independent_select(recs, split, field)
        expected = tuple(sorted(FROZEN_SELECTED[field]))
        match = report["selected"] == expected
        all_ok = all_ok and match and report["no_eligible_candidate_beats_selection"]

        print(f"{field}")
        print(f"  row-band pool             {report['row_band_pool_size']}")
        print(f"  eligible pool             {report['eligible_pool_size']}")
        print(f"  feasible k-combinations   {report['feasible_combination_count']}")
        print(f"  independent recompute  -> {report['selected']}")
        print(f"  frozen registry value  -> {expected}")
        print(f"  MATCH                     {match}")
        print(f"  union train-row loss      {report['union_train_row_loss']}")
        print(f"  no eligible candidate beats this selection: "
              f"{report['no_eligible_candidate_beats_selection']}")
        print()

    print("=" * 70)
    print("ALL THREE ATTRIBUTES MATCH THE FROZEN REGISTRY AND ARE PROVEN OPTIMAL"
          if all_ok else
          "MISMATCH OR SUBOPTIMALITY DETECTED -- STOP, do not proceed")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
