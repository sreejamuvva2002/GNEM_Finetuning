# PROVENANCE_v3.md

Provenance record for the GNEM v3 experiment.

This file records approvals, freeze points, commit SHAs, and important code ports, as permitted by
`CLAUDE.md` §6 ("Record the exact commit SHA used as the v2 reference in the v3 repository
documentation or Phase 0 record") and §30 ("A separate `PROVENANCE_v3.md` is optional; if created,
it should document the frozen v2 reference and important code ports").

It is an **append-only record**. Existing entries are not rewritten; corrections are added as new,
dated entries that state what they supersede.

---

## Phase 0 — approval and freeze record

**Recorded:** 2026-08-23
**Phase 0 status:** CLOSED — approved by the user.

### Approval

Phase 0 was **explicitly approved by the user** on 2026-08-23. The user's approval was given as a
formal Phase 0 approval and directed that no training condition, seed policy, comparison hierarchy,
or other protocol decision be changed.

The repository state and all Phase 0 decisions are **frozen** as of that approval.

### Compute budget — CONFIRMED

The **full 18-training-run experimental matrix is explicitly confirmed** by the user, exactly as
specified in `README.md` (Phase 0, "Compute budget, decided here"): 5 primary arms at ≥3 seeds each,
plus 3 diagnostic arms at 1 seed each.

Consequence, recorded explicitly so that no later phase has to re-derive it:

- **`C_answers` remains PRIMARY at ≥3 seeds.**
- The contingent demotion branch in `README.md` Phase 0 ("If the budget does not cover 18 runs,
  demote `C_answers` to diagnostic **now**") is **NOT** taken.
- Phase 41's primary-comparison hierarchy is therefore **unchanged**. Seed count and claim status
  agree, as the protocol requires.

### Training arms and seed policy

Frozen exactly as defined in `README.md` (Phases 33–39). No arm, seed count, or condition is altered
by this record.

| Phase | Condition | Seeds | Claim status |
|---|---|---|---|
| 33 | `A_cpt` | 1 | diagnostic |
| 34 | `B_facts` | ≥3 | primary |
| 35 | `C_answers` | ≥3 | primary (confirmed by the 18-run budget) |
| 36 | `D_sql` | ≥3 | primary |
| 37 | `BC` | 1 | diagnostic |
| 38 | `BD_controlled` + `D_repeat_budgetmatched` | ≥3 | primary |
| 39 | `BD_full` | 1 | diagnostic (predeclared) |

Baselines (`base`, `base_ctx_oracle`, `base_sql`, `base_sql_5shot`) decode greedily at temperature 0
and therefore have a single deterministic result with no spread.

### Adapter retention

**All 18 per-seed adapters are to be retained and archived.** No adapter is deleted after evaluation.
Each is archived at Phase 42 with its config, seed, source dataset manifest, base-model revision, and
adapter hash (`README.md` Phase 0 "Adapter retention — DECIDED"; `CLAUDE.md` §31).

### Authoritative documents

- **`README.md`** is the **authoritative frozen GNEM v3 experimental protocol** (Phases 0–42).
- **`CLAUDE.md`** is the **execution contract** governing how the protocol is carried out.

If the implementation conflicts with `README.md`, execution stops and the conflict is reported. The
protocol is not silently modified to make implementation easier.

### Source workbook

```text
kb/GNEM_Final_Combined_Dataset.xlsx
sheet: GNEM Combined
```

Present in the repository at the Phase 0 freeze. The workbook SHA256 and the source-level checks
(205 rows, 18 columns, 193 exact company names) are **Phase 1** artifacts and are recorded in
`SOURCE_MANIFEST_v3.json`, not here. Their absence from this record is by design, not an omission.

### Historical v2 reference

```text
tag:    v2-frozen-reference
commit: b18313ae593995e8d415880603b3d355dd695ebd
```

Verified with `git rev-parse v2-frozen-reference` at the time of this record.

The v2 repository is **historical, read-only reference material only**. It is evidence and
implementation history, never an executable dependency. Historical files are inspected with
`git show v2-frozen-reference:<path>`. The v2 branch is never merged into v3, never rebased onto,
never checked out as the working branch, and v3 never acquires a runtime dependency on the old
repository path or its datasets, databases, adapters, predictions, or results (`CLAUDE.md` §7).

Note: `v2-frozen-reference` is a **local Git tag**. Tags do not travel with pushed commits by
default, so the tag must be preserved (or re-created against the SHA above) in any clone that needs
to consult the historical reference.

### Phase 0 freeze commit

```text
commit: 3d6505d98436a1035c25f4a08ad7939fd19b9e3f
subject: Freeze GNEM v3 experimental protocol
```

**Working tree state at the original Phase 0 freeze: CLEAN.** `git status --porcelain` returned zero
lines at that commit — no modified, staged, or untracked files.

Tracked files present at the freeze commit, in full:

```text
CLAUDE.md
README.md
kb/GNEM_Final_Combined_Dataset.xlsx
```

### Base model and tokenizer — Phase 0 policy only

The Phase 0 exit condition is that the **revision policy** is recorded. The policy is:

- Every adapter starts from the **same pinned base revision** of `Qwen/Qwen2.5-14B-Instruct`
  (`README.md`, Phases 33–39).
- Plain LoRA, bf16, and **no sequential adapter chaining** — never A→B, B→D, or D→BD.

The **concrete immutable model/tokenizer revision hash is deliberately not recorded at Phase 0.** It
is resolved and recorded later, at the protocol-defined stage when the base model is materialized,
and enters the full hash chain required by `README.md` ("base-model and tokenizer revision"). This
deferral is the recorded Phase 0 decision, not an unrecorded gap.

### KB scopes and SQL execution

Frozen exactly as defined in `README.md` and `CLAUDE.md` §12–§14. There are exactly three named KB
scopes:

```text
train_kb
train_dev_kb
full_kb
```

There is **no unscoped KB accessor**; every call site names a scope explicitly. `run_sql(...)`
requires an explicit scope and refuses to execute without one. Prediction and gold always execute in
the same scope. The generated SQL itself remains scope-neutral — the executor chooses which scoped
data are visible.

### Test and Q42 blinding

**No test inference and no Q42 inference is permitted before Phase 40.** Before Phase 40 there is no
test scoring, no test error analysis, and no test example logging. Phases 31–39 are dev-only. Dev is
the only place where configuration decisions are made, and every dev-driven decision is recorded in
`MODEL_SELECTION_LOG_v3.md`. Test and Q42 outcomes never tune anything.

### Phase 0 exit conditions — verification

| Exit condition (`CLAUDE.md` §37) | State |
|---|---|
| `README.md` contains the frozen v3 protocol | ✅ |
| `CLAUDE.md` exists and is committed | ✅ committed at `3d6505d` |
| `v2-frozen-reference` resolves to the intended historical commit | ✅ `b18313ae…` |
| Historical commit SHA recorded | ✅ this record |
| 18-run GPU budget explicitly confirmed (else C demoted consistently) | ✅ confirmed; C stays primary |
| All per-seed adapters confirmed for retention | ✅ all 18 retained and archived |
| Base model/tokenizer revision policy recorded | ✅ policy recorded above; concrete hash deferred by decision |
| Phase 0 freeze commit SHA recorded | ✅ `3d6505d…` |
| Working tree state at freeze documented | ✅ clean |

**Phase 0 gate: PASS.**

---

## Amendment A-001 — geographic semantics

**Recorded:** 2026-08-23
**Approved by:** the user, explicitly, as a formal protocol amendment.
**Status:** ACTIVE.

### Timing — why this amendment is legitimate

A-001 was made **before Phase 2 was frozen**, before any canonical records existed, and **before any
model result, test or Q42 inference, holdout selection, or downstream evaluation had been observed**.

Repository state when the amendment was approved:

```text
Phase 0 freeze commit  3d6505d98436a1035c25f4a08ad7939fd19b9e3f
HEAD before amendment  64c8f2fc4b3719c2b68eb1b43eb4c1e50b53c56d  (Phase 1 complete)
TEST_STATUS            LOCKED_UNTIL_PHASE_40
Phases completed       0, 1
Phases not started     2 onward
```

At that point the repository contained the frozen protocol, the execution contract, the source
workbook, and the Phase 1 source manifest — and nothing else. No cleaned records, no splits, no
holdouts, no datasets, no adapters, no predictions, no scores. No measured outcome could have
informed this amendment, and none did.

### Problem

The original Phase 2 clause made derived `city`/`county` conditional on a location being *a real
Georgia location*, conflating two separate properties — whether a `Location` is **real**, and whether
it is **in Georgia**. A real non-Georgia `Location` would have been discarded as geographic data
purely for being out of state.

It also left a genuinely unknown `Location` undefined. The workbook has three blank-`Location` rows
which are not alike:

```text
row_id 187  Valeo                      Location blank, Address blank
row_id 192  Volvo Cars USA             Location blank, Address 1800 Volvo Place, Mahwah, NJ 07430
row_id 193  Volvo Group North America  Location blank, Address 7900 National Service Rd, Greensboro, NC 27409
```

Valeo's location is *unknown*; Volvo's is *structurally inapplicable*, because a real non-Georgia
address exists and so a Georgia location does not apply. The original wording named only Volvo and
had no sentinel for the Valeo case.

### The amended rule

```text
real Location (Georgia or non-Georgia)   preserve the Location value
                                         derived city/county only as permitted below

missing / unknown Location               Location = Not specified
                                         derived city/county = SQL NULL

structurally inapplicable Location       Location = Not applicable
                                         derived city/county = SQL NULL
```

**Derived geography is read, never inferred.** Derived `city`/`county` may be populated only from
geographic information **explicitly represented in the canonical `Location` value**. They are never
inferred from `Address`, external geocoding, company knowledge, or any other field. If a `Location`
names a real city but does not explicitly provide a county, `county` remains `NULL`. `Address`
remains an independent factual field and is never substituted for `Location`. The sentinel never
enters the `city`/`county` field.

### Consequences for the named cases

```text
Valeo  (row_id 187)   Location = Not specified
                      Address  = Not specified
                      derived city/county = NULL

Volvo  (row_id 192)   Location = Not applicable
                      Address  = 1800 Volvo Place, Mahwah, NJ 07430      (preserved)
                      derived city/county = NULL

Volvo  (row_id 193)   Location = Not applicable
                      Address  = 7900 National Service Rd, Greensboro, NC 27409  (preserved)
                      derived city/county = NULL
```

### Clauses superseded

```text
README.md  Phase 2  geographic clause                  (was: "not a real Georgia location")
README.md  Phase 4  city/county parsing clause         (was: "only from real location values")
```

The full amendment text is recorded in `README.md` under `# Protocol amendments`, section A-001.

### Scope limit

A-001 changes geographic semantics only. It does **not** reinstate any retired v3 component — no
latitude/longitude, no geocoding, no geo training or evaluation, no distance/radius/nearest logic,
no `probe_geo`, no geo SQL prompts. Those remain retired under `CLAUDE.md` §32. No training arm,
seed policy, KB scope, holdout rule, comparison hierarchy, or grading rule was altered.

Phase 2 does **not** materialize `city`/`county`. Derivation belongs to the Phase 4 loader.

---


## Amendment A-002 — original V3 full-field training

The user explicitly selected “Revise original V3 now for full-field training” during resumption. [PROTOCOL_A002_FULL_FIELD.md](PROTOCOL_A002_FULL_FIELD.md) records the active specification and its overrides. Existing company holdouts and the eight-variant/minimum-18-run study remain; categorical field omissions and within-training literal holdouts are superseded. Phase 21 exposure interpretation and controlled-mixture sampling change as documented. No V3 training/test inference was performed at amendment time. Earlier phase approvals remain historical and are not reused to certify amended artifacts. This records specification authorization, not downstream completion.


### A-002 clarification — recorded Certification Count excluded from training

User-authorized exception: retain Certification Count in source/canonical data for validation but exclude it from model-facing training and schema. Full certification lists remain included. Loader updated to kb_v3.2_count_internal; no source, canonical or training dataset values were edited by this clarification. Earlier A-002 count-inclusion wording is superseded.

## 2026-09-11 — A-002 Phase 5–8 implementation and regression verification

Rebuilt the database byte-identically and revalidated complete context. Phase 5's forbidden-V2-path scan now targets executable `finetune/` sources, excluding historical review evidence and installed packages; this is a literal source check, not proof of transitive runtime isolation. Corrected unambiguous single-cell alias grading while preserving strict-schema scores. Added a configurable five-second SQLite VM deadline (progress callbacks every 1,000 instructions plus completion check); setup is outside the query deadline and a single long-running SQLite builtin may delay a callback, so this is not process-level resource isolation. An actual expensive cross-join interruption is regression-tested. Updated Phase 8 grader/executor pins after passing the Phase 7 tests; preserved earlier synthetic fixtures in `archive/pre_A002_phase8_2026-09-11/`.

Passing checks: Phase 5 builder and 8 faults; Phase 6 budget gates and 16 faults; Phase 7 existing 81 checks and 5 new regressions; Phase 8 synthetic 94 checks and 4 statistics regressions. See `validation_v3/resumption/PHASE5_8_MANIFEST.json` for exact current artifact hashes. These are agent-run engineering checks, not independent human review, model evaluation, or approval of the old training datasets. Next: Phase 9 A-002 registry migration.

## A-002 runtime continuation — development and smoke evidence

Regenerated the full-field A/B/C/D and mixture datasets. Independent coverage verifies 2,220 training-row/attribute observations; company identifiers and source-record provenance are retained. Complete assistant labels were checked with the pinned training tokenizer; overlength, empty-assistant and unsupported-turn regressions fail explicitly. The structured pool contains 1,326 tasks and 3,978 verified scoped SQL gold executions.

Built development and protected probe inputs without protected model scoring. Q42 candidate oracles remain pending adjudication and personal approval; the user explicitly selected “Keep Q42 approval pending; continue runtime checks.” No final training release was created.

Ran four development baselines with preserved raw outputs, canonical records and telemetry. The first prose-format and missing-catalogue runs are retained as pilots. Prompt corrections and their reasons are recorded in MODEL_SELECTION_LOG_v3.md. The current 51 structured dev questions are narrow entity-conditioned filters, so their scores do not establish analytical generalization. Broader analytical development and final scoring integration remain open gates.

All eight recipes completed representative two-step LoRA smoke tests and adapter reload checks. Nonzero LoRA updates, finite losses and identical reload logits were verified. These are smoke adapters, not any of the 18 required final training runs. The first prefix-only smoke suite was archived because it did not exercise every mixture component. Six real-model SQL micro cases exercised count, top-k, no-match, composition, grouping and multipart paths; no quality claim is drawn from this small plumbing battery.

Current evidence: validation_v3/resumption/RUNTIME_PROGRESS_A002.json; results_v3/dev/REPORT_A002.md; V3_PHASE_STATUS.md. The experiment remains incomplete until outstanding review, evaluation and final-training gates are satisfied.

## Repository cleanup verification — 12 September 2026

User-authorized cleanup removed redundant completed smoke checkpoint copies and optimizer/scheduler/RNG resume state: 224 recorded actions, 13,549,695,392 logical bytes (12.62 GiB). Identical checkpoint files now use relative links to retained selected adapters. All selected adapters, source data, datasets and raw results were retained. Completed smoke runs no longer support optimizer-state resume; final-training retention requirements are unchanged.

README and CLAUDE now describe current status; their complete previous contents remain in docs as historical protocol references. Removed unused superseded omission/sampling helpers and corrected the BD audit wording. Rebuilt A, B and BD artifacts, rechecked the frozen A-002 registry and full-field coverage. Final cleanup integrity results and current file hashes are recorded in validation_v3/resumption/CLEANUP_VERIFICATION_2026-09-12.json. Earlier runtime manifests remain historical snapshots, not claims that the new documentation/code produced earlier model runs. Final training remains 0/18; Q42 approval remains pending.

## Intermediate push preparation — 12 September 2026

Added versioned A002.2 dev rescoring and 30 parser regression tests; retained r1 predictions and reports. Current report is results_v3/dev/REPORT_A002_r2.md. Added explicit pre-training gates and corrected generated A/BD budget documentation without changing training data. Large weights remain local, excluded from ordinary Git; no external backup is claimed. This milestone is not a training release, and Q42 approval remains pending.

## 2026-09-12 — development set replacement and release-gate hardening

Two pre-training gates were closed as engineering work; neither is an approval.

**Structured development set.** `dev_structured_v3.jsonl` quoted its complete gold
answer inside every one of its 51 questions and was the checkpoint-selection signal
for five of the eight arms. `dev_structured_r2_v3.jsonl` (120 tasks, join arity
0/1/2, 96 set answers and 24 counts) replaces it for selection. The original file,
`results_v3/dev/REPORT_A002.md`, `VERIFIED_BASELINES_A002.json` and the r2 rescoring
outputs are preserved byte-identically as historical artifacts; the new set is a new
file, not an edit. Frozen company, operation and composition holdouts are unchanged
and re-asserted fail-closed by `dev_structured_r2_tests.py`. Reasoning is recorded in
`MODEL_SELECTION_LOG_v3.md`; hashes and test results in
`validation_v3/resumption/DEV_SET_AND_RELEASE_GATE_2026-09-12.json`.

**Release gate.** `train_v3.py` previously accepted a release with an empty input
hash map and never checked the seed being run. It now requires a complete, undrifted
22-input pin, `q42_approval: approved`, and a pre-declared 18-entry `run_schedule`
containing the exact `(variant, seed)` pair. The proposed pairs are recorded in
`validation_v3/PROPOSED_RUN_SCHEDULE_A002.json`, which is explicitly not a release.

No model inference was performed, no training was started, no approved release was
created, and Q42 approval remains pending at the user's direction. Final training
runs completed: 0 of 18. Earlier runtime and cleanup manifests remain snapshots of
their own dates and were not rewritten.

## Current continuation: corrected dev baselines and sampling

Ran four unchanged-base conditions against the corrected dev input with isolated protocol_A002_dev_r3 outputs. Factual base 0/255, oracle 245/255; structured base 0/120, SQL and SQL-five-shot 120/120. These are a changed benchmark, not a model-improvement comparison. Preserved all prior raw predictions and inputs.

Changed final partial repetition to proportional source-token allocation by join arity, retaining all sources. Archived old mixtures; current controlled/repeated budgets 94,417/94,440. Rebuilt audits, checked full-field coverage. Existing smoke adapters describe old inputs, not smoke validation of the new mixtures.

D_sql rehearsal exercises final accumulation and epoch selection, 6 steps; finite losses and deterministic best-adapter reload checked. Added exact structured result grading and output-contract helper. Base floor sanity 30/30; does not establish broad capability. New helper integration into final sealed evaluation remains open. No final training, approved release, Q42 approval, commit or push performed by this continuation.

## Offline final-driver integration

Added final_eval_v3.py and nine synthetic tests. Driver authorization checks precede protected-content parsing; Q42 approval and Phase 40 release files remain absent. Explicit per-probe scopes retained, including train_kb for structured recall/paraphrase. Canonical multipart serialization, SQL result evidence, no-match counts and independent-seed summaries verified. No final inference, unsealing, protected grading, commit or push occurred. Remaining generation/export/sealing and planned comparison integration is stated in docs/FINAL_EVALUATION_DRIVER.md.

## 2026-09-12 — training release bound to external Q42 approval evidence

`train_v3.py` previously accepted a release whose own `approved` and `q42_approval`
fields asserted approval; flipping those two strings unlocked all 18 final runs with
no external evidence, while `final_eval_v3.authorize()` already required a pinned,
hash-verified `Q42_HUMAN_APPROVAL_A002.json` for protected scoring.

`check_q42_approval()` now mirrors that requirement for training: the release must pin
both the approval artifact and `datasets_v3/probe_42_v3.jsonl`, both pinned digests
must match the files on disk, the approval must itself record `approved: true`, and it
must name the current benchmark bytes so a stale adjudication cannot certify a changed
Q42 set. The training gate is therefore no weaker than the evaluation gate.

Verified by re-running the original bypass: a release satisfying every other check —
complete pins, correct pre-registered schedule, both approval strings flipped — is now
refused, and only genuine, correctly pinned, current evidence is accepted. Ten new
rejection tests cover a missing artifact, `approved: false`, malformed JSON, a stale
benchmark reference, an unpinned or wrongly pinned digest, and the absence of any
approval artifact in the repository. 35 release-gate tests pass; 110 across all suites.

No approval was fabricated, no `TRAINING_RELEASE_A002.json` or
`Q42_HUMAN_APPROVAL_A002.json` was created, no training was started. Operation
holdouts and all training datasets are unchanged. Q42 adjudication remains pending at
the user's direction and final training remains 0/18.

## 2026-09-12 — BD partial-cycle repetition stratified jointly

The arity-only sampler balanced join arity but left the task-kind axis skewed: count
tasks received 39.05% of extra-copy tokens against a 9.30% source share, and no filter
task was ever repeated, because ordering inside an arity was a lexicographic prefix and
`count` sorts before `filter`.

Repetition now retains every source and every complete cycle, and allocates the final
partial cycle jointly across `(join_arity, task_kind)` by source supervised-token share.
Within a stratum the order is a keyed sha256 digest of the example ID — deterministic and
reproducible from the artifact, decorrelated from the ID text, salted with the generator
version so a future generator reshuffles openly.

Maximum joint-stratum token-share deviation is 0.26% (BD_controlled) and 0.13%
(D_repeat_budgetmatched), against +29.75% before. Whole-example rounding leaves the single
`threshold` task (0.05% of D tokens) without an extra copy; deviations, the seven-token
overshoot and the ordering rule are recorded in BD_COMPOSITION_v3.md and
BD_SAMPLING_MANIFEST_v3.json rather than summarised away.

BD_controlled is 3,512 items / 94,411 tokens (B 47,202, D 47,209); D_repeat is 2,724 /
94,418. BD_full, A, B, C, D and BC are byte-identical. Factual coverage re-verified at
2,220/2,220. Both earlier mixtures are archived with hashes under
archive/pre_stratified_BD_2026-09-12 (original) and archive/pre_joint_stratified_BD_2026-09-12
(arity-only). The controlled-BD and repeated-D smoke runs were produced on the ORIGINAL
mixtures and still resolve to those input hashes; they do not validate the current
mixtures, and the affected checks must be repeated if smoke-level evidence is wanted.

No approval was created, no training was started, nothing was committed or pushed.
