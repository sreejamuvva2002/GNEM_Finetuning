# Current review and next steps

The claim that candidate drift was undocumented is incorrect. Commit 486cdc9 contains an explicit note in docs/REPOSITORY_MAINTENANCE.md and candidate_pin_mismatches in validation_v3/resumption/STEPS_1_2_COMMIT_VERIFICATION.json. The candidate now also carries a visible limitation, without refreshed pins. Gate-register pinning has been promoted from optional to required and omission/drift is regression-tested. Stale paragraphs describing resolved approval-binding and sampling defects were removed.

Validation: 119 tests across eight suites; all eight training hashes match their current audits; factual coverage 2,220/2,220; 80 original protected files unchanged; only three intentional mixture changes, with original bytes archived; 66 Python modules parse. Candidate pins for train_v3.py and PRE_TRAINING_GATES_A002.md are stale following these edits. It remains approved=false. No final training/Phase-40/Q42 approval artifact exists.

## Current continuation — Q42 review deferred

The user identified `kb/Human validated questions.xlsx` as the source of the 42 questions and plans to add questions at evaluation time. It contains 42 populated questions and answers; all question texts match the current benchmark. Reviewing the supplied answers is deferred at the user's request. This does not create an approval artifact or change the training release policy. Additional questions should form a separately versioned benchmark with answers and scoring fixed before inspecting model outputs, evaluated consistently across conditions.

## Implemented safeguards

Final evaluation now checks pinned generation identity manifests, rejects extra multipart SQL statements before execution, and uses a new explicit unique-row output contract. Historical prompts and results remain unchanged. The expanded evaluation rubric is drafted in `docs/EXPANDED_EVALUATION_RUBRIC.md`; its items and baselines are not yet complete.

A follow-up check fixed two final-contract edge cases: extra multipart keys could regain format/strict credit after the parent grader rejected them, and JSON null could be conflated with the literal string "None" when counting duplicate multi-column rows. Both now have regression tests. The seven safeguard tests and nine final-driver tests pass (16 tests in this follow-up, not a rerun of every repository suite).

## Remaining steps

1. Complete protected-generation authorization and enforce runtime identity against the approved specification. The in-memory generation core now connects to export and passes five synthetic tests; the exporter passes four. The unchanged-base backend passed a two-prompt real GPU rehearsal with matching repeated token IDs and valid exports on 2026-09-13. The existing six-step D_sql diagnostic adapter also passed GPU loading, saved/loaded tensor comparison, repeat-generation and export checks. The protected memory-generation entry point now enforces exact runtime specifications and evidence-bound authorization (eight synthetic tests). Actual per-run specifications, release review and complete scoring registration remain unfinished.
2. Author and validate broader development items for multipart questions, ambiguity and evidence analysis; establish matching base baselines. Preserve the original operation/composition holdouts.
3. Complete artifact backup arrangements, the broader matched forgetting evaluation and the final analysis plan.
4. Revisit Q42 adjudication before release under the current protocol. Training before adjudication would require an explicit protocol amendment; no such amendment has been applied. Candidate regeneration still requires an explicit request before release review.

Final training remains 0/18 runs; diagnostic smoke/rehearsal adapters are not completed experimental variants.

The base model's 96 structured set responses were all empty arrays despite nonempty golds. They are incorrect omissions, not fabricated company lists; 0/120 must not be interpreted as 120 fabricated answers. This observation does not establish correct uncertainty calibration. Counts must be analyzed separately.

Next engineering step: generation/export and sealing integration. Q42 answer review remains deferred while independent preparation continues.

No historical model results were changed, no candidate pins were refreshed, and no commit or push was performed. The review checked active code/contracts and recorded integrity; it did not independently reread every historical log or weight tensor.

## Pre-update checkpoint — 2026-09-13

A 12-question / 30-part diagnostic dev set is now built and SQL-verified. The unchanged-base run completed with 0/12 all-parts correct; results are in results_v3/dev/base_multipart_r1. It does not change checkpoint selection or training. Recovery instructions and pending work are in docs/LAB_UPDATE_RECOVERY_2026-09-13.md.
