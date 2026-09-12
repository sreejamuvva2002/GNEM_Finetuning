# Remaining pre-training gates — 12 September 2026

Final runs: 0/18. Q42 approval remains pending by explicit user decision.

This supersedes the remaining_gates list in GLOBAL_AUDIT_A002.json, a historical construction snapshot. Micro runtime checks, four development baselines and eight representative smoke recipes are completed. Earlier runtime/cleanup hash manifests remain snapshots of their dates.

1. Replace the 51 structured dev questions: every gold company name appears in its question. They are unsuitable for checkpoint selection. Cover non-tautological dev entities, counts and joins of arity 1–2 without contaminating held-out operations/compositions. Correct misleading split metadata.
2. Finish and test natural-language top-k/multipart scoring, Q42 multipart gold handling and all final reporting paths before protected evaluation.
3. Complete Q42 adjudication and obtain the user's approval. Do not create an approved release merely to bypass this gate.
4. Strengthen the release validator: require a nonempty complete artifact hash map and an explicit 18-run variant/seed schedule. Release file validation_v3/TRAINING_RELEASE_A002.json remains absent.
5. Rehearse accumulation 8, epoch evaluation/save and best-checkpoint reload. Resolve empty-output-directory and one-token CPT-tail edge cases before final training.
6. Review BD repetition distribution. Currently the 45 extra D records in controlled BD all have join arity 1; repeated-D's 96 triple-counted records also have arity 1. This is disclosed, not accepted as the final balancing design.
7. Predeclare near-identity: BD_full has 92,655 supervised tokens; controlled BD 94,407, only 1.89% more. Do not interpret this as a substantial supervision-allocation contrast.
8. Score and assess the limited general-capability sanity screen; decide whether broader forgetting evaluation is needed.
9. Confirm durable external storage for all 18 final adapters. Local retention and hashes alone are not a remote backup.

The seven chat variants have a shifted assistant-label audit. A_cpt uses a different objective: 34,923 passage tokens plus 148 EOS = 35,071 input tokens; longest passage including EOS is 340. Manual 1,024-token stream chunks give 35 sequences and 35,036 shifted supervised targets per pass (one initial target is lost per chunk). No TRL packing flag is used.

Current single-device defaults (not approved final settings): batch 1, accumulation 8, A four epochs, others three. Installed Transformers 4.56.2 set_initial_training_values computes ceil(sequence_count/8) updates per epoch. Planned totals: A 20; B 807; C 492; D 492; BC 1,299; BD_full 1,299; BD_controlled 1,317; D_repeat 1,020. Final measured steps must be recorded separately.
