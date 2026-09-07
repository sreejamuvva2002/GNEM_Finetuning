# DATASET_B_FACTS_v3

Phase 11 — `train_B_facts_v3.jsonl`, cell-level closed-book factual QA.

## Provenance

```text
artifact          datasets_v3/train_B_facts_v3.jsonl
sha256            17ddccd67f2c46bb94e5d948c130cd2d6c99b564a07fc171618eb0f5e3f957b0
generator         b_facts_v3.0
scope             train_kb (Phase 4 contract)
holdout registry  holdout_v3.1 frozen 2026-08-24
```

## Per-attribute counts

| attribute | items |
|---|--:|
| `category` | 141 |
| `industry_group` | 141 |
| `location` | 139 |
| `address` | 140 |
| `primary_facility_type` | 141 |
| `ev_supply_chain_role` | 138 |
| `primary_oems` | 125 |
| `supplier_or_affiliation_type` | 125 |
| `employment` | 137 |
| `product_or_service` | 136 |
| `ev_battery_relevant` | 137 |
| `classification_method` | 141 |
| `processes` | 130 |
| `services` | 138 |
| `certifications` | 102 |

**Total: 2011 items.**

## Skips (never merged, never asked)

| reason | count |
|---|--:|
| `holdout_value_present` | 21 |
| `multirow_conflict` | 23 |
| `sentinel_or_empty` | 60 |

`multirow_conflict`: the (company, attribute) pair disagreed across that company's rows and was dropped, never merged (README:456-459). `sentinel_or_empty`: the resolved value is a frozen sentinel or an empty set (no QA is ever asked about a sentinel). `holdout_value_present`: a set field's value contains a held-out term, so the WHOLE field is omitted for that company (omit the item, never truncate the truth).

## Multi-row conflicts (all 9 multi-row companies, all splits)

`validation_v3/MULTIROW_CONFLICTS_v3.csv` — 50 conflicting (company, attribute) pairs across 9 companies. README's Phase 11 estimate is 'expect ≈28 pairs across 9 companies'; the measured count against the frozen v3 KB is **50** across all 9 (of which the pairs belonging to the 5 TRAIN-split multi-row companies — Haering Precision USA LP, Lyle Industries Inc., Novelis Inc., Panasonic Automotive Systems Co., Sewon America Inc. — are the ones that actually suppress a B item; the other 4 companies are dev/test-side and produce no B items regardless). This is a real, measured deviation from the README estimate, reported here rather than silently reconciled — see the commit message for the full accounting.

## Exposure

```text
strings scanned   4023   (system prompt + every question + every answer)
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
| `registry_frozen_before_generation` | PASS | HOLDOUT_REGISTRY_v3 holdout_v3.1 dated 2026-08-24 |
| `nonzero_items` | PASS | 2011 B items |
| `unique_example_ids` | PASS | 2011 unique ids |
| `no_duplicate_questions` | PASS | 0 duplicate questions |
| `no_incoherent_merged_scalar_gold` | PASS | every scalar gold_value is a verbatim raw value from one of that company's rows, never a cross-row join (the v2 'Indirect; No' bug) |
| `well_formed_set_answers` | PASS | 370 set-valued items, all non-empty/deduped/non-blank |
| `no_sentinel_answers` | PASS | no item's gold contains a frozen sentinel |
| `no_certification_count_target` | PASS | Certification Count never rendered |
| `zero_heldout_or_dev_companies_present` | PASS | 0 of 52 dev/test companies appear in rendered B text |
| `static_check_generator_never_reaches_full_kb` | PASS | no forbidden scope literal in 1 scanned file(s) |
| `exposure_count_zero` | PASS | 0 held-out literals across 4023 rendered strings |
| `multirow_conflicts_recorded` | PASS | 50 conflicting (company, attribute) pairs across 9 multi-row companies |
| `nine_multirow_companies` | PASS | 9 multi-row companies (README:456-459 names 9: Novelis x3, ZF Gainesville x3, and 7 others x2) |
