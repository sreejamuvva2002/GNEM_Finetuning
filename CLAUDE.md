# CLAUDE.md — GNEM v3 Experimental Execution Rules

## 1. Repository purpose

This repository is the clean implementation of the **GNEM v3 experiment**.

The repository intentionally starts small. At initialization it may contain only:

```text
README.md
CLAUDE.md
```

`README.md` contains the frozen GNEM v3 experimental protocol (Phases 0–42).

This `CLAUDE.md` defines how Claude must execute that protocol.

The previous GNEM/v2 repository is historical reference only. Reusable logic may be inspected and selectively ported when a phase requires it, but v3 must not become dependent on the v2 runtime tree.

---

## 2. Order of authority

When instructions conflict, follow this order:

1. Explicit user instruction in the current conversation
2. `README.md` — frozen GNEM v3 experimental protocol
3. This `CLAUDE.md`
4. v3 tests and validation contracts
5. Historical v2 code, notes, or behavior

If the implementation conflicts with `README.md`, **stop and report the conflict**.

Do not silently modify the experimental protocol to make implementation easier.

---

## 3. Experiment status

Maintain this block as work progresses:

```text
PROTOCOL_STATUS: FROZEN
CURRENT_PHASE: 16
LAST_COMPLETED_PHASE: 15
NEXT_PHASE: Phase 17 — Dev evaluation sets
TEST_STATUS: LOCKED_UNTIL_PHASE_40
```

Update it only after the current phase passes its gate and the user approves proceeding.

---

## 4. One phase at a time

Execute **exactly one phase at a time**.

For every phase:

1. Read the corresponding phase in `README.md`.
2. State which files/modules will be created or changed.
3. Implement only what the phase requires.
4. Run all required validations/assertions.
5. Produce the artifacts named by the protocol.
6. Report:
   - files changed,
   - artifacts created,
   - validation results,
   - deviations or unresolved issues,
   - gate status.
7. **STOP and wait for user review.**

Do not automatically continue into the next phase.

A failed gate is a stop condition.

Do not compensate for a failed phase later.

---

## 5. Do not redesign during execution

The protocol is now an experimental contract, not a brainstorming plan.

Do not add, remove, or alter without explicit user approval:

- training arms,
- seed policy,
- holdout definitions,
- train/dev/test split policy,
- evaluation families,
- grading rules,
- primary-comparison hierarchy,
- KB scope policy,
- test-access policy,
- budget-matching logic,
- model family,
- training objective.

If a phase reveals a genuine contradiction that makes the protocol impossible to execute, stop and explain it before changing anything.

---

# Historical v2 access

## 6. Frozen v2 Git reference

The previous implementation should be exposed to this repository as a frozen Git reference named:

```text
v2-frozen-reference
```

The intended setup is performed once from the new v3 repository:

```bash
git remote add v2-reference /PATH/TO/OLD/GNEM_REPOSITORY
git fetch v2-reference finetune-updated-data-no-geo
git tag v2-frozen-reference v2-reference/finetune-updated-data-no-geo
git remote remove v2-reference
```

Before using the reference, verify it exists:

```bash
git rev-parse v2-frozen-reference
```

Record the exact commit SHA used as the v2 reference in the v3 repository documentation or Phase 0 record.

If `v2-frozen-reference` does not exist, stop and ask the user for the old repository path. Do not guess a path.

---

## 7. v2 is read-only historical material

Never:

- merge the entire v2 branch into v3,
- rebase v3 onto v2,
- checkout the v2 branch as the working branch,
- cherry-pick broad historical commits without review,
- execute v3 against v2 datasets/results/databases by convenience,
- introduce a runtime dependency on the old repository path.

Inspect historical files with:

```bash
git show v2-frozen-reference:<path>
```

Examples:

```bash
git show v2-frozen-reference:finetune/grade.py
git show v2-frozen-reference:finetune/sqlexec.py
git show v2-frozen-reference:finetune/kb.py
git show v2-frozen-reference:finetune/train_lora.py
git show v2-frozen-reference:finetune/taxonomy.py
git show v2-frozen-reference:ISSUES.md
git show v2-frozen-reference:FINDINGS.md
```

Historical Git history may also be inspected:

```bash
git log v2-frozen-reference -- finetune/grade.py
```

The v2 reference is **evidence and implementation history**, not an executable dependency.

---

## 8. Selective porting rule

Port only behavior that is useful to the current v3 phase.

For every port:

1. Inspect the historical implementation.
2. Identify the exact behavior worth preserving.
3. Check that behavior against `README.md`.
4. Port only the required logic.
5. Preserve or create regression tests for solved bugs.
6. Remove v2 assumptions that violate v3.
7. Record important provenance in comments, commit messages, or a repository provenance note.

Do not copy whole modules merely because they already exist.

### Important historical modules

#### `grade.py`

Preserve useful grading fixes, especially:

- result arity handling,
- scalar/set/top-k distinctions,
- degenerate-output handling where applicable.

But rebuild validation around the v3 grading contract.

#### `norm_company`

Do **not** reuse aggressive company suffix normalization for answer identity or split construction.

v3 uses:

```text
row_id
company
split_group
```

as separate concepts.

Answer identity uses exact trimmed `company`.

Split-group normalization is a separate leakage-control mechanism.

#### `taxonomy.py`

Use historical taxonomy only as reference.

The v3 taxonomy must be revalidated during the Q42 phase.

#### `sqlexec.py`

Useful execution/error-handling logic may be ported, but v3 must:

- remove geo registration,
- remove hard-coded old DB paths,
- remove old row caps,
- require explicit KB scope,
- refuse unscoped SQL execution,
- never silently truncate.

#### `train_lora.py`

May be ported selectively, but audit:

- pinned base revision,
- LoRA configuration,
- bf16 behavior,
- assistant-only loss,
- full-sequence CPT loss,
- seeds,
- output paths,
- adapter retention,
- no sequential adapter chaining.

#### Evaluation/report code

Port only code actually needed by v3.

Do not recreate retired geo/graph/router functionality just because historical reporting code references it.

---

# Repository construction

## 9. Build the new repository incrementally

Do not create the entire project structure up front unless the current phase needs it.

The repository may begin as:

```text
README.md
CLAUDE.md
```

Then create directories and files only as phases require them.

Likely v3 roots include:

```text
kb/
finetune/
tests/
prompts/
datasets_v3/
adapters_v3/
results_v3/
validation_v3/
```

Do not write v3 artifacts into old v2 paths.

---

## 10. Source workbook

The source workbook required by the frozen protocol is:

```text
kb/GNEM_Final_Combined_Dataset.xlsx
sheet: GNEM Combined
```

Expected source-level checks:

```text
205 rows
18 columns
193 exact company names
```

If the workbook is not present when Phase 1 starts, obtain/copy the exact frozen workbook before proceeding.

Do not substitute another workbook with a similar name.

Treat the frozen workbook/database as **closed-world experimental truth**, not universal real-world truth.

---

# Core v3 contracts

## 11. Identity contract

Keep these identities separate:

```text
row_id       = Record No.
company      = exact trimmed company name
split_group  = leakage-control identity
```

Rules:

- answer/scoring identity uses exact trimmed `company`,
- do not strip `Inc.`, `LLC`, `Corp.`, etc. for answer counting,
- `split_group` is separate,
- grading normalization must not define split identity,
- OEM-reference leakage guard must be derived and audited,
- conflicting multi-row `(company, attribute)` facts are skipped for company-level factual QA rather than artificially disambiguated.

---

## 12. Three mandatory KB scopes

There are exactly three named KB scopes:

```text
train_kb
train_dev_kb
full_kb
```

Use them as follows:

```text
TRAIN
A passages                    -> train_kb
B factual QA                  -> train_kb
C supervision                 -> train_kb_gold
D task generation/eligibility -> train_kb

DEV
dev factual/structured gold   -> train_dev_kb
dev SQL execution             -> train_dev_kb

TEST
test gold                     -> full_kb
test SQL execution            -> full_kb
```

There must be **no unscoped KB accessor**.

Every call site must name a scope explicitly.

Training-task generation and eligibility must be determined from `train_kb` before any `train_dev_kb` or `full_kb` result is consulted.

No training file may contain `train_dev_kb_gold` or `full_kb_gold`.

---

## 13. SQL scope contract

`run_sql(...)` must require an explicit scope:

```text
train_kb
train_dev_kb
full_kb
```

and refuse to execute without one.

Prediction and gold must always execute in the same scope:

```text
training gold          -> train_kb
dev prediction + gold  -> train_dev_kb
test prediction + gold -> full_kb
```

The generated SQL itself should remain scope-neutral.

The model should learn SQL against the logical v3 schema, not special names such as `train_kb` or `full_kb`.

The executor chooses which scoped data are visible.

---

## 14. SQLite contract

Active structured schema contains four logical tables:

```text
companies
certifications
processes
services
```

Rules:

- process/service/certification membership uses child-table joins,
- never query semicolon-joined multi-values as scalar membership,
- no latitude/longitude,
- no graph tables,
- no model-facing `Certification Count`.

The v3 database must expose scoped read-only access for:

```text
train_kb
train_dev_kb
full_kb
```

These may be implemented as views or equivalent explicit scoped connections.

Never introduce fallback to old `gnem.sqlite`.

---

## 15. Sentinel semantics

Use the frozen meanings:

```text
Not specified
    source value unknown/unprovided

None identified after search
    no credential evidence identified in the frozen dataset/research

Not applicable
    field structurally does not apply

SQL NULL for derived city/county
    no usable derived SQL value
```

None proves a real-world negative.

Sentinels must not become ordinary:

- factual targets,
- query entities,
- candidate values,
- filter values,
- group-by values.

Blank certification evidence yields zero certification child rows.

---

# Holdouts and datasets

## 16. Holdout/exposure contract

Required artifacts include:

```text
HOLDOUT_REGISTRY_v3.json
FACT_EXPOSURE_LEDGER_v3.json
VALUE_HOLDOUT_COST_v3.csv
```

A value declared unseen during fine-tuning must have **zero relevant model-visible training exposure**.

If a held-out value occurs inside a multi-valued fact:

- A: omit the whole field from that row passage,
- B: omit the whole `(company, attribute)` QA,
- C/D: omit structured supervision using that value.

Never truncate a true multi-valued answer merely to hide a held-out value.

Enforce:

```text
exposure_count == 0
```

for each held-out value across all relevant training arms.

The exposure scan must include all model-visible training text, including rendered messages/system prompts/value catalogues if present.

At training time, do not expose held-out literals through a supposedly harmless catalogue.

The full runtime value catalogue may be available at inference where the protocol allows it.

Also enforce:

- minimum support,
- per-value collateral-loss limits,
- cumulative attribute-level coverage floors,
- per-split support reporting,
- operation-heldout construct exclusion,
- compositional superset exclusion,
- cross-probe consistency.

---

## 17. Training arms

Expected v3 conditions:

```text
A_cpt
B_facts
C_answers
D_sql
BC
BD_controlled
D_repeat_budgetmatched
BD_full
```

Rules:

- every adapter starts from the same pinned base revision,
- no sequential chaining,
- plain LoRA,
- bf16 unless the protocol is amended,
- chat SFT uses assistant-only supervised loss,
- A CPT uses one canonical passage per row and full-sequence LM loss,
- report A in LM tokens, not on the B/C/D completion-token axis,
- C and D derive from one canonical structured task pool,
- C target = `train_kb_gold`,
- D target = `gold_sql`,
- `D_repeat_budgetmatched` repeats D to match the controlled supervised-completion-token budget,
- `BD_full` means the full **eligible** B+D recipe after split/holdout/exposure exclusions.

Do not make causal claims stronger than the comparison supports.

---

## 18. Canonical C/D task pool

`STRUCTURED_TASK_POOL_v3.jsonl` is the canonical source for C and D.

Each task must include at least:

```text
task_id
question
operation_family
fields_used
values_used
logical_components
logical_fingerprint
join_arity
required_constructs
gold_sql
answer_type
target_columns
entity_dependent
split
train_kb_gold
train_dev_kb_gold
full_kb_gold
```

Requirements:

- candidate generation and eligibility come from `train_kb`,
- C and D use identical `task_id` sets,
- question text is byte-identical,
- logical task and metadata are identical,
- only supervision target differs,
- C target = `train_kb_gold`,
- D target = `gold_sql`,
- ranking/top-k/argmax SQL uses deterministic total tie-breaks,
- gold SQL does not filter by `row_id` unless the question explicitly refers to a record,
- `train_dev_kb_gold` and `full_kb_gold` never become training targets.

---

# Evaluation

## 19. Evaluation families

The v3 protocol includes:

```text
factual recall
factual paraphrase
structured held-in diagnostic
value-heldout
operation-heldout
compositional-heldout
structured paraphrase
no-match / abstention
Q42 business benchmark
```

The 30-item general-capability sanity suite is separate and **not a GNEM research endpoint**.

---

## 20. No-match scoring

Report separately:

```text
hallucination avoidance
valid abstention
```

Empty output, parser failure, noise, malformed output, and irrelevant refusal do not count as valid abstention.

For SQL systems, valid abstention requires executable SQL returning zero rows.

Broken SQL does not count.

---

## 21. Knowledge exposure

`knowledge_exposure` is multi-label.

Valid rules:

- `no_match` is mutually exclusive with all other labels,
- `heldout_entity` and `heldout_value` may co-occur,
- `trained_fact` may not co-occur with either holdout label.

Report overlap counts.

Where exposure semantics differ by training condition, preserve condition-specific exposure internally rather than pretending all models saw the same training evidence.

---

## 22. Entity dependence

Compute:

```text
entity_dependent = (full_kb_gold != train_kb_gold)
```

Use it for stratified interpretation.

Do not replace primary full-KB test truth with a held-in-only truth.

---

# Test discipline

## 23. Absolute test blinding

Before Phase 40:

```text
NO TEST INFERENCE
NO Q42 INFERENCE
NO TEST SCORING
NO TEST ERROR ANALYSIS
NO TEST EXAMPLE LOGGING
```

Phases 31–39 are dev-only.

Before Phase 40, test/Q42 materials may be touched only where the frozen protocol explicitly allows benchmark construction/validation, and logs must remain limited to allowed hashes/counts rather than predictions or scores.

The evaluation entry point must require an explicit Phase-40-only `--unseal` control or equivalent.

At Phase 40:

- run all frozen baselines and trained conditions,
- use `full_kb`,
- score against `full_kb_gold`,
- retain raw predictions,
- do not silently regenerate after inspecting results.

---

## 24. Dev policy

Dev is the only place for configuration decisions.

Use dev for:

- checkpoint selection,
- learning rate,
- epochs,
- LoRA rank,
- prompt debugging,
- convergence checks.

Record every dev-driven decision in:

```text
MODEL_SELECTION_LOG_v3.md
```

Never use test/Q42 outcomes to tune anything.

---

# Grading and baselines

## 25. Grading contract

Every structured item must carry generator-authored:

```text
answer_type
target_columns
```

Do not infer them after prediction generation.

Primary structured metric:

```text
task_result_correctness
```

Secondary:

```text
strict_result_schema_accuracy
```

Rules:

- set answers: project required columns, dedupe, compare sets,
- scalar: require exactly one scalar-compatible result,
- top-k/ranked: preserve order and length,
- multipart: require every requested part,
- no silent SQL row truncation,
- no silent prompt truncation,
- generation ending at `max_new_tokens` -> `truncated_output`,
- never parse partial output as a normal prediction.

Every expected evaluation item must end in exactly one status:

```text
correct
incorrect
generation_failure
parse_failure
SQL_error
timeout
truncated_output
invalid_output
```

Hard assertion:

```text
scored + failed == expected_probe_size
```

---

## 26. Baselines

Required baselines:

```text
base
base_ctx_oracle
base_sql
base_sql_5shot
```

All baseline decoding is greedy at temperature 0.

### `base_ctx_oracle`

- factual probes only,
- deterministic oracle row retrieval,
- includes relevant company/process/service/certification facts,
- is an oracle-context upper bound,
- never describe it as a production RAG baseline.

### SQL baselines

`base_sql` and `base_sql_5shot`:

- use the v3 schema,
- use the shared runtime value catalogue,
- execute on `train_dev_kb` for dev,
- execute on `full_kb` for test.

---

# Interpretation and reporting

## 27. Claim discipline

Do not overclaim.

Interpret comparisons as frozen in `README.md`.

In particular:

- B tests factual SFT.
- D tests SQL SFT against zero/few-shot SQL baselines.
- BD controlled vs repeated-D tests **supervision allocation at matched exposure**.
- It does not isolate “facts help” from “fresh examples beat repetition.”
- A and BC are diagnostic.
- C remains primary only if Phase 0 confirms its required multi-seed compute budget.
- BD_full is practical/descriptive.

Frame the study as a controlled **single-model, single-domain KB case study**.

Lead with:

- per-seed results,
- mean ± SD,
- effect sizes,
- paired item-level bootstrap estimates,
- exact denominators,
- error analysis.

P-values are supporting evidence, not the headline.

---

## 28. Metrics and weighting

Always report denominators.

Example:

```text
38 / 42 = 90.5%
```

Split-group weighting applies only to entity-attributable items.

For split-group-weighted metrics:

1. average item scores within each `split_group`,
2. average split-group scores equally.

Do not apply split-group weighting to global aggregate questions.

---

# Reproducibility

## 29. Artifact roots

Use v3-only artifact roots such as:

```text
datasets_v3/
adapters_v3/
results_v3/
validation_v3/
prompts/
tests/
```

Do not write v3 artifacts into v2 directories.

Important artifacts named by the protocol include:

```text
SOURCE_MANIFEST_v3.json
CLEANED_DATA_MANIFEST_v3.json
canonical_records_v3.jsonl
company_split_groups_v3.csv
SPLIT_IDENTITY_AUDIT_v3.md
HOLDOUT_REGISTRY_v3.json
FACT_EXPOSURE_LEDGER_v3.json
VALUE_HOLDOUT_COST_v3.csv
gnem_v3.sqlite
DB_VALIDATION_v3.md
GRADER_VALIDATION_v3.md
STRUCTURED_TASK_POOL_v3.jsonl
MULTIROW_CONFLICTS_v3.csv
BD_COMPOSITION_v3.md
MODEL_SELECTION_LOG_v3.md
FEWSHOT_MANIFEST_v3.json
probe_42_v3.jsonl
PROBE_42_AUDIT_v3.csv
DATASET_VALIDATION_v3.md
REPORT_v3.md
```

---

## 30. Hashing and provenance

Hash and record where required:

- raw workbook,
- cleaning-code version/commit,
- canonical records,
- split-group map,
- holdout registry,
- exposure ledger,
- SQLite database,
- train/dev/probe JSONLs,
- prompt templates,
- context renderer,
- few-shot manifest,
- base-model revision,
- tokenizer revision,
- training configs,
- seeds,
- adapters,
- final predictions/results.

Record the Git commit and dirty-tree state at major freeze points.

Do not rely on filenames alone for provenance.

A separate `PROVENANCE_v3.md` is optional; if created, it should document the frozen v2 reference and important code ports. Its absence must not block execution unless the user explicitly adds it to the protocol.

---

## 31. Adapter retention

Keep **all 18 per-seed v3 adapters** through final reporting/archive, as frozen in the protocol.

Do not delete adapters after evaluation.

Archive each with:

- config,
- seed,
- source dataset manifest,
- base model revision,
- adapter hash.

---

# Retired scope

## 32. Do not reintroduce retired v3 components

Do not reintroduce these into active v3 paths:

```text
latitude / longitude
geo training/evaluation
distance / radius / nearest
probe_geo
geo SQL prompts
D_sql_k0 / D_sql_k5 / D_sql_k25
relationship / graph training
graph_edges
probe_relationship
R / BDR
recursive traversal
router variants
Certification Count as a learned target
sequential adapter chaining
aggressive suffix normalization for scoring
silent SQL truncation
silent prompt truncation
v2 DB fallback
```

Historical files may be inspected through `v2-frozen-reference`, but active v3 execution must not depend on them.

---

## 33. Phase 8 migration rule

Because this is a new repository, Phase 8 means **port/build only the active v3 evaluation/reporting stack**.

Do not recreate the entire historical report architecture.

Bring across only what Phases 40–42 actually need:

- evaluation,
- grading,
- statistics,
- error analysis,
- verification/regrade,
- `REPORT_v3.md` generation.

The Phase 8 gate is functional:

> Known-correct and known-wrong synthetic fixtures must pass through parsing, grading, statistics, error analysis, and report generation without touching retired components.

---

## 34. Q42 policy

Q42 is a human business benchmark, never training material.

During the benchmark-revalidation phase:

- recompute gold against v3,
- update scoring metadata,
- reword only to remove genuine ambiguity,
- version each wording change,
- exclude or adjudicate genuinely ambiguous questions if required.

Q42 may never change training composition.

After Q42 is frozen:

- no Q42 inference before Phase 40,
- no Q42 error inspection before Phase 40,
- no model/config decision based on Q42.

---

# Failure handling

## 35. Failure and deviation policy

If execution differs from the frozen protocol:

1. stop,
2. describe the deviation,
3. explain why it occurred,
4. identify affected artifacts/claims,
5. ask for approval before proceeding.

Do not silently patch a protocol deviation after results exist.

Classify unexpected issues as:

```text
implementation bug
validation failure
protocol deviation
resource constraint
genuine experimental result
```

Do not confuse them.

---

## 36. Code-change discipline

Prefer small, auditable changes.

For every port or rewrite:

- preserve/add regression tests,
- preserve previously solved bug behavior,
- avoid broad unrelated refactors,
- avoid formatting churn,
- keep paths/configuration explicit,
- never add silent fallbacks.

If a bug was already discovered in v2, add a regression test in v3 before trusting the corresponding ported behavior.

---

# Phase 0

## 37. Phase 0 exit conditions

Because the frozen plan lives in `README.md`, do **not** create a duplicate `GNEM_v3_SPEC.md` unless the user explicitly requests one.

Phase 0 is not closed until:

- `README.md` contains the frozen v3 protocol,
- `CLAUDE.md` exists and is committed,
- `v2-frozen-reference` resolves to the exact historical commit intended for consultation,
- the historical commit SHA is recorded,
- the 18-run GPU budget is explicitly confirmed, or C is demoted consistently in the protocol and analysis hierarchy,
- all per-seed adapters are confirmed for retention,
- base model/tokenizer revision policy is recorded,
- the Phase 0 freeze commit SHA is recorded,
- the working tree state at freeze is documented.

Then update the status block to:

```text
PROTOCOL_STATUS: FROZEN
CURRENT_PHASE: 1
LAST_COMPLETED_PHASE: 0
NEXT_PHASE: Phase 1 — Freeze the source workbook
TEST_STATUS: LOCKED_UNTIL_PHASE_40
```

Do not begin Phase 1 until Phase 0 is closed.

---

# Required Claude response format

## 38. End-of-phase report

At the end of every phase, report:

```text
Phase:
Status: PASS / FAIL / NEEDS REVIEW
Files changed:
Artifacts created:
Validation results:
Protocol deviations:
Git status / commit:
Next phase:
```

Then stop.

---

## 39. Final operating principle

The goal is not to move through phases as quickly as possible.

The goal is to produce a **reproducible, leakage-controlled, auditable GNEM v3 experiment whose final claims can be traced back to frozen data, code, prompts, manifests, scoped databases, model weights, and evaluation outputs**.

When in doubt:

> preserve the frozen experimental interpretation, make the implementation explicit, validate it, document it, and stop at the phase gate.
