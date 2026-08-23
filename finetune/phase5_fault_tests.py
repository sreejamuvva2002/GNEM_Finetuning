"""Phase 5 fault-injection suite.

A gate that only passes on good input proves little. Each fault below corrupts a
freshly built database in a temporary directory and asserts that the Phase 5
validation catches it. The committed artifacts are never touched.

Faults covered (as required by the Phase 5 gate):
    frozen hash drift
    orphan child row
    certification sentinel emitted as a credential
    wrong scoped-view membership
    forbidden schema field (certification_count / split_group)
    child/parent company mismatch
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as kb          # noqa: E402
import phase5_build_sqlite as p5  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _fresh(td: Path, records, scope_ids):
    db = td / f"f{len(list(td.iterdir()))}.sqlite"
    p5.build_database(db, records, scope_ids)
    return db


def _failing(db, records, canon, scope_ids) -> set[str]:
    checks, _ = p5.validate(db, records, canon, scope_ids)
    return {n for n, ok, _ in checks if not ok}


def main() -> int:
    records = kb.load_kb("full_kb")
    scope_ids = {s: sorted(r.row_id for r in kb.load_kb(s)) for s in kb.KB_SCOPES}
    canon = [json.loads(l) for l in
             (ROOT / "datasets_v3" / "canonical_records_v3.jsonl")
             .read_text(encoding="utf-8").splitlines()]

    results: list[tuple[str, bool, str]] = []

    def record(name, caught_by, detail):
        results.append((name, bool(caught_by), detail))

    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)

        # 1. Frozen hash drift -- must refuse before building anything.
        orig = kb.EXPECTED_CANONICAL_SHA
        try:
            kb.EXPECTED_CANONICAL_SHA = "deadbeef" * 8
            kb.load_kb("full_kb")
            record("frozen_hash_drift", False, "*** NOT CAUGHT ***")
        except kb.IntegrityError as e:
            record("frozen_hash_drift", True, f"IntegrityError: {str(e).splitlines()[0][:60]}")
        finally:
            kb.EXPECTED_CANONICAL_SHA = orig

        # 2. Orphan child row.
        db = _fresh(td, records, scope_ids)
        con = sqlite3.connect(db)
        con.execute("INSERT INTO processes (row_id, company, process) VALUES (9999,'Ghost','Welding')")
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("orphan_child_row", "processes_zero_orphans" in f,
               f"caught by {sorted(x for x in f if 'orphan' in x or 'processes' in x)[:3]}")

        # 3. Certification sentinel emitted as a credential.
        db = _fresh(td, records, scope_ids)
        sid = next(r.row_id for r in records if r.certifications == p5.CERT_SENTINEL)
        comp = next(r.company for r in records if r.row_id == sid)
        con = sqlite3.connect(db)
        con.execute("INSERT INTO certifications (row_id, company, standard_family) VALUES (?,?,?)",
                    (sid, comp, p5.CERT_SENTINEL))
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("sentinel_emitted_as_certification",
               "sentinel_yields_zero_certification_rows" in f
               and "sentinel_never_stored_as_a_credential" in f,
               f"caught by {sorted(x for x in f if 'sentinel' in x)}")

        # 4. Wrong scoped-view membership -- train_kb widened to include a test row.
        db = _fresh(td, records, scope_ids)
        test_id = sorted(set(scope_ids["full_kb"]) - set(scope_ids["train_dev_kb"]))[0]
        con = sqlite3.connect(db)
        con.execute("DROP VIEW train_kb_companies")
        ids = ",".join(str(i) for i in sorted(scope_ids["train_kb"] + [test_id]))
        con.execute(f"CREATE VIEW train_kb_companies AS SELECT * FROM companies "
                    f"WHERE row_id IN ({ids})")
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("wrong_scoped_view_membership",
               "view_train_kb_companies_row_count" in f
               or "view_train_kb_membership_equals_frozen_split" in f,
               f"caught by {sorted(x for x in f if 'train_kb' in x)[:3]}")

        # 5. Forbidden schema field.
        db = _fresh(td, records, scope_ids)
        con = sqlite3.connect(db)
        con.execute("ALTER TABLE companies ADD COLUMN certification_count INTEGER")
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("forbidden_schema_field_certification_count",
               "no_forbidden_columns_anywhere" in f,
               f"caught by {sorted(x for x in f if 'forbidden' in x or 'schema' in x)[:3]}")

        db = _fresh(td, records, scope_ids)
        con = sqlite3.connect(db)
        con.execute("ALTER TABLE companies ADD COLUMN split_group TEXT")
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("forbidden_schema_field_split_group",
               "no_forbidden_columns_anywhere" in f,
               f"caught by {sorted(x for x in f if 'forbidden' in x)[:3]}")

        # 6. Child/parent company mismatch.
        db = _fresh(td, records, scope_ids)
        con = sqlite3.connect(db)
        con.execute("UPDATE processes SET company='WRONG NAME' WHERE rowid=1")
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("child_parent_company_mismatch",
               "processes_child_parent_company_match" in f,
               f"caught by {sorted(x for x in f if 'company_match' in x)}")

        # 7. Round-trip corruption -- a term silently altered.
        db = _fresh(td, records, scope_ids)
        con = sqlite3.connect(db)
        con.execute("UPDATE services SET service='Renamed Service' WHERE rowid=1")
        con.commit(); con.close()
        f = _failing(db, records, canon, scope_ids)
        record("altered_term_breaks_round_trip",
               "round_trip_reconstructs_canonical_exactly" in f,
               f"caught by {sorted(x for x in f if 'round_trip' in x or 'verbatim' in x)[:2]}")

    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] fault:{name}: {detail}")
    missed = [n for n, ok, _ in results if not ok]
    if missed:
        print(f"\nFAULT SUITE FAILED — {len(missed)} fault(s) not caught: {missed}",
              file=sys.stderr)
        return 1
    print(f"\nAll {len(results)} faults correctly caught.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
