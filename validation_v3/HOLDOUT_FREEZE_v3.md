# HOLDOUT_FREEZE_v3

Phase 9 — the Holdout Registry and Fact Exposure Ledger, frozen **before any training dataset exists**. README Phase 9: *"If holdouts are chosen after seeing the generated data, the holdout that gets picked is the one the data happens to support."*

> Filename is a Phase 9 provenance convention; README names `HOLDOUT_REGISTRY_v3.json`, `FACT_EXPOSURE_LEDGER_v3.json` and `VALUE_HOLDOUT_COST_v3.csv`, which are the protocol artifacts.

## Policy revision (v3.0 -> v3.1)

This registry was first frozen as `holdout_v3.0` and **revised the same day** after independent review. The earlier version is not hidden.

| changed | from | to |
|---|---|---|
| split minima | train>=2, test>=1 | train>=2, **dev>=1**, test>=1 (all mandatory) |
| objective | maximise total test support | **minimize union of train rows lost** |
| tie-breaks | train rows, dev rows, name | **exact-company union, summed dev support, lexicographic** |
| test support | objective | **eligibility only** |

**Why.** Selecting holdouts to maximise test support optimises the pre-registration against test-side properties of the KB. No model outcome is involved, so it was not a blinding breach, but it is test-informed selection and a weaker posture than deciding purely on train-side collateral. The revised objective is test-blind by construction and also cheaper: union train-row loss falls from 17 to 6 (processes), 11 to 2 (services).

**Provenance.** v3.0 implemented the configuration approved in the decision-analysis round, which specified 'maximise total test support' with minima train>=2/test>=1 and no dev minimum. v3.1 is therefore a deliberate POLICY REVISION directed after independent review, not a correction of an implementation that had deviated from its approval. Both facts are recorded so the pre-registration history stays accurate.

## Frozen inputs

```text
datasets_v3/canonical_records_v3.jsonl       42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488
datasets_v3/company_split_groups_v3.csv      a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701
datasets_v3/gnem_v3.sqlite                   7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b
```

## Support-unit provenance (frozen interpretation)

README Phase 21's published candidate table — **26 process / 13 service / 8 certification** — is reproduced by **row-occurrence** support, verified cell by cell against the frozen KB. `supporting_companies` separately reports **exact trimmed company** counts (README:700). Both units appear in `VALUE_HOLDOUT_COST_v3.csv`; the distinction is never hidden.

## Frozen parameters

```text
support band                 [3, 15]
min train support            2
min test support             1
attribute coverage floor     85.0%
per-value threshold          85.0%
holdout counts               {'processes': 4, 'services': 3, 'certifications': 2}
objective                    minimize union of train rows losing the attribute
tie-breaks                   minimize union of exact train companies affected -> maximize total dev support (sum of per-value dev ROW support) -> lexicographically smallest sorted canonical value tuple
```

## Selected value holdouts

| attribute | value | rows | train | dev | test | companies | train rows lost | coverage after |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| certifications | `AS9100` | 10 | 6 | 3 | 1 | 10 | 6 | 95.12% |
| certifications | `ASI Chain of Custody` | 3 | 3 | 0 | 0 | 2 | 3 | 97.56% |
| certifications | `Ford Q1` | 3 | 3 | 0 | 0 | 3 | 3 | 97.56% |
| certifications | `ISO 22301` | 3 | 2 | 0 | 1 | 3 | 2 | 98.37% |
| certifications | `ISO 26262` | 7 | 7 | 0 | 0 | 6 | 7 | 94.31% |
| certifications | `ISO/IEC 17025` | 10 | 8 | 1 | 1 | 10 | 8 | 93.5% |
| certifications | `ISO/SAE 21434` | 7 | 6 | 1 | 0 | 6 | 6 | 95.12% |
| certifications | `OHSAS 18001` | 8 | 5 | 0 | 3 | 8 | 5 | 95.93% |
| processes | `Battery Installation` | 3 | 2 | 1 | 0 | 3 | 2 | 98.65% |
| processes | `Battery Module Assembly` | 8 | 3 | 1 | 4 | 8 | 3 | 97.97% |
| processes | `Battery Pack Assembly` | 7 | 2 | 1 | 4 | 7 | 2 | 98.65% |
| processes | `Battery Recycling Logistics` | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| processes | `Cell Assembly` | 5 | 4 | 0 | 1 | 5 | 4 | 97.3% |
| processes | `Cell Testing` | 10 | 5 | 1 | 4 | 10 | 5 | 96.62% |
| processes | `Composite Layup` | 8 | 7 | 1 | 0 | 8 | 7 | 95.27% |
| processes | `Composite Manufacturing` | 8 | 7 | 1 | 0 | 8 | 7 | 95.27% |
| processes | `Converter Manufacturing` | 3 | 0 | 0 | 3 | 1 | 0 | 100.0% |
| processes | `Drive Unit Assembly` | 4 | 2 | 1 | 1 | 4 | 2 | 98.65% |
| processes | `Electroplating` | 3 | 2 | 0 | 1 | 3 | 2 | 98.65% |
| processes | `End-of-Line Testing` | 14 | 12 | 1 | 1 | 14 | 12 | 91.89% |
| processes | `Formation Cycling` | 5 | 4 | 0 | 1 | 5 | 4 | 97.3% |
| processes | `Grinding` | 14 | 10 | 2 | 2 | 14 | 10 | 93.24% |
| processes | `Inverter Manufacturing` | 3 | 0 | 0 | 3 | 1 | 0 | 100.0% |
| processes | `Material Blending` | 4 | 1 | 2 | 1 | 4 | 1 | 99.32% |
| processes | `Milling` | 15 | 12 | 0 | 3 | 15 | 12 | 91.89% |
| processes | `Powder Coating` | 6 | 4 | 1 | 1 | 6 | 4 | 97.3% |
| processes | `Powertrain Installation` | 14 | 12 | 1 | 1 | 14 | 12 | 91.89% |
| processes | `Refining` | 6 | 3 | 1 | 2 | 6 | 3 | 97.97% |
| processes | `Rolling` | 6 | 4 | 0 | 2 | 6 | 4 | 97.3% |
| processes | `Sensor Integration` | 6 | 4 | 1 | 1 | 6 | 4 | 97.3% |
| processes | `Turning` | 15 | 11 | 2 | 2 | 15 | 11 | 92.57% |
| processes | `Welding` | 15 | 11 | 1 | 3 | 15 | 11 | 92.57% |
| processes | `Wire Harness Manufacturing` | 5 | 3 | 0 | 2 | 5 | 3 | 97.97% |
| processes | `Wiring Harness Installation` | 5 | 3 | 0 | 2 | 5 | 3 | 97.97% |
| services | `Asset Management` | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |
| services | `Battery Collection` | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Battery Engineering` | 15 | 9 | 2 | 4 | 15 | 9 | 93.92% |
| services | `Battery Repurposing` | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Circular Economy Consulting` | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Customer Support` | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |
| services | `Embedded Software Development` | 5 | 2 | 1 | 2 | 4 | 2 | 98.65% |
| services | `Inventory Management` | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |
| services | `Supplier Management` | 3 | 3 | 0 | 0 | 3 | 3 | 97.97% |
| services | `Systems Integration Engineering` | 5 | 3 | 1 | 1 | 5 | 3 | 97.97% |
| services | `Thermal Modeling` | 3 | 2 | 1 | 0 | 3 | 2 | 98.65% |
| services | `Vehicle Engineering` | 15 | 12 | 1 | 2 | 15 | 12 | 91.89% |
| services | `Warehousing` | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |

### Cumulative attribute-level floor (union, not sum)

| attribute | row-band pool | eligible after minima | train rows | lost | remaining coverage | companies remaining |
|---|--:|--:|--:|--:|--:|--:|
| processes | 26 | 13 | 148 | 6 | **95.95%** | 95.74% |
| services | 13 | 7 | 148 | 2 | **98.65%** | 98.58% |
| certifications | 8 | 2 | 123 | 13 | **89.43%** | 88.79% |

A row carrying two held-out values is lost once, so the cumulative cost is the union of affected rows rather than the sum.

**Recorded selection characteristic:** maximising test support concentrates the processes/services selection in the battery/EV cluster, because battery values are test-heavy in the frozen split. This is an artefact of the deterministic objective, not cherry-picking, and it means the value axis measures slot transfer mostly within one domain. Recorded here so the final report can state it.

## Operation holdouts

Held out: `argmax_topk`, `group_by`, `limit_only` — README Phase 22 requires all three defining constructs to appear **0 times** in training gold.

Exactly one `operation_family` per task by precedence (argmax_topk > group_by > limit_only); a task matching more than one held-out family is **excluded from training entirely** so the zero-occurrence assertion stays unambiguous. Validated on synthetic fixtures — Phase 12 applies this frozen policy to the real task pool.

## Compositional holdout

Arity 2, one held-out set: **{certifications, processes}**, chosen by lowest train support then lexicographic.

**Collateral scope (frozen):** structured-task exclusion only. Individual component literals remain independently train-visible unless separately selected on the VALUE axis. An unseen COMBINATION is not an unseen VALUE.

## Conventions frozen here

- `logical_fingerprint` **lfp1** over 8 semantic fields
- multi-part serialization **parts_list_v1**
- few-shot eligibility: fail closed, 8 conditions

## Exposure policy

`exposure_count == 0` for every held-out item across A, B, C, D, BC, BD, scanned on final rendered strings, after chat-template rendering, system-prompt and catalogue insertion, few-shot insertion and target rendering.

## Validation

| check | result | detail |
|---|---|---|
| `frozen_inputs_unchanged` | PASS | canonical, split and DB hashes match |
| `initial_row_band_candidate_count_processes` | PASS | 26 == 26 (README stage-1 row-band pool) |
| `post_split_filter_eligible_count_processes` | PASS | 13 eligible after split minima (distinct from the 26 row-band candidates) |
| `initial_row_band_candidate_count_services` | PASS | 13 == 13 (README stage-1 row-band pool) |
| `post_split_filter_eligible_count_services` | PASS | 7 eligible after split minima (distinct from the 13 row-band candidates) |
| `initial_row_band_candidate_count_certifications` | PASS | 8 == 8 (README stage-1 row-band pool) |
| `post_split_filter_eligible_count_certifications` | PASS | 2 eligible after split minima (distinct from the 8 row-band candidates) |
| `count_processes` | PASS | 4 == 4: Battery Module Assembly, Battery Pack Assembly, Battery Recycling Logistics, Refining |
| `band_processes` | PASS | all within (3, 15) |
| `min_train_support_processes` | PASS | all train >= 2 |
| `min_dev_support_processes` | PASS | all dev >= 1 (mandatory) |
| `min_test_support_processes` | PASS | all test >= 1 (eligibility only) |
| `selection_is_collateral_minimal_processes` | PASS | no feasible combination has smaller union train-row loss |
| `coverage_floor_processes` | PASS | 95.95% >= 85.0% |
| `per_value_threshold_processes` | PASS | every value individually >= 85.0% |
| `multi_company_support_processes` | PASS | no held-out value lives in a single company |
| `count_services` | PASS | 3 == 3: Battery Collection, Battery Repurposing, Circular Economy Consulting |
| `band_services` | PASS | all within (3, 15) |
| `min_train_support_services` | PASS | all train >= 2 |
| `min_dev_support_services` | PASS | all dev >= 1 (mandatory) |
| `min_test_support_services` | PASS | all test >= 1 (eligibility only) |
| `selection_is_collateral_minimal_services` | PASS | no feasible combination has smaller union train-row loss |
| `coverage_floor_services` | PASS | 98.65% >= 85.0% |
| `per_value_threshold_services` | PASS | every value individually >= 85.0% |
| `multi_company_support_services` | PASS | no held-out value lives in a single company |
| `count_certifications` | PASS | 2 == 2: AS9100, ISO/IEC 17025 |
| `band_certifications` | PASS | all within (3, 15) |
| `min_train_support_certifications` | PASS | all train >= 2 |
| `min_dev_support_certifications` | PASS | all dev >= 1 (mandatory) |
| `min_test_support_certifications` | PASS | all test >= 1 (eligibility only) |
| `selection_is_collateral_minimal_certifications` | PASS | no feasible combination has smaller union train-row loss |
| `coverage_floor_certifications` | PASS | 89.43% >= 85.0% |
| `per_value_threshold_certifications` | PASS | every value individually >= 85.0% |
| `multi_company_support_certifications` | PASS | no held-out value lives in a single company |
| `composition_arity` | PASS | ['certifications', 'processes'] |
| `composition_components_train_visible` | PASS | each component independently present in training |
| `composition_collateral_scope_recorded` | PASS | component literals stay train-visible unless separately value-held-out |
| `operation_classification_deterministic` | PASS | one family per task by frozen precedence |
| `operation_multi_family_detected` | PASS | a GROUP BY + ORDER BY/LIMIT task is seen as two held-out families and is excluded from training (fail closed) |
| `operation_all_three_held_out` | PASS | README Phase 22 requires all three constructs at 0 occurrences |
| `fingerprint_same_for_equivalent` | PASS | wording/format-insensitive |
| `fingerprint_differs_on_value` | PASS | values_used differs |
| `fingerprint_differs_on_answer_type` | PASS | answer_type differs |
| `multi_part_serialization_frozen` | PASS | explicit parts[]; Phase 7 stand-in could not express multi-operation parts |
