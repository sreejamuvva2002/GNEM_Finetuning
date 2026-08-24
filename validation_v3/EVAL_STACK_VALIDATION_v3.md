# EVAL_STACK_VALIDATION_v3

Phase 8 — build the v3 evaluation and reporting stack.

> **This filename is a Phase 8 implementation/provenance convention.** `README.md` and `CLAUDE.md` do not prescribe a dedicated Phase 8 validation-artifact filename. README was not amended to name it.

> Every number in this document comes from **deterministic synthetic fixtures**. Nothing here is an experimental result.

## Frozen Phase 7 inputs

```text
datasets_v3/gnem_v3.sqlite         7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b
finetune/sqlexec_v3.py             a6c06b71dd97541997bedc2202e1980ab2e4cdd721aaf20ff43eacfda876c461
finetune/grade_v3.py               619b9350e38ac976ad5ce9d4ba377fdcc4504e00b9ac34ef49fa47f6931b4cbd
finetune/phase7_grader_tests.py    fefbd447694a96c25c30e90438e2a24cf1638e8e1ef643f63c76dcb7de0f2692
```

## Stack modules

```text
finetune/eval_records_v3.py               14f6e953af26ece71e8dfca862e741edc2594e566027664477020f1106d122a5
finetune/eval_stats_v3.py                 28add5267e6d77abd589243ab52dcdbbddaa612d7b8b1e733289af08132f9f24
finetune/eval_report_v3.py                562cf6fe5dab69a09cd8aa011f6da1e7ca36ad0f89d1e090d16bbe630f325838
finetune/eval_verify_v3.py                89d5b3359638e470757f70a2f10a9601aef92f8ffae18dc28ee0fc24d3dabf09
finetune/phase8_eval_stack_tests.py       211e6e85ada8caf1d9cc844104b5da0a41e42988f37eba8126db2dc0da571e0d
```

Rebuilt v3-native rather than ported. v2's stack is 4,213 lines and `report.py` alone carries 111 retired-concept references; README Phase 8 warns that recreating it "would add risk rather than remove it". Only the statistical METHODS were carried across as concepts, reimplemented against the v3 schema — no v2 file was copied.

## Fixture manifest

```text
validation_v3/fixtures_v3/fixture_records_v3.jsonl   14610bb2e7d76a34f6cc617ab918b9d50a7b6048dae4e6cde1ee37ad38958e27
validation_v3/fixtures_v3/summary_v3.json            bb0d2c7af020499940dde16bd3aa591208846d452b287c081f6b0a953022abde
validation_v3/fixtures_v3/error_analysis_v3.json     f6f78983bc021a80901d1c20a01fa9f2231b0be097eb139352d1b9a9e0d53368
validation_v3/fixtures_v3/REPORT_v3.md               cb05ce52925afbb4dd9694ca9f20c0771d6fec85fdd980455d630f02390c700e
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

Test and Q42 remain `LOCKED_UNTIL_PHASE_40`. Validated with **synthetic sealed fixtures only** — no real test or Q42 content was created, read or reported.

- classification **fails closed**: a family is sealed unless demonstrably a dev family
- `load_dev_results` refuses a sealed set and has **no** `unseal` parameter
- `summarize` and `error_analysis` refuse sealed records
- **no generic `unseal=True` exists anywhere in the library** — such a switch would also unlock real sealed output later
- `sealed_metadata` returns count, hash, path, families and conditions only; no question, gold, prediction, error detail or score
- the real unblind authority belongs to the Phase 40 entry point (`CLAUDE.md` §23), which is deliberately not created here

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
| `stats_mcnemar_present_cited` | PASS | McNemar implemented as secondary evidence (README:973) |
| `stats_split_group_weighting_cited` | PASS | average within split_group then across groups; aggregate item excluded as undefined (CLAUDE.md:847-854) |
| `stats_hierarchical_bootstrap_deferred` | PASS | not implemented: absent from the live protocol, so deferred not invented |
| `regrade_preserves_raw_and_gold` | PASS | raw prediction, gold and question carried through untouched |
| `regrade_records_grader_provenance` | PASS | every regraded record stamped grade_v3.0 |
| `regrade_reproduces_metrics` | PASS | status distribution identical after regrade |
| `sql_fixtures_use_phase7_executor` | PASS | SQL fixture path calls the approved Phase 7 executor (train_kb=148); no second execution implementation exists |
| `no_duplicate_sql_execution_in_stack` | PASS | no module in the reporting stack opens its own database connection |
| `seal_classification_fails_closed` | PASS | test/q42/probe_42 families classify as sealed; dev as dev |
| `dev_loader_refuses_sealed` | PASS | SealError: refused a set containing sealed families ['probe_42_business', 'test_structured_hel |
| `dev_loader_accepts_dev` | PASS | 18 dev records loaded |
| `dev_summarize_refuses_sealed` | PASS | SealError |
| `dev_error_analysis_refuses_sealed` | PASS | SealError |
| `no_generic_unseal_parameter` | PASS | no unseal parameter on any dev or library API; Phase 40 owns the unblind authority (CLAUDE.md 23) |
| `sealed_metadata_discloses_no_content` | PASS | keys ['conditions', 'contents_disclosed', 'families', 'item_count', 'kind', 'note', 'path', 'sha256'] ⊆ metadata-only; count=2, sha256=89c6a4460907…; no question, gold, prediction, error detail or score echoed |
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
| `fault_mismatched_grader_provenance` | PASS | VerificationError: records graded by a different grader build: ['619b9350e3 |
| `fault_corrupted_record_missing_provenance` | PASS | VerificationError: fx01_set_correct: missing required field 'prompt_hash' |

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
| `fault_mismatched_grader_provenance` | yes | VerificationError: records graded by a different grader build: ['619b9350e3 |
| `fault_corrupted_record_missing_provenance` | yes | VerificationError: fx01_set_correct: missing required field 'prompt_hash' |
