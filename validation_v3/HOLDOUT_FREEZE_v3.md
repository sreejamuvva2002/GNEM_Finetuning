# HOLDOUT_FREEZE_v3

Phase 9 — the Holdout Registry and Fact Exposure Ledger, frozen **before any training dataset exists**. README Phase 9: *"If holdouts are chosen after seeing the generated data, the holdout that gets picked is the one the data happens to support."*

> Filename is a Phase 9 provenance convention; README names `HOLDOUT_REGISTRY_v3.json`, `FACT_EXPOSURE_LEDGER_v3.json` and `VALUE_HOLDOUT_COST_v3.csv`, which are the protocol artifacts.

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
objective                    maximise total test support
tie-breaks                   fewest train rows lost -> fewest dev rows lost -> lexicographic value name
```

## Selected value holdouts

| attribute | value | rows | train | dev | test | companies | train rows lost | coverage after |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| certifications | `ISO 22301` | 3 | 2 | 0 | 1 | 3 | 2 | 98.37% |
| certifications | `OHSAS 18001` | 8 | 5 | 0 | 3 | 8 | 5 | 95.93% |
| processes | `Battery Module Assembly` | 8 | 3 | 1 | 4 | 8 | 3 | 97.97% |
| processes | `Battery Pack Assembly` | 7 | 2 | 1 | 4 | 7 | 2 | 98.65% |
| processes | `Cell Testing` | 10 | 5 | 1 | 4 | 10 | 5 | 96.62% |
| processes | `Welding` | 15 | 11 | 1 | 3 | 15 | 11 | 92.57% |
| services | `Battery Collection` | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Battery Engineering` | 15 | 9 | 2 | 4 | 15 | 9 | 93.92% |
| services | `Battery Repurposing` | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |

### Cumulative attribute-level floor (union, not sum)

| attribute | pool | train rows | lost | remaining coverage | companies remaining |
|---|--:|--:|--:|--:|--:|
| processes | 20 | 148 | 17 | **88.51%** | 87.94% |
| services | 11 | 148 | 11 | **92.57%** | 92.2% |
| certifications | 4 | 123 | 6 | **95.12%** | 94.83% |

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
| `readme_candidate_count_processes` | PASS | 26 == 26 (row unit) |
| `readme_candidate_count_services` | PASS | 13 == 13 (row unit) |
| `readme_candidate_count_certifications` | PASS | 8 == 8 (row unit) |
| `count_processes` | PASS | 4 == 4: Battery Module Assembly, Battery Pack Assembly, Cell Testing, Welding |
| `band_processes` | PASS | all within (3, 15) |
| `min_train_support_processes` | PASS | all train >= 2 |
| `min_test_support_processes` | PASS | all test >= 1 (a value with no test support measures nothing) |
| `coverage_floor_processes` | PASS | 88.51% >= 85.0% |
| `per_value_threshold_processes` | PASS | every value individually >= 85.0% |
| `multi_company_support_processes` | PASS | no held-out value lives in a single company |
| `count_services` | PASS | 3 == 3: Battery Collection, Battery Engineering, Battery Repurposing |
| `band_services` | PASS | all within (3, 15) |
| `min_train_support_services` | PASS | all train >= 2 |
| `min_test_support_services` | PASS | all test >= 1 (a value with no test support measures nothing) |
| `coverage_floor_services` | PASS | 92.57% >= 85.0% |
| `per_value_threshold_services` | PASS | every value individually >= 85.0% |
| `multi_company_support_services` | PASS | no held-out value lives in a single company |
| `count_certifications` | PASS | 2 == 2: ISO 22301, OHSAS 18001 |
| `band_certifications` | PASS | all within (3, 15) |
| `min_train_support_certifications` | PASS | all train >= 2 |
| `min_test_support_certifications` | PASS | all test >= 1 (a value with no test support measures nothing) |
| `coverage_floor_certifications` | PASS | 95.12% >= 85.0% |
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
