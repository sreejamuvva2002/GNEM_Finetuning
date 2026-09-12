# HOLDOUT_FREEZE_v3

Phase 9 — the Holdout Registry and Fact Exposure Ledger. v3.0 was frozen before any training dataset existed. Phase 10 (train_A_cpt_v3.jsonl) was then generated from v3.0 and fully reverted. v3.1 was frozen after that correction, before any training dataset was ever built from it. No model training or evaluation ever used v3.0-derived data. README Phase 9: *"If holdouts are chosen after seeing the generated data, the holdout that gets picked is the one the data happens to support."*

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

## Phase 9 correction (registry/code hardening, post-v3.1)

Independent audit found real gaps in the supporting code and registry completeness after v3.1 was frozen. **The nine selected values and the selection algorithm above are unchanged** -- full independent recomputation (a standalone script importing nothing from `holdout_v3.py`) confirms the same nine values remain optimal under the frozen objective. What changed:

- added allowed_operations_per_field (README-required, previously absent)
- operation-construct detection: comment/quote-aware lexer replacing raw substring matching (closes a GROUP/**/BY-style evasion)
- registry loading: two-function split -- load_candidate_registry_for_phase9_audit() (recompute-and-compare, usable pre-approval) and load_registry() (requires an external PHASE9_APPROVAL.json anchor, raises Phase9NotApproved otherwise)
- registry wrapper is deeply immutable (stores canonical JSON text, every accessor returns a fresh parse)
- scan_strings/scan_operations/scan_compositions: list-only, raise on a bare str/dict instead of silently mis-iterating it
- exposure-report assertions: three typed functions (assert_value_scan_verified/assert_operation_scan_verified/assert_composition_scan_verified), each requiring real scan evidence (a nonzero scanned-count), not just total_exposures == 0
- exposure normalization: NFKC compatibility-normalize + casefold + whitespace-collapse (NFC alone does not fold fullwidth Unicode forms)
- logical_fingerprint: lfp1 -> lfp2, folds canonicalized logical_components into the hash (closes an AND/OR collision)
- scan_operations_multipart / scan_compositions_multipart: scan every part of a multi-part task, not a dict's keys (a live, reproduced bug in the original multi-part design) and check compositional holdouts against the whole task's component union, not per part

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

## Candidate pool (all row-band values, selected and rejected)

Every value in the 3-15 row-support band, whether or not it was selected -- kept so a rejection is auditable rather than invisible. **This table is the full candidate pool, not the selection** (Phase 9 correction, finding 9A: an earlier version of this document named this table 'Selected value holdouts', which was misleading since it listed all candidates). See the next section for the actual 9 selected values.

| attribute | value | selected? | rows | train | dev | test | companies | est. train rows lost | coverage after |
|---|---|:--:|--:|--:|--:|--:|--:|--:|--:|
| certifications | `AS9100` | **YES** | 10 | 6 | 3 | 1 | 10 | 6 | 95.12% |
| certifications | `ASI Chain of Custody` | no | 3 | 3 | 0 | 0 | 2 | 3 | 97.56% |
| certifications | `Ford Q1` | no | 3 | 3 | 0 | 0 | 3 | 3 | 97.56% |
| certifications | `ISO 22301` | no | 3 | 2 | 0 | 1 | 3 | 2 | 98.37% |
| certifications | `ISO 26262` | no | 7 | 7 | 0 | 0 | 6 | 7 | 94.31% |
| certifications | `ISO/IEC 17025` | **YES** | 10 | 8 | 1 | 1 | 10 | 8 | 93.5% |
| certifications | `ISO/SAE 21434` | no | 7 | 6 | 1 | 0 | 6 | 6 | 95.12% |
| certifications | `OHSAS 18001` | no | 8 | 5 | 0 | 3 | 8 | 5 | 95.93% |
| processes | `Battery Installation` | no | 3 | 2 | 1 | 0 | 3 | 2 | 98.65% |
| processes | `Battery Module Assembly` | **YES** | 8 | 3 | 1 | 4 | 8 | 3 | 97.97% |
| processes | `Battery Pack Assembly` | **YES** | 7 | 2 | 1 | 4 | 7 | 2 | 98.65% |
| processes | `Battery Recycling Logistics` | **YES** | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| processes | `Cell Assembly` | no | 5 | 4 | 0 | 1 | 5 | 4 | 97.3% |
| processes | `Cell Testing` | no | 10 | 5 | 1 | 4 | 10 | 5 | 96.62% |
| processes | `Composite Layup` | no | 8 | 7 | 1 | 0 | 8 | 7 | 95.27% |
| processes | `Composite Manufacturing` | no | 8 | 7 | 1 | 0 | 8 | 7 | 95.27% |
| processes | `Converter Manufacturing` | no | 3 | 0 | 0 | 3 | 1 | 0 | 100.0% |
| processes | `Drive Unit Assembly` | no | 4 | 2 | 1 | 1 | 4 | 2 | 98.65% |
| processes | `Electroplating` | no | 3 | 2 | 0 | 1 | 3 | 2 | 98.65% |
| processes | `End-of-Line Testing` | no | 14 | 12 | 1 | 1 | 14 | 12 | 91.89% |
| processes | `Formation Cycling` | no | 5 | 4 | 0 | 1 | 5 | 4 | 97.3% |
| processes | `Grinding` | no | 14 | 10 | 2 | 2 | 14 | 10 | 93.24% |
| processes | `Inverter Manufacturing` | no | 3 | 0 | 0 | 3 | 1 | 0 | 100.0% |
| processes | `Material Blending` | no | 4 | 1 | 2 | 1 | 4 | 1 | 99.32% |
| processes | `Milling` | no | 15 | 12 | 0 | 3 | 15 | 12 | 91.89% |
| processes | `Powder Coating` | no | 6 | 4 | 1 | 1 | 6 | 4 | 97.3% |
| processes | `Powertrain Installation` | no | 14 | 12 | 1 | 1 | 14 | 12 | 91.89% |
| processes | `Refining` | **YES** | 6 | 3 | 1 | 2 | 6 | 3 | 97.97% |
| processes | `Rolling` | no | 6 | 4 | 0 | 2 | 6 | 4 | 97.3% |
| processes | `Sensor Integration` | no | 6 | 4 | 1 | 1 | 6 | 4 | 97.3% |
| processes | `Turning` | no | 15 | 11 | 2 | 2 | 15 | 11 | 92.57% |
| processes | `Welding` | no | 15 | 11 | 1 | 3 | 15 | 11 | 92.57% |
| processes | `Wire Harness Manufacturing` | no | 5 | 3 | 0 | 2 | 5 | 3 | 97.97% |
| processes | `Wiring Harness Installation` | no | 5 | 3 | 0 | 2 | 5 | 3 | 97.97% |
| services | `Asset Management` | no | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |
| services | `Battery Collection` | **YES** | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Battery Engineering` | no | 15 | 9 | 2 | 4 | 15 | 9 | 93.92% |
| services | `Battery Repurposing` | **YES** | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Circular Economy Consulting` | **YES** | 5 | 2 | 1 | 2 | 5 | 2 | 98.65% |
| services | `Customer Support` | no | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |
| services | `Embedded Software Development` | no | 5 | 2 | 1 | 2 | 4 | 2 | 98.65% |
| services | `Inventory Management` | no | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |
| services | `Supplier Management` | no | 3 | 3 | 0 | 0 | 3 | 3 | 97.97% |
| services | `Systems Integration Engineering` | no | 5 | 3 | 1 | 1 | 5 | 3 | 97.97% |
| services | `Thermal Modeling` | no | 3 | 2 | 1 | 0 | 3 | 2 | 98.65% |
| services | `Vehicle Engineering` | no | 15 | 12 | 1 | 2 | 15 | 12 | 91.89% |
| services | `Warehousing` | no | 6 | 5 | 0 | 1 | 6 | 5 | 96.62% |

## Selected value holdouts (the actual 9)

| attribute | value | rows | train | dev | test | companies |
|---|---|--:|--:|--:|--:|--:|
| certifications | `AS9100` | 10 | 6 | 3 | 1 | 10 |
| certifications | `ISO/IEC 17025` | 10 | 8 | 1 | 1 | 10 |
| processes | `Battery Module Assembly` | 8 | 3 | 1 | 4 | 8 |
| processes | `Battery Pack Assembly` | 7 | 2 | 1 | 4 | 7 |
| processes | `Battery Recycling Logistics` | 5 | 2 | 1 | 2 | 5 |
| processes | `Refining` | 6 | 3 | 1 | 2 | 6 |
| services | `Battery Collection` | 5 | 2 | 1 | 2 | 5 |
| services | `Battery Repurposing` | 5 | 2 | 1 | 2 | 5 |
| services | `Circular Economy Consulting` | 5 | 2 | 1 | 2 | 5 |

### Cumulative attribute-level floor (union, not sum)

| attribute | row-band pool | eligible after minima | train rows | lost | remaining coverage | companies remaining |
|---|--:|--:|--:|--:|--:|--:|
| processes | 26 | 13 | 148 | 6 | **95.95%** | 95.74% |
| services | 13 | 7 | 148 | 2 | **98.65%** | 98.58% |
| certifications | 8 | 2 | 123 | 13 | **89.43%** | 88.79% |

A row carrying two held-out values is lost once, so the cumulative cost is the union of affected rows rather than the sum.

**Recorded selection characteristic, corrected (Phase 9 correction, finding 9B).** An earlier version of this document attributed the processes/services selection landing in the battery/EV cluster to "maximising test support" -- that was the v3.0 objective, and the sentence survived describing v3.1 numbers by mistake. The true v3.1 mechanism: these values are selected because they independently carry the LOWEST union train-row collateral among eligible candidates under the frozen minimize-collateral objective. Test support plays no causal role in v3.1 -- it is eligibility-only. That the collateral-minimal values also cluster in the battery/EV domain is a property of this frozen KB (those values happen to have low train support alongside adequate dev support), not a consequence of the selection objective.

## Operation holdouts

Held out: `argmax_topk`, `group_by`, `limit_only` — README Phase 22 requires all three defining constructs to appear **0 times** in training gold.

Exactly one `operation_family` per task by precedence (argmax_topk > group_by > limit_only); a task matching more than one held-out family is **excluded from training entirely** so the zero-occurrence assertion stays unambiguous. Detection is comment/quote-aware (Phase 9 correction): comments and string/identifier literals are replaced with a single space before keyword matching, so a lexical trick like `GROUP/**/BY` cannot evade it. Validated on synthetic fixtures — Phase 12 applies this frozen policy to the real task pool.

## Allowed operations per field (Phase 9 correction: previously absent)

README requires this contract to be frozen at Phase 9; it was missing until this correction. Four layers: semantic validity (what's meaningful for a field, including held-out operations where meaningful -- needed by the Phase 22 operation-heldout probe), the three query-level held-out constructs, named field-specific restrictions sourced verbatim from README, and the derived training-eligible set (semantic minus held-out, a literal set difference). This map is a candidate-generation-time heuristic; the authoritative training-eligibility gate is always the real SQL-construct scanner run against a task's actual rendered SQL.

```text
query-level constructs (held out everywhere): ['argmax_topk', 'group_by', 'limit_only']
named restrictions: ['address', 'primary_oems', 'row_id']
```

## Compositional holdout

Arity 2, one held-out set: **{certifications, processes}**, chosen by lowest train support then lexicographic.

**Collateral scope (frozen):** structured-task exclusion only. Individual component literals remain independently train-visible unless separately selected on the VALUE axis. An unseen COMBINATION is not an unseen VALUE.

**Multi-part tasks (Phase 9 correction):** for a multi-part task, T is the UNION of every declared part's component usage, not each part checked in isolation -- a multi-part task is one logical training item

## Conventions frozen here

- `logical_fingerprint` **lfp2** over 9 semantic fields (Phase 9 correction: lfp1 -> lfp2, folds canonicalized `logical_components` into the hash so AND/OR predicate structure is no longer invisible to it)
- multi-part serialization **parts_list_v1**, result representation **multipart_result_v1** (keyed independent per-part results, not a shared discriminator table)
- few-shot eligibility: fail closed, 8 conditions

## Exposure policy

`exposure_count == 0` for every held-out item across A, B, C, D, BC, BD, scanned on final rendered strings, after chat-template rendering, system-prompt and catalogue insertion, few-shot insertion and target rendering.

**Normalization (Phase 9 correction):** NFKC compatibility-normalize, casefold, collapse internal whitespace, then substring match -- NFC alone does not fold fullwidth Unicode forms (verified: NFC('ＡＳ９１００') != 'AS9100', NFKC(...) == 'AS9100'). Biased toward over-detection: a false positive costs one extra row to inspect, a false negative is an actual leak.

**Scope boundary:** applies to model-visible FINE-TUNING text only. The shared runtime value catalogue used by baselines (base_sql, base_sql_5shot) at INFERENCE legitimately contains every value, held-out included, per this same policy -- the scanner must never be run against that catalogue and must never flag it as a violation

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
| `operation_classification_deterministic` | PASS | one family per task by frozen precedence, including the GROUP/**/BY evasion attempt |
| `operation_multi_family_detected` | PASS | a GROUP BY + ORDER BY/LIMIT task is seen as two held-out families and is excluded from training (fail closed) |
| `operation_all_three_held_out` | PASS | README Phase 22 requires all three constructs at 0 occurrences |
| `allowed_operations_per_field_present` | PASS | README:388 'allowed operations per field' contract is frozen in the registry |
| `training_eligible_is_semantic_minus_heldout` | PASS | field_training_eligible_operations[f] == field_semantic_operations[f] - HELD_OUT_OPERATIONS for every field (exact set equality) |
| `no_held_out_family_ever_training_eligible` | PASS | no field's training-eligible set contains a held-out family |
| `named_field_restrictions_sourced_from_readme` | PASS | Primary OEMs / Address / row_id restrictions frozen verbatim from README |
| `fingerprint_same_for_equivalent` | PASS | wording/format-insensitive |
| `fingerprint_differs_on_value` | PASS | values_used differs |
| `fingerprint_differs_on_answer_type` | PASS | answer_type differs |
| `fingerprint_differs_on_and_vs_or` | PASS | lfp2 correction: AND and OR over the same predicates must differ (lfp1 collided these) |
| `fingerprint_same_on_commutative_reorder` | PASS | reordered AND operands hash identically (same logical task) |
| `fingerprint_missing_components_fails_closed` | PASS | missing logical_components raises rather than hashing a weaker skeleton |
| `multi_part_serialization_frozen` | PASS | explicit parts[]; Phase 7 stand-in could not express multi-operation parts |
| `multipart_result_representation_frozen` | PASS | keyed independent per-part execution results, not a shared discriminator-column table |
