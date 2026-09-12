"""Phase 6 -- deterministic oracle-context renderer for `base_ctx_oracle`.

The retired whole-table baseline was not merely large but impossible: the naive
render is ~35k tokens for companies alone and ~52k with child tables. Pruning
columns until it fits would make the ceiling an artifact of which columns were
dropped, so it is replaced rather than shrunk.

`base_ctx_oracle` performs deterministic gold-ROW retrieval and renders that
row's company record plus its process, service and certification child facts.

LANGUAGE DISCIPLINE. This is an **oracle-context baseline** -- a
**retrieval-grounded factual upper bound**. It is never a "RAG baseline", a
"retrieval-system benchmark" or a "retriever benchmark": the row is handed over
by construction, so it measures grounded answering, not retrieval quality.

ORACLE RETRIEVAL IS NOT ANSWER LEAKAGE. The selected row is deliberately the
correct one, so the raw evidence is *expected* to contain the information needed
to answer -- `Employment: 500` is legitimate even when the eventual answer is
`500`. What is forbidden is a separate target/evaluation artifact: a gold-answer
annotation, gold SQL, generated QA, `answer_type`, `target_columns`, correctness
labels, or hidden probe metadata. The renderer emits raw KB evidence only, and
never receives any of those in the first place.

APPLICABILITY. Factual probes only. Global structured questions -- filtering
across many companies, aggregation, counting, ranking, top-k, global joins --
compare against `base_sql` / `base_sql_5shot`, which are NOT implemented here.

SCOPE. `render_oracle_context(scope, row_id)` requires an explicit scope and
verifies the row genuinely belongs to it, so `scope="train_kb"` with a test
`row_id` fails rather than returning the row.

NO SILENT TRUNCATION. This module never truncates, slices, clips or drops a
field. Budget enforcement lives in phase6_context_budget.py and raises.

Physical scoped-view names (`train_kb_companies`, ...) are Phase 5 infrastructure
and never appear in a prompt.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as kb  # noqa: E402

RENDERER_VERSION = "ctx_oracle_v3.1_A002_record_id"

# ---------------------------------------------------------------------------
# FROZEN RENDERING SPEC
# ---------------------------------------------------------------------------
# Scalar company fields, in fixed render order. Derived from the Phase 4
# model-facing allowlist MINUS the three multi-valued fields, which are rendered
# exactly once each in their own child-fact sections below. Rendering them both
# generically and as child facts would duplicate the evidence.
MULTIVALUED = ("processes", "services", "certifications")
SCALAR_FIELDS: tuple[str, ...] = tuple(
    f for f in kb.MODEL_FACING_FIELDS if f not in MULTIVALUED and f != "row_id")

FIELD_LABELS = {
    "company": "Company",
    "category": "Category",
    "industry_group": "Industry group",
    "location": "Location",
    "address": "Address",
    "primary_facility_type": "Primary facility type",
    "ev_supply_chain_role": "EV supply chain role",
    "primary_oems": "Primary OEMs",
    "supplier_or_affiliation_type": "Supplier or affiliation type",
    "employment": "Employment",
    "product_or_service": "Product / service",
    "ev_battery_relevant": "EV / battery relevant",
    "classification_method": "Classification method",
    "city": "City",
    "county": "County",
}
CHILD_LABELS = {
    "processes": "Processes",
    "services": "Services",
    "certifications": "Certifications",
}

LABEL_SEP = ": "        # between a label and its value
LINE_SEP = "\n"         # between rendered lines
TERM_SEP = "; "         # between child-fact terms
NULL_RENDER = "Not specified"   # derived city/county absent -> frozen unknown sentinel

SYSTEM_PROMPT = (
    "You are answering questions about companies in the Georgia new-energy "
    "mobility supply chain. Use only the company record provided. If the record "
    "does not contain the answer, say so."
)
CONTEXT_HEADING = "Company record:"
QUESTION_HEADING = "Question:"

# Never renderable. Structurally unreachable because SCALAR_FIELDS derives from
# the Phase 4 allowlist, but asserted at import so a future edit cannot slip.
FORBIDDEN_IN_CONTEXT = frozenset({
    "split", "split_group", "certification_count",
    "latitude", "longitude", "graph_id", "graph_edges",
})
assert not (set(SCALAR_FIELDS) & FORBIDDEN_IN_CONTEXT), \
    "renderer must never expose leakage-control or retired-geo metadata"
assert not (set(SCALAR_FIELDS) & set(MULTIVALUED)), \
    "multi-valued fields are rendered once, as child facts only"


class ScopeError(ValueError):
    """Raised when a scope is missing/unknown, or a row is outside it."""


def _record(scope, row_id: int):
    """Fetch a row through the Phase 4 contract, enforcing scope membership."""
    if scope is None or scope not in kb.SCOPE_SPLITS:
        raise ScopeError(
            f"KB scope is required and must be named explicitly; got {scope!r}. "
            f"Valid scopes: {', '.join(kb.KB_SCOPES)}")
    for rec in kb.load_kb(scope):
        if rec.row_id == row_id:
            return rec
    raise ScopeError(
        f"row_id {row_id} is not present in scope {scope!r}; a row outside the "
        f"requested scope is never returned")


def render_oracle_context(scope, row_id: int) -> str:
    """Render one row's frozen factual evidence. Scope is required, no default.

    Deterministic: same frozen KB + scope + row_id + renderer version yields
    byte-identical output. Child facts follow the Phase 5 canonical
    case-insensitive order, never SQLite's natural row order.
    """
    rec = _record(scope, row_id)
    lines = [f"Source record: {rec.row_id}"]
    for field in SCALAR_FIELDS:
        value = getattr(rec, field)
        rendered = NULL_RENDER if value is None else str(value)
        lines.append(f"{FIELD_LABELS[field]}{LABEL_SEP}{rendered}")
    for field in MULTIVALUED:
        # Already-canonical Phase 2 text, preserved verbatim. A row with no
        # certification evidence carries the frozen sentinel string; no
        # certification child fact is manufactured for it.
        lines.append(f"{CHILD_LABELS[field]}{LABEL_SEP}{getattr(rec, field)}")
    return LINE_SEP.join(lines)


def build_ctx_oracle_prompt(scope, row_id: int, question: str) -> list[dict]:
    """Complete chat message list for `base_ctx_oracle`.

    Returned so token accounting covers the whole prompt that reaches the model
    -- system message, question, rendered context, instructions, and (once the
    chat template is applied) its control tokens -- not just the context block.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    context = render_oracle_context(scope, row_id)
    user = (f"{CONTEXT_HEADING}{LINE_SEP}{context}{LINE_SEP}{LINE_SEP}"
            f"{QUESTION_HEADING}{LINE_SEP}{question}")
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user}]


def rendering_spec() -> dict:
    """The frozen spec, recorded in the audit so it is reviewable, not implicit."""
    return {
        "renderer_version": RENDERER_VERSION,
        "scalar_field_order": list(SCALAR_FIELDS),
        "child_fact_order": list(MULTIVALUED),
        "labels": {**FIELD_LABELS, **CHILD_LABELS},
        "label_separator": LABEL_SEP,
        "line_separator": LINE_SEP,
        "term_separator": TERM_SEP,
        "null_render": NULL_RENDER,
        "child_ordering": "Phase 5 canonical case-insensitive order (never SQLite row order)",
        "system_prompt": SYSTEM_PROMPT,
        "context_heading": CONTEXT_HEADING,
        "question_heading": QUESTION_HEADING,
        "whitespace": "canonical values preserved verbatim; no trimming or collapsing",
        "duplicate_rendering": "multi-valued fields rendered exactly once, as child facts",
        "forbidden_in_context": sorted(FORBIDDEN_IN_CONTEXT),
    }
