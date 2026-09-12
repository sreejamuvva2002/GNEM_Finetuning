# V3 development baselines — not final test results

These are unchanged-base-model development runs. There are no completed final fine-tuning runs. Q42 approval remains pending.

| Condition | Family | Exact correct / total | Score |
|---|---|---:|---:|
| base | factual_recall | 0 / 255 | 0.0% |
| base | dev_structured | 13 / 51 | 25.5% |
| base_ctx_oracle | factual_recall | 214 / 255 | 83.9% |
| base_sql | dev_structured | 51 / 51 | 100.0% |
| base_sql_5shot | dev_structured | 51 / 51 | 100.0% |

The factual metric is conservative normalized exact-value/set scoring under a JSON response contract. Extra certification/process/service entries fail exact-set accuracy. Semantically equivalent prose or different descriptions of missing evidence can still be rejected; raw outputs remain available for separate adjudication. SQL conditions execute against train_dev_kb with identical full-source vocabulary catalogues. Oracle context provides the correct record by construction. These information-access conditions must not be compared as pure weight memorization.

The current 51 structured development questions are entity-conditioned filters, not a comprehensive analytical benchmark. Their scores cannot establish aggregation or supplier-risk competence. A separate real-model micro battery exercises count, ranking, grouping, composition, empty results and multipart SQL, but its six hand-constructed items are a plumbing check, not a generalization estimate.

Every input ID and gold was verified against its declared development artifact. Canonical records use the existing EvalRecord schema; additional runtime fields are retained in sidecar telemetry. No failed prediction was removed from a denominator. Earlier initial/json_contract runs are pilots and are excluded from this table.
