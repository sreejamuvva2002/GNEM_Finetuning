# DATASET_BD_v3

Phase 16 — BD datasets and budget manifests.

## Artifacts

```text
train_BD_facts_sql_v3.jsonl          sha256 68a82340b9ea1b6e08089bd11b2689307a462e34b1bbb7df0a1120f953bc6238
train_BD_controlled_v3.jsonl         sha256 fc3ce5ae3a4b05bf1e3d5808defa7f1aaa3ecd9f8013aa1c8acbc3756da502a6
train_D_repeat_budgetmatched_v3.jsonl sha256 9be037d6d0fa6fc0557c746e6c091dad38bf2fea3c9bf57814948990c5f0d7ec
BD_SAMPLING_MANIFEST_v3.json, BD_COMPOSITION_v3.md
```

## Standalone totals (supervised completion tokens, real tokenizer)

```text
B    2011 examples     38824 tokens
D    1150 examples     41163 tokens
```

v2 reference (context only, not a v3 target): B ~89.3k supervised chars, D ~71.2k, BD ~160.4k. v3's own KB, task pool and eligibility rules are different in scale and composition, so these numbers are not expected to match, and are not treated as a target here.

## BD_controlled

```text
B    2011 examples     38824 tokens (full B, anchor arm)
D    1029 examples     38825 tokens (subsampled)
```

## D_repeat_budgetmatched

```text
 2071 examples (D cycled/repeated)     77651 tokens
```

## Optimizer steps / effective passes

Not computed. Both batch_size and epoch count are Phase 24 dev-tuned hyperparameters not yet frozen — reporting a step count now would require inventing them. See BD_SAMPLING_MANIFEST_v3.json's `optimizer_steps_and_effective_passes` note for the formula.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.1 |
| `bd_full_is_exact_union_of_b_and_d` | PASS | 3161 items = 2011 B + 1150 D, no additions or omissions |
| `bd_controlled_items_are_genuine_b_or_d` | PASS | 2011 from B + 1029 from D = 3040, no fabricated items |
| `bd_controlled_approximately_50_50` | PASS | B 38824 / D 38825 supervised completion tokens (ratio 1.000, target >= 0.95 for '~50/50') |
| `bd_controlled_uses_full_anchor_arm` | PASS | the smaller-total arm (B) is used in full (2011 items), never subsampled downward |
| `d_repeat_is_pure_d_content` | PASS | every D_repeat_budgetmatched item's source id traces to a real D item; no B content present |
| `d_repeat_matches_controlled_budget` | PASS | D_repeat_budgetmatched 77651 supervised tokens vs BD_controlled 77649 (within one item's worth of exact, since repetition proceeds in whole-item units) |
| `real_tokenizer_used` | PASS | tokenizer.json hash matches the frozen Phase 6/10 expectation - no estimator, no substitution |
