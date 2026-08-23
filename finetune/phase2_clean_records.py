"""Phase 2 -- clean, normalize, and freeze the canonical records.

Reads the frozen source workbook (whose hash is re-verified against the Phase 1
manifest before anything is produced) and emits the canonical v3 representation
plus its manifest, a cell-level audit, and a normalization report.

Only the normalization frozen in README.md Phase 2 is applied:

  Category              OEM Footprint -> OEM (Footprint)
  Primary Facility Type Manufacturing plant         -> Manufacturing Plant
                        Engineering / Manufacturing -> Manufacturing / Engineering
                        Manufacturing stays a distinct value
  Processes/Services/Certifications
                        split ';' -> trim -> drop empties -> dedupe (exact,
                        case-insensitive) -> case-insensitive sort -> rejoin
  Sentinels             Not specified / Not applicable / None identified after search

Ordering rule (README.md Phase 2, "Order matters"): `Certification Count` is
validated against the PRE-SENTINEL certification parse, and only afterwards is
the certification sentinel inserted.

Amendment A-001 governs geography: a real Location (Georgia or non-Georgia) is
preserved; a missing Location becomes `Not specified`; a structurally
inapplicable Location becomes `Not applicable`. `Address` is never substituted
for `Location`. Phase 2 does NOT materialize city/county -- that derivation
belongs to the Phase 4 loader.

Explicitly NOT done here (later phases): split_group, splits, collision map,
OEM-reference guard, holdouts, multi-row conflict resolution, SQLite, child
tables, datasets, probes, Q42, training.

Any failed invariant is a Phase 2 GATE FAILURE: the script exits non-zero and
writes no artifact, rather than adjusting an expectation or patching the source.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "kb" / "GNEM_Final_Combined_Dataset.xlsx"
SHEET = "GNEM Combined"
SOURCE_MANIFEST = ROOT / "datasets_v3" / "SOURCE_MANIFEST_v3.json"

OUT_RECORDS = ROOT / "datasets_v3" / "canonical_records_v3.jsonl"
OUT_MANIFEST = ROOT / "datasets_v3" / "CLEANED_DATA_MANIFEST_v3.json"
OUT_AUDIT = ROOT / "validation_v3" / "CLEANING_AUDIT_v3.csv"
OUT_REPORT = ROOT / "validation_v3" / "NORMALIZATION_REPORT_v3.md"

# Sentinels -- frozen meanings (CLAUDE.md 15). None proves a real-world negative.
NOT_SPECIFIED = "Not specified"          # source value unknown / unprovided
NOT_APPLICABLE = "Not applicable"        # field structurally does not apply
NONE_IDENTIFIED = "None identified after search"  # no credential evidence found

# Frozen expectations from README.md Phase 2. Never edited to match an observation.
EXPECTED = {
    "row_count": 205,
    "category": {"OEM Footprint": 0, "OEM (Footprint)": 8},
    "facility": {
        "Manufacturing plant": 0,
        "Manufacturing Plant": 187,
        "Manufacturing": 4,
        "Engineering / Manufacturing": 0,
    },
}

CATEGORY_MAP = {"OEM Footprint": "OEM (Footprint)"}
FACILITY_MAP = {
    "Manufacturing plant": "Manufacturing Plant",
    "Engineering / Manufacturing": "Manufacturing / Engineering",
}

# Source column -> canonical snake_case field. Order defines the JSONL field order.
COLUMN_TO_FIELD = [
    ("Record No.", "row_id"),
    ("Company", "company"),
    ("Category", "category"),
    ("Industry Group", "industry_group"),
    ("Location", "location"),
    ("Address", "address"),
    ("Primary Facility Type", "primary_facility_type"),
    ("EV Supply Chain Role", "ev_supply_chain_role"),
    ("Primary OEMs", "primary_oems"),
    ("Supplier or Affiliation Type", "supplier_or_affiliation_type"),
    ("Employment", "employment"),
    ("Product / Service", "product_or_service"),
    ("Processes", "processes"),
    ("Services", "services"),
    ("EV / Battery Relevant", "ev_battery_relevant"),
    ("Classification Method", "classification_method"),
    ("Certifications", "certifications"),
    ("Certification Count", "certification_count"),
]
MULTIVALUE_FIELDS = ("processes", "services", "certifications")

# Rows named by the frozen protocol / Amendment A-001.
VALEO_ROW = 187
VOLVO_ROWS = (192, 193)


def sha256_file(path: Path) -> str:
    """Chunked file digest. Ported from v2 finetune/validate/manifest.py."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def is_blank(v) -> bool:
    return v is None or str(v).strip() == ""


def parse_terms(raw) -> list[str]:
    """Split ';' -> trim -> drop empties -> dedupe (case-insensitive, first
    spelling wins) -> case-insensitive sort. Term spelling is preserved; no
    taxonomy normalization of any kind is applied."""
    if is_blank(raw):
        return []
    seen, out = set(), []
    for term in str(raw).split(";"):
        term = term.strip()
        if not term:
            continue
        if term.casefold() in seen:
            continue
        seen.add(term.casefold())
        out.append(term)
    return sorted(out, key=str.casefold)


class Gate(Exception):
    """A frozen invariant failed. Phase 2 stops; nothing is written."""


def main() -> int:
    audit: list[dict] = []

    def record_change(row_id, company, field, old, new, change_type, reason):
        audit.append({
            "row_id": row_id,
            "company": company,
            "field": field,
            "old_value": "" if old is None else str(old),
            "new_value": "" if new is None else str(new),
            "change_type": change_type,
            "reason": reason,
        })

    # ---- 0. Re-verify the frozen source before producing anything ----------
    if not SOURCE_MANIFEST.is_file():
        raise Gate(f"Phase 1 manifest missing: {SOURCE_MANIFEST}")
    manifest_v1 = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    expected_sha = manifest_v1["source_workbook"]["sha256"]
    actual_sha = sha256_file(WORKBOOK)
    if actual_sha != expected_sha:
        raise Gate(f"source workbook drifted from Phase 1 manifest\n"
                   f"  manifest: {expected_sha}\n  workbook: {actual_sha}")

    # ---- 1. Read the workbook exactly as stored ---------------------------
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    try:
        rows = list(wb[SHEET].iter_rows(values_only=True))
    finally:
        wb.close()
    header, data = rows[0], rows[1:]
    col = {name: i for i, name in enumerate(header)}
    if len(data) != EXPECTED["row_count"]:
        raise Gate(f"expected {EXPECTED['row_count']} source rows, found {len(data)}")

    records = []
    ws_trim_hits = Counter()

    for raw in data:
        row_id = raw[col["Record No."]]
        company_raw = raw[col["Company"]]
        company = str(company_raw).strip()
        if str(company_raw) != company:
            raise Gate(f"row {row_id}: Company has surrounding whitespace; Phase 1 "
                       f"asserted 0 such rows")

        rec: dict = {}
        for src, field in COLUMN_TO_FIELD:
            rec[field] = raw[col[src]]

        rec["row_id"] = int(row_id)
        rec["company"] = company

        # -- Category ------------------------------------------------------
        cat = rec["category"]
        cat_s = str(cat).strip() if not is_blank(cat) else ""
        if cat_s in CATEGORY_MAP:
            new = CATEGORY_MAP[cat_s]
            record_change(row_id, company, "category", cat_s, new,
                          "category_normalization",
                          "README Phase 2: Category 'OEM Footprint' -> 'OEM (Footprint)'")
            cat_s = new
        rec["category"] = cat_s

        # -- Primary Facility Type ----------------------------------------
        fac = rec["primary_facility_type"]
        fac_s = str(fac).strip() if not is_blank(fac) else ""
        if fac_s in FACILITY_MAP:
            new = FACILITY_MAP[fac_s]
            record_change(row_id, company, "primary_facility_type", fac_s, new,
                          "facility_type_normalization",
                          f"README Phase 2: facility type '{fac_s}' -> '{new}'")
            fac_s = new
        rec["primary_facility_type"] = fac_s

        # -- Multi-valued fields (PRE-sentinel) ----------------------------
        pre_sentinel_terms = {}
        for field in MULTIVALUE_FIELDS:
            original = rec[field]
            terms = parse_terms(original)
            pre_sentinel_terms[field] = terms
            canonical = "; ".join(terms)
            original_s = "" if is_blank(original) else str(original).strip()
            if canonical != original_s:
                n_before = len([t.strip() for t in str(original).split(";")
                                if t.strip()]) if not is_blank(original) else 0
                kind = ("multivalue_dedupe_and_order" if n_before != len(terms)
                        else "multivalue_canonical_order")
                record_change(row_id, company, field, original_s, canonical, kind,
                              "README Phase 2: split ';', trim, drop empties, dedupe, "
                              "case-insensitive sort, rejoin (spelling preserved)")
            rec[field] = canonical

        # -- Employment: preserve exactly; never impute --------------------
        emp = rec["employment"]
        if is_blank(emp):
            raise Gate(f"row {row_id}: employment blank; protocol asserts populated "
                       f"on all 205 rows and forbids fillna(0)")
        rec["employment"] = int(emp) if isinstance(emp, int) else emp

        # -- Certification Count: validation-only, kept as stored ----------
        rec["certification_count"] = int(rec["certification_count"])

        # -- Single-value passthrough fields: record trims transparently ---
        for src, field in COLUMN_TO_FIELD:
            if field in ("row_id", "company", "employment", "certification_count",
                         "category", "primary_facility_type") + MULTIVALUE_FIELDS:
                continue
            v = rec[field]
            if is_blank(v):
                rec[field] = None  # sentinel decided below
                continue
            s = str(v).strip()
            if s != str(v):
                ws_trim_hits[field] += 1
                record_change(row_id, company, field, str(v), s,
                              "whitespace_trim", "surrounding whitespace removed")
            rec[field] = s

        rec["_pre_sentinel_terms"] = pre_sentinel_terms
        records.append(rec)

    # ---- 2. ORDER MATTERS: validate Certification Count against the -------
    #         PRE-SENTINEL parse, before any certification sentinel exists.
    cc_mismatches = []
    for rec in records:
        parsed = len(rec["_pre_sentinel_terms"]["certifications"])
        if rec["certification_count"] != parsed:
            cc_mismatches.append((rec["row_id"], rec["company"],
                                  rec["certification_count"], parsed))
    if cc_mismatches:
        raise Gate("Certification Count disagrees with the PRE-SENTINEL parse on "
                   f"{len(cc_mismatches)} row(s): {cc_mismatches[:10]}")
    cert_count_validated = len(records)

    # ---- 3. Only now insert sentinels -------------------------------------
    for rec in records:
        row_id, company = rec["row_id"], rec["company"]

        # Certifications: blank -> no credential evidence found.
        if rec["certifications"] == "":
            record_change(row_id, company, "certifications", "", NONE_IDENTIFIED,
                          "sentinel_none_identified",
                          "blank certification evidence; inserted AFTER Certification "
                          "Count validation (README Phase 2 'Order matters'); still "
                          "represents zero certification terms")
            rec["certifications"] = NONE_IDENTIFIED

        # Location / Address -- Amendment A-001.
        if rec["location"] is None:
            if row_id in VOLVO_ROWS:
                new, why = NOT_APPLICABLE, (
                    "A-001: structurally inapplicable -- a real non-Georgia Address "
                    "exists, so a Georgia Location does not apply; Address preserved "
                    "and never substituted for Location")
            elif row_id == VALEO_ROW:
                new, why = NOT_SPECIFIED, (
                    "A-001: Location missing and Address also missing -- source "
                    "unknown/unprovided, not structurally inapplicable")
            else:
                raise Gate(f"row {row_id}: blank Location not covered by A-001's "
                           f"named cases (Valeo {VALEO_ROW}, Volvo {VOLVO_ROWS})")
            record_change(row_id, company, "location", "", new,
                          "sentinel_location", why)
            rec["location"] = new

        if rec["address"] is None:
            if row_id != VALEO_ROW:
                raise Gate(f"row {row_id}: blank Address not covered by the frozen "
                           f"protocol (only Valeo {VALEO_ROW} is)")
            record_change(row_id, company, "address", "", NOT_SPECIFIED,
                          "sentinel_address",
                          "A-001: Address missing -- source unknown/unprovided")
            rec["address"] = NOT_SPECIFIED

        # Primary OEMs -- frozen category-dependent blank policy.
        if rec["primary_oems"] is None:
            cat = rec["category"]
            if cat in ("OEM", "OEM (Footprint)"):
                new, why = NOT_APPLICABLE, (
                    f"frozen blank policy: category '{cat}' -> Not applicable "
                    "(an OEM has no upstream Primary OEMs)")
            elif cat == "OEM Supply Chain":
                new, why = NOT_SPECIFIED, (
                    "frozen blank policy: category 'OEM Supply Chain' -> Not specified")
            else:
                raise Gate(f"row {row_id}: blank Primary OEMs under category {cat!r}, "
                           f"which the frozen blank policy does not cover")
            record_change(row_id, company, "primary_oems", "", new,
                          "sentinel_primary_oems", why)
            rec["primary_oems"] = new

        # Supplier or Affiliation Type -- all blanks -> Not specified.
        if rec["supplier_or_affiliation_type"] is None:
            record_change(row_id, company, "supplier_or_affiliation_type", "",
                          NOT_SPECIFIED, "sentinel_supplier_affiliation",
                          "frozen rule: blank -> Not specified. Sibling-row frequency "
                          "is NOT source evidence; nothing is imputed")
            rec["supplier_or_affiliation_type"] = NOT_SPECIFIED

        # Any remaining blank in a passthrough field is unhandled -> stop.
        for _, field in COLUMN_TO_FIELD:
            if rec[field] is None:
                raise Gate(f"row {rec['row_id']}: field {field!r} left blank with no "
                           f"frozen sentinel rule")

    # ---- 4. Assertions ----------------------------------------------------
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    check("canonical_row_count", len(records) == 205, f"{len(records)} == 205")
    ids = [r["row_id"] for r in records]
    check("row_id_unique", len(set(ids)) == 205, f"{len(set(ids))} unique == 205")
    src_ids = [int(r[col["Record No."]]) for r in data]
    check("no_rows_dropped", sorted(ids) == sorted(src_ids), "row_id set == source set")

    cats = Counter(r["category"] for r in records)
    for value, expected in EXPECTED["category"].items():
        check(f"category::{value}", cats.get(value, 0) == expected,
              f"{cats.get(value, 0)} == {expected}")
    facs = Counter(r["primary_facility_type"] for r in records)
    for value, expected in EXPECTED["facility"].items():
        check(f"facility::{value}", facs.get(value, 0) == expected,
              f"{facs.get(value, 0)} == {expected}")

    for field in MULTIVALUE_FIELDS:
        bad = []
        for r in records:
            v = r[field]
            if field == "certifications" and v == NONE_IDENTIFIED:
                continue
            if "; ".join(parse_terms(v)) != v:
                bad.append(r["row_id"])
        check(f"{field}_canonically_ordered", not bad, f"{len(bad)} non-canonical")

    check("certification_count_matches_pre_sentinel_parse",
          cert_count_validated == 205 and not cc_mismatches,
          f"validated on {cert_count_validated}/205 rows, 0 mismatches")

    sentinel_zero_terms = [
        r["row_id"] for r in records
        if r["certifications"] == NONE_IDENTIFIED and r["certification_count"] != 0
    ]
    check("cert_sentinel_means_zero_terms", not sentinel_zero_terms,
          f"{len(sentinel_zero_terms)} sentinel rows with nonzero count")

    emp_ok = sum(1 for r in records if isinstance(r["employment"], int))
    check("employment_populated", emp_ok == 205, f"{emp_ok}/205 populated")
    src_emp = [int(r[col["Employment"]]) for r in data]
    check("employment_values_preserved",
          [r["employment"] for r in records] == src_emp, "byte-equal to source")
    check("employment_no_zero_imputation",
          sum(1 for r in records if r["employment"] == 0) == 0, "0 zero values")

    valeo = next(r for r in records if r["row_id"] == VALEO_ROW)
    check("valeo_location_not_specified", valeo["location"] == NOT_SPECIFIED,
          repr(valeo["location"]))
    check("valeo_address_not_specified", valeo["address"] == NOT_SPECIFIED,
          repr(valeo["address"]))
    for rid, frag in ((192, "Mahwah, NJ"), (193, "Greensboro, NC")):
        v = next(r for r in records if r["row_id"] == rid)
        check(f"volvo_{rid}_location_not_applicable",
              v["location"] == NOT_APPLICABLE, repr(v["location"]))
        check(f"volvo_{rid}_address_preserved", frag in v["address"], repr(v["address"]))

    src_blank_supplier = sum(1 for r in data
                             if is_blank(r[col["Supplier or Affiliation Type"]]))
    filled = sum(1 for a in audit if a["change_type"] == "sentinel_supplier_affiliation")
    check("supplier_blanks_all_not_specified", filled == src_blank_supplier,
          f"{filled}/{src_blank_supplier} blanks -> Not specified")
    check("no_supplier_imputation",
          all(a["new_value"] == NOT_SPECIFIED for a in audit
              if a["change_type"] == "sentinel_supplier_affiliation"),
          "no blank filled with a sibling-row value")

    forbidden = {"city", "county", "latitude", "longitude", "split_group"}
    present = forbidden.intersection(*(set(r) for r in records)) if records else set()
    check("no_city_county_materialized", not present, f"absent: {sorted(forbidden)}")

    src_companies = [str(r[col["Company"]]).strip() for r in data]
    check("no_unauthorized_company_normalization",
          [r["company"] for r in records] == src_companies,
          "company == exact trimmed source value")

    failed = [(n, d) for n, ok, d in checks if not ok]
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    if failed:
        raise Gate(f"{len(failed)} invariant(s) failed: {[n for n, _ in failed]}")

    # ---- 5. Write artifacts ----------------------------------------------
    for rec in records:
        rec.pop("_pre_sentinel_terms", None)
    field_order = [f for _, f in COLUMN_TO_FIELD]
    records.sort(key=lambda r: r["row_id"])

    OUT_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_RECORDS.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps({k: rec[k] for k in field_order},
                                ensure_ascii=False) + "\n")

    audit.sort(key=lambda a: (a["row_id"], a["field"]))
    with OUT_AUDIT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["row_id", "company", "field", "old_value",
                                           "new_value", "change_type", "reason"])
        w.writeheader()
        w.writerows(audit)

    by_field = Counter(a["field"] for a in audit)
    by_type = Counter(a["change_type"] for a in audit)
    canonical_sha = sha256_file(OUT_RECORDS)
    code_sha = sha256_file(Path(__file__).resolve())

    manifest = {
        "manifest": "CLEANED_DATA_MANIFEST_v3",
        "phase": 2,
        "protocol": "README.md Phase 2 -- Clean, normalize, and freeze canonical records",
        "amendments_applied": ["A-001 (geographic semantics)"],
        "hash_chain": {
            "1_source_workbook": {
                "path": str(WORKBOOK.relative_to(ROOT)),
                "sha256": actual_sha,
                "verified_against": str(SOURCE_MANIFEST.relative_to(ROOT)),
            },
            "2_cleaning_code": {
                "path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": code_sha,
            },
            "3_canonical_records": {
                "path": str(OUT_RECORDS.relative_to(ROOT)),
                "sha256": canonical_sha,
                "bytes": OUT_RECORDS.stat().st_size,
                "record_count": len(records),
            },
        },
        "schema": {
            "fields": field_order,
            "field_count": len(field_order),
            "identity": {
                "row_id": "Record No. (int)",
                "company": "exact trimmed Company; no suffix stripping",
            },
            "not_materialized": sorted(forbidden),
            "note": "city/county derivation belongs to the Phase 4 loader (A-001).",
        },
        "sentinels": {
            "Not specified": "source value unknown/unprovided",
            "Not applicable": "field structurally does not apply",
            "None identified after search": "no credential evidence identified",
            "note": "No sentinel proves a real-world negative.",
        },
        "changed_cells": {
            "total": len(audit),
            "by_field": dict(sorted(by_field.items())),
            "by_change_type": dict(sorted(by_type.items())),
            "audit": str(OUT_AUDIT.relative_to(ROOT)),
        },
        "distributions": {
            "category": dict(sorted(cats.items())),
            "primary_facility_type": dict(sorted(facs.items())),
        },
        "validation": {name: {"pass": ok, "detail": d} for name, ok, d in checks},
        "generation_context": {
            "git_commit": git("rev-parse", "HEAD"),
            "git_tree_dirty": bool(git("status", "--porcelain")),
            "python": sys.version.split()[0],
            "openpyxl": openpyxl.__version__,
        },
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")

    _write_report(records, audit, checks, cats, facs, by_field, by_type,
                  actual_sha, code_sha, canonical_sha, ws_trim_hits)

    print(f"\nAll Phase 2 invariants passed.")
    print(f"  canonical records : {OUT_RECORDS.relative_to(ROOT)}  sha256 {canonical_sha}")
    print(f"  cleaning code     : sha256 {code_sha}")
    print(f"  changed cells     : {len(audit)}")
    return 0


def _write_report(records, audit, checks, cats, facs, by_field, by_type,
                  src_sha, code_sha, canonical_sha, ws_trim_hits) -> None:
    L = []
    L.append("# NORMALIZATION_REPORT_v3\n")
    L.append("Phase 2 — clean, normalize, and freeze canonical records.\n")
    L.append("## Hash chain\n")
    L.append("```text")
    L.append(f"raw workbook        {src_sha}")
    L.append(f"cleaning code       {code_sha}")
    L.append(f"canonical records   {canonical_sha}")
    L.append("```\n")
    L.append("The source hash was re-verified against `SOURCE_MANIFEST_v3.json` before "
             "any artifact was produced.\n")

    L.append("## What changed\n")
    L.append(f"**{len(audit)} cells changed** across {len({a['row_id'] for a in audit})} "
             f"of 205 rows. No row was added, dropped or reordered.\n")
    L.append("| field | cells changed |")
    L.append("|---|---|")
    for f, n in sorted(by_field.items(), key=lambda x: -x[1]):
        L.append(f"| `{f}` | {n} |")
    L.append("")
    L.append("| change type | cells |")
    L.append("|---|---|")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        L.append(f"| `{t}` | {n} |")
    L.append("")
    L.append("Every changed cell is listed individually in `CLEANING_AUDIT_v3.csv` with "
             "its old value, new value, change type and the frozen rule that authorised "
             "it.\n")

    L.append("## Value normalization\n")
    L.append("### Category\n")
    L.append("| value | rows |")
    L.append("|---|---|")
    for k, v in sorted(cats.items(), key=lambda x: -x[1]):
        L.append(f"| `{k}` | {v} |")
    L.append("\n`OEM Footprint` → `OEM (Footprint)`: 3 rows remapped, joining 5 already "
             "correct, giving **8**. `OEM Footprint` is now **0**.\n")
    L.append("### Primary Facility Type\n")
    L.append("| value | rows |")
    L.append("|---|---|")
    for k, v in sorted(facs.items(), key=lambda x: -x[1]):
        L.append(f"| `{k}` | {v} |")
    L.append("\n`Manufacturing plant` → `Manufacturing Plant`: 10 rows remapped, joining "
             "177, giving **187**. `Engineering / Manufacturing` → "
             "`Manufacturing / Engineering`: 1 row. `Manufacturing` remains a distinct "
             "value at **4**.\n")

    L.append("## Multi-valued fields\n")
    L.append("`Processes`, `Services`, `Certifications` were split on `;`, trimmed, "
             "emptied terms dropped, exact duplicates removed case-insensitively, sorted "
             "case-insensitively and rejoined as `\"; \"`. **Term spelling is preserved "
             "exactly**; no taxonomy normalization was applied.\n")
    reorder = Counter(a["field"] for a in audit
                      if a["change_type"].startswith("multivalue_"))
    L.append("| field | cells reordered/rejoined |")
    L.append("|---|---|")
    for f in MULTIVALUE_FIELDS:
        L.append(f"| `{f}` | {reorder.get(f, 0)} |")
    L.append("")
    L.append("(`certifications` sentinel insertions are counted under Sentinels below, "
             "not here.)")
    L.append("")

    L.append("## Sentinels applied\n")
    L.append("Frozen meanings — none proves a real-world negative.\n")
    L.append("| sentinel | meaning | cells |")
    L.append("|---|---|---|")
    L.append(f"| `Not specified` | source unknown/unprovided | "
             f"{sum(1 for a in audit if a['new_value'] == NOT_SPECIFIED)} |")
    L.append(f"| `Not applicable` | structurally does not apply | "
             f"{sum(1 for a in audit if a['new_value'] == NOT_APPLICABLE)} |")
    L.append(f"| `None identified after search` | no credential evidence | "
             f"{sum(1 for a in audit if a['new_value'] == NONE_IDENTIFIED)} |")
    L.append("")
    L.append("### Ordering rule\n")
    L.append("`Certification Count` was validated against the **pre-sentinel** "
             "certification parse on all 205 rows (0 mismatches) **before** the "
             "`None identified after search` sentinel was inserted. The 34 sentinel rows "
             "all carry `certification_count == 0`, so the sentinel still represents "
             "**zero certification terms** for later child-table construction.\n")
    L.append("### Geography (Amendment A-001)\n")
    L.append("```text")
    L.append("row 187  Valeo                      location = Not specified   (source unknown)")
    L.append("                                    address  = Not specified")
    L.append("row 192  Volvo Cars USA             location = Not applicable  (structurally N/A)")
    L.append("                                    address  = 1800 Volvo Place, Mahwah, NJ 07430")
    L.append("row 193  Volvo Group North America  location = Not applicable")
    L.append("                                    address  = 7900 National Service Rd, Greensboro, NC 27409")
    L.append("```\n")
    L.append("`Address` was never substituted for `Location`. **No `city`/`county` field "
             "is materialized in Phase 2** — that derivation belongs to the Phase 4 "
             "loader, and may read only geographic information explicitly present in a "
             "real `Location` value.\n")

    L.append("## Judgment calls, recorded\n")
    L.append("- **The single blank `Supplier or Affiliation Type` on an `OEM`-category "
             "row was NOT imputed.** 11 of 12 `OEM` rows carry "
             "`Original Equipment Manufacturer`, but sibling-row frequency is not source "
             "evidence for the twelfth. It received `Not specified` like every other "
             "blank, and the pattern is recorded here rather than acted on.\n")
    L.append("- **Multi-row companies were left untouched.** 9 companies occupy 21 rows. "
             "Conflict handling, `split_group` and identity grouping are Phase 3+.\n")
    _n = sum(ws_trim_hits.values())
    L.append(f"- **Whitespace trimming on single-value passthrough fields** affected "
             f"{_n} cell{'' if _n == 1 else 's'}"
             + (f" ({dict(ws_trim_hits)})" if ws_trim_hits else "")
             + ". Any such change is itemised in the audit CSV.\n")

    L.append("## Validation\n")
    L.append("| check | result | detail |")
    L.append("|---|---|---|")
    for name, ok, detail in checks:
        L.append(f"| `{name}` | {'PASS' if ok else 'FAIL'} | {detail} |")
    L.append("")
    OUT_REPORT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Gate as exc:
        print(f"\nPHASE 2 GATE FAILURE: {exc}", file=sys.stderr)
        print("No artifact written. The frozen expectation was not altered.",
              file=sys.stderr)
        raise SystemExit(1)
