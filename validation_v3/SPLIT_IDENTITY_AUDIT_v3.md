# SPLIT_IDENTITY_AUDIT_v3

Phase 3 — identity, split groups, and the frozen train/dev/test split.

## Input provenance

```text
canonical_records_v3.jsonl  42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488
phase2_clean_records.py     72ad2b52f4777b09b3cc585b783390311e426597b88a882e85a5d6362f5974a5
detector version            split_detect_v3.1
split seed                  20260823
target allocation           train 70% / dev 10% / test 20% at split-group level
allocation method           stratified by category; OEM-referenced groups placed first and held in
```

## The three identities

| concept | definition | used for |
|---|---|---|
| `row_id` | exact `Record No.` | row identity |
| `company` | exact trimmed `Company` | **answer / database identity** |
| `split_group` | organizational leakage-control identity | **only** to keep related names off opposite sides |

`split_group` is leakage-control metadata. It is **never** the answer identity, **never** model-visible, and no exact `company` string was altered, merged, canonicalized or renamed. Answer semantics — including Q29 behaviour — continue to rest on the exact trimmed company name.

## Detector

`split_detect_key()` (split_detect_v3.1) is a deliberate self-contained **copy**, never an import of `grade.norm_company` or any successor, so grading changes cannot silently move split boundaries. It proposes **candidates only**; grouping requires explicit human approval.

### Approved collision mappings

| split_group | exact companies | basis |
|---|---|---|
| `ecoplastic` | `Ecoplastic America Corporation` · `Ecoplastic Corporation` | README.md Phase 3 predeclared collision pair |
| `hitachi_astemo` | `Hitachi Astemo` · `Hitachi Astemo Americas Inc.` | README.md Phase 3 predeclared collision pair |
| `jefferson_southern` | `Jefferson Southern Corp.` · `Jefferson Southern Corporation` | README.md Phase 3 predeclared collision pair |
| `trenton_pressing` | `Trenton Pressing` · `Trenton Pressing Inc.` | README.md Phase 3 predeclared collision pair |
| `lund_international` | `Lund International Inc.` · `Lund International Inc./Ventshade Division` | user-adjudicated 2026-08-23: name containment (one name contains the other) plus identical facility evidence -- same address, county, category and employment |
| `seoyon_ehwa` | `Seoyon E-HWA` · `Seoyon E-Hwa Interior Systems` | user-adjudicated 2026-08-23: case-variant of the same name plus a descriptive tail, with identical facility evidence |
| `great_dane` | `Great Dane LP` · `Great Dane Trailers` | user-adjudicated 2026-08-23: name-variant evidence with identical facility evidence -- same address, county and category |

**Approval basis, stated precisely.** The four predeclared pairs come from `README.md` Phase 3. The three added groups — `lund_international`, `seoyon_ehwa`, `great_dane` — are approved leakage-control collisions because they combine strong name-variant/containment evidence, identical facility evidence, and explicit human adjudication.

**No general rule is encoded that identical addresses imply the same `split_group`.** The Hyundai campus entities share an address yet represent distinct named entities, and shared address alone is not sufficient for grouping, so they remain separate.

### Candidates deliberately NOT grouped

| exact companies | reason |
|---|---|
| `Hyundai Motor Group` · `Hyundai Industrial Co.` · `Hyundai & LG Energy Solution (LGES)` | distinct named legal entities sharing one campus address. Shared address alone is not sufficient evidence for grouping (user-adjudicated 2026-08-23) |
| `Hyundai Motor Group` · `Hyundai MOBIS (Georgia)` · `Hyundai Transys Georgia Powertrain` · `Hyundai Transys Georgia Seating Systems` · `Hyundai Industrial Co.` · `Hyundai & LG Energy Solution (LGES)` | shared brand token only; distinct legal entities at distinct facilities (user-adjudicated 2026-08-23) |
| `Continental Automotive` · `Continental Tire the Americas LLC` | distinct facilities in different counties (Fairburn/Fayette vs Barnesville/Lamar); shared brand only (user-adjudicated 2026-08-23) |
| `Daesol Ausys` · `Daesol Material Georgia, LLC` | distinct facilities in different counties (Smyrna/Cobb vs Duluth/Gwinnett); shared brand only (user-adjudicated 2026-08-23) |
| `Volvo Cars USA` · `Volvo Group North America` | genuinely separate corporate groups in different states; not one organization (user-adjudicated 2026-08-23) |
| `PAI Industries Inc.` · `PPG Industries Inc.` | unrelated companies; fuzzy-similarity false positive (user-adjudicated 2026-08-23) |
| `Blue Bird Corp.` · `Blue Ridge Manufacturing` | unrelated companies sharing only a first token (user-adjudicated 2026-08-23) |

### Full candidate disposition

22 candidate group(s) were produced by the primary detector and the three secondary sweeps (shared first token, token-prefix containment, fuzzy similarity ≥ 0.86). Every one has an explicit disposition; **zero are unmapped**. A candidate in neither the approved nor the reviewed list fails the build.

| origin | companies | disposition |
|---|---|---|
| `primary:suffix_key='ecoplastic'` | `Ecoplastic America Corporation` · `Ecoplastic Corporation` | APPROVED -> grouped |
| `primary:suffix_key='hitachi astemo'` | `Hitachi Astemo` · `Hitachi Astemo Americas Inc.` | APPROVED -> grouped |
| `primary:suffix_key='jefferson southern'` | `Jefferson Southern Corp.` · `Jefferson Southern Corporation` | APPROVED -> grouped |
| `primary:suffix_key='trenton pressing'` | `Trenton Pressing` · `Trenton Pressing Inc.` | APPROVED -> grouped |
| `sweep_a:first_token='great'` | `Great Dane LP` · `Great Dane Trailers` | APPROVED -> grouped |
| `sweep_a:first_token='lund'` | `Lund International Inc.` · `Lund International Inc./Ventshade Division` | APPROVED -> grouped |
| `sweep_a:first_token='seoyon'` | `Seoyon E-HWA` · `Seoyon E-Hwa Interior Systems` | APPROVED -> grouped |
| `sweep_a:first_token='blue'` | `Blue Bird Corp.` · `Blue Ridge Manufacturing` | REVIEWED -> deliberately not grouped |
| `sweep_a:first_token='continental'` | `Continental Automotive` · `Continental Tire the Americas LLC` | REVIEWED -> deliberately not grouped |
| `sweep_a:first_token='daesol'` | `Daesol Ausys` · `Daesol Material Georgia, LLC` | REVIEWED -> deliberately not grouped |
| `sweep_a:first_token='hyundai'` | `Hyundai & LG Energy Solution (LGES)` · `Hyundai Industrial Co.` · `Hyundai MOBIS (Georgia)` · `Hyundai Motor Group` · `Hyundai Transys Georgia Powertrain` · `Hyundai Transys Georgia Seating Systems` | REVIEWED -> deliberately not grouped |
| `sweep_a:first_token='volvo'` | `Volvo Cars USA` · `Volvo Group North America` | REVIEWED -> deliberately not grouped |
| `sweep_c:fuzzy>=0.86` | `PAI Industries Inc.` · `PPG Industries Inc.` | REVIEWED -> deliberately not grouped |

## OEM-reference guard

Derived dynamically from the canonical data — **never** asserted against a constant. Excluding the non-entity placeholders (Multiple OEMs, None identified after search, Not applicable, Not available, Not specified), 25 rows carry entity-bearing `primary_oems`.

**Derived count: 11 companies across 11 split groups**, all forced held-in (train).

| company | referenced by row_id | split_group |
|---|---|---|
| `Archer Aviation Inc.` | 179 | `Archer Aviation Inc.` |
| `Blue Bird Corp.` | 175 | `Blue Bird Corp.` |
| `Club Car LLC` | 95 | `Club Car LLC` |
| `Hyundai Motor Group` | 171 | `Hyundai Motor Group` |
| `Kia Georgia Inc.` | 173 | `Kia Georgia Inc.` |
| `Mercedes-Benz USA LLC` | 174 | `Mercedes-Benz USA LLC` |
| `Porsche Cars North America Inc.` | 116 | `Porsche Cars North America Inc.` |
| `Rivian Automotive` | 172 | `Rivian Automotive` |
| `SK Battery America` | 178 | `SK Battery America` |
| `Textron Specialized Vehicles` | 177 | `Textron Specialized Vehicles` |
| `Yamaha Motor Manufacturing Corp.` | 176 | `Yamaha Motor Manufacturing Corp.` |

### Composite values and why no guess was needed

3 `primary_oems` value(s) name OEM brands but match no company exactly: `Blue Bird`, `Hyundai Kia`, `Hyundai Kia Rivian`. The guard uses **exact matching only**. Every brand token appearing in those composites is already covered by a company that is exactly referenced elsewhere, so the composites introduce no brand the guard has not captured — this is asserted, not assumed. A looser brand-token expansion would instead pull in additional entities (the other Hyundai companies), which would be precisely the organizational guess the protocol forbids and which was adjudicated against. No guess was made. `Multiple OEMs` is preserved as a non-entity placeholder and never becomes an entity. No graph normalization or recursive relationship logic is introduced — `primary_oems` remains the frozen composite factual field, and this guard is leakage control only.

### Limitation created by the guard

Forcing 11 OEM-referenced groups held-in removes them from the dev/test pool. Those companies are structurally absent from the test distribution, so test results cannot speak to them. This is the price of preventing their identities leaking through another company's answer, and must be stated in the final report.

## Realized split

Target 70/10/20 is an allocation **target at split-group level**, not a quota. Realized figures are reported as they fell, without distorting leakage-control grouping or OEM-reference placement to hit round numbers.

| side | split groups | % | exact companies | % | rows | % |
|---|---|---|---|---|---|---|
| train | 134 | 72.0% | 141 | 73.1% | 148 | 72.2% |
| dev | 17 | 9.1% | 17 | 8.8% | 17 | 8.3% |
| test | 35 | 18.8% | 35 | 18.1% | 40 | 19.5% |
| **total** | **186** | 100% | **193** | 100% | **205** | 100% |

## Stratification / distribution audit

A rare attribute landing entirely on one side would be pathological. Counts below are per side; any attribute absent from a side is flagged.

### Category

| value | rows | train | dev | test | absent from | assessment |
|---|---|---|---|---|---|---|
| `Tier 1` | 77 | 58 | 6 | 13 | — | covered |
| `Tier 2/3` | 73 | 52 | 6 | 15 | — | covered |
| `Tier 1/2` | 18 | 13 | 2 | 3 | — | covered |
| `OEM Supply Chain` | 17 | 12 | 1 | 4 | — | covered |
| `OEM` | 12 | 9 | 1 | 2 | — | covered |
| `OEM (Footprint)` | 8 | 4 | 1 | 3 | — | covered |

### Primary facility type

| value | rows | train | dev | test | absent from | assessment |
|---|---|---|---|---|---|---|
| `Manufacturing Plant` | 187 | 139 | 16 | 32 | — | covered |
| `Manufacturing` | 4 | 1 | 0 | 3 | dev | **notable gap** |
| `Manufacturing / Engineering` | 3 | 3 | 0 | 0 | dev, test | **notable gap** |
| `Engineering / Operations` | 3 | 1 | 1 | 1 | — | covered |
| `North American Headquarters` | 2 | 0 | 0 | 2 | train, dev | structural — too few rows to span three sides |
| `Corporate operations` | 2 | 2 | 0 | 0 | dev, test | structural — too few rows to span three sides |
| `Headquarters` | 1 | 1 | 0 | 0 | dev, test | structural — too few rows to span three sides |
| `R&D` | 1 | 0 | 0 | 1 | train, dev | structural — too few rows to span three sides |
| `Manufacturing / OEM operations` | 1 | 0 | 0 | 1 | train, dev | structural — too few rows to span three sides |
| `Regional corporate operations` | 1 | 1 | 0 | 0 | dev, test | structural — too few rows to span three sides |

### Certification presence

| value | rows | train | dev | test | absent from | assessment |
|---|---|---|---|---|---|---|
| `has certifications` | 171 | 123 | 14 | 34 | — | covered |
| `none identified` | 34 | 25 | 3 | 6 | — | covered |

### Process coverage

| value | rows | train | dev | test | absent from | assessment |
|---|---|---|---|---|---|---|
| `2 process term(s)` | 62 | 41 | 7 | 14 | — | covered |
| `1 process term(s)` | 48 | 36 | 4 | 8 | — | covered |
| `5 process term(s)` | 35 | 25 | 3 | 7 | — | covered |
| `3 process term(s)` | 32 | 24 | 3 | 5 | — | covered |
| `4 process term(s)` | 28 | 22 | 0 | 6 | dev | **notable gap** |

### Service coverage

| value | rows | train | dev | test | absent from | assessment |
|---|---|---|---|---|---|---|
| `1 service term(s)` | 151 | 108 | 13 | 30 | — | covered |
| `2 service term(s)` | 31 | 23 | 3 | 5 | — | covered |
| `3 service term(s)` | 15 | 13 | 0 | 2 | dev | **notable gap** |
| `4 service term(s)` | 8 | 4 | 1 | 3 | — | covered |

### Residual gaps after stratification

The split is stratified by **category**, which is what the audit found actually broken: an unstratified draw placed 0 of 17 `OEM Supply Chain` rows in test even though only 1 was guard-forced. After stratification every category appears on all three sides. Remaining gaps are reported, not engineered away — further simultaneous stratification on facility type and term-count would over-constrain a 186-group split whose dev side is only ~17 groups, and would amount to fitting the split to the audit.

**4 notable residual gap(s)** (values on ≥3 rows missing from a side). Most are dev-side absences driven by dev holding only ~9% of groups:

- `Manufacturing` (Primary facility type): 4 rows, absent from dev
- `Manufacturing / Engineering` (Primary facility type): 3 rows, absent from dev, test
- `4 process term(s)` (Process coverage): 28 rows, absent from dev
- `3 service term(s)` (Service coverage): 15 rows, absent from dev

Values on fewer than three rows cannot span three sides and are marked structural rather than pathological.

### Multi-row companies

| company | rows | split |
|---|---|---|
| `Novelis Inc.` | 3 | train |
| `Sewon America Inc.` | 3 | train |
| `ZF Gainesville LLC` | 3 | test |
| `Arising Industries Inc.` | 2 | test |
| `Freudenberg-NOK` | 2 | test |
| `Haering Precision USA LP` | 2 | train |
| `Lyle Industries Inc.` | 2 | train |
| `Panasonic Automotive Systems Co.` | 2 | train |
| `TI Fluid Systems` | 2 | test |

All rows of each multi-row company sit on a single side, as do all members of each approved collision group.

Multi-row **factual conflicts** are deliberately not resolved here and `MULTIROW_CONFLICTS_v3.csv` is not created — that belongs to the later factual-training/probe logic.

## Data-quality observation (not Phase 3's to fix)

Rows 83, 93 and 80 share `700 Hyundai Blvd, Ellabell, GA 31308` but record three different counties — `Ellabell, Bryan County`, `Ellabell, Lowndes County`, `Ellabell, Forsyth County`. One city, three counties. This is frozen canonical data; Phase 3 does not rewrite it. Recorded for whoever owns the factual-conflict phase.

## Validation

| check | result | detail |
|---|---|---|
| `canonical_sha_matches_phase2` | PASS | 42851c0a2e93209a… |
| `cleaning_code_sha_matches_phase2` | PASS | 72ad2b52f4777b09… |
| `canonical_rows` | PASS | 205 == 205 |
| `exact_companies` | PASS | 193 == 193 |
| `every_row_assigned_one_split` | PASS | 205/205 rows assigned |
| `every_company_one_side` | PASS | 0 companies straddling |
| `every_split_group_one_side` | PASS | 0 groups straddling |
| `protocol_four_pairs_grouped` | PASS | all four share a split_group |
| `all_seven_approved_groups_intact` | PASS | 7 approved groups |
| `detector_zero_unmapped_collisions` | PASS | 22 candidate(s) evaluated, 0 unmapped |
| `oem_guard_derived_dynamically` | PASS | 11 companies derived (never asserted as a constant) |
| `oem_reference_placement_rule` | PASS | 11 OEM-referenced groups all held-in (train); 0 misplaced |
| `oem_candidates_exclude_placeholders` | PASS | sentinels and 'Multiple OEMs' excluded from entity candidates |
| `composite_oem_brands_already_exactly_referenced` | PASS | every brand token in a composite value is already covered by an exactly-referenced company |
| `train_non_empty` | PASS | 134 split groups |
| `dev_non_empty` | PASS | 17 split groups |
| `test_non_empty` | PASS | 35 split groups |
| `no_company_normalization_applied` | PASS | exact company strings untouched; split_group is separate metadata |
| `no_rows_dropped` | PASS | 205 unique row_id |
