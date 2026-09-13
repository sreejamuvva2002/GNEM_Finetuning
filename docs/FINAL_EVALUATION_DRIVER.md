# Offline final evaluation driver

`finetune/final_eval_v3.py` grades retained predictions; it does not generate them. The CLI requires `--unseal` and `validation_v3/PHASE40_RELEASE_A002.json` with approved=true, phase=40, pinned input/prediction/database/code hashes, a sealed-input classification, and an explicit runs entry containing condition, seed, mode and prediction path. It also verifies the actual pinned Q42_HUMAN_APPROVAL_A002.json and benchmark identity. Neither approval file was created by this work.

Inputs are JSONL tasks with frozen example IDs, questions, golds, scopes and answer metadata. Prediction records must contain the exact IDs/questions, condition/seed, raw_output, a prompt_hash and adapter_hash (null for a base model). Missing outputs must be explicit records rather than omitted IDs. Input and prediction contents are parsed only after CLI authorization. The lower-level functions accept in-memory fixtures for tests and are not an authorization boundary.

Outputs belong under results_v3/test and use a new directory. Canonical records retain raw outputs and SQL execution evidence; telemetry retains grader details, part outcomes, no-match correctness and output contracts. SQL evidence is obtained through a second read-only scoped execution after successful grading. Summaries retain failures and exact denominators. All-item Q42 scores are descriptive; diagnostic proposals do not automatically become approved primary results. Independent-seed summaries reject repeated seeds or changed item sets and do not pool items as independent model runs.

Nine synthetic tests cover canonical serialization, ranked/multipart/set/scalar paths, empty answers, missing/duplicate records, truncation, SQL result evidence, train-only scope, seed summaries and missing-release refusal. No protected output was read or scored. This completes offline grading plumbing, not final inference/export/sealing integration or inferential analysis. Those remain in the current gate register.

## New final-only safeguards

final_eval_A002.2 requires a release-pinned generation identity manifest indexed by prediction path. It binds prediction bytes, base revision, frozen prompt artifact, new structured prompt module, per-item prompt hashes, and either an explicit base model with null adapter hashes or an existing release-pinned adapter file. Export registration still needs to be produced and verified by the final generation pipeline; hashes do not independently authenticate how outputs were generated.

The new structured_prompt_A002.2_unique_sets contract explicitly forbids duplicate set values/rows. final_contract_v3 preserves membership correctness while reporting duplicate_rows, format=false and strict=0. Ordered results retain exact sequence comparison. This policy is final-only; prior prompts and scored baselines are unchanged. Multipart SQL requires exactly one statement per part before execution; historical SQL grader behavior remains unchanged.

Five new synthetic safeguard tests cover duplicates, rank errors, extra SQL, missing identity manifests, prompt substitution and adapter drift. No protected input was scored.

Follow-up: final_unique_sets_A002.2 preserves rejection of extra multipart keys and distinguishes JSON null from the literal string "None" in duplicate row detection. The safeguard suite now has seven tests; the nine final-driver tests also pass. These are synthetic checks, not model performance results.

## Prediction export component

`finetune/prediction_export_v3.py` exports already-generated in-memory records, computing prompt hashes from retained rendered text and adapter hashes from artifact bytes. It requires exact expected ID coverage, explicit raw outputs and truncation flags, and a new output directory. It writes predictions, the identity manifest consumed by the evaluator, and an unapproved registration fragment. This does not grant Phase-40 access or approve Q42. Four synthetic tests cover base/adapter evaluator round trips, drift, overwrite refusal, duplicate IDs and identity mismatch.

The caller must still authorize benchmark access and bind the generation runtime (tokenizer, adapter configuration, decoding settings and actual model loading) before using this component for final predictions. No final inference was run.

## Generation core (not yet released)

`generation_core_v3.py` provides tool-free in-memory generation and a local Transformers base/LoRA backend, connected to the exporter through `generate_and_export`. It builds prompts from questions and declared output shapes, retains input/output token IDs and rendered text, refuses context overflow, and detects EOS versus token-budget truncation. Runtime metadata includes tokenizer serialization and template hashes plus decoding configuration; the exporter retains and hashes it.

Five synthetic generation tests pass, including an export/evaluator identity round trip; four exporter tests also pass. The real backend has not been GPU-tested. This is not a protected-input CLI: the caller must still authorize input access, enforce approved runtime/configuration and adapter identities, and arrange complete sealing registration. Merely storing runtime metadata does not verify it against an approved specification. No final predictions or approval artifacts were created.

## Real base GPU rehearsal — 2026-09-13

`rehearse_generation_v3.py` ran the local unchanged base on two fixed synthetic prompts, twice each. Repeated output token IDs matched and the export passed evaluator identity verification. Evidence is in `validation_v3/generation_rehearsal_2026-09-13/base/`, including rendered prompts, tokens, runtime/package metadata and hashes. The token budget was 64 for this rehearsal. This verifies base runtime plumbing only: it does not measure domain competence, adapter loading, reload reproducibility or protected-generation authorization. No training or protected-input access occurred.

## Diagnostic adapter GPU rehearsal — 2026-09-13

`rehearse_adapter_generation_v3.py` loaded the existing six-step D_sql diagnostic adapter on the frozen base, checked its active adapter and inference-only parameters, and compared every loaded adapter tensor with the saved safetensors state (cast to saved dtype). Saved weights/configuration hashes remained unchanged. Two fixed synthetic prompts repeated with identical output token IDs; export identity verification passed. Evidence is in `validation_v3/generation_rehearsal_2026-09-13/diagnostic_D_sql/`. This tests diagnostic adapter loading and export, not one of the 18 final runs or domain competence. Protected-generation release enforcement and approved runtime binding remain outstanding.

## Protected memory-generation entry point

`final_generate_v3.py --unseal --run-id <approved-id>` requires the fixed `validation_v3/GENERATION_RELEASE_A002.json` with `approved: true`, `purpose: protected_generation`, one matching run, and pinned code, input, runtime specification, Q42 benchmark and current Q42 approval evidence. Adapter runs additionally pin selected safetensors and adapter configuration. Outputs must be new directories under `results_v3/sealed_generation`. No actual release was created.

Each run declares `run_id`, `inputs`, `runtime_spec`, `out`, `mode: memory`, `condition`, `seed`, `model_kind`, and (for an adapter) `adapter_path`. The runtime specification contains the exact frozen `prompt_config` and exact observed `backend_runtime`. The entry point verifies these after loading the backend, rechecks input pins before parsing tasks, generates without tools, and exports an unapproved registration fragment for later scoring review. A copied generation release records authorization; it does not itself authorize scoring. All release pins are rechecked after generation.

Eight isolated tests cover authorization before backend loading, missing/drifted code, stale Q42 approval, run/path restrictions, runtime substitution, and a complete synthetic generation/export. Real runtime rehearsals remain separate from this synthetic gate test. SQL/tool generation is outside this entry point. Completing the actual per-run runtime specifications, independent review and Phase-40 scoring registration remains necessary.
