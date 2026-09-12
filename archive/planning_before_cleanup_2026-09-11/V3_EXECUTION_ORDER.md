# V3 execution order — original experiment first

> **Latest user decision:** Finish the original eight-variant V3 study with full-field training now, under [A-002](PROTOCOL_A002_FULL_FIELD.md). Earlier instructions here to defer all full-field changes are superseded. The broader analytical FT-1/FT-2 follow-on remains later. See [current phase status](V3_PHASE_STATUS.md).

User-directed sequencing decision: complete the existing README V3 experiment and obtain its required scores before pursuing the broader fine-tuning plan. This takes precedence over earlier recommendations to replace the active experiment immediately. It records sequencing, not completed implementation, phase clearance, or new scores.

## First: complete the original V3 study

README.md and CLAUDE.md remain the active scientific protocol. Preserve its research questions, field policies, train/dev/test scopes, holdouts, model, baselines and comparison hierarchy. Preserve all source Excel data in the source/canonical layer. Its intentional training exclusions remain in effect for this study and must be disclosed in reporting. The later complete-field training requirement does not silently alter these frozen comparisons.

| Fine-tuning condition | Minimum final seeds |
|---|---:|
| A_cpt | 1 |
| B_facts | 3 |
| C_answers | 3 |
| D_sql | 3 |
| BC | 1 |
| BD_controlled | 3 |
| D_repeat_budgetmatched | 3 |
| BD_full | 1 |

Eight variants, at least 18 final training runs. Each starts independently from the same pinned base revision. Include the original base, base_ctx_oracle, base_sql and base_sql_5shot baselines with their declared information access. The original study therefore includes context and SQL/tool conditions now; it is not an entirely model-only study. Do not collapse their results into a memorization score.

Execution sequence:

1. Close outstanding implementation audit findings relevant to the original study and reconcile actual phase status. Re-audit the latest handoff proposals after implementation. Correct source mappings, source integrity/message scans, task semantics/metadata, misleading reports and sampling-coverage accounting. Preserve frozen sampling rules unless a documented decision amends them.
2. Resolve grading ambiguities and statistics defects before any model outcomes guide changes. Implement real execution limits. Record any necessary scientific/measurement amendment explicitly; do not silently change the original contract.
3. Complete the planned development sets, probes, prompts, Q42 gold audit and pre-training validation gates. Keep test/Q42 inference sealed according to the original protocol.
4. Implement a reproducible trainer and inference runner. Verify actual post-template/tokenization/masking/truncation/packing labels, retained data, supervised-token budgets and expected optimizer steps. Current length-difference budgets are not sufficient certificates. Verify model revision loading, gradients/updates, EOS behavior and checkpoint reload in smoke tests.
5. Run the original development baselines and train all eight conditions with the required seeds. Log train/dev losses, development task scores, learning rates, gradients, lengths, tokens, runtime, memory and failures. Make selections only from development results. Retain adapters and exact manifests.
6. After the prescribed gates and selection freeze, execute the final original test suite and report each baseline/variant on its applicable task families. Include per-seed results, mean/SD where appropriate, denominators, complete-answer accuracy, failures, uncertainty and error analysis. Do not call synthetic fixture scores model results or infer correctness from low training loss.
7. Archive the original study before beginning the follow-on study. Completion means the required comparisons and results are reproducible and their limitations documented; it does not require perfect scores.

“As planned” preserves the experimental design; it does not preserve known bugs or reenact the V2 truncation and archival failures. The independent historical audit and current V3 audit findings remain required engineering inputs.

## Then: broader company-data and analytical fine-tuning

After the original study is complete, pursue V3_UPDATED_REVIEW_AND_PLAN.md as a separately versioned follow-on plan. Its internal Stage 1/Stage 2 terminology refers to stages within that later study:

- Base versus FT-1 factual QA versus FT-2 factual-plus-analytical QA, initially without inference tools.
- Every Excel field represented, including full processes, services, certifications and recorded Certification Count; only explicitly documented test/research holdouts may exclude source observations from training exposure.
- Source-qualified numeric facts, conflicts and missing evidence represented rather than silently skipped.
- Expanded multipart aggregation, supplier alternatives, replaceability and vulnerability analysis, with additional evidence requirements made explicit.
- Subsequent equivalent tool-access comparisons after that study's model-only checkpoints/results are frozen.

Use original-study errors as development evidence for the follow-on study, not as a protected final test. Construct a new protected final evaluation for any claims influenced by the original results. Keep study IDs, dataset versions, artifacts and claims separate. Reconfirm the later comparison details against the completed original findings before launching its runs.

## Immediate work

Resume the original study at its first unmet audit/validation gate, not at full training. The existing Phase 10–16 corrections are not all verified closed; the status markers and absence of development/training artifacts must be reconciled with that evidence. No training was launched and no phase approval was created by this sequencing update.
