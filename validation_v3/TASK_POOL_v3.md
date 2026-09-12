# TASK_POOL_v3

Phase 12 — `STRUCTURED_TASK_POOL_v3.jsonl`, the canonical source for C (train_kb_gold) and D (gold_sql), rendered in Phases 13-14.

## Provenance

```text
artifact          datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl
sha256            fb158d92eb56060020b2e33fd6ddf9338c94f8c8ea61926ce0dfdc6a7cc988a7
generator         task_pool_v3.0
scope             candidate generation from train_kb (README:495)
holdout registry  holdout_v3.2_A002 frozen 2026-09-11
```

## Operation family distribution

| operation_family | tasks | held out from C/D? |
|---|--:|---|
| `argmax_topk` | 9 | YES |
| `filter` | 1311 | no |
| `group_by` | 6 | YES |

**Total: 1326 tasks.**

A held-out family's tasks remain in this pool (they are the source material for the Phase 22 operation-heldout probe); eligibility for C/D training is a Phase 13/14 computation, not a pool-generation exclusion, per README's own eligibility/training-target distinction.

## Operation catalogue (documented scope decision)

filter, count, child_filter, child_count, threshold_filter, group_by_breakdown, argmax_single, topk_employment, composition_filter. Fields drawn from `holdout_v3.FIELD_SEMANTIC_OPERATIONS`, the frozen field/operation map — never a separately invented list. `product_or_service` (semantic_filter, free text), `location` (redundant with the derived `city`/`county` columns), `row_id` and `company` (no natural aggregate/filter shape) are out of scope for this catalogue. `limit_only` (LIMIT without ORDER BY) is not manufactured here — README never requires it of Phase 12, and a genuinely non-deterministic gold query would contradict this protocol's own tie-break requirements; the Phase 22 operation-heldout probe may need to construct it separately.

## Composition holdout

held-out pair [['certifications', 'processes']] — excluded from candidate generation entirely, not merely from training rendering, so it never reaches the pool at all.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.2_A002 dated 2026-09-11 |
| `nonzero_tasks` | PASS | 1326 tasks |
| `gold_100pct_execution` | PASS | 0 execution failures across 1326 candidates |
| `unique_task_ids` | PASS | 1326 unique task_ids |
| `required_fields_complete` | PASS | all 17 README-required fields present on every task |
| `nonempty_questions` | PASS | every question is non-blank |
| `logical_fingerprint_reproducible` | PASS | every stored fingerprint reproduces byte-identically from its own task metadata |
| `operation_family_matches_real_scanner` | PASS | every stored operation_family reproduces from holdout_v3.classify_operation(gold_sql), the authoritative gate (README:279) |
| `composition_holdout_pair_never_generated` | PASS | the held-out composition [('certifications', 'processes')] never appears as a task's fields_used |
| `deterministic_tiebreak_on_ranking_tasks` | PASS | every one of 9 top_k tasks orders by metric plus at least one tie-break column (README:510-513) |
| `no_row_id_where_filter` | PASS | row_id appears only inside JOIN...ON clauses, never a WHERE filter (README:541-543) |
| `entity_dependent_flag_present` | PASS | 447/1326 tasks are entity_dependent (full_kb_gold != train_kb_gold) |
| `no_empty_set_answer_tasks` | PASS | every set-answer task has >=1 train_kb_gold row (0 empty candidates excluded before reaching the pool) |
| `count_uses_distinct_company_not_count_star` | PASS | every count/child_count task's gold_sql uses COUNT(DISTINCT company), never COUNT(*) (a multi-row company must count once, not once per row) |
| `no_aggregation_on_filter_only_fields` | PASS | no count task targets a field outside AGGREGATABLE_FIELDS (address, primary_oems carry only 'filter' in FIELD_SEMANTIC_OPERATIONS -- README:537-538) |
| `no_sentinel_as_group_by_category` | PASS | no group_by_breakdown task's gold rows contain a frozen sentinel as a category value |
| `result_size_within_caps_by_join_arity` | PASS | every set-answer task's row count is within its arity-appropriate cap (arity 0: <= 40, arity >= 1: <= 25) |
