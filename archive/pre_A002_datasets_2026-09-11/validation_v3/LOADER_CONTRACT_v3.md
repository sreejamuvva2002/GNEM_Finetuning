# LOADER_CONTRACT_v3

Phase 4 — loader and data contract. One module defines what a row means to everything downstream.

## Frozen inputs

```text
canonical_records_v3.jsonl   42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488
company_split_groups_v3.csv  a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701
loader                       kb_v3.2_count_internal
finetune/kb_v3.py            2f13bc61212c7bd65103cb0c9f2a31c482e1589ec6f0fae47df9fe08ef9c7100
```

Both hashes are re-verified on **every** `load_kb()` call, not merely once at import, so drift cannot slip past a long-running process.

## The three KB scopes

`load_kb(scope)` takes scope as a **required positional parameter with no default**. There is no unscoped accessor, no convenience wrapper, no cached global and no module-level object holding all 205 rows. Scopes are derived from the frozen Phase 3 split; the expected counts are asserted as validation and are never the construction mechanism.

| scope | splits included | rows | exact companies | split groups | used for |
|---|---|---|---|---|---|
| `train_kb` | train | 148 | 141 | 134 | **all training targets** — A passages, B facts, C answers |
| `train_dev_kb` | dev, train | 165 | 158 | 151 | **dev evaluation gold only** |
| `full_kb` | dev, test, train | 205 | 193 | 186 | **test evaluation gold only**, and the deployed SQL database |

Phase 3 split sides: train 148 · dev 17 · test 40 rows.

`train_kb` ⊂ `train_dev_kb` ⊂ `full_kb`, strictly. No dev or test row is reachable through `train_kb`; no test row through `train_dev_kb`; all 40 test rows are reachable only through `full_kb`.

## Geographic derivation (Amendment A-001)

`city`/`county` are derived **only** from geographic information explicitly present in that row's own canonical `Location`. `derive_city_county()` receives the location string and nothing else, so it is structurally incapable of consulting `Address`, ZIP, external geocoding, company knowledge, latitude/longitude, or another row.

| outcome | rows |
|---|---|
| city derived | 202 |
| county derived | 202 |
| city NULL | 3 |
| county NULL | 3 |
| sentinel `Location` → NULL/NULL | 3 |
| real `Location` not fully parseable | 0 |

County text is preserved **verbatim as represented** — `"Hall County"`, never normalized to `"Hall"`. Stripping the type-word is a normalization no rule authorizes.

### Frozen A-001 cases

```text
row 187  Valeo
    location = 'Not specified'
    address  = 'Not specified'
    city     = None   county = None
row 192  Volvo Cars USA
    location = 'Not applicable'
    address  = '1800 Volvo Place, Mahwah, NJ 07430'
    city     = None   county = None
row 193  Volvo Group North America
    location = 'Not applicable'
    address  = '7900 National Service Rd, Greensboro, NC 27409'
    city     = None   county = None
```

### Hyundai shared address — deliberately NOT reconciled

Rows 80, 83 and 93 share one `Address` but state three different counties. Each row's own `Location` is parsed independently; `Address` is irrelevant to derivation, so the inconsistency is carried through as frozen-source behaviour rather than repaired.

```text
row 80  location='Ellabell, Forsyth County' -> county='Forsyth County'
row 83  location='Ellabell, Bryan County' -> county='Bryan County'
row 93  location='Ellabell, Lowndes County' -> county='Lowndes County'
    all three share address '700 Hyundai Blvd, Ellabell, GA 31308' (ignored)
```

No latitude, longitude, geocoding, distance, radius, nearest-company logic, spatial index or geo SQL is introduced. `city`/`county` are ordinary structured attributes.

## Model-facing contract

`model_facing_record()` builds its result from an explicit **allowlist** of 19 fields — it is not a full record with prohibited fields deleted afterwards, so a field added to the internal record cannot leak by omission.

Structurally absent from model-facing output: `certification_count`, `geo`, `graph_edges`, `graph_id`, `latitude`, `longitude`, `split`, `split_group`.

The user-authorized A-002 exception keeps `certification_count` for source validation only; complete certification lists remain model-facing. `split` and `split_group` are leakage-control metadata, exposed solely through the separate `split_metadata()` accessor and never merged into a record.

## Static training-generator check

README Phase 4 requires a static check that no training generator can reach `full_kb`. It is implemented and **reusable**, but its coverage today is reported honestly:

```text
training generators scanned      = 6
forbidden full_kb call sites     = 0
```

The six existing direct training renderers were scanned for forbidden scope literals. This is not a proof about transitive imports or runtime accesses. Every later training-data phase must re-run `static_check_no_training_generator_reaches_full_kb()` with its own module paths and report the scanned count.

## Validation

| check | result | detail |
|---|---|---|
| `canonical_sha_matches_phase2` | PASS | 42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488 |
| `split_sha_matches_phase3` | PASS | a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701 |
| `canonical_and_split_row_ids_identical` | PASS | 205 canonical vs 205 split rows |
| `train_kb_row_count` | PASS | 148 == 148 |
| `train_dev_kb_row_count` | PASS | 165 == 165 |
| `full_kb_row_count` | PASS | 205 == 205 |
| `train_kb_ids_equal_phase3_train` | PASS | 148 rows == exact train split |
| `train_dev_kb_ids_equal_train_union_dev` | PASS | 165 rows == train ∪ dev |
| `full_kb_ids_equal_all_205` | PASS | 205 rows == all canonical row_ids |
| `scope_nesting_train_sub_traindev_sub_full` | PASS | train_kb ⊂ train_dev_kb ⊂ full_kb (strict) |
| `no_dev_rows_in_train_kb` | PASS | 0 dev rows leaked |
| `no_test_rows_in_train_kb` | PASS | 0 test rows leaked |
| `no_test_rows_in_train_dev_kb` | PASS | 0 test rows leaked |
| `all_test_rows_only_via_full_kb` | PASS | all 40 test rows reachable only through full_kb |
| `no_company_partially_inside_a_scope` | PASS | 0 partial companies |
| `no_split_group_partially_inside_a_scope` | PASS | 0 partial split groups |
| `all_18_canonical_fields_mapped` | PASS | 18 fields |
| `canonical_values_preserved_byte_for_byte` | PASS | 0 drifted field(s) across 205 rows |
| `avs_row16_trailing_space_preserved` | PASS | '6110 McFarland Station Dr, Alpharetta, GA 30004 ' |
| `employment_populated_all_rows` | PASS | 205/205 |
| `model_facing_excludes_forbidden_fields` | PASS | 19 allowlisted fields; split/split_group/certification_count/lat/long absent; other source fields included |
| `model_facing_is_allowlist_not_deletion` | PASS | projection built from MODEL_FACING_FIELDS |
| `all_nonexcluded_source_fields_model_facing_under_a002` | PASS | all 17 nonexcluded source fields preserved for all 205 rows |
| `certification_count_internal_only_and_source_preserved` | PASS | source count retained internally, including zeros; excluded from model-facing records |
| `no_latitude_longitude_anywhere` | PASS | no geo columns produced |
| `derived_geo_is_literal_substring_of_own_location` | PASS | 0 value(s) not present in their own Location |
| `address_independence_proven` | PASS | re-derivation from Location alone is byte-identical |
| `sentinel_locations_yield_null_geo` | PASS | 3 sentinel row(s) -> NULL/NULL |
| `a001_valeo_187` | PASS | location/address = Not specified, city/county NULL |
| `a001_volvo_192_193` | PASS | location = Not applicable, real NJ/NC address preserved, city/county NULL |
| `hyundai_counties_not_reconciled` | PASS | 3 distinct counties from 3 Locations despite 1 shared Address |
| `no_unparseable_real_locations` | PASS | 0 real Location(s) not fully parseable |
| `geo_derivation_deterministic` | PASS | repeat derivation identical |
| `static_check_reports_coverage_honestly` | PASS | training generators scanned = 6; forbidden full_kb call sites = 0; proves no forbidden scope literal in 6 scanned file(s) |

## Fault injection

Each fault must be rejected. A gate that only passes on good input proves little.

| fault | rejected | how |
|---|---|---|
| `omitted_scope` | yes | TypeError: load_kb() missing 1 required positional argument: 'scope' |
| `none_scope` | yes | ScopeError: KB scope is required and must be named explicitly; got None. Valid scopes: tra |
| `invalid_scope_string` | yes | ScopeError: unknown KB scope 'full'; there is no default scope. Valid scopes: train_kb, tr |
| `invalid_scope_type` | yes | ScopeError: unknown KB scope 123; there is no default scope. Valid scopes: train_kb, train |
| `case_variant_scope` | yes | ScopeError: unknown KB scope 'FULL_KB'; there is no default scope. Valid scopes: train_kb, |
| `canonical_hash_drift` | yes | IntegrityError: canonical records drifted |
| `split_hash_drift` | yes | IntegrityError: split artifact drifted |
| `incorrect_split_membership` | yes | IntegrityError: scope 'train_kb' produced 188 rows, expected 148 |
| `model_facing_leak_detected` | yes | ScopeError: model-facing projection would expose split_group |
| `geography_cannot_depend_on_address` | yes | ScopeError: Address '301 Teco Dr, Pendergrass, GA 30567' yields (None, None), never the ro |
