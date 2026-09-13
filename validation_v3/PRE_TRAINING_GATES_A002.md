# Current pre-training gates

Final independent training runs: **0/18**. Q42 approval remains pending by explicit user decision. No approved release has been created. This register supersedes earlier dated status lists, without rewriting their evidence.

## Completed engineering and development work

- Corrected 120-item structured dev set: full predicates have dev row anchors, split metadata is explicit, 21 tests pass. Baselines on this set are now complete: base 0/120, SQL 120/120, SQL five-shot 120/120. Factual base 0/255; oracle context 245/255. See results_v3/dev/REPORT_A002_r3.md for slices and information-access limits. SQL ceiling persists despite removing answer-in-question leakage; the set remains narrow.
- Release validator rejects incomplete hashes, unscheduled seeds and malformed seed values, and now requires EXTERNAL Q42 approval evidence: the release must pin validation_v3/Q42_HUMAN_APPROVAL_A002.json and datasets_v3/probe_42_v3.jsonl, both pinned digests must match disk, the approval must record approved=true, and it must name the current benchmark bytes so a stale adjudication cannot certify a changed Q42 set. The release's own `q42_approval` string is no longer sufficient; previously flipping two fields unlocked all 18 runs. 35 rejection tests pass, including one asserting no approval artifact exists in the repository. This closes the mechanism only. The adjudication itself is gate 1 below and remains pending; neither approval file has been created.
- BD sampling now stratifies the partial repetition cycle JOINTLY across (join_arity, task_kind); every source and every complete cycle is retained. Within a stratum the order is a keyed sha256 digest of the example ID, not a lexicographic prefix. Maximum joint-stratum token-share deviation is 0.26% (controlled) and 0.13% (repeated-D), against +29.75% on the task-kind axis under the previous arity-only sampler; filter tasks are now repeated, where before none ever were. Whole-example rounding leaves the single `threshold` task (0.05% of D tokens) with no extra copy, reported rather than smoothed. Deviations, overshoot and ordering are recorded in BD_COMPOSITION_v3.md and BD_SAMPLING_MANIFEST_v3.json. Both earlier mixtures are archived under archive/pre_stratified_BD_2026-09-12 and archive/pre_joint_stratified_BD_2026-09-12. 10 repetition tests pass.
- Controlled BD: 3,512 items, 94,411 supervised tokens (B 47,202 / D 47,209). Repeated-D: 2,724 items, 94,418 tokens, 7 above controlled. BD_full unchanged: 3,460 items, 92,655 tokens. Controlled exceeds full by 1.90%; do not frame this as a substantial allocation contrast.
- Historical smoke evidence for controlled BD and repeated-D was produced on the ORIGINAL pre-stratification mixtures and still resolves to those input hashes, preserved in archive/pre_stratified_BD_2026-09-12. Those two smoke runs do not validate the current mixtures; the affected checks must be repeated if smoke-level evidence is wanted for them.
- CPT tail and empty-output-directory cases corrected. Three boundary tests verify every source token is preserved. D_sql rehearsal used 16 train examples, four dev examples, accumulation 8, three epochs, six optimizer steps and epoch eval/save. Train loss 0.88913, selected dev loss 0.24147. Selected weights match best checkpoint; reload logits identical. This is a configuration rehearsal, not a final quality result or one of the 18 runs.
- Ordered row, multi-column set and multipart JSON grading implemented with five synthetic regression tests; public parser dispatch tested. Q42 multipart SQL keys, gold keys, part IDs and columns agree. Versioned structured_prompt_v3.py defines multipart contracts; existing frozen baseline prompts remain unchanged.
- All eight current training recipes have actual shifted-label audits; 2,220/2,220 eligible factual observations remain covered. Current counts and configured step estimates are in validation_v3/resumption/TRAINING_LABEL_AUDIT_CURRENT.json.
- Base general sanity screen: 30/30. This is a floor screen, insufficient to establish absence of forgetting. Matched post-training scoring remains required.

## Evaluation coverage limitations to report with any result

The study evaluates more than the 42 business questions, but coverage is uneven and
must be stated as a limitation rather than assumed:

| Question type | Development | Sealed probes |
|---|---:|---:|
| Simple recorded facts | 255 | 2,820 recall + 2,820 paraphrase |
| Complete lists (processes/services/certifications) | 48 | 533 |
| Entity/attribute filtering | 96 | 1,306 held-in + 401 composition |
| Aggregation (counts) | 24 | — |
| Grouping / ranking | 0 | 15 (held out of training by design) |
| Multipart | 0 | 1 |
| Evidence-based analysis | 0 | 42 Q42 (33 diagnostic, 9 primary-eligible) |
| Unknown / no-match | 0 | 20 no-match + 2 insufficient-evidence |
| Clarification requests | 0 | 0 |

Known-company recall and held-out-company generalisation are already separated:
probe_fact_recall carries 2,220 `trained_fact` and 600 `heldout_entity` items.

`group_by`, `argmax_topk` and `limit_only` are withheld from training gold by the
frozen registry, so C/D/BD teach filter-family tasks only. This must not be described
as guaranteed failure on grouping or ranking, and equally must not be described as
likely success. The 120/120 SQL baseline covers filter and count questions only and is
no evidence either way about grouping or ranking. Transfer to those operations is
UNKNOWN and can only be established by measurement, on the 15-item held-out operation
probe. The study cannot claim competence at grouping or ranking, and cannot predict
the outcome in advance; it reports the measured generalisation result, whatever it is.

Multipart, evidence-based analysis and clarification-request coverage are genuinely
thin or absent in development. Expanding them requires a scoring method for answers
that have no executable SQL gold, which is the same unresolved adjudication problem
as Q42 and is not merely a matter of authoring more items. Any new benchmark also
needs its own unchanged-base baseline before a fine-tuned comparison means anything.

Finishing this controlled comparison does not demonstrate a capable domain assistant.
The broader operation coverage belongs to a separately versioned recipe.

## Still required before release / protected evaluation

1. Complete Q42 semantic adjudication and obtain the user's explicit approval. SQL execution proves consistency with recorded data, not that the question supports the proposed conclusion. Approval remains pending.
2. Offline final evaluation driver implemented in finetune/final_eval_v3.py: nine synthetic integration tests pass for all answer shapes, no-match handling, serialization, explicit probe scope and independent-seed summaries. CLI refuses protected inputs without a pinned Phase 40 approval and genuine Q42 approval evidence. Still required: final model-output generation/export integration, artifact sealing registration, and approved analysis contrasts/multiplicity and primary-Q42 inclusion. No protected outputs have been scored.
3. Build a reviewable release candidate from current inputs, code, environment and actual approval/gate evidence; do not create an approved release based only on booleans. Final hyperparameters need explicit frozen identities.
4. Confirm a durable backup destination and verify restore hashes for retained and future adapters and the V2 prediction corpus. No external backup is configured or verified; the destination question is pending.
5. Choose a broader matched general-capability evaluation before interpreting forgetting. Current arithmetic/copy screen is not sufficient. Additional dev paraphrases and analytical diversity remain limitations to report, not silently assumed evidence.

Current single-device configured totals (not observed final runs): A 20; B 807; C/D 492 each; BC/full BD 1,299; controlled BD 1,317; repeated D 1,023. A source: 35,071 tokens including EOS, 35 chunks and 35,036 shifted targets. Chat maximum length 244 versus 1,024 limit.

## Current review corrections

The earlier approval-binding and arity-only sampling defects are resolved by the evidence-bound gate and joint stratification described above. The gate register itself is now a mandatory release pin: omitting it or retaining a stale digest is rejected. Pinning a document establishes identity, not that its open tasks have been completed.

Protected-driver prompt/adapter identity manifest binding and exact multipart SQL counts are now implemented and covered by synthetic rejection tests. A new final-only unique-set prompt contract separates membership correctness from duplicate-format penalties; existing baseline prompts and judgments remain unchanged. Final generation/export must still create the independently pinned identities and sealing registration. The proposed broader evaluation rubric is in docs/EXPANDED_EVALUATION_RUBRIC.md; it is not approved gold or an observed model result.

The unapproved release candidate remains a historical proposal with stale pins, including this register and the subsequently edited trainer. Its limitations identify that drift. Regeneration requires a separate explicit user request immediately before release review; no regeneration or approval was performed by this correction.
