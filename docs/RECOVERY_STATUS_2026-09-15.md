# Recovery status — 2026-09-15

## Verified destination

Host `gylab-asimov1`, user `sm11926`, repository `/home/sm11926/GNEM_Finetuning`.
The repository is on `/home`, ZFS source `fast1/labs/Geng_Yuan_Lab`.
The source host reported by the user is `gylab-geass`; identical repository paths
on these hosts do not establish shared filesystems.

## Restored artifacts

The complete archives arrived through the user's Mac in
`.recovery/from_geass.c3xWVR/`. Both archive sizes and SHA-256 digests match
`manifest.json`. Thirty regular files and sixteen checkpoint links were restored,
including historical V2 predictions, smoke adapters and rehearsal weights/state.
Regular-file bytes were verified during restoration; existing differing files
would abort restoration rather than be overwritten.
See `validation_v3/resumption/ARTIFACT_RESTORE_2026-09-15.json`.

The verified chat archive remains preserved, without replacing active Codex state.
Earlier incomplete upload copies remain in place and are ignored by Git; do not
use them for restoration. Keep the complete Mac backup. This host's staging
archive alone does not establish durable off-host retention for future runs.

## Rebuilt runtime

Neither original virtual environment was present on this destination, and the
archives explicitly exclude environments and the downloaded base-model cache.
After user authorization to proceed, `.venv-v3-train` was reconstructed using
`validation_v3/resumption/TRAINING_ENVIRONMENT.lock`. It is not a copied or
independently tested source-host virtual environment. `.venv-v3` remains absent.
Use `.venv-v3-train/bin/python` for the checks validated here.

- All 65 recorded package versions match; `pip check` reports no broken requirements.
- Both NVIDIA A100 80GB GPUs passed a small bfloat16 matrix multiplication.
- Exact Qwen revision `cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8` tokenizer/config
  files were downloaded; tokenizer SHA-256 matches
  `c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539`.
- 143 tests passed across twelve suites, including the previously blocked
  structured-dev and training-token suites plus CPT boundary checks.

Full evidence: `validation_v3/resumption/REBUILT_RUNTIME_CHECKS_2026-09-15.json`.
Earlier failure reports are preserved as historical observations.

## Remaining work

1. Base weights at the exact pinned revision are now downloaded. Both synthetic
   base and diagnostic-adapter rehearsals passed on this host, with repeated
   token IDs matching and valid export identities. Loaded diagnostic adapter
   tensors match saved weights. Evidence is in
   `validation_v3/generation_rehearsal_2026-09-15/HOST_VERIFICATION.json`.
   These checks establish same-loaded-model repeatability, not full reload
   reproducibility or domain competence. Original rehearsal evidence is preserved.
2. Continue independent generation/export/scoring review and broader development
   evaluation preparation described in `docs/CURRENT_REVIEW_AND_NEXT_STEPS.md`.
3. Resolve final release requirements, including durable artifact storage,
   evaluation/analysis decisions and explicit Q42 adjudication when the user
   chooses to resume it.

Final training remains **0/18**. No protected inference, Q42 approval, generation
release, scoring release or training candidate regeneration was performed during
recovery. Q42 review remains deferred; candidate regeneration still requires an
explicit user request. Recovery work does not approve the experiment for release.
