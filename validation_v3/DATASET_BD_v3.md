# DATASET_BD_v3

Phase 16 — BD datasets and budget manifests.

## Artifacts

```text
train_BD_facts_sql_v3.jsonl          sha256 93d0b1ca574f04132c5971e511b4b48487f8d4e1de7c947f02041c7d682abcdb
train_BD_controlled_v3.jsonl         sha256 163cee459544aea762c1b36b5c8f26740ac60e6be5f6ba744c9329a69605e841
train_D_repeat_budgetmatched_v3.jsonl sha256 0e3e7c2d393e83997676951b2eaf9e63cb1bd1fd240315f013a823056d662cc5
BD_SAMPLING_MANIFEST_v3.json, BD_COMPOSITION_v3.md
```

## Standalone totals (supervised completion tokens, real tokenizer)

```text
B    2011 examples     38824 tokens
D    1008 examples     33982 tokens
```

v2 reference (context only, not a v3 target): B ~89.3k supervised chars, D ~71.2k, BD ~160.4k. v3's own KB, task pool and eligibility rules are different in scale and composition, so these numbers are not expected to match, and are not treated as a target here.

## BD_controlled

```text
B    1779 examples     33983 tokens (full B, anchor arm)
D    1008 examples     33982 tokens (subsampled)
```

## D_repeat_budgetmatched

```text
 2017 examples (D cycled/repeated)     68001 tokens
```

## Optimizer steps / effective passes

Not computed. Both batch_size and epoch count are dev-tuned hyperparameters (CLAUDE.md 'Dev policy'; fixed during README's 'Phases 33-39 — Full training') not yet frozen — reporting a step count now would require inventing them. See BD_SAMPLING_MANIFEST_v3.json's `optimizer_steps_and_effective_passes` note for the formula.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.1 |
| `source_hashes_match_ledger` | PASS | B 17ddccd67f2c.. == ledger 17ddccd67f2c.. and D 9244bd4a884b.. == ledger 9244bd4a884b.. -- refusing to inherit a prior exposure verdict for drifted source |
| `exposure_count_zero_rescanned` | PASS | 0 held-out literals across 9057 strings in BD_full, RE-SCANNED here (not inherited from B/D's ledger entries) -- BD_controlled and D_repeat are subsets/repeats of this same content, so this scan covers them too |
| `bd_full_is_exact_union_of_b_and_d` | PASS | 3019 items = 2011 B + 1008 D, no additions or omissions |
| `bd_controlled_items_are_genuine_b_or_d` | PASS | 1779 from B + 1008 from D = 2787, no fabricated items |
| `bd_controlled_approximately_50_50` | PASS | B 33983 / D 33982 supervised completion tokens (ratio 1.000, target >= 0.95 for '~50/50') |
| `bd_controlled_uses_full_anchor_arm` | PASS | the smaller-total arm (D) is used in full (1008 items), never subsampled downward |
| `d_repeat_is_pure_d_content` | PASS | every D_repeat_budgetmatched item's source id traces to a real D item; no B content present |
| `d_repeat_matches_controlled_budget` | PASS | D_repeat_budgetmatched 68001 supervised tokens vs BD_controlled 67965 (within one item's worth of exact, since repetition proceeds in whole-item units) |
| `real_tokenizer_used` | PASS | tokenizer.json hash matches the frozen Phase 6/10 expectation - no estimator, no substitution |
