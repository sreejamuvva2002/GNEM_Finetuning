# NORMALIZATION_REPORT_v3

Phase 2 — clean, normalize, and freeze canonical records.

## Hash chain

```text
raw workbook        a8a4ca5c72211e7e2e32bbf418873f86677b7fb1264d2c657955b3fee008b034
cleaning code       72ad2b52f4777b09b3cc585b783390311e426597b88a882e85a5d6362f5974a5
canonical records   42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488
```

The source hash was re-verified against `SOURCE_MANIFEST_v3.json` before any artifact was produced.

## What changed

**277 cells changed** across 154 of 205 rows. No row was added, dropped or reordered.

| field | cells changed |
|---|---|
| `processes` | 134 |
| `certifications` | 37 |
| `services` | 36 |
| `primary_oems` | 26 |
| `supplier_or_affiliation_type` | 26 |
| `primary_facility_type` | 11 |
| `location` | 3 |
| `category` | 3 |
| `address` | 1 |

| change type | cells |
|---|---|
| `multivalue_canonical_order` | 173 |
| `sentinel_none_identified` | 34 |
| `sentinel_primary_oems` | 26 |
| `sentinel_supplier_affiliation` | 26 |
| `facility_type_normalization` | 11 |
| `sentinel_location` | 3 |
| `category_normalization` | 3 |
| `sentinel_address` | 1 |

Every changed cell is listed individually in `CLEANING_AUDIT_v3.csv` with its old value, new value, change type and the frozen rule that authorised it.

## Value normalization

### Category

| value | rows |
|---|---|
| `Tier 1` | 77 |
| `Tier 2/3` | 73 |
| `Tier 1/2` | 18 |
| `OEM Supply Chain` | 17 |
| `OEM` | 12 |
| `OEM (Footprint)` | 8 |

`OEM Footprint` → `OEM (Footprint)`: 3 rows remapped, joining 5 already correct, giving **8**. `OEM Footprint` is now **0**.

### Primary Facility Type

| value | rows |
|---|---|
| `Manufacturing Plant` | 187 |
| `Manufacturing` | 4 |
| `Manufacturing / Engineering` | 3 |
| `Engineering / Operations` | 3 |
| `North American Headquarters` | 2 |
| `Corporate operations` | 2 |
| `Headquarters` | 1 |
| `R&D` | 1 |
| `Manufacturing / OEM operations` | 1 |
| `Regional corporate operations` | 1 |

`Manufacturing plant` → `Manufacturing Plant`: 10 rows remapped, joining 177, giving **187**. `Engineering / Manufacturing` → `Manufacturing / Engineering`: 1 row. `Manufacturing` remains a distinct value at **4**.

## Multi-valued fields

`Processes`, `Services`, `Certifications` were split on `;`, trimmed, emptied terms dropped, exact duplicates removed case-insensitively, sorted case-insensitively and rejoined as `"; "`. **Term spelling is preserved exactly**; no taxonomy normalization was applied.

| field | cells reordered/rejoined |
|---|---|
| `processes` | 134 |
| `services` | 36 |
| `certifications` | 3 |

(`certifications` sentinel insertions are counted under Sentinels below, not here.)

## Sentinels applied

Frozen meanings — none proves a real-world negative.

| sentinel | meaning | cells |
|---|---|---|
| `Not specified` | source unknown/unprovided | 45 |
| `Not applicable` | structurally does not apply | 11 |
| `None identified after search` | no credential evidence | 34 |

### Ordering rule

`Certification Count` was validated against the **pre-sentinel** certification parse on all 205 rows (0 mismatches) **before** the `None identified after search` sentinel was inserted. The 34 sentinel rows all carry `certification_count == 0`, so the sentinel still represents **zero certification terms** for later child-table construction.

### Geography (Amendment A-001)

```text
row 187  Valeo                      location = Not specified   (source unknown)
                                    address  = Not specified
row 192  Volvo Cars USA             location = Not applicable  (structurally N/A)
                                    address  = 1800 Volvo Place, Mahwah, NJ 07430
row 193  Volvo Group North America  location = Not applicable
                                    address  = 7900 National Service Rd, Greensboro, NC 27409
```

`Address` was never substituted for `Location`. **No `city`/`county` field is materialized in Phase 2** — that derivation belongs to the Phase 4 loader, and may read only geographic information explicitly present in a real `Location` value.

## Judgment calls, recorded

- **The single blank `Supplier or Affiliation Type` on an `OEM`-category row was NOT imputed.** 11 of 12 `OEM` rows carry `Original Equipment Manufacturer`, but sibling-row frequency is not source evidence for the twelfth. It received `Not specified` like every other blank, and the pattern is recorded here rather than acted on.

- **Multi-row companies were left untouched.** 9 companies occupy 21 rows. Conflict handling, `split_group` and identity grouping are Phase 3+.

- **No generic scalar normalization.** Fields with no explicit frozen rule preserve the exact workbook value, surrounding whitespace included. `strip()` is used only to detect an effectively-blank cell so its frozen sentinel rule can apply. Row 16 (AVS) therefore retains its trailing space in `address`, exactly as stored. A validation reconstructs every canonical value from source under the frozen rules alone and fails on any difference, so this class of defect cannot recur silently in another field.

## Validation

| check | result | detail |
|---|---|---|
| `canonical_row_count` | PASS | 205 == 205 |
| `row_id_unique` | PASS | 205 unique == 205 |
| `no_rows_dropped` | PASS | row_id set == source set |
| `category::OEM Footprint` | PASS | 0 == 0 |
| `category::OEM (Footprint)` | PASS | 8 == 8 |
| `facility::Manufacturing plant` | PASS | 0 == 0 |
| `facility::Manufacturing Plant` | PASS | 187 == 187 |
| `facility::Manufacturing` | PASS | 4 == 4 |
| `facility::Engineering / Manufacturing` | PASS | 0 == 0 |
| `processes_canonically_ordered` | PASS | 0 non-canonical |
| `services_canonically_ordered` | PASS | 0 non-canonical |
| `certifications_canonically_ordered` | PASS | 0 non-canonical |
| `certification_count_matches_pre_sentinel_parse` | PASS | validated on 205/205 rows, 0 mismatches |
| `cert_sentinel_means_zero_terms` | PASS | 0 sentinel rows with nonzero count |
| `employment_populated` | PASS | 205/205 populated |
| `employment_values_preserved` | PASS | byte-equal to source |
| `employment_no_zero_imputation` | PASS | 0 zero values |
| `valeo_location_not_specified` | PASS | 'Not specified' |
| `valeo_address_not_specified` | PASS | 'Not specified' |
| `volvo_192_location_not_applicable` | PASS | 'Not applicable' |
| `volvo_192_address_preserved` | PASS | '1800 Volvo Place, Mahwah, NJ 07430' |
| `volvo_193_location_not_applicable` | PASS | 'Not applicable' |
| `volvo_193_address_preserved` | PASS | '7900 National Service Rd, Greensboro, NC 27409' |
| `supplier_blanks_all_not_specified` | PASS | 26/26 blanks -> Not specified |
| `no_supplier_imputation` | PASS | no blank filled with a sibling-row value |
| `no_city_county_materialized` | PASS | absent: ['city', 'county', 'latitude', 'longitude', 'split_group'] |
| `no_unauthorized_company_normalization` | PASS | company == exact trimmed source value |
| `only_authorized_transformations` | PASS | 0 unauthorized field transformation(s) |
| `scalar_passthrough_byte_preserved` | PASS | 1789/1789 nonblank scalar cells identical to source |
| `avs_row16_address_exact` | PASS | canonical == source ('6110 McFarland Station Dr, Alpharetta, GA 30004 ') |
