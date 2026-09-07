# DATASET_BC_v3

Phase 15 — `train_BC_facts_answers_v3.jsonl`, the deterministic union of the frozen B and C files. Never a regenerated variant.

## Provenance

```text
artifact          datasets_v3/train_BC_facts_answers_v3.jsonl
sha256            7fe6ea83569ed9d23d75a933539027dc636cefd6219fe40ce89f28798f6ccf1c
generator         bc_v3.0
source B          datasets_v3/train_B_facts_v3.jsonl sha256 17ddccd67f2c46bb94e5d948c130cd2d6c99b564a07fc171618eb0f5e3f957b0
source C          datasets_v3/train_C_answers_v3.jsonl sha256 fa5fdfe7ad96a6d04e146861a5b8c64bdfe7d43cf716de56d1b3f52e606d820a
```

## Composition

B: 2011 items (order 1-2011) + C: 1150 items (order 2012-3161) = 3161 total, B first then C, fixed order.

No new exposure scan runs here: every string in this file was already scanned and frozen against the holdout registry at Phase 11 (B) and Phase 13 (C); concatenation creates no new model-visible content.

## Validation

| check | result | detail |
|---|---|---|
| `b_and_c_frozen_and_nonempty` | PASS | B: 2011 items · C: 1150 items |
| `no_example_id_collision` | PASS | 3161 unique ids across 3161 total (B and C use disjoint 'B_'/'C_' prefixes by construction) |
| `no_variant_regeneration` | PASS | every B line, re-serialized identically, matches the frozen file byte-for-byte -- nothing was regenerated, only concatenated |
