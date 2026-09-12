# GNEM V3 execution instructions

## Authority

1. Explicit user instructions and decisions.
2. [A-002 full-field amendment](PROTOCOL_A002_FULL_FIELD.md).
3. Unaffected requirements in [the detailed phase protocol](docs/PHASE_PROTOCOL_REFERENCE.md).
4. These instructions and unaffected [historical execution requirements](docs/EXECUTION_RULES_REFERENCE.md).
5. Implementation tests, historical reviews and V2 reference code.

The user authorized implementation and continuation across phases. Historical auditor-only roles and routine phase-by-phase pauses do not override that authorization. The user explicitly kept Q42 approval pending; do not fabricate approval or release full training.

## Current status

Read [V3_PHASE_STATUS.md](V3_PHASE_STATUS.md) and [V3_UPDATED_REVIEW_AND_PLAN.md](V3_UPDATED_REVIEW_AND_PLAN.md). There are 43 numbered phases (0–42), with non-contiguous gates. Data migration, development baselines and eight representative smoke runs are checked; no final run or protected test evaluation is complete.

```text
PROTOCOL_STATUS: A002_DATA_MIGRATED_RELEASE_PENDING
CURRENT_PHASE: Q42 adjudication, analytical dev coverage and scoring integration
FINAL_TRAINING_RUNS_COMPLETED: 0 / 18
Q42_APPROVAL: PENDING_BY_USER
TEST_STATUS: LOCKED_UNTIL_PHASE_40
PHASE_STATUS_AUTHORITY: V3_PHASE_STATUS.md
```

## Data and reproducibility

Preserve the workbook, canonical records and frozen company split. Include all eligible factual observations and complete process/service/certification lists. Certification Count stays internal. Preserve missingness and conflicts with source attribution. Do not substitute employment for capacity or certificates for qualification.

Use explicit database scopes. Training may use train_kb; development gold uses train_dev_kb. No V2 runtime dependency. Keep full-field coverage and actual post-tokenization label checks; never silently truncate or drop examples. Controlled BD retains all B/D sources and repeats the smaller source to balance supervision.

Record exact source/code/model/template identities, actual losses, optimizer steps, retained examples and failures. Distinguish raw outputs, parser metrics, model knowledge and external SQL execution. Log development-driven changes in MODEL_SELECTION_LOG_v3.md. Preserve failed/pilot runs as labeled evidence.

## Validation and retention

Run checks appropriate to changes and report their limits. Historical hash manifests describe historical snapshots; do not rewrite them to imply current verification. Use a new current manifest after changes. Do not claim independent human review for agent-run tests.

Preserve selected smoke adapters and their metrics. Completed two-step smoke optimizer/scheduler/RNG resume state was removed by user-authorized cleanup; identical checkpoint files link to selected_adapter. These smoke checkpoints support inference, not optimizer-state resume. Preserve every final per-seed adapter and required final-run evidence under the unchanged final retention policy.

Both .venv-v3 (data validation) and .venv-v3-train (pinned GPU runtime) are required local environments, ignored by Git. Do not delete them during routine cleanup. Historical review inputs and approvals remain necessary evidence even when they are not active instructions.
