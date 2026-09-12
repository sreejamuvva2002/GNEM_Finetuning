# Corrected development-set baselines — r3

These are fresh unchanged-base runs. Structured questions use dev_structured_r2_v3.jsonl (120 items); factual questions retain the 255-item input. Old r1/r2 outputs are preserved. Scores across different benchmarks are not evidence of model improvement.

Oracle context covers factual questions only and supplies the correct source record. SQL conditions execute against train_dev_kb. These conditions do not measure pure weight memorization. SQL strictness measures column-schema equality; natural-language strictness requires correct content without repair in the JSON contract. Format is not applicable to SQL.

| Condition | Slice | Correct / total | Semantic | Format | Strict |
|---|---|---:|---:|---:|---:|
| base | family:factual_recall | 0/255 | 0.0% | 97.6% | 0.0% |
| base | family:dev_structured_r2 | 0/120 | 0.0% | 100.0% | 0.0% |
| base | arity:0 | 0/23 | 0.0% | 100.0% | 0.0% |
| base | answer_type:set | 0/96 | 0.0% | 100.0% | 0.0% |
| base | set_size:1 | 0/36 | 0.0% | 100.0% | 0.0% |
| base | answer_type:scalar | 0/24 | 0.0% | 100.0% | 0.0% |
| base | arity:1 | 0/73 | 0.0% | 100.0% | 0.0% |
| base | set_size:11+ | 0/33 | 0.0% | 100.0% | 0.0% |
| base | set_size:2-10 | 0/27 | 0.0% | 100.0% | 0.0% |
| base | arity:2 | 0/24 | 0.0% | 100.0% | 0.0% |
| base_ctx_oracle | family:factual_recall | 245/255 | 96.1% | 98.4% | 83.9% |
| base_sql | family:dev_structured_r2 | 120/120 | 100.0% | N/A | 80.0% |
| base_sql | arity:0 | 23/23 | 100.0% | N/A | 52.2% |
| base_sql | answer_type:set | 96/96 | 100.0% | N/A | 100.0% |
| base_sql | set_size:1 | 36/36 | 100.0% | N/A | 100.0% |
| base_sql | answer_type:scalar | 24/24 | 100.0% | N/A | 0.0% |
| base_sql | arity:1 | 73/73 | 100.0% | N/A | 82.2% |
| base_sql | set_size:11+ | 33/33 | 100.0% | N/A | 100.0% |
| base_sql | set_size:2-10 | 27/27 | 100.0% | N/A | 100.0% |
| base_sql | arity:2 | 24/24 | 100.0% | N/A | 100.0% |
| base_sql_5shot | family:dev_structured_r2 | 120/120 | 100.0% | N/A | 100.0% |
| base_sql_5shot | arity:0 | 23/23 | 100.0% | N/A | 100.0% |
| base_sql_5shot | answer_type:set | 96/96 | 100.0% | N/A | 100.0% |
| base_sql_5shot | set_size:1 | 36/36 | 100.0% | N/A | 100.0% |
| base_sql_5shot | answer_type:scalar | 24/24 | 100.0% | N/A | 100.0% |
| base_sql_5shot | arity:1 | 73/73 | 100.0% | N/A | 100.0% |
| base_sql_5shot | set_size:11+ | 33/33 | 100.0% | N/A | 100.0% |
| base_sql_5shot | set_size:2-10 | 27/27 | 100.0% | N/A | 100.0% |
| base_sql_5shot | arity:2 | 24/24 | 100.0% | N/A | 100.0% |

All expected IDs and golds checked, all failures retained in denominators. Machine report includes per-slice statuses. This is still a small dataset with repeated source companies and related templates; slices are descriptive, not independent trials. It does not evaluate supplier qualification, capacity, import vulnerability or broad reasoning. Final training and protected evaluation have not run; Q42 approval remains pending.
