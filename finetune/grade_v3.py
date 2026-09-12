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

PHASE BOUNDARY -- MULTI-PART ENCODING WAS NOT FROZEN HERE. README fixes the
*semantics* ("multi-part questions require every part") but Phase 7 did not
freeze a serialization for how parts are declared or executed. Phase 9 has
since frozen both: `parts: [{part_id, answer_type, target_columns}]`
(`parts_list_v1`) and the execution/grading representation
(`multipart_result_v1`, see `grade_multipart` below) -- a part_id-keyed
collection of independently-executed, independently-typed per-part results,
not one shared rectangular table. `compare_results`'s original flattened
`multi_part` branch (each `target_columns` entry treated as one part of ONE
shared result) is kept EXACTLY as it was for any caller that invokes it
directly with a plain tuple of columns -- that is a different, lower-level
entry point than `grade_structured`/`grade_multipart`, so old and new callers
are naturally disjoint rather than needing an explicit legacy allowlist: a
caller that builds a `dict` `gold_sql` and goes through `grade_structured`
always gets the new keyed path and always requires real `parts` metadata
(fails closed if absent); a caller that calls `compare_results` directly with
a flat `target_columns` tuple is explicitly using the old, simpler contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlexec_v3 as X

GRADER_VERSION = "grade_v3.2_A002"

# Frozen answer types (README Phase 7).
ANSWER_TYPES = ("set", "scalar", "top_k", "multi_part")

# Frozen status vocabulary (CLAUDE.md 25). Exactly one per item.
STATUSES = ("correct", "incorrect", "generation_failure", "parse_failure",
            "SQL_error", "timeout", "truncated_output", "invalid_output")

MULTI_PART_ENCODING_NOTE = (
    "Phase 9 froze both the metadata serialization (parts_list_v1: "
    "parts=[{part_id, answer_type, target_columns}]) and the execution/"
    "grading representation (multipart_result_v1: gold_sql is a part_id-"
    "keyed dict of independently-normal SQL strings, each producing its own "
    "naturally-typed SQLResult; the model's prediction is a sequence of "
    "statements paired POSITIONALLY to parts[] order -- parts[] order is "
    "authoritative, predicted statement N belongs to declared part N). "
    "compare_results's original flattened multi_part branch (each "
    "target_columns entry as one part of ONE shared result) remains for "
    "direct callers using the older, simpler contract; grade_structured "
    "dispatches to the new grade_multipart path whenever gold_sql is a dict."
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


def grade_structured(item: dict, prediction_text, gold_sql, scope, *,
                     db_path=None, stopped_at_max_new_tokens: bool = False) -> GradeResult:
    """Grade one structured item. `gold_sql` is a single SQL string for an
    ordinary item, or a part_id-keyed dict for a multi_part item -- routed to
    `grade_multipart` automatically. Prediction and gold execute in ONE scope.

    Dispatch is keyed on `answer_type`, not merely on `gold_sql`'s type: a
    `multi_part` item MUST supply a dict `gold_sql` (and real `parts`
    metadata, enforced inside `grade_multipart`); a non-`multi_part` item MUST
    NOT supply a dict `gold_sql`. Reproduced as a live bug: an item declaring
    `answer_type="multi_part"` with a plain STRING `gold_sql` silently fell
    through to the ordinary single-query path (and its legacy flattened
    `compare_results` multi_part branch), completely bypassing the
    parts-required fail-closed check -- scoring 1.0/1.0 with no `parts`
    metadata ever validated.
    """
    declared_multipart = item.get("answer_type") == "multi_part"
    if declared_multipart and not isinstance(gold_sql, dict):
        raise GraderMetadataError(
            "answer_type is 'multi_part' but gold_sql is not a part_id-keyed "
            "dict -- fails closed rather than silently grading through the "
            "single-query path")
    if isinstance(gold_sql, dict) and not declared_multipart:
        raise GraderMetadataError(
            "gold_sql is a part_id-keyed dict but answer_type is not "
            "'multi_part' -- inconsistent task metadata")
    if isinstance(gold_sql, dict):
        return grade_multipart(
            item, prediction_text, gold_sql, scope, db_path=db_path,
            stopped_at_max_new_tokens=stopped_at_max_new_tokens)

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
    except TimeoutError as e:
        return GradeResult("timeout", 0.0, 0.0, f"execution timeout: {str(e)[:100]}")
    except (X.SQLPolicyError, Exception) as e:  # noqa: BLE001
        return GradeResult("SQL_error", 0.0, 0.0,
                           f"{type(e).__name__}: {str(e)[:120]}")

    X.assert_same_scope(pred_res, gold_res)
    return compare_results(pred_res, gold_res, answer_type, target_columns)


# ---------------------------------------------------------------------------
# Multi-part grading (multipart_result_v1) -- a part_id-keyed collection of
# independently-executed, independently-typed per-part results. No shared
# schema, no discriminator column, no casting: each part is graded through
# the existing, unmodified `compare_results` using its own answer_type/
# target_columns.
# ---------------------------------------------------------------------------
_NOISE_MASK_RE = re.compile(
    r"""
    --[^\n]*                     |
    /\*.*?\*/                    |
    '(?:[^']|'')*'                |
    "(?:[^"]|"")*"                |
    `(?:[^`]|``)*`                |
    \[[^\]]*\]
    """,
    re.VERBOSE | re.DOTALL,
)


def split_top_level_statements(sql: str) -> list[str]:
    """Split on top-level ';' using a comment/quote-aware scan, so a semicolon
    inside a string literal or comment is never mistaken for a statement
    boundary. An interior empty fragment (from ';;') is preserved as '' so the
    caller can classify it as an omitted/parse-failed part rather than it
    silently disappearing; a single trailing empty fragment (a lone final ';')
    is dropped."""
    mask = _NOISE_MASK_RE.sub(lambda m: "_" * len(m.group(0)), sql)
    raw, start = [], 0
    for i, ch in enumerate(mask):
        if ch == ";":
            raw.append(sql[start:i])
            start = i + 1
    raw.append(sql[start:])
    parts = [p.strip() for p in raw]
    while parts and parts[-1] == "":
        parts.pop()
    return parts


def grade_multipart(item: dict, prediction_text, gold_sql: dict, scope, *,
                    db_path=None, stopped_at_max_new_tokens: bool = False) -> GradeResult:
    """Grade one multi_part item against the multipart_result_v1 contract.

    Whole-response degeneracy (including truncation) is checked ONCE, before
    any statement-splitting or execution -- mirroring the single-query
    contract exactly ("partial or degenerate output is NEVER parsed or
    executed"): a truncated/degenerate response results in ZERO executor
    calls across every declared part.
    """
    parts_meta = item.get("parts")
    if not parts_meta:
        raise GraderMetadataError(
            "multi_part item is missing required 'parts' metadata -- fails "
            "closed rather than falling back to legacy per-column grading")
    part_ids = [p.get("part_id") for p in parts_meta]
    if len(part_ids) != len(set(part_ids)):
        raise GraderMetadataError(f"duplicate part_id(s) in declared parts: {part_ids}")

    # Each part's OWN metadata must pass the same validation a normal item
    # would -- reproduced as a live bug: a part with answer_type="set" and
    # target_columns=[] projected zero columns, making any two same-row-count
    # results compare equal regardless of actual values (999 scored "correct"
    # against gold 1). Validated up front, before any execution, exactly like
    # the single-query path validates item metadata before touching the
    # prediction.
    for p in parts_meta:
        try:
            validate_item_metadata(
                {"answer_type": p.get("answer_type"),
                 "target_columns": p.get("target_columns")})
        except GraderMetadataError as e:
            raise GraderMetadataError(
                f"part {p.get('part_id')!r}: {e}") from e

    status = classify_prediction_text(
        prediction_text, stopped_at_max_new_tokens=stopped_at_max_new_tokens)
    if status is not None:
        return GradeResult(
            status, 0.0, 0.0,
            f"{status}: prediction not parsed or executed (whole-response "
            f"check, before any part is split or any executor is called)")

    pred_statements = split_top_level_statements(str(prediction_text).strip())

    # (part_id, failure_status_or_None, detail, GradeResult_or_None)
    part_outcomes: list[tuple[str, str | None, str, GradeResult | None]] = []
    for i, p in enumerate(parts_meta):
        pid = p["part_id"]
        p_answer_type = p["answer_type"]
        p_target_columns = tuple(p["target_columns"])

        if i >= len(pred_statements) or not pred_statements[i]:
            part_outcomes.append((pid, "parse_failure",
                                  "omitted required statement", None))
            continue
        stmt = pred_statements[i]
        if not (stmt.lower().startswith("select") or stmt.lower().startswith("with")):
            part_outcomes.append((pid, "parse_failure",
                                  "statement is not a SELECT/WITH query", None))
            continue

        gold_part_sql = gold_sql.get(pid)
        if gold_part_sql is None:
            raise GraderMetadataError(
                f"gold_sql has no entry for declared part {pid!r}")
        try:
            pred_res, gold_res = X.execute_pair(stmt, gold_part_sql, scope,
                                                db_path=db_path)
        except X.ScopeError:
            raise
        except TimeoutError as e:
            part_outcomes.append((pid, "timeout",
                                  f"execution timeout: {str(e)[:100]}", None))
            continue
        except (X.SQLPolicyError, Exception) as e:  # noqa: BLE001
            part_outcomes.append((pid, "SQL_error",
                                  f"{type(e).__name__}: {str(e)[:120]}", None))
            continue

        X.assert_same_scope(pred_res, gold_res)
        gr = compare_results(pred_res, gold_res, p_answer_type, p_target_columns)
        part_outcomes.append((pid, None, gr.detail, gr))

    # Extra, undeclared statements beyond what parts[] declares: does not fail
    # task_result_correctness (each declared part is still graded on its own
    # terms), but does fail strict_result_schema_accuracy -- extends the
    # existing precedent that an extra column passes task_result_correctness
    # but fails strict_result_schema_accuracy.
    extra_present = any(s for s in pred_statements[len(parts_meta):])

    failing = [(pid, st, d) for pid, st, d, _ in part_outcomes if st is not None]
    if failing:
        # Deterministic: the FIRST failure by declared part order, not an
        # arbitrary one -- per-part detail is retained, never genericized.
        pid, st, d = failing[0]
        summary = "; ".join(
            f"{pid2}:{st2 if st2 else (gr2.status if gr2 else '?')}"
            for pid2, st2, _d2, gr2 in part_outcomes)
        return GradeResult(
            st, 0.0, 0.0,
            f"multi_part part {pid!r} failed with {st}: {d} (all parts: {summary})")

    all_correct = all(gr.status == "correct" for _, _, _, gr in part_outcomes)
    strict_ok = (all(gr.strict_result_schema_accuracy == 1.0
                     for _, _, _, gr in part_outcomes)
                and not extra_present)
    summary = "; ".join(f"{pid}:{gr.status}" for pid, _, _, gr in part_outcomes)
    detail = f"multi_part: {summary}"
    if extra_present:
        detail += " (extra undeclared statement(s) present -- fails strict schema only)"
    return GradeResult(
        "correct" if all_correct else "incorrect",
        1.0 if all_correct else 0.0,
        1.0 if strict_ok else 0.0,
        detail,
        {"answer_type": "multi_part", "parts": [pid for pid, _, _, _ in part_outcomes],
         # Retained so regrade() can reproduce the SAME strict-schema penalty
         # from retained evidence alone -- without this, regrading (which
         # never re-parses raw_output) could not know an extra statement had
         # been present at original grading time, and would silently drop
         # the penalty.
         "extra_present": extra_present})


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
        # A-002: a single returned cell has an unambiguous semantic value.
        # Aliases still affect the independently computed strict-schema score.
        if (answer_type == "scalar" and len(target_columns) == 1
                and len(pred_res.columns) == 1 and len(pred_res.rows) == 1
                and len(pred_res.rows[0]) == 1):
            pred_proj = list(pred_res.rows)
        else:
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
