# Development decisions — V3 A-002

## 2026-09-11: micro inference output contract, before full baseline runs

Initial micro runs are retained under results_v3/micro/. The oracle-context model returned correct source values inside explanatory prose, which the conservative exact parser rejected. The question referenced a record number absent from the context. These are harness/prompt findings, not final model scores.

Revision: include the source row identifier in oracle context; request JSON scalar/list outputs consistently for all model-only and context conditions, while preserving SQL output requirements for SQL conditions. Freeze the revised templates before the new development runs. Training targets and protected test outcomes did not inform this change. Keep strict value/set parsing and report parse failures separately; no substring-containment correctness was introduced.

Q42 approval remains pending at the user's explicit direction. Final training is not released. All smoke runs are diagnostic two-step runs and cannot count toward the 18 final runs.

## Shared SQL catalogue correction

Static protocol comparison found the initial SQL runner omitted the shared runtime vocabulary required by README Phase 31. Retain earlier runs as pilots, not protocol-complete baselines. The corrected catalogue contains full-source categorical/process/service/certification vocabularies without company-to-value associations and is identical for SQL conditions. Freeze its hash with prompts before corrected runs. No model score motivated vocabulary selection; the allowed fields are explicit in the builder.

## Smoke-test sampling coverage correction

The first two-step smoke suite sampled the first eight examples. Because BC/BD concatenate sources, this did not exercise every component of each mixture. The first suite and adapter reload evidence are retained in archive/smoke_prefix_pilot_2026-09-11/. Repeat the smoke suite with eight deterministic positions spanning each complete recipe and four positions spanning development targets; record exact indices. This is an engineering test change, not final-model selection.

## Development-driven parser revision A002.2 — 12 September 2026

Bounded matched-quote removal and requested-key object unwrapping separate semantic accuracy from original JSON format compliance. Wrong values, extra/missing members, boolean substitutions and nonstandard JSON constants remain rejected as specified. Thirty parser tests pass. Rescoring retained dev outputs recovers 30 quote-wrapped answers and one named object: oracle semantic accuracy 245/255 (96.1%), previously 214/255. Ten boolean-surface differences remain incorrect. SQL verdicts unchanged; SQL format is N/A under the JSON answer contract. No model inference repeated or protected scoring performed. Versioned report: results_v3/dev/REPORT_A002_r2.md; full changes and code hashes accompany it.

## 2026-09-12: structured development set replaced before any final run

The 51 questions in `dev_structured_v3.jsonl` all take the form *"Which recorded
company is named X and has &lt;field&gt; recorded as V?"* with gold `[[X]]`. The complete
answer is quoted inside its own question, so the task is solvable by echoing the
prompt: both SQL baselines scored 51/51, the set could not discriminate between arms,
and `train_v3.py` was using it as the checkpoint-selection eval signal for
`C_answers`, `D_sql`, `D_repeat_budgetmatched` and half of `BC`/`BD_*`.

`dev_structured_r2_v3.jsonl` replaces it for selection: 120 tasks anchored on
attribute values observed in held-out development records, never naming a company.
Join arity 0/1/2 (23/73/24), 96 set answers (sizes 1-25, median 9) and 24 counts
(1-134). Built by `phase17b_build_dev_structured_r2.py`, validated by
`dev_structured_r2_tests.py` (17 checks).

Construction respects the frozen holdouts, asserted fail-closed: no held-out
operation construct, the `{certifications, processes}` composition excluded, no
test-split company in any question or gold answer, and no `gold_sql`,
`logical_fingerprint` or question colliding with training, the task pool, the
reserved few-shot sources or any sealed probe. 189 candidates were skipped precisely
because their gold SQL reproduced a trained query -- selecting on those would have
rewarded memorisation. Split metadata is corrected: `make_task`'s hardcoded
`split: "train"` is removed in favour of `task_split` and `anchor_entity_split`.

Development targets now reuse Phase 13's frozen `render_answer`, so a count renders
as *"The answer is N."* rather than the previous *"The companies are: 3."*.

No model outcome informed any of this: no inference was run, the old set and every
result computed from it are preserved unchanged, and the change was driven by the
structure of the questions alone. Q42 approval remains pending and final training
remains unreleased.

## 2026-09-12: final-training release gate strengthened

The gate accepted any file with `approved: true` and an **empty** `sha256` map, which
froze nothing, and it never checked which seed was being run. It now requires an
approved release that pins all 22 required inputs by hash with no drift, records
`q42_approval: approved`, and pre-declares the exact `(variant, seed)` pair being run
in a `run_schedule` of exactly 18 entries meeting each arm's minimum seed count.
`release_gate_tests.py` covers 17 rejection paths and asserts no approved release
exists in the repository.

The 18 pairs are pre-registered in `validation_v3/PROPOSED_RUN_SCHEDULE_A002.json`
(seeds 61/62/63 for the five primary arms, 61 for the three diagnostic arms; 61 is
the seed already fixed by the smoke suite, so no seed was chosen after seeing an
outcome). That file is explicitly **not** a release and carries no `approved` key.

## 2026-09-12 (later): two gaps found in review, corrected

Independent review of the above found two defects. Both are fixed, and both now have
permanent regressions. Nothing was accepted on the strength of the first pass.

**1. Development anchoring was not what it claimed.** 14 of the 120 tasks had no
development record satisfying their *combined* predicate: each value was drawn from
dev data separately, but the conjunction described only training or test records.
Execution scope (`train_dev_kb`) meant no test answer could leak, so this was a
provenance defect rather than contamination — but "anchored on a held-out development
record" was false for those tasks. The builder now requires the full predicate to
match at least one dev record, retains the matching row IDs in `dev_anchor_row_ids`,
and rejects unanchored candidates at generation (26 skipped). All 17 development rows
appear as anchors. Task count is unchanged at 120 because the mixed generator
backfills from its ordered candidate list.

**2. The proposed seed schedule was not enforced.** The release gate checked run
count, arm minimums and membership *within the submitted release*, but never compared
it against the separately recorded proposal — so substituting seed 999 for 62 passed.
The gate now requires `run_schedule_source` to name the proposal, pins its sha256, and
demands exact agreement between the release's pairs and the pre-registered pairs.
Seeds must be integers in [0, 2**32-1]; `bool` is rejected explicitly because it is an
`int` subclass and `True` would silently seed as 1. Five previously-accepted mutations
(999, `True`, -5, 2**40, `"61"`) are now refused, as are a missing source and a wrong
schedule hash.

**Reporting corrections.** `anchor_entity_split` listed the splits of all matching
records while reading as though it identified the anchor; it is replaced by
`dev_anchor_row_ids` (the actual anchors) and `matching_record_splits` (descriptive
only). The scalar-plus-child queries are now described as **new combinations of
familiar operations** rather than as in-distribution: both halves appear in training
individually, their conjunction does not appear in the pool, and whether a model
generalises to the combination is part of what the set measures.

**Outstanding.** The published baselines describe the legacy 51 questions. The r2 set
has no baseline evaluation yet, so no score in the repository characterises it.
`infer_dev_v3.py --structured r2` and `EVALUATION_INPUT_MANIFEST_A002_r2.json` are in
place to run it; the frozen A002 manifest was not edited. No inference was run.

## Current continuation: corrected dev baselines and sampling

Ran four unchanged-base conditions against the corrected dev input with isolated protocol_A002_dev_r3 outputs. Factual base 0/255, oracle 245/255; structured base 0/120, SQL and SQL-five-shot 120/120. These are a changed benchmark, not a model-improvement comparison. Preserved all prior raw predictions and inputs.

Changed final partial repetition to proportional source-token allocation by join arity, retaining all sources. Archived old mixtures; current controlled/repeated budgets 94,417/94,440. Rebuilt audits, checked full-field coverage. Existing smoke adapters describe old inputs, not smoke validation of the new mixtures.

D_sql rehearsal exercises final accumulation and epoch selection, 6 steps; finite losses and deterministic best-adapter reload checked. Added exact structured result grading and output-contract helper. Base floor sanity 30/30; does not establish broad capability. New helper integration into final sealed evaluation remains open. No final training, approved release, Q42 approval, commit or push performed by this continuation.
