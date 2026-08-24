"""Phase 8 -- canonical evaluation record schema and the sealed-test boundary.

RECORD SCHEMA. README Phase 40 fixes what must be retained for every item:
`example_id`, question, raw output, parsed output, generated SQL, execution
result, gold, score, error type, adapter hash, prompt hash -- and states plainly
"**Never scores alone.**" `EvalRecord` carries all of it, plus the frozen Phase 7
grading metadata (`answer_type`, `target_columns`, both metrics, `status`).

Phase 8 populates these with synthetic fixtures, but the schema is the one real
evaluation records will use. Nothing here decides metadata that Phase 9 owns.

THE SEALED-TEST BOUNDARY. Test and Q42 outputs must be unreadable by ordinary
dev-facing reporting until Phase 40.

THE SEALING DECISION ATTACHES TO THE ARTIFACT, NOT TO WHAT THE ARTIFACT SAYS
ABOUT ITSELF. A superseded design inferred sealing from `family` strings inside
the records. Review demonstrated three failures of that approach:

    1. a sealed artifact whose records declared `family = factual_recall` was
       accepted by the dev loader
    2. an unknown future family (`brand_new_future_family`) silently defaulted
       to dev-accessible
    3. `sealed_metadata` parsed sealed records to compute `families` and
       `conditions`, exceeding the pre-Phase-40 metadata boundary

Content cannot be trusted to classify itself, and an unknown artifact must not
default open. The corrected flow is:

    identify artifact (resolved canonical path)
        -> trusted registry lookup + integrity hash
        -> classification: dev | sealed | unknown
        -> sealed or unknown  -> REFUSE
        -> only an authorized dev artifact is opened and parsed

Classification therefore happens BEFORE any record is read. `family`,
`condition`, `status`, filename keywords and record contents take no part in
the security decision.

    dev-facing reporting      cannot request unseal -- the parameter does not
                              exist on any dev API
    this library              CANNOT read sealed content at all. There is no
                              `load_results(path, unseal=True)`, because such a
                              switch would also work on real sealed output
    sealed_metadata(...)      trusted-manifest fields ONLY. It never opens the
                              result file, so it cannot disclose families,
                              conditions, statuses, scores, errors or examples
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

# Artifact classification. UNKNOWN is the default for anything not explicitly
# registered, and it refuses -- an unregistered artifact never becomes dev.
DEV_KIND, SEALED_KIND, UNKNOWN_KIND = "dev", "sealed", "unknown"


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


@dataclass(frozen=True)
class ArtifactRegistration:
    """A trusted, content-blind classification of one result artifact.

    Every field is provenance about the artifact. None of it is derived by
    reading the evaluation records, and `item_count` is PREDECLARED here rather
    than counted from the file, so metadata never requires opening sealed
    content.
    """
    artifact_id: str
    canonical_path: str        # os.path.realpath, so symlinks and relative
                               # spellings resolve to one identity
    artifact_kind: str         # DEV_KIND | SEALED_KIND
    sha256: str
    schema_version: str
    item_count: int
    provenance: str

    def __post_init__(self):
        if self.artifact_kind not in (DEV_KIND, SEALED_KIND):
            raise ValueError(f"artifact_kind {self.artifact_kind!r} invalid")


class ArtifactRegistry:
    """The trusted manifest. Classification comes from here, never from content.

    Lookup is by RESOLVED canonical path, so a relative spelling, an absolute
    spelling and a symlink all resolve to the same registration. A file whose
    bytes no longer match its registered hash, or that is not registered at
    all, classifies as UNKNOWN -- which refuses.
    """

    def __init__(self, registrations=()):
        self._by_path: dict[str, ArtifactRegistration] = {}
        for r in registrations:
            self.register(r)

    def register(self, reg: ArtifactRegistration) -> None:
        self._by_path[str(Path(reg.canonical_path))] = reg

    @staticmethod
    def canonicalize(path) -> str:
        # realpath resolves symlinks AND relative segments to one identity.
        return str(Path(path).resolve())

    def classify(self, path) -> tuple[str, ArtifactRegistration | None]:
        """(kind, registration). Unregistered or altered -> UNKNOWN, which refuses."""
        canonical = self.canonicalize(path)
        reg = self._by_path.get(canonical)
        if reg is None:
            return UNKNOWN_KIND, None
        p = Path(canonical)
        if not p.is_file() or sha256_file(p) != reg.sha256:
            # Registered identity, but the bytes are not the registered bytes.
            return UNKNOWN_KIND, None
        return reg.artifact_kind, reg

    def manifest(self) -> list[dict]:
        return [asdict(r) for r in
                sorted(self._by_path.values(), key=lambda r: r.artifact_id)]


def load_dev_results(path, registry: ArtifactRegistry) -> list[EvalRecord]:
    """Load an authorized DEV artifact.

    CLASSIFY BEFORE PARSE. The authorization decision is made from the trusted
    registry before the file is opened, so a sealed artifact is never read --
    not even to discover what it contains.

    There is deliberately no `unseal` parameter. A sealed or unknown artifact
    raises, and no argument can change that: a generic boolean switch would also
    unlock real test/Q42 output before Phase 40.
    """
    kind, reg = registry.classify(path)          # <-- before any read
    if kind == SEALED_KIND:
        raise SealError(
            f"artifact {reg.artifact_id!r} is registered SEALED; dev-facing "
            f"loading is refused and the file was not opened. Sealed results "
            f"are readable only through the Phase 40 unblind entry point, "
            f"which does not exist yet.")
    if kind != DEV_KIND:
        raise SealError(
            "artifact is not a registered dev artifact (unregistered, moved, "
            "copied, or its bytes no longer match the registered hash). "
            "Classification fails closed: unknown is refused, never treated "
            "as dev.")
    raw = [json.loads(l) for l in
           Path(reg.canonical_path).read_text(encoding="utf-8").splitlines()
           if l.strip()]
    if len(raw) != reg.item_count:
        raise SealError(
            f"artifact {reg.artifact_id!r} holds {len(raw)} records but the "
            f"trusted manifest predeclares {reg.item_count}")
    return [from_dict(r) for r in raw]


def sealed_metadata(path, registry: ArtifactRegistry) -> dict:
    """Non-content integrity/provenance for a sealed artifact.

    This function NEVER OPENS THE RESULT FILE. Every value comes from the
    trusted manifest, so it is structurally incapable of disclosing families,
    conditions, statuses, scores, error types, questions, answers, SQL or
    execution results. `item_count` is the manifest's predeclared count, not a
    count of parsed records.
    """
    kind, reg = registry.classify(path)
    if kind != SEALED_KIND:
        raise SealError(
            f"sealed_metadata is only defined for a registered sealed "
            f"artifact; this one classifies as {kind!r}")
    return {
        "artifact_id": reg.artifact_id,
        "artifact_path": reg.canonical_path,
        "sha256": reg.sha256,
        "item_count": reg.item_count,
        "schema_version": reg.schema_version,
        "provenance": reg.provenance,
        "artifact_kind": SEALED_KIND,
        "records_parsed": False,
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
