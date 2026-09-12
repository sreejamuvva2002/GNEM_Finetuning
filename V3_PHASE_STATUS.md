# V3 phase status — A-002 runtime verification

There are 43 phases (0–42). Status below separates built artifacts, engineering checks, model smoke tests and final scientific results. No final fine-tuning run or protected test evaluation has been completed.

**Current gate:** Q42 approval is pending at the user’s explicit direction. Continue pre-training review without treating smoke tests or dev scores as final results. Broader analytical dev coverage, final scorer integration and benchmark adjudication remain open.

| Phase | Purpose | Status | Evidence / limits |
|---:|---|---|---|
| 0 | Freeze the v3 specification | Specification amended | A-002 active; final training release pending. |
| 1 | Freeze the source workbook | Revalidated | Original workbook preserved: 205 records, 193 exact names, 18 source fields. |
| 2 | Clean, normalize, and freeze canonical records | Revalidated | Canonical records reproduce source normalization and audit. |
| 3 | Identity, split groups, and the train/dev/test split | Revalidated | 148 train / 17 dev / 40 test records; original group assignments retained. |
| 4 | Loader and data contract | Revalidated | Complete model-facing source fields; Certification Count internal only. |
| 5 | Build gnem_v3.sqlite | Revalidated | Byte-identical database; all memberships retained; eight fault tests pass. |
| 6 | Context renderer and token budget | Revalidated after runtime correction | Oracle context includes source record number; all budget checks and 16 fault tests pass. |
| 7 | SQL execution and grading | Corrected and tested | 81 existing checks and six amendment tests pass; scalar aliases and SQL literals handled; execution deadline tested. |
| 8 | Build the v3 evaluation and reporting stack | Stack revalidated | 94 synthetic stack checks; four statistics regressions; real dev records verified through canonical schema. |
| 9 | Freeze the Holdout Registry and Fact Exposure Ledger | A-002 registry built and checked | No deliberate value exclusions; entity/operation/composition holdouts retained; historical approval preserved. |
| 10 | train_A_cpt_v3.jsonl | Rebuilt; coverage checked | 148 complete record passages with qualified missingness and record provenance. |
| 11 | train_B_facts_v3.jsonl | Rebuilt; coverage checked | 2,149 factual QA items; all 2,220 eligible row/attribute observations mapped, including conflicts and unknowns. |
| 12 | Canonical structured task pool | Rebuilt; execution checked | 1,326 tasks; all 3,978 scoped gold executions match. Actual joins and SQL metadata checked. |
| 13 | train_C_answers_v3.jsonl | Rebuilt; paired with D | 1,311 answer-supervised structured tasks. |
| 14 | train_D_sql_v3.jsonl | Rebuilt; paired with C | 1,311 SQL-supervised tasks; actual-operation eligibility and membership checks pass. |
| 15 | train_BC_facts_answers_v3.jsonl | Rebuilt; source checked | 3,460 B+C items; all messages scanned. |
| 16 | BD datasets and budget manifests | Rebuilt; source and label budgets checked | BD_full 3,460; BD_controlled 3,505; repeated-D 2,718. Every B/D source retained; shifted assistant-label budgets verified. |
| 17 | Dev evaluation sets | Dev sets built; scope verified | 255 factual and 51 entity-conditioned structured filters. Broader analytical dev coverage remains a limitation before final selection. |
| 18 | probe_fact_recall_v3.jsonl | Probe inputs built | 2,820 factual questions; no protected model scoring. |
| 19 | probe_fact_paraphrase_v3.jsonl | Probe inputs built | 2,820 factual paraphrases; question overlap checks pass; no protected model scoring. |
| 20 | probe_structured_train_v3.jsonl | Diagnostic inputs built | 1,306 held-in structured questions after reserving five-shot sources. |
| 21 | Value-held-out probe | Amended exposure probe built | 130 value-exposure tasks; no fabricated deliberately-unseen-value claim. |
| 22 | Operation-held-out probe | Probe inputs built | 15 operation-heldout tasks; no protected model scoring. |
| 23 | Compositional-held-out probe | Probe inputs built | 401 composition-heldout tasks; required join arity seen in training. |
| 24 | Structured paraphrase probe | Probe inputs built | 1,305 structured paraphrases; final scorer integration still required. |
| 25 | probe_no_match_v3.jsonl | Probe inputs built; parser regressions pass | 20 no-match items. Final separate hallucination-avoidance and valid-abstention reporting still required. |
| 26 | Cross-probe holdout consistency audit | Construction checks pass | Heldout operations/compositions and reserved few-shot overlap checked; final input/scorer gate remains before test release. |
| 27 | Freeze few-shot manifest and prompt templates | Prompts and sanity screen built | JSON output contract, source-ID context and shared SQL catalogue recorded; 30-item sanity screen not yet scored. |
| 28 | Revalidate the 42 business questions | Pending user approval and adjudication | All 42 candidate golds constructed. User explicitly kept approval pending; old/new entity/numeric deltas and ambiguity review remain open. |
| 29 | Global dataset and leakage audit | Engineering checks pass; release gate open | Coverage and scoped golds verified. This is not a full training release. |
| 30 | Micro end-to-end battery | Real-model micro checks pass | Factual/context and SQL pilots retained; six SQL cases cover count, top-k, no-match, composition, grouping and multipart. Not final quality estimates. |
| 31 | Baseline dev evaluation | Four current dev baselines completed | All expected records verified; limitations and exact-score denominators in results_v3/dev/REPORT_A002_r2.md. |
| 32 | Training smoke tests | Representative two-step smoke suite passes | All eight recipes; finite losses, nonzero LoRA updates, identical reload logits. Initial prefix-only pilots preserved separately. |
| 33 | Train A_cpt | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 34 | Train B_facts | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 35 | Train C_answers | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 36 | Train D_sql | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 37 | Train BC | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 38 | Train BD_controlled and D_repeat_budgetmatched | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 39 | Train BD_full | Not started | Final independent runs require Q42 approval and the completed pre-training release. Smoke adapters do not count. |
| 40 | Unblind: run the frozen test suite once | Not started | Protected scoring, final statistics and archive follow completed final training and selection freeze. |
| 41 | Statistical analysis | Not started | Protected scoring, final statistics and archive follow completed final training and selection freeze. |
| 42 | Report and archive | Not started | Protected scoring, final statistics and archive follow completed final training and selection freeze. |

Current evidence: [coverage](validation_v3/resumption/FULL_FIELD_COVERAGE_A002.json), [actual trainer labels](validation_v3/resumption/TRAINER_LABEL_AUDIT_A002.json), [representative smoke results](validation_v3/resumption/SMOKE_TRAINING_RESULTS_A002.json), [adapter reloads](validation_v3/resumption/SMOKE_RELOAD_A002.json), [verified dev baselines](results_v3/dev/REPORT_A002_r2.md), and [pending Q42 review](validation_v3/Q42_REVIEW_A002.md).

Checks are agent-run, not an independent human audit. Earlier manifests describe historical snapshots; the current runtime manifest records new hashes. No guarantee of error-free implementation is claimed.

Current pre-training limitations and configured-step corrections: [gate register](validation_v3/PRE_TRAINING_GATES_A002.md). The r2 report supersedes r1 scoring; historical evidence remains preserved.
