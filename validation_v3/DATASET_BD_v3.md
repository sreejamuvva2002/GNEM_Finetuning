# DATASET_BD_v3

Phase 16 — BD datasets and budget manifests.

## Artifacts

```text
train_BD_facts_sql_v3.jsonl          sha256 64dc25b3df873505ecfa67f7af7e90029889d5a379a145d1d115f51c43d3271a
train_BD_controlled_v3.jsonl         sha256 df95dd003c9d9f17df78f75e7facd7aee2095c1aa7f20919e94f821704e2b033
train_D_repeat_budgetmatched_v3.jsonl sha256 6d7bc704fb26c9496289e172a9d4bad0764e93e1fdf8728bff56dd9a5453f93b
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
D    1356 examples     47205 tokens (all D sources retained; repetitions if needed)
```

## D_repeat_budgetmatched

```text
 2718 examples (D cycled/repeated)     94432 tokens
```

## Optimizer steps / effective passes

Current single-device trainer defaults: batch size 1, accumulation 8, three epochs. Transformers 4.56.2 uses ceil(examples/8) updates per epoch: BD_full 1,299, BD_controlled 1,317, D_repeat 1,020 total planned steps. These are configured estimates, not observed runs or approved final hyperparameters. See PRE_TRAINING_GATES_A002.md.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.2_A002 |
| `source_hashes_match_ledger` | PASS | B 87ea988d2e0a.. == ledger 87ea988d2e0a.. and D 6a199c7d15ef.. == ledger 6a199c7d15ef.. -- refusing to inherit a prior exposure verdict for drifted source |
| `exposure_count_zero_rescanned` | PASS | 0 held-out literals across 10380 strings in BD_full, RE-SCANNED here (not inherited from B/D's ledger entries) -- BD_controlled and D_repeat are subsets/repeats of this same content, so this scan covers them too |
| `bd_full_is_exact_union_of_b_and_d` | PASS | 3460 items = 2149 B + 1311 D, no additions or omissions |
| `bd_controlled_items_are_genuine_b_or_d` | PASS | 2149 from B + 1356 from D = 3505, no fabricated items |
| `bd_controlled_approximately_50_50` | PASS | B 47202 / D 47205 supervised completion tokens (ratio 1.000, target >= 0.95 for '~50/50') |
| `bd_controlled_uses_full_anchor_arm` | PASS | the larger-total arm (B) is used in full (2149 items), never subsampled downward |
| `d_repeat_is_pure_d_content` | PASS | every D_repeat_budgetmatched item's source id traces to a real D item; no B content present |
| `d_repeat_matches_controlled_budget` | PASS | D_repeat_budgetmatched 94432 supervised tokens vs BD_controlled 94407 (within one item's worth of exact, since repetition proceeds in whole-item units) |
| `real_tokenizer_used` | PASS | tokenizer.json hash matches the frozen Phase 6/10 expectation - no estimator, no substitution |
