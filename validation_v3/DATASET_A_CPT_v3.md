# DATASET_A_CPT_v3

Phase 10 — `train_A_cpt_v3.jsonl`, continued pre-training passages.

## Provenance

```text
artifact          datasets_v3/train_A_cpt_v3.jsonl
sha256            8d4737439cae67798d8f9ab0351acde65a1e66b2cc375920758e5f77247c985f
generator         a_cpt_v3.2_A002
scope             train_kb (Phase 4 contract)
holdout registry  holdout_v3.2_A002 frozen 2026-09-11
```

## Composition

```text
passages                148   (one canonical passage per train row)
renderings per row      1             (Phase 0 decision; v2's three are retired)
```

**Known interpretation limit (README Phase 10).** A one-passage A has weaker phrasing diversity than v2's three renderings, so it is *expected* to underperform on `probe_fact_paraphrase_v3` relative to a three-rendering A. That is a design consequence, never a finding about CPT.

## Budget — LM tokens

```text
tokenizer     Qwen/Qwen2.5-14B-Instruct @ cf98f3b3bbb4
passage tokens before EOS   34923
min / median / p95 / max   191 / 229 / 285 / 339
```

Trainer appends one EOS per passage: 35071 input tokens, maximum passage length 340. Manual 1,024-token stream chunking is used with **full-sequence LM loss**, a different objective from the chat variants' `assistant_only_loss=True`. This budget is reported in LM tokens and is **never** placed on the completion-token axis.

## Holdout omissions (omit the item, never truncate the truth)

| attribute | rows omitting the field | remaining coverage | registry predicted |
|---|--:|--:|--:|
| `processes` | 0 | 100.0% | 0 |
| `services` | 0 | 100.0% | 0 |
| `certifications` | 0 | 100.0% | 0 |

A-002 removes deliberate value exclusions. Every training-record field is rendered, including source-qualified missingness. Complete lists are retained.

## Exposure

```text
strings scanned   148   (final rendered passages)
exposure_count    0
```

## Phase 4 static check (re-run for this generator)

```text
scanned            ['finetune/phase10_build_a_cpt.py']
violation_count    0
proves             no forbidden scope literal in 1 scanned file(s)
```

Full-KB access needed for the dev/test-company leak check (below) lives in `finetune/leak_audit_v3.py`, a separate validation-only module deliberately excluded from this scan -- it is never a training-target source.

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.2_A002 dated 2026-09-11 |
| `one_passage_per_row` | PASS | 148 passages for 148 train rows (one each) |
| `unique_example_ids` | PASS | 148 unique ids |
| `no_duplicate_passages` | PASS | 0 duplicate passages |
| `zero_heldout_or_dev_companies_present` | PASS | 0 of 52 dev/test companies appear in the plain text |
| `static_check_generator_never_reaches_full_kb` | PASS | no forbidden scope literal in 1 scanned file(s) |
| `sentinel_evidence_qualified` | PASS | ['None identified after search', 'Not applicable', 'Not specified'] |
| `no_certification_count_target` | PASS | Certification Count never rendered |
| `exposure_count_zero` | PASS | 0 held-out literals across 148 rendered passages |
| `omitted_fields_match_registry_processes` | PASS | 0 rows omit processes == registry train_rows_lost 0 |
| `omitted_fields_match_registry_services` | PASS | 0 rows omit services == registry train_rows_lost 0 |
| `omitted_fields_match_registry_certifications` | PASS | 0 rows omit certifications == registry train_rows_lost 0 |
| `coverage_floor_holds` | PASS | processes 100.0% · services 100.0% · certifications 100.0% |
| `coverage_matches_registry_prediction_processes` | PASS | 100.00% recomputed == 100.0% frozen at Phase 9 |
| `coverage_matches_registry_prediction_services` | PASS | 100.00% recomputed == 100.0% frozen at Phase 9 |
| `coverage_matches_registry_prediction_certifications` | PASS | 100.00% recomputed == 100.0% frozen at Phase 9 |
| `real_tokenizer_loaded_at_pinned_revision` | PASS | Qwen/Qwen2.5-14B-Instruct @ cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8 (Qwen2Tokenizer, local_files_only=True) |
| `tokenizer_json_sha_matches_expected` | PASS | c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539 |
