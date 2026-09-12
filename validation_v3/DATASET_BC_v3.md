# DATASET_BC_v3

Phase 15 — `train_BC_facts_answers_v3.jsonl`, the deterministic union of the frozen B and C files. Never a regenerated variant.

## Provenance

```text
artifact          datasets_v3/train_BC_facts_answers_v3.jsonl
sha256            0b0a34c0d11dbfcc01368003180a5fb84e171a72fc294bb26170c495b5385ace
generator         bc_v3.0
source B          datasets_v3/train_B_facts_v3.jsonl sha256 87ea988d2e0a8e68f76daa0d4ea5fb5227314003ad4c83618375c3a487d9db21
source C          datasets_v3/train_C_answers_v3.jsonl sha256 e887a8cf0c3f576c8a137ae3f4af2c93001da01e457f6c422d72497f9ce5c6e3
```

## Composition

B: 2149 items (order 1-2149) + C: 1311 items (order 2150-3460) = 3460 total, B first then C, fixed order.

## Exposure (re-scanned, not inherited)

Correction (post-approval audit): an earlier version of this generator copied forward B/C's previously recorded exposure_count/strings_scanned without verifying those source files hadn't drifted, and without scanning anything itself. This build verifies current B/C sha256 against the ledger's recorded values first, then re-scans every rendered string in the concatenated file directly.

```text
strings scanned   10380   (system prompt + question + answer, every B and C item)
exposure_count    0
```

## Validation

| check | result | detail |
|---|---|---|
| `source_hashes_match_ledger` | PASS | B 87ea988d2e0a.. == ledger 87ea988d2e0a.. and C e887a8cf0c3f.. == ledger e887a8cf0c3f.. -- refusing to inherit a prior exposure verdict for drifted source |
| `b_and_c_frozen_and_nonempty` | PASS | B: 2149 items · C: 1311 items |
| `no_example_id_collision` | PASS | 3460 unique ids across 3460 total (B and C use disjoint 'B_'/'C_' prefixes by construction) |
| `no_variant_regeneration` | PASS | every B line, re-serialized identically, matches the frozen file byte-for-byte -- nothing was regenerated, only concatenated |
| `exposure_count_zero_rescanned` | PASS | 0 held-out literals across 10380 strings, RE-SCANNED here (not inherited from B/C's ledger entries) |
