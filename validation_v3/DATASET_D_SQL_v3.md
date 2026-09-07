# DATASET_D_SQL_v3

Phase 14 — `train_D_sql_v3.jsonl`, the same eligible tasks as C rendered as SQL targets.

## Provenance

```text
artifact          datasets_v3/train_D_sql_v3.jsonl
sha256            9244bd4a884bff9cab2de087b5c8ed0843ec094947f8b309ab742eceefd1abcd
generator         d_sql_v3.0
source pool       datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl (1090 tasks)
holdout registry  holdout_v3.1 frozen 2026-08-24
```

## Eligibility (identical to C by construction)

**1008** of **1090** pool tasks eligible.

| excluded reason | count |
|---|--:|
| `held_out_operation:argmax_topk` | 9 |
| `held_out_operation:group_by` | 6 |
| `held_out_value:certifications` | 15 |
| `held_out_value:processes` | 25 |
| `held_out_value:services` | 27 |

## Join-arity distribution

| join_arity | items |
|---|--:|
| 0 | 515 |
| 1 | 180 |
| 2 | 313 |

## Operation-family distribution (D-eligible only)

| operation_family | items |
|---|--:|
| `filter` | 1008 |

## Exposure

```text
strings scanned   2017   (system prompt + every question + every gold_sql)
exposure_count    0
```

## Validation

| check | result | detail |
|---|---|---|
| `nonzero_items` | PASS | 1008 D items |
| `every_item_traces_to_pool_task_id` | PASS | every D item's task_id is present in STRUCTURED_TASK_POOL_v3.jsonl |
| `unique_example_ids` | PASS | 1008 unique ids |
| `gold_100pct_execution` | PASS | 0 execution failures across 1008 items |
| `identical_task_id_set_as_C` | PASS | 1008 task_ids, identical to train_C_answers_v3.jsonl |
| `byte_equal_question_and_metadata_vs_C` | PASS | question text and core metadata are byte-identical to C's matching item for every shared task_id |
| `no_semicolon_string_membership` | PASS | no gold_sql compares a child field against a semicolon-joined string literal (child tables are queried via JOIN) |
| `join_counts_recorded` | PASS | arity 0: 515 · arity 1: 180 · arity 2: 313 |
| `only_eligible_operation_families` | PASS | operation families present: {'filter': 1008}, none held out |
| `no_row_id_where_filter` | PASS | row_id appears only inside JOIN...ON clauses, never a WHERE filter (README:541-543) |
| `answer_sizes_within_caps` | PASS | every item's train_kb_gold row count is within the README Phase 14 caps (list/filter 1-40, cross-table 1-25) and satisfies the implicit minimum of 1 for a list-shaped answer |
