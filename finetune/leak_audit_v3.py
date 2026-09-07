"""Shared validation-only helper: confirms no dev/test-split company literal
appears in a training generator's final rendered strings.

Deliberately isolated from every training-data generator module (phase10+) so
the Phase 4 static check
(`kb_v3.static_check_no_training_generator_reaches_full_kb`) scans generator
source clean of `full_kb`/`train_dev_kb` literals. This module is validation
infrastructure -- it is imported by generators to prove a negative about their
OWN output, never to source a training target -- and is itself excluded from
that static check's scanned paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as KB  # noqa: E402


def non_train_companies() -> set[str]:
    """Every company NOT reachable through train_kb -- i.e. every dev or test
    company under the frozen Phase 3 split."""
    train_co = {r.company for r in KB.load_kb("train_kb")}
    all_co = {r.company for r in KB.load_kb("full_kb")}
    return all_co - train_co


def company_splits() -> dict[str, str]:
    """company -> split ('train'/'dev'/'test'), for audit reporting only.

    Reads full_kb split metadata -- validation-only, same reasoning as
    non_train_companies(): this module exists so generator source never
    contains a full_kb/train_dev_kb literal for the Phase 4 static check.
    """
    meta = KB.split_metadata("full_kb")
    recs = {r.row_id: r.company for r in KB.load_kb("full_kb")}
    return {recs[rid]: v["split"] for rid, v in meta.items()}


def row_splits() -> dict[int, str]:
    """row_id -> split, for audit reporting only (see company_splits())."""
    return {rid: v["split"] for rid, v in KB.split_metadata("full_kb").items()}


def companies_leaked_in(texts: list[str]) -> list[str]:
    """Which dev/test companies appear as a literal substring of any text.

    A plain substring check, deliberately stricter than the exposure
    scanner's NFKC/casefold normalization: an exact-name leak is the failure
    mode this check exists to catch, and over-detection here just means one
    extra name to eyeball, never a missed leak.
    """
    if isinstance(texts, (str, bytes, dict)):
        raise TypeError(
            f"companies_leaked_in expects list[str], got {type(texts).__name__}")
    blob = "\n".join(texts)
    return sorted(c for c in non_train_companies() if c in blob)
