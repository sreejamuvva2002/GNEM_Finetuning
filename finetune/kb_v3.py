"""GNEM v3 loader and data contract -- the one module that defines what a row
means to everything downstream.

THE CORE ANTI-LEAKAGE CONTRACT (README.md Phase 4)
--------------------------------------------------
There are exactly three named knowledge scopes and **no unscoped accessor**:

    train_kb      train rows only          -- ALL training targets
    train_dev_kb  train + dev rows         -- dev evaluation gold only
    full_kb       all rows                 -- test evaluation gold only, and the
                                              deployed SQL database

`load_kb(scope)` takes scope as a REQUIRED positional parameter with no default.
Omitting it raises TypeError; an unknown scope or None raises ScopeError. There
is deliberately no convenience wrapper, no module-level singleton and no cache
that could hand `full_kb` to training code by accident.

The scopes are DERIVED from the frozen Phase 3 split. The expected row counts
(148 / 165 / 205) are asserted as validation, never used as construction logic.

GEOGRAPHY (Amendment A-001)
---------------------------
`city`/`county` are derived ONLY from geographic information explicitly present
in that row's own canonical `Location`. Never from `Address`, ZIP, external
geocoding, company knowledge, latitude/longitude, or any other row. A sentinel
`Location` yields NULL/NULL. Where a component is not explicitly represented,
that component is NULL -- it is never inferred.

County text is preserved exactly as represented ("Hall County", never "Hall").

MODEL-FACING CONTRACT
---------------------
`model_facing_record()` builds its result from an explicit ALLOWLIST. It is not
a full record with prohibited fields deleted afterwards, so a field added to the
internal record can never leak into model-facing text by omission. `split`,
`split_group` and `certification_count` are structurally unable to appear;
latitude/longitude and graph metadata do not exist in this module at all.

`certification_count` exists internally for validation only.

NOT IN THIS PHASE: gnem_v3.sqlite, child tables, holdouts, exposure ledgers,
training datasets, probes, Q42, inference, training. Those are Phase 5+.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "datasets_v3" / "canonical_records_v3.jsonl"
SPLIT_CSV = ROOT / "datasets_v3" / "company_split_groups_v3.csv"

LOADER_VERSION = "kb_v3.0"

# Frozen Phase 2 / Phase 3 inputs. Re-verified on every load.
EXPECTED_CANONICAL_SHA = "42851c0a2e93209ac5d37e73ce07447009e038b9db625004212722d7738e6488"
EXPECTED_SPLIT_SHA = "a59d673ac9acafd1f70f60cf560491c32d8d11bacdab3c9bc5d77016b536b701"

# The only valid scopes. There is no default and no fourth option.
KB_SCOPES = ("train_kb", "train_dev_kb", "full_kb")
SCOPE_SPLITS: dict[str, frozenset[str]] = {
    "train_kb": frozenset({"train"}),
    "train_dev_kb": frozenset({"train", "dev"}),
    "full_kb": frozenset({"train", "dev", "test"}),
}
# Validation only -- never the mechanism by which a scope is built.
EXPECTED_SCOPE_ROWS = {"train_kb": 148, "train_dev_kb": 165, "full_kb": 205}

# Location sentinels. These never parse into city/county.
LOCATION_SENTINELS = frozenset({
    "Not specified", "Not applicable", "Not available",
    "None identified after search",
})

# All 18 canonical columns, in canonical order.
CANONICAL_FIELDS = (
    "row_id", "company", "category", "industry_group", "location", "address",
    "primary_facility_type", "ev_supply_chain_role", "primary_oems",
    "supplier_or_affiliation_type", "employment", "product_or_service",
    "processes", "services", "ev_battery_relevant", "classification_method",
    "certifications", "certification_count",
)

# ---------------------------------------------------------------------------
# Model-facing ALLOWLIST. Adding a field to the internal record does NOT add it
# here -- that is the point. `split`, `split_group` and `certification_count`
# are absent by construction, not by deletion.
# ---------------------------------------------------------------------------
MODEL_FACING_FIELDS = (
    "row_id", "company", "category", "industry_group", "location", "address",
    "primary_facility_type", "ev_supply_chain_role", "primary_oems",
    "supplier_or_affiliation_type", "employment", "product_or_service",
    "processes", "services", "ev_battery_relevant", "classification_method",
    "certifications", "city", "county",
)
# Never model-facing, asserted at import and by the Phase 4 gate.
FORBIDDEN_MODEL_FACING = frozenset({
    "split", "split_group", "certification_count",
    "latitude", "longitude", "geo", "graph_id", "graph_edges",
})
assert not (set(MODEL_FACING_FIELDS) & FORBIDDEN_MODEL_FACING), \
    "model-facing allowlist must never contain a forbidden field"


class ScopeError(ValueError):
    """Raised when a KB scope is missing, None, or not one of KB_SCOPES."""


class IntegrityError(RuntimeError):
    """Raised when a frozen upstream input has drifted."""


@dataclass(frozen=True)
class KBRecord:
    """One GNEM row. `city`/`county` are derived per Amendment A-001; every other
    field is the frozen canonical value, byte-for-byte."""
    row_id: int
    company: str
    category: str
    industry_group: str
    location: str
    address: str
    primary_facility_type: str
    ev_supply_chain_role: str
    primary_oems: str
    supplier_or_affiliation_type: str
    employment: int
    product_or_service: str
    processes: str
    services: str
    ev_battery_relevant: str
    classification_method: str
    certifications: str
    # Derived under A-001, strictly from this row's own `location`.
    city: str | None
    county: str | None
    # Validation-only. Never model-facing; excluded from MODEL_FACING_FIELDS.
    certification_count: int = field(repr=False)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# `City, County` -- both components explicitly present, exactly one separator.
_LOCATION_RE = re.compile(r"^(?P<city>[^,]+?)\s*,\s*(?P<county>[^,]+?)$")


def derive_city_county(location: str) -> tuple[str | None, str | None]:
    """Derive (city, county) from a row's own canonical `Location` and nothing else.

    Amendment A-001. This function takes ONLY the location string: it structurally
    cannot consult `Address`, ZIP, geocoding, company knowledge, latitude/longitude
    or another row, because it is never given them.

    A component that is not explicitly represented is NULL; it is never inferred.
    County text is preserved verbatim, including the word "County".
    """
    if location is None:
        return None, None
    text = location.strip()
    if text == "" or text in LOCATION_SENTINELS:
        return None, None

    m = _LOCATION_RE.match(text)
    if not m:
        # Not unambiguously parseable under the frozen rule -> prefer NULL over a
        # guess. Reported by the Phase 4 gate rather than silently swallowed.
        return None, None

    city = m.group("city").strip() or None
    county = m.group("county").strip() or None
    # A component must be explicitly represented to be populated. A trailing
    # "County" word alone is not a county name, and a bare county with no city
    # leaves city NULL -- neither is synthesised from the other.
    if county is not None and county.casefold() == "county":
        county = None
    return city, county


def _read_frozen_inputs() -> tuple[list[dict], dict[int, str], dict[int, str], str, str]:
    canonical_sha = sha256_file(CANONICAL)
    if canonical_sha != EXPECTED_CANONICAL_SHA:
        raise IntegrityError(
            f"canonical records drifted\n  expected {EXPECTED_CANONICAL_SHA}"
            f"\n  actual   {canonical_sha}")
    split_sha = sha256_file(SPLIT_CSV)
    if split_sha != EXPECTED_SPLIT_SHA:
        raise IntegrityError(
            f"split artifact drifted\n  expected {EXPECTED_SPLIT_SHA}"
            f"\n  actual   {split_sha}")

    rows = [json.loads(l) for l in CANONICAL.read_text(encoding="utf-8").splitlines()]
    split_of: dict[int, str] = {}
    group_of: dict[int, str] = {}
    with SPLIT_CSV.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            split_of[int(r["row_id"])] = r["split"]
            group_of[int(r["row_id"])] = r["split_group"]

    if {r["row_id"] for r in rows} != set(split_of):
        raise IntegrityError("canonical and split row_id sets differ")
    return rows, split_of, group_of, canonical_sha, split_sha


def _build_record(raw: dict) -> KBRecord:
    city, county = derive_city_county(raw["location"])
    if raw.get("employment") is None:
        raise IntegrityError(f"row {raw['row_id']}: employment not populated")
    return KBRecord(
        **{f: raw[f] for f in CANONICAL_FIELDS},
        city=city,
        county=county,
    )


def load_kb(scope):
    """Load the KB at an EXPLICIT scope.

    `scope` is a required positional parameter with no default:
        load_kb()               -> TypeError  (Python arity)
        load_kb(None)           -> ScopeError
        load_kb("full")         -> ScopeError
        load_kb("full_kb")      -> ok

    There is no unscoped accessor, no default, and no cached global. Every caller
    must name the scope it is entitled to read.
    """
    if scope is None:
        raise ScopeError(
            "KB scope is required and must be named explicitly; got None. "
            f"Valid scopes: {', '.join(KB_SCOPES)}")
    if not isinstance(scope, str) or scope not in SCOPE_SPLITS:
        raise ScopeError(
            f"unknown KB scope {scope!r}; there is no default scope. "
            f"Valid scopes: {', '.join(KB_SCOPES)}")

    rows, split_of, group_of, _, _ = _read_frozen_inputs()
    allowed = SCOPE_SPLITS[scope]
    selected = [r for r in rows if split_of[r["row_id"]] in allowed]

    expected = EXPECTED_SCOPE_ROWS[scope]
    if len(selected) != expected:  # validation, not construction
        raise IntegrityError(
            f"scope {scope!r} produced {len(selected)} rows, expected {expected}")

    return [_build_record(r) for r in sorted(selected, key=lambda r: r["row_id"])]


def model_facing_record(rec: KBRecord) -> dict:
    """Project a record to model-facing knowledge using the explicit ALLOWLIST.

    Built by allowlist, never by deleting prohibited fields from a full record,
    so a newly added internal field cannot leak by omission.
    """
    return {f: getattr(rec, f) for f in MODEL_FACING_FIELDS}


def split_metadata(scope) -> dict[int, dict[str, str]]:
    """Leakage-control metadata, kept deliberately OUT of the KB record.

    Available to split-integrity auditing only. It is never merged into a record
    and never reaches model-facing text.
    """
    if scope not in SCOPE_SPLITS:
        raise ScopeError(f"unknown KB scope {scope!r}; there is no default scope.")
    _, split_of, group_of, _, _ = _read_frozen_inputs()
    allowed = SCOPE_SPLITS[scope]
    return {rid: {"split": split_of[rid], "split_group": group_of[rid]}
            for rid in sorted(split_of) if split_of[rid] in allowed}


def frozen_input_hashes() -> dict[str, str]:
    _, _, _, canonical_sha, split_sha = _read_frozen_inputs()
    return {"canonical_records_v3.jsonl": canonical_sha,
            "company_split_groups_v3.csv": split_sha,
            "loader_version": LOADER_VERSION,
            "kb_v3.py": sha256_file(Path(__file__).resolve())}


# ---------------------------------------------------------------------------
# Static check required by README.md Phase 4: "a static check confirms no
# training generator can reach `full_kb`".
#
# REUSABLE ON PURPOSE. Training generators do not exist yet (Phase 10+), so a
# run today scans zero files and proves nothing about generators not yet
# written. Every later training-data phase MUST re-run this with its own module
# paths, and the audit must report the scanned count honestly.
# ---------------------------------------------------------------------------
TRAINING_GENERATOR_FORBIDDEN_SCOPES = ("full_kb", "train_dev_kb")


def static_check_no_training_generator_reaches_full_kb(paths) -> dict:
    """Scan the given training-generator sources for forbidden scope literals.

    Returns a report; callers decide whether a non-empty `violations` is fatal.
    Reports `scanned` so a vacuous pass over zero files can never be presented
    as evidence.
    """
    scanned, violations = [], []
    for p in sorted(Path(x) for x in paths):
        if not p.is_file():
            continue
        scanned.append(str(p.relative_to(ROOT) if p.is_absolute() else p))
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            for bad in TRAINING_GENERATOR_FORBIDDEN_SCOPES:
                if f'"{bad}"' in code or f"'{bad}'" in code:
                    violations.append({"file": scanned[-1], "line": n,
                                       "scope": bad, "text": line.strip()})
    return {
        "scanned_files": scanned,
        "scanned_count": len(scanned),
        "violations": violations,
        "violation_count": len(violations),
        "proves": ("nothing about generators that do not exist yet; this check must "
                   "be re-run by every later training-data phase with its own paths"
                   if not scanned else
                   f"no forbidden scope literal in {len(scanned)} scanned file(s)"),
    }
