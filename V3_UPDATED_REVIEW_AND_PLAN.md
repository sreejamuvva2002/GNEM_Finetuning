# V3 current implementation plan

This is the active implementation roadmap. [A-002](PROTOCOL_A002_FULL_FIELD.md) defines the current scientific amendment; it overrides conflicting historical clauses in the [phase reference](docs/PHASE_PROTOCOL_REFERENCE.md) and [execution reference](docs/EXECUTION_RULES_REFERENCE.md). [V3_PHASE_STATUS.md](V3_PHASE_STATUS.md) records verified progress. Older proposals are historical evidence, not additional active plans.

## Objective and comparison

Finish the original eight-variant experiment with full-field training for eligible records. Establish what the unchanged base and fine-tuned models can answer from memory, reporting factual, structured and multipart performance separately. Report context and SQL-execution baselines separately because they receive external evidence. Do not combine their scores with model-only scores.

| Variant | Minimum independent final runs |
|---|---:|
| A_cpt | 1 |
| B_facts | 3 |
| C_answers | 3 |
| D_sql | 3 |
| BC | 1 |
| BD_controlled | 3 |
| D_repeat_budgetmatched | 3 |
| BD_full | 1 |

All 18 runs start independently from the same pinned base revision. Keep the four declared baselines: base, base_ctx_oracle, base_sql and base_sql_5shot. Broader factual-plus-analytical recipes and subsequent tool development remain a separately versioned follow-on after this study. Supplier alternatives may be described as plausible only with supporting evidence; certifications alone do not establish customer qualification. Employment is not production capacity. Missing import, capacity or qualification evidence must remain explicit.

## Data contract

- Preserve the complete Excel workbook and canonical representation: 205 records, 193 exact company names, 18 source columns. Repeated names remain traceable records; do not assume they represent different facilities.
- Retain the explicit split: 148 training records, 17 development records, 40 test records. Full-field training applies to training-eligible records; held-out companies must not leak into training.
- Include full certifications, processes, services, Employment and all other substantive source attributes. Certification Count is the sole user-approved source-field exclusion from model-facing training; preserve it internally. Record identifiers provide provenance and support record-scoped questions.
- Remove deliberate literal/value exclusions within training-company facts. Preserve complete lists, missingness, conflicting observations and source spellings with provenance. Do not infer unrecorded facts or merge conflicting values silently.
- A/B and factual mixtures must cover eligible observations; C/D must share questions/task IDs and validated SQL-derived gold. Report actual exposure separately from field support. Preserve the amended operation/composition holdouts.
- Controlled BD must retain every eligible B/D example, using repetition to balance actual supervised tokens. Repeated-D must match the resulting budget without dropping factual coverage.

## Execution sequence and gates

| Phases | Work and required evidence |
|---|---|
| 0–4 | Amendment recorded; source/split revalidation and amended loader checks pass. Preserve existing evidence and immutable source hashes. |
| 5–6 | Revalidate count-free SQLite against every source record and child membership; verify complete oracle context with the pinned tokenizer and no truncation. |
| 7–8 | Correct single-cell alias-sensitive grading; retain separate strict-schema scores. Add real SQL deadlines. Revalidate reporting and zero-variance statistics with meaningful negative tests. |
| 9 | Version the amended registry/exposure ledger. Preserve old approvals as historical; remove deliberate value withholding and verify remaining operation/composition rules. |
| 10–16 | Repair builders, provenance, all-message scans, SQL/metadata consistency and coverage-preserving mixtures. Regenerate every training variant. Audit actual post-template labels, complete lists, source-to-example mappings and zero unexplained omissions. |
| 17–29 | Build dev/probe sets, exposure-stratified value probes, paraphrases, no-match and multipart tests; freeze prompts, few-shot sources and metrics. Audit Q42 gold without running protected model evaluation. Complete global leakage and coverage checks. |
| 30–32 | Implement reproducible training/inference; run end-to-end fixtures, base dev evaluation and actual training smoke tests. Verify gradients, checkpoint reload, assistant masks, nonzero labels, lengths and optimizer-step accounting. |
| 33–39 | Train all eight variants with required seeds. Log actual train/dev loss, task scores, learning rates, token budgets, steps, runtime and failures. Select configurations/checkpoints using development evidence only. Retain all final adapters. |
| 40–42 | Freeze selections, run protected evaluation, compute per-seed and aggregate statistics, analyze each question/error, and archive reproducible artifacts. Completion requires actual results, not perfect scores. |

The full-field training variants have been regenerated and their coverage, labels and scoped SQL golds verified. Development/probe inputs and prompts are built. Four development baselines and all eight representative two-step training smoke tests have run; these are not the final 18 independent training runs.

The current release gates are Q42 adjudication/approval (explicitly pending at the user's direction), broader analytical development coverage, and final scoring integration. See [phase status](V3_PHASE_STATUS.md) for individual gates and [development results](results_v3/dev/REPORT_A002_r2.md) for actual denominators and limitations. Do not launch full training until the release is satisfied. Protected test inference remains sealed.

## V2 regression requirements

1. Inspect labels after the actual training preprocessing. V2 dose extras lost all assistant supervision after truncation; nominally different inputs became identical effective training sets.
2. Hash and retain the exact data bytes used in each run, alongside code, environment, tokenizer/template and checkpoint identities.
3. Record development loss and task scores. Low training loss or teacher-forced accuracy does not establish reliable question answering.
4. Test paraphrases, wrong-company facts, incomplete or invented list entries, SQL precedence and unsupported SQL. Do not reward a certification answer merely because it contains one correct term.
5. Grade the question actually asked; do not require an unrequested quantity. Separate semantic result accuracy, strict schema, SQL execution and closed-book factual correctness.

## Repository organization

Keep executable modules in `finetune/`, source in `kb/`, generated data in `datasets_v3/`, and validation evidence in `validation_v3/`. Preserve historical training and question-level audits in their existing review directories because manifests and scripts reference those paths.

Superseded planning snapshots and the conversation export were moved to [the planning archive](archive/planning_before_cleanup_2026-09-11/README.md). The [cleanup manifest](validation_v3/resumption/CLEANUP_2026-09-11.json) records exact hashes and dispositions. Historical reviews and the handoff remain available as evidence, while this document supplies the current roadmap.

Current pre-training limitations and configured-step corrections: [gate register](validation_v3/PRE_TRAINING_GATES_A002.md). The r2 report supersedes r1 scoring; historical evidence remains preserved.
