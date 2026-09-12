# DATASET_A_CPT_v3

Phase 10 — `train_A_cpt_v3.jsonl`, continued pre-training passages.

## Provenance

```text
artifact          datasets_v3/train_A_cpt_v3.jsonl
sha256            ae5f77239743150597e33ed34e831dfe18404f4df566d17e44d66e55788a5c14
generator         a_cpt_v3.1
scope             train_kb (Phase 4 contract)
holdout registry  holdout_v3.1 frozen 2026-08-24
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
total LM tokens   28486
min / median / p95 / max   154 / 192 / 233 / 267
```

A trains under `packing=True` with **full-sequence LM loss**, a different objective from the chat variants' `assistant_only_loss=True`. This budget is reported in LM tokens and is **never** placed on the completion-token axis.

## Holdout omissions (omit the item, never truncate the truth)

| attribute | rows omitting the field | remaining coverage | registry predicted |
|---|--:|--:|--:|
| `processes` | 6 | 95.9% | 6 |
| `services` | 2 | 98.6% | 2 |
| `certifications` | 13 | 89.4% | 13 |

A row whose multi-valued field contains a held-out value has that **whole field** omitted from its passage. Emitting the surviving terms would teach an incomplete fact.

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
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.1 dated 2026-08-24 |
| `one_passage_per_row` | PASS | 148 passages for 148 train rows (one each) |
| `unique_example_ids` | PASS | 148 unique ids |
| `no_duplicate_passages` | PASS | 0 duplicate passages |
| `zero_heldout_or_dev_companies_present` | PASS | 0 of 52 dev/test companies appear in the plain text |
| `static_check_generator_never_reaches_full_kb` | PASS | no forbidden scope literal in 1 scanned file(s) |
| `no_sentinel_rendered_as_fact` | PASS | Not specified / Not applicable / None identified after search absent |
| `no_certification_count_target` | PASS | Certification Count never rendered |
| `exposure_count_zero` | PASS | 0 held-out literals across 148 rendered passages |
| `omitted_fields_match_registry_processes` | PASS | 6 rows omit processes == registry train_rows_lost 6 |
| `omitted_fields_match_registry_services` | PASS | 2 rows omit services == registry train_rows_lost 2 |
| `omitted_fields_match_registry_certifications` | PASS | 13 rows omit certifications == registry train_rows_lost 13 |
| `coverage_floor_holds` | PASS | processes 95.9% · services 98.6% · certifications 89.4% |
| `coverage_matches_registry_prediction_processes` | PASS | 95.95% recomputed == 95.95% frozen at Phase 9 |
| `coverage_matches_registry_prediction_services` | PASS | 98.65% recomputed == 98.65% frozen at Phase 9 |
| `coverage_matches_registry_prediction_certifications` | PASS | 89.43% recomputed == 89.43% frozen at Phase 9 |
| `real_tokenizer_loaded_at_pinned_revision` | PASS | Qwen/Qwen2.5-14B-Instruct @ cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8 (Qwen2Tokenizer, local_files_only=True) |
| `tokenizer_json_sha_matches_expected` | PASS | c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539 |
