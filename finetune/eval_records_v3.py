"""Phase 8 -- canonical evaluation record schema and the sealed-test boundary.

RECORD SCHEMA. README Phase 40 fixes what must be retained for every item:
`example_id`, question, raw output, parsed output, generated SQL, execution
result, gold, score, error type, adapter hash, prompt hash -- and states plainly
"**Never scores alone.**" `EvalRecord` carries all of it, plus the frozen Phase 7
grading metadata (`answer_type`, `target_columns`, both metrics, `status`).

Phase 8 populates these with synthetic fixtures, but the schema is the one real
evaluation records will use. Nothing here decides metadata that Phase 9 owns.

THE SEALED-TEST BOUNDARY. Test and Q42 outputs must be unreadable by ordinary
dev-facing reporting until Phase 40. The design deliberately avoids a reusable
boolean backdoor:

    dev-facing reporting      cannot request unseal -- the parameter does not
                              exist on any dev API
    this library              CANNOT read sealed content at all. There is no
                              `load_results(path, unseal=True)`, because such a
                              switch would also work on real sealed output
    sealed_metadata(path)     count / hash / path / provenance ONLY -- never
                              example text, answers, errors or scores
    Phase 40 entry point      owns the real unblind authority (CLAUDE.md 23:
                              "an explicit Phase-40-only `--unseal` control")

`CLAUDE.md` 23 defines the authorization mechanism as belonging to the
evaluation entry point at Phase 40; it does not exist yet and is deliberately
NOT created here. Phase 8 validates the boundary with synthetic sealed fixtures
only -- no real test or Q42 content is created, read or reported.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import grade_v3 as G

RECORDS_VERSION = "eval_records_v3.0"

# Frozen status vocabulary. Sourced from the Phase 7 grader rather than
# redeclared, so the two can never drift apart.
STATUSES = G.STATUSES
SUCCESS_STATUS = "correct"
FAILURE_STATUSES = tuple(s for s in STATUSES if s not in ("correct", "incorrect"))

# Result-set classification. `sealed` covers everything the protocol keeps
# blind until Phase 40.
DEV_KIND, SEALED_KIND = "dev", "sealed"
SEALED_FAMILY_MARKERS = ("test", "q42", "probe_42")


class SealError(RuntimeError):
    """A sealed result set was addressed by a path that may not read it."""


class RecordSchemaError(ValueError):
    """A record is missing required fields or carries an invalid status."""


@dataclass(frozen=True)
class EvalRecord:
    """One evaluated item. Every README Phase 40 retention field is present."""

    example_id: str
    family: str                 # probe / evaluation family identifier
    condition: str              # e.g. base, base_sql, B_facts
    question: str
    raw_output: str | None      # exactly as generated
    parsed_output: str | None   # None when parsing was refused
    generated_sql: str | None
    execution_result: list | None
    gold: object
    answer_type: str | None     # from generator metadata (Phase 7 contract)
    target_columns: list | None
    task_result_correctness: float
    strict_result_schema_accuracy: float
    status: str
    error_type: str | None
    error_detail: str | None
    prompt_hash: str
    adapter_hash: str | None    # None for untrained baselines
    seed: int | None            # None for deterministic baselines
    grader_version: str
    grader_sha256: str

    def __post_init__(self):
        if self.status not in STATUSES:
            raise RecordSchemaError(
                f"status {self.status!r} is not in the frozen vocabulary "
                f"{STATUSES}")
        if self.status == SUCCESS_STATUS and self.task_result_correctness != 1.0:
            raise RecordSchemaError(
                "status 'correct' must carry task_result_correctness == 1.0")
        if self.status != SUCCESS_STATUS and self.task_result_correctness == 1.0:
            raise RecordSchemaError(
                f"status {self.status!r} must not carry a perfect task score")

    def to_dict(self) -> dict:
        return asdict(self)


REQUIRED_FIELDS = tuple(EvalRecord.__dataclass_fields__)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_result_set(family: str) -> str:
    """Sealed unless demonstrably a dev family. Fail closed, not open."""
    low = (family or "").lower()
    return SEALED_KIND if any(m in low for m in SEALED_FAMILY_MARKERS) else DEV_KIND


def load_dev_results(path) -> list[EvalRecord]:
    """Load a DEV result set.

    There is deliberately no `unseal` parameter. A sealed result set raises,
    and no argument to this function can change that -- a generic boolean
    switch would also unlock real test/Q42 output before Phase 40.
    """
    path = Path(path)
    raw = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    sealed = sorted({r.get("family", "") for r in raw
                     if classify_result_set(r.get("family", "")) == SEALED_KIND})
    if sealed:
        raise SealError(
            f"{path} contains sealed families {sealed}; dev-facing loading is "
            f"refused. Sealed results are readable only through the Phase 40 "
            f"unblind entry point, which does not exist yet. Use "
            f"sealed_metadata() for counts and hashes.")
    return [from_dict(r) for r in raw]


def sealed_metadata(path) -> dict:
    """Metadata for a sealed result set: count / hash / path / provenance ONLY.

    Deliberately returns no example text, question, answer, gold, error detail
    or score -- the point is that a pre-Phase-40 audit can confirm a file
    exists and is unchanged without learning anything about its contents.
    """
    path = Path(path)
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    families, conditions = set(), set()
    for line in lines:
        rec = json.loads(line)
        families.add(rec.get("family", ""))
        conditions.add(rec.get("condition", ""))
    return {
        "path": str(path),
        "item_count": len(lines),
        "sha256": sha256_file(path),
        "families": sorted(families),
        "conditions": sorted(conditions),
        "kind": SEALED_KIND,
        "contents_disclosed": False,
        "note": ("counts, hashes and provenance only; no example text, gold, "
                 "prediction, error detail or score is read or returned"),
    }


def from_dict(d: dict) -> EvalRecord:
    missing = [f for f in REQUIRED_FIELDS if f not in d]
    if missing:
        raise RecordSchemaError(f"record missing required field(s): {missing}")
    unknown = [k for k in d if k not in REQUIRED_FIELDS]
    if unknown:
        raise RecordSchemaError(
            f"record carries unsupported field(s) {unknown}; the schema is "
            f"versioned ({RECORDS_VERSION}) and stale records must not be "
            f"silently accepted")
    return EvalRecord(**d)


def write_records(path, records: list[EvalRecord]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return sha256_file(path)
