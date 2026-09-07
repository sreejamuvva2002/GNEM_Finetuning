# DATASET_BC_v3

Phase 15 — `train_BC_facts_answers_v3.jsonl`, the deterministic union of the frozen B and C files. Never a regenerated variant.

## Provenance

```text
artifact          datasets_v3/train_BC_facts_answers_v3.jsonl
sha256            2914d2d1346211a8ef60fecbea06dc500d3fddc83a0c2099147edd24144f3dfb
generator         bc_v3.0
source B          datasets_v3/train_B_facts_v3.jsonl sha256 17ddccd67f2c46bb94e5d948c130cd2d6c99b564a07fc171618eb0f5e3f957b0
source C          datasets_v3/train_C_answers_v3.jsonl sha256 95da32e3a9dafb4bfd66764f9e9047f1fe3ee0f50390903f24a0586e6256c9b7
```

## Composition

B: 2011 items (order 1-2011) + C: 1008 items (order 2012-3019) = 3019 total, B first then C, fixed order.

## Exposure (re-scanned, not inherited)

Correction (post-approval audit): an earlier version of this generator copied forward B/C's previously recorded exposure_count/strings_scanned without verifying those source files hadn't drifted, and without scanning anything itself. This build verifies current B/C sha256 against the ledger's recorded values first, then re-scans every rendered string in the concatenated file directly.

```text
strings scanned   9057   (system prompt + question + answer, every B and C item)
exposure_count    0
```

## Validation

| check | result | detail |
|---|---|---|
| `source_hashes_match_ledger` | PASS | B 17ddccd67f2c.. == ledger 17ddccd67f2c.. and C 95da32e3a9da.. == ledger 95da32e3a9da.. -- refusing to inherit a prior exposure verdict for drifted source |
| `b_and_c_frozen_and_nonempty` | PASS | B: 2011 items · C: 1008 items |
| `no_example_id_collision` | PASS | 3019 unique ids across 3019 total (B and C use disjoint 'B_'/'C_' prefixes by construction) |
| `no_variant_regeneration` | PASS | every B line, re-serialized identically, matches the frozen file byte-for-byte -- nothing was regenerated, only concatenated |
| `exposure_count_zero_rescanned` | PASS | 0 held-out literals across 9057 strings, RE-SCANNED here (not inherited from B/C's ledger entries) |
