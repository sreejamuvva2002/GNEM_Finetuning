# Review of the 62 Source Control files — 2026-09-15

Inventory captured before this review document was added: **5 modified, 57 new, 0 deleted**. All changes are relative to recovered commit `2b0a750`; the 57 new paths did not exist in that commit. This report adds one file, making the intended checkpoint 63 paths. No files are deleted to reduce the count.

## Review outcome

Ready for an intermediate preservation commit, not final experiment release. Runtime comparison fixes, environment identity, recovery evidence and draft evaluation work are appropriate to retain. Historical failure reports remain because they document the earlier incomplete environment. No final models, approvals or protected evaluation results are claimed.

## Counts

| Group | Modified | New | Total |
|---|---:|---:|---:|

| code/tests/config | 4 | 8 | 12 |

| documentation | 1 | 6 | 7 |

| evaluation drafts and review artifacts | 0 | 9 | 9 |

| model outputs and associated evidence | 0 | 26 | 26 |

| recovery and validation evidence | 0 | 8 | 8 |

## Complete inventory

### code/tests/config

| Status | Path | Purpose / disposition |
|---|---|---|

| Modified | `.gitignore` | Necessary: excludes private recovery uploads. |

| Modified | `finetune/final_generate_v3.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| Modified | `finetune/final_generation_tests.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| Modified | `finetune/generation_core_v3.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| New | `finetune/audit_dev_multipart_r1.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| New | `finetune/build_dev_ambiguity_v3.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| New | `finetune/build_dev_review_packet_v3.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| New | `finetune/build_dev_supplier_evidence_v3.py` | Implementation/test or reproducible draft/audit builder; retained source. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/rehearse_adapter_generation_v3.py` | Dated copy of synthetic runner; necessary to reproduce that retained rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/rehearse_generation_v3.py` | Dated copy of synthetic runner; necessary to reproduce that retained rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/rehearse_adapter_generation_v3.py` | Dated copy of synthetic runner; necessary to reproduce that retained rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/rehearse_generation_v3.py` | Dated copy of synthetic runner; necessary to reproduce that retained rehearsal. |

### documentation

| Status | Path | Purpose / disposition |
|---|---|---|

| Modified | `docs/CURRENT_REVIEW_AND_NEXT_STEPS.md` | Documentation: current status, draft rubric/analysis plan or focused engineering review. |

| New | `LAB_UPDATE_RECOVERY_2026-09-13.md` | Exact duplicate of docs/ handoff; retained convenience copy, not a new experiment result. |

| New | `docs/DEV_AMBIGUITY_R1_DRAFT.md` | Documentation: current status, draft rubric/analysis plan or focused engineering review. |

| New | `docs/DEV_SUPPLIER_EVIDENCE_R1_DRAFT.md` | Documentation: current status, draft rubric/analysis plan or focused engineering review. |

| New | `docs/FINAL_ANALYSIS_PLAN_DRAFT_2026-09-15.md` | Documentation: current status, draft rubric/analysis plan or focused engineering review. |

| New | `docs/GENERATION_REVIEW_2026-09-15.md` | Documentation: current status, draft rubric/analysis plan or focused engineering review. |

| New | `docs/RECOVERY_STATUS_2026-09-15.md` | Documentation: current status, draft rubric/analysis plan or focused engineering review. |

### evaluation drafts and review artifacts

| Status | Path | Purpose / disposition |
|---|---|---|

| New | `datasets_v3/dev_ambiguity_r1_draft_v3.jsonl` | New unapproved development draft; separate from existing training/protected inputs. |

| New | `datasets_v3/dev_supplier_evidence_r1_draft_v3.jsonl` | New unapproved development draft; separate from existing training/protected inputs. |

| New | `validation_v3/DEV_AMBIGUITY_R1_DRAFT_CHECKS.json` | Generated source pins or draft validation evidence; not human adjudication. |

| New | `validation_v3/DEV_AMBIGUITY_R1_DRAFT_MANIFEST.json` | Generated source pins or draft validation evidence; not human adjudication. |

| New | `validation_v3/DEV_SUPPLIER_EVIDENCE_R1_DRAFT_CHECKS.json` | Generated source pins or draft validation evidence; not human adjudication. |

| New | `validation_v3/DEV_SUPPLIER_EVIDENCE_R1_DRAFT_MANIFEST.json` | Generated source pins or draft validation evidence; not human adjudication. |

| New | `validation_v3/dev_review_packet_2026-09-15/REVIEW_DECISIONS.csv` | Generated blank human decision template; no approvals or reviewer identities filled. |

| New | `validation_v3/dev_review_packet_2026-09-15/REVIEW_PACKET.md` | Generated readable draft questions, source context and reviewer-only fact sheets. |

| New | `validation_v3/dev_review_packet_2026-09-15/manifest.json` | Generated review packet/input hashes; blank template provenance. |

### model outputs and associated evidence

| Status | Path | Purpose / disposition |
|---|---|---|

| New | `results_v3/dev/base_multipart_r1_audit_2026-09-15/REPORT.md` | Derived audit of existing dev outputs; historical source results unchanged. |

| New | `results_v3/dev/base_multipart_r1_audit_2026-09-15/audit.json` | Derived audit of existing dev outputs; historical source results unchanged. |

| New | `results_v3/dev/base_multipart_r1_audit_2026-09-15/parts.jsonl` | Derived audit of existing dev outputs; historical source results unchanged. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/ENVIRONMENT_BINDING_VERIFICATION.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/base/identity.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/base/predictions.jsonl` | Generated two-question synthetic output; not protected benchmark inference. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/base/registration.json` | Generated unapproved export registration; no release authority. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/base/runtime.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/base/verification.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/diagnostic_D_sql/identity.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/diagnostic_D_sql/predictions.jsonl` | Generated two-question synthetic output; not protected benchmark inference. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/diagnostic_D_sql/registration.json` | Generated unapproved export registration; no release authority. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/diagnostic_D_sql/runtime.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_environment_rehearsal_2026-09-15/diagnostic_D_sql/verification.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/HOST_VERIFICATION.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/RUNNER_PROVENANCE.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/base/identity.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/base/predictions.jsonl` | Generated two-question synthetic output; not protected benchmark inference. |

| New | `validation_v3/generation_rehearsal_2026-09-15/base/registration.json` | Generated unapproved export registration; no release authority. |

| New | `validation_v3/generation_rehearsal_2026-09-15/base/runtime.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/base/verification.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/diagnostic_D_sql/identity.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/diagnostic_D_sql/predictions.jsonl` | Generated two-question synthetic output; not protected benchmark inference. |

| New | `validation_v3/generation_rehearsal_2026-09-15/diagnostic_D_sql/registration.json` | Generated unapproved export registration; no release authority. |

| New | `validation_v3/generation_rehearsal_2026-09-15/diagnostic_D_sql/runtime.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

| New | `validation_v3/generation_rehearsal_2026-09-15/diagnostic_D_sql/verification.json` | Generated runtime/identity/verification evidence for dated synthetic rehearsal. |

### recovery and validation evidence

| Status | Path | Purpose / disposition |
|---|---|---|

| New | `validation_v3/resumption/ANALYSIS_DESIGN_CHECKS_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/ARTIFACT_RESTORE_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/POST_UPDATE_RECOVERY_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/POST_UPDATE_TESTS_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/PREPARATION_CHECKPOINT_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/REBUILT_RUNTIME_CHECKS_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/RECOVERY_HOST_IDENTITY_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

| New | `validation_v3/resumption/STRICT_RUNTIME_MATCH_TESTS_2026-09-15.json` | Generated recovery, regression or design check evidence; retained historical checkpoint. |

## Preservation and duplicates

The root LAB_UPDATE_RECOVERY note is byte-identical to its existing docs/ counterpart. It is retained as the user-visible convenience copy. Dated rehearsal runners intentionally duplicate earlier scripts with output/root/provenance changes; the first and second September 15 rehearsal series use different runtime identity code. Matching prediction bytes across them do not make their runtime evidence redundant. The multipart report and parts file are derived from retained outputs, not another inference run. Temporary setup/verification scripts remain under /tmp and are not in this change set.

## Original files unchanged

Fresh Git blob comparisons verified **133 tracked files** in datasets_v3, kb and results_v3, plus the proposed run schedule and training release candidate, against 2b0a750. Existing training sets, workbook, holdout/benchmark files and tracked historical predictions are unchanged. The excluded full V2 prediction corpus was restored from the checksum-verified archive; it is not in Git and is covered separately by ARTIFACT_RESTORE_2026-09-15.json.

## Privacy and exclusions

git check-ignore confirmed the private .recovery folder, misplaced recovery copies, root archives, virtual environment paths, representative restored weights and full V2 predictions are ignored. git ls-files found no tracked archive/weight/virtual-environment/Codex-snapshot/auth.json/private-key paths in the checked patterns. A scan of every proposed text file found no private-key blocks or common GitHub/Hugging Face/OpenAI token patterns. This is a targeted check, not a guarantee against every possible secret format. No credentials were copied into the commit. Runtime metadata includes repository/cache paths, hostname and package/hardware versions, not credentials or chat contents.

## Validation and boundaries

All proposed Python files parse, JSON/JSONL files parse, and the 32 decision rows remain blank. The preparation checkpoint records 151 passing tests. The final precommit command `.venv-v3-train/bin/python -m unittest discover -s finetune -p '*tests.py'` passed all 157 discovered tests (exit 0). Full domain validity, actual release specs, forgetting battery and final analysis decisions remain open. Q42 review stays deferred and candidate regeneration requires explicit user instruction. Final training: **0/18**. No reviewer was selected on the user’s behalf.

## Precommit notes

The generated CSV uses standard CRLF line endings. The initial staged whitespace
check flagged carriage returns; rerunning with Git cr-at-eol recognition passed.
CSV bytes and their existing manifest pins were preserved. This host had no Git
author identity configured; the commit uses the identity from the preceding three
repository commits as command-local settings, without changing global Git config.
