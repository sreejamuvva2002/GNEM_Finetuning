"""Phase 1 -- freeze the source workbook.

Records SHA256, size, sheet structure, row/column counts and the exact unique
company count for the single source workbook, and asserts the four values the
frozen protocol fixes in README.md Phase 1:

    205 rows | 18 columns | 193 exact company names | Certification Key is 0x0

Phase 1 does NOT clean, normalize, transform or reinterpret any workbook value.
Cells are read exactly as stored; nothing is written back to the workbook.

A mismatch is a Phase 1 GATE FAILURE: this script exits non-zero and writes no
manifest, rather than recording a corrected number.

Provenance note: the chunked `sha256` helper is ported from the v2 reference
(`finetune/validate/manifest.py` at v2-frozen-reference
b18313ae593995e8d415880603b3d355dd695ebd). Nothing else is carried over -- v2
hashed a different workbook (`GNEM_Excel_Data.xlsx`) under a different layout.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "kb" / "GNEM_Final_Combined_Dataset.xlsx"
ACTIVE_SHEET = "GNEM Combined"
EMPTY_SHEET = "Certification Key"
OUT = ROOT / "datasets_v3" / "SOURCE_MANIFEST_v3.json"

# Frozen in README.md Phase 1. Never edited to match an observation.
EXPECTED_ROWS = 205
EXPECTED_COLUMNS = 18
EXPECTED_COMPANIES = 193


def sha256(path: Path) -> str:
    """Chunked file digest. Ported from v2 finetune/validate/manifest.py."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    if not WORKBOOK.is_file():
        print(f"GATE FAILURE: source workbook not found: {WORKBOOK}", file=sys.stderr)
        return 1

    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    try:
        sheet_names = list(wb.sheetnames)
        sheets = []
        for name in wb.sheetnames:
            ws = wb[name]
            rows = list(ws.iter_rows(values_only=True))
            has_values = any(c is not None for r in rows for c in r)
            sheets.append({
                "name": name,
                # Effective extent: rows/cells that actually carry values.
                "effective_rows": len(rows) if has_values else 0,
                "effective_columns": (max(len(r) for r in rows) if rows and has_values else 0),
                # openpyxl reports 1x1 for a wholly empty sheet (dimension "A1").
                # Both are recorded so the 0x0 claim is auditable, not asserted.
                "openpyxl_max_row": ws.max_row,
                "openpyxl_max_column": ws.max_column,
                "has_any_value": has_values,
            })

        ws = wb[ACTIVE_SHEET]
        rows = list(ws.iter_rows(values_only=True))
        header, data = rows[0], rows[1:]
        columns = [str(h) for h in header]

        company_idx = columns.index("Company")
        raw = [r[company_idx] for r in data]
        # str.strip() only -- the protocol's `company` identity is the exact
        # trimmed name (CLAUDE.md 11). No suffix/case normalization, ever.
        trimmed = [str(v).strip() for v in raw]

        distinct_exact_trimmed = len(set(trimmed))
        multi_row = {k: v for k, v in Counter(trimmed).items() if v > 1}
    finally:
        wb.close()

    checks = [
        ("row_count", len(data), EXPECTED_ROWS),
        ("column_count", len(columns), EXPECTED_COLUMNS),
        ("unique_company_count", distinct_exact_trimmed, EXPECTED_COMPANIES),
    ]
    ck = next(s for s in sheets if s["name"] == EMPTY_SHEET)
    ck_empty = ck["effective_rows"] == 0 and ck["effective_columns"] == 0

    validation = {
        name: {"expected": exp, "observed": obs, "pass": obs == exp}
        for name, obs, exp in checks
    }
    validation["certification_key_is_0x0"] = {
        "expected": "0x0",
        "observed": f"{ck['effective_rows']}x{ck['effective_columns']}",
        "pass": ck_empty,
    }
    failed = [k for k, v in validation.items() if not v["pass"]]

    for k, v in validation.items():
        print(f"  [{'PASS' if v['pass'] else 'FAIL'}] {k}: expected {v['expected']}, observed {v['observed']}")

    if failed:
        print(f"\nPHASE 1 GATE FAILURE: {', '.join(failed)}", file=sys.stderr)
        print("No manifest written. Mismatch is recorded as a gate failure, not corrected.", file=sys.stderr)
        return 1

    manifest = {
        "manifest": "SOURCE_MANIFEST_v3",
        "phase": 1,
        "protocol": "README.md Phase 1 -- Freeze the source workbook",
        "source_workbook": {
            "path": str(WORKBOOK.relative_to(ROOT)),
            "sha256": sha256(WORKBOOK),
            "bytes": WORKBOOK.stat().st_size,
        },
        "workbook_structure": {
            "sheet_names": sheet_names,
            "sheet_count": len(sheets),
            "sheets": sheets,
            "active_sheet": ACTIVE_SHEET,
            "ignored_empty_sheet": EMPTY_SHEET,
        },
        "active_sheet": {
            "name": ACTIVE_SHEET,
            "header_row_count": 1,
            "data_row_count": len(data),
            "column_count": len(columns),
            "column_names": columns,
        },
        "companies": {
            "identity": "exact trimmed Company cell (CLAUDE.md 11); no suffix or case normalization",
            "unique_company_count": distinct_exact_trimmed,
            # Recorded to show the count carries no interpretive ambiguity.
            "unique_raw_untrimmed": len(set(raw)),
            "unique_casefolded": len({t.casefold() for t in trimmed}),
            "rows_requiring_trim": sum(1 for a, b in zip(raw, trimmed) if str(a) != b),
            "blank_company_cells": sum(1 for v in raw if v is None or str(v).strip() == ""),
            # Observation only. Multi-row (company, attribute) handling is Phase 2+.
            "companies_on_multiple_rows": len(multi_row),
            "rows_covered_by_multi_row_companies": sum(multi_row.values()),
        },
        "validation": validation,
        "phase_1_scope": {
            "cleaning_applied": False,
            "normalization_applied": False,
            "transformation_applied": False,
            "note": "Values read exactly as stored. Cleaning is Phase 2.",
        },
        "generation_context": {
            "git_commit": git("rev-parse", "HEAD"),
            "git_tree_dirty": bool(git("status", "--porcelain")),
            "generator": str(Path(__file__).resolve().relative_to(ROOT)),
            "generator_sha256": sha256(Path(__file__).resolve()),
            "python": sys.version.split()[0],
            "openpyxl": openpyxl.__version__,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nAll Phase 1 checks passed. Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
