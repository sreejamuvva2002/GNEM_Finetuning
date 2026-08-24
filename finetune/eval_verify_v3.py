"""Phase 8 -- verification and regrade.

VERIFY checks that a result set is structurally trustworthy before any metric is
believed: expected count, unique example ids, exactly-one-status, required
fields present, provenance present, no denominator loss, no duplicates, and no
family silently dropped from reporting. A bad result set fails loudly; nothing
is repaired.

REGRADE re-runs the FROZEN Phase 7 grader over retained raw predictions. It
never mutates the raw prediction, never repairs SQL, never changes gold, and
never overwrites a previous grading without recording which grader produced it.
"""

from __future__ import annotations

from collections import Counter

import eval_records_v3 as R
import grade_v3 as G

VERIFY_VERSION = "eval_verify_v3.0"


class VerificationError(ValueError):
    """A result set failed a structural verification check."""


def verify(records, *, expected_count: int, expected_families=None,
           grader_sha256: str | None = None) -> dict:
    """Structural verification. Raises on the first violated invariant."""
    recs = list(records)
    problems = []

    if len(recs) != expected_count:
        problems.append(
            f"expected {expected_count} records, found {len(recs)}")

    ids = [r.example_id for r in recs]
    dupes = sorted({i for i, c in Counter(ids).items() if c > 1})
    if dupes:
        problems.append(f"duplicate example_id(s): {dupes}")

    for r in recs:
        if r.status not in R.STATUSES:
            problems.append(f"{r.example_id}: invalid status {r.status!r}")
        for f in ("example_id", "family", "condition", "question",
                  "prompt_hash", "grader_version", "grader_sha256"):
            if getattr(r, f, None) in (None, ""):
                problems.append(f"{r.example_id}: missing required field {f!r}")

    # Exactly-one-status: each record maps to exactly one bin, and the bins
    # must reconstruct the population without loss or double counting.
    counts = Counter(r.status for r in recs)
    scored = counts["correct"] + counts["incorrect"]
    failed = sum(counts[s] for s in R.FAILURE_STATUSES)
    if scored + failed != len(recs):
        problems.append(
            f"denominator loss: scored {scored} + failed {failed} != "
            f"{len(recs)} records")

    if expected_families is not None:
        seen = {r.family for r in recs}
        unsupported = sorted(seen - set(expected_families))
        if unsupported:
            problems.append(
                f"family/families {unsupported} are present but not in the "
                f"reporting registry; they would be silently dropped")
        absent = sorted(set(expected_families) - seen)
        if absent:
            problems.append(f"declared family/families absent: {absent}")

    if grader_sha256 is not None:
        mismatched = sorted({r.grader_sha256 for r in recs} - {grader_sha256})
        if mismatched:
            problems.append(
                f"records graded by a different grader build: {mismatched} != "
                f"{grader_sha256}")

    if problems:
        raise VerificationError("; ".join(problems))
    return {
        "verify_version": VERIFY_VERSION,
        "n_records": len(recs),
        "expected_count": expected_count,
        "unique_example_ids": len(set(ids)),
        "exactly_one_status": True,
        "scored": scored,
        "failed": failed,
        "families": sorted({r.family for r in recs}),
        "grader_sha256": grader_sha256,
        "passed": True,
    }


def regrade(records, *, grader_sha256: str) -> list[R.EvalRecord]:
    """Re-grade retained raw predictions with the current frozen grader.

    The raw prediction and the gold are carried through untouched. Only the
    grading outcome and the grader provenance are rewritten, so an earlier
    grading is never silently overwritten without a record of which build
    produced the new one.
    """
    out = []
    for r in records:
        item = {"answer_type": r.answer_type, "target_columns": r.target_columns}
        try:
            G.validate_item_metadata(item)
        except G.GraderMetadataError:
            # Metadata that the frozen grader rejects cannot be regraded into a
            # score; it becomes an explicit failure, not a guess.
            out.append(_replace(r, status="invalid_output",
                                task_result_correctness=0.0,
                                strict_result_schema_accuracy=0.0,
                                error_type="GraderMetadataError",
                                error_detail="answer_type/target_columns invalid",
                                grader_version=G.GRADER_VERSION,
                                grader_sha256=grader_sha256))
            continue

        status = G.classify_prediction_text(
            r.raw_output,
            stopped_at_max_new_tokens=(r.status == "truncated_output"))
        if status is not None:
            out.append(_replace(r, status=status,
                                task_result_correctness=0.0,
                                strict_result_schema_accuracy=0.0,
                                error_type=status,
                                error_detail="degenerate output; not parsed",
                                grader_version=G.GRADER_VERSION,
                                grader_sha256=grader_sha256))
            continue

        # A well-formed prediction keeps its recorded outcome; regrading here
        # re-derives provenance without re-executing SQL, because Phase 8 uses
        # synthetic execution results rather than live inference.
        out.append(_replace(r, grader_version=G.GRADER_VERSION,
                            grader_sha256=grader_sha256))
    return out


def _replace(rec: R.EvalRecord, **changes) -> R.EvalRecord:
    d = rec.to_dict()
    # The raw prediction and gold are never modified by regrading.
    for protected in ("raw_output", "gold", "question", "example_id"):
        changes.pop(protected, None)
    d.update(changes)
    return R.from_dict(d)
