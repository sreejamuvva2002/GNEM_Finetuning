# GNEM V3 — EV and battery supply-chain fine-tuning

**Current state:** full-field training datasets rebuilt and checked; development baselines and eight two-step smoke tests completed. **Final training: 0 of 18 runs. Protected test evaluation has not run.** Q42 approval is pending at the user's direction. Broader analytical development coverage and final scoring integration also remain open.

Start with the [current implementation plan](V3_UPDATED_REVIEW_AND_PLAN.md) and [phase-by-phase status](V3_PHASE_STATUS.md). The [A-002 amendment](PROTOCOL_A002_FULL_FIELD.md) defines the full-field policy; its migration-state text records the amendment's issuance, while the phase-status file records current implementation progress.

## Data and experiment

The immutable source is [GNEM_Final_Combined_Dataset.xlsx](kb/GNEM_Final_Combined_Dataset.xlsx): 205 records, 193 exact company names and 18 columns. The [normalized records](datasets_v3/canonical_records_v3.jsonl) preserve every source field. Training uses 148 records; 17 development and 40 test records remain held out.

Include full processes, services, certifications, Employment and the other eligible source observations. Certification Count is preserved internally and excluded from model-facing training by user decision. Missing evidence and conflicting records receive qualified, record-specific supervision. Recorded employment does not establish capacity, and recorded certifications do not establish current customer qualification.

| Training variant | Examples | Required final runs |
|---|---:|---:|
| A_cpt | 148 passages | 1 |
| B_facts | 2,149 | 3 |
| C_answers | 1,311 | 3 |
| D_sql | 1,311 | 3 |
| BC | 3,460 | 1 |
| BD_controlled | 3,505 | 3 |
| D_repeat_budgetmatched | 2,718 | 3 |
| BD_full | 3,460 | 1 |

All variants start independently from the pinned Qwen2.5-14B-Instruct base revision. The four baselines are base, base_ctx_oracle, base_sql and base_sql_5shot. Their information access differs and their scores must be reported separately.

## Verified evidence

- [Factual coverage](validation_v3/resumption/FULL_FIELD_COVERAGE_A002.json): 2,220/2,220 eligible row/attribute observations mapped; full factual sources retained in mixtures.
- [Actual training-label audit](validation_v3/resumption/TRAINER_LABEL_AUDIT_A002.json): all seven chat variants checked (A_cpt has a separate LM objective); chat sequences at most 244 tokens against a 1,024-token limit.
- [Smoke training](validation_v3/resumption/SMOKE_TRAINING_RESULTS_A002.json) and [adapter reload checks](validation_v3/resumption/SMOKE_RELOAD_A002.json): eight representative two-step diagnostic runs; these do not count toward final training.
- [Development baseline results](results_v3/dev/REPORT_A002_r2.md): exact-score denominators and limitations. The 51 structured dev questions are simple entity-conditioned filters, not a comprehensive analytical benchmark.
- [Q42 review](validation_v3/Q42_REVIEW_A002.md): candidate golds and unresolved interpretations; approval remains pending.

## Repository map

| Location | Purpose |
|---|---|
| `kb/` | Immutable source workbook |
| `datasets_v3/` | Canonical data, database, training data, dev/probe inputs, active and historical registry records |
| `finetune/` | Builders, validation, trainer and development inference code |
| `validation_v3/` | Audits, logs, pending Q42 review and retained smoke adapters |
| `results_v3/dev/` | Development outputs, canonical records, telemetry and verified report |
| `results_v3/micro/` | Diagnostic pipeline checks and retained pilot outputs |
| `review_training_2026-09-11/`, `review_v2_questions/` | V2 training and question-level evidence; no V3 runtime dependency |
| `review_v3_updated_2026-09-11/` | Historical V3 repository review |
| `archive/` | Superseded plans, dataset/fixture snapshots and initial smoke pilot |
| `docs/` | Detailed historical phase/execution references |

Older root review/handoff documents are retained at their original paths because review scripts and manifests reference them. They are evidence, not the current roadmap. [Repository maintenance](docs/REPOSITORY_MAINTENANCE.md) records cleanup and retention decisions.

## Rules for continuing

User instructions and [A-002](PROTOCOL_A002_FULL_FIELD.md) override incompatible historical clauses. Unaffected scientific requirements remain in the [detailed phase reference](docs/PHASE_PROTOCOL_REFERENCE.md) and [execution reference](docs/EXECUTION_RULES_REFERENCE.md). Older code comments citing README/CLAUDE line numbers refer to these snapshots.

Use development results for decisions; keep protected test results sealed until Phase 40. Preserve every final adapter and exact run inputs. Do not infer model correctness from low loss or call smoke tests final experiments. Do not release full training while Q42 approval and the other pre-training gates remain open.

Current pre-training limitations and configured-step corrections: [gate register](validation_v3/PRE_TRAINING_GATES_A002.md). The r2 report supersedes r1 scoring; historical evidence remains preserved.
