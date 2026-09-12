# DATASET_C_ANSWERS_v3

Phase 13 — `train_C_answers_v3.jsonl`, structured tasks rendered as direct closed-book answers (train_kb_gold).

## Provenance

```text
artifact          datasets_v3/train_C_answers_v3.jsonl
sha256            e887a8cf0c3f576c8a137ae3f4af2c93001da01e457f6c422d72497f9ce5c6e3
generator         c_answers_v3.0
source pool       datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl (1326 tasks)
holdout registry  holdout_v3.2_A002 frozen 2026-09-11
```

## Eligibility

**1311** of **1326** pool tasks are C-eligible.

| excluded reason | count |
|---|--:|
| `held_out_actual_sql_operation` | 15 |

`held_out_operation:*`: README Phase 22 requires argmax_topk and group_by at zero training occurrences; these tasks remain in the pool as Phase 22's own probe source material. `held_out_value:*`: the task's values_used touches a value-held-out literal — omit the item, never truncate the truth.

## Exposure

```text
strings scanned   2623   (system prompt + every question + every answer)
exposure_count    0
```

## Validation

| check | result | detail |
|---|---|---|
| `nonzero_items` | PASS | 1311 C items |
| `every_item_traces_to_pool_task_id` | PASS | every C item's task_id is present in STRUCTURED_TASK_POOL_v3.jsonl |
| `unique_example_ids` | PASS | 1311 unique ids |
| `every_target_equals_train_kb_gold` | PASS | every item's gold_value is byte-identical to its pool task's train_kb_gold |
| `zero_entity_dependent_items_carrying_full_kb_answer` | PASS | no entity_dependent item's target coincides with full_kb_gold (train_kb_gold and full_kb_gold differ by definition for these, so equality here would itself indicate a wiring bug) |
| `no_held_out_operation_family_eligible` | PASS | no eligible item carries a held-out operation_family (argmax_topk/group_by/limit_only) |
| `no_held_out_value_eligible` | PASS | no eligible item's values_used intersects a held-out value |
| `only_set_or_scalar_answer_types` | PASS | every eligible item is answer_type set or scalar (the only types reachable once argmax_topk/group_by are excluded) |
| `no_sql_text_in_items` | PASS | no C item carries a gold_sql field |
| `no_dev_or_test_gold_fields_present` | PASS | no C item carries full_kb_gold or train_dev_kb_gold (README:508) |
| `zero_heldout_or_dev_companies_present` | PASS | 0 of 52 dev/test companies appear in rendered C text (train_kb_gold structurally cannot name one) |
| `exposure_count_zero` | PASS | 0 held-out literals across 2623 rendered strings |
