# DATASET_B_FACTS_v3

Phase 11 — `train_B_facts_v3.jsonl`, cell-level closed-book factual QA.

## Provenance

```text
artifact          datasets_v3/train_B_facts_v3.jsonl
sha256            87ea988d2e0a8e68f76daa0d4ea5fb5227314003ad4c83618375c3a487d9db21
generator         b_facts_v3.1_A002
scope             train_kb (Phase 4 contract)
holdout registry  holdout_v3.2_A002 frozen 2026-09-11
```

## Per-attribute counts

| attribute | items |
|---|--:|
| `category` | 141 |
| `industry_group` | 141 |
| `location` | 141 |
| `address` | 141 |
| `primary_facility_type` | 141 |
| `ev_supply_chain_role` | 145 |
| `primary_oems` | 141 |
| `supplier_or_affiliation_type` | 141 |
| `employment` | 147 |
| `product_or_service` | 148 |
| `ev_battery_relevant` | 147 |
| `classification_method` | 141 |
| `processes` | 148 |
| `services` | 143 |
| `certifications` | 143 |

**Total: 2149 items.**

## Skips (never merged, never asked)

| reason | count |
|---|--:|

A-002 retains missing evidence as qualified answers and conflicting training observations as record-scoped QA. No value-based exclusions remain. Company holdouts still apply.

## Multi-row conflicts (all 9 multi-row companies, all splits)

`validation_v3/MULTIROW_CONFLICTS_v3.csv` — 50 conflicting (company, attribute) pairs across 9 companies. README's Phase 11 estimate is 'expect ≈28 pairs across 9 companies'; the measured count against the frozen v3 KB is **50** across all 9 (of which the pairs belonging to the 5 TRAIN-split multi-row companies — Haering Precision USA LP, Lyle Industries Inc., Novelis Inc., Panasonic Automotive Systems Co., Sewon America Inc. — are the ones that receive record-scoped B items; the other 4 companies are dev/test-side and produce no B items regardless). This is a real, measured deviation from the README estimate, reported here rather than silently reconciled — see the commit message for the full accounting.

## Exposure

```text
strings scanned   6447   (system prompt + every question + every answer)
exposure_count    0
```

## Phase 4 static check (re-run for this generator)

```text
scanned            ['finetune/phase11_build_b_facts.py']
violation_count    0
proves             no forbidden scope literal in 1 scanned file(s)
```

## Validation

| check | result | detail |
|---|---|---|
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.2_A002 dated 2026-09-11 |
| `nonzero_items` | PASS | 2149 B items |
| `unique_example_ids` | PASS | 2149 unique ids |
| `no_duplicate_questions` | PASS | 0 duplicate questions |
| `no_incoherent_merged_scalar_gold` | PASS | every scalar gold_value is a verbatim raw value from one of that company's rows, never a cross-row join (the v2 'Indirect; No' bug) |
| `well_formed_set_answers` | PASS | 409 set-valued items, all non-empty/deduped/non-blank |
| `sentinel_answers_qualified` | PASS | ['B_Anovion_Technologies_certifications', 'B_Club_Car_LLC_certifications', 'B_Daesol_Ausys_certifications', 'B_Denkai_America_certifications', 'B_Down_2_Earth_Trailers_certifications'] |
| `no_certification_count_target` | PASS | Certification Count never rendered |
| `zero_heldout_or_dev_companies_present` | PASS | 0 of 52 dev/test companies appear in rendered B text |
| `static_check_generator_never_reaches_full_kb` | PASS | no forbidden scope literal in 1 scanned file(s) |
| `exposure_count_zero` | PASS | 0 held-out literals across 6447 rendered strings |
| `multirow_conflicts_recorded` | PASS | 50 conflicting (company, attribute) pairs across 9 multi-row companies |
| `nine_multirow_companies` | PASS | 9 multi-row companies (README:456-459 names 9: Novelis x3, ZF Gainesville x3, and 7 others x2) |
