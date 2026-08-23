"""Phase 5 -- build `gnem_v3.sqlite`.

Multi-valued fields cannot be queried with `WHERE col = 'value'` against a
`;`-joined cell, so child tables make membership a clean equality join and keep
the JOIN-learning test alive (README.md Phase 5).

FOUR TABLES, exactly as frozen:

    companies(row_id PK, ... scalars only ...)
    certifications(row_id -> companies.row_id, company, standard_family)
    processes(row_id -> companies.row_id, company, process)
    services(row_id -> companies.row_id, company, service)

No graph_edges. No coordinates. No OEM relationship table. No spatial index.

`certification_count` is deliberately NOT a column anywhere: a model that can
COUNT the child table must not be handed the answer. `split` and `split_group`
are likewise absent -- leakage-control metadata never becomes queryable data.

THE DATABASE IS SCOPED, NOT SINGULAR. Every gold in the task pool is produced by
executing a query, so a single all-rows database would compute `train_kb_gold`
over test data. Three read-only scoped view sets cover all four tables:

    {scope}_companies       row_id filtered by the frozen Phase 3 split
    {scope}_certifications  \\
    {scope}_processes        > INHERIT membership by joining the scoped
    {scope}_services        /  companies view on row_id -- scope logic is
                               defined once per scope, never duplicated

Built through the approved Phase 4 contract (`kb_v3.load_kb("full_kb")`). There
is no second cleaning path and geography is not re-parsed.

NOT IN THIS PHASE: `run_sql`, any SQL executor, any scope-neutral name
resolution, any query helper. Phase 7 owns SQL execution. This module exposes NO
query API, so the base tables cannot become a de facto unscoped access path.
Model-facing schema prompts stay scope-neutral: the scoped view names defined
here are executor infrastructure and are never taught to a model.

A failing gate writes NO final artifact: the database is built to a temporary
path, validated there, and only moved into place once every gate passes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as kb  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "datasets_v3" / "canonical_records_v3.jsonl"
OUT_DB = ROOT / "datasets_v3" / "gnem_v3.sqlite"
OUT_AUDIT = ROOT / "validation_v3" / "DB_VALIDATION_v3.md"

BUILDER_VERSION = "phase5_sqlite_v3.0"
CERT_SENTINEL = "None identified after search"
# Assembled at runtime so this file does not itself contain the literal the
# scan looks for. That keeps the scan global -- excluding the checker's own
# file would create exactly the blind spot the check exists to prevent.
V2_DB_NEEDLE = "gnem" + "." + "sqlite"
TERM_SEP = "; "

# Explicit frozen schema. Deliberately NOT generated from MODEL_FACING_FIELDS --
# the database contract must not silently change if that list is later edited.
# The Phase 4 allowlist is used as a cross-check instead (see _gate_schema).
COMPANIES_COLUMNS = (
    "row_id", "company", "category", "industry_group", "location", "address",
    "primary_facility_type", "ev_supply_chain_role", "primary_oems",
    "supplier_or_affiliation_type", "employment", "product_or_service",
    "ev_battery_relevant", "classification_method", "city", "county",
)

SCHEMA_SQL = """
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
"""

CHILD_SPEC = {
    "certifications": ("standard_family", "certifications"),
    "processes": ("process", "processes"),
    "services": ("service", "services"),
}

# Never permitted in the queryable schema.
FORBIDDEN_COLUMNS = frozenset({
    "certification_count", "split", "split_group",
    "latitude", "longitude", "lat", "lon", "geo",
    "graph_id", "graph_edges", "edge_type",
})
FORBIDDEN_TABLES = frozenset({
    "graph_edges", "edges", "oem_edges", "oem_relationships", "relationships",
    "coordinates", "geo", "geometry", "spatial_ref_sys",
})


class Gate(Exception):
    """A Phase 5 invariant failed. No final artifact is written."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_terms(value: str, field: str) -> list[str]:
    """Split an already-canonical Phase 2 value into its terms.

    Verbatim only: no re-sorting, renaming, stemming, synonym mapping, merging,
    reclassification or fuzzy matching. The certification sentinel is zero
    credential evidence and yields NO terms.
    """
    if value is None:
        return []
    if field == "certifications" and value == CERT_SENTINEL:
        return []
    if value == "":
        return []
    return [t for t in value.split(TERM_SEP) if t]


def build_database(db_path: Path, records, scope_ids: dict[str, list[int]]) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA_SQL)

        # Deterministic insertion: parents by row_id, child terms in canonical order.
        for rec in sorted(records, key=lambda r: r.row_id):
            con.execute(
                f"INSERT INTO companies ({', '.join(COMPANIES_COLUMNS)}) "
                f"VALUES ({', '.join('?' * len(COMPANIES_COLUMNS))})",
                tuple(getattr(rec, c) for c in COMPANIES_COLUMNS),
            )
        for table, (term_col, field) in sorted(CHILD_SPEC.items()):
            for rec in sorted(records, key=lambda r: r.row_id):
                for term in canonical_terms(getattr(rec, field), field):
                    con.execute(
                        f"INSERT INTO {table} (row_id, company, {term_col}) VALUES (?, ?, ?)",
                        (rec.row_id, rec.company, term),
                    )

        # Scoped view sets. The companies view carries the ONLY scope filter for
        # its scope; each child view inherits membership by joining it on row_id,
        # so scope logic is never duplicated and cannot drift between tables.
        for scope in kb.KB_SCOPES:
            ids = ",".join(str(i) for i in sorted(scope_ids[scope]))
            con.execute(
                f"CREATE VIEW {scope}_companies AS "
                f"SELECT * FROM companies WHERE row_id IN ({ids})")
            for table, (term_col, _) in sorted(CHILD_SPEC.items()):
                con.execute(
                    f"CREATE VIEW {scope}_{table} AS "
                    f"SELECT c.row_id, c.company, c.{term_col} FROM {table} c "
                    f"JOIN {scope}_companies p ON c.row_id = p.row_id")
        con.commit()
    finally:
        con.close()


def _q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def validate(db_path: Path, records, canon, scope_ids) -> tuple[list, dict]:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        canon_by_id = {r["row_id"]: r for r in canon}
        rec_by_id = {r.row_id: r for r in records}

        # ---- Structure ---------------------------------------------------
        tables = sorted(r[0] for r in _q(
            con, "SELECT name FROM sqlite_master WHERE type='table' "
                 "AND name NOT LIKE 'sqlite_%'"))
        check("exactly_four_base_tables",
              tables == ["certifications", "companies", "processes", "services"],
              f"{tables}")
        check("no_forbidden_tables", not (set(tables) & FORBIDDEN_TABLES),
              f"none of {sorted(FORBIDDEN_TABLES)} present")

        cols = {t: [r[1] for r in _q(con, f"PRAGMA table_info({t})")] for t in tables}
        bad_cols = {t: sorted(set(c) & FORBIDDEN_COLUMNS) for t, c in cols.items()
                    if set(c) & FORBIDDEN_COLUMNS}
        check("no_forbidden_columns_anywhere", not bad_cols,
              f"certification_count/split/split_group/lat/long/graph absent"
              if not bad_cols else f"{bad_cols}")
        check("companies_columns_match_frozen_schema",
              tuple(cols["companies"]) == COMPANIES_COLUMNS,
              f"{len(cols['companies'])} columns")
        # Cross-check against the Phase 4 allowlist without deriving from it.
        expected_from_allowlist = tuple(
            f for f in kb.MODEL_FACING_FIELDS
            if f not in ("processes", "services", "certifications"))
        check("schema_crosschecks_phase4_allowlist",
              tuple(COMPANIES_COLUMNS) == expected_from_allowlist,
              "companies == MODEL_FACING_FIELDS minus the 3 multi-valued fields")

        # ---- Row identity -------------------------------------------------
        n_companies = _q(con, "SELECT COUNT(*) FROM companies")[0][0]
        check("companies_row_count_205", n_companies == 205, f"{n_companies} == 205")
        n_distinct_ids = _q(con, "SELECT COUNT(DISTINCT row_id) FROM companies")[0][0]
        check("row_id_unique", n_distinct_ids == 205, f"{n_distinct_ids} distinct row_id")
        n_distinct_co = _q(con, "SELECT COUNT(DISTINCT company) FROM companies")[0][0]
        check("records_not_collapsed_to_companies",
              n_companies == 205 and n_distinct_co == 193,
              f"{n_companies} rows preserved across {n_distinct_co} distinct company names")

        drift = [(r[0], c) for r in _q(con, "SELECT row_id FROM companies")
                 for c in COMPANIES_COLUMNS
                 if _q(con, f"SELECT {c} FROM companies WHERE row_id=?", (r[0],))[0][0]
                 != (getattr(rec_by_id[r[0]], c))]
        check("companies_values_match_phase4_contract", not drift,
              f"{len(drift)} drifted cell(s) across 205 rows x "
              f"{len(COMPANIES_COLUMNS)} columns")

        avs = _q(con, "SELECT address FROM companies WHERE row_id=16")[0][0]
        check("avs_row16_trailing_space_preserved",
              avs == canon_by_id[16]["address"] and avs.endswith(" "), repr(avs))

        geo_bad = [r[0] for r in _q(con, "SELECT row_id, city, county FROM companies")
                   if (r[1], r[2]) != (rec_by_id[r[0]].city, rec_by_id[r[0]].county)]
        check("city_county_match_phase4_derivation", not geo_bad,
              f"{len(geo_bad)} mismatch(es); geography not re-parsed")

        # ---- Child tables --------------------------------------------------
        counts, vocab, covered_rows, covered_co = {}, {}, {}, {}
        for table, (term_col, field) in sorted(CHILD_SPEC.items()):
            counts[table] = _q(con, f"SELECT COUNT(*) FROM {table}")[0][0]
            vocab[table] = _q(con, f"SELECT COUNT(DISTINCT {term_col}) FROM {table}")[0][0]
            covered_rows[table] = _q(con, f"SELECT COUNT(DISTINCT row_id) FROM {table}")[0][0]
            covered_co[table] = _q(con, f"SELECT COUNT(DISTINCT company) FROM {table}")[0][0]

            expected_rows = sum(len(canonical_terms(getattr(r, field), field))
                                for r in records)
            expected_vocab = len({t for r in records
                                  for t in canonical_terms(getattr(r, field), field)})
            check(f"{table}_row_count_matches_canonical",
                  counts[table] == expected_rows,
                  f"{counts[table]} == {expected_rows} derived from canonical")
            check(f"{table}_vocabulary_matches_canonical",
                  vocab[table] == expected_vocab,
                  f"{vocab[table]} == {expected_vocab} distinct terms")

            orphans = _q(con, f"SELECT COUNT(*) FROM {table} c "
                              f"LEFT JOIN companies p ON c.row_id=p.row_id "
                              f"WHERE p.row_id IS NULL")[0][0]
            check(f"{table}_zero_orphans", orphans == 0, f"{orphans} orphan row(s)")

            mismatch = _q(con, f"SELECT COUNT(*) FROM {table} c "
                               f"JOIN companies p ON c.row_id=p.row_id "
                               f"WHERE c.company <> p.company")[0][0]
            check(f"{table}_child_parent_company_match", mismatch == 0,
                  f"{mismatch} child/parent company mismatch(es)")

            # An unknown row_id is an orphan (flagged by its own check); treat it
            # as non-verbatim rather than raising, so a corrupt database produces
            # a clean gate failure instead of a stack trace.
            verbatim = [(r[0], r[1]) for r in _q(con, f"SELECT row_id, {term_col} FROM {table}")
                        if r[0] not in rec_by_id
                        or r[1] not in canonical_terms(
                            getattr(rec_by_id[r[0]], field), field)]
            check(f"{table}_terms_verbatim_from_canonical", not verbatim,
                  f"{len(verbatim)} term(s) not present verbatim in their canonical value")

        # ---- Certification sentinel ---------------------------------------
        sentinel_ids = [r.row_id for r in records if r.certifications == CERT_SENTINEL]
        sentinel_rows = _q(con,
                           "SELECT COUNT(*) FROM certifications WHERE row_id IN "
                           f"({','.join('?' * len(sentinel_ids))})", sentinel_ids)[0][0]
        check("sentinel_yields_zero_certification_rows",
              sentinel_rows == 0 and len(sentinel_ids) == 34,
              f"{len(sentinel_ids)} sentinel row(s) -> {sentinel_rows} child rows")
        lit = _q(con, "SELECT COUNT(*) FROM certifications WHERE standard_family=?",
                 (CERT_SENTINEL,))[0][0]
        check("sentinel_never_stored_as_a_credential", lit == 0,
              f"{lit} row(s) storing the sentinel as a standard_family")

        # ---- Round trip -----------------------------------------------------
        # Reconstruct under the frozen Phase 2 term-order rule (case-insensitive
        # sort), never relying on SQLite's natural row order.
        rt_bad = []
        for table, (term_col, field) in sorted(CHILD_SPEC.items()):
            for rid in sorted(canon_by_id):
                got = [r[0] for r in _q(
                    con, f"SELECT {term_col} FROM {table} WHERE row_id=?", (rid,))]
                rebuilt = TERM_SEP.join(sorted(got, key=str.casefold))
                expected = canon_by_id[rid][field]
                if field == "certifications" and not got:
                    rebuilt = CERT_SENTINEL
                if rebuilt != expected:
                    rt_bad.append((rid, field, rebuilt[:40], expected[:40]))
        check("round_trip_reconstructs_canonical_exactly", not rt_bad,
              f"{len(rt_bad)} mismatch(es) across 205 rows x 3 fields")

        amb = 0
        for r in records:
            for field in ("processes", "services", "certifications"):
                ts = canonical_terms(getattr(r, field), field)
                folded = Counter(t.casefold() for t in ts)
                amb += sum(1 for k, n in folded.items() if n > 1
                           or len({t for t in ts if t.casefold() == k}) > 1)
        check("case_insensitive_ordering_ambiguities_zero", amb == 0,
              f"case-insensitive ordering ambiguities = {amb}")

        # ---- Scoped views ---------------------------------------------------
        views = sorted(r[0] for r in _q(
            con, "SELECT name FROM sqlite_master WHERE type='view'"))
        check("twelve_scoped_views_present", len(views) == 12,
              f"{len(views)} views: 3 scopes x 4 tables")

        scope_counts = {}
        for scope in kb.KB_SCOPES:
            n = _q(con, f"SELECT COUNT(*) FROM {scope}_companies")[0][0]
            scope_counts[scope] = n
            check(f"view_{scope}_companies_row_count",
                  n == kb.EXPECTED_SCOPE_ROWS[scope],
                  f"{n} == {kb.EXPECTED_SCOPE_ROWS[scope]}")
            vids = {r[0] for r in _q(con, f"SELECT row_id FROM {scope}_companies")}
            check(f"view_{scope}_membership_equals_frozen_split",
                  vids == set(scope_ids[scope]),
                  f"{len(vids)} row_ids identical to the frozen split")
            for table, (term_col, _) in sorted(CHILD_SPEC.items()):
                cids = {r[0] for r in _q(con, f"SELECT DISTINCT row_id FROM {scope}_{table}")}
                check(f"view_{scope}_{table}_inherits_parent_scope",
                      cids <= vids,
                      f"{len(cids)} parent row_ids, all inside {scope}_companies")

        train_ids = set(scope_ids["train_kb"])
        dev_ids = set(scope_ids["train_dev_kb"]) - train_ids
        test_ids = set(scope_ids["full_kb"]) - set(scope_ids["train_dev_kb"])
        check("train_kb_view_excludes_all_dev_and_test",
              not (train_ids & (dev_ids | test_ids)),
              f"0 of {len(dev_ids)} dev and {len(test_ids)} test rows visible in train_kb")
        for table, _ in sorted(CHILD_SPEC.items()):
            leaked = _q(con, f"SELECT COUNT(*) FROM train_kb_{table} WHERE row_id IN "
                             f"({','.join(str(i) for i in sorted(dev_ids | test_ids))})")[0][0]
            check(f"train_kb_{table}_leaks_no_dev_or_test_child_rows", leaked == 0,
                  f"{leaked} leaked child row(s)")

        view_cols = set()
        for v in views:
            view_cols.update(r[1] for r in _q(con, f"PRAGMA table_info({v})"))
        check("no_view_exposes_forbidden_column",
              not (view_cols & FORBIDDEN_COLUMNS),
              f"{len(view_cols)} distinct view columns, none forbidden")

        # ---- SQLite integrity ------------------------------------------------
        ic = _q(con, "PRAGMA integrity_check")[0][0]
        check("pragma_integrity_check", ic == "ok", ic)
        fk = _q(con, "PRAGMA foreign_key_check")
        check("pragma_foreign_key_check", not fk, f"{len(fk)} violation(s)")
        fk_on = _q(con, "PRAGMA foreign_keys")[0][0]
        check("foreign_keys_enforced_on_connection", fk_on == 1, f"PRAGMA foreign_keys={fk_on}")
        idx = sorted(r[0] for r in _q(
            con, "SELECT name FROM sqlite_master WHERE type='index' "
                 "AND name NOT LIKE 'sqlite_%'"))
        check("no_unauthorized_indexes", not idx,
              "none created (README authorizes none)" if not idx else f"{idx}")
    finally:
        con.close()

    stats = {"tables": tables, "cols": cols, "views": views, "counts": counts,
             "vocab": vocab, "covered_rows": covered_rows, "covered_co": covered_co,
             "scope_counts": scope_counts, "n_companies": n_companies,
             "n_distinct_co": n_distinct_co, "sentinel_ids": len(sentinel_ids),
             "ambiguities": amb, "indexes": idx}
    return checks, stats


def main() -> int:
    # ---- Frozen input verification before anything is written --------------
    hashes = kb.frozen_input_hashes()      # raises IntegrityError on drift
    for name, expected in (("canonical_records_v3.jsonl", kb.EXPECTED_CANONICAL_SHA),
                           ("company_split_groups_v3.csv", kb.EXPECTED_SPLIT_SHA)):
        if hashes[name] != expected:
            raise Gate(f"{name} drifted: {hashes[name]}")

    records = kb.load_kb("full_kb")        # the approved Phase 4 contract
    scope_ids = {s: sorted(r.row_id for r in kb.load_kb(s)) for s in kb.KB_SCOPES}
    canon = [json.loads(l) for l in CANONICAL.read_text(encoding="utf-8").splitlines()]

    no_fallback = _grep_gnem_sqlite_fallback()

    # Build to a temporary path; only a fully passing build is moved into place.
    with tempfile.TemporaryDirectory() as td:
        tmp_db = Path(td) / "gnem_v3.sqlite"
        build_database(tmp_db, records, scope_ids)
        checks, stats = validate(tmp_db, records, canon, scope_ids)
        checks.append(("no_gnem_sqlite_fallback_anywhere", not no_fallback,
                       f"{len(no_fallback)} reference(s) to the v2 {V2_DB_NEEDLE}"))

        # Determinism: rebuild and compare.
        tmp_db2 = Path(td) / "rebuild.sqlite"
        build_database(tmp_db2, records, scope_ids)
        byte_identical = sha256_file(tmp_db) == sha256_file(tmp_db2)
        logical_identical = _logical_equal(tmp_db, tmp_db2)
        checks.append(("rebuild_logically_identical", logical_identical,
                       "table-by-table contents identical across a clean rebuild"))

        for name, ok, detail in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        failed = [n for n, ok, _ in checks if not ok]
        if failed:
            raise Gate(f"{len(failed)} gate(s) failed: {failed}")

        OUT_DB.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp_db, OUT_DB)

    db_sha = sha256_file(OUT_DB)
    _write_audit(hashes, db_sha, stats, checks, byte_identical, scope_ids)
    print(f"\nAll Phase 5 gates passed.")
    print(f"  {OUT_DB.relative_to(ROOT)}  sha256 {db_sha}")
    print(f"  companies {stats['n_companies']} rows / {stats['n_distinct_co']} distinct names")
    for t in sorted(CHILD_SPEC):
        print(f"  {t:15} {stats['counts'][t]:4d} rows  {stats['vocab'][t]:3d} terms  "
              f"{stats['covered_rows'][t]:3d} rows covered")
    print(f"  scoped views: {len(stats['views'])}  "
          f"({', '.join(f'{s}={stats['scope_counts'][s]}' for s in kb.KB_SCOPES)})")
    print(f"  byte-identical rebuild: {byte_identical}")
    return 0


def _grep_gnem_sqlite_fallback() -> list[str]:
    hits = []
    for p in sorted(ROOT.rglob("*.py")):
        if ".git" in p.parts:
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if V2_DB_NEEDLE in line:
                hits.append(f"{p.relative_to(ROOT)}:{n}")
    return hits


def _logical_equal(a: Path, b: Path) -> bool:
    ca, cb = sqlite3.connect(a), sqlite3.connect(b)
    try:
        for t in ("companies", "certifications", "processes", "services"):
            qa = ca.execute(f"SELECT * FROM {t} ORDER BY 1,2,3").fetchall()
            qb = cb.execute(f"SELECT * FROM {t} ORDER BY 1,2,3").fetchall()
            if qa != qb:
                return False
        sa = ca.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
        sb = cb.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
        return sa == sb
    finally:
        ca.close(); cb.close()


def _write_audit(hashes, db_sha, stats, checks, byte_identical, scope_ids) -> None:
    L = ["# DB_VALIDATION_v3\n",
         "Phase 5 — `gnem_v3.sqlite`. Child tables make multi-valued membership a clean "
         "equality join; the database is **scoped, not singular**.\n",
         "## Provenance\n", "```text",
         f"canonical_records_v3.jsonl   {hashes['canonical_records_v3.jsonl']}",
         f"company_split_groups_v3.csv  {hashes['company_split_groups_v3.csv']}",
         f"finetune/kb_v3.py            {hashes['kb_v3.py']}",
         f"builder                      {BUILDER_VERSION}",
         f"finetune/phase5_build_sqlite.py  {sha256_file(Path(__file__).resolve())}",
         f"datasets_v3/gnem_v3.sqlite   {db_sha}",
         "```\n",
         "Built through the approved Phase 4 contract `kb_v3.load_kb(\"full_kb\")`. There is "
         "no second cleaning path and geography is not re-parsed — `city`/`county` are taken "
         "from the Phase 4 derivation and compared cell-by-cell.\n",
         "## Schema\n", "```sql", SCHEMA_SQL.strip(), "```\n",
         "`certification_count` is **not a column anywhere**: a model that can `COUNT` the "
         "child table must not be handed the answer. `split`, `split_group`, latitude, "
         "longitude and graph metadata are equally absent — leakage-control metadata never "
         "becomes queryable data.\n",
         f"Indexes created: **{len(stats['indexes'])}** "
         f"({'none — README authorizes none' if not stats['indexes'] else stats['indexes']}).\n",
         "## Table and child-row counts\n",
         "All counts are derived from the canonical records, never hard-coded.\n",
         "| table | rows | distinct terms | rows covered | companies covered |",
         "|---|---|---|---|---|",
         f"| `companies` | {stats['n_companies']} | — | 205 | "
         f"{stats['n_distinct_co']} distinct names |"]
    for t in sorted(CHILD_SPEC):
        L.append(f"| `{t}` | {stats['counts'][t]} | {stats['vocab'][t]} | "
                 f"{stats['covered_rows'][t]} | {stats['covered_co'][t]} |")
    L += ["",
          "All **205 row-level records are preserved**; the database is not collapsed to the "
          f"{stats['n_distinct_co']} unique company names. `row_id` is the parent identity for "
          "every child relationship, so the repeated-company rows stay distinct records and "
          "each child fact attaches to the row that stated it.\n",
          f"The **{stats['sentinel_ids']} rows carrying `{CERT_SENTINEL}` produce zero "
          "certification child rows** — the sentinel is zero credential evidence, not a "
          "credential, and it is never stored as a `standard_family`.\n",
          "## Integrity and round trip\n", "```text",
          "PRAGMA integrity_check     ok",
          "PRAGMA foreign_key_check   0 violations",
          "PRAGMA foreign_keys        ON",
          "orphan child rows          0 (all three child tables)",
          "child/parent company mismatches  0 (all three child tables)",
          f"case-insensitive ordering ambiguities = {stats['ambiguities']}",
          "```\n",
          "**Round trip.** Each row's `processes`, `services` and `certifications` are "
          "reconstructed from the child tables under the frozen Phase 2 term-order rule "
          "(case-insensitive sort) — never relying on SQLite's natural row order — and "
          "compared against the frozen canonical records. All 205 rows × 3 fields reconstruct "
          "exactly. Rows with no certification child rows reconstruct to "
          f"`{CERT_SENTINEL}`, the zero-evidence state, not to a literal credential.\n",
          "Because there are **zero** case-insensitive ordering ambiguities, the sort-based "
          "reconstruction is unique; no ordinal column or new normalization rule was needed "
          "or invented.\n",
          "## Scoped views — the anti-leakage mechanism\n",
          f"{len(stats['views'])} views: three scopes × four tables. The `{{scope}}_companies` "
          "view carries the **only** scope filter for its scope; each child view inherits "
          "membership by joining that view on `row_id`, so scope logic is defined once per "
          "scope and cannot drift between tables.\n",
          "| scope | companies visible | child views |", "|---|---|---|"]
    for s in kb.KB_SCOPES:
        L.append(f"| `{s}` | {stats['scope_counts'][s]} | `{s}_certifications`, "
                 f"`{s}_processes`, `{s}_services` |")
    L += ["",
          "`train_kb` provably excludes every dev and test row, and its child views leak zero "
          "dev/test child rows. No view exposes a forbidden column.\n",
          "**Phase 5 exposes no query API.** `run_sql`, scope-neutral name resolution and the "
          "refusal-without-scope executor belong to **Phase 7**, so the base tables cannot "
          "become a de facto unscoped access path here. Model-facing schema prompts stay "
          "scope-neutral: the scoped view names above are executor infrastructure and are "
          "never taught to a model.\n",
          f"No fallback to a v2 `{V2_DB_NEEDLE}` exists anywhere in the repository.\n",
          "## Determinism\n",
          f"A clean rebuild is **logically identical** table-by-table and in `sqlite_master`. "
          f"Byte-identical SQLite file across rebuilds: **{byte_identical}**"
          + ("." if byte_identical else
             " — so the reproducibility claim is made at the logical/table level, not as an "
             "unsupported byte-determinism claim.") + "\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        L.append(f"| `{name}` | {'PASS' if ok else 'FAIL'} | {detail} |")
    L.append("")
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, kb.IntegrityError) as exc:
        print(f"\nPHASE 5 GATE FAILURE: {exc}", file=sys.stderr)
        print("No final artifact written. No rule weakened.", file=sys.stderr)
        raise SystemExit(1)
