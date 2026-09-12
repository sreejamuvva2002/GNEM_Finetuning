# V3 development baselines, revision r2 — not final test results

Regrade of the **retained r1 raw predictions** under `answer_parser_A002.2`. No model inference was repeated; only the verdict computed from the preserved text changed. The r1 report and its artifacts remain unmodified at [REPORT_A002.md](REPORT_A002.md) and `*/protocol_A002/`.

There are no completed final fine-tuning runs (0 of 18). Q42 approval remains pending at the user's direction. No protected test evaluation has run.

## Two independently computed axes

`semantic` asks whether the answer carried the recorded value, after a bounded, documented output-format repair. `format` asks whether the original response obeyed the frozen JSON output contract for its answer type, judged from the response text alone and never from agreement with gold. A well-formed wrong answer scores format but not semantic; a correct answer in prose scores semantic but not format. `strict` is the conjunction: contract-compliant AND matching gold with no repair.

| Condition | Family | Semantic correct / total | Semantic | Format-compliant | Strict |
|---|---|---:|---:|---:|---:|
| base | factual_recall | 0 / 255 | 0.0% | 97.6% | 0.0% |
| base | dev_structured | 13 / 51 | 25.5% | 100.0% | 25.5% |
| base_ctx_oracle | factual_recall | 245 / 255 | 96.1% | 98.4% | 83.9% |
| base_sql | dev_structured | 51 / 51 | 100.0% | N/A (SQL) | 100.0% |
| base_sql_5shot | dev_structured | 51 / 51 | 100.0% | N/A (SQL) | 27.5% |

## What moved between r1 and r2

| Condition | r1 correct | r2 correct | Reclassified |
|---|---:|---:|---:|
| base | 13 / 306 | 13 / 306 | 0 |
| base_ctx_oracle | 214 / 255 | 245 / 255 | 31 |
| base_sql | 51 / 51 | 51 / 51 | 0 |
| base_sql_5shot | 51 / 51 | 51 / 51 | 0 |

Reclassification causes: named_object_unwrap x1, surplus_quote_strip x30.

Every reclassification is incorrect -> correct: the bounded repair is strictly widening and is regression-tested never to reject a strictly correct answer. SQL conditions are regraded through the unchanged `grade_v3` as a control and must not move; the run aborts if they do.

## Limits that r2 does not change

- The oracle-context condition is provided the correct record by construction, and the SQL conditions execute against `train_dev_kb` with identical full-source vocabulary catalogues. These information-access conditions must not be compared as pure weight memorization.
- All 51 structured development questions quote their own gold answer inside the question (*"Which recorded company is named X and has &lt;field&gt; recorded as V?"* with gold `[[X]]`). A 100% score on them is a ceiling artifact, not evidence of analytical capability, and they remain unfit for checkpoint selection. Tracked in [PRE_TRAINING_GATES_A002.md](../../validation_v3/PRE_TRAINING_GATES_A002.md).
- Boolean surface forms (`true`/`False`) against recorded `Yes`/`No` remain incorrect by decision; the contract asks for the recorded value.
- No failed prediction was removed from a denominator. Earlier `initial`/`json_contract` runs remain pilots and are excluded.

## Post-publication documentation clarification

For SQL conditions, Strict is grade_v3's independent column-schema match (including aliases), not the natural-language JSON-contract conjunction described above. Both SQL conditions answer 51/51 correctly; base_sql_5shot matches the expected schema in 14/51 cases (27.5%), versus 51/51 for base_sql. The other 37 five-shot cases are schema mismatches, not incorrect answer sets. Do not interpret this strict-score difference as an answer-capability gap.

This explanatory addendum does not change scores, raw outputs or the original regrader code identity. A rerun of the historical generator reproduces the report before this addendum; documentation-correction hashes are recorded separately in validation_v3/resumption/DOCUMENTATION_CORRECTIONS_POST_PUSH.json.
