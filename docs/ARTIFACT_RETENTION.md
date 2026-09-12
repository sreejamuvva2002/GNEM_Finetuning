# Current excluded-artifact retention

These artifacts are excluded from ordinary Git and remain only at the local repository paths listed below as far as this audit can establish. **No additional backup is configured or verified.** GitHub does not contain these files; losing the local copies would lose the exact saved adapters and the complete historical prediction corpus. A checksum verifies identity but cannot recover a missing file. This audit does not claim to have searched every external storage system.

| Local path | Files | Logical bytes | Backup status |
|---|---:|---:|---|
| `validation_v3/smoke_models/*/selected_adapter/adapter_model.safetensors` | 8 | 4,404,745,472 | No verified backup |
| `archive/smoke_prefix_pilot_2026-09-11/smoke_models/*/selected_adapter/adapter_model.safetensors` | 8 | 4,404,745,472 | No verified backup |
| `validation_v3/rehearsal_models/**` (weight/state files) | 13 | 3,043,488,313 | No verified backup |
| `review_v2_questions/all_predictions.jsonl` | 1 | 158,826,666 | No verified backup |

The 16 smoke weight files total 8.20 GiB. The prediction corpus is approximately 151.47 MiB. Checkpoint symlinks resolve to these same selected files and are not additional backups. Hash evidence is retained in [the cleanup manifest](../validation_v3/resumption/CLEANUP_RUNTIME_2026-09-11.json) for adapters and [the V2 output manifest](../review_v2_questions/OUTPUT_MANIFEST.json) for the prediction corpus.

Completed smoke optimizer/scheduler/RNG states were intentionally deleted during cleanup; optimizer-state resume is unavailable. Selected adapters, tokenizers and inference evidence were retained. No final adapters exist yet. Before final training, select durable storage, copy the retained and future artifacts, verify hashes at the destination, and record restore instructions. No upload, deletion or backup was performed by this documentation change.

The rehearsal adds 2.83 GiB of excluded weight/state content. Unlike completed smoke checkpoints, its checkpoint directories retain optimizer, scheduler and RNG state; they support resume with compatible code and environment (resume itself has not been tested). All copies remain local; no backup is verified.
