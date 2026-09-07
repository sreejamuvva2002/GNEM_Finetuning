# TASK_POOL_v3

Phase 12 — `STRUCTURED_TASK_POOL_v3.jsonl`, the canonical source for C (train_kb_gold) and D (gold_sql), rendered in Phases 13-14.

## Provenance

```text
artifact          datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl
sha256            4883601acb10e7cbcbe6cf3b0cfad75daf0f011feea763adc3eabc79df3566dc
generator         task_pool_v3.0
scope             candidate generation from train_kb (README:495)
holdout registry  holdout_v3.1 frozen 2026-08-24
```

## Operation family distribution

| operation_family | tasks | held out from C/D? |
|---|--:|---|
| `argmax_topk` | 9 | YES |
| `filter` | 1217 | no |
| `group_by` | 6 | YES |

**Total: 1232 tasks.**

A held-out family's tasks remain in this pool (they are the source material for the Phase 22 operation-heldout probe); eligibility for C/D training is a Phase 13/14 computation, not a pool-generation exclusion, per README's own eligibility/training-target distinction.

## Operation catalogue (documented scope decision)

filter, count, child_filter, child_count, threshold_filter, group_by_breakdown, argmax_single, topk_employment, composition_filter. Fields drawn from `holdout_v3.FIELD_SEMANTIC_OPERATIONS`, the frozen field/operation map — never a separately invented list. `product_or_service` (semantic_filter, free text), `location` (redundant with the derived `city`/`county` columns), `row_id` and `company` (no natural aggregate/filter shape) are out of scope for this catalogue. `limit_only` (LIMIT without ORDER BY) is not manufactured here — README never requires it of Phase 12, and a genuinely non-deterministic gold query would contradict this protocol's own tie-break requirements; the Phase 22 operation-heldout probe may need to construct it separately.

## Composition holdout

held-out pair [['certifications', 'processes']] — excluded from candidate generation entirely, not merely from training rendering, so it never reaches the pool at all.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.1 dated 2026-08-24 |
| `nonzero_tasks` | PASS | 1232 tasks |
| `gold_100pct_execution` | PASS | 0 execution failures across 1232 candidates |
| `unique_task_ids` | PASS | 1232 unique task_ids |
| `required_fields_complete` | PASS | all 17 README-required fields present on every task |
| `nonempty_questions` | PASS | every question is non-blank |
| `logical_fingerprint_reproducible` | PASS | every stored fingerprint reproduces byte-identically from its own task metadata |
| `operation_family_matches_real_scanner` | PASS | every stored operation_family reproduces from holdout_v3.classify_operation(gold_sql), the authoritative gate (README:279) |
| `composition_holdout_pair_never_generated` | PASS | the held-out composition [('certifications', 'processes')] never appears as a task's fields_used |
| `deterministic_tiebreak_on_ranking_tasks` | PASS | every one of 9 top_k tasks orders by metric plus at least one tie-break column (README:510-513) |
| `no_row_id_where_filter` | PASS | row_id appears only inside JOIN...ON clauses, never a WHERE filter (README:541-543) |
| `entity_dependent_flag_present` | PASS | 422/1232 tasks are entity_dependent (full_kb_gold != train_kb_gold) |
