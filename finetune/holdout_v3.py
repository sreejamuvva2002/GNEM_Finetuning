"""Phase 9 -- the frozen holdout policy, and the exposure scanner every dataset
phase must run.

FROZEN 2026-08-24 by explicit user authorization, after a read-only decision
analysis, and REVISED the same day (v3.0 -> v3.1) after independent review --
see POLICY_REVISION below. The parameters below are pre-registration: they were fixed BEFORE any
training dataset existed, which is the property README Phase 9 exists to protect
("If holdouts are chosen after seeing the generated data, the holdout that gets
picked is the one the data happens to support").

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
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "datasets_v3" / "canonical_records_v3.jsonl"
SPLITS = ROOT / "datasets_v3" / "company_split_groups_v3.csv"
REGISTRY = ROOT / "datasets_v3" / "HOLDOUT_REGISTRY_v3.json"

POLICY_VERSION = "holdout_v3.1"
FROZEN_DATE = "2026-08-24"

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
HOLDOUT_COUNTS = {"processes": 4, "services": 3, "certifications": 2}

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

# logical_fingerprint_v1
FINGERPRINT_VERSION = "lfp1"
FINGERPRINT_SEMANTIC_FIELDS = ("operation_family", "fields_used", "values_used",
                               "target_columns", "answer_type", "join_arity",
                               "required_constructs", "entity_dependent")

# answer_type / target_columns conventions. Phase 7 froze the four semantics;
# Phase 9 freezes the multi-part SERIALIZATION that Phase 7 deferred.
ANSWER_TYPES = ("set", "scalar", "top_k", "multi_part")
MULTI_PART_SERIALIZATION = "parts_list_v1"
MULTI_PART_NOTE = (
    "A multi_part task carries parts: [{part_id, answer_type, target_columns}], "
    "and `target_columns` remains the flattened ordered union so the frozen "
    "Phase 7 grader keeps working unchanged. Phase 7's stand-in treated each "
    "target column as one part, which cannot express a multi-part question whose "
    "parts are different OPERATIONS (a count and a set); this serialization can.")


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


class HoldoutError(ValueError):
    """A holdout policy invariant was violated."""


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


def classify_operation(sql: str) -> str:
    """Exactly one operation_family, by frozen precedence."""
    u = " ".join(sql.upper().split())
    has_group = "GROUP BY" in u
    has_limit = "LIMIT" in u
    has_order = "ORDER BY" in u
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
    u = " ".join(sql.upper().split())
    out = set()
    if "ORDER BY" in u and "LIMIT" in u:
        out.add("argmax_topk")
    if "GROUP BY" in u:
        out.add("group_by")
    if "LIMIT" in u and "ORDER BY" not in u:
        out.add("limit_only")
    return out


def logical_fingerprint(task: dict) -> str:
    """Semantic identity, insensitive to wording, formatting, aliases and ids."""
    canon = {}
    for f in FINGERPRINT_SEMANTIC_FIELDS:
        v = task.get(f)
        if isinstance(v, (list, tuple, set)):
            v = sorted(str(x) for x in v)
        canon[f] = v
    blob = json.dumps(canon, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return f"{FINGERPRINT_VERSION}:{hashlib.sha256(blob.encode()).hexdigest()[:32]}"


# --------------------------------------------------------------------------
# Exposure scanning -- run by EVERY dataset phase on FINAL RENDERED strings
# --------------------------------------------------------------------------
def load_registry() -> dict:
    if not REGISTRY.is_file():
        raise HoldoutError(f"holdout registry not frozen: {REGISTRY}")
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def held_out_values(reg=None) -> dict:
    reg = reg or load_registry()
    return {f: tuple(reg["value_holdouts"][f]["selected"]) for f in MULTIVALUED}


def scan_strings(strings, reg=None) -> dict:
    """Scan FINAL RENDERED model-visible strings for held-out value literals.

    README:404 -- zero exposure applies to every model-visible fine-tuning
    string: system prompts, schema text, value catalogues, few-shot text, chat
    messages and rendered context, not only questions and targets.
    """
    reg = reg or load_registry()
    hv = held_out_values(reg)
    counts, hits = {}, []
    for f, vals in hv.items():
        for v in vals:
            n = 0
            for i, s in enumerate(strings):
                if s and v in s:
                    n += 1
                    if len(hits) < 50:
                        hits.append({"attribute": f, "value": v, "string_index": i})
            counts[v] = n
    return {"exposure_counts": counts,
            "total_exposures": sum(counts.values()),
            "strings_scanned": len(strings),
            "hits": hits}


def scan_operations(sql_texts, reg=None) -> dict:
    """Held-out operation constructs must appear 0 times in training gold SQL."""
    reg = reg or load_registry()
    held = set(reg["operation_holdouts"]["held_out_families"])
    counts = {f: 0 for f in sorted(held)}
    for s in sql_texts:
        if not s:
            continue
        for fam in operation_families_present(s) & held:
            counts[fam] += 1
    return {"operation_exposure_counts": counts,
            "total_exposures": sum(counts.values()),
            "sql_scanned": len(sql_texts)}


def scan_compositions(component_sets, reg=None) -> dict:
    """Superset rule: for held-out H and training set T, assert not H subset-of T."""
    reg = reg or load_registry()
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


def assert_zero_exposure(report: dict, arm: str) -> None:
    if report.get("total_exposures", 0) != 0:
        raise HoldoutError(
            f"{arm}: exposure_count != 0 -- held-out literals appear in rendered "
            f"training text: {report.get('hits', [])[:5]}")
