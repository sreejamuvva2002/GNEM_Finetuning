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
