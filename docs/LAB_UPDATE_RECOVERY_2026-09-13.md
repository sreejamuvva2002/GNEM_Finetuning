# Resume V3 after the lab update

This is the handoff for a new Codex conversation if the original chat cannot be restored. User requested committing and pushing all current project work before a lab update. Do not mistake this checkpoint for a completed experiment.

## Objective and experiment state

Compare unchanged Qwen/Qwen2.5-14B-Instruct (revision cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8) with eight fine-tuning variants across 18 independent final runs, initially without tools. Preserve all eligible source information, including processes/services, certifications and numbers. Certification Count alone is intentionally excluded model-facing, retained canonically. Preserve documented entity/operation/composition holdouts. Factual coverage previously verified 2,220/2,220 eligible observations.

Final training: **0/18**. Eight two-step smoke runs and one six-step D_sql rehearsal are diagnostic adapters only. No final training, Q42 approval, generation release or Phase-40 release has been created. Q42 adjudication remains explicitly deferred by the user. Do not invent approval or silently remove the gate. Candidate regeneration requires an explicit user request; its recorded stale pins are intentional.

Variants/run counts: A_cpt 1; B_facts 3; C_answers 3; D_sql 3; BC 1; BD_controlled 3; D_repeat_budgetmatched 3; BD_full 1. Primary seeds 61/62/63; diagnostic arms seed 61, per proposal. Current controlled BD has 3,512 items / 94,411 supervised tokens; repeated D 2,724 / 94,418; BD_full 3,460 / 92,655. Earlier mixtures archived. Never use archived mixtures as current training input.

## Current evidence and recent changes

- Historical r1/r2 predictions and reports preserved. New dev r3: base 0/375; oracle 245/255; SQL and SQL-five-shot each 120/120. SQL is a different information-access condition, not closed-book competence.
- Corrected final-only unique-set and multipart grading; runtime/prompt/adapter identity checks; generation/export implementation with synthetic gate tests.
- Real GPU generation rehearsals: `validation_v3/generation_rehearsal_2026-09-13/` for base and existing diagnostic D_sql. Repeated token IDs match, adapter loaded tensors match saved weights, exported identities validate. Both synthetic set prompts produced incorrect empty arrays; these are runtime checks only.
- New diagnostic multipart dev set: `datasets_v3/dev_multipart_r1_v3.jsonl`, 12 questions / 30 parts, recombines allowed existing dev components; all gold parts SQL-verified. No training/checkpoint-selection change. Unchanged-base result: **0/12 all-parts correct**, at `results_v3/dev/base_multipart_r1/`. Do not relabel this as independent unseen-fact evidence.
- Human question workbook: `kb/Human validated questions.xlsx`, all 42 question texts match Q42. Source answers still need reconciliation; OEM links do not prove sole sourcing, and employment does not prove capacity. Additional future questions need separately versioned golds fixed before inspecting outputs.
- Recent checks: `validation_v3/resumption/PRE_UPDATE_TESTS_2026-09-13.json`. Each entry contains actual command output and exit status. Historical verification snapshots may refer to older code hashes; do not overwrite them to imply fresh verification.

## Remaining work

1. Independently review protected generation/runtime binding and scoring registration; build actual approved per-run specifications only after decisions/approval. Current `final_generate_v3.py` is memory-only, not SQL/tool generation. Separate generation and scoring releases avoid pretending future prediction hashes exist before inference.
2. Finish broader evaluation: ambiguity with answerable controls, evidence-grounded supplier alternatives and vulnerabilities, matched general-capability/forgetting evaluation. Rubric draft: `docs/EXPANDED_EVALUATION_RUBRIC.md`. Multipart dev covers allowed count/filter recombinations only.
3. Obtain verified durable artifact storage and Q42 adjudication; freeze final hyperparameters, analysis contrasts and release evidence. Do not claim hashes alone provide backup or approval authenticity.
4. Only then perform the 18 final runs, matched baseline/adapter evaluations and full scientific reporting.

Read `docs/CURRENT_REVIEW_AND_NEXT_STEPS.md`, `validation_v3/PRE_TRAINING_GATES_A002.md`, `docs/FINAL_EVALUATION_DRIVER.md`, and `docs/ARTIFACT_RETENTION.md` before continuing. Verify current state rather than trusting this handoff blindly.

## Recover repository and environment

Remote: https://github.com/sreejamuvva2002/GNEM_Finetuning.git, branch main. After the update, clone/pull and compare `git rev-parse HEAD` with `git ls-remote origin refs/heads/main`. Preserve any local changes before pulling. The push result is reported in the chat; do not infer success from this document alone.

Runtime environments are `.venv-v3` and `.venv-v3-train`; pinned training packages are recorded in `validation_v3/resumption/TRAINING_ENVIRONMENT.lock`. Virtual environments and downloaded base weights are not in Git. If the machine is rebuilt, recreate compatible environments and download the exact base revision, then rerun runtime checks. GPU rehearsals used one A6000 with bfloat16/SDPA.

The multipart inference job finished successfully before recovery preparation. No experiment process is intentionally left running for the update. Temporary backup/test shell jobs must finish before shutdown.

## Recover the chat

The installed CLI supports `codex resume --last`, `codex resume --all`, and `codex resume <SESSION_ID>`. From this repository, try `codex resume --last`; use `--all` to choose another thread. This depends on preserved local session state. Exact IDE restoration across reinstall/version changes is not guaranteed.

A private snapshot is staged under `.recovery/lab_update_2026-09-13/` (ignored by Git). It includes local sessions, attachments, session index and SQLite online backups for thread/history/goal state. Credentials and logs are not included. The snapshot is taken while this conversation is active, so later messages may not be present. Close Codex before restoring. Preserve any new local Codex directory before restoring the snapshot's contents into the appropriate Codex home; sign in again if needed. Do not publish the private snapshot to GitHub.

`excluded_artifacts.tar` holds retained repository weight/state files and the full V2 prediction corpus. `codex_history.tar.gz` holds the private chat snapshot. `manifest.json` records checksums. These are SAME-FILESYSTEM staging copies, not protection against a wiped home directory; copy them to storage known to survive the update. GitHub contains the project files, not these archives. A private external destination has been requested but not yet supplied.

If chat restoration fails, open the repository in a new Codex conversation and send:

> Read docs/LAB_UPDATE_RECOVERY_2026-09-13.md and the linked current-state documents. Independently verify the worktree, approvals and evidence. Continue the original V3 experiment. Q42 review is deferred; do not fabricate release approval or regenerate the training candidate without my explicit request.
