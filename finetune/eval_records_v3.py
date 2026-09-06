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

    dev-facing reporting      cannot request unseal, and cannot supply or
                              replace the classification authority -- neither
                              parameter exists on any dev API
    this library              CANNOT read sealed content at all. There is no
                              `load_results(path, unseal=True)`, because such a
                              switch would also work on real sealed output
    sealed_metadata(...)      trusted-manifest fields ONLY. It may read raw
                              bytes to verify the registered hash, but it never
                              PARSES record content, so it cannot disclose
                              families, conditions, statuses, scores, errors or
                              examples
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
from types import MappingProxyType

import grade_v3 as G

RECORDS_VERSION = "eval_records_v3.1"

# Fields added after the original schema was frozen (Phase 9 correction).
# They carry defaults so an old serialized record (predating them) still
# loads via from_dict -- they are backfilled to None, never treated as
# missing-required.
NEW_OPTIONAL_FIELDS = ("parts", "regrade_outcome", "regrader_sha256")

# Valid values for `regrade_outcome`. None means "never regraded". This is a
# separate, NON-AUTHORITATIVE field from `status` -- it never joins the
# frozen 8-value status vocabulary (CLAUDE.md 25's closed status enum and its
# scored+failed==expected_probe_size assertion are untouched by this field).
REGRADE_OUTCOMES = ("recomputed", "insufficient_evidence")

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
    # -- added after the original schema was frozen (Phase 9 correction) --
    parts: tuple | None = None            # multi_part metadata, mirrors item["parts"]
    regrade_outcome: str | None = None    # None | "recomputed" | "insufficient_evidence"
    regrader_sha256: str | None = None    # eval_verify_v3.py's own hash at regrade() time

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
        if self.regrade_outcome is not None and self.regrade_outcome not in REGRADE_OUTCOMES:
            raise RecordSchemaError(
                f"regrade_outcome {self.regrade_outcome!r} not in "
                f"{(None, *REGRADE_OUTCOMES)}")

    def to_dict(self) -> dict:
        return asdict(self)


ALL_FIELDS = tuple(EvalRecord.__dataclass_fields__)
REQUIRED_FIELDS = tuple(f for f in ALL_FIELDS if f not in NEW_OPTIONAL_FIELDS)


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

    Every field is provenance ABOUT the artifact. None is derived by reading
    evaluation records, and `item_count` is PREDECLARED so metadata never
    requires parsing sealed content.
    """
    artifact_id: str
    canonical_path: str        # resolved, so symlinks and relative spellings
                               # collapse to one identity
    artifact_kind: str         # DEV_KIND | SEALED_KIND
    sha256: str
    schema_version: str
    item_count: int
    provenance: str

    def __post_init__(self):
        if self.artifact_kind not in (DEV_KIND, SEALED_KIND):
            raise ManifestError(f"artifact_kind {self.artifact_kind!r} invalid")


class ManifestError(ValueError):
    """The trusted manifest is malformed, conflicting, or unreadable."""


class ClassificationAuthority:
    """IMMUTABLE classification authority built from the trusted manifest.

    There is deliberately no `register`, no setter and no post-construction
    mutation: an authority cannot be edited after it is built, and ordinary
    code cannot construct a competing one through the supported API.
    """

    __slots__ = ("_by_path", "_by_id", "_manifest_sha256", "_manifest_version",
                 "_frozen")

    def __init__(self, registrations, *, manifest_sha256: str,
                 manifest_version: str):
        by_path, by_id = {}, {}
        for reg in registrations:
            key = str(Path(reg.canonical_path))
            # Conflicts are errors, never last-write-wins.
            prior = by_path.get(key)
            if prior is not None and prior != reg:
                raise ManifestError(
                    f"conflicting entries for path {key}: "
                    f"{prior.artifact_id}/{prior.artifact_kind} vs "
                    f"{reg.artifact_id}/{reg.artifact_kind}")
            prior_id = by_id.get(reg.artifact_id)
            if prior_id is not None and prior_id != reg:
                raise ManifestError(
                    f"artifact_id {reg.artifact_id!r} declared twice with "
                    f"different path/hash/kind")
            by_path[key], by_id[reg.artifact_id] = reg, reg
        object.__setattr__(self, "_by_path", MappingProxyType(by_path))
        object.__setattr__(self, "_by_id", MappingProxyType(by_id))
        object.__setattr__(self, "_manifest_sha256", manifest_sha256)
        object.__setattr__(self, "_manifest_version", manifest_version)
        object.__setattr__(self, "_frozen", True)

    def __setattr__(self, name, value):
        raise ManifestError(
            "the classification authority is immutable; artifact_kind, path "
            "identity and hash identity cannot be reassigned after loading")

    def __delattr__(self, name):
        raise ManifestError("the classification authority is immutable")

    @staticmethod
    def canonicalize(path) -> str:
        # resolve() collapses symlinks AND relative segments to one identity.
        return str(Path(path).resolve())

    def classify(self, path) -> tuple[str, ArtifactRegistration | None]:
        """(kind, registration). Unregistered or altered -> UNKNOWN, which refuses.

        Reads raw bytes to verify the registered hash. It never parses records.
        """
        canonical = self.canonicalize(path)
        reg = self._by_path.get(canonical)
        if reg is None:
            return UNKNOWN_KIND, None
        p = Path(canonical)
        if not p.is_file() or sha256_file(p) != reg.sha256:
            return UNKNOWN_KIND, None
        return reg.artifact_kind, reg

    @property
    def manifest_sha256(self) -> str:
        return self._manifest_sha256

    @property
    def manifest_version(self) -> str:
        return self._manifest_version

    def artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id))


TRUSTED_MANIFEST_SCHEMA = "trusted_artifacts_v3"
_MANIFEST_FIELDS = ("artifact_id", "canonical_path", "artifact_kind", "sha256",
                    "schema_version", "item_count", "provenance")

# Module-level authority. Built once, by the internal factory, from the trusted
# manifest. Ordinary dev/report code queries it and cannot replace it.
_AUTHORITY: ClassificationAuthority | None = None


def _build_authority_from_manifest(manifest_path) -> ClassificationAuthority:
    """INTERNAL trusted factory. Validates deterministically, then freezes.

    Rejects unknown schema, missing fields, and any conflicting entry. There is
    no last-write-wins path.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.is_file():
        raise ManifestError(f"trusted manifest not found: {manifest_path}")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if doc.get("schema") != TRUSTED_MANIFEST_SCHEMA:
        raise ManifestError(
            f"unsupported manifest schema {doc.get('schema')!r}; expected "
            f"{TRUSTED_MANIFEST_SCHEMA!r}")
    entries = doc.get("artifacts")
    if not isinstance(entries, list):
        raise ManifestError("manifest 'artifacts' must be a list")
    regs = []
    for e in entries:
        missing = [f for f in _MANIFEST_FIELDS if f not in e]
        if missing:
            raise ManifestError(f"manifest entry missing {missing}")
        extra = [k for k in e if k not in _MANIFEST_FIELDS]
        if extra:
            raise ManifestError(f"manifest entry carries unsupported {extra}")
        regs.append(ArtifactRegistration(**e))
    # Deterministic ordering, independent of manifest order.
    regs.sort(key=lambda r: (r.artifact_id, r.canonical_path))
    return ClassificationAuthority(
        regs, manifest_sha256=sha256_file(manifest_path),
        manifest_version=str(doc.get("version", "unversioned")))


def trusted_authority() -> ClassificationAuthority:
    """The classification authority for ordinary dev/report code.

    Read-only. Callers may QUERY classification; they cannot redefine it, and
    no supported dev API accepts an authority argument.
    """
    if _AUTHORITY is None:
        raise ManifestError(
            "no trusted artifact authority has been initialized; dev-facing "
            "loading is refused. Classification comes from the trusted "
            "manifest, never from the caller.")
    return _AUTHORITY


def _install_trusted_authority_for_fixtures(manifest_path):
    """FIXTURE/TEST-ONLY trusted initialization. NOT part of the dev API.

    Phase 8 validates the architecture with synthetic manifests under temporary
    paths, which requires a way to stand up a synthetic trusted environment.
    This underscore-prefixed hook is that mechanism and is used only by the
    Phase 8 gate.

    THREAT MODEL, stated accurately: this is a workflow-integrity and
    accidental-leakage boundary, not a sandbox against hostile code. Arbitrary
    Python with full module and filesystem access can always reach private
    names. What the design guarantees is narrower and is the property the
    protocol needs -- the NORMAL SUPPORTED dev/report API offers no route to
    reinterpret a sealed artifact as dev.
    """
    global _AUTHORITY
    _AUTHORITY = _build_authority_from_manifest(manifest_path)
    return _AUTHORITY


def load_dev_results(path) -> list[EvalRecord]:
    """Load an authorized DEV artifact.

    CLASSIFY BEFORE PARSE. Authorization is decided from the trusted authority
    before the file is parsed, so a sealed artifact's records are never read.

    There is deliberately NO authority parameter and NO `unseal` parameter. A
    caller cannot supply, replace or relabel the classification authority
    through this API, and no argument can turn a sealed artifact into a dev one.
    """
    authority = trusted_authority()      # internal; never caller-supplied
    kind, reg = authority.classify(path)  # before any record is parsed
    if kind == SEALED_KIND:
        raise SealError(
            f"artifact {reg.artifact_id!r} is classified SEALED by the trusted "
            f"authority; dev-facing loading is refused and no record was "
            f"parsed. Sealed results are readable only through the Phase 40 "
            f"unblind entry point, which does not exist yet.")
    if kind != DEV_KIND:
        raise SealError(
            "artifact is not a registered dev artifact (unregistered, moved, "
            "copied, or its bytes no longer match the registered hash). "
            "Classification fails closed: unknown is refused, never dev.")
    raw = [json.loads(l) for l in
           Path(reg.canonical_path).read_text(encoding="utf-8").splitlines()
           if l.strip()]
    if len(raw) != reg.item_count:
        raise SealError(
            f"artifact {reg.artifact_id!r} holds {len(raw)} records but the "
            f"trusted manifest predeclares {reg.item_count}")
    return [from_dict(r) for r in raw]


def sealed_metadata(path) -> dict:
    """Non-content integrity/provenance for a sealed artifact.

    It may read RAW BYTES to verify the registered SHA256, but it never parses
    or exposes evaluation-record content. Every returned value comes from the
    trusted manifest, so it cannot disclose families, conditions, statuses,
    scores, error types, questions, answers, SQL or execution results.
    `item_count` is the manifest's predeclared count, not a count of records.
    """
    authority = trusted_authority()
    kind, reg = authority.classify(path)
    if kind != SEALED_KIND:
        raise SealError(
            f"sealed_metadata is only defined for an artifact the trusted "
            f"authority classifies as sealed; this one classifies as {kind!r}")
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
    unknown = [k for k in d if k not in ALL_FIELDS]
    if unknown:
        raise RecordSchemaError(
            f"record carries unsupported field(s) {unknown}; the schema is "
            f"versioned ({RECORDS_VERSION}) and stale records must not be "
            f"silently accepted")
    d = dict(d)
    for f in NEW_OPTIONAL_FIELDS:
        d.setdefault(f, None)
    if d.get("parts") is not None:
        d["parts"] = tuple(d["parts"])
    return EvalRecord(**d)


def write_records(path, records: list[EvalRecord]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    return sha256_file(path)
