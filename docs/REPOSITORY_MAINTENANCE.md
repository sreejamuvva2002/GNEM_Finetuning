# Repository maintenance — 12 September 2026

The root README is the current entry point; V3_UPDATED_REVIEW_AND_PLAN.md is the roadmap and V3_PHASE_STATUS.md is the status authority. The two detailed reference documents in this directory preserve pre-cleanup README/CLAUDE bytes. Their old relative links and line references use the original repository-root context; they are snapshots, not current status reports. A-002 supersedes conflicting historical instructions.

The cleanup removed completed two-step smoke optimizer, scheduler and RNG state. Byte-identical checkpoint files were replaced with relative links to each run's selected_adapter, preserving checkpoint paths such as adapter_config.json. Every selected adapter, configuration, tokenizer, loss record, trainer state and raw result was retained. Smoke optimizer-state resume is no longer supported. No final training checkpoint was deleted; none exists.

The [cleanup manifest](../validation_v3/resumption/CLEANUP_RUNTIME_2026-09-11.json) records each removed file or replacement, exact hashes, and 12.62 GiB of redundant file content removed. This is a logical byte count, not a claim about physical filesystem allocation. Source, dataset, result and selected-adapter hashes were checked before and after cleanup. Python bytecode caches were also removed.

Retain old registries/approvals, source and review manifests, logs, pilot predictions and archived plans. They explain the experiment's history and remain referenced by code or audit records. Current code uses phase9_freeze_a002.py for the active registry; the original Phase 9 scripts describe the older value-withholding policy.

No model training or inference was launched by this cleanup. Q42 approval remains pending at the user's direction. Broader analytical development coverage and final scoring integration remain open before final training.

## Git milestone policy — 12 September 2026

Ordinary Git retains code, datasets, source workbook, raw development outputs, configuration, tokenizer files, metrics and manifests. Weight/state files (*.safetensors, *.pt, *.pth) and review_v2_questions/all_predictions.jsonl stay at their existing local paths and are ignored. Their manifest hashes remain tracked. No remote artifact backup is configured or verified; a clone cannot reproduce the exact saved adapters without these local files, although training inputs and pinned model identity remain available. This limitation is a final-training storage gate. Symlinks to ignored weights are ignored by extension too. No Git garbage collection or pruning was performed.

Historical root README/CLAUDE references are preserved byte-identically in docs/PHASE_PROTOCOL_REFERENCE.md and docs/EXECUTION_RULES_REFERENCE.md. Relative links inside those snapshots resolve using their original root context: use ../ for root targets when navigating manually. Historical Chat 2.txt is at ../archive/planning_before_cleanup_2026-09-11/Chat 2.txt; Chat 1.txt remains at the root as historical conversation evidence. No historical snapshot was silently rewritten.
