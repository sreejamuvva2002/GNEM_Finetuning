# DB_VALIDATION_v3

Phase 5 — `gnem_v3.sqlite`. Child tables make multi-valued membership a clean equality join; the database is **scoped, not singular**.

## Provenance

```text
canonical_records_v3.jsonl   42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488
company_split_groups_v3.csv  a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701
finetune/kb_v3.py            67207659abe46cea7c090157a7ebeafce92196c7ffd4175eafe1d03ad83614ba
builder                      phase5_sqlite_v3.0
finetune/phase5_build_sqlite.py  262a330a90a55777416953436d5e30561690985b6a8ef6d46e7501bc89f39abb
datasets_v3/gnem_v3.sqlite   7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b
```

Built through the approved Phase 4 contract `kb_v3.load_kb("full_kb")`. There is no second cleaning path and geography is not re-parsed — `city`/`county` are taken from the Phase 4 derivation and compared cell-by-cell.

## Schema

```sql
CREATE TABLE companies (
    row_id                       INTEGER PRIMARY KEY NOT NULL,
    company                      TEXT    NOT NULL,
    category                     TEXT    NOT NULL,
    industry_group               TEXT    NOT NULL,
    location                     TEXT    NOT NULL,
    address                      TEXT    NOT NULL,
    primary_facility_type        TEXT    NOT NULL,
    ev_supply_chain_role         TEXT    NOT NULL,
    primary_oems                 TEXT    NOT NULL,
    supplier_or_affiliation_type TEXT    NOT NULL,
    employment                   INTEGER NOT NULL,
    product_or_service           TEXT    NOT NULL,
    ev_battery_relevant          TEXT    NOT NULL,
    classification_method        TEXT    NOT NULL,
    city                         TEXT,
    county                       TEXT
);

CREATE TABLE certifications (
    row_id          INTEGER NOT NULL REFERENCES companies(row_id),
    company         TEXT    NOT NULL,
    standard_family TEXT    NOT NULL
);

CREATE TABLE processes (
    row_id  INTEGER NOT NULL REFERENCES companies(row_id),
    company TEXT    NOT NULL,
    process TEXT    NOT NULL
);

CREATE TABLE services (
    row_id  INTEGER NOT NULL REFERENCES companies(row_id),
    company TEXT    NOT NULL,
    service TEXT    NOT NULL
);
```

`certification_count` is **not a column anywhere**: a model that can `COUNT` the child table must not be handed the answer. `split`, `split_group`, latitude, longitude and graph metadata are equally absent — leakage-control metadata never becomes queryable data.

Indexes created: **0** (none — README authorizes none).

## Table and child-row counts

All counts are derived from the canonical records, never hard-coded.

| table | rows | distinct terms | rows covered | companies covered |
|---|---|---|---|---|
| `companies` | 205 | — | 205 | 193 distinct names |
| `certifications` | 662 | 59 | 171 | 160 |
| `processes` | 555 | 49 | 205 | 193 |
| `services` | 290 | 22 | 205 | 193 |

All **205 row-level records are preserved**; the database is not collapsed to the 193 unique company names. `row_id` is the parent identity for every child relationship, so the repeated-company rows stay distinct records and each child fact attaches to the row that stated it.

The **34 rows carrying `None identified after search` produce zero certification child rows** — the sentinel is zero credential evidence, not a credential, and it is never stored as a `standard_family`.

## Integrity and round trip

```text
PRAGMA integrity_check     ok
PRAGMA foreign_key_check   0 violations
PRAGMA foreign_keys        ON
orphan child rows          0 (all three child tables)
child/parent company mismatches  0 (all three child tables)
case-insensitive ordering ambiguities = 0
```

**Round trip.** Each row's `processes`, `services` and `certifications` are reconstructed from the child tables under the frozen Phase 2 term-order rule (case-insensitive sort) — never relying on SQLite's natural row order — and compared against the frozen canonical records. All 205 rows × 3 fields reconstruct exactly. Rows with no certification child rows reconstruct to `None identified after search`, the zero-evidence state, not to a literal credential.

Because there are **zero** case-insensitive ordering ambiguities, the sort-based reconstruction is unique; no ordinal column or new normalization rule was needed or invented.

## Scoped views — the anti-leakage mechanism

12 views: three scopes × four tables. The `{scope}_companies` view carries the **only** scope filter for its scope; each child view inherits membership by joining that view on `row_id`, so scope logic is defined once per scope and cannot drift between tables.

| scope | companies visible | child views |
|---|---|---|
| `train_kb` | 148 | `train_kb_certifications`, `train_kb_processes`, `train_kb_services` |
| `train_dev_kb` | 165 | `train_dev_kb_certifications`, `train_dev_kb_processes`, `train_dev_kb_services` |
| `full_kb` | 205 | `full_kb_certifications`, `full_kb_processes`, `full_kb_services` |

`train_kb` provably excludes every dev and test row, and its child views leak zero dev/test child rows. No view exposes a forbidden column.

**Phase 5 exposes no query API.** `run_sql`, scope-neutral name resolution and the refusal-without-scope executor belong to **Phase 7**, so the base tables cannot become a de facto unscoped access path here. Model-facing schema prompts stay scope-neutral: the scoped view names above are executor infrastructure and are never taught to a model.

No fallback to a v2 `gnem.sqlite` exists anywhere in the repository.

## Determinism

A clean rebuild is **logically identical** table-by-table and in `sqlite_master`. Byte-identical SQLite file across rebuilds: **True**.

## Validation

| check | result | detail |
|---|---|---|
| `exactly_four_base_tables` | PASS | ['certifications', 'companies', 'processes', 'services'] |
| `no_forbidden_tables` | PASS | none of ['coordinates', 'edges', 'geo', 'geometry', 'graph_edges', 'oem_edges', 'oem_relationships', 'relationships', 'spatial_ref_sys'] present |
| `no_forbidden_columns_anywhere` | PASS | certification_count/split/split_group/lat/long/graph absent |
| `companies_columns_match_frozen_schema` | PASS | 16 columns |
| `schema_crosschecks_phase4_allowlist` | PASS | companies == MODEL_FACING_FIELDS minus the 3 multi-valued fields |
| `companies_row_count_205` | PASS | 205 == 205 |
| `row_id_unique` | PASS | 205 distinct row_id |
| `records_not_collapsed_to_companies` | PASS | 205 rows preserved across 193 distinct company names |
| `companies_values_match_phase4_contract` | PASS | 0 drifted cell(s) across 205 rows x 16 columns |
| `avs_row16_trailing_space_preserved` | PASS | '6110 McFarland Station Dr, Alpharetta, GA 30004 ' |
| `city_county_match_phase4_derivation` | PASS | 0 mismatch(es); geography not re-parsed |
| `certifications_row_count_matches_canonical` | PASS | 662 == 662 derived from canonical |
| `certifications_vocabulary_matches_canonical` | PASS | 59 == 59 distinct terms |
| `certifications_zero_orphans` | PASS | 0 orphan row(s) |
| `certifications_child_parent_company_match` | PASS | 0 child/parent company mismatch(es) |
| `certifications_terms_verbatim_from_canonical` | PASS | 0 term(s) not present verbatim in their canonical value |
| `processes_row_count_matches_canonical` | PASS | 555 == 555 derived from canonical |
| `processes_vocabulary_matches_canonical` | PASS | 49 == 49 distinct terms |
| `processes_zero_orphans` | PASS | 0 orphan row(s) |
| `processes_child_parent_company_match` | PASS | 0 child/parent company mismatch(es) |
| `processes_terms_verbatim_from_canonical` | PASS | 0 term(s) not present verbatim in their canonical value |
| `services_row_count_matches_canonical` | PASS | 290 == 290 derived from canonical |
| `services_vocabulary_matches_canonical` | PASS | 22 == 22 distinct terms |
| `services_zero_orphans` | PASS | 0 orphan row(s) |
| `services_child_parent_company_match` | PASS | 0 child/parent company mismatch(es) |
| `services_terms_verbatim_from_canonical` | PASS | 0 term(s) not present verbatim in their canonical value |
| `sentinel_yields_zero_certification_rows` | PASS | 34 sentinel row(s) -> 0 child rows |
| `sentinel_never_stored_as_a_credential` | PASS | 0 row(s) storing the sentinel as a standard_family |
| `round_trip_reconstructs_canonical_exactly` | PASS | 0 mismatch(es) across 205 rows x 3 fields |
| `case_insensitive_ordering_ambiguities_zero` | PASS | case-insensitive ordering ambiguities = 0 |
| `twelve_scoped_views_present` | PASS | 12 views: 3 scopes x 4 tables |
| `view_train_kb_companies_row_count` | PASS | 148 == 148 |
| `view_train_kb_membership_equals_frozen_split` | PASS | 148 row_ids identical to the frozen split |
| `view_train_kb_certifications_inherits_parent_scope` | PASS | 123 parent row_ids, all inside train_kb_companies |
| `view_train_kb_processes_inherits_parent_scope` | PASS | 148 parent row_ids, all inside train_kb_companies |
| `view_train_kb_services_inherits_parent_scope` | PASS | 148 parent row_ids, all inside train_kb_companies |
| `view_train_dev_kb_companies_row_count` | PASS | 165 == 165 |
| `view_train_dev_kb_membership_equals_frozen_split` | PASS | 165 row_ids identical to the frozen split |
| `view_train_dev_kb_certifications_inherits_parent_scope` | PASS | 137 parent row_ids, all inside train_dev_kb_companies |
| `view_train_dev_kb_processes_inherits_parent_scope` | PASS | 165 parent row_ids, all inside train_dev_kb_companies |
| `view_train_dev_kb_services_inherits_parent_scope` | PASS | 165 parent row_ids, all inside train_dev_kb_companies |
| `view_full_kb_companies_row_count` | PASS | 205 == 205 |
| `view_full_kb_membership_equals_frozen_split` | PASS | 205 row_ids identical to the frozen split |
| `view_full_kb_certifications_inherits_parent_scope` | PASS | 171 parent row_ids, all inside full_kb_companies |
| `view_full_kb_processes_inherits_parent_scope` | PASS | 205 parent row_ids, all inside full_kb_companies |
| `view_full_kb_services_inherits_parent_scope` | PASS | 205 parent row_ids, all inside full_kb_companies |
| `train_kb_view_excludes_all_dev_and_test` | PASS | 0 of 17 dev and 40 test rows visible in train_kb |
| `train_kb_certifications_leaks_no_dev_or_test_child_rows` | PASS | 0 leaked child row(s) |
| `train_kb_processes_leaks_no_dev_or_test_child_rows` | PASS | 0 leaked child row(s) |
| `train_kb_services_leaks_no_dev_or_test_child_rows` | PASS | 0 leaked child row(s) |
| `no_view_exposes_forbidden_column` | PASS | 19 distinct view columns, none forbidden |
| `pragma_integrity_check` | PASS | ok |
| `pragma_foreign_key_check` | PASS | 0 violation(s) |
| `foreign_keys_enforced_on_connection` | PASS | PRAGMA foreign_keys=1 |
| `no_unauthorized_indexes` | PASS | none created (README authorizes none) |
| `no_gnem_sqlite_fallback_anywhere` | PASS | 0 reference(s) to the v2 gnem.sqlite |
| `rebuild_logically_identical` | PASS | table-by-table contents identical across a clean rebuild |
