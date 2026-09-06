"""Phase 8 -- verification and regrade.

VERIFY checks that a result set is structurally trustworthy before any metric is
believed: expected count, unique example ids, exactly-one-status, required
fields present, provenance present, no denominator loss, no duplicates, and no
family silently dropped from reporting. A bad result set fails loudly; nothing
is repaired.

REGRADE re-runs the FROZEN Phase 7 grader over retained raw predictions. It
never mutates the raw prediction, never repairs SQL, never changes gold, and
never overwrites a previous grading without recording which grader produced it.

RETAINED-EVIDENCE SHAPE (Phase 9 correction). `execution_result`/`gold` on an
EvalRecord for a structured (non-multipart) item are `None`, or
`{"columns": [str, ...], "rows": [[...], ...]}` -- enough to reconstruct the
actual `SQLResult` objects `compare_results` needs, including any EXTRA
columns beyond `target_columns` (needed for `strict_result_schema_accuracy`
to mean anything on regrade -- a target_columns-only projection would make
every regraded item trivially schema-correct). For a `multi_part` item, both
are `None` or `{"parts": {part_id: {"columns": [...], "rows": [...]}}}`,
mirroring `grade_v3`'s `multipart_result_v1` representation.

INSUFFICIENT-EVIDENCE REGRADING (Phase 9 correction, D.21). A record whose
retained evidence can't support recomputation (no execution_result/gold, or a
part missing from a multi_part record's retained parts) is never silently
reclassified. Its `status`, both scores, `grader_version` and `grader_sha256`
are left BYTE-IDENTICAL to what they were -- regrade only sets a separate,
NON-AUTHORITATIVE `regrade_outcome: "insufficient_evidence"` field. A record's
provenance must never claim to originate from a grader that never actually
evaluated it. `assert_fully_regraded` below is the consumer-side gate: it is a
strict WHITELIST (every record must show `regrade_outcome == "recomputed"`
AND the expected `grader_sha256`), not a blacklist of one known-bad value, so
a record that was simply never regraded (`regrade_outcome is None`) cannot
silently pass either.
"""

from __future__ import annotations

from collections import Counter

import eval_records_v3 as R
import grade_v3 as G
import sqlexec_v3 as X

VERIFY_VERSION = "eval_verify_v3.1"


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


def _sql_result_from_retained(payload) -> X.SQLResult | None:
    """Reconstruct an X.SQLResult from retained {"columns":..., "rows":...}.
    No SQL is re-executed -- this is a pure structural rehydration of
    evidence retained at ORIGINAL grading time."""
    if not payload or "columns" not in payload or "rows" not in payload:
        return None
    return X.SQLResult(columns=tuple(payload["columns"]),
                       rows=tuple(tuple(row) for row in payload["rows"]),
                       scope="retained", row_count=len(payload["rows"]))


def regrade(records, *, grader_sha256: str) -> list[R.EvalRecord]:
    """Re-grade retained raw predictions with the current frozen grader.

    The raw prediction and the gold are carried through untouched (enforced
    by `_replace`'s whitelist, not a best-effort blacklist). Never re-executes
    SQL or re-runs the model -- Phase 8 uses synthetic execution results
    rather than live inference, and this is a pure re-verification pass over
    retained evidence.
    """
    out = []
    for r in records:
        if r.answer_type == "multi_part":
            out.append(_regrade_multipart(r, grader_sha256))
        else:
            out.append(_regrade_single(r, grader_sha256))
    return out


def _regrade_single(r: R.EvalRecord, grader_sha256: str) -> R.EvalRecord:
    item = {"answer_type": r.answer_type, "target_columns": r.target_columns}
    try:
        G.validate_item_metadata(item)
    except G.GraderMetadataError:
        # Metadata that the frozen grader rejects cannot be regraded into a
        # score; it becomes an explicit failure, not a guess. Derivable purely
        # from metadata -- genuinely recomputed, no execution_result needed.
        return _replace(r, status="invalid_output",
                        task_result_correctness=0.0,
                        strict_result_schema_accuracy=0.0,
                        error_type="GraderMetadataError",
                        error_detail="answer_type/target_columns invalid",
                        grader_version=G.GRADER_VERSION,
                        grader_sha256=grader_sha256,
                        regrade_outcome="recomputed")

    status = G.classify_prediction_text(
        r.raw_output,
        stopped_at_max_new_tokens=(r.status == "truncated_output"))
    if status is not None:
        # Derivable purely from retained raw_output/stop-metadata -- genuinely
        # recomputed, no execution_result needed either.
        return _replace(r, status=status,
                        task_result_correctness=0.0,
                        strict_result_schema_accuracy=0.0,
                        error_type=status,
                        error_detail="degenerate output; not parsed",
                        grader_version=G.GRADER_VERSION,
                        grader_sha256=grader_sha256,
                        regrade_outcome="recomputed")

    pred_res = _sql_result_from_retained(r.execution_result)
    gold_res = _sql_result_from_retained(r.gold)
    if pred_res is None or gold_res is None:
        # Never relabel a historical score as newly recomputed when the
        # evidence needed to recompute it is absent. status/scores/grader
        # provenance stay byte-identical -- only regrade_outcome changes.
        return _replace(r, regrade_outcome="insufficient_evidence")

    gr = G.compare_results(pred_res, gold_res, r.answer_type, tuple(r.target_columns))
    return _replace(r, status=gr.status,
                    task_result_correctness=gr.task_result_correctness,
                    strict_result_schema_accuracy=gr.strict_result_schema_accuracy,
                    error_type=None if gr.status == "correct" else gr.status,
                    error_detail=gr.detail,
                    grader_version=G.GRADER_VERSION,
                    grader_sha256=grader_sha256,
                    regrade_outcome="recomputed")


def _regrade_multipart(r: R.EvalRecord, grader_sha256: str) -> R.EvalRecord:
    status = G.classify_prediction_text(
        r.raw_output,
        stopped_at_max_new_tokens=(r.status == "truncated_output"))
    if status is not None:
        return _replace(r, status=status,
                        task_result_correctness=0.0,
                        strict_result_schema_accuracy=0.0,
                        error_type=status,
                        error_detail="degenerate output; not parsed "
                                    "(whole-response check)",
                        grader_version=G.GRADER_VERSION,
                        grader_sha256=grader_sha256,
                        regrade_outcome="recomputed")

    if not r.parts:
        return _replace(r, regrade_outcome="insufficient_evidence")

    pred_parts = (r.execution_result or {}).get("parts", {}) \
        if isinstance(r.execution_result, dict) else {}
    gold_parts = (r.gold or {}).get("parts", {}) if isinstance(r.gold, dict) else {}

    outcomes = []
    for p in r.parts:
        pid = p["part_id"]
        pred_res = _sql_result_from_retained(pred_parts.get(pid))
        gold_res = _sql_result_from_retained(gold_parts.get(pid))
        if pred_res is None or gold_res is None:
            outcomes.append((pid, None))
            continue
        gr = G.compare_results(pred_res, gold_res, p["answer_type"],
                               tuple(p["target_columns"]))
        outcomes.append((pid, gr))

    if any(gr is None for _, gr in outcomes):
        # ANY part lacking retained evidence makes the whole item
        # not-genuinely-recomputable -- never partially recompute and call it
        # verified.
        return _replace(r, regrade_outcome="insufficient_evidence")

    all_correct = all(gr.status == "correct" for _, gr in outcomes)
    strict_ok = all(gr.strict_result_schema_accuracy == 1.0 for _, gr in outcomes)
    summary = "; ".join(f"{pid}:{gr.status}" for pid, gr in outcomes)
    return _replace(r, status="correct" if all_correct else "incorrect",
                    task_result_correctness=1.0 if all_correct else 0.0,
                    strict_result_schema_accuracy=1.0 if strict_ok else 0.0,
                    error_type=None if all_correct else "incorrect",
                    error_detail=f"regraded multi_part: {summary}",
                    grader_version=G.GRADER_VERSION,
                    grader_sha256=grader_sha256,
                    regrade_outcome="recomputed")


# Whitelist, not a blacklist: regrade may ONLY ever change these fields.
# Anything else (raw_output, gold, execution_result, question, example_id,
# parts, target_columns, answer_type, ...) is structurally protected because
# it is simply never accepted as a change key.
_REGRADE_MUTABLE_FIELDS = frozenset((
    "status", "task_result_correctness", "strict_result_schema_accuracy",
    "error_type", "error_detail", "grader_version", "grader_sha256",
    "regrade_outcome",
))


def _replace(rec: R.EvalRecord, **changes) -> R.EvalRecord:
    bad = [k for k in changes if k not in _REGRADE_MUTABLE_FIELDS]
    if bad:
        raise ValueError(
            f"regrade attempted to change protected field(s) {bad}; only "
            f"{sorted(_REGRADE_MUTABLE_FIELDS)} may ever be rewritten by regrade")
    d = rec.to_dict()
    d.update(changes)
    return R.from_dict(d)


def assert_fully_regraded(records, *, expected_grader_sha256: str) -> None:
    """Strict whitelist gate: EVERY record must show
    regrade_outcome == 'recomputed' AND grader_sha256 == the current expected
    build. Raises on 'insufficient_evidence', on None (never regraded), and on
    a 'recomputed' record stamped by a DIFFERENT (stale) grader build.

    Call this before any report labels its output "freshly regraded" / "fully
    re-verified under the current grader" -- it is the only thing standing
    between a report and silently certifying a claim it can't back.
    """
    bad = []
    for r in records:
        if r.regrade_outcome != "recomputed":
            bad.append((r.example_id, r.regrade_outcome))
        elif r.grader_sha256 != expected_grader_sha256:
            bad.append((r.example_id, f"stale grader {r.grader_sha256}"))
    if bad:
        raise VerificationError(
            f"{len(bad)} record(s) are not fully regraded under the current "
            f"grader ({expected_grader_sha256}): {bad[:10]}")


def regrade_coverage(records) -> dict:
    """Reporting-only breakdown, never a pass/fail gate by itself. Every
    record is counted in exactly one bucket; nothing is dropped."""
    recs = list(records)
    counts = Counter(r.regrade_outcome for r in recs)
    return {
        "recomputed": counts.get("recomputed", 0),
        "insufficient_evidence": counts.get("insufficient_evidence", 0),
        "not_yet_regraded": counts.get(None, 0),
        "total": len(recs),
    }
