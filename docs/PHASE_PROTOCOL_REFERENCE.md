# GNEM v3 — Experimental protocol and current implementation

**Active amendment:** [A-002 — Full-field training](PROTOCOL_A002_FULL_FIELD.md) revises the original eight-variant study. It supersedes incompatible field-exclusion, value-holdout, conflict-skipping and sampling clauses below. Implementation migration is not complete. See [phase status](V3_PHASE_STATUS.md).

**Current roadmap:** [V3 updated plan](V3_UPDATED_REVIEW_AND_PLAN.md). This README retains the detailed original phase specification for traceability; A-002 takes precedence where it conflicts.

**Repository:** GNEM v3 experimental repository

**Protocol file:** `README.md`

**Historical implementation reference:** `v2-frozen-reference`

**Source:** `kb/GNEM_Final_Combined_Dataset.xlsx`, sheet `GNEM Combined`
The previous GNEM/v2 implementation is preserved as a read-only historical reference. GNEM v3 may selectively port reviewed implementation logic, regression tests, and documented bug fixes, but it must not depend on v2 runtime paths, databases, datasets, adapters, predictions, or results.

**Research question.** Which kinds of GNEM knowledge are effectively learned in model weights, and
which are better served by externally executed structured access?

**Three disciplines govern the whole plan.**

1. **Pre-registration.** Every holdout is frozen before the data that tests it exists.
2. **Sealed test.** Dev drives every decision; the test suite and Q42 are unblinded once, at Phase 40.
3. **One clean interpretation per claim.** Each comparison varies exactly one thing.
Each phase states **why it exists**, what we do, what it produces, what is checked, and what must pass
before moving on. Validation numbers were verified against the workbook and the v2 code.

---

# Protocol amendments

Amendments to this frozen protocol are numbered, dated, and recorded here. Each states what changed,
why, and when relative to the experimental timeline. `PROVENANCE_v3.md` carries the same record.

## A-001 — Geographic semantics: real non-Georgia locations are valid geographic data

**Approved:** 2026-08-23 · **Status:** ACTIVE · **Supersedes:** the geographic clause of Phase 2 and
the `city`/`county` parsing clause of Phase 4.

**Timing.** Made **before Phase 2 was frozen** and before any canonical records existed — and before
any model result, test or Q42 inference, holdout selection, or downstream evaluation had been
observed. Test and Q42 remain sealed (`LOCKED_UNTIL_PHASE_40`). No measured outcome informed it.

**Problem.** The original wording made derived `city`/`county` conditional on a location being *a
real Georgia location*, conflating **reality** with **Georgia-ness**: a real non-Georgia `Location`
would have been discarded as geographic data purely for being out of state. It also left a genuinely
unknown `Location` — blank `Location` *and* blank `Address` — with no defined sentinel, since the
only named exception was Volvo.

**The amended rule.**

| `Location` | `Location` value | derived `city`/`county` |
|---|---|---|
| real (Georgia **or** non-Georgia) | preserved as-is | derived only as the rule below allows |
| missing / unknown | `Not specified` | SQL `NULL` |
| structurally inapplicable | `Not applicable` | SQL `NULL` |

**Derived geography is read, never inferred.** Derived `city`/`county` may be populated **only from
geographic information explicitly represented in the canonical `Location` value**. They are never
inferred from `Address`, external geocoding, company knowledge, or any other field. If a `Location`
names a real city but does not explicitly provide a county, `county` remains `NULL`. `Address`
remains an independent factual field and is **never** substituted for `Location`. The sentinel never
enters the `city`/`county` field.

**Consequences for the two named cases.**

- **Valeo** (`row_id` 187) — `Location` blank and `Address` blank: `Location` = `Not specified`,
  `Address` = `Not specified`, derived `city`/`county` = `NULL`.
- **Volvo** (`row_id` 192, 193) — the frozen exception is retained on the amended basis: the real
  NJ/NC `Address` values are preserved as factual `Address`, `Location` remains `Not applicable`, and
  derived facility `city`/`county` remain `NULL`.

**Scope limit.** A-001 changes geographic semantics only. It does **not** reinstate any retired v3
component — no latitude/longitude, no geocoding, no geo training or evaluation, no
distance/radius/nearest logic, no `probe_geo`, no geo SQL prompts. Those remain retired per
`CLAUDE.md` §32.

---

# Part I — Data foundation (Phases 0–5)

## Phase 0 — Freeze the v3 specification

**Why.** Every later phase cites this document. Ambiguity here becomes contradiction later.

**We do.** Fix scope, conditions, baselines, schema, sentinel policy, split policy, evaluation
families, grading policy and output paths. Declare in writing:

- **Seeds:** ≥3 for every arm carrying a **primary** comparison — `B_facts`, `C_answers`, `D_sql`,
  `BD_controlled`, `D_repeat_budgetmatched`. Single seed for the **diagnostic** arms — `A_cpt`, `BC`,
  `BD_full`. **Seed count and claim status must agree:** if compute forces C to one seed, C moves to
  diagnostic in Phase 41's hierarchy. Never leave an arm primary at n=1. Baselines decode greedily
  at temperature 0 and therefore have a single deterministic result with no spread.

- **Blinding:** dev may influence model and config decisions; test and Q42 may never. Headline
  metrics are test-only and computed once.

- **`BD_full` is predeclared**, not contingent on earlier results.
- **Compute budget, decided here — not improvised at Phase 35.** The matrix is **18 training runs**
  (5 primary arms × ≥3 seeds, plus 3 diagnostic arms). Measured v2 timings on this box, at ~36 GB
  peak VRAM: `A_cpt` 5.3 min · `C_answers` 9.3 · `B_facts` 20.8 · `BC` 30.0 · `D_sql` 43.5 · `BD`
  63.9. `D_sql` costs 4.7× `C_answers` on identical example counts because the 4,497-char schema
  prompt rides every row — wall-clock tracks **total** tokens even though loss is completion-only, so
  `D_repeat_budgetmatched` is the most expensive arm in the matrix. Extrapolated to v3's larger
  datasets: roughly **18–20 GPU-hours of training**, with **evaluation dominating** — 22 conditions
  × ~4,600+ probe items each. Estimate this before Phase 0 closes. If the budget does not cover 18
  runs, demote `C_answers` to diagnostic **now**, as a recorded decision, rather than dropping seeds
  under time pressure later.

- **Adapter retention — DECIDED: keep every per-seed adapter.** v2 deleted them after evaluation to
  save disk. v3 keeps all 18 (537 MB each, ~9.7 GB total). Disk is cheap; losing the ability to
  re-run a single seed's evaluation, or to trace an anomalous result back to its weights, is not.
  Phase 42 archives all of them.

- **Compute confirmation is a Phase 0 exit condition.** The 18-run matrix above assumes `C_answers`
  stays primary at ≥3 seeds. Confirm the GPU budget covers it **before closing Phase 0**. If it does
  not, demote C to diagnostic here, in writing, and update Phase 41's hierarchy in the same edit —
  the two must never disagree.

- **`A_cpt` rendering count — DECIDED: one canonical passage per row.** v2 emitted three renderings
  (key-value record, prose paragraph, table line). v3 uses one. **The cost, recorded now rather than
  discovered at Phase 41:** three renderings were v2's deliberate defence against binding a fact to
  a single phrasing, so a one-passage A is **expected** to be weaker on
  `probe_fact_paraphrase_v3` specifically. That is a consequence of the design choice, not evidence
  that CPT fails to generalize, and the report must say so. In exchange, A's LM-token exposure is no
  longer inflated 3× relative to the facts it covers, which makes its budget legible.

- **General-capability retention — DECIDED: include it.** v3 does not evaluate broad model
  capability as a research endpoint. A fixed 30-item instruction/reasoning sanity suite is run

**only as a retention/regression screen** and cannot affect training, model selection, prompt
  selection, or any phase decision. It is frozen before Phase 33, run only at Phase 40 alongside the
  sealed tests, and reported separately from every GNEM research claim. Its purpose is one question:
  did fine-tuning damage basic instruction-following? A model can look strong on GNEM while becoming
  brittle elsewhere, and this is the cheapest way to notice.

**Artifacts.** Frozen `README.md`; `CLAUDE.md`; recorded `v2-frozen-reference` commit SHA; recorded Phase 0 freeze commit SHA.

**Gate.** `README.md` approved as the authoritative frozen protocol, Phase 0 compute decision recorded, historical reference SHA recorded, and freeze commit recorded. Nothing in the pipeline moves before this.

---

## Phase 1 — Freeze the source workbook

**Why.** Prove the experiment starts from exactly one artifact.

**We do.** Record SHA256, size, sheets, row/column counts, unique company count. Ignore the empty
`Certification Key` sheet.

**Artifacts.** `SOURCE_MANIFEST_v3.json`.

**Validation.** 205 rows · 18 columns · 193 exact company names · `Certification Key` is 0×0.

**Gate.** Hash recorded. No cleaning yet.

---

## Phase 2 — Clean, normalize, and freeze canonical records

**Why.** The same workbook with different cleaning code is a different experiment. Hashing the raw
file alone does not catch that, so the **cleaned** representation is frozen and hashed here.

**We do.** Category `OEM Footprint` → `OEM (Footprint)`. Facility type `Manufacturing plant` →
`Manufacturing Plant`, `Engineering / Manufacturing` → `Manufacturing / Engineering`; `Manufacturing`
stays distinct. For `Processes`, `Services`, `Certifications`: split on `;`, trim, drop empties,
dedupe, case-insensitive sort, rejoin. Apply sentinels — `Not applicable` (structurally
inapplicable), `Not specified` (unknown), `None identified after search` (no credential found).
Derived `city`/`county` follow **Amendment A-001**: a **real** `Location` — Georgia or
non-Georgia — is preserved; a **missing** `Location` becomes `Not specified` and a
**structurally inapplicable** `Location` becomes `Not applicable`, both yielding
`city`/`county` = SQL `NULL`. Derived `city`/`county` may be populated only from geographic
information explicitly represented in the canonical `Location` value — never inferred from
`Address`, external geocoding, company knowledge or any other field — and where a `Location`
names a city but no county, `county` remains `NULL`. The sentinel never enters the
`city`/`county` field. Volvo's real NJ/NC addresses are preserved as factual `Address`, with
`Location` = `Not applicable`.

**Order matters.** Validate `Certification Count` against the **pre-sentinel** parse, then insert the
sentinel.

**Artifacts.** `canonical_records_v3.jsonl`, `CLEANED_DATA_MANIFEST_v3.json` (hashed here, not at
the end), `CLEANING_AUDIT_v3.csv`, `NORMALIZATION_REPORT_v3.md`.

**Hash chain established.** raw Excel → cleaning-code version → canonical records → SQLite →
datasets/probes. Every later phase asserts it loaded this exact canonical representation.

**Validation.** `OEM Footprint` = 0 remaining, `OEM (Footprint)` = 8 · `Manufacturing plant` = 0,
`Manufacturing Plant` = 187, `Manufacturing` = 4 · `Engineering / Manufacturing` = 0 · all
multi-valued cells canonically ordered · `Certification Count` matches parsed terms on all 205 rows ·
employment populated on all 205 (assert; never `fillna(0)`).

**Gate.** **Checkpoint 1** — cleaned data reviewed and hashed.

---

## Phase 3 — Identity, split groups, and the train/dev/test split

**Why.** Two different questions were previously conflated: *what counts as one company in an
answer* (exact name — this is what makes Q29's gold of 23 reproduce) and *what must not straddle a
split* (organizational identity). They need separate fields.

**We do.** Three identities: `row_id` = `Record No.`; `company` = exact trimmed name, no suffix
stripping; `split_group` = leakage-control identity. Build a split-specific normalizer — a **copy**,
never an import of `grade.norm_company`, so grading changes cannot silently move splits — use it as a

**detector**, approve mappings by hand, freeze them.

**Split.** train 70% / dev 10% / test 20% as a **target allocation at split-group level**, frozen
here. Because the OEM-reference guard forces some groups held-in and stratification constrains the
rest, the realized split will not land exactly on those percentages — **report the realized number
of split groups, exact companies and rows per side rather than distorting the split to hit round
numbers.** **Stratify or audit** across category, facility type, certification presence, process and
service coverage, and multi-row companies — a random split can leave a rare attribute entirely on
one side.

**OEM-reference guard.** Companies named in another row's `primary_oems` stay held-in, because
holding one out leaks it through another company's answer. **Derive** this set, write it into the
manifest, report the current count (11), and assert the **placement rule** — never
`assert len(...) == 11`. If cleaning legitimately changes it, that must surface as a review failure,
not a crash against a stale constant. Name the forced-in companies and record the test-distribution
limitation for the report.

**Artifacts.** `company_split_groups_v3.csv`, `SPLIT_IDENTITY_AUDIT_v3.md`.

**Validation.** All rows of one exact company on one side · all four known collision pairs
(Ecoplastic, Hitachi Astemo, Jefferson Southern, Trenton Pressing) grouped · detector finds no
unmapped collision (**build fails**) · dev set non-empty · stratification audit recorded.

**Gate.** **Checkpoint 2** — identities and splits reviewed.

---

## Phase 4 — Loader and data contract

**Why.** One module defines what a row means to everything downstream.

**We do.** Map all 18 columns, including `processes`, `services`, `certifications`,
`certification_count`. Remove any `latitude`/`longitude` requirement. Keep employment as recorded and
assert populated. Load `certification_count` for validation only. Parse `city`/`county` only
from geographic information explicitly present in a real `Location` value — never from
`Address`, geocoding or any other field (Amendment A-001).

**Three named KB scopes — the core anti-leakage contract.** Every generator and grader declares which
scope it reads. There is no unscoped accessor.

| scope | contents | used for |
|---|---|---|
| `train_kb` | train split groups only | **all training targets** — A passages, B facts, C answers |
| `train_dev_kb` | train + dev | **dev evaluation gold only** |
| `full_kb` | all 205 rows | **test evaluation gold only**, and the deployed SQL database |

**The rule this enforces:** *training-task generation never consults test data, and dev measurement
never consults test data either.* Dev drives configuration decisions, so computing dev gold over
`full_kb` would route test knowledge into the decision loop through the back door — subtler than
training on it, and just as disqualifying. `full_kb` is reachable only by the test-gold path and by
the SQLite mirror the SQL arms query at inference, which is correct: the database is the deployed
source of truth, and the whole point of the tool-use arms is answering over rows they never trained
on.

**Validation.** All 205 records load · no geo column required · sentinels never parsed into
`city`/`county` · loader asserts the canonical-records hash from Phase 2 · **every call site names a
scope**, and a static check confirms no training generator can reach `full_kb`.

---

## Phase 5 — Build `gnem_v3.sqlite`

**Why.** Multi-valued fields cannot be queried with `WHERE col = 'value'` against a `;`-joined cell.
Child tables make membership a clean equality join and keep the JOIN-learning test alive.

**We do.** Four tables: `companies` (scalars only), `certifications(row_id, company,
standard_family)`, `processes(row_id, company, process)`, `services(row_id, company, service)`. No
`graph_edges`, no coordinates. `certification_count` is **not** model-facing — a model that can
`COUNT` the child table should not be handed the answer.

**The database is scoped, not singular.** Phase 4 defines three KB scopes, and SQL must honour them
or the scoping is fiction — every gold in the task pool is produced by **executing** a query, so a
single all-rows database would compute `train_kb_gold` over test data. Build three read-only scoped
views over the same four tables:

| scope | rows visible | used by |
|---|---|---|
| `train_kb` | train split groups | computing `train_kb_gold` (C's targets) |
| `train_dev_kb` | train + dev | computing `train_dev_kb_gold`; **dev-time SQL inference** |
| `full_kb` | all 205 | computing `full_kb_gold`; **test-time SQL inference** |

**Prediction and gold must always execute in the same scope.** At dev, a SQL arm queries the
`train_dev_kb` view and is scored against `train_dev_kb_gold`; at test, it queries `full_kb` and is
scored against `full_kb_gold`. Mixing them — a model querying all 205 rows while graded against a
train-only gold — marks correct queries wrong for rows that genuinely exist, which looks like a SQL
failure and is really a harness bug.

**Artifacts.** `gnem_v3.sqlite` with the three scoped views, `DB_VALIDATION_v3.md`.

**Validation.** Every child row has a valid parent `row_id`, zero orphans · vocabulary sizes recorded
(expect ≈49 processes, ≈22 services, ≈59 certification families; ≈555 / ≈290 / ≈662 child rows) ·
`None identified after search` yields **zero** certification rows · DB printed and hashed · **each
scoped view returns the expected row count**, and `train_kb` provably excludes every dev and test
split group.

**Gate.** **Checkpoint 3** — database reviewed. No fallback to `gnem.sqlite` anywhere.

---

# Part II — Trustworthy measurement infrastructure (Phases 6–8)

*These come before any dataset because a probe generated against a broken executor is worthless, and
because a baseline that silently truncates sets the ceiling every other result is judged against.*

## Phase 6 — Context renderer and token budget

**Why.** The old "paste the whole table" baseline is not merely large, it is impossible: the naive
render is ~35k tokens for companies alone and ~52k with child tables, while `run_eval.py` silently
cuts prompts at 24,576. Pruning columns until it fits would make the ceiling an artifact of which
columns were dropped.

**We do.** Replace it with **`base_ctx_oracle`**: deterministic gold-row retrieval rendering the
company record plus its process, service and certification child facts. Oracle retrieval is
deliberate — it makes this an **upper bound on retrieval-grounded factual answering**, not a
measurement of some retriever's quality. Scope it to **factual probes only**; for global structured
questions the external-access comparators are `base_sql` and `base_sql_5shot`.

**Budget assertion.** Not `input_tokens < tokenizer.model_max_length`, but
`input_tokens + max_new_tokens <= actual configured usable context`, checked against the model
config **and** the evaluator's `max_seq_length` — otherwise a model/evaluator mismatch stays silent.

**Artifacts.** Context renderer + version hash, `CONTEXT_BUDGET_v3.md`.

**Validation.** No prompt family exceeds budget · **no silent truncation anywhere** · rendered
context carries raw KB facts only — never gold answers, gold SQL, or generated QA.

**Language discipline.** In the report this is an **oracle-context baseline**, never a "RAG baseline."

---

## Phase 7 — SQL execution and grading

**Why.** Three silent-failure paths currently exist, and all three produce plausible numbers rather
than errors.

**We do.**

- DB path **and scope** from experiment config; no hard-coded `gnem.sqlite`, and no unscoped
  execution. `run_sql` takes an explicit scope (`train_kb` / `train_dev_kb` / `full_kb`) and refuses
  to run without one — a default would silently reintroduce the leak Phase 4 exists to close.

- Remove the unconditional `from finetune.geo import register` from the executor.
- Remove the `max_rows = 200` fetch cap and the `truncation=True, max_length=24576` prompt cut; any
  safety ceiling must raise, not truncate.

- **Task-aware scoring.** Every structured item carries `answer_type` and `target_columns`
**emitted by the generator**, never inferred at grading time. Set answers project then dedupe;
  scalar requires exactly one scalar-compatible column; top-k preserves order and length and is never
  set-deduped; multi-part questions require every part. Report
  `task_result_correctness` (primary) and `strict_result_schema_accuracy` (secondary).

- **Output-side failure handling.** If generation stops because `max_new_tokens` was reached, mark
  `truncated_output` and do **not** parse partial SQL or partial answers as normal predictions.

**Artifacts.** `GRADER_VALIDATION_v3.md` with unit tests.

**Validation.** Tests cover the known v2 failures **and** the degenerate-prediction battery — empty
string, refusal, noise, malformed — all of which currently score 1.0 on an empty-gold item.

**Gate.** Grader green. **Blocks the canonical structured task pool, C and D generation, every
structured probe, the Q42 revalidation, and final evaluation** — everything whose gold is produced or
scored by this executor. A probe built against a broken executor is worthless, and one scored by a
broken grader is worse than worthless, because it produces a number.

---

## Phase 8 — Build the v3 evaluation and reporting stack

**Why.** The historical v2 evaluation/reporting modules contain useful solved bugs and regression knowledge, but they are also heavily wired to retired geo/graph/router/dose concepts. In the clean v3 repository, recreating that entire architecture would add risk rather than remove it.

**We do.** Inspect the corresponding historical modules through `v2-frozen-reference` and selectively port or rebuild only the functionality actually required by v3: evaluation, grading integration, statistics, error analysis, verification/regrade where needed, and `REPORT_v3.md` generation. Preserve validated fixes and regression tests, but do not reproduce retired layers merely to strip them out again. Historical reference counts (for example, the old `report.py`, `run_eval.py`, `error_analysis.py`, `stats.py`, `verify.py`, and `regrade.py`) are evidence of migration risk, not a requirement to copy those files wholesale.

**Validation.** Drive the entire active v3 stack with **dummy known-correct and known-wrong prediction fixtures** and confirm it emits summary JSON, per-probe metrics, statistics, error analysis, and a `REPORT_v3.md` skeleton without touching retired components or any v2 runtime path.

**Gate.** Fixture run green. Blocking.

---

# Part III — Pre-registration (Phase 9)

## Phase 9 — Freeze the Holdout Registry and Fact Exposure Ledger

**Why.** If holdouts are chosen after seeing the generated data, the holdout that gets picked is the
one the data happens to support, and the generalization claim is not the claim it appears to be.

**We do.** Freeze entity / dev / test assignments; value-held-out values with minimum support
thresholds; operation-held-out families and their defining SQL constructs; compositional component
sets, required join arity and superset-exclusion rules; allowed operations per field; `answer_type`
and `target_columns` conventions; few-shot eligibility; the logical-fingerprint definition.

**Strict value-holdout, and how it is actually enforced.** A value claimed unseen during fine-tuning
must be absent from **every** training source, A and B included. That creates a trap: if
`Powder Coating` is held out and a company's `Processes` are `Injection Molding; Powder Coating`,
you must not answer "Injection Molding" — that teaches an incomplete fact.

**Policy: omit the item, never truncate the truth.**

- **A:** omit that field from that row's passage.
- **B:** generate no QA for that (company, attribute) pair.
- **C/D:** no structured supervision using the held-out value.
Record every occurrence in `FACT_EXPOSURE_LEDGER_v3.json` and assert, per held-out value,
`exposure_count(A, B, C, D, BC, BD) == 0`.

**Model-visible prompt leakage.** Zero exposure applies to every model-visible fine-tuning string, not only example questions and targets. Training-time system prompts, schema descriptions, value catalogues, few-shot text, chat messages, and rendered context must also exclude held-out literals. The exposure audit scans those strings explicitly. The complete runtime value catalogue is introduced only at inference/dev/test where the protocol permits it; a held-out literal may not appear in a fine-tuning prompt merely because it is presented as catalogue or schema context.

**Artifacts.** `HOLDOUT_REGISTRY_v3.json`, `FACT_EXPOSURE_LEDGER_v3.json` — committed, timestamped,
hashed.

**Validation.** Registry complete and internally consistent; no holdout references a value,
operation or combination the KB cannot support at the declared support threshold.

**Gate.** Registry frozen. **Blocks all dataset generation.**

---

# Part IV — Training datasets (Phases 10–16)

*All items carry stable IDs (`B_v3_processes_000123`); every dataset gets a manifest of exact IDs,
not merely a seed, because a seed does not reproduce the same examples after generator code changes.
Experiment-only fields — `split_group`, `entity_dependent`, `holdout_type`, `logical_fingerprint`,
`target_columns`, `certification_count`, `knowledge_exposure` — must never reach a model-visible
prompt.*

## Phase 10 — `train_A_cpt_v3.jsonl`

**Why.** Tests pure knowledge injection with no task format.

**We do.** **One canonical plain-text passage per row** (Phase 0 decision — v2's three renderings are
retired). Real factual fields only. No `Certification Count` target; no sentence that turns a
sentinel into a substantive fact; held-out values omitted per the exposure ledger.

**Known interpretation limit.** A one-passage A has weaker phrasing diversity than v2's three, so
expect it to underperform on `probe_fact_paraphrase_v3` relative to what a three-rendering A would
achieve. Report that as a design consequence, never as a finding about CPT.
Report A's passage count and LM-token budget so its exposure stays legible against the chat variants.

**Validation.** Examples, tokens, coverage, duplicate passages, sentinel leakage · **hard assert:
zero held-out or dev companies present** — plain text carries no split metadata, so this is where a
leak hides best · exposure ledger satisfied.

**Budget note.** A trains under `packing=True` with full-sequence LM loss, a different objective from
the chat variants' `assistant_only_loss=True`. Report A's budget in LM tokens and **never** place it
on the completion-token axis.

**Gate.** **Checkpoint 4.**

---

## Phase 11 — `train_B_facts_v3.jsonl`

**Why.** The classic "teach it our data" recipe — the arm the factual hypothesis rests on.

**We do.** Cell-level factual QA; processes, services and certifications as set answers. No
`Certification Count` target. No QA whose answer is a sentinel.

**Multi-row conflicts: skip them.** Location cannot disambiguate — all nine multi-row companies share
one location across their rows (Novelis' three are all `Atlanta, Fulton County`; ZF Gainesville's
three all `Gainesville, Hall County`). Rather than invent disambiguators no user would ask, skip
every conflicting (company, attribute) pair and enumerate them.

**Artifacts.** `MULTIROW_CONFLICTS_v3.csv` with `action = skipped_company_level_fact` — expect ≈28
pairs across 9 companies.

**Validation.** Per-attribute counts · entity-split distribution · well-formed set answers · no
sentinel answers · no incoherent gold such as `Indirect; No` · no duplicate questions · exposure
ledger satisfied.

**Gate.** **Checkpoint 5.**

---

## Phase 12 — Canonical structured task pool

**Why.** A central question is *does teaching the answer differ from teaching the query for the same
task?* If C and D are generated separately, they may differ in question composition too, and the
comparison stops being clean. Generating one pool and rendering both from it makes supervision target
the only difference.

**We do.** Build `STRUCTURED_TASK_POOL_v3.jsonl`. Each task carries `task_id`, question,
`operation_family`, `fields_used`, `values_used`, `logical_components`, `logical_fingerprint`,
`join_arity`, `required_constructs`, `gold_sql`, `answer_type`, `target_columns`,
`entity_dependent`, `split`, and **three computed answers**, one per KB scope:

- **`train_kb_gold`** — executed over `train_kb`. C's supervision target. Never used to score.
- **`train_dev_kb_gold`** — executed over `train_dev_kb`. **Dev** evaluation gold only.
- **`full_kb_gold`** — executed over `full_kb`. **Test** evaluation gold only. Never a training
  target, and never used for dev.

**Why three.** "How many companies are in category X?" answered over the full KB embeds a count
computed from held-out and dev companies. Training C on that number leaks test knowledge into the
weights even though no held-out company is ever named. v2 solved this by generating training from
`df_in` while probes carried full-table gold — this plan restores that, and `entity_dependent`
(`full_kb_gold != train_kb_gold`) is exactly the flag that marks where the two disagree.

**Strictness contract — what makes C vs D a clean control.** For any `task_id` rendered into both
files: identical `task_id`, identical question text **byte-for-byte**, identical metadata, identical
logical task. Only the supervision target differs.

**The one asymmetry, stated rather than hidden.** D's target is a **query**, and the query is the same
whichever KB it is computed over — so D is unaffected by the two-gold split. C's target is a

**value**, so it must take `train_kb_gold`. This asymmetry is inherent to the comparison, not a defect:
it is precisely why the SQL path is robust to a KB it was not trained on. Report it as a finding,
not a footnote.

**Validation.** 100% execution for all three golds · metadata complete · registry compliance ·
byte-equality of question text and metadata across every C/D pair · identical rendered `task_id`
sets · **no training file anywhere contains `full_kb_gold` or `train_dev_kb_gold`.**

**Deterministic ordering.** Every ranking, top-k and argmax gold SQL must carry a total tie-break —
`ORDER BY <metric> DESC, company ASC, row_id ASC` or the equivalent for its projection. Without it,
a correct query can return a different valid order than gold and be scored wrong for a reason that
is not about SQL.

---

## Phase 13 — `train_C_answers_v3.jsonl`

**Why.** Tests whether structured operations can be taught as direct answers, no tool use.

**We do.** Render C from eligible pool `task_id`s: question → **`train_kb_gold`**. Never
`full_kb_gold` — see Phase 12.

**Validation.** Every item traces to a pool `task_id` · every target equals that task's
`train_kb_gold` · metadata carried through, since C contains no SQL text and **metadata is the only
way to detect operation leakage** · zero `entity_dependent` items carrying a full-KB answer.

**Gate.** **Checkpoint 6.**

---

## Phase 14 — `train_D_sql_v3.jsonl`

**Why.** Tests the tool-use path: the model routes, the database computes.

**We do.** Render D from the **same** eligible `task_id`s: question → gold SQL. Child tables via
JOIN, never semicolon-string equality. Per-field operation policy: `Primary OEMs` excluded from
group-by and ranking (composite strings like `Hyundai Kia Rivian`); `Address` gets no structured
aggregation. Result-size caps: list/filter 1–40, cross-table 1–25.

**`row_id` policy.** SQL may join on `row_id`, but gold SQL must **not filter by `row_id`** unless the
question explicitly names a record — otherwise the model learns an artificial record-index shortcut.

**Validation.** 100% gold execution · C and D cover the identical `task_id` set · join-count and
construct distributions recorded · answer sizes within caps.

**Gate.** **Checkpoint 7.**

---

## Phase 15 — `train_BC_facts_answers_v3.jsonl`

Deterministic union of the frozen B and C files. Never regenerate variants inside BC.

---

## Phase 16 — BD datasets and budget manifests

**Why.** BD's example count (2,111 vs D's 647) overstates its advantage; with
`assistant_only_loss=True` only completions carry gradient, and by that measure BD carries **2.25×**
D, not 3.3×.

**We do.** `train_BD_facts_sql_v3.jsonl` = frozen B + D (natural recipe). Plus a controlled sampling
manifest balancing B and D by **supervised completion tokens** (~50/50). Plus

**`D_repeat_budgetmatched`**: pure D resampled to the same total supervised-token budget as
`BD_controlled`. The name states what it is — the same SQL information **repeated** to match exposure.

**What "full" means in `BD_full`.** The **full eligible v3 recipe** — every B and D example
surviving the split, holdout and exposure-ledger exclusions. It is **not** every example the workbook
could produce, because held-out entities and values are omitted from training under v3's leakage
rules. Say this in the report; "full" invites the wrong reading otherwise.

**Report.** Available vs sampled examples, supervised completion tokens, total tokens, optimizer
steps, effective passes. Reference from v2: B ≈ 89.3k supervised chars, D ≈ 71.2k, BD ≈ 160.4k.

**Composition report, not just totals.** A 50/50 token split can still overrepresent short, easy
factual attributes or a few easy SQL templates. Emit `BD_COMPOSITION_v3.md` giving the **B attribute
mix** (share of supervised tokens per attribute) and the **D operation mix** (share per
`operation_family` and `join_arity`), for both `BD_controlled` and `BD_full`, alongside the same
breakdown for standalone B and D. If the mixture skews an attribute or family relative to its
standalone source, that is a finding about the sampler, and it must be visible before training.

---

# Part V — Dev and probes (Phases 17–27)

## Phase 17 — Dev evaluation sets

**Why.** Phase 0 promises tuning happens on dev, but a dev **split** is not a dev **dataset**. Without
these files there is nowhere legitimate to make decisions, and pressure falls back onto the test
probes.

**We do.** Generate `dev_fact_v3.jsonl` and `dev_structured_v3.jsonl` from `split = "dev"`, using the
same generators as their test counterparts. **Dev gold comes from `train_dev_kb_gold`, never
`full_kb_gold`** — dev drives configuration decisions, so scoring it against the full KB would route
test knowledge into the decision loop.

**Used for.** Checkpoint selection, learning rate, epochs, LoRA rank, prompt debugging, convergence
checks.

**Never used for.** Any headline metric.

**Every dev-driven decision is logged.** `MODEL_SELECTION_LOG_v3.md` (appended throughout Phases
33–39) records every configuration tried — learning rate, epochs, LoRA rank, prompt variant — the
dev metric it was judged on, and why the final configuration was chosen. An unlogged "dev only"
claim is unverifiable; this artifact is what makes it checkable after the fact.

**Gate.** Dev sets exist and are disjoint from train and test.

---

## Phase 18 — `probe_fact_recall_v3.jsonl`

**Why.** One unified factual probe, with per-attribute submetrics rather than separate files.

**Critical labelling.** Every item carries `knowledge_exposure` as a **multi-label list**, not a
single tag — an item can genuinely be both a held-out entity and a held-out value, e.g.
`["heldout_entity", "heldout_value"]`. Labels: `trained_fact`, `heldout_entity`, `heldout_value`,
`no_match`. Report each axis singly **and** report the overlap counts, so a doubly-held-out item is
not silently counted as evidence on either axis alone. Without this labelling, B looks bad simply
for being asked facts it was deliberately never trained on, and a collapsed headline number would be
actively misleading.

**Valid combinations — asserted, not assumed:**

- `no_match` is **mutually exclusive** with all three others: an item with no matching record cannot
  simultaneously be a trained or held-out fact.

- `heldout_entity` and `heldout_value` **may co-occur** — a held-out company asked about a held-out
  value is a legitimate, and maximally hard, item.

- `trained_fact` **may not co-occur** with `heldout_entity` or `heldout_value`: if either holdout
  applies, the fact was by definition not trained.
Any item violating these is a generation bug and fails the build.

**We do.** Items carry `attribute`, company/row identity, `entity_split`, `answer_type`,
`knowledge_exposure`. Submetrics for product/service, processes, services, certifications, location,
category and the rest, plus an overall score. Set-valued attributes use exact-set, precision, recall,
F1.

---

## Phase 19 — `probe_fact_paraphrase_v3.jsonl`

Genuine rewordings, not punctuation changes. **Validation.** No exact duplicate of any B question or
recall-probe question.

---

## Phase 20 — `probe_structured_train_v3.jsonl`

Held-in diagnostic and few-shot source. Explicitly **not** a headline generalization benchmark.

---

## Phase 21 — Value-held-out probe

**Why.** Tests whether a learned operation can be instantiated with a value absent from fine-tuning.
Held-out values are **present in the runtime value catalogue** — unseen in training ≠ invisible at
inference — and the catalogue is identical across all arms. Prefer values with real support.

**Interpretation.** A floor / slot-transfer diagnostic, not the strongest generalization result.
Lead with **delta over `base_sql` and `base_sql_5shot`**, not absolute accuracy. Expect saturation:
v2 recorded tuned variants emitting gold-identical SQL 99% of the time on this axis.

### Support band — resolving a conflict between the two audits

"Prefer values with sufficient support" and "strictly remove every occurrence from A and B" pull
against each other: under the strict rule, holding out a high-support value deletes that attribute
from many training rows. Holding out `Injection Molding` (55 companies) would gut B's process
coverage entirely.
Measured value distributions and the collateral cost per held-out value:

| field | values | support 1 | support 2 | **3–5** | **6–15** | 16–40 | >40 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Processes | 49 | 9 | 3 | **11** | **15** | 9 | 2 |
| Services | 22 | 5 | 2 | **7** | **6** | 1 | 1 |
| Certifications | 59 | 36 | 7 | **3** | **5** | 4 | 4 |

Average rows losing the attribute if one value is held out: processes 4.1 (band 3–5) / 10.1 (6–15);
services 4.4 / 9.0; certifications 3.0 / 8.4.

**Registry parameter: minimum support 3, draw held-out values from the 3–15 band.** That yields 26
process, 13 service and 8 certification candidates — enough to build the probe — while capping
collateral training loss at roughly 4–10 rows per value.

**Note the certification constraint:** 43 of 59 certification values appear in fewer than 3
companies, so the certification holdout pool is at most 8 values. If the probe needs more
certification items than that supports, widen the band deliberately and record the extra B/A cost —
do not quietly drop the minimum-support rule.

**Collateral-loss ledger — required artifact.** `VALUE_HOLDOUT_COST_v3.csv`, one row per held-out
value, written at Phase 9 and re-asserted here:

| column | meaning |
|---|---|
| `value` | the held-out literal |
| `attribute_type` | process / service / certification |
| `supporting_companies` | how many companies carry it |
| `removed_train_items` | C/D structured items dropped |
| `removed_A_fields` | row-passage fields omitted |
| `removed_B_items` | factual QA pairs not generated |
| `remaining_attribute_coverage` | rows still carrying that attribute in training |

If `remaining_attribute_coverage` falls below a threshold declared in the registry, the value is not
eligible for holdout — the probe must not be bought by hollowing out the training signal it is
measuring against.

**Cumulative budget, not just per-value.** Four process holdouts costing 7, 8, 9 and 10 rows each can
individually pass a per-value threshold while jointly gutting B's process supervision. The registry
must therefore predeclare an **attribute-level floor** — after all holdouts for that attribute, at
least X% of the original train-side QA for it remains — frozen at Phase 9, before generation.

**Support reported per split, not only overall.** Each candidate carries `total_support`,
`train_support`, `dev_support`, `test_support`. A value with healthy global support but almost no
test-side support produces a probe with no usable items, which passes every per-value check and still
measures nothing.

---

## Phase 22 — Operation-held-out probe

**Validation.** Defining constructs (`GROUP BY`, `LIMIT`, argmax/top-k) appear **0 times** across all
relevant training gold — checked in D's SQL text **and** in C's metadata.

---

## Phase 23 — Compositional-held-out probe

**Why.** Tests unseen **combinations**, not unseen syntax. Training must already contain the required
join arity and constructs through **other** combinations.

**Superset rule.** For each held-out set H and every training set T: assert `not H ⊆ T`. A
`{county, process, certification}` training item would leak a `{process, certification}` holdout.

---

## Phase 24 — Structured paraphrase probe

Same gold, reworded; no exact duplication of training questions.

---

## Phase 25 — `probe_no_match_v3.jsonl`

**Why.** Under the current grader an empty string, a refusal and pure noise all score 1.0 on an
empty-gold item. A probe built naively would measure "did not hallucinate" and be maxed by a broken
model.

**Two separate scores.** **A — hallucination avoidance:** did it refrain from inventing entities?

**B — valid abstention:** did it positively state that no record matches? Empty output, parser crash,
noise, malformed output and irrelevant refusal all **fail B** while passing A. SQL systems must emit
executable SQL returning 0 rows; broken SQL does not count.

**Validation.** Test against intentionally broken dummy predictions before trusting the probe.

---

## Phase 26 — Cross-probe holdout consistency audit

**Why.** The four structured holdout probes constrain each other and cannot be designed
independently.

**Validation.** Held-out values do not appear as compositional components where forbidden ·
operation-held-out constructs are not required by compositional items · no training component set
equals or contains a held-out compositional set · required constructs and arity demonstrably seen
elsewhere.

**Gate.** **Checkpoint 8** — probes measure what they claim.

---

## Phase 27 — Freeze few-shot manifest and prompt templates

**Why.** Prompts must be frozen **before** any baseline runs, or the baseline and the tuned arms are
not answering the same prompt.

**Artifacts.** `FEWSHOT_MANIFEST_v3.json`, all prompt templates with hashes (system prompts, context
renderer version, chat template, model/tokenizer revision), and
`general_capability_sanity_v3.jsonl` — the 30-item regression screen, frozen and hashed here so it
cannot be adjusted after seeing any model.

**Validation.** Few-shot examples are train-side only · no held-out entity, value, operation or
combination · no logical fingerprint shared with any probe item.

---

# Part VI — Benchmark and final audit (Phases 28–30)

## Phase 28 — Revalidate the 42 business questions

**Why.** The v2 golds were produced against a 15-column KB. Adding Processes and Services changes at
least three answers — Q19's gold names one powder-coating company where `Processes` marks six
including **TCI Powder Coatings**; Q17 stops being empty; Q35 gains three.

**We do.** Per question: old gold, new deterministic oracle, new result, companies added/removed,
numeric change, ambiguity note, human approval. Rederive `QUESTION_SKILLS`, `ANSWER_TYPE`,
`REQUIRED_PHRASES`, `REQUIRED_NUMBERS`, `CLOSED_BOOK_EXPECTED_PASS`. Special attention to Q17, Q19,
Q29, Q35 — all 42 reviewed. If Q17 is genuinely non-empty, accept the new truth; the hallucination
role has moved to `probe_no_match_v3`.

**What the audit may change.** Gold, scoring metadata, and — with explicit human adjudication —

**question wording, solely to remove ambiguity**, every change versioned. A genuinely ambiguous
question may instead be excluded from the primary scored benchmark or given multiple acceptable
interpretations. Forcing one answer onto an ambiguous question is worse than versioning it.

**What it may never change.** Training composition. Discovering that Q19 needs process-membership and
then adding a process generator would be the benchmark leaking into training design.

**How Q42 sealing works, stated precisely** — the plan would otherwise read as contradictory:

- **During Phase 28** the audit **may** inspect Q42 questions, recompute golds against the v3 oracle,
  adjudicate ambiguity, and freeze the benchmark. This is benchmark **construction**, not measurement.

- **After Phase 28**, Q42 may not influence dataset generation, prompt design, model config,
  hyperparameters, or any training choice.

- **Q42 scores, predictions and error examples stay sealed until Phase 40**, like every other test
  artifact. Constructing the benchmark and scoring against it are separate events.

**Artifacts.** `probe_42_v3.jsonl`, `PROBE_42_AUDIT_v3.csv`, `taxonomy_v3`.

**Gate.** **Checkpoint 9** — personally approved. Blocks full training, not dataset-code development.

---

## Phase 29 — Global dataset and leakage audit

**Validation.** Six training files, dev sets and nine probes present · **absent:** `probe_geo`,
`probe_relationship`, `D_sql_k0/k5/k25`, `R`, `BDR`, `graph_edges` · held-out split groups absent from
training · OEM-reference guard holds · value/operation/compositional holdouts clean including the
superset rule · exposure ledger asserts zero · no question or paraphrase duplicates · the 42 not
leaked into training · every gold SQL executes with 100% answer match and zero truncation.

**Schema-contract test.** A literal scan of serialized JSONL messages, rendered prompts, few-shot
examples and context strings confirming no experiment-only field appears anywhere model-visible.

**Artifacts.** `DATASET_VALIDATION_v3.md`.

**Gate.** **Checkpoint 10** — the major pre-training gate.

---

## Phase 30 — Micro end-to-end battery

A few items from every family through the whole pipeline: prompt construction, token lengths, SQL
generation, execution, grader, parsers, raw-prediction retention, report generation. Plumbing test,
not scoring.

---

# Part VII — Training under a sealed test set (Phases 31–39)

**The blinding rule.** From here until Phase 40, no one looks at test or Q42 scores. Reviews cover
training loss, **dev** loss, **dev** metrics, runtime, VRAM, checkpoint integrity and technical
failures only. If B's test scores were inspected before D was trained, D would have been configured
downstream of a test-set observation, and the test set would no longer be held out for D.

**What "sealed" means mechanically.** Not a convention — an enforced property:

- **No test or Q42 inference runs at all before Phase 40.** Not "generate then hide" — simply do not
  run it. Prohibiting generation is strictly safer than sealing its output, and it removes any
  question of whether a stored prediction was read, reused, or regenerated. The cost is that all
  test-time GPU work lands in one Phase 40 batch, which is a scheduling matter, not a scientific one.

- No process may print or log test scores, per-item correctness, aggregate counts, pass/fail
  tallies, or failure examples.

- Sealed outputs are written to a dedicated `sealed/` path, hashed on write, and never read by any
  reporting or analysis code before Phase 40.

- The evaluation entry point takes an explicit `--unseal` flag that does not exist in any Phase
  31–39 config. Scoring test artifacts without it is an error, not an option.

- Dev-facing summaries must be generated by a code path that has no access to the sealed directory.
- **Test probe** **contents** **stay quiet too, not only scores.** Any log touching a test or Q42 probe
  before Phase 40 may print counts and hashes only — never example text, gold answers, or failure
  cases. Reading the items is a slower form of reading the scores.

## Phase 31 — Baseline dev evaluation

`base`, `base_ctx_oracle`, `base_sql`, `base_sql_5shot` on **dev**, greedy at temperature 0.

**Dev only — no baseline test inference is run here.** Baselines are re-run against the test suite
in Phase 40 alongside every trained arm. SQL baselines execute against the `train_dev_kb` view, so
prediction and gold share a scope.

**Validation.** `base_ctx_oracle` receives company + process + service + certification facts and fits
the budget · `base_sql` variants use the v3 schema and the shared runtime value catalogue.

---

## Phase 32 — Training smoke tests

Tiny runs for A/B/C/D/BC/BD: trainer reads files, LoRA saves, evaluator loads adapters, no schema
mismatch, no OOM, correct result directories. Not results.

**Gate.** **Checkpoint 11** — pipeline safe for GPU.

---

## Phases 33–39 — Full training

Every adapter starts from the **same pinned base revision** of `Qwen/Qwen2.5-14B-Instruct`. Plain
LoRA, bf16, **no sequential chaining** — never A→B, B→D, or D→BD.

| phase | condition | seeds | question it answers |
|---|---|---|---|
| 33 | `A_cpt` | 1 | Does CPT on raw passages inject facts? |
| 34 | `B_facts` | ≥3 | Does factual SFT improve factual recall? |
| 35 | `C_answers` | ≥3 | Can structured operations be taught as direct answers? |
| 36 | `D_sql` | ≥3 | Does SQL SFT beat `base_sql` and `base_sql_5shot`, and where? |
| 37 | `BC` | 1 | Does facts + direct answers trade off usefully? |
| 38 | `BD_controlled` + `D_repeat_budgetmatched` | ≥3 | At equal supervised-token budget, does splitting supervision between facts and SQL beat spending it all on SQL? |
| 39 | `BD_full` | 1 | What does the complete B+D recipe deliver in practice? |

**Why C is at ≥3 seeds.** Phase 41 lists `C vs base` as a **primary** comparison, and a primary claim
cannot rest on a single adapter. If compute forces a choice, demote C to diagnostic alongside A and
BC — do not leave it primary at n=1. Seeds and claim status must agree.

**Phase 38 is an allocation experiment, not "adding B."** `D_repeat_budgetmatched` reaches its budget
by repeating D, so it controls optimizer exposure rather than information. If `BD_controlled` wins,
the honest reading is **a mixed allocation beat repeating SQL data** — a useful practical finding, but
not "facts help" in isolation. State this in the report, not the conclusion.

**Gate.** **Checkpoint 12** — review dev and technical metrics before each next run. Test stays
sealed.

---

# Part VIII — Unblinding and reporting (Phases 40–42)

## Phase 40 — Unblind: run the frozen test suite once

**Why.** One unblinding, after every model condition is frozen, is what makes the test set a test
set.

**Before unsealing — the no-test-access audit.** Scan every config, log, report, notebook and result
JSON produced in Phases 31–39 and confirm **no test or Q42 inference was ever run** and no test
metric was read, computed or summarized. Because generation itself was prohibited, this audit
checks for the **absence of artifacts**, which is a far easier property to verify than the absence of
a read. **It gates the unseal**; if it fails, the affected conditions must be treated as having seen
the test set and reported with that limitation stated.

**We do.** Generate and score all test predictions in a single pass — every condition, all baselines
included, executing against the `full_kb` view and scored against `full_kb_gold`. Run them
against all **nine** test evaluation families — factual recall, factual paraphrase, structured
held-in, value-held-out, operation-held-out, compositional-held-out, structured paraphrase,
no-match/abstention, and `probe_42_v3` — plus the 30-item general-capability sanity suite, which sits
outside the nine and outside every research claim.

**The sanity suite is reported separately** and carries no GNEM research claim. It answers only
whether fine-tuning damaged basic instruction-following. A large drop is a flag to investigate, not
a result to interpret; it never retroactively changes model selection, since selection is already
frozen.

**Failure accounting.** Every expected item ends in exactly one status: `correct`, `incorrect`,
`generation_failure`, `parse_failure`, `SQL_error`, `timeout`, `truncated_output`, `invalid_output`.
Non-success counts against the denominator. **Hard assert:** `scored + failed == expected probe size`.

**Retention.** For every item: `example_id`, question, raw output, parsed output, generated SQL,
execution result, gold, score, error type, adapter hash, prompt hash. Never scores alone.

---

## Phase 41 — Statistical analysis

**Lead with description, not p-values.** At three seeds the strongest presentation is per-seed
scores, mean ± SD, paired item-level bootstrap effect estimates, effect sizes and exact denominators.
Significance testing is supporting evidence, not the headline. McNemar secondary for predeclared
binary comparisons; Holm correction across primary comparisons.

**Baselines are deterministic; do not invent variance for them.** Per Phase 0 all baselines decode
greedily at temperature 0, so each has exactly **one** inference result and no spread at all.
Trained-arm variation reflects training-seed variability only. Compare each trained seed against the
same deterministic baseline; never pair a baseline "seed" with a training seed, and never report a
baseline standard deviation.

**Required stratifications.**

- `knowledge_exposure` — B's factual recall reported separately for `trained_fact` vs
  `heldout_entity` vs `heldout_value`. A collapsed number would misread deliberate holdout as failure.

- `entity_dependent` — especially for B, C and BC, so unavailable knowledge is not mistaken for
  failed reasoning.

- **Item-weighted** **and** **split-group-weighted** scores, so multi-row companies like Novelis and ZF
  Gainesville cannot quietly dominate. Named `split_group`-weighted, not "company"-weighted, because
  a split group may deliberately contain more than one exact company name (Trenton Pressing /
  Trenton Pressing Inc.) — the label must say what the unit actually is. **Weighting is defined here,
  before any result is seen:** average item scores **within** each split group, then average across
  groups unweighted. Report the group count beside the item count.

**Applies only to entity-attributable probes** — factual recall, factual paraphrase, and any
  item whose subject is a single company. It is **undefined** for aggregate structured questions
  ("how many companies are in Fulton County?"), which belong to no split group; those are reported
  item-weighted only, and the report must not imply a group-weighted figure exists for them. If
  literal company-weighting is wanted later, use exact trimmed `company` and name it as such.

- Attribute, operation family, holdout axis, and seed.
**Denominators everywhere** — `38 / 42 = 90.5%`, never a bare percentage. Report baseline headroom
alongside gains: if `base_sql_5shot` = 95%, then D = 96% is ceiling-limited, not a failure.

**Primary comparisons, predeclared.** B vs `base` and `base_ctx_oracle` (factual) · C vs `base`
(direct-answer structured) · D vs `base_sql` and `base_sql_5shot` (SQL) · `BD_controlled` vs
`D_repeat_budgetmatched` (supervision allocation) · `BD_full` descriptive. A and BC are diagnostic.

**Closed-world policy.** The frozen workbook and database are the evaluation universe. Findings read
"according to the frozen GNEM v3 dataset," never "in the real world." External knowledge never
overrides gold. **v2 vs v3 is historical and descriptive only** — workbook, schema, grader, probes
and holdouts all changed together, so no single factor is isolated.

---

## Phase 42 — Report and archive

**Artifacts.** `REPORT_v3.md`; archive `datasets_v3/`, `adapters_v3/`, `results_v3/`, and
`validation_v3/`. Create or update v3 `ISSUES.md` and `FINDINGS.md` as needed. Historical v2 findings remain preserved in `v2-frozen-reference`; when a v3 finding depends on a historical bug or decision, reference that lineage rather than rewriting v2 history.

**Limitations stated explicitly.** Forced-in OEM-referenced companies and their effect on the test
distribution · skipped multi-row conflicting attributes · oracle-context is an upper bound, not a
retriever · `D_repeat_budgetmatched` controls exposure, not information · general-capability
retention evaluated separately as a regression screen, not as a GNEM research claim · `A_cpt`'s
single-passage rendering and its expected cost on factual paraphrase · `BD_full` meaning the full

**eligible** recipe after holdout and exposure exclusions, not every example the workbook could
produce.

**Full hash chain recorded.** `v2-frozen-reference` commit · Phase 0 freeze commit and dirty-tree state · raw workbook · cleaning-code version · canonical records · split-group map · holdout registry · exposure ledger · `gnem_v3.sqlite` · every train, dev and probe JSONL · every prompt template · context-renderer version · few-shot manifest · base-model and tokenizer revision · training configs · seeds · examples · total and supervised tokens · optimizer steps · adapter hashes · denominators · all final metrics.

---

# Stopped in v3

Latitude/longitude · geospatial training and evaluation · distance/radius/nearest questions ·
`probe_geo` · geo SQL prompts · `D_sql_k0/k5/k25` · relationship and graph training and evaluation ·
`graph_edges` · `probe_relationship` · `R` / `BDR` · recursive-traversal experiments · router
variants · separate cert/process/service recall files · `Certification Count` as a learned target ·
sequential adapter training · aggressive company-suffix normalization for scoring · silent SQL or
prompt truncation · v2 database fallback · test-set inspection before Phase 40.

# Kept for future work

Geo reasoning · relationship and graph reasoning · recursive-SQL dose-response · certification
registrar / expiry / `source_url` reasoning · the certification-definition key · site-level employment
validation · OEM graph normalization · production retrieval/RAG layer. Historical geo/coords/graph implementations remain available through `v2-frozen-reference` and are **not ported into active v3** unless a future protocol explicitly reinstates those experiments.

# Final pre-training checklist

Every line must pass before Phase 33.

1. Source workbook hash recorded; 205 / 18 / 193 confirmed.
2. Canonical cleaned records frozen and hashed; hash chain established.
3. Normalization asserted: `OEM (Footprint)` = 8, `Manufacturing Plant` = 187, `Manufacturing` = 4,
   variant spellings gone, multi-valued cells sorted.

4. Sentinels absent from every question, gold SQL literal and candidate pool; `city`/`county` NULL,
   not sentinel.

5. `split_group` frozen; detector finds no unmapped collision; 70/10/20 split recorded and
   stratification audited; OEM-reference guard derived (not hard-coded) and its companies named.

6. `gnem_v3.sqlite` built and hashed; four tables; zero orphan child rows; DB path from config.
7. Context renderer measured against `input + max_new_tokens <= configured usable context`; no silent
   truncation.

8. Grader task-aware; degenerate-prediction battery passes; `max_rows`, the 24,576 prompt cut, and
   partial-output parsing all removed.

9. Active v3 eval/report stack selectively ported or rebuilt and fixture-validated; no retired component or v2 runtime dependency is reachable.
10. `HOLDOUT_REGISTRY_v3.json` and `FACT_EXPOSURE_LEDGER_v3.json` frozen **before** any dataset was
    generated; per-value exposure asserts zero across examples, targets, system prompts, schema text,
    training-time catalogues, few-shot text, and every other model-visible fine-tuning string. The full
    runtime value catalogue is inference/dev/test-only where permitted.

11. Canonical structured task pool frozen; C and D render from the identical `task_id` set, with
**byte-identical question text and metadata**. Each task carries identical `train_kb_gold`,
    `train_dev_kb_gold` and `full_kb_gold` metadata across both renderings. **Supervision targets
    differ by design:** C targets `train_kb_gold`, D targets `gold_sql`, dev scores against
    `train_dev_kb_gold`, and test scores against `full_kb_gold`. Do not assert equality of targets.

12. All training files, dev sets and probes built, ID-stamped and manifested.
13. **Per-dataset leakage assertions, every training file — not only A.** `A_cpt`: zero held-out or
    dev companies (strongest check, since plain passages carry no split metadata). `B_facts`: no
    dev/test `split_group` present. `C_answers`: targets are `train_kb_gold`, and no
    entity-specific exposure of held-out companies. `D_sql`: no held-out entity literals where
    prohibited. `BC` and `BD`: inherit and re-assert their components' compliance rather than
    assuming it.

14. `MULTIROW_CONFLICTS_v3.csv` enumerates every skipped conflicting pair.
15. `entity_dependent` and `knowledge_exposure` computed on all applicable items.
16. Operation-held-out constructs absent from D's SQL **and** C's metadata.
17. Compositional superset rule verified in both directions.
18. Cross-probe consistency audit passed.
19. Few-shot manifest and all prompt templates frozen and hashed.
20. `probe_42_v3` and `taxonomy_v3` frozen and personally approved; any reworded question versioned.
21. Every gold SQL executes, 100% answer match, zero truncation.
22. Schema-contract scan confirms no experiment-only field is model-visible, and a literal scan of
    serialized training messages/prompts confirms no held-out entity/value leaks through system text,
    schemas, catalogues, few-shot examples, or rendered context.

23. Seed policy, blinding rule and primary-comparison hierarchy declared in writing.
24. `VALUE_HOLDOUT_COST_v3.csv` written; no held-out value drops its attribute's remaining training
    coverage below the registry threshold, **and the cumulative attribute-level floor holds after
    all holdouts**; per-split support (`total` / `train` / `dev` / `test`) recorded per value.

25. **Scope discipline holds:** no training file contains `full_kb_gold` or `train_dev_kb_gold`;
    C's targets are `train_kb_gold` throughout; dev scores against `train_dev_kb_gold`; only test
    gold and the deployed SQLite mirror read `full_kb`. Every KB call site names its scope, and a
    static check confirms no training generator can reach `full_kb`.

26. Every ranking/top-k/argmax gold SQL carries a total tie-break, so gold order is deterministic.
27. `knowledge_exposure` is multi-label with overlap counts reportable, and its combination
    invariants are asserted: `no_match` exclusive with all others; `heldout_entity` +
    `heldout_value` allowed; `trained_fact` never co-occurring with either holdout label.

28. C's seed count matches its claim status: ≥3 if primary, otherwise demoted to diagnostic.
29. `A_cpt` uses **one canonical passage per row**, with passage count and LM-token budget reported,
    and the expected paraphrase-robustness cost recorded as a design consequence.

30. `BD_COMPOSITION_v3.md` shows B attribute mix and D operation mix for both BD arms.
31. `MODEL_SELECTION_LOG_v3.md` exists and covers every dev-driven configuration decision.
32. Sealing mechanism in place: **no test or Q42 inference runs before Phase 40**, `--unseal` flag
    absent from every Phase 31–39 config, dev summaries produced by a code path with no
    sealed-directory access, and pre-Phase-40 probe logs limited to counts and hashes.

33. SQL execution is scope-bound: three views built and verified, `run_sql` refuses to run without an
    explicit scope, and prediction and gold always share one — `train_dev_kb` at dev, `full_kb` at
    test.

34. Adapter retention decided: all 18 per-seed adapters kept and archived.
35. Compute budget confirmed against the 18-run matrix, or `C_answers` demoted to diagnostic in both
    Phase 0 and Phase 41 in the same edit.

36. The 30-item general-capability sanity suite is frozen and hashed.
37. Split-group-weighting rule (unit = `split_group`, average within then across) declared before
    any result exists, and scoped to entity-attributable probes only.

38. Realized split reported — split groups, exact companies and rows per side — rather than forced
    to hit 70/10/20 exactly.

39. Micro end-to-end battery and training smoke tests green.
