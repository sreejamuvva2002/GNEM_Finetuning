# A-002 — Full-field training in the original eight-variant V3 study

Status: ACTIVE SPECIFICATION; implementation migration pending.

Authorization: the user requested resuming the original V3 phases, then explicitly selected “Revise original V3 now for full-field training” when asked to resolve the conflict with existing exclusions. This supersedes the sequencing-only assumption that complete-field coverage would wait for a later study. It does not authorize fabrication of data or unsealing tests early.

Timing: after the historical Phase 0–16 implementation and its audits; before any completed V3 model training or inference evidenced in this checkout. Base commit at decision: `8e7196e0e58d6ebcb35d7a14944146039f4c912f`. Historical source and audit artifacts remain evidence of their original versions.

## Unchanged experimental structure

Keep A_cpt, B_facts, C_answers, D_sql, BC, BD_controlled, D_repeat_budgetmatched and BD_full. Keep the original four baselines and minimum 18 final independent training runs, pinned model family, development-only selection, protected final evaluation and adapter retention. Keep all 43 phase numbers; revalidate affected earlier phases before advancing to Phase 17.

The existing company/split-group assignments are the explicit retained data holdout: 148 training rows / 141 names; 17 development rows / 17 names; 40 test rows / 35 names. Preserve all 205 source rows / 193 names and all 18 columns. This choice preserves the existing unseen-company comparison while including every substantive field for training-eligible companies, except the explicitly excluded recorded Certification Count. Full-field coverage does not mean leaking the 57 dev/test rows into model-visible training.

## Coverage and interpretation

1. Include processes, services, certifications, Employment, Classification Method and all other source attributes except Certification Count. The user explicitly permitted excluding that redundant count from training; preserve it internally for validation. Record No. supplies source-record provenance and is available in explicitly record-scoped tasks. Split labels and experimental metadata remain infrastructure, not model-facing facts.
2. Preserve complete process/service/certification lists. Remove the current value-holdout policy that drops whole fields or company/attribute QA. Retain raw spellings and cell provenance alongside normalized sets. Do not truncate a true list to hide a term.
3. A must represent every training-row observation, including missingness and conflicts with source attribution. B must cover every training-eligible field observation, using company-level QA only when unambiguous and record-scoped/conflict explanations otherwise. BC and BD_full retain the full eligible factual source. C and D remain a paired structured-task experiment with identical task IDs and questions; every applicable field is supported, but they are not required to recite every row as a lookup task. Their exposure ledger must distinguish field support from actual fact exposure.
4. Missing evidence and conflicts are not automatic skip reasons. Teach source-qualified statements and uncertainty; never invent resolution, silently merge incompatible observations, infer absence from unknown, or call every repeated row a distinct facility.
5. Certification Count denotes the number recorded in the workbook. Preserve it in the immutable source and canonical records for validation against parsed source entries; exclude it from model-facing loader output, schema prompts, training inputs and targets. Do not add it to the model-facing SQL schema. Complete certification lists remain included. Questions may still count recorded list entries where the task policy allows; that does not assert current valid credentials. Numeric aggregation must distinguish record counts, distinct companies and business quantities with unresolved scope.
6. BD_controlled must not silently remove companies/factual observations for budget matching. Its revised sampler must retain the eligible B and D sources, balance their actual supervised-token allocations by repeating the smaller source as necessary, and match repeated-D against the resulting total. Record order, multiplicities and actual post-preprocessing token totals. This replaces the old smaller-anchor prefix subsampling rule. It remains a supervision-allocation comparison, not a pure causal claim that facts help.
7. Every source observation must be traceable to training supervision, an explicit company holdout, or declared non-model-facing provenance. Do not use the provenance category to hide a substantive factual omission. Check complete-list memberships and coverage independently in A/B and their mixtures, and task/fact exposures independently in C/D. Require zero unexplained omissions after actual rendering and trainer preprocessing.

## Holdout and evaluation migration

Remove deliberate literal/value withholding inside training-company records. The old Phase 9 registry/exposure certificates are historical and cannot certify amended datasets. Replace them with versioned registry/manifests; never alter the meaning of an existing approval record.

Retain operation and composition holdouts as question/task holdouts where compatible with complete factual records: they withhold particular analytical supervision, not underlying company field lists. Distinguish B's recorded numeric facts from C/D aggregation-task supervision in operation scans.

Phase 21 becomes an exposure-stratified value probe: classify values by actual fine-tuning exposure and company split. Values present in training must never be called unseen. Naturally unexposed values in held-out-company records can be reported separately where they exist; do not manufacture absent-value coverage or promise a nonempty stratum. Update Phases 9, 21, 26, 27, 29 and final reporting consistently. Keep old selected-value costs/probes as historical evidence only. Do not interpret amended results using the previous literal-withholding hypothesis.

Freeze revised prompts, task identities, exposure labels, evaluation rules and source scope before baseline/model outcomes. Original Q42/test inference remains sealed until the prescribed gate. Rebuild all affected downstream golds and manifests after schema/curriculum changes, never just patch stale counts.

## Trustworthiness requirements

Use actual shifted/non-ignored training labels for budgets, not full-minus-prompt length estimates. Verify no unintended drops/truncation, parameter updates, checkpoint reload and exact archived input hashes. Preserve all V2 regression lessons.

Resolve outstanding provenance, SQL shape/eligibility, scanning and reporting findings. Primary scalar result correctness must not reject an otherwise unambiguous single-cell answer merely because its SQL alias differs; strict schema correctness remains separate. Zero-variance standardized effect sizes must be reported as undefined with their raw mean difference, not zero effect. Validate real SQL deadlines before generated-query execution. These decisions must be implemented and tested before final scoring.

## Migration state and authority

This amendment overrides incompatible clauses in README.md and CLAUDE.md, including dropping conflicting/sentinel QA, literal-value omissions, value-probe claims and the old controlled-mixture sampler. Unaffected requirements remain in force. Their older text is retained for traceability during migration, not as concurrent conflicting instructions.

Existing generated files remain unchanged until their builders and gates are migrated. Do not describe old datasets as compliant with A-002. The amendment is a completed specification change, not clearance of Phase 7–16 implementations.

## Subsequent user clarification — Certification Count exception

The user stated that Certification Count is unnecessary and authorized excluding it if agreed. Its source value remains available for validation, but it is the sole categorical source-field exception to model-facing training under this amendment. This overrides earlier requests in planning documents to train this count. Complete certification, process and service lists and other field coverage remain required. Phase 5 must revalidate the existing count-free schema rather than add this column.
