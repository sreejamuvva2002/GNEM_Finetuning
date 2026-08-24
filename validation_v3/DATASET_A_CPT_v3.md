# DATASET_A_CPT_v3

Phase 10 — `train_A_cpt_v3.jsonl`, continued pre-training passages.

## Provenance

```text
artifact          datasets_v3/train_A_cpt_v3.jsonl
sha256            4e5f005d29106bad4dd86b3cc684abaaa72f8c89f358634e81af1b520db58fd2
generator         a_cpt_v3.0
scope             train_kb (Phase 4 contract)
holdout registry  holdout_v3.0 frozen 2026-08-24
```

## Composition

```text
passages                148   (one canonical passage per train row)
renderings per row      1             (Phase 0 decision; v2's three are retired)
```

**Known interpretation limit (README Phase 10).** A one-passage A has weaker phrasing diversity than v2's three renderings, so it is *expected* to underperform on `probe_fact_paraphrase_v3` relative to a three-rendering A. That is a design consequence, never a finding about CPT.

## Budget — LM tokens

```text
tokenizer     Qwen/Qwen2.5-14B-Instruct@cf98f3b3
total LM tokens   28634
min / median / p95 / max   147 / 192 / 233 / 267
```

A trains under `packing=True` with **full-sequence LM loss**, a different objective from the chat variants' `assistant_only_loss=True`. This budget is reported in LM tokens and is **never** placed on the completion-token axis.

## Holdout omissions (omit the item, never truncate the truth)

| attribute | rows omitting the field | remaining coverage | registry predicted |
|---|--:|--:|--:|
| `processes` | 17 | 88.5% | 17 |
| `services` | 11 | 92.6% | 11 |
| `certifications` | 6 | 95.9% | 6 |

A row whose multi-valued field contains a held-out value has that **whole field** omitted from its passage. Emitting the surviving terms would teach an incomplete fact.

## Exposure

```text
strings scanned   148   (final rendered passages)
exposure_count    0
```

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.0 dated 2026-08-24 |
| `one_passage_per_row` | PASS | 148 passages for 148 train rows (one each) |
| `unique_example_ids` | PASS | 148 unique ids |
| `no_duplicate_passages` | PASS | 0 duplicate passages |
| `zero_heldout_or_dev_companies_present` | PASS | 0 of 52 dev/test companies appear in the plain text |
| `no_sentinel_rendered_as_fact` | PASS | Not specified / Not applicable / None identified after search absent |
| `no_certification_count_target` | PASS | Certification Count never rendered |
| `exposure_count_zero` | PASS | 0 held-out literals across 148 rendered passages |
| `omitted_fields_match_registry_processes` | PASS | 17 rows omit processes == registry train_rows_lost 17 |
| `omitted_fields_match_registry_services` | PASS | 11 rows omit services == registry train_rows_lost 11 |
| `omitted_fields_match_registry_certifications` | PASS | 6 rows omit certifications == registry train_rows_lost 6 |
| `coverage_floor_holds` | PASS | processes 88.5% · services 92.6% · certifications 95.9% |
