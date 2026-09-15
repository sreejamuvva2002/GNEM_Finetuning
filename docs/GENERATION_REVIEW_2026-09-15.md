# Protected generation review — 2026-09-15

Scope: inspected final_generate_v3.py, generation_core_v3.py and
prediction_export_v3.py, with synthetic regression checks. This is a focused
review, not final release approval or a complete scientific review.

## Fixed: specification type substitutions passed exact-match checks

`final_generate_v3.verify_runtime` compared dictionaries with ordinary Python
equality, which accepts False == 0 and True == 1 recursively. The prompt-config
check used the same comparison. Specifications changing nested decoding or
runtime types therefore passed the claimed exact comparison. Runtime matching
now checks types recursively, disallows non-JSON values and non-finite floats,
and preserves dictionary-key order independence. Prompt matching uses the same
comparison before backend loading. Missing runtime dictionaries are rejected.

Three additional tests cover nested substitutions, non-JSON/missing values, and
prompt substitution refusal before model loading. Five affected suites pass:
36 tests in total. Evidence: validation_v3/resumption/STRICT_RUNTIME_MATCH_TESTS_2026-09-15.json.

## Runtime identity scope — initial finding, resolved below

LocalTransformersBackend.runtime records the model ID/revision, dtype, attention
implementation, device map, adapter directory, generation configuration,
tokenizer serialization hash and template hash. It does not currently include
Python/package versions, CUDA runtime/driver or GPU identity. The rehearsal
scripts record some packages separately, but that does not make them enforced
fields in protected generation's approved backend_runtime specification.
Consequently exact matching currently establishes equality only for the fields
actually collected; it does not establish an identical software/hardware runtime.
These fields need collection and explicit matching before final per-run
specifications are finalized. The restored host uses A100 GPUs rather than the
original A6000 rehearsal hardware.

## Remaining release work

- Complete runtime identity scope and review actual per-run specifications.
- Complete scoring registration, planned contrasts and broader evaluation.
- Obtain Q42 adjudication and durable storage evidence before release under the
  existing protocol. Q42 remains deferred; no approval was created.

Historical results and prompt artifacts remain unchanged. The protected entry
point code hash changed, so historical code pins are historical evidence only;
future releases must pin the revised code. No candidate was regenerated, no
protected inference or scoring ran, and final training remains 0/18.

## Follow-up: environment identity now enforced

LocalTransformersBackend now includes an environment identity in its runtime
object: all installed distribution versions, Python/platform, CUDA/cuDNN and
NVIDIA driver versions, selected GPU type/index/name/capability/memory, and
effective deterministic, TF32, SDPA and CUBLAS workspace settings. Failure to
establish the driver or duplicate package metadata aborts collection. Exact
protected-runtime comparison now includes these fields before protected tasks
are parsed. GPU serial identity is intentionally not required; this records
hardware characteristics rather than an inventory asset identifier.

37 tests pass across five affected suites. Real base and diagnostic-adapter
rehearsals both pass with the expanded environment metadata, repeated token IDs
match, exports validate, and loaded adapter tensors match saved weights. The
real serialized runtime also passes strict comparison and rejects driver drift.
Evidence: validation_v3/generation_environment_rehearsal_2026-09-15/ENVIRONMENT_BINDING_VERIFICATION.json.

These are observations and rejection checks, not approved per-run specifications.
Runtime metadata is not proof of full reload or cross-machine determinism. Base
weight revision identity still relies on the pinned local model cache; the
runtime object does not independently hash every loaded base tensor. The
remaining release work above continues to apply. Earlier code/runtime evidence
is preserved and is not claimed to validate these later edits.
