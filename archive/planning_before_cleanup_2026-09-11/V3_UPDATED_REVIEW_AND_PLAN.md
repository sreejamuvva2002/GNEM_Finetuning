# V3 updated repository review and implementation plan

> **Latest field exception:** The user has authorized excluding Certification Count from model-facing training. Keep it in source/canonical data for validation. Complete certification lists, processes, services and all other source fields remain covered under [A-002](PROTOCOL_A002_FULL_FIELD.md). This supersedes earlier count-inclusion requirements below.

> **Latest user decision:** Finish the original eight-variant V3 study with full-field training now, under [A-002](PROTOCOL_A002_FULL_FIELD.md). Earlier instructions here to defer all full-field changes are superseded. The broader analytical FT-1/FT-2 follow-on remains later. See [current phase status](V3_PHASE_STATUS.md).

> **Execution-order update — original V3 first:** The user has directed us to finish the existing README experiment, including all eight fine-tuning variants and its original baselines, before implementing the broader plan below. [V3_EXECUTION_ORDER.md](V3_EXECUTION_ORDER.md) is the current sequencing reference. The proposed scope replacement and Stage 1/Stage 2 milestones below are deferred to a separately versioned follow-on study. Verified defects still need correction before the original experiment runs. This notice supersedes the earlier immediate-replacement recommendation in this document.

Review date: 11 September 2026. Reviewed checkout: `8e7196e0e58d6ebcb35d7a14944146039f4c912f`.

**Decision:** Keep the source-preservation, normalization, identity-audit, deterministic-gold, and evaluation-accounting foundation. Revise the experiment around the user's current objective: full-workbook coverage, model-only factual and analytical fine-tuning first, tools later. Do not launch full training from the existing generated datasets.

This document updates the recommendations in [the earlier review](REPOSITORY_REVIEW_2026-09-11.md) and [the initial goal handoff](V3_GOAL_AND_V2_LESSONS.md). Their technical evidence remains useful; their tool-first ordering and old eight-arm research assumptions do not describe the newly requested Stage 1. This is a concrete review and implementation plan, not a claim that changes below have been implemented. README.md, CLAUDE.md, phase approvals, source data, and training artifacts were not changed by this review.

## 1. Final objective and experiment

Develop and rigorously evaluate a fine-tuned language model that understands verified EV and battery supply-chain company data, answers factual and multipart analytical questions, and assesses plausible supplier alternatives, local product replaceability, and supply-chain vulnerabilities. First establish its capabilities without external tools, comparing it against the unchanged base model and distinguishing supported conclusions from missing or uncertain evidence.

| Stage 1 condition | Training | Evaluation |
|---|---|---|
| Base | None; unchanged pinned base model | Same questions, output requirements, information access, and decoding policy as fine-tuned models |
| FT-1 | Factual QA covering the complete source dataset, including source-qualified numeric facts, ambiguity and missing-information handling | Company facts, lists, aggregates, and analytical tasks, broken down by family |
| FT-2 | The same factual coverage plus verified filtering, comparisons, grouping, ranking, multipart calculations, supplier matching, and evidence-limited analysis | Identical evaluation to FT-1 |

Both fine-tunes start independently from the same pinned model revision. Start with one seed per recipe to verify the pipeline and develop the configuration; complete three seeds per final recipe for the reported comparison. Six final fine-tuning runs, not six training recipes. Pilot runs only count toward those six if they use the final frozen recipe/configuration; otherwise retain them as development history. Retain every final adapter. Do not chain adapters or choose the luckiest seed and describe it as representative.

Use the existing Qwen2.5-14B-Instruct/LoRA choice as the starting candidate to minimize unrelated changes. Confirm hardware, installed dependencies, and supported template/masking behavior before fixing final hyperparameters. There is no basis yet to prescribe optimal epochs or learning rate.

FT-2 has more kinds of supervision. If it also consumes more training tokens/compute, the comparison measures the practical recipes together, not a clean causal effect of analytical examples. Preserve complete factual coverage in both; record actual supervised tokens, fact exposure, steps and compute. A matched-budget control can follow only if a stronger causal claim is required. Do not drop companies just to match a budget.

**No tools at model inference in Stage 1.** Offline Python/SQL used by researchers to generate and verify gold answers remains appropriate. Separately score closed-book questions and evidence-provided questions, where supporting records are explicitly included in the prompt for every model. Evidence-provided performance is not evidence of memorization.

## 2. Review coverage and limits

The current inventory covers 178 existing project/evidence files before new review artifacts. All 81 files in the earlier project review match their recorded SHA-256 prefixes; all 94 files in the historical training audit's full-hash manifest also match. No earlier reviewed implementation has changed. The additional documents include the initial V3 goal and historical-audit material. See the [complete file inventory and dispositions](review_v3_updated_2026-09-11/FILE_REVIEW.md) and [machine-readable inventory](review_v3_updated_2026-09-11/file_inventory.json).

I reused the prior source review for byte-identical files and re-read the current execution contract, latest phase handoff, data transformations, generators, eligibility, budgets, and grading paths relevant to the changed objective. Every inventoried Python file was parsed; every JSON/JSONL/CSV artifact was read and parsed. Both workbook sheets and the workbook package were inspected, all 3,690 data-cell positions were compared with canonical records, and all 1,090 stored training-scope SQL answers were re-executed. Existing tests ran in a disposable copy, not against mutable experiment artifacts.

This is not a claim that every sentence of the two long chat transcripts is factually correct or newly reread line by line. They remain historical context, not implementation authority or verified scientific results. Installed dependency trees, Git internals, and bytecode caches are excluded from the project-file inventory. Images/PDFs are historical plotted artifacts, not additional training results. No new model training, checkpoint replay, inference, or sealed test/Q42 scoring was performed. Workbook preservation does not independently verify the underlying real-world claims.

## 3. Excel completeness: verified observations

Source: [GNEM_Final_Combined_Dataset.xlsx](kb/GNEM_Final_Combined_Dataset.xlsx).

- SHA-256: `a8a4ca5c72211e7e2e32bbf418873f86677b7fb1264d2c657955b3fee008b034`; matches the frozen source manifest.
- `GNEM Combined`: 205 records, 18 columns, 193 exact trimmed company names.
- `Certification Key`: empty; there is no hidden credential dictionary to import from it.
- No formula cells, worksheet hyperlinks, hidden rows, or comment/external-link/embedded-object package parts were found by this check.
- All 205 row IDs and all 18 source fields are represented in canonical records. There are 277 raw-to-canonical changed cells; every changed row/field has a cleaning-audit entry. This establishes accounted-for transformations, not that the canonical text is a byte-for-byte copy of Excel.
- Employment and Certification Count are unchanged in every row. The source contains no latitude/longitude columns.

The [cell evidence](review_v3_updated_2026-09-11/workbook_cells.json), [all changed cells](review_v3_updated_2026-09-11/cell_changes.json), and [audit results](review_v3_updated_2026-09-11/audit_results.json) make this review reproducible.

| Source field | Nonblank source rows | Changed canonical cells | Required treatment |
|---|---:|---:|---|
| Record No. | 205 | 0 | Preserve source identity; do not treat it as a company ID |
| Company | 205 | 0 | Preserve exact source spelling and explicit alias relationships |
| Category | 205 | 3 | Preserve raw label alongside normalized category |
| Industry Group | 205 | 0 | Preserve and document vocabulary |
| Location | 202 | 3 | Preserve blanks/raw values; separate derived geography and interpretation |
| Address | 204 | 1 | Preserve complete text, including out-of-state records |
| Primary Facility Type | 205 | 11 | Preserve raw and normalized forms |
| EV Supply Chain Role | 205 | 0 | Preserve source claim and meaning |
| Primary OEMs | 179 | 26 | Preserve source blanks; do not invent commercial relationships |
| Supplier or Affiliation Type | 179 | 26 | Preserve uncertainty and source values |
| Employment | 205 | 0 | Retain all observations; clarify reporting scope before business aggregates |
| Product / Service | 205 | 0 | Preserve complete text; add reviewed product mapping separately |
| Processes | 205 | 134 | Preserve raw lists and normalized membership |
| Services | 205 | 36 | Preserve raw lists and normalized membership |
| EV / Battery Relevant | 205 | 0 | Preserve label and classification context |
| Classification Method | 205 | 0 | Preserve methodology metadata; do not present a method as independent verification |
| Certifications | 171 | 37 | Preserve source entries and blank-evidence status; distinguish credential types |
| Certification Count | 205 | 0 | Preserve recorded count; label it as recorded entries, not verified active qualifications |

**Current training is not complete-workbook training.** It uses only 148 rows / 141 exact names. Dev adds 17 rows, and test adds 40. B produces 2,011 examples and skips 21 company/attribute candidates because of value holdouts, 23 because of conflicts, and 60 because of missing/sentinel values. A omits whole fields in 6 process, 2 service, and 13 certification row passages. Certification Count is intentionally excluded from model-facing records, factual QA, and SQL schema. These were deliberate old-protocol choices, not unexplained Excel deletion; they conflict with the new comprehensive-coverage goal if carried forward unchanged.

## 4. What is good and should be retained

- The original workbook is frozen by hash. The source manifest identifies both sheets, all columns, and the company-count distinction.
- Canonical records retain the entire row population, transformations are logged, employment is preserved, and primary-OEM/affiliation blanks are not filled from sibling records.
- OEM label normalization already handles `OEM Footprint` versus `OEM (Footprint)`. Do not assume label normalization alone resolves model identity mistakes.
- Process/service/certification membership is represented in child tables rather than substring matching. Current counts are 555 / 290 / 662 child rows respectively.
- Explicit KB scopes, read-only database access, and separate record/name/split-group concepts provide useful infrastructure. The old split membership must be reconsidered, but the explicit-access design should survive.
- The C task pool and deterministic gold computations are reusable foundations for direct-answer training. All 1,090 training-scope stored answers reproduce in the new check.
- Existing grading distinguishes sets, scalars, ordered answers, multipart requirements, failures and truncation. Reuse the accounting principles while implementing natural-language answer parsing and analytical rubrics.
- V2 evidence is archived with raw logs and a reproducible mask reconstruction. Keep it independent of the V3 runtime.

There are no completed V3 model results in the checkout. Files under `validation_v3/fixtures_v3/` contain synthetic plumbing checks. Logs under `review_training_2026-09-11/` are historical V2 evidence.

## 5. Changes required before Stage 1 training

### A. Reconcile the protocol and actual status

README.md still defines A/B/C/D/BC/BD variants, literal/company holdouts, operation holdouts and tool baselines. CLAUDE.md names current phase 17 / last completed 16 / next phase 18. The latest handoff contains plans for unresolved corrections, not proof those corrections were implemented.

Record the model-only two-variant plan as a versioned amendment and map the old phases to the new milestones below. Preserve the old protocol and artifacts for provenance. Update active references and status together after the applicable work is verified. Do not silently rerun old generators under new semantics while keeping their old manifests/certificates.

### B. Separate source completeness, interpretation, and training exposure

**User-confirmed coverage requirement:** No Excel field is excluded as a training category. Certifications, processes, services, products, employment, Certification Count, and every other source field must remain represented. All 205 records and 18 fields remain in the preserved source dataset. Both FT-1 and FT-2 must cover every training-eligible observation; analytical supervision is additional in FT-2.

Explicitly designated dev/test or research holdouts are permitted. They are the only planned data-exposure exclusions, must be selected before training, and must be recorded by source record/fact, field, reason, evaluation purpose and affected examples. Do not carry forward the old exclusions automatically. No holdout may accidentally eliminate an entire required field from training; report remaining record and term coverage for each field. The exact holdout selection and size remain to be specified.

For every training-eligible record, preserve its complete process, service and certification lists in suitable supervision. If a specific term is deliberately held out as unseen, do not remove it from an answer and present the shortened list as complete. Record the affected complete-list examples as explicit holdout exclusions, including the collateral facts they withhold. Prefer question/composition or whole-record holdouts when they avoid this loss of field coverage.

Conflicts and missing values are not automatic skip reasons. Represent conflicting observations with source-record attribution, and missing information as unknown/unprovided evidence. Include Certification Count as the workbook's recorded entry count, not proof of that many valid current certifications. Retain source record identifiers and classification metadata in provenance and appropriate record-level examples.

**Coverage gate:** Every source observation must be mapped to either training supervision or an explicitly declared holdout; there must be zero unexplained omissions. Separately verify every non-held-out process/service/certification membership reaches the final rendered examples and survives actual trainer preprocessing. Coverage must be checked for FT-1 and FT-2 independently, before and after tokenization, masking, truncation, packing and sampling. No single prompt needs to contain the whole workbook.

Create a raw cell/observation layer with workbook hash, sheet, cell, source record ID, raw value/type and missingness. Keep the original workbook permanently. Store normalized values as additional representations with versioned transformation rules. Lists may be deduplicated for set reasoning, but their raw order, spelling and occurrences remain recoverable.

Introduce a coverage ledger linking each source cell/fact to its interpretation and actual rendered training examples. Every source field, including Certification Count and classification metadata, must be accounted for. Not every metadata field needs an artificial standalone QA; it must remain accessible through provenance or an appropriate record question. Every meaningful company observation should receive suitable supervision, including explanations of unresolved conflicts and missing evidence.

Do not silently exclude a source claim merely because it is uncertain. Preserve and teach it as “the workbook records X; scope/verification is unavailable.” Avoid teaching it as established current reality. A source blank can support “not supplied in this workbook,” not “the company has none.” The existing missing-value interpretations are annotations, not additional raw evidence.

### C. Resolve identity and scope before aggregate gold

Keep 205 source records, 193 exact-name identities and 186 existing leakage groups distinct. Nine repeated-name groups contain 50 conflicting company/attribute pairs across all splits. None should be automatically interpreted as multiple sites; the earlier audit found only one recorded address per repeated-name group. Comments describing them as different facilities need correction.

For conflicting fields, retain each row observation and its source ID. Answer company-level questions with the conflict unless independent evidence resolves it. Scope record-specific QA explicitly. Do not teach a single unexplained number or merge contradictory relevance labels.

Employment values such as TI Fluid Systems 80 versus 19,600 or ZF Gainesville 170,000 / 17,500 / 106,100 need scope/date/source verification before totals are described as Georgia employment. Until resolved, allow clearly labelled calculations over recorded observations or explain that the requested business aggregate is unsupported. Employment is not production capacity. SUM(DISTINCT employment) does not solve entity duplication.

Preserve out-of-state addresses; inclusion in a Georgia supply-chain workbook does not prove a Georgia production site. Qualification must distinguish company-level capabilities from co-located site capabilities. A company-level intersection across records cannot establish that one site has both attributes.

### D. Change the split strategy for the full-data objective

Recommended default: expose all curated workbook observations during factual training and hold out independently authored evaluation questions, analytical task instances, requirement combinations, and scenario families. The user also permits explicitly declared record/fact holdouts where needed for testing; if selected, expose all remaining observations and report those exclusions and their coverage impact separately. Use separate train/dev/test manifests for tasks. All paraphrases of an analytical task must stay together; deduplicate normalized questions and logical fingerprints across splits. Known-fact recall paraphrases should be labelled as recall, not as unseen-fact generalization.

This deliberately allows underlying company facts to be shared with evaluation: learning those facts is the stated objective. It does not permit training on protected evaluation questions/answers or selecting recipes from final-test performance. If additional evidence-provided scenarios are included, split scenario families and their derivations together. Log exposure separately for FT-1 and FT-2.

If all workbook companies are exposed, do not claim unseen-company results for them. If an explicit entity holdout is selected, exclude its relevant exposure consistently from both recipes and label its results separately from known-company recall; it can be evaluated within the same six-run comparison. A claim comparing full-data training against entity-held-out training would require additional independently trained conditions. The current plan does not require that additional comparison. Never change what the old `full_kb` scope means in place. Introduce a versioned full-workbook training snapshot and task registry so old experimental claims remain interpretable.

### E. Expand the direct-answer curriculum

The current C/D pairing has 1,008 eligible tasks: 280 contain COUNT, but none contain SUM/AVG/MIN/MAX/GROUP BY/HAVING/LIMIT/OR/NOT/WITH/UNION. No current C/D training example has a multipart answer type. A question with two predicates is not the same as a question requesting several outputs. Existing `render_answer` handles only a company set or scalar answer.

Reuse B and C generation patterns, but rebuild FT-1/FT-2 targets against the new source scope. Do not merely concatenate today's B+C and call it the new complete recipe. Add explicit answer-part metadata, constraints, scope, units, missing-value policies, ranking tie rules and independent deterministic gold checks. Include exact/approximate quantities only where their interpretation is valid. Add no-match, insufficient-evidence, ambiguous-identity and conflicting-observation examples rather than skipping all such cases.

FT-2 should include:

- factual contrasts between similar companies, labels and capabilities;
- multi-condition filtering and complete company lists;
- counts of distinct named companies versus counts of records, explicitly distinguished;
- groups, ordered rankings, extrema and scoped arithmetic;
- multipart answers with every requested result and a concise supported explanation;
- supplier alternatives, replaceability, and vulnerability scenarios with explicit evidence and uncertainty.

Use independently verified target computations, not a second LLM's agreement as ground truth. Generated paraphrases and proposed explanations need evidence checks. Keep explanations concise and externally checkable; long synthetic reasoning narratives are not required.

### F. Bound business-analysis claims by available evidence

| Requested capability | Existing workbook helps with | Additional evidence or explicit limitation needed |
|---|---|---|
| Alternative suppliers | Categories, product/service text, processes/services, credential entries, locations | Lost component specification, material/process requirements, required qualification, lead time, volume and available capacity |
| Hard-to-replace products | Coverage of products and capability matches within this dataset | Reviewed product taxonomy, technical substitutability, independent suppliers, switching constraints and capacity |
| Import dependence + few qualified suppliers + limited local capacity | Local candidate coverage within the recorded sample | Product-level import exposure, qualification evidence, production units, utilization/available capacity, dates and population coverage |

Do not infer import dependence from ownership, capacity from employment, or qualification from a certification keyword alone. Few suppliers in 205 records is not proof of few suppliers across Georgia. The correct answer may be a provisional shortlist plus missing qualification checks, or a statement that all three risk dimensions cannot be ranked from this workbook.

For Stage 1 evidence-provided tasks, supplied verified tables or clearly labelled hypothetical scenarios can test this reasoning without tools. Hypothetical capacities/import shares must never become training facts about real companies. The three questions supplied in the conversation are capability requirements/development examples; use fresh independently constructed questions for the protected final evaluation.

## 6. Existing defects: fix, reuse carefully, or defer

| Finding | Current evidence | Required disposition |
|---|---|---|
| A006 exact-ID provenance incomplete | Separate A/B/C/D/BC/pool manifests absent; repeated-D mappings are wrong | New FT-1/FT-2 and evaluation manifests must map exact IDs, source cells/tasks, ordering/multiplicity and upstream hashes. Repair old repeated-D mapping only if that experiment is revived. |
| A007 mixture scans incomplete | BC scans only message indexes 0–2; current files themselves scan clean | Scan every model-visible message and final template output in all new pipelines, with stale-source and injected-extra-message tests. |
| A008 reporting mismatch | Controlled BD report says full B is anchor, but B is sampled | Generate new composition and exposure reports from actual retained data. Old report should be labelled stale; old BD is not Stage 1's recipe. |
| A009 JOIN metadata mismatch | 313 tasks declare two JOINs but use subquery composition | Fix metadata/actual logic consistency in any reused pool. Physical SQL syntax controls are only needed if continuing the old SQL experiment. Preserve intended company versus site semantics. |
| A010 eligibility trusts metadata | A GROUP BY query can pass after changing labels to eligible metadata | Validate actual operations and task/source integrity. New task-family holdouts must also fail closed when metadata is stale. |
| Alias-sensitive result grading | Same scalar value under a different alias is marked incorrect | Separate semantic answer correctness from formatting/schema scores in the new direct-answer grader; fix SQL grading before Stage 2. |
| No real SQL deadline | Timeout tests inject exceptions; executor has no enforced query deadline | Add a real timeout before unrestricted generated SQL is used. Stage 1 trusted gold generation also needs bounded execution when extending query templates. |
| Zero-SD statistics | Constant positive differences produce standardized effect 0 | Fix before final statistics: report raw difference and an explicit undefined standardized-effect policy. |
| Phase 9 stale checks | Approval-absence test assumes approval file is absent; ledger check assumes no later arms | Isolate fault fixtures and make historical validation phase-aware. New full-data task registry needs new checks, not disabled old failures. |
| Completion-budget claim overstates evidence | Phase 16 uses full-chat length minus prompt length, not actual training labels | Measure shifted, non-ignored labels from the real selected V3 trainer/collator. Historical-template screening is diagnostic only. |
| Training environment/pipeline missing | No active V3 trainer, full inference runner, completed dev/probe artifacts or model outputs | Implement after data/evaluation contracts; existing fixture reports are not a substitute. |

Do not spend the entire Stage 1 budget repairing retired BD/dose experiments. Preserve their evidence and carry the general failure protections into the new active recipe. The frozen handoff's proposed narrow SQL grammar should not be copied wholesale into the expanded analytical task generator without checking which new constructs it must support.

## 7. Prevent the verified V2 failures

The [independent historical audit](review_training_2026-09-11/REPORT.md) remains the evidence source.

| V2 lesson | Required V3 acceptance check |
|---|---|
| All 25 appended dose examples disappeared after 1,024-token truncation in each dose arm | Inspect the exact post-template, post-tokenization, post-truncation/packing examples and labels. Record every retained/dropped example and intended construct; fail on unexplained loss. |
| Near-zero SQL loss was mistaken for broader capability | Report development loss and generated-answer scores separately. Never label teacher-forced token accuracy as question accuracy. |
| No evaluation loss in historical logs | Configure and retain train/dev loss curves with clear denominators and matching masks; use declared development metrics for selection. |
| Standalone B archive corrupted after training | Save immutable exact input bytes, parsed-record counts and hashes at runtime; verify archive hashes and reload checkpoints before reporting. |
| Missing weights/state prevented replay | Retain all comparison adapters, checkpoint-selection evidence, configurations, seeds, source patch/commit, model/tokenizer revisions, environment and resumption state where needed. |
| Some runs used dirty source trees | Record exact source patch, not only a commit ID; prefer a clean reproducible run snapshot. |
| Mixed factual/objective distributions make raw losses incomparable | Compare generated answers on common evaluation sets. If reporting common dev loss, use the same targets and masking across models. |

A larger context limit alone is not proof that preprocessing is correct. Determine the limit from actual rendered training/evaluation lengths plus answer needs, then enforce it. Validate nonzero target labels, protected prompt regions, boundary tokens, EOS, nonfinite loss/gradients, expected updates, token counts and checkpoint reload in the smoke test. No silent input or output truncation.

## 8. Sequenced build plan with concrete completion criteria

| Milestone | Work and proposed artifacts | Completion criterion |
|---|---|---|
| M0 — Reconcile scope | Versioned protocol amendment; current goal; old-to-new phase map; status reconciliation | Base/FT-1/FT-2, full-data semantics, three seeds, no inference tools, evaluation tracks and deferred work all explicit |
| M1 — Preserve and interpret source | Raw cell/observation export; data dictionary; transformation ledger; identity/conflict register; credential semantics; source coverage ledger | All 205 records / 18 fields accounted for; exact raw workbook retained; every observation mapped to training or declared holdout; no silent deletion or invented resolution |
| M2 — Freeze evaluation contract | Task/scenario split manifests; development sets; protected final sets; prompts; scoring rubric; answer-part schema; selection policy | Clear known-fact versus novel-task labels; no analytical logical-task/paraphrase overlap; all deterministic golds independently verified; uncertain scenarios reviewed |
| M3 — Build FT-1/FT-2 | Versioned generators and JSONL; exact-ID/upstream manifests; coverage and duplicate audits | Complete non-held-out factual coverage in both recipes, including every process/service/certification membership; declared exclusions audited; FT-2 task families present; source-qualified targets and no protected benchmark contamination |
| M4 — Implement trainer and scorer | Dependency lock/setup; pinned model/config; direct-answer inference runner; output parser; quantitative and analytical graders; preprocessing audit | Actual labels/exposure verified; meaningful fault tests pass; all expected outputs accounted for; test access mechanically restricted |
| M5 — Smoke and development | Reloadable small checkpoint; base dev predictions; first-seed pilot runs; model-selection log | Parameter updates and reload verified; loss/length/stop behavior understood; configurations selected only from development results |
| M6 — Final runs | Three independent seeds per final recipe, exact run manifests, retained adapters and development results | Six final runs complete or clearly reported failures; equal comparison conditions and measured budgets; final selection frozen |
| M7 — Stage 1 final evaluation | Base and both variants on protected suites; raw predictions, scores, statistical report, error analysis, archive | Denominators and failure accounting complete; per-seed/mean/SD and task breakdowns; limitations and negative results documented |
| M8 — Stage 2 later | Identical tools/data access for base and selected frozen fine-tuned model | Tool contribution measured separately; any further tool-training recipe/version reported separately |

**First implementation batch:** M0 followed by M1 under the existing review workflow. The review request itself has been completed through this report; it does not launch training or silently advance implementation phases.

Proposed new artifacts can live under a clearly versioned Stage 1 directory (for example `datasets_v3/stage1/`, `validation_v3/stage1/`, `results_v3/stage1/`) after the amendment. Preserve today's frozen artifacts at their existing paths. Avoid inventing a second inconsistent company database; derive raw/normalized/training views from one provenance chain.

## 9. Required scorecard and evaluation rules

- Factual correctness by attribute, including numbers, processes, services, credentials and conflicts.
- Company-set exact match plus precision, recall and F1; false additions and omissions reported separately.
- Count/arithmetic accuracy with declared scope, units, rounding and missing-value rules. No arbitrary numeric tolerance that hides wrong integer counts.
- Ordered ranking correctness and tie handling. Semantically valid paraphrases need not match one sentence verbatim.
- Multipart per-part score and strict all-parts correctness, including the denominator of requested parts.
- Supplier-analysis constraint satisfaction, candidate plausibility, evidence support, uncertainty and missing-requirement identification. Use a documented expert-reviewed rubric; any LLM judge is secondary and checked against human judgements.
- Unsupported-claim rate, valid abstention and clarification quality. Distinguish no match from unknown and conflicting evidence; do not reward blanket refusal.
- Training/development loss, nonfinite events, length/truncation/failure rates, runtime/memory and per-seed variability. For comparison loss, hold the evaluated target distribution constant. Perplexity is exp(loss) only when the reported loss definition warrants it; it is not another measure of business-answer accuracy.

Freeze numeric release/quality targets after the development-task specification and before comparing candidate outcomes. They remain to be set; this plan does not invent acceptable business error rates. Use family-level results rather than one opaque aggregate. Preserve the final test for final claims. If its errors guide another training revision, a new protected test is needed for the next final claim.

## 10. Fresh verification results and limits

Fresh regression runs in a disposable copy: Phase 5 fault checks 8/8; Phase 6 16/16; Phase 7 grader checks 81/81; Phase 8 synthetic evaluation checks 91/91; Phase 12 15/15. Phase 9 independent value selection matches all three frozen attribute selections. Phase 9 fault suite has the known missing-approval-fixture failure; Phase 9 `--check` has the known later-ledger-arms mismatch. Both remain reported, not hidden or cleared.

SQLite integrity is `ok`. Canonical child memberships and held-out literal scans are recorded in the supplemental evidence. Current V3 tokenizer/mask screening uses the pinned Qwen tokenizer and historical TRL training template as a diagnostic because no active V3 trainer exists. It cannot certify a future library version's actual data path. Full checkpoint-level V3 verification remains M4–M6 work.

Supporting documentation for implementation principles: [TRL SFT configuration](https://huggingface.co/docs/trl/v1.1.0/en/sft_trainer) exposes assistant-only loss, truncation, evaluation and checkpoint settings; verify behavior for the version actually selected. [Scikit-learn's evaluation guidance](https://scikit-learn.org/stable/common_pitfalls.html) explains why test-driven selection biases evaluation. These support methodology; repository-specific findings come from the local evidence linked above.

### Supplemental token and exposure findings

All eight current training files have zero held-out literal exposures when every actual message is scanned. Independent raw-to-canonical term membership checks pass for processes, services and certifications across all 205 rows; canonical-to-database checks also find zero missing or extra child memberships. These checks verify representation, not completeness of the original research about each company.

| Current artifact | Maximum rendered tokens | Historical-template supervised tokens per pass |
|---|---:|---:|
| A passages | 267 | Not applicable: full-sequence LM objective |
| B factual QA | 139 | 40,835 |
| C direct answers | 243 | 18,209 |
| D SQL | 223 | 34,990 |
| BC | 243 | 59,044 |
| BD full | 223 | 75,825 |
| BD controlled | 223 | 70,752 |
| Repeated D | 223 | 70,018 |

No current example exceeds 1,024 tokens or loses its entire assistant target under the checked historical training template. That is encouraging for the existing short templates, not a guarantee for the longer analytical examples we still need to build.

The Phase 16 length-difference helper undercounts one supervised boundary token in every chat example relative to the historical TRL template. Consequently BD controlled and repeated D differ by 734 actual supervised tokens per pass under that template, approximately 1.04% of the controlled total. Recompute budgets from the actual chosen V3 label path; do not treat the current manifest as a label-level certificate. This is new diagnostic evidence, not a claim that a V3 training run already used those masks.

The new checks also reproduce all 2,017 erroneous repeated-D mappings, the 18 training companies with no B examples in BD controlled, the metadata-only eligibility bypass, the alias-only grading failure, and the constant-positive standardized-effect bug. `.venv-v3` currently contains transformers but lacks torch, TRL, PEFT, openpyxl, pandas and pytest; not all are mandatory runtime dependencies, but a reproducible data/training environment has not been established here.

Detailed outputs: [exposure and token results](review_v3_updated_2026-09-11/exposure_and_token_results.json), [raw term preservation](review_v3_updated_2026-09-11/raw_term_preservation.json), [regression results](review_v3_updated_2026-09-11/check_results.json). The standalone audit scripts are retained beside those outputs.
