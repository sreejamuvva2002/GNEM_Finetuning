# Current pre-training gates

Final independent training runs: **0/18**. Q42 approval remains pending by explicit user decision. No approved release has been created. This register supersedes earlier dated status lists, without rewriting their evidence.

## Completed engineering and development work

- Corrected 120-item structured dev set: full predicates have dev row anchors, split metadata is explicit, 21 tests pass. Baselines on this set are now complete: base 0/120, SQL 120/120, SQL five-shot 120/120. Factual base 0/255; oracle context 245/255. See results_v3/dev/REPORT_A002_r3.md for slices and information-access limits. SQL ceiling persists despite removing answer-in-question leakage; the set remains narrow.
- Release validator rejects incomplete hashes, unscheduled seeds and malformed seed values; 25 tests pass. The proposed 18 pairs remain unchanged and are not approval. The final approval workflow still needs to bind actual human Q42 evidence and all completed gate evidence, not merely an approval string.
- BD sampling decision implemented: preserve complete cycles and allocate the last partial cycle according to source supervised-token shares across join arities. Every source retained; extra repetitions cover arities 0/1/2. Earlier mixtures preserved under archive/pre_stratified_BD_2026-09-12. Two regression tests pass.
- Controlled BD: 3,515 items, 94,417 supervised tokens (B 47,202 / D 47,215). Repeated-D: 2,732 items, 94,440 tokens, only 23 above controlled. BD_full unchanged: 3,460 items, 92,655 tokens. Controlled exceeds full by 1.90%; do not frame this as a substantial allocation contrast.
- CPT tail and empty-output-directory cases corrected. Three boundary tests verify every source token is preserved. D_sql rehearsal used 16 train examples, four dev examples, accumulation 8, three epochs, six optimizer steps and epoch eval/save. Train loss 0.88913, selected dev loss 0.24147. Selected weights match best checkpoint; reload logits identical. This is a configuration rehearsal, not a final quality result or one of the 18 runs.
- Ordered row, multi-column set and multipart JSON grading implemented with five synthetic regression tests; public parser dispatch tested. Q42 multipart SQL keys, gold keys, part IDs and columns agree. Versioned structured_prompt_v3.py defines multipart contracts; existing frozen baseline prompts remain unchanged.
- All eight current training recipes have actual shifted-label audits; 2,220/2,220 eligible factual observations remain covered. Current counts and configured step estimates are in validation_v3/resumption/TRAINING_LABEL_AUDIT_CURRENT.json.
- Base general sanity screen: 30/30. This is a floor screen, insufficient to establish absence of forgetting. Matched post-training scoring remains required.

## Still required before release / protected evaluation

1. Complete Q42 semantic adjudication and obtain the user's explicit approval. SQL execution proves consistency with recorded data, not that the question supports the proposed conclusion. Approval remains pending.
2. Offline final evaluation driver implemented in finetune/final_eval_v3.py: nine synthetic integration tests pass for all answer shapes, no-match handling, serialization, explicit probe scope and independent-seed summaries. CLI refuses protected inputs without a pinned Phase 40 approval and genuine Q42 approval evidence. Still required: final model-output generation/export integration, artifact sealing registration, and approved analysis contrasts/multiplicity and primary-Q42 inclusion. No protected outputs have been scored.
3. Build a reviewable release candidate from current inputs, code, environment and actual approval/gate evidence; do not create an approved release based only on booleans. Final hyperparameters need explicit frozen identities.
4. Confirm a durable backup destination and verify restore hashes for retained and future adapters and the V2 prediction corpus. No external backup is configured or verified; the destination question is pending.
5. Choose a broader matched general-capability evaluation before interpreting forgetting. Current arithmetic/copy screen is not sufficient. Additional dev paraphrases and analytical diversity remain limitations to report, not silently assumed evidence.

Current single-device configured totals (not observed final runs): A 20; B 807; C/D 492 each; BC/full BD 1,299; controlled BD 1,320; repeated D 1,026. A source: 35,071 tokens including EOS, 35 chunks and 35,036 shifted targets. Chat maximum length 244 versus 1,024 limit.

## Independent-review corrections before committing

The arity-balanced sampler still overweights count tasks and omits filter tasks from partial repeats because selection within arity uses lexicographic prefixes. See the generated task-kind table in BD_COMPOSITION_v3.md. **Final sampling is unresolved**, not accepted merely by disclosure.

The training validator currently checks Q42 approval strings but does not bind actual external Q42 approval evidence; this is an open release-blocking defect. Protected-driver prompt/adapter identity binding and SQL extra-statement handling also remain open. Duplicate structured-row handling needs a clearly defined distinction between mathematical set correctness and strict schema compliance. No protected evaluation or final training is authorized by this review.
