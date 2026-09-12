# DATASET_BD_v3

Phase 16 — BD datasets and budget manifests.

## Artifacts

```text
train_BD_facts_sql_v3.jsonl          sha256 64dc25b3df873505ecfa67f7af7e90029889d5a379a145d1d115f51c43d3271a
train_BD_controlled_v3.jsonl         sha256 996c9bdc361e813607d77080322dd445e55f47da9dfe4842072abf8c270436c1
train_D_repeat_budgetmatched_v3.jsonl sha256 239419aa178e3ac9b2ba5c742678f79e9640e3be570084aed23dc389b33730ec
BD_SAMPLING_MANIFEST_v3.json, BD_COMPOSITION_v3.md
```

## Standalone totals (supervised completion tokens, real tokenizer)

```text
B    2149 examples     47202 tokens
D    1311 examples     45453 tokens
```

v2 reference (context only, not a v3 target): B ~89.3k supervised chars, D ~71.2k, BD ~160.4k. v3's own KB, task pool and eligibility rules are different in scale and composition, so these numbers are not expected to match, and are not treated as a target here.

## BD_controlled

```text
B    2149 examples     47202 tokens (all B sources retained; repetitions if needed)
D    1366 examples     47215 tokens (all D sources retained; repetitions if needed)
```

## D_repeat_budgetmatched

```text
 2732 examples (D cycled/repeated)     94440 tokens
```

## Optimizer steps / effective passes

Current single-device trainer defaults: batch size 1, accumulation 8, three epochs. Transformers 4.56.2 uses ceil(examples/8) updates per epoch: BD_full 1299, BD_controlled 1320, D_repeat 1026 total planned steps. These are configured estimates, not observed runs or approved final hyperparameters. See PRE_TRAINING_GATES_A002.md.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.2_A002 |
| `source_hashes_match_ledger` | PASS | B 87ea988d2e0a.. == ledger 87ea988d2e0a.. and D 6a199c7d15ef.. == ledger 6a199c7d15ef.. -- refusing to inherit a prior exposure verdict for drifted source |
| `exposure_count_zero_rescanned` | PASS | 0 held-out literals across 10380 strings in BD_full, RE-SCANNED here (not inherited from B/D's ledger entries) -- BD_controlled and D_repeat are subsets/repeats of this same content, so this scan covers them too |
| `bd_full_is_exact_union_of_b_and_d` | PASS | 3460 items = 2149 B + 1311 D, no additions or omissions |
| `bd_controlled_items_are_genuine_b_or_d` | PASS | 2149 from B + 1366 from D = 3515, no fabricated items |
| `bd_controlled_approximately_50_50` | PASS | B 47202 / D 47215 supervised completion tokens (ratio 1.000, target >= 0.95 for '~50/50') |
| `bd_controlled_uses_full_anchor_arm` | PASS | the larger-total arm (B) is used in full (2149 items), never subsampled downward |
| `d_repeat_is_pure_d_content` | PASS | every D_repeat_budgetmatched item's source id traces to a real D item; no B content present |
| `d_repeat_matches_controlled_budget` | PASS | D_repeat_budgetmatched 94440 supervised tokens vs BD_controlled 94417 (within one item's worth of exact, since repetition proceeds in whole-item units) |
| `real_tokenizer_used` | PASS | tokenizer.json hash matches the frozen Phase 6/10 expectation - no estimator, no substitution |
