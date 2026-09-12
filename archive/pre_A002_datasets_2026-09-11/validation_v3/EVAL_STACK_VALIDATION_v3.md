# EVAL_STACK_VALIDATION_v3

Phase 8 — build the v3 evaluation and reporting stack.

> **This filename is a Phase 8 implementation/provenance convention.** `README.md` and `CLAUDE.md` do not prescribe a dedicated Phase 8 validation-artifact filename. README was not amended to name it.

> Every number in this document comes from **deterministic synthetic fixtures**. Nothing here is an experimental result.

## Frozen Phase 7 inputs

```text
datasets_v3/gnem_v3.sqlite         7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b
finetune/sqlexec_v3.py             f2f7f206b1083370a213c82d4428299fec65ab0153767ca6d850b711a8cce7b2
finetune/grade_v3.py               c7775cdcf69f11705eb35a172202cc917648fa6df149a13c8cb8d217e63cfb04
finetune/phase7_grader_tests.py    bcdbdbb67211321c8ebd50e2d5a8eeb6908c5fb7b7b692a8cf028ba76b16d8b6
```

## Stack modules

```text
finetune/eval_records_v3.py               2b92d82a49ccd3d8a3a901ce14b33569c665c255ef9120c3fb302cc2f83058f9
finetune/eval_stats_v3.py                 eee51e3897a41fee1288adb95da5826dd719cf9df3e2b6ca38e9ea2227a513b5
finetune/eval_report_v3.py                75113c4372dd2ae76b2e146a5e51774886b5df22cafcda56f09d46b5ec7799fa
finetune/eval_verify_v3.py                839a04a04e17f293060385b38a48f7dfc293d2a0d1801dbade4d846c5629f665
finetune/phase8_eval_stack_tests.py       5bfb2c3934cb5f255ef37b5f0d71090d6928b5ecd3127f5fb985b4d601953e29
```

Rebuilt v3-native rather than ported. v2's stack is 4,213 lines and `report.py` alone carries 111 retired-concept references; README Phase 8 warns that recreating it "would add risk rather than remove it". Only the statistical METHODS were carried across as concepts, reimplemented against the v3 schema — no v2 file was copied.

## Fixture manifest

```text
validation_v3/fixtures_v3/fixture_records_v3.jsonl   dee9db4ed0990901ee005a457ea28fa2ae466193b8519085eb89aa244f87467a
validation_v3/fixtures_v3/fixtures_manifest_v3.json  ac7363186c33a9e23cafad38e34c0902447aa9e8676befd08e8fbd5d08a3c14a
validation_v3/fixtures_v3/summary_v3.json            8f892a730a9413585cb654d641de942721ffcbc9c24808dab704369eeab600de
validation_v3/fixtures_v3/error_analysis_v3.json     a662aaa3ba75d440eae83ccbc613c08e072ac608688f155c9650eb8e75a95216
validation_v3/fixtures_v3/REPORT_v3.md               e3f8d3190f3a11fa016ef9e29a4d458dd9dd0d9966a7e5a2ff3d1e6a2e6129ac
fixture item count                                   18
families                                             factual_recall, no_match, structured_heldin, structured_paraphrase
```

The fixture-local `REPORT_v3.md` is a **skeleton** carrying a synthetic banner. The authoritative repo-root `REPORT_v3.md` is created only at **Phase 42** and does not exist yet.

## Result-record schema

21 fields, covering every README Phase 40 retention requirement — `example_id`, question, raw output, parsed output, generated SQL, execution result, gold, score, error type, adapter hash, prompt hash — plus the frozen Phase 7 grading metadata. README's rule is explicit: **never scores alone**.

```text
  example_id, family, condition, question, raw_output, parsed_output, generated_sql, execution_result, gold, answer_type, target_columns, task_result_correctness, strict_result_schema_accuracy, status, error_type, error_detail, prompt_hash, adapter_hash, seed, grader_version, grader_sha256
```

The status vocabulary is imported from the frozen Phase 7 grader rather than redeclared, so the two cannot drift apart.

## Status and denominator accounting

```text
expected item count   18
scored                12
failed                6
scored + failed       18
invariant holds       True
```

| status | count |
|---|---|
| `correct` | 8 |
| `incorrect` | 4 |
| `generation_failure` | 1 |
| `parse_failure` | 1 |
| `SQL_error` | 1 |
| `timeout` | 1 |
| `truncated_output` | 1 |
| `invalid_output` | 1 |

All eight frozen statuses are exercised. Every item ends in exactly one, and non-success counts against the denominator — no item disappears, counts twice, or silently becomes correct.

## Primary and secondary metrics

| metric | role | fixture value |
|---|---|---|
| `task_result_correctness` | **primary** | 8 / 18 = 44.4% |
| `strict_result_schema_accuracy` | secondary | 11 / 18 = 61.1% |

Fixtures prove the two can diverge in **both** directions — `fx07` is task-correct with a wrong schema, `fx08` is task-wrong with a correct schema — so the secondary can never stand in for the primary.

## Per-family metrics

| family | n | correct | incorrect | failed | task | schema |
|---|---|---|---|---|---|---|
| `factual_recall` | 7 | 3 | 2 | 2 | 42.9% | 71.4% |
| `no_match` | 1 | 1 | 0 | 0 | 100.0% | 100.0% |
| `structured_heldin` | 9 | 3 | 2 | 4 | 33.3% | 44.4% |
| `structured_paraphrase` | 1 | 1 | 0 | 0 | 100.0% | 100.0% |

Families are discovered from the records. A previously unseen family (`brand_new_family_v3`) appears in the summary with **no code edit**, which is the property v2's hard-coded `REPORT_ORDER` lacked.

## Error analysis

10 synthetic failures grouped by status, family and `answer_type`, distinguishing the frozen outcome classes:

| class | count |
|---|---|
| `incorrect_valid_prediction` | 4 |
| `generation_failure` | 1 |
| `parse_failure` | 1 |
| `SQL_error` | 1 |
| `timeout` | 1 |
| `truncated_output` | 1 |
| `invalid_output` | 1 |

No scientific error taxonomy is invented from probes that do not exist.

## Statistical plumbing

Every method maps to an explicit live-protocol requirement. Nothing is included because v2 had it.

| method | frozen requirement |
|---|---|
| per-seed scores | README:972, CLAUDE.md:826 |
| mean ± SD | README:972, CLAUDE.md:827 |
| effect size | README:972, CLAUDE.md:828 |
| paired item-level bootstrap | README:972, CLAUDE.md:829 |
| exact denominators | README:972, CLAUDE.md §28 |
| Holm correction | README:974 |
| McNemar (secondary) | README:973 |
| split-group weighting | README:990-991, CLAUDE.md:847-854 |

**Deferred: hierarchical bootstrap.** v2 implemented it; the live protocol never mentions it, so it is not introduced here.

Fixture outputs (synthetic inputs, no significance claim):

```text
per-seed scores            {11: 0.8, 22: 0.84, 33: 0.82}
mean +/- SD                0.8200 +/- 0.0200 (n=3)
baseline SD                refused (deterministic condition)
effect size (d_z)          0.5040
paired bootstrap 95% CI    [-0.1250, 0.8750]
bootstrap items            8
Holm-adjusted              {'B_vs_base': 0.03, 'D_vs_base_sql': 0.08, 'BD_vs_Drepeat': 0.2}
McNemar p (secondary)      1.0
split_group-weighted       0.7500 over 2 groups
item-weighted              2 / 3 = 66.7%
```

A deterministic baseline is **refused** an SD rather than reported as 0.0, per README:976-979. Split-group weighting averages within group then across groups unweighted, and excludes the non-attributable aggregate item as undefined.

## Verification and regrade

Verify checks expected count, unique `example_id`, exactly-one-status, required fields, provenance, denominator integrity, duplicates and silently dropped families. Regrade re-runs the frozen Phase 7 grader over retained raw predictions, carries the raw prediction, gold and question through untouched, and stamps grader version and hash — it never repairs SQL, changes gold, or overwrites without provenance.

## Sealed-test guard

Test and Q42 remain `LOCKED_UNTIL_PHASE_40`. Validated with **synthetic sealed fixtures only** — no real test or Q42 prediction, example, gold, score or error case was created, read, reported or inferred.

### Correction history — two successive defects, both reproduced

**Stage 1 — the original family-based design (fail-open).** The first Phase 8 candidate inferred sealing from `family` strings **inside the records**. Independent review demonstrated three failures, all reproduced before the redesign:

1. a sealed artifact whose records declared `family = factual_recall` was **accepted** by `load_dev_results` — content classified itself
2. `classify_result_set("brand_new_future_family")` returned `dev` — an unknown future family silently defaulted **open**
3. `sealed_metadata` **parsed sealed records** to compute `families` and `conditions`, exceeding the pre-Phase-40 metadata boundary

**Stage 1 root cause:** the sealing decision was attached to what the artifact said about itself rather than to the artifact, and the default for an unrecognised value was open rather than closed.

**Stage 2 — the first registry redesign (still caller-controlled).** Replacing family strings with an `ArtifactRegistry` fixed content-based classification, but the registry was **constructed and passed by the caller**. Independent review reproduced two further bypasses: an ordinary caller could build a second registry declaring the same sealed path as `dev` and load it, and could mutate an existing registry in place via `register(...)`. The trust boundary had merely moved from caller-controlled *family* to caller-controlled *registry declaration*. **This stage was not sufficient, and the audit does not present it as though it were.**

**Stage 3 — trusted authority (current).** Classification now comes from a frozen manifest loaded by one internal factory into an immutable authority. Ordinary dev/report code may QUERY classification and cannot redefine it.

### The current design: trusted, immutable classification authority

```text
identify artifact (resolved canonical path)
    -> trusted registry lookup + integrity hash
    -> classification: dev | sealed | unknown
    -> sealed or unknown  -> REFUSE
    -> only an authorized dev artifact is opened and parsed
```

`family`, `condition`, `status`, filename keywords and record contents take **no part** in the security decision. Identity is the resolved canonical path plus the registered SHA256; the manifest predeclares `item_count`, so metadata never requires opening sealed content.

**Classify-before-parse is proved, not asserted.** One synthetic sealed fixture contains deliberately unparseable bytes (`<<<NOT-JSON-AT-ALL>>>`). It raises `SealError`, never a JSON error — so authorization demonstrably happened before any parser ran. `sealed_metadata` returns full metadata for that same unparseable artifact. That is possible because it reads raw bytes only to verify the registered hash and **never parses record content**.

### Trust boundary

```text
frozen trusted manifest
    -> internal factory (_build_authority_from_manifest)
    -> validated deterministically, conflicts rejected
    -> IMMUTABLE authority
    -> dev/report code QUERIES it; cannot redefine it
```

`load_dev_results(path)` and `sealed_metadata(path)` take **no** registry, authority, manifest, unseal, allow_test, bypass_seal or force argument, so a caller has nowhere to attach a competing authority. The authority exposes no `register`, its mappings are read-only, and attribute assignment raises. Conflicting manifest entries — the same path with different kinds, or the same `artifact_id` with a different path/hash/kind — are rejected rather than resolved last-write-wins. An uninitialized authority refuses rather than defaulting open.

**Threat model, stated accurately.** This is a workflow-integrity and accidental-leakage boundary, not a sandbox against hostile code. Arbitrary Python with full module and filesystem access can always reach private names; Phase 8 does not claim otherwise. The guarantee is the narrower one the protocol needs: **the normal supported dev/report API offers no route to reinterpret a sealed artifact as dev.** Phase 8 fixtures stand up synthetic trusted environments through an explicitly underscore-prefixed, fixture-only hook that is not part of that API.

The synthetic `trusted_artifacts_v3.json` used by the gate validates the ARCHITECTURE only. It is not, and does not claim to be, the future real test manifest.

**Fail closed.** An unregistered artifact, a copied artifact at a new path, and a registered path whose bytes no longer match its hash all classify `unknown` and are refused. Unknown never becomes dev.

**Path identity.** Absolute, relative and dotted spellings resolve to one identity, and a symlink pointing at a registered sealed artifact remains sealed.

**Restricted metadata contract.** `sealed_metadata` may read raw bytes for integrity hashing but never parses or exposes evaluation-record content. It returns exactly: `artifact_id`, `artifact_path`, `sha256`, `item_count`, `schema_version`, `provenance`, `artifact_kind`, `records_parsed`. No family, condition, status, score, error type, answer type, question, gold, SQL or execution result — and no per-family or score distribution.

**No pre-Phase-40 unseal capability.** There is no `unseal` parameter on any dev or library API; a generic boolean switch would also unlock real sealed output later. The real unblind authority belongs to the Phase 40 entry point (`CLAUDE.md` §23) and is deliberately not created here.

The seal boundary is enforced at **ingress**. `summarize` and `error_analysis` are pure computations over already-authorized records and deliberately no longer re-derive sealing from record content, since that is the unsound check this replaced.

## Retired components

None of 15 retired concepts appear in the stack, and no v2 repository path or v2 database fallback exists. The stack opens no database connection of its own: SQL fixtures call the approved Phase 7 executor.

## Validation

| check | result | detail |
|---|---|---|
| `phase7_frozen_hashes_unchanged` | PASS | DB, executor, grader and Phase 7 tests all match |
| `record_schema_carries_retention_fields` | PASS | 21 fields incl. every README Phase 40 retention field; never scores alone |
| `status_vocabulary_sourced_from_phase7` | PASS | 8 statuses imported from the frozen grader, not redeclared |
| `verify_accepts_good_fixture` | PASS | 18 records, 18 unique ids, exactly-one-status holds |
| `denominator_invariant_scored_plus_failed` | PASS | scored 12 + failed 6 == expected 18 |
| `all_eight_statuses_represented` | PASS | ['SQL_error', 'correct', 'generation_failure', 'incorrect', 'invalid_output', 'parse_failure', 'timeout', 'truncated_output'] |
| `failures_counted_in_denominator` | PASS | denominator 18 includes all 6 failures |
| `metrics_distinct_task_ok_schema_wrong` | PASS | task=1.0 schema=0.0 |
| `metrics_distinct_task_wrong_schema_ok` | PASS | task=0.0 schema=1.0 |
| `metrics_not_merged` | PASS | primary 0.444 != secondary 0.611 |
| `per_family_metrics_data_driven` | PASS | 4 families discovered from records: ['factual_recall', 'no_match', 'structured_heldin', 'structured_paraphrase'] |
| `new_family_needs_no_code_edit` | PASS | a previously unseen family appears with no REPORT_ORDER edit |
| `error_analysis_distinguishes_classes` | PASS | 10 failures grouped by status, family and answer_type |
| `stats_per_seed_and_mean_sd` | PASS | per-seed {11: 0.8, 22: 0.84, 33: 0.82}, mean±SD n=3 |
| `stats_refuses_baseline_sd` | PASS | a deterministic baseline is refused an SD (README:976-979) |
| `stats_paired_bootstrap_deterministic` | PASS | identical CI across runs at seed 20260824 |
| `stats_effect_size_and_holm` | PASS | effect size computed; Holm adjustment monotonic |
| `stats_constant_-1.0_effect_undefined` | PASS | zero variance has undefined standardized effect; raw difference retained |
| `stats_constant_0.0_effect_undefined` | PASS | zero variance has undefined standardized effect; raw difference retained |
| `stats_constant_1.0_effect_undefined` | PASS | zero variance has undefined standardized effect; raw difference retained |
| `stats_mcnemar_present_cited` | PASS | McNemar implemented as secondary evidence (README:973) |
| `stats_split_group_weighting_cited` | PASS | average within split_group then across groups; aggregate item excluded as undefined (CLAUDE.md:847-854) |
| `stats_hierarchical_bootstrap_deferred` | PASS | not implemented: absent from the live protocol, so deferred not invented |
| `regrade_preserves_raw_and_gold` | PASS | raw prediction, gold and question carried through untouched |
| `regrade_records_grader_provenance` | PASS | every regraded record stamped grade_v3.2_A002 |
| `regrade_reproduces_metrics` | PASS | status distribution identical after regrade |
| `sql_fixtures_use_phase7_executor` | PASS | SQL fixture path calls the approved Phase 7 executor (train_kb=148); no second execution implementation exists |
| `no_duplicate_sql_execution_in_stack` | PASS | no module in the reporting stack opens its own database connection |
| `seal01_sealed_artifact_with_dev_family_denied` | PASS | SealError: artifact 'fx_sealed_devlook' is classified SEALED by (records claim family=factual_recall) |
| `seal02_sealed_artifact_with_future_family_denied` | PASS | SealError: artifact 'fx_sealed_future' is classified SEALED by  |
| `seal03_unregistered_artifact_fails_closed` | PASS | SealError: artifact is not a registered dev artifact (unregiste -- unknown never becomes dev |
| `seal04_classification_before_parsing` | PASS | SealError: artifact 'fx_sealed_unparseable' is classified SEALE -- unparseable bytes never reached a JSON parser |
| `seal05_sealed_metadata_does_not_parse_records` | PASS | metadata returned for an UNPARSEABLE sealed artifact; item_count came from the trusted manifest. Raw bytes are read for hash verification; records are never parsed |
| `seal06_metadata_exposes_no_family` | PASS | keys: ['artifact_id', 'artifact_kind', 'artifact_path', 'item_count', 'provenance', 'records_parsed', 'schema_version', 'sha256'] |
| `seal07_metadata_exposes_no_condition` | PASS | no condition field |
| `seal08_metadata_exposes_no_score_status_error` | PASS | no status, score, error or answer-type distribution |
| `seal09_relative_and_absolute_paths_same_identity` | PASS | absolute, relative and dotted spellings all classify sealed |
| `seal10_symlink_to_sealed_remains_sealed` | PASS | SealError: artifact 'fx_sealed_devlook' is classified SEALED by -- symlink resolves to the sealed artifact |
| `seal11_copied_artifact_fails_closed` | PASS | SealError: artifact is not a registered dev artifact (unregiste -- identical bytes at an unregistered path stay unknown |
| `seal11b_hash_mismatch_fails_closed` | PASS | SealError: artifact is not a registered dev artifact (unregiste -- registered path, unregistered bytes |
| `seal12_registered_dev_artifact_loads` | PASS | 18 dev records loaded via the trusted authority |
| `trust01_caller_cannot_supply_authority` | PASS | load_dev_results(path) -> 'list[EvalRecord]' and sealed_metadata(path) -> 'dict' accept no registry/authority/unseal argument |
| `trust02_authority_is_immutable` | PASS | no register(); mapping is read-only; attribute assignment raises ManifestError |
| `trust03_rogue_manifest_not_consulted_by_dev_api` | PASS | SealError: artifact 'fx_sealed_devlook' is classified SEALED by -- a caller-authored manifest has no supported route into the dev loader |
| `trust04_conflicting_manifest_rejected` | PASS | same-path and same-artifact_id conflicts both raise ManifestError; no last-write-wins |
| `trust05_malformed_manifest_rejected` | PASS | unknown schema, missing field, extra field and invalid artifact_kind all raise ManifestError |
| `trust06_manifest_provenance_deterministic` | PASS | two builds of the same manifest agree on a 64-hex sha256 and on 4 artifacts in deterministic order (value omitted: the synthetic manifest embeds temporary paths) |
| `trust07_no_authority_fails_closed` | PASS | an uninitialized authority refuses dev loading rather than defaulting open |
| `seal14_family_not_used_for_classification` | PASS | no record field participates in classification; identity is canonical path + registered hash |
| `no_retired_component_dependency` | PASS | none of 15 retired concepts appear in executable code; mentioned only in prose explaining their avoidance: ['REPORT_ORDER'] |
| `no_v2_runtime_path` | PASS | no v2 repository path and no v2 database fallback |
| `fault_duplicate_example_id` | PASS | VerificationError: duplicate example_id(s): ['fx01_set_correct'] |
| `fault_expected_count_mismatch` | PASS | VerificationError: expected 19 records, found 18 |
| `fault_denominator_mismatch` | PASS | DenominatorError: scored (12) + failed (6) = 18 != expected probe size (23 |
| `fault_unsupported_family_dropped` | PASS | VerificationError: family/families ['no_match', 'structured_heldin', 'struc |
| `fault_invalid_status` | PASS | RecordSchemaError: status 'totally_made_up' is not in the frozen vocabulary |
| `fault_status_score_contradiction` | PASS | RecordSchemaError: status 'incorrect' must not carry a perfect task score |
| `fault_missing_required_field` | PASS | RecordSchemaError: record missing required field(s): ['family', 'condition' |
| `fault_stale_result_schema` | PASS | RecordSchemaError: record carries unsupported field(s) ['legacy_v2_field']; |
| `fault_mismatched_grader_provenance` | PASS | VerificationError: records graded by a different grader build: ['c7775cdcf6 |
| `fault_corrupted_record_missing_provenance` | PASS | VerificationError: fx01_set_correct: missing required field 'prompt_hash' |
| `pre_regrade_all_start_unregraded` | PASS | no record carries a regrade_outcome before regrade() runs |
| `regrade_recomputes_and_disagrees_with_stale_score` | PASS | stale score was 'correct'; genuine recomputation from retained evidence (WRONG_COMPANY vs RIGHT_COMPANY) now correctly says 'incorrect' -- proves regrade recomputes rather than re-stamping |
| `insufficient_evidence_preserves_status_and_scores` | PASS | status/scores byte-identical to pre-regrade despite no retained execution_result/gold |
| `insufficient_evidence_preserves_grader_provenance` | PASS | grader_version/grader_sha256 NOT re-stamped to the current build -- a record must never claim to originate from a grader that never actually evaluated it |
| `insufficient_evidence_outcome_flagged` | PASS | regrade_outcome correctly distinguishes this from a real recompute |
| `multipart_regrade_recomputes_and_disagrees` | PASS | one part's retained evidence disagrees (WRONG vs B); multi-part regrade correctly recomputes to 'incorrect' |
| `multipart_missing_one_part_is_insufficient_not_partial` | PASS | a single part lacking retained evidence makes the WHOLE item insufficient_evidence, never a partial recompute; original score preserved untouched |
| `assert_fully_regraded_rejects_mixed_batch` | PASS | VerificationError: 2 record(s) are not fully regraded under the current grader (c7775cdcf |
| `assert_fully_regraded_accepts_genuine_full_coverage` | PASS | a batch where every record is genuinely recomputed under the current grader passes |
| `assert_fully_regraded_rejects_never_regraded` | PASS | VerificationError: 1 record(s) are not fully regraded under the current grader (c7775cdcf |
| `assert_fully_regraded_rejects_stale_grader_build` | PASS | VerificationError: 1 record(s) are not fully regraded under the current grader (c7775cdcf |
| `regrade_coverage_accounts_for_every_record` | PASS | {'recomputed': 2, 'insufficient_evidence': 2, 'not_yet_regraded': 0, 'total': 4} |
| `full_path_reload_preserves_records` | PASS | serialized/reloaded records are unregraded, matching what was written |
| `full_path_verify_passes_structurally` | PASS | structural verification passes on the regraded mixed batch (verify does not itself judge regrade completeness) |
| `full_path_report_shows_mixed_coverage` | PASS | {'recomputed': 2, 'insufficient_evidence': 2, 'not_yet_regraded': 0, 'total': 4} |
| `full_path_cannot_certify_fully_regraded` | PASS | VerificationError: 2 record(s) are not fully regraded under the current grader (c7775cdcf |
| `stale_grader_fixture_actually_recomputed` | PASS | the fixture must reach regrade_outcome='recomputed' (real evidence present) so the certification check below isolates grader-IDENTITY rejection specifically, not merely insufficient-evidence rejection: got 'recomputed' |
| `report_certification_checks_grader_identity_not_just_counts` | PASS | a record 'recomputed' under a stale grader build must NOT certify as fully regraded under the current one: fully_regraded_certified=False |
| `report_renders_not_fully_regraded_for_stale_grader` | PASS | the rendered report text must say NOT fully regraded, not falsely claim certification |
| `report_certifies_when_genuinely_fully_regraded` | PASS | a record recomputed under the actual current grader build correctly certifies as fully regraded |
| `report_omits_certification_when_not_requested` | PASS | omitting expected_grader_sha256 makes no fully-regraded claim either way (safer default than assuming completeness) |
| `fresh_grading_penalizes_extra_statement` | PASS | task=1.0 schema=0.0 |
| `regrade_preserves_extra_statement_penalty` | PASS | regrading from retained evidence (with extra_present retained alongside per-part evidence) reproduces the SAME strict-schema penalty fresh grading applied: task=1.0 schema=0.0 |
| `missing_extra_present_flag_absent_is_insufficient_not_a_pass` | PASS | an absent extra_present flag proves nothing about whether an extra statement was present at original grading time -- it must never default to 'confirmed no extra statement': got regrade_outcome='insufficient_evidence' |
| `missing_extra_present_flag_null_is_insufficient_not_a_pass` | PASS | an null extra_present flag proves nothing about whether an extra statement was present at original grading time -- it must never default to 'confirmed no extra statement': got regrade_outcome='insufficient_evidence' |
| `regrade_validates_per_part_metadata_before_comparing` | PASS | a declared part with empty target_columns must fail closed on regrade exactly as it does on fresh grading, not silently project zero columns and certify 999=='correct' against gold 1: status=invalid_output task=0.0 |
| `regrade_validated_failure_still_passes_structural_verify` | PASS | an invalid_output outcome is still a structurally valid record (exactly one frozen status, required fields present) |
| `report_does_not_falsely_certify_invalid_multipart_regrade` | PASS | the record IS genuinely recomputed (recomputed correctly to an explicit invalid_output failure, not silently passed as correct) -- certification here correctly reflects a real, honest recomputation outcome, not a false 'correct': {'correct': 0, 'incorrect': 0, 'generation_failure': 0, 'parse_failure': 0, 'SQL_error': 0, 'timeout': 0, 'truncated_output': 0, 'invalid_output': 1} |
| `assert_fully_regraded_rejects_stale_regrader_build` | PASS | VerificationError: 1 record(s) are not fully regraded under the current grader (c7775cdcf |
| `assert_fully_regraded_accepts_current_regrader` | PASS | a record genuinely produced by the current regrade() build passes (assert_fully_regraded returns None / does not raise) |
| `fresh_grading_rejects_duplicate_part_id` | PASS | fresh grading correctly refuses a duplicate declared part_id |
| `regrade_rejects_duplicate_part_id_same_as_fresh_grading` | PASS | a duplicate declared part_id must fail closed on regrade exactly as it does on fresh grading, not silently compare the same retained evidence twice and certify it correct: status=invalid_output task=0.0 |
| `evalrecord_rejects_recomputed_without_regrader_sha256` | PASS | RecordSchemaError: regrade_outcome is 'recomputed' but regrader_sha256 is None -- a record cannot c |

## Fault tests

| fault | rejected | how |
|---|---|---|
| `fault_duplicate_example_id` | yes | VerificationError: duplicate example_id(s): ['fx01_set_correct'] |
| `fault_expected_count_mismatch` | yes | VerificationError: expected 19 records, found 18 |
| `fault_denominator_mismatch` | yes | DenominatorError: scored (12) + failed (6) = 18 != expected probe size (23 |
| `fault_unsupported_family_dropped` | yes | VerificationError: family/families ['no_match', 'structured_heldin', 'struc |
| `fault_invalid_status` | yes | RecordSchemaError: status 'totally_made_up' is not in the frozen vocabulary |
| `fault_status_score_contradiction` | yes | RecordSchemaError: status 'incorrect' must not carry a perfect task score |
| `fault_missing_required_field` | yes | RecordSchemaError: record missing required field(s): ['family', 'condition' |
| `fault_stale_result_schema` | yes | RecordSchemaError: record carries unsupported field(s) ['legacy_v2_field']; |
| `fault_mismatched_grader_provenance` | yes | VerificationError: records graded by a different grader build: ['c7775cdcf6 |
| `fault_corrupted_record_missing_provenance` | yes | VerificationError: fx01_set_correct: missing required field 'prompt_hash' |
