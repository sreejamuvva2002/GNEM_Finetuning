"""Phase 9 -- the frozen holdout policy, and the exposure scanner every dataset
phase must run.

FROZEN 2026-08-24 by explicit user authorization, after a read-only decision
analysis, and REVISED the same day (v3.0 -> v3.1) after independent review --
see POLICY_REVISION below. The parameters below are pre-registration: v3.0 was
fixed before any training dataset existed, which is the property README
Phase 9 exists to protect ("If holdouts are chosen after seeing the generated
data, the holdout that gets picked is the one the data happens to support").
Accurate chronology, corrected after independent audit (this file previously
said "fixed before any training dataset existed" without qualification, which
became imprecise once Phase 10 was briefly generated and reverted): v3.0 was
frozen before any training dataset existed; Phase 10 (`train_A_cpt_v3.jsonl`)
was then generated from v3.0 and fully reverted; v3.1 was frozen after that,
before any training dataset was ever built from the corrected registry. No
model training or evaluation ever used v3.0-derived data. Git history is not
rewritten -- the original commit messages remain as they were, accurate to
what was true when written.

SUPPORT-UNIT PROVENANCE (frozen interpretation)
    README Phase 21's candidate table -- 26 process / 13 service / 8
    certification -- is reproduced by ROW-OCCURRENCE support, verified cell by
    cell against the frozen KB. `supporting_companies` is reported separately as
    exact trimmed company counts (README:700). The distinction is deliberate and
    is never hidden: eligibility uses rows, collateral reporting carries both.

COMPOSITIONAL COLLATERAL (frozen interpretation)
    For a held-out component set H, collateral means excluding structured tasks
    whose component set T satisfies H subset-of T. It does NOT mean hiding either
    individual component literal from A/B/C/D. An unseen COMBINATION is not an
    unseen VALUE; a component stays independently train-visible unless that
    literal is separately selected on the VALUE axis.

OPERATION AXIS AT PHASE 9 (frozen interpretation)
    Phase 12's real task pool does not exist yet, so Phase 9 freezes the
    operation definitions, held-out constructs, metadata semantics, exposure
    detection rules and axis applicability, and validates them on synthetic
    fixtures. Phase 12 later applies this frozen policy to the real pool.

TEST BLINDING
    Phase 9 uses the frozen train/dev/test assignment and KB-derived support
    counts to establish eligibility, which the protocol requires. It reads no
    model prediction, no accuracy, no error analysis and no Q42 content.
    TEST_STATUS remains LOCKED_UNTIL_PHASE_40.

CORRECTION HISTORY (post-v3.1, registry/code hardening -- selected values and
selection algorithm UNCHANGED throughout)
    Independent audit found real gaps in the supporting code and registry
    completeness, none of which touch `select_values`/`select_composition`:
    an "allowed operations per field" contract required by README was absent;
    the operation-construct detector could be evaded by lexical tricks like
    `GROUP/**/BY`; the registry loader trusted any file on disk with no
    provenance check; `scan_strings` mis-scanned a bare string as a character
    iterable; the zero-exposure assertion could pass vacuously; the logical
    fingerprint omitted `logical_components`, colliding AND/OR predicates; a
    dict passed to the exposure scanners was silently scanned by its keys
    instead of its values. All are corrected below; see `PHASE9_CORRECTION`.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "datasets_v3" / "canonical_records_v3.jsonl"
SPLITS = ROOT / "datasets_v3" / "company_split_groups_v3.csv"
REGISTRY = ROOT / "datasets_v3" / "HOLDOUT_REGISTRY_A002.json"
PHASE9_APPROVAL = ROOT / "datasets_v3" / "PHASE9_AUTHORIZATION_A002.json"

FROZEN_INPUT_PATHS = (
    "datasets_v3/canonical_records_v3.jsonl",
    "datasets_v3/company_split_groups_v3.csv",
    "datasets_v3/gnem_v3.sqlite",
)
README_ROW_BAND_TABLE = {"processes": 26, "services": 13, "certifications": 8}

POLICY_VERSION = "holdout_v3.2_A002"
FROZEN_DATE = "2026-09-11"

MULTIVALUED = ("processes", "services", "certifications")
CERT_SENTINEL = "None identified after search"

# --------------------------------------------------------------------------
# FROZEN SCIENTIFIC CONFIGURATION (user-approved 2026-08-24)
# --------------------------------------------------------------------------
SUPPORT_UNIT = "row_occurrences"      # eligibility; companies reported alongside
SUPPORT_BAND = (3, 15)                # README:684 "minimum support 3 ... 3-15 band"
# All three split minima are mandatory. A candidate failing ANY of them is
# ineligible; eligibility is the ONLY role split support plays.
MIN_TRAIN_SUPPORT = 2
MIN_DEV_SUPPORT = 1
MIN_TEST_SUPPORT = 1

# TEST SUPPORT IS ELIGIBILITY-ONLY. Once a candidate clears the minima above,
# test support plays NO part in ranking -- not as objective, not as tie-break.
# Selecting holdouts to maximise test support would optimise the pre-registration
# against test-side properties of the KB, which weakens the blinding posture even
# though no model outcome is involved. The objective below is decided purely on
# TRAIN-side collateral, so the choice is test-blind by construction.
SELECTION_OBJECTIVE = "minimize union of train rows losing the attribute"
SELECTION_TIE_BREAKS = (
    "minimize union of exact train companies affected",
    "maximize total dev support (sum of per-value dev ROW support)",
    "lexicographically smallest sorted canonical value tuple",
)
TIE2_DEV_SUPPORT_DEFINITION = (
    "sum over selected values of that value's dev ROW-occurrence support; a "
    "summed count, deliberately not a union, so a value adding dev breadth is "
    "rewarded even when it shares dev rows with another selected value")
COVERAGE_FLOOR_PCT = 85.0             # README:712 "at least X%" -- X frozen here
PER_VALUE_COVERAGE_THRESHOLD_PCT = 85.0   # README:706, one knob not two
HOLDOUT_COUNTS = {"processes": 0, "services": 0, "certifications": 0}

# Operation axis. README Phase 22's validation requires all three defining
# constructs to appear 0 times in training gold, so all three are held out.
# Exactly ONE operation_family per task, assigned by this precedence; a task
# matching more than one held-out family is excluded from training entirely
# (fail closed) so the zero-occurrence assertion stays unambiguous.
OPERATION_PRECEDENCE = ("argmax_topk", "group_by", "limit_only")
HELD_OUT_OPERATIONS = ("argmax_topk", "group_by", "limit_only")
OPERATION_CONSTRUCTS = {
    "argmax_topk": ("ORDER BY", "LIMIT"),   # both present
    "group_by": ("GROUP BY",),
    "limit_only": ("LIMIT",),               # without ORDER BY
}

# Compositional axis: arity 2, one held-out pair, deterministic by lowest train
# support then lexicographic.
COMPOSITION_ARITY = 2
COMPOSITION_FAMILIES = (("processes", "services"),
                        ("processes", "certifications"),
                        ("services", "certifications"))
COMPOSITION_MIN_TRAIN_ROWS = 20
COMPOSITION_MIN_TEST_ROWS = 10
COMPOSITION_HOLDOUT_COUNT = 1

# logical_fingerprint_v2 (lfp1 -> lfp2, correction: lfp1 omitted
# logical_components, so an AND-predicate task and an OR-predicate task over
# the same fields/values collided to the same fingerprint. lfp2 folds a
# canonicalized logical_components into the hash: commutative operands (AND/OR
# operands) sort before hashing so reordering doesn't change the fingerprint;
# the operator and any differing predicate/value still change it.
FINGERPRINT_VERSION = "lfp2"
FINGERPRINT_SEMANTIC_FIELDS = ("operation_family", "fields_used", "values_used",
                               "target_columns", "answer_type", "join_arity",
                               "required_constructs", "entity_dependent",
                               "logical_components")
COMMUTATIVE_LOGICAL_OPERATORS = ("AND", "OR")

# answer_type / target_columns conventions. Phase 7 froze the four semantics;
# Phase 9 freezes the multi-part SERIALIZATION that Phase 7 deferred.
ANSWER_TYPES = ("set", "scalar", "top_k", "multi_part")
MULTI_PART_SERIALIZATION = "parts_list_v1"
MULTI_PART_NOTE = (
    "A multi_part task carries parts: [{part_id, answer_type, target_columns}], "
    "and `target_columns` remains the flattened ordered union so the frozen "
    "Phase 7 grader keeps working unchanged. Phase 7's stand-in treated each "
    "target column as one part, which cannot express a multi-part question whose "
    "parts are different OPERATIONS (a count and a set); this serialization can. "
    "The grading/execution REPRESENTATION for a rendered multi_part task is "
    "frozen separately as MULTIPART_RESULT_REPRESENTATION below: a part_id-keyed "
    "collection of independently-executed, independently-typed per-part "
    "results -- not one shared rectangular table.")
MULTIPART_RESULT_REPRESENTATION_VERSION = "multipart_result_v1"
MULTIPART_RESULT_NOTE = (
    "gold_sql for a multi_part task is a dict keyed by part_id, one "
    "independently normal SQL string per declared part, each executed on its "
    "own producing its own natural SQLResult (own columns, own types, own row "
    "count). The model's predicted SQL is a sequence of statements, split on "
    "top-level ';' with the same comment/quote-aware lexer used for operation "
    "detection, paired positionally: predicted statement N belongs to declared "
    "part N (parts[] order is authoritative). Every declared part is required; "
    "an omitted statement is a parse_failure for that part. Grading calls the "
    "existing, unmodified compare_results once per declared part -- no shared "
    "schema, no discriminator column, no casting.")

# --------------------------------------------------------------------------
# Allowed operations per field (README Phase 9: "allowed operations per
# field" is a required freeze item; it was absent from the registry until
# this correction). Four explicit layers, not a single field->ops map:
#   1. field_semantic_operations   -- meaningful for the field, INCLUDING
#      held-out operations where they make sense (needed by the Phase 22
#      operation-heldout probe, which must be able to construct exactly
#      these operations for evaluation).
#   2. query_level_constructs      -- the three held-out families themselves,
#      tagged as structural/query-shape operations rather than field
#      properties (limit_only is field-agnostic).
#   3. field_specific_restrictions -- named exceptions sourced verbatim from
#      README, not invented.
#   4. field_training_eligible_operations (derived) = layer 1 minus
#      HELD_OUT_OPERATIONS, a literal set difference on the SAME vocabulary
#      as HELD_OUT_OPERATIONS (no softer synonyms like "ranking" for
#      "argmax_topk" -- that mismatch would silently defeat the subtraction).
# This map is a candidate-generation-time heuristic; the authoritative
# training-eligibility gate is always the real SQL-construct scanner
# (operation_families_present) run against a task's actual rendered gold_sql.
# --------------------------------------------------------------------------
QUERY_LEVEL_CONSTRUCTS = frozenset(HELD_OUT_OPERATIONS)

FIELD_SEMANTIC_OPERATIONS = {
    # companies table
    "category": {"filter", "aggregation", "group_by"},
    "industry_group": {"filter", "aggregation", "group_by"},
    "location": {"filter"},
    "address": {"filter"},                                  # README:538
    "primary_facility_type": {"filter", "aggregation", "group_by"},
    "ev_supply_chain_role": {"filter", "aggregation", "group_by"},
    "primary_oems": {"filter"},                              # README:537-538
    "supplier_or_affiliation_type": {"filter", "aggregation", "group_by"},
    "employment": {"filter", "aggregation", "argmax_topk"},
    "product_or_service": {"semantic_filter"},
    "ev_battery_relevant": {"filter", "aggregation"},
    "classification_method": {"filter", "aggregation"},
    "city": {"filter", "aggregation", "group_by"},
    "county": {"filter", "aggregation", "group_by"},
    "row_id": {"join", "filter"},
    "company": {"filter"},
    # child tables
    "certifications": {"filter", "aggregation", "group_by"},
    "processes": {"filter", "aggregation", "group_by"},
    "services": {"filter", "aggregation", "group_by"},
}

FIELD_SPECIFIC_RESTRICTIONS = {
    "primary_oems": {
        "excludes": ["group_by", "argmax_topk"],
        "basis": ("README:537-538 -- `Primary OEMs` excluded from group-by and "
                  "ranking; composite strings like `Hyundai Kia Rivian`"),
    },
    "address": {
        "excludes": ["aggregation", "group_by", "argmax_topk"],
        "basis": "README:538 -- `Address` gets no structured aggregation",
    },
    "row_id": {
        "conditional": {
            "filter": ("only when the question explicitly names a record "
                      "(README:541-543); join is unconditionally allowed"),
        },
        "basis": ("README:541-543 -- SQL may join on row_id, but gold SQL must "
                  "not filter by row_id unless the question explicitly names a "
                  "record, otherwise the model learns an artificial "
                  "record-index shortcut"),
    },
}


def field_training_eligible_operations() -> dict:
    """Layer 4, derived mechanically: semantic ops minus the globally held-out
    families. Machine-testable equation, not a name-based heuristic."""
    return {f: sorted(ops - QUERY_LEVEL_CONSTRUCTS)
            for f, ops in FIELD_SEMANTIC_OPERATIONS.items()}


def allowed_operations_per_field_section() -> dict:
    return {
        "field_semantic_operations": {f: sorted(ops) for f, ops
                                      in FIELD_SEMANTIC_OPERATIONS.items()},
        "query_level_constructs": sorted(QUERY_LEVEL_CONSTRUCTS),
        "field_specific_restrictions": FIELD_SPECIFIC_RESTRICTIONS,
        "field_training_eligible_operations": field_training_eligible_operations(),
        "taxonomy_provenance": (
            "traced against every operation-shaped mention in README Phases "
            "12, 14, 18-26, 41 ('aggregation' and 'join' are the document's "
            "own words -- README:264,539,541); independently cross-checked "
            "against v2-frozen-reference:finetune/taxonomy.py, which uses "
            "FILTER_LIST, AGGREGATE (count/sum/group-by/argmax/top-k) and "
            "SEMANTIC_FILTER for free-text columns -- the two sources "
            "converge on the same core names."),
        "basis": ("candidate-generation-time heuristic; the authoritative "
                  "training-eligibility gate is always the real SQL-construct "
                  "scanner (operation_families_present) run against a task's "
                  "actual rendered gold_sql, not this map"),
    }


POLICY_REVISION = {
    "version": "holdout_v3.1",
    "supersedes": "holdout_v3.0",
    "date": "2026-08-24",
    "changed": [
        "split minima: dev >= 1 added and made mandatory alongside train >= 2 "
        "and test >= 1",
        "selection objective: 'maximise total test support' replaced by "
        "'minimize union of train rows losing the attribute'",
        "tie-breaks: now (1) minimize union of exact train companies, "
        "(2) maximize summed dev support, (3) lexicographic tuple",
        "test support demoted to eligibility-only; it can no longer influence "
        "ranking",
        "candidate-pool terminology split into initial_row_band_candidate_count "
        "and post_split_filter_eligible_count",
    ],
    "why": (
        "Selecting holdouts to maximise test support optimises the "
        "pre-registration against test-side properties of the KB. No model "
        "outcome is involved, so it was not a blinding breach, but it is "
        "test-informed selection and a weaker posture than deciding purely on "
        "train-side collateral. The revised objective is test-blind by "
        "construction and also cheaper: union train-row loss falls from 17 to 6 "
        "(processes), 11 to 2 (services)."),
    "provenance_note": (
        "v3.0 implemented the configuration approved in the decision-analysis "
        "round, which specified 'maximise total test support' with minima "
        "train>=2/test>=1 and no dev minimum. v3.1 is therefore a deliberate "
        "POLICY REVISION directed after independent review, not a correction of "
        "an implementation that had deviated from its approval. Both facts are "
        "recorded so the pre-registration history stays accurate."),
    "effect_on_selection": (
        "processes and services selections changed; certifications changed "
        "because ISO 22301 and OHSAS 18001 both have dev_support 0 and are "
        "ineligible under the mandatory dev minimum"),
}

PHASE9_CORRECTION = {
    "corrects": "holdout_v3.1 (selected values and selection algorithm UNCHANGED)",
    "date": "2026-09-06",
    "registry_schema_revision": "phase9_registry_schema_r2",
    "changed": [
        "added allowed_operations_per_field (README-required, previously absent)",
        "operation-construct detection: comment/quote-aware lexer replacing raw "
        "substring matching (closes a GROUP/**/BY-style evasion)",
        "registry loading: two-function split -- "
        "load_candidate_registry_for_phase9_audit() (recompute-and-compare, "
        "usable pre-approval) and load_registry() (requires an external "
        "PHASE9_AUTHORIZATION_A002.json anchor, raises Phase9NotApproved otherwise)",
        "registry wrapper is deeply immutable (stores canonical JSON text, "
        "every accessor returns a fresh parse)",
        "scan_strings/scan_operations/scan_compositions: list-only, raise on a "
        "bare str/dict instead of silently mis-iterating it",
        "exposure-report assertions: three typed functions "
        "(assert_value_scan_verified/assert_operation_scan_verified/"
        "assert_composition_scan_verified), each requiring real scan evidence "
        "(a nonzero scanned-count), not just total_exposures == 0",
        "exposure normalization: NFKC compatibility-normalize + casefold + "
        "whitespace-collapse (NFC alone does not fold fullwidth Unicode forms)",
        "logical_fingerprint: lfp1 -> lfp2, folds canonicalized "
        "logical_components into the hash (closes an AND/OR collision)",
        "scan_operations_multipart / scan_compositions_multipart: scan every "
        "part of a multi-part task, not a dict's keys (a live, reproduced bug "
        "in the original multi-part design) and check compositional holdouts "
        "against the whole task's component union, not per part",
    ],
    "why": (
        "Independent audit found real gaps in the supporting code and "
        "registry completeness. None touch select_values/select_composition; "
        "the nine selected holdout values and the v3.1 objective/tie-breaks "
        "are unchanged. Full independent recomputation (a standalone script "
        "importing nothing from this module) confirmed the same nine values "
        "are still optimal under the frozen objective after these fixes."),
}


class HoldoutError(ValueError):
    """A holdout policy invariant was violated."""


class Phase9NotApproved(HoldoutError):
    """load_registry() refuses to serve the registry to production code until
    a separate, externally-recorded approval anchor exists."""


class RegistryTamperError(HoldoutError):
    """The current registry does not match its recorded approval anchor."""


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def terms(value, field) -> list[str]:
    """Canonical terms of a multi-valued field. The certification sentinel is
    zero credential evidence, never a term."""
    if not value or (field == "certifications" and value == CERT_SENTINEL):
        return []
    return [t for t in value.split("; ") if t]


def load_kb():
    recs = [json.loads(l) for l in CANONICAL.read_text(encoding="utf-8").splitlines()]
    with SPLITS.open(encoding="utf-8") as fh:
        split = {int(r["row_id"]): r["split"] for r in csv.DictReader(fh)}
    return recs, split


def support_tables(recs, split):
    """Row-occurrence and exact-company support, per split. Both units, always."""
    rows = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    cos = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    train_rows = defaultdict(lambda: defaultdict(set))
    train_cos = defaultdict(lambda: defaultdict(set))
    for r in recs:
        s = split[r["row_id"]]
        for f in MULTIVALUED:
            for t in set(terms(r[f], f)):
                rows[f][t][s] += 1
                rows[f][t]["ALL"] += 1
                cos[f][t][s].add(r["company"])
                cos[f][t]["ALL"].add(r["company"])
                if s == "train":
                    train_rows[f][t].add(r["row_id"])
                    train_cos[f][t].add(r["company"])
    return rows, cos, train_rows, train_cos


def attribute_totals(recs, split):
    """Train-side denominators: rows/companies carrying the attribute at all."""
    tr = {f: sum(1 for r in recs if split[r["row_id"]] == "train" and terms(r[f], f))
          for f in MULTIVALUED}
    tc = {f: len({r["company"] for r in recs if split[r["row_id"]] == "train"
                  and terms(r[f], f)}) for f in MULTIVALUED}
    return tr, tc


def row_band_candidates(rows, field) -> list[str]:
    """Stage 1: the INITIAL row-support 3-15 candidate pool.

    This is the pool README Phase 21 publishes as 26 process / 13 service /
    8 certification. Split minima are NOT applied here -- they are stage 2.
    """
    lo, hi = SUPPORT_BAND
    return sorted(v for v in rows[field] if lo <= rows[field][v]["ALL"] <= hi)


def eligible_values(rows, field) -> list[str]:
    """Stage 2: candidates surviving the mandatory split minima.

    Reported separately from the stage-1 pool so a post-filter count is never
    mistaken for README's published row-band figure.
    """
    return sorted(v for v in row_band_candidates(rows, field)
                  if rows[field][v]["train"] >= MIN_TRAIN_SUPPORT
                  and rows[field][v]["dev"] >= MIN_DEV_SUPPORT
                  and rows[field][v]["test"] >= MIN_TEST_SUPPORT)


def select_values(rows, train_rows, totals, field, train_cos=None) -> tuple[str, ...]:
    """Deterministic, TEST-BLIND selection.

        PRIMARY   minimize |union(train rows losing the attribute)|
        TIE 1     minimize |union(exact train companies affected)|
        TIE 2     maximize total dev support (sum of per-value dev row support)
        TIE 3     lexicographically smallest sorted canonical value tuple

    Test support established eligibility and plays no part here.
    """
    pool = eligible_values(rows, field)
    k = HOLDOUT_COUNTS[field]
    if len(pool) < k:
        raise HoldoutError(
            f"{field}: post-split-filter eligible pool {len(pool)} < requested {k}")
    best = None
    for combo in itertools.combinations(pool, k):
        lost = set().union(*(train_rows[field][v] for v in combo))
        cov = 100.0 * (totals[field] - len(lost)) / totals[field]
        if cov < COVERAGE_FLOOR_PCT:
            continue
        cos = (len(set().union(*(train_cos[field][v] for v in combo)))
               if train_cos else 0)
        key = (len(lost), cos, -sum(rows[field][v]["dev"] for v in combo),
               tuple(sorted(combo)))
        if best is None or key < best[0]:
            best = (key, tuple(sorted(combo)))
    if best is None:
        raise HoldoutError(
            f"{field}: no {k}-combination satisfies the {COVERAGE_FLOOR_PCT}% floor")
    return best[1]


def select_composition(recs, split) -> tuple[str, ...]:
    """Lowest train support, then lexicographic. Both components must remain
    independently train-visible (README Phase 23)."""
    def has(r, f):
        return bool(terms(r[f], f))
    scored = []
    for pair in COMPOSITION_FAMILIES:
        rws = [r for r in recs if all(has(r, c) for c in pair)]
        tr = sum(1 for r in rws if split[r["row_id"]] == "train")
        ts = sum(1 for r in rws if split[r["row_id"]] == "test")
        if tr < COMPOSITION_MIN_TRAIN_ROWS or ts < COMPOSITION_MIN_TEST_ROWS:
            continue
        scored.append((tr, tuple(sorted(pair))))
    if len(scored) < COMPOSITION_HOLDOUT_COUNT:
        raise HoldoutError("no compositional pair meets the support minima")
    scored.sort()
    return scored[0][1]


# --------------------------------------------------------------------------
# Operation-construct detection -- comment/quote-aware, not raw substring
# matching. Correction: raw substring matching on whitespace-collapsed SQL
# text could be evaded by a lexical trick like `GROUP/**/BY` (the comment is
# invisible to SQLite's own lexer, so it still executes as a real GROUP BY).
# Fix: replace (never delete) every comment/string-literal/quoted-identifier
# span with a single space -- preserving token boundaries, so
# `GROUP/**/BY` becomes `GROUP BY` (detected), not `GROUPBY` (silently
# reconcatenated, which would just move the bug rather than fix it) -- then
# apply keyword-boundary regex to what remains.
# --------------------------------------------------------------------------
_SQL_NOISE_RE = re.compile(
    r"""
    --[^\n]*                     |   # line comment
    /\*.*?\*/                    |   # block comment
    '(?:[^']|'')*'                |   # single-quoted string literal ('' escape)
    "(?:[^"]|"")*"                |   # double-quoted string/identifier ("" escape)
    `(?:[^`]|``)*`                |   # backtick-quoted identifier
    \[[^\]]*\]                        # bracket-quoted identifier
    """,
    re.VERBOSE | re.DOTALL,
)
_GROUP_BY_RE = re.compile(r"\bGROUP\s+BY\b", re.IGNORECASE)
_ORDER_BY_RE = re.compile(r"\bORDER\s+BY\b", re.IGNORECASE)
_LIMIT_RE = re.compile(r"\bLIMIT\b", re.IGNORECASE)


def _strip_sql_noise(sql: str) -> str:
    """Replace comments/literals/quoted-identifiers with a single space each."""
    return _SQL_NOISE_RE.sub(" ", sql)


def classify_operation(sql: str) -> str:
    """Exactly one operation_family, by frozen precedence."""
    u = _strip_sql_noise(sql)
    has_group = bool(_GROUP_BY_RE.search(u))
    has_limit = bool(_LIMIT_RE.search(u))
    has_order = bool(_ORDER_BY_RE.search(u))
    if has_order and has_limit:
        return "argmax_topk"
    if has_group:
        return "group_by"
    if has_limit:
        return "limit_only"
    return "filter"


def operation_families_present(sql: str) -> set[str]:
    """Every held-out family whose defining construct is present. More than one
    means the task is excluded from training entirely (fail closed)."""
    u = _strip_sql_noise(sql)
    out = set()
    has_group = bool(_GROUP_BY_RE.search(u))
    has_limit = bool(_LIMIT_RE.search(u))
    has_order = bool(_ORDER_BY_RE.search(u))
    if has_order and has_limit:
        out.add("argmax_topk")
    if has_group:
        out.add("group_by")
    if has_limit and not has_order:
        out.add("limit_only")
    return out


# --------------------------------------------------------------------------
# Logical fingerprint -- lfp2. Correction: lfp1 omitted logical_components, so
# an AND-of-two-predicates task and an OR-of-the-same-two-predicates task
# collided to the same fingerprint. lfp2 canonicalizes logical_components:
# commutative operands (AND/OR) sort before hashing so reordering doesn't
# change identity; the operator and any differing predicate/value do.
# --------------------------------------------------------------------------
def _validate_logical_components(node) -> None:
    """An incomplete/ambiguous logical_components tree must fail closed, not
    silently hash. Reproduced as live bugs: {} and {"op":"AND"} (no operands)
    both previously produced a fingerprint instead of raising."""
    if not isinstance(node, dict) or not node:
        raise HoldoutError(
            "logical_components node is empty or not a mapping -- fails "
            "closed rather than hashing an incomplete logical structure")
    op = node.get("op")
    if op is None:
        raise HoldoutError("logical_components node is missing required 'op'")
    if op in COMMUTATIVE_LOGICAL_OPERATORS:
        operands = node.get("operands")
        if not isinstance(operands, (list, tuple)) or not operands:
            raise HoldoutError(
                f"logical_components: '{op}' requires a non-empty 'operands' "
                f"list -- fails closed rather than hashing an AND/OR with no "
                f"actual operands")
        for o in operands:
            _validate_logical_components(o)
    else:
        # A comparison-predicate leaf requires BOTH 'field' and 'value' -- not
        # merely ">= 2 keys total". Reproduced as a live bug:
        # {"op": "eq", "field": "county"} (no 'value') passed the old ">= 2
        # keys" check and still produced a fingerprint for a predicate that
        # can never actually be evaluated (an equality with nothing to
        # compare against). This is a stated implementation choice, not a
        # frozen protocol requirement: every leaf predicate this repository
        # currently represents needs both a field and a value, so both are
        # required uniformly rather than defining a per-operator schema for
        # predicate shapes the protocol has not itself enumerated.
        missing = [k for k in ("field", "value") if k not in node]
        if missing:
            raise HoldoutError(
                f"logical_components leaf node with op={op!r} is missing "
                f"required field(s) {missing} -- fails closed rather than "
                f"hashing a predicate that could never actually be evaluated")


def _canon_logical_components(node):
    if isinstance(node, dict):
        op = node.get("op")
        operands = node.get("operands")
        if op in COMMUTATIVE_LOGICAL_OPERATORS and isinstance(operands, (list, tuple)):
            canon_operands = sorted(
                (_canon_logical_components(o) for o in operands),
                key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
            return {"op": op, "operands": canon_operands}
        return {k: _canon_logical_components(v) for k, v in sorted(node.items())}
    if isinstance(node, (list, tuple)):
        return [_canon_logical_components(x) for x in node]
    return node


def logical_fingerprint(task: dict) -> str:
    """Semantic identity, insensitive to wording, formatting, aliases, ids and
    commutative predicate reordering. Missing OR incomplete logical_components
    fails closed rather than silently hashing a weaker skeleton."""
    canon = {}
    for f in FINGERPRINT_SEMANTIC_FIELDS:
        v = task.get(f)
        if f == "logical_components":
            if v is None:
                raise HoldoutError(
                    "logical_fingerprint: task is missing required "
                    "'logical_components' -- fails closed rather than hashing "
                    "a weaker skeleton that could collide AND with OR")
            _validate_logical_components(v)
            v = _canon_logical_components(v)
        elif isinstance(v, (list, tuple, set)):
            v = sorted(str(x) for x in v)
        canon[f] = v
    blob = json.dumps(canon, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return f"{FINGERPRINT_VERSION}:{hashlib.sha256(blob.encode()).hexdigest()[:32]}"


# --------------------------------------------------------------------------
# Registry construction -- the deterministic pipeline, called both by the
# Phase 9 freeze script (to WRITE the registry) and by the verified loader
# below (to INDEPENDENTLY RECOMPUTE it for comparison against what's on
# disk). Living in one place means "recompute from frozen inputs via the
# unmodified selection pipeline" is literally true, not aspirational.
# --------------------------------------------------------------------------
def build_registry_bundle():
    """Everything needed to assemble the registry dict, plus the intermediate
    tables the Phase 9 freeze script also needs for its cost-CSV/audit report."""
    recs, split = load_kb()
    rows, cos, train_rows, train_cos = support_tables(recs, split)
    tot_rows, tot_cos = attribute_totals(recs, split)

    selected = {f: select_values(rows, train_rows, tot_rows, f, train_cos=train_cos)
                for f in MULTIVALUED}
    comp = select_composition(recs, split)

    ent = {"train": sorted({r["company"] for r in recs if split[r["row_id"]] == "train"}),
           "dev": sorted({r["company"] for r in recs if split[r["row_id"]] == "dev"}),
           "test": sorted({r["company"] for r in recs if split[r["row_id"]] == "test"})}

    per_field = {}
    for f in MULTIVALUED:
        lost = set().union(*(train_rows[f][v] for v in selected[f]))
        lost_co = set().union(*(train_cos[f][v] for v in selected[f]))
        cov = 100.0 * (tot_rows[f] - len(lost)) / tot_rows[f]
        cov_co = 100.0 * (tot_cos[f] - len(lost_co)) / tot_cos[f]
        band = row_band_candidates(rows, f)
        elig = eligible_values(rows, f)
        per_field[f] = {
            "train_rows_total": tot_rows[f], "train_companies_total": tot_cos[f],
            "train_rows_lost": len(lost), "train_companies_lost": len(lost_co),
            "remaining_attribute_coverage_rows_pct": round(cov, 2),
            "remaining_attribute_coverage_companies_pct": round(cov_co, 2),
            "initial_row_band_candidate_count": len(band),
            "post_split_filter_eligible_count": len(elig),
            "post_split_filter_eligible_values": elig,
        }

    registry = {
        "registry": "HOLDOUT_REGISTRY_v3",
        "phase": 9,
        "policy_version": POLICY_VERSION,
        "frozen_date": FROZEN_DATE,
        "frozen_by": "explicit user authorization after read-only decision analysis",
        "policy_revision": POLICY_REVISION,
        "phase9_correction": PHASE9_CORRECTION,
        "timestamp_note": ("the authoritative freeze timestamp is the git commit "
                           "date; a runtime timestamp is deliberately not embedded "
                           "because it would break the determinism gate"),
        "frozen_inputs": {k: sha256_file(ROOT / k) for k in FROZEN_INPUT_PATHS},
        "support_unit_provenance": {
            "eligibility_unit": SUPPORT_UNIT,
            "readme_initial_row_band_candidate_table": README_ROW_BAND_TABLE,
            "stage_note": ("README's 26/13/8 is the STAGE-1 row-band pool. The "
                           "post-split-filter eligible pool is smaller and is "
                           "reported separately per attribute; the two are never "
                           "conflated under one name."),
            "reproduced_by": "row-occurrence support (verified cell-by-cell)",
            "supporting_companies_unit": "exact trimmed company names",
            "note": ("README's frozen 26/13/8 table is reproduced by ROW-OCCURRENCE "
                     "support; `supporting_companies` separately reports exact "
                     "trimmed company counts (README:700). The distinction is "
                     "recorded, never hidden."),
        },
        "parameters": {
            "support_band": list(SUPPORT_BAND),
            "min_train_support": MIN_TRAIN_SUPPORT,
            "min_dev_support": MIN_DEV_SUPPORT,
            "min_test_support": MIN_TEST_SUPPORT,
            "split_minima_role": ("eligibility ONLY; once a candidate clears the "
                                  "minima, split support plays no part in ranking"),
            "attribute_coverage_floor_pct": COVERAGE_FLOOR_PCT,
            "per_value_coverage_threshold_pct": PER_VALUE_COVERAGE_THRESHOLD_PCT,
            "holdout_counts": HOLDOUT_COUNTS,
            "selection_objective": SELECTION_OBJECTIVE,
            "tie_breaks": list(SELECTION_TIE_BREAKS),
            "tie2_dev_support_definition": TIE2_DEV_SUPPORT_DEFINITION,
            "test_support_role": ("eligibility only -- never an objective and "
                                  "never a tie-break. Optimising selection on "
                                  "test support would tune the pre-registration "
                                  "against test-side properties of the KB; the "
                                  "objective is decided purely on train-side "
                                  "collateral and is test-blind by construction"),
        },
        "entity_holdouts": {
            "source": "frozen Phase 3 split; nothing re-decided here",
            "counts": {k: len(v) for k, v in ent.items()},
            "dev_companies": ent["dev"], "test_companies": ent["test"],
        },
        "value_holdouts": {
            f: {"selected": list(selected[f]), **per_field[f]}
            for f in MULTIVALUED
        },
        "operation_holdouts": {
            "held_out_families": list(HELD_OUT_OPERATIONS),
            "precedence": list(OPERATION_PRECEDENCE),
            "constructs": {k: list(v) for k, v in OPERATION_CONSTRUCTS.items()},
            "basis": ("README Phase 22 requires GROUP BY, LIMIT and argmax/top-k to "
                      "appear 0 times in training gold, so all three are held out"),
            "multi_family_rule": ("exactly one operation_family per task by "
                                  "precedence; a task matching more than one "
                                  "HELD-OUT family is excluded from training "
                                  "entirely (fail closed)"),
            "detection": ("comment/quote-aware lexer over the actual rendered "
                          "SQL text -- comments and string/identifier literals "
                          "are replaced with a single space (never deleted) "
                          "before keyword-boundary matching, so a lexical trick "
                          "like GROUP/**/BY cannot evade detection"),
            "applied_to_real_pool_at": "Phase 12",
        },
        "composition_holdouts": {
            "arity": COMPOSITION_ARITY,
            "families": [list(p) for p in COMPOSITION_FAMILIES],
            "held_out_sets": [list(comp)],
            "superset_rule": "for held-out H and training set T: assert not H subset-of T",
            "multipart_note": ("for a multi-part task, T is the UNION of every "
                              "declared part's component usage, not each part "
                              "checked in isolation -- a multi-part task is one "
                              "logical training item"),
            "collateral_scope": ("structured-task exclusion only. Individual "
                                 "component literals remain independently "
                                 "train-visible unless separately selected on the "
                                 "VALUE axis. An unseen COMBINATION is not an "
                                 "unseen VALUE."),
            "min_train_rows": COMPOSITION_MIN_TRAIN_ROWS,
            "min_test_rows": COMPOSITION_MIN_TEST_ROWS,
        },
        "allowed_operations_per_field": allowed_operations_per_field_section(),
        "answer_type_conventions": {
            "answer_types": list(ANSWER_TYPES),
            "frozen_by": "Phase 7 grade_v3 semantics",
            "target_columns": "non-empty ordered list[str]; scalar requires exactly 1",
            "multi_part_serialization": MULTI_PART_SERIALIZATION,
            "multi_part_note": MULTI_PART_NOTE,
            "multipart_result_representation_version": MULTIPART_RESULT_REPRESENTATION_VERSION,
            "multipart_result_note": MULTIPART_RESULT_NOTE,
        },
        "logical_fingerprint": {
            "version": FINGERPRINT_VERSION,
            "semantic_fields": list(FINGERPRINT_SEMANTIC_FIELDS),
            "excluded": ["question wording", "SQL formatting", "alias spelling",
                         "column order", "example_id", "dataset path", "split",
                         "split_group", "condition", "seed"],
            "canonicalisation": ("json sort_keys, separators (,:), lists sorted; "
                                 "logical_components: commutative (AND/OR) "
                                 "operands sorted before hashing, operator and "
                                 "differing predicates/values still distinguish"),
            "construction": "lfp2: + sha256(canonical utf-8)[:32]",
        },
        "fewshot_eligibility": {
            "rule": "fail closed -- unprovable eligibility means ineligible",
            "conditions": [
                "every referenced row is train-side",
                "contains no held-out value literal anywhere",
                "operation_family not held out and no held-out construct present",
                "component set C contains no held-out set H (not H subset-of C)",
                "logical_fingerprint collides with no probe item",
                "no held-out entity literal",
                "any shipped schema text or value catalogue is filtered to "
                "training-visible values",
                "eligibility is checked on FINAL RENDERED chat messages",
            ],
        },
        "exposure_policy": {
            "invariant": "exposure_count == 0 for every held-out item, every arm",
            "arms": ["A", "B", "C", "D", "BC", "BD"],
            "scan_point": ("final rendered strings, after chat-template "
                           "rendering, system-prompt and catalogue insertion, "
                           "few-shot insertion and target rendering"),
            "surfaces": ["cpt_passages", "system_prompts", "user_messages",
                         "assistant_targets", "sql_text", "schema_text",
                         "value_catalogues", "fewshot_text",
                         "combined_renderings", "repeat_renderings"],
            "scope_boundary": ("applies to model-visible FINE-TUNING text only. "
                              "The shared runtime value catalogue used by "
                              "baselines (base_sql, base_sql_5shot) at INFERENCE "
                              "legitimately contains every value, held-out "
                              "included, per this same policy -- the scanner "
                              "must never be run against that catalogue and "
                              "must never flag it as a violation"),
            "normalization": ("NFKC compatibility-normalize, casefold, collapse "
                              "internal whitespace, then substring match -- NFC "
                              "alone does not fold fullwidth Unicode forms "
                              "(verified: NFC('ＡＳ９１００') != 'AS9100', "
                              "NFKC(...) == 'AS9100'). Biased toward "
                              "over-detection: a false positive costs one extra "
                              "row to inspect, a false negative is an actual leak."),
            "report_schemas": {
                "value_scan": ["exposure_counts", "total_exposures",
                              "strings_scanned", "hits"],
                "operation_scan": ["operation_exposure_counts", "total_exposures",
                                   "sql_scanned"],
                "composition_scan": ["composition_violations", "violations",
                                     "sets_scanned"],
                "verified_states": ["pending (scanned:false, count:null)",
                                    "verified-zero (scanned:true, evidence "
                                    "counter > 0, exposure_count 0, internally "
                                    "consistent)", "exposure-detected (fails)",
                                    "malformed (fails)"],
            },
            "omit_policy": ("omit the item, never truncate the truth -- A omits the "
                            "whole field from that row's passage, B generates no QA "
                            "for that (company, attribute), C/D emit no structured "
                            "supervision using the value"),
        },
    }
    # A-002 supersedes only the deliberate value-withholding axis.
    registry["registry"] = "HOLDOUT_REGISTRY_A002"
    registry["policy_revision"] = {"amendment": "PROTOCOL_A002_FULL_FIELD.md",
        "authorization": "User requested full-field original V3; Certification Count excluded",
        "historical_policy": "holdout_v3.1",
        "timing": "After historical datasets, before V3 model training or evaluation"}
    registry["frozen_by"] = "User-authorized amendment; agent implementation and automated validation"
    registry["timestamp_note"] = "Policy date; no claim of a newly approved Git commit"
    registry["parameters"].update({"selection_objective": "No deliberate value withholding under A-002",
        "tie_breaks": [], "value_support_rules": "Historical diagnostics only; no values selected"})
    registry["exposure_policy"]["omit_policy"] = (
        "No value-based omissions. Complete training-record observations, missingness and conflicts "
        "must be supervised. Certification Count stays internal. Company holdouts remain excluded.")
    registry["exposure_policy"]["value_axis_status"] = "disabled_under_A002_not_evidence_of_unseen_values"
    registry["coverage_policy"] = {"required": "all training source observations",
        "source_field_exception": ["certification_count"], "missingness": "source-qualified",
        "conflicts": "record-scoped observations with explicit uncertainty",
        "phase21": "exposure-stratified value probe, no deliberately withheld literals"}
    return (recs, split, rows, cos, train_rows, train_cos, tot_rows, tot_cos,
            selected, comp, ent, per_field, registry)


def recompute_registry_dict() -> dict:
    """Independent recomputation entry point for the verified loader below."""
    return build_registry_bundle()[-1]


# --------------------------------------------------------------------------
# Registry loading -- two APIs with genuinely different guarantees.
#
#   load_candidate_registry_for_phase9_audit()  -- usable BEFORE approval.
#       Recomputes the whole registry from the frozen inputs via the
#       unmodified selection pipeline above and compares it field-for-field
#       to the committed file, plus schema/upstream-hash checks. This is what
#       --check, fault tests and synthetic validation use.
#
#   load_registry()  -- the production / Phase-10+ entry point. Requires the
#       candidate checks above to pass AND a separate, externally-recorded
#       approval anchor (PHASE9_AUTHORIZATION_A002.json) to exist and match. Raises
#       Phase9NotApproved if the anchor is absent -- it never returns a
#       partially-usable object with a pending flag. A file inside the same
#       writable repo is not a cryptographic guarantee; this is a separately
#       reviewed approval record anchored to the reviewed commit, not more.
#
# Both return a VerifiedCandidateRegistry: deeply immutable (stores canonical
# JSON text; every accessor returns a fresh parse), so a caller mutating a
# returned section can never corrupt the stored original.
# --------------------------------------------------------------------------
REQUIRED_REGISTRY_SECTIONS = (
    "registry", "phase", "policy_version", "frozen_date", "frozen_inputs",
    "parameters", "entity_holdouts", "value_holdouts", "operation_holdouts",
    "composition_holdouts", "allowed_operations_per_field",
    "answer_type_conventions", "logical_fingerprint", "fewshot_eligibility",
    "exposure_policy",
)


# Capability token: only `_load_and_verify_candidate` (below) holds a
# reference to it, so `VerifiedCandidateRegistry(text)` cannot be constructed
# directly without deliberately importing this private, leading-underscore
# module attribute. Stated plainly: this is a naming/friction convention, not
# a language-enforced guarantee -- Python cannot make direct construction
# impossible, only conspicuous misuse.
_VERIFICATION_TOKEN = object()


class VerifiedCandidateRegistry:
    """Deeply-immutable registry handle. Stores only the canonical JSON text;
    every read parses a fresh copy, so mutating a returned dict/list can never
    corrupt what's stored here. May only be constructed by
    `_load_and_verify_candidate`, which performs verification first."""

    __slots__ = ("_text",)

    def __init__(self, text: str, *, _token=None):
        if _token is not _VERIFICATION_TOKEN:
            raise HoldoutError(
                "VerifiedCandidateRegistry may not be constructed directly; "
                "obtain one from load_candidate_registry_for_phase9_audit() or "
                "load_registry(), which verify the content first")
        object.__setattr__(self, "_text", text)

    def __setattr__(self, name, value):
        raise AttributeError("VerifiedCandidateRegistry is immutable")

    def _data(self) -> dict:
        return json.loads(self._text)

    def __getitem__(self, key):
        return self._data()[key]

    def __contains__(self, key):
        return key in self._data()

    def get(self, key, default=None):
        return self._data().get(key, default)

    def keys(self):
        return self._data().keys()

    def sha256(self) -> str:
        return hashlib.sha256(self._text.encode("utf-8")).hexdigest()

    def raw_text(self) -> str:
        return self._text


def _verify_registry_schema(data: dict) -> None:
    missing = [s for s in REQUIRED_REGISTRY_SECTIONS if s not in data]
    if missing:
        raise HoldoutError(f"registry missing required section(s): {missing}")
    if data.get("policy_version") != POLICY_VERSION:
        raise HoldoutError(
            f"registry policy_version {data.get('policy_version')!r} != "
            f"expected {POLICY_VERSION!r}")
    for f in MULTIVALUED:
        sel = data.get("value_holdouts", {}).get(f, {}).get("selected", [])
        if len(sel) != len(set(sel)):
            raise HoldoutError(f"duplicate selected value(s) in {f}: {sel}")


def _verify_upstream_inputs(data: dict) -> None:
    frozen = data.get("frozen_inputs", {})
    for rel, expected in frozen.items():
        got = sha256_file(ROOT / rel)
        if got != expected:
            raise HoldoutError(
                f"upstream input {rel} has drifted: registry expects "
                f"{expected}, current file hashes to {got}")


def _load_and_verify_candidate(text: str) -> VerifiedCandidateRegistry:
    """Core verification against arbitrary registry text. Separated from the
    real-file loader below so fault tests can exercise rejection paths
    (stale/mutated/malformed registries) without touching the real file."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        raise HoldoutError(f"malformed registry JSON: {e}") from e
    _verify_registry_schema(data)
    _verify_upstream_inputs(data)
    recomputed = recompute_registry_dict()
    if recomputed != data:
        drifted = sorted(k for k in set(recomputed) | set(data)
                         if recomputed.get(k) != data.get(k))
        raise HoldoutError(
            "registry does not match deterministic recomputation from the "
            f"frozen inputs -- drifted section(s): {drifted}")
    return VerifiedCandidateRegistry(text, _token=_VERIFICATION_TOKEN)


def load_candidate_registry_for_phase9_audit() -> VerifiedCandidateRegistry:
    if not REGISTRY.is_file():
        raise HoldoutError(f"holdout registry not frozen: {REGISTRY}")
    return _load_and_verify_candidate(REGISTRY.read_text(encoding="utf-8"))


# Approval record fields ALL required, not sha256 alone -- a hash-only record
# is not a complete, auditable approval (who approved what commit, when).
REQUIRED_APPROVAL_FIELDS = ("approved_registry_sha256", "approved_commit",
                           "approved_date")


def load_registry() -> VerifiedCandidateRegistry:
    candidate = load_candidate_registry_for_phase9_audit()
    if not PHASE9_APPROVAL.is_file():
        raise Phase9NotApproved(
            "Phase 9 has not been approved: no PHASE9_AUTHORIZATION_A002.json anchor "
            "exists. Production/Phase-10+ code may not consume this registry "
            "until an explicit, separately-reviewed approval record is "
            "written -- see PHASE9_AUTHORIZATION_A002.json's documented workflow.")
    try:
        approval = json.loads(PHASE9_APPROVAL.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HoldoutError(f"malformed PHASE9_AUTHORIZATION_A002.json: {e}") from e
    missing = [f for f in REQUIRED_APPROVAL_FIELDS if not approval.get(f)]
    if missing:
        raise HoldoutError(
            f"PHASE9_AUTHORIZATION_A002.json missing required field(s) {missing} -- a "
            f"hash-only approval record is not a complete, auditable approval")
    if approval["approved_registry_sha256"] != candidate.sha256():
        raise RegistryTamperError(
            "the current registry does not match the approved digest recorded "
            "in PHASE9_AUTHORIZATION_A002.json -- registry and/or code changed since "
            "approval")
    return candidate


def _require_verified_registry(reg):
    """A raw dict bypasses every verification this module performs. Every
    scanner/accessor that takes an optional `reg` must reject one -- confirmed
    a live bug: mutating a copy of the verified registry's data and passing it
    straight through as `reg=` produced a passing zero-exposure certificate
    for a value that was never actually still held out."""
    if reg is not None and not isinstance(reg, VerifiedCandidateRegistry):
        raise TypeError(
            f"reg must be a VerifiedCandidateRegistry (from "
            f"load_candidate_registry_for_phase9_audit()/load_registry()), "
            f"not {type(reg).__name__} -- a raw dict bypasses all registry "
            f"verification")
    return reg


def held_out_values(reg=None) -> dict:
    reg = _require_verified_registry(reg) or load_registry()
    return {f: tuple(reg["value_holdouts"][f]["selected"]) for f in MULTIVALUED}


# --------------------------------------------------------------------------
# Exposure scanning -- run by EVERY dataset phase on FINAL RENDERED strings.
# List-only contracts (D.5): a bare str/dict raises rather than being
# silently mis-iterated (a bare string scans as characters; a dict scans as
# its keys -- both reproduced bugs, both closed here).
# --------------------------------------------------------------------------
def _normalize_for_exposure(s: str) -> str:
    """NFKC compatibility-normalize, casefold, collapse whitespace. Confined
    to the scanning step only -- never mutates actual training text."""
    s = unicodedata.normalize("NFKC", s)
    s = s.casefold()
    return " ".join(s.split())


def scan_strings(strings, reg=None) -> dict:
    """Scan FINAL RENDERED model-visible strings for held-out value literals.

    README:404 -- zero exposure applies to every model-visible fine-tuning
    string: system prompts, schema text, value catalogues, few-shot text, chat
    messages and rendered context, not only questions and targets. Applies to
    fine-tuning text only -- never the legitimate inference-time value
    catalogue (see exposure_policy.scope_boundary in the registry).
    """
    if isinstance(strings, (str, bytes, dict)):
        raise TypeError(
            f"scan_strings expects list[str], got {type(strings).__name__} -- "
            "wrap a single string in a list; for a part_id-keyed dict use "
            "list(d.values())")
    strings = list(strings)
    # Every entry must be a genuine string -- an empty string "" is a
    # legitimate "nothing rendered here" value, but None/other types are not
    # silently skipped: reproduced as a live bug, a list mixing one real
    # string with a None entry passed a "verified" zero-exposure certificate
    # while the None slot was never actually examined for anything.
    bad = [i for i, s in enumerate(strings) if s is not None and not isinstance(s, str)]
    if bad:
        raise TypeError(
            f"scan_strings: entr(y/ies) at index {bad[:5]} are not strings -- "
            f"every entry must be a real rendered string (or None is also "
            f"rejected below), not silently skipped")
    if any(s is None for s in strings):
        raise HoldoutError(
            "scan_strings: a None entry means a slot was never actually "
            "rendered -- it cannot be silently treated as 'nothing to scan' "
            "for a slot that was supposed to carry model-visible text")
    reg = _require_verified_registry(reg) or load_registry()
    hv = held_out_values(reg)
    norm_strings = [_normalize_for_exposure(s) for s in strings]
    real_evidence_count = len(strings)
    counts, hits = {}, []
    for f, vals in hv.items():
        for v in vals:
            nv = _normalize_for_exposure(v)
            n = 0
            for i, ns in enumerate(norm_strings):
                if nv and ns and nv in ns:
                    n += 1
                    if len(hits) < 50:
                        hits.append({"attribute": f, "value": v, "string_index": i})
            counts[v] = n
    return {"exposure_counts": counts,
            "total_exposures": sum(counts.values()),
            "strings_scanned": real_evidence_count,
            "hits": hits}


def scan_operations(sql_texts, reg=None) -> dict:
    """Held-out operation constructs must appear 0 times in training gold SQL."""
    if isinstance(sql_texts, (str, bytes, dict)):
        raise TypeError(
            f"scan_operations expects list[str], got {type(sql_texts).__name__} "
            "-- for a part_id-keyed multi-part gold_sql dict, use "
            "scan_operations_multipart")
    sql_texts = list(sql_texts)
    # Every entry must be a genuine string, for the same reason as
    # scan_strings: reproduced as a live bug, scan_operations_multipart with
    # one declared part's SQL set to None silently dropped that part from
    # sql_scanned entirely -- a held-out construct hiding in the untested
    # part would never have been caught.
    bad = [i for i, s in enumerate(sql_texts)
          if s is not None and not isinstance(s, str)]
    if bad:
        raise TypeError(
            f"scan_operations: entr(y/ies) at index {bad[:5]} are not strings")
    if any(s is None for s in sql_texts):
        raise HoldoutError(
            "scan_operations: a None entry means a declared part's SQL was "
            "never actually supplied -- it cannot be silently dropped from "
            "the scan rather than failing closed")
    # A blank/whitespace-only string is not a legitimate empty QUERY -- unlike
    # scan_strings (where an empty rendered string can be genuine content),
    # there is no such thing as a real SQL statement with no text. Reproduced
    # as a live bug: scan_operations([""], reg) reported "1 SQL scanned" and
    # passed as verified evidence, though no query was ever actually present
    # to check for held-out constructs.
    if any(isinstance(s, str) and not s.strip() for s in sql_texts):
        raise HoldoutError(
            "scan_operations: a blank/whitespace-only entry is not an "
            "executed query -- it cannot count as scanned SQL evidence")
    reg = _require_verified_registry(reg) or load_registry()
    held = set(reg["operation_holdouts"]["held_out_families"])
    counts = {f: 0 for f in sorted(held)}
    for s in sql_texts:
        for fam in operation_families_present(s) & held:
            counts[fam] += 1
    return {"operation_exposure_counts": counts,
            "total_exposures": sum(counts.values()),
            "sql_scanned": len(sql_texts)}


def scan_operations_multipart(gold_sql: dict, reg=None) -> dict:
    """Scan EVERY part's SQL and combine detected families across all parts --
    a multi-part task with a held-out construct in ANY part is excluded from
    training entirely, exactly as a single-query task is under
    multi_family_rule. Correction: passing the dict itself to scan_operations
    would silently scan its KEYS (part_id strings), not the SQL -- reproduced
    directly (a bare LIMIT in one part scored 0 exposures when the dict was
    passed directly, 1 when .values() was extracted first)."""
    if not isinstance(gold_sql, dict):
        raise TypeError("scan_operations_multipart expects a part_id-keyed dict")
    if not gold_sql:
        raise HoldoutError(
            "scan_operations_multipart: empty parts dict -- a multi-part task "
            "with zero parts is not a valid task and cannot yield a genuine "
            "zero-exposure certificate")
    return scan_operations(list(gold_sql.values()), reg)


def _validate_component_names(names, *, where: str) -> None:
    """Every member of a component collection must itself be a non-blank str
    -- reproduced as a live bug: scan_compositions([[None]], reg) and
    scan_compositions_multipart({"p1": [b"certifications"], "p2":
    [b"processes"]}, reg) both passed the outer collection-shape checks (a
    list of a list; a dict of lists) and then did set(...) directly on the
    un-validated members, so None/bytes/int component names silently formed
    a set that could never equal the (str-only) held-out set -- a genuine
    held-out composition (certifications+processes) reported zero violations
    solely because the member type didn't match, not because it was absent."""
    bad = [n for n in names
           if not isinstance(n, str) or not n.strip()]
    if bad:
        raise TypeError(
            f"{where}: component name(s) {bad[:5]!r} are not non-blank "
            f"strings -- every member of a component set must be a real "
            f"component name (e.g. \"processes\"), not None/bytes/a number/"
            f"blank text")


def scan_compositions(component_sets, reg=None) -> dict:
    """Superset rule: for held-out H and training set T, assert not H subset-of T."""
    if isinstance(component_sets, (str, bytes, dict)):
        # Reproduced as a live bug: a bare string is iterable, so
        # scan_compositions("certifications processes", reg) silently treated
        # each CHARACTER as one "component set" -- 24 characters reported as
        # "24 component sets scanned", with the real intended set never
        # actually checked.
        raise TypeError(
            f"scan_compositions expects list[iterable[str]], got "
            f"{type(component_sets).__name__} -- wrap a single component set "
            f"in a list: [component_set], not the bare set/string itself; "
            f"for a multi-part task's component sets, use "
            f"scan_compositions_multipart")
    component_sets = list(component_sets)
    # Each individual component SET must itself be a real collection, not a
    # bare string -- reproduced as a live bug: scan_compositions(["certifications
    # processes"], reg) passed the outer-shape check (a list!) but then did
    # set("certifications processes") on the single nested string, scanning
    # 24 individual characters as if they were 24 components, with the real
    # intended two-component set never actually checked.
    bad = [i for i, T in enumerate(component_sets) if isinstance(T, (str, bytes))]
    if bad:
        raise TypeError(
            f"scan_compositions: component set(s) at index {bad[:5]} are bare "
            f"strings, not a collection of component names -- wrap each one: "
            f"[\"processes\"] not \"processes\"")
    # Materialize each component collection exactly ONCE, before validation.
    # Regression, reproduced directly: validating list(T) and then later
    # scanning the original T silently exhausts T when it's an iterator/
    # generator (not a list/tuple/set) -- the validation pass consumes it,
    # so the scan pass that runs afterward sees an empty collection and
    # reports a false zero-violation certificate for a genuinely held-out
    # composition. Validate and scan the SAME materialized list.
    component_sets = [list(T) for T in component_sets]
    for i, T in enumerate(component_sets):
        _validate_component_names(T, where=f"scan_compositions: set at index {i}")
    reg = _require_verified_registry(reg) or load_registry()
    held = [set(h) for h in reg["composition_holdouts"]["held_out_sets"]]
    violations = []
    for i, T in enumerate(component_sets):
        Ts = set(T)
        for H in held:
            if H <= Ts:
                violations.append({"index": i, "held_out_set": sorted(H),
                                   "training_set": sorted(Ts)})
    return {"composition_violations": len(violations),
            "violations": violations[:50],
            "sets_scanned": len(component_sets)}


def scan_compositions_multipart(parts_component_sets: dict, reg=None) -> dict:
    """Compositional-heldout exclusion must use the WHOLE task's component
    UNION, not each part checked in isolation -- README's superset rule
    operates on one training set T per task, and a multi-part task is one
    logical training item. Reproduced directly: {certifications} in one part
    and {processes} in another each pass a per-part check individually while
    their union violates the frozen {certifications, processes} holdout."""
    if not isinstance(parts_component_sets, dict):
        raise TypeError(
            "scan_compositions_multipart expects a part_id-keyed dict of "
            "component sets")
    if not parts_component_sets:
        raise HoldoutError(
            "scan_compositions_multipart: empty parts dict -- a multi-part "
            "task with zero parts is not a valid task and cannot yield a "
            "genuine composition-scan certificate")
    # Same nested-string guard as scan_compositions -- reproduced as a live
    # bug: {"p1": "certifications", "p2": "processes"} passed the dict-shape
    # check but then did set("certifications") per value, scanning
    # characters instead of the one real component each part declared.
    bad = [pid for pid, s in parts_component_sets.items()
          if isinstance(s, (str, bytes))]
    if bad:
        raise TypeError(
            f"scan_compositions_multipart: part(s) {bad[:5]} carry a bare "
            f"string as their component set, not a collection -- wrap each "
            f"one: [\"processes\"] not \"processes\"")
    # Same materialize-once discipline as scan_compositions -- reproduced
    # directly: validating list(s) and then later doing set(s) on the
    # original s silently exhausts an iterator/generator part value between
    # the two passes, so the union-building step sees an empty collection
    # and the composition scan certifies zero violations for a genuinely
    # held-out composition.
    parts_component_sets = {pid: list(s) for pid, s in parts_component_sets.items()}
    for pid, s in parts_component_sets.items():
        _validate_component_names(
            s, where=f"scan_compositions_multipart: part {pid!r}")
    union = set()
    for s in parts_component_sets.values():
        union |= set(s)
    return scan_compositions([sorted(union)], reg)


def assert_value_scan_verified(report: dict) -> None:
    """Verified-zero requires real scan evidence (strings_scanned > 0), not
    merely total_exposures == 0 -- an empty scan would otherwise pass
    vacuously. Also requires internal consistency: a nonzero `hits` list
    while `total_exposures == 0` (or vice versa) is a malformed report, not a
    genuine zero-exposure certificate -- reproduced directly as a live bug."""
    required = ("exposure_counts", "total_exposures", "strings_scanned", "hits")
    missing = [k for k in required if k not in report]
    if missing:
        raise HoldoutError(f"malformed value-scan report, missing {missing}")
    if report["strings_scanned"] <= 0:
        raise HoldoutError(
            "value-scan report proves nothing was actually scanned "
            "(strings_scanned <= 0) -- not a valid zero-exposure certificate")
    if sum(report["exposure_counts"].values()) != report["total_exposures"]:
        raise HoldoutError(
            "value-scan report internally inconsistent: per-value counts "
            "don't sum to total_exposures")
    hits = report["hits"]
    if report["total_exposures"] == 0 and hits:
        raise HoldoutError(
            "value-scan report internally inconsistent: total_exposures == 0 "
            f"but hits is non-empty ({hits[:3]})")
    if report["total_exposures"] > 0 and not hits:
        raise HoldoutError(
            "value-scan report internally inconsistent: total_exposures > 0 "
            "but hits is empty")
    if report["total_exposures"] != 0:
        raise HoldoutError(
            f"exposure_count != 0 -- held-out literals appear in rendered "
            f"training text: {hits[:5]}")


def assert_operation_scan_verified(report: dict) -> None:
    required = ("operation_exposure_counts", "total_exposures", "sql_scanned")
    missing = [k for k in required if k not in report]
    if missing:
        raise HoldoutError(f"malformed operation-scan report, missing {missing}")
    if report["sql_scanned"] <= 0:
        raise HoldoutError(
            "operation-scan report proves nothing was actually scanned "
            "(sql_scanned <= 0) -- not a valid zero-exposure certificate")
    if sum(report["operation_exposure_counts"].values()) != report["total_exposures"]:
        raise HoldoutError("operation-scan report internally inconsistent: "
                           "per-family counts don't sum to total_exposures")
    if report["total_exposures"] != 0:
        raise HoldoutError(
            f"held-out operation construct(s) present: "
            f"{report['operation_exposure_counts']}")


def assert_composition_scan_verified(report: dict) -> None:
    """Requires internal consistency: a nonzero `violations` list while
    `composition_violations == 0` (or vice versa) is malformed, not a
    genuine zero-violation certificate."""
    required = ("composition_violations", "violations", "sets_scanned")
    missing = [k for k in required if k not in report]
    if missing:
        raise HoldoutError(f"malformed composition-scan report, missing {missing}")
    if report["sets_scanned"] <= 0:
        raise HoldoutError(
            "composition-scan report proves nothing was actually scanned "
            "(sets_scanned <= 0) -- not a valid zero-exposure certificate")
    violations = report["violations"]
    if report["composition_violations"] == 0 and violations:
        raise HoldoutError(
            "composition-scan report internally inconsistent: "
            f"composition_violations == 0 but violations is non-empty "
            f"({violations[:3]})")
    if report["composition_violations"] > 0 and not violations:
        raise HoldoutError(
            "composition-scan report internally inconsistent: "
            "composition_violations > 0 but violations is empty")
    if report["composition_violations"] != 0:
        raise HoldoutError(
            f"held-out composition present: {violations[:5]}")
