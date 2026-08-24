"""Phase 7 -- task-aware grader with explicit failure statuses.

README Phase 7: every structured item carries `answer_type` and `target_columns`
**emitted by the generator**, never inferred at grading time. This module refuses
to guess: missing or invalid metadata is an explicit failure, never a fallback.

Nothing here is inferred from question wording, predicted SQL, gold SQL,
prediction contents, or gold result shape.

TWO DISTINCT METRICS
    task_result_correctness        primary   -- did the task get the right answer
    strict_result_schema_accuracy  secondary -- did the result also have the right shape
The secondary never substitutes for the primary; fixtures prove they differ.

THE v2 BUG THIS FIXES
    v2 finetune/grade.py:170  `if not gold_set and not pred_set: return 1.0`
An empty/refusal/noise/malformed prediction against an empty gold scored 1.0.
Here a degenerate prediction never reaches comparison: it is classified by its
own explicit status first.

SCOPE-PAIR INVARIANT. Grading executes prediction and gold through one scope
argument (sqlexec_v3.execute_pair). A mismatch raises before any score exists.

PHASE BOUNDARY -- MULTI-PART ENCODING IS NOT FROZEN HERE. README fixes the
*semantics* ("multi-part questions require every part") but does not freeze a
serialization for how parts are declared. This module therefore treats each
entry of `target_columns` as one required part, which is the minimal reading
that satisfies the frozen semantics, and does NOT establish a permanent
generator format. Phase 9/12 owns that decision; see MULTI_PART_ENCODING_NOTE.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import sqlexec_v3 as X

GRADER_VERSION = "grade_v3.0"

# Frozen answer types (README Phase 7).
ANSWER_TYPES = ("set", "scalar", "top_k", "multi_part")

# Frozen status vocabulary (CLAUDE.md 25). Exactly one per item.
STATUSES = ("correct", "incorrect", "generation_failure", "parse_failure",
            "SQL_error", "timeout", "truncated_output", "invalid_output")

MULTI_PART_ENCODING_NOTE = (
    "README freezes multi-part SEMANTICS (every required part must be correct) "
    "but not a serialization for declaring parts. This grader treats each entry "
    "of target_columns as one required part -- the minimal reading consistent "
    "with the frozen semantics. This is deliberately NOT a permanent generator "
    "format; freezing that representation belongs to the phase that owns task "
    "metadata, not to Phase 7."
)

# A scalar result must be a single scalar-compatible cell.
_SCALAR_OK = (int, float, str, bytes, type(None))


class GraderMetadataError(ValueError):
    """answer_type / target_columns missing or invalid. Never inferred."""


@dataclass(frozen=True)
class GradeResult:
    status: str
    task_result_correctness: float
    strict_result_schema_accuracy: float
    detail: str
    metrics: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"status {self.status!r} not in the frozen vocabulary")


def validate_item_metadata(item: dict) -> tuple[str, tuple[str, ...]]:
    """answer_type and target_columns must be SUPPLIED. Never inferred."""
    if not isinstance(item, dict):
        raise GraderMetadataError("item metadata must be a mapping")
    if "answer_type" not in item:
        raise GraderMetadataError(
            "answer_type is missing; it must be emitted by the generator and is "
            "never inferred from question text, SQL, or result shape")
    at = item["answer_type"]
    if at not in ANSWER_TYPES:
        raise GraderMetadataError(
            f"invalid answer_type {at!r}; valid: {', '.join(ANSWER_TYPES)}")
    if "target_columns" not in item:
        raise GraderMetadataError(
            "target_columns is missing; it must be emitted by the generator and "
            "is never inferred")
    tc = item["target_columns"]
    if (not isinstance(tc, (list, tuple)) or not tc
            or not all(isinstance(c, str) and c for c in tc)):
        raise GraderMetadataError(
            f"invalid target_columns {tc!r}; expected a non-empty list of column names")
    if at == "scalar" and len(tc) != 1:
        raise GraderMetadataError(
            f"answer_type 'scalar' requires exactly one target column, got {len(tc)}")
    return at, tuple(tc)


def _project(result: X.SQLResult, target_columns: tuple[str, ...]) -> list[tuple]:
    """Project the requested columns. A missing column is a schema failure, not
    a silent reprojection."""
    idx = []
    for col in target_columns:
        if col not in result.columns:
            raise KeyError(col)
        idx.append(result.columns.index(col))
    return [tuple(row[i] for i in idx) for row in result.rows]


# ---------------------------------------------------------------------------
# Degenerate-output classification. A degenerate prediction is classified by its
# OWN status before any comparison, so it can never coincide with an empty gold
# and score 1.0 -- the v2 failure this replaces.
# ---------------------------------------------------------------------------
_REFUSAL_MARKERS = ("i cannot", "i can't", "i am unable", "i'm unable",
                    "as an ai", "sorry", "cannot help", "unable to answer")


def classify_prediction_text(text, *, stopped_at_max_new_tokens: bool = False) -> str | None:
    """Return an explicit failure status, or None if the text should be parsed.

    `truncated_output` comes ONLY from explicit generation-stop metadata -- it is
    never inferred from what the text looks like.
    """
    if stopped_at_max_new_tokens:
        return "truncated_output"
    if text is None:
        return "generation_failure"
    if not isinstance(text, str) or not text.strip():
        return "generation_failure"
    low = text.strip().lower()
    if any(m in low for m in _REFUSAL_MARKERS):
        return "invalid_output"
    return None


def grade_structured(item: dict, prediction_text, gold_sql: str, scope, *,
                     db_path=None, stopped_at_max_new_tokens: bool = False) -> GradeResult:
    """Grade one structured item. Prediction and gold execute in ONE scope."""
    answer_type, target_columns = validate_item_metadata(item)

    status = classify_prediction_text(
        prediction_text, stopped_at_max_new_tokens=stopped_at_max_new_tokens)
    if status is not None:
        # Partial or degenerate output is NEVER parsed or executed.
        return GradeResult(status, 0.0, 0.0,
                           f"{status}: prediction not parsed or executed")

    pred_sql = str(prediction_text).strip()
    if not (pred_sql.lower().startswith("select") or pred_sql.lower().startswith("with")):
        return GradeResult("parse_failure", 0.0, 0.0,
                           "prediction is not a SELECT/WITH query")

    try:
        pred_res, gold_res = X.execute_pair(pred_sql, gold_sql, scope, db_path=db_path)
    except X.ScopeError:
        raise
    except (X.SQLPolicyError, Exception) as e:  # noqa: BLE001
        return GradeResult("SQL_error", 0.0, 0.0,
                           f"{type(e).__name__}: {str(e)[:120]}")

    X.assert_same_scope(pred_res, gold_res)
    return compare_results(pred_res, gold_res, answer_type, target_columns)


def compare_results(pred_res: X.SQLResult, gold_res: X.SQLResult,
                    answer_type: str, target_columns: tuple[str, ...]) -> GradeResult:
    """Frozen answer-type semantics. Never a generic set comparison for all types."""
    # strict schema: exact column tuple equality, computed independently of the
    # task-result metric so the two can genuinely disagree.
    strict = 1.0 if pred_res.columns == gold_res.columns else 0.0

    try:
        gold_proj = _project(gold_res, target_columns)
    except KeyError as e:
        return GradeResult("invalid_output", 0.0, strict,
                           f"gold result lacks target column {e}")
    try:
        pred_proj = _project(pred_res, target_columns)
    except KeyError as e:
        return GradeResult("incorrect", 0.0, strict,
                           f"prediction result lacks target column {e}")

    if answer_type == "set":
        ok = set(gold_proj) == set(pred_proj)          # project, then dedupe
        detail = (f"set: {len(set(pred_proj))} distinct predicted vs "
                  f"{len(set(gold_proj))} gold")
    elif answer_type == "scalar":
        if len(gold_proj) != 1:
            return GradeResult("invalid_output", 0.0, strict,
                               f"scalar gold must have exactly one row, got {len(gold_proj)}")
        if len(pred_proj) != 1:
            ok, detail = False, (f"scalar requires exactly one row, prediction "
                                 f"returned {len(pred_proj)}")
        elif not isinstance(pred_proj[0][0], _SCALAR_OK):
            ok, detail = False, "prediction value is not scalar-compatible"
        else:
            ok = pred_proj[0] == gold_proj[0]
            detail = f"scalar: {pred_proj[0][0]!r} vs {gold_proj[0][0]!r}"
    elif answer_type == "top_k":
        # order and length preserved; NEVER set-deduped
        ok = pred_proj == gold_proj
        detail = (f"top_k: length {len(pred_proj)} vs {len(gold_proj)}, "
                  f"order {'preserved' if ok else 'differs'}")
    elif answer_type == "multi_part":
        # Every required part must be present and correct. See
        # MULTI_PART_ENCODING_NOTE -- the encoding is provisional, the
        # every-part semantics are frozen.
        missing = []
        for i, col in enumerate(target_columns):
            g = {r[i] for r in gold_proj}
            p = {r[i] for r in pred_proj}
            if g != p:
                missing.append(col)
        ok = not missing
        detail = ("multi_part: all parts correct" if ok
                  else f"multi_part: {len(missing)}/{len(target_columns)} parts wrong "
                       f"({', '.join(missing)}) -- partial is not correct")
    else:  # unreachable: validate_item_metadata already gated this
        raise GraderMetadataError(f"unhandled answer_type {answer_type!r}")

    return GradeResult("correct" if ok else "incorrect",
                       1.0 if ok else 0.0, strict, detail,
                       {"answer_type": answer_type,
                        "target_columns": list(target_columns),
                        "pred_rows": pred_res.row_count,
                        "gold_rows": gold_res.row_count})
