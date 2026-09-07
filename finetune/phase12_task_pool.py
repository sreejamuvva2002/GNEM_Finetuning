"""Phase 12 -- build `STRUCTURED_TASK_POOL_v3.jsonl`, the canonical source for
both C (`train_kb_gold` as a direct-answer target) and D (`gold_sql` as a
target). One pool, rendered two ways in Phases 13/14, so C and D differ only
in supervision target -- never in question composition (README Phase 12).

THREE COMPUTED GOLDS PER TASK, one per KB scope:
  train_kb_gold       executed over train_kb.       C's supervision target.
  train_dev_kb_gold   executed over train_dev_kb.   Dev evaluation gold only.
  full_kb_gold        executed over full_kb.        Test evaluation gold only.
`entity_dependent = (full_kb_gold != train_kb_gold)`. Candidate generation and
support/cap checks use train_kb ONLY (README:495) -- the other two scopes are
never consulted to decide whether a task exists, only to compute its gold.

MODEL SQL STAYS SCOPE-NEUTRAL: every gold_sql here reads the logical tables
`companies`, `processes`, `services`, `certifications` (finetune/sqlexec_v3.py)
and is executed once per scope by the scoped executor -- never a `train_kb_*`
table name.

OPERATION CATALOGUE (a documented scope decision, not enumerated by README):
  filter / count           WHERE <field> = <value>                filter
  child_filter / child_count  JOIN <child> WHERE <term> = <value>  filter
  threshold_filter          WHERE employment > <n>                 filter
  group_by_breakdown        GROUP BY <field>, no LIMIT              group_by (HELD OUT)
  argmax_single             GROUP BY ... ORDER BY n DESC LIMIT 1    argmax_topk (HELD OUT)
  topk_employment           ORDER BY employment DESC LIMIT k        argmax_topk (HELD OUT)
  composition_filter        two-child-table intersection            filter (composition axis)
Fields eligible per shape are read from holdout_v3.FIELD_SEMANTIC_OPERATIONS
(the frozen, README-sourced field/operation map), never a separately invented
list. `product_or_service` (semantic_filter), `location` (redundant with the
derived `city`/`county` columns already covering it), `row_id` and `company`
(no natural aggregate/filter shape) are out of scope for this catalogue --
documented here, not silently omitted.

HELD-OUT AWARENESS, applied at pool-generation time (registry:
"applied_to_real_pool_at: Phase 12"):
  - the composition pair {certifications, processes} is never generated as a
    composition_filter candidate at all (README's compositional holdout).
  - operation_family classification uses the real SQL-construct scanner
    (holdout_v3.classify_operation) on the actual rendered gold_sql, never an
    a-priori label -- the authoritative gate README:279 requires.
  - a task touching a value-held-out literal is NOT excluded from the pool
    (Phase 21's value-heldout probe needs exactly such tasks); ELIGIBILITY for
    C/D training is a separate computation Phases 13/14 make by scanning
    values_used/gold_sql against the registry, not baked into this pool.

Deterministic total tie-breaks (README:510-513): every ranking/top-k/argmax
gold_sql carries `ORDER BY <metric> DESC, company ASC, row_id ASC` or the
group-level equivalent. Set/group-by queries also carry `ORDER BY` for a
byte-stable stored artifact, even though set comparison is order-insensitive.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H        # noqa: E402
import kb_v3 as KB             # noqa: E402
import sqlexec_v3 as X         # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "datasets_v3" / "gnem_v3.sqlite"
OUT = ROOT / "datasets_v3" / "STRUCTURED_TASK_POOL_v3.jsonl"
OUT_AUDIT = ROOT / "validation_v3" / "TASK_POOL_v3.md"
GENERATOR_VERSION = "task_pool_v3.0"
SCOPES = ("train_kb", "train_dev_kb", "full_kb")

LIST_CAP = 40           # README Phase 14: list/filter 1-40
CROSS_TABLE_CAP = 25    # README Phase 14: cross-table 1-25
MIN_SUPPORT = 1

CHILD_TABLES = {"processes": "processes", "services": "services",
                "certifications": "certifications"}
CHILD_COLUMN = {"processes": "process", "services": "service",
                "certifications": "standard_family"}

QUESTION = {
    "filter": "List every company whose {field_h} is {value}.",
    "count": "How many companies have {field_h} equal to {value}?",
    "child_filter": "List every company associated with {value}.",
    "child_count": "How many companies are associated with {value}?",
    "threshold_filter": "List every company that employs more than {value} people.",
    "group_by_breakdown": "How many companies fall into each {field_h}?",
    "argmax_single": "Which {field_h} has the most companies, and how many?",
    "topk_employment": "Which {value} companies have the highest employment?",
    "composition_filter": "List every company associated with both {value}.",
}

FIELD_LABEL = {
    "category": "category", "industry_group": "industry group",
    "primary_facility_type": "primary facility type",
    "ev_supply_chain_role": "EV supply chain role",
    "supplier_or_affiliation_type": "supplier or affiliation type",
    "classification_method": "classification method", "city": "city",
    "county": "county", "primary_oems": "primary OEMs", "address": "address",
    "ev_battery_relevant": "EV/battery relevance",
    "processes": "process", "services": "service",
    "certifications": "certification",
}


class Gate(Exception):
    """A Phase 12 invariant failed. No artifact is written."""


def sql_lit(v) -> str:
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Candidate generation -- from train_kb ONLY (README:495)
# ---------------------------------------------------------------------------
def semantic_ops_for(field: str) -> set[str]:
    ops = set(H.FIELD_SEMANTIC_OPERATIONS.get(field, set()))
    excl = H.FIELD_SPECIFIC_RESTRICTIONS.get(field, {}).get("excludes", [])
    return ops - set(excl)


SCALAR_FIELDS = ("category", "industry_group", "primary_facility_type",
                 "ev_supply_chain_role", "supplier_or_affiliation_type",
                 "classification_method", "city", "county",
                 "primary_oems", "address", "ev_battery_relevant")
# Correction (post-approval audit): count is an AGGREGATION, and address/
# primary_oems carry only {"filter"} in FIELD_SEMANTIC_OPERATIONS -- no
# "aggregation" at all. The original build iterated SCALAR_FIELDS
# unconditionally for count, generating 131 address-count and 12
# primary_oems-count tasks in violation of README:538's "Address gets no
# structured aggregation" (and, by the same unstated semantic-ops rule,
# primary_oems). Gated here exactly like GROUPABLE_FIELDS already was.
AGGREGATABLE_FIELDS = tuple(f for f in SCALAR_FIELDS if "aggregation" in semantic_ops_for(f))
GROUPABLE_FIELDS = tuple(f for f in SCALAR_FIELDS if "group_by" in semantic_ops_for(f))
GROUPABLE_CHILD_FIELDS = ("processes", "services", "certifications")
SENTINEL_VALUES = ("Not specified", "Not applicable")
COMPOSITION_PAIRS = tuple(
    p for p in H.COMPOSITION_FAMILIES
    if tuple(sorted(p)) not in {tuple(sorted(h)) for h in
                                (lambda reg: reg["composition_holdouts"]["held_out_sets"])(
                                    json.loads((ROOT / "datasets_v3" /
                                               "HOLDOUT_REGISTRY_v3.json").read_text()))})


def scalar_field_values(train_recs, field: str) -> dict[str, set[str]]:
    """value -> {companies}, among train_kb, excluding sentinels/blank."""
    out = defaultdict(set)
    for r in train_recs:
        v = getattr(r, field)
        if v is None or (isinstance(v, str) and v.strip() in
                         ("Not specified", "Not applicable")):
            continue
        out[v].add(r.company)
    return dict(out)


def child_field_values(train_recs, field: str) -> dict[str, set[str]]:
    out = defaultdict(set)
    for r in train_recs:
        for t in H.terms(getattr(r, field), field):
            out[t].add(r.company)
    return dict(out)


def composition_candidates(train_recs, f1: str, f2: str) -> dict[tuple, set[str]]:
    v1 = child_field_values(train_recs, f1)
    v2 = child_field_values(train_recs, f2)
    out = {}
    for a, cos_a in v1.items():
        for b, cos_b in v2.items():
            both = cos_a & cos_b
            if MIN_SUPPORT <= len(both) <= CROSS_TABLE_CAP:
                out[(a, b)] = both
    return out


# ---------------------------------------------------------------------------
# gold_sql builders -- scope-neutral, logical table names only
# ---------------------------------------------------------------------------
def sql_filter(field: str, value) -> str:
    # DISTINCT: a multi-row company matching on this field more than once
    # (e.g. two Atlanta facilities) must not appear twice in a company LIST.
    return (f"SELECT DISTINCT company FROM companies WHERE {field} = "
           f"{sql_lit(value)} ORDER BY company")


def sql_count(field: str, value) -> str:
    # Correction (post-approval audit, confirmed): COUNT(*) counts ROWS, but
    # the question asks "how many COMPANIES" -- a company with >1 matching
    # row (Atlanta: Novelis Inc. has 3 rows there) was counted once per row.
    # Reproduced and fixed: Atlanta's committed answer was 7 (rows); the
    # correct company count is 5.
    return (f"SELECT COUNT(DISTINCT company) AS n FROM companies WHERE "
           f"{field} = {sql_lit(value)}")


def sql_child_filter(field: str, value) -> str:
    t, col = CHILD_TABLES[field], CHILD_COLUMN[field]
    return (f"SELECT DISTINCT c.company FROM companies c JOIN {t} x ON "
           f"x.row_id = c.row_id WHERE x.{col} = {sql_lit(value)} "
           f"ORDER BY c.company")


def sql_child_count(field: str, value) -> str:
    t, col = CHILD_TABLES[field], CHILD_COLUMN[field]
    return (f"SELECT COUNT(DISTINCT c.company) AS n FROM companies c JOIN "
           f"{t} x ON x.row_id = c.row_id WHERE x.{col} = {sql_lit(value)}")


def sql_threshold(n: int) -> str:
    return (f"SELECT DISTINCT company FROM companies WHERE employment > "
           f"{int(n)} ORDER BY employment DESC, company ASC")


def _sentinel_exclusion(field: str) -> str:
    lits = " AND ".join(f"{field} != {sql_lit(s)}" for s in SENTINEL_VALUES)
    return f"WHERE {lits} "


def sql_group_by_breakdown(field: str) -> str:
    if field in GROUPABLE_CHILD_FIELDS:
        t, col = CHILD_TABLES[field], CHILD_COLUMN[field]
        return (f"SELECT x.{col} AS {col}, COUNT(DISTINCT c.company) AS n "
               f"FROM companies c JOIN {t} x ON x.row_id = c.row_id "
               f"GROUP BY x.{col} ORDER BY x.{col} ASC")
    # Correction (post-approval audit, confirmed): a group-by breakdown with
    # no WHERE clause grouped over raw DB values, including the sentinel
    # "Not specified" (16 companies for supplier_or_affiliation_type) as if
    # it were an ordinary category. Sentinels are excluded here exactly as
    # they already are from filter/count candidate generation (scalar_field_
    # values), not merely at the candidate-count-check level.
    return (f"SELECT {field}, COUNT(DISTINCT company) AS n FROM companies "
           f"{_sentinel_exclusion(field)}GROUP BY {field} ORDER BY {field} ASC")


def sql_argmax_single(field: str) -> str:
    if field in GROUPABLE_CHILD_FIELDS:
        t, col = CHILD_TABLES[field], CHILD_COLUMN[field]
        return (f"SELECT x.{col} AS {col}, COUNT(DISTINCT c.company) AS n "
               f"FROM companies c JOIN {t} x ON x.row_id = c.row_id "
               f"GROUP BY x.{col} ORDER BY n DESC, x.{col} ASC LIMIT 1")
    return (f"SELECT {field}, COUNT(DISTINCT company) AS n FROM companies "
           f"{_sentinel_exclusion(field)}GROUP BY {field} "
           f"ORDER BY n DESC, {field} ASC LIMIT 1")


def target_col_name(field: str) -> str:
    return CHILD_COLUMN[field] if field in GROUPABLE_CHILD_FIELDS else field


def sql_topk_employment(k: int) -> str:
    return (f"SELECT company, employment FROM companies "
           f"ORDER BY employment DESC, company ASC LIMIT {int(k)}")


def sql_composition(f1: str, v1: str, f2: str, v2: str) -> str:
    # Correction (post-approval audit, confirmed): joining both child tables
    # ON x1.row_id = c.row_id AND x2.row_id = c.row_id requires BOTH facts to
    # be recorded against the exact same physical row -- but composition
    # candidates (composition_candidates(), below) are selected at COMPANY
    # level, aggregating terms across every row that company has (matching
    # CLAUDE.md's own company-level answer identity, #11). For the five
    # multi-row train companies this mismatch produced real candidates
    # (e.g. Sewon America does CNC Machining at one facility and Asset
    # Management at another) that executed to an empty result -- reproduced
    # directly: 8 tasks, all involving processes+services, all zero rows.
    # Fixed by matching on company NAME (both child tables carry it), the
    # same key the candidate selection already uses, not on row_id.
    t1, c1 = CHILD_TABLES[f1], CHILD_COLUMN[f1]
    t2, c2 = CHILD_TABLES[f2], CHILD_COLUMN[f2]
    return (f"SELECT DISTINCT c.company FROM companies c "
           f"WHERE c.company IN (SELECT company FROM {t1} WHERE {c1} = "
           f"{sql_lit(v1)}) AND c.company IN (SELECT company FROM {t2} "
           f"WHERE {c2} = {sql_lit(v2)}) ORDER BY c.company")


# ---------------------------------------------------------------------------
# Task assembly
# ---------------------------------------------------------------------------
def leaf(field: str, value) -> dict:
    return {"op": "eq", "field": field, "value": str(value)}


def make_task(task_id: str, question: str, gold_sql: str, *, answer_type: str,
             target_columns: list[str], fields_used: list[str],
             values_used: list[str], logical_components: dict,
             join_arity: int) -> dict:
    family = H.classify_operation(gold_sql)
    u = gold_sql.upper()
    required = [kw for kw, pat in (
        ("JOIN", r"\bJOIN\b"), ("GROUP BY", r"\bGROUP\s+BY\b"),
        ("ORDER BY", r"\bORDER\s+BY\b"), ("LIMIT", r"\bLIMIT\b"),
    ) if re.search(pat, u)]
    if re.search(r"\bWHERE\b", u) and "WHERE" not in required:
        required.append("WHERE")
    if not required:
        required.append("SELECT")
    task = {
        "task_id": task_id,
        "question": question,
        "operation_family": family,
        "fields_used": sorted(set(fields_used)),
        "values_used": sorted(set(str(v) for v in values_used)),
        "logical_components": logical_components,
        "join_arity": join_arity,
        "required_constructs": required,
        "gold_sql": gold_sql,
        "answer_type": answer_type,
        "target_columns": target_columns,
        "split": "train",
    }
    return task


def gold_for(task: dict) -> dict:
    """Execute gold_sql in all three scopes. entity_dependent computed here."""
    out = {}
    for scope in SCOPES:
        res = X.run_sql(task["gold_sql"], scope, db_path=DB_PATH)
        out[scope] = {"columns": list(res.columns),
                      "rows": [list(r) for r in res.rows]}
    entity_dependent = out["full_kb"] != out["train_kb"]
    return {"train_kb_gold": out["train_kb"], "train_dev_kb_gold": out["train_dev_kb"],
           "full_kb_gold": out["full_kb"], "entity_dependent": entity_dependent}


def build():
    reg = H.load_registry()
    train_recs = KB.load_kb("train_kb")
    tasks, exec_failures, empty_skips = [], [], []
    seen_ids = set()

    def add(t):
        tid = t["task_id"]
        if tid in seen_ids:
            raise Gate(f"duplicate task_id generated: {tid}")
        seen_ids.add(tid)
        try:
            g = gold_for(t)
        except Exception as e:  # noqa: BLE001
            exec_failures.append({"task_id": tid, "gold_sql": t["gold_sql"],
                                  "error": f"{type(e).__name__}: {e}"})
            return
        # README's "1-40"/"1-25" result-size caps have an implicit floor of 1
        # for LIST-shaped answers (scalar counts legitimately can be 0).
        # Correction: candidate-time company-level support checks (min
        # support >= 1) are not the same guarantee as the ACTUAL executed
        # row count being >= 1 -- the composition row_id/company mismatch
        # (fixed above) produced exactly this gap for 8 tasks. Enforced here
        # post-execution, on real train_kb_gold, as defense in depth even
        # after that root-cause fix.
        if t["answer_type"] == "set" and not g["train_kb_gold"]["rows"]:
            empty_skips.append({"task_id": tid, "gold_sql": t["gold_sql"]})
            return
        t.update(g)
        # logical_fingerprint depends on entity_dependent (a FINGERPRINT_
        # SEMANTIC_FIELDS member), which gold_for() just computed -- must be
        # set AFTER the gold update, or the stored fingerprint would silently
        # hash a None placeholder instead of the real flag.
        t["logical_fingerprint"] = H.logical_fingerprint(t)
        tasks.append(t)

    # filter / count. filter: every SCALAR_FIELDS value (arity 0, list/filter
    # cap 40). count: only AGGREGATABLE_FIELDS (arity 0 aggregation) --
    # correction, address/primary_oems carry no "aggregation" in their
    # frozen semantic ops at all (README:537-538), so they never generate a
    # count candidate now.
    for field in SCALAR_FIELDS:
        vals = scalar_field_values(train_recs, field)
        for value, cos in sorted(vals.items()):
            if MIN_SUPPORT <= len(cos) <= LIST_CAP:
                q = QUESTION["filter"].format(field_h=FIELD_LABEL[field], value=value)
                tid = f"D_v3_filter_{field}_{len(tasks):05d}"
                add(make_task(tid, q, sql_filter(field, value), answer_type="set",
                              target_columns=["company"], fields_used=[field],
                              values_used=[value], logical_components=leaf(field, value),
                              join_arity=0))
            if field in AGGREGATABLE_FIELDS and len(cos) >= MIN_SUPPORT:
                q = QUESTION["count"].format(field_h=FIELD_LABEL[field], value=value)
                tid = f"D_v3_count_{field}_{len(tasks):05d}"
                add(make_task(tid, q, sql_count(field, value), answer_type="scalar",
                              target_columns=["n"], fields_used=[field],
                              values_used=[value], logical_components=leaf(field, value),
                              join_arity=0))

    # child_filter / child_count -- arity 1 (a JOIN), so the cross-table cap
    # (25) applies, not the single-table list/filter cap (40). Correction:
    # the original cap here was LIST_CAP, which let 4 child_filter tasks
    # through at 27-36 rows.
    for field in GROUPABLE_CHILD_FIELDS:
        vals = child_field_values(train_recs, field)
        for value, cos in sorted(vals.items()):
            if not (MIN_SUPPORT <= len(cos) <= CROSS_TABLE_CAP):
                continue
            label = FIELD_LABEL[field]
            q = QUESTION["child_filter"].format(value=f"the {label} {value}")
            tid = f"D_v3_child_filter_{field}_{len(tasks):05d}"
            add(make_task(tid, q, sql_child_filter(field, value), answer_type="set",
                          target_columns=["company"], fields_used=[field],
                          values_used=[value], logical_components=leaf(field, value),
                          join_arity=1))
            q = QUESTION["child_count"].format(value=f"the {label} {value}")
            tid = f"D_v3_child_count_{field}_{len(tasks):05d}"
            add(make_task(tid, q, sql_child_count(field, value), answer_type="scalar",
                          target_columns=["n"], fields_used=[field],
                          values_used=[value], logical_components=leaf(field, value),
                          join_arity=1))

    # threshold_filter (employment)
    emp = sorted(r.employment for r in train_recs)
    thresholds = sorted({emp[len(emp) // 4], emp[len(emp) // 2],
                        emp[3 * len(emp) // 4]})
    for n in thresholds:
        support = sum(1 for r in train_recs if r.employment > n)
        if not (MIN_SUPPORT <= support <= LIST_CAP):
            continue
        q = QUESTION["threshold_filter"].format(value=n)
        tid = f"D_v3_threshold_employment_{len(tasks):05d}"
        add(make_task(tid, q, sql_threshold(n), answer_type="set",
                      target_columns=["company"], fields_used=["employment"],
                      values_used=[n], logical_components={"op": "gt",
                      "field": "employment", "value": str(n)}, join_arity=0))

    # group_by_breakdown / argmax_single. group_by_breakdown returns one row
    # PER GROUP, i.e. it's a list -- arity 1 (child fields) means a JOIN, so
    # the cross-table cap applies there, same correction as child_filter.
    for field in GROUPABLE_FIELDS + GROUPABLE_CHILD_FIELDS:
        arity = 1 if field in GROUPABLE_CHILD_FIELDS else 0
        n_groups = len(scalar_field_values(train_recs, field)
                      if field in SCALAR_FIELDS
                      else child_field_values(train_recs, field))
        cap = CROSS_TABLE_CAP if arity >= 1 else LIST_CAP
        if not (1 <= n_groups <= cap):
            continue
        q = QUESTION["group_by_breakdown"].format(field_h=FIELD_LABEL[field])
        tid = f"D_v3_group_by_{field}"
        add(make_task(tid, q, sql_group_by_breakdown(field), answer_type="set",
                      target_columns=[target_col_name(field), "n"],
                      fields_used=[field], values_used=[],
                      logical_components={"op": "group_by", "field": field,
                                         "value": field}, join_arity=arity))
        q = QUESTION["argmax_single"].format(field_h=FIELD_LABEL[field])
        tid = f"D_v3_argmax_{field}"
        add(make_task(tid, q, sql_argmax_single(field), answer_type="top_k",
                      target_columns=[target_col_name(field), "n"],
                      fields_used=[field], values_used=[],
                      logical_components={"op": "argmax", "field": field,
                                         "value": field}, join_arity=arity))

    # topk_employment
    for k in (3, 5, 10):
        q = QUESTION["topk_employment"].format(value=k)
        tid = f"D_v3_topk_employment_{k}"
        add(make_task(tid, q, sql_topk_employment(k), answer_type="top_k",
                      target_columns=["company", "employment"],
                      fields_used=["employment"], values_used=[k],
                      logical_components={"op": "topk", "field": "employment",
                                         "value": str(k)}, join_arity=0))

    # composition_filter -- held-out pair excluded from candidate generation
    for f1, f2 in COMPOSITION_PAIRS:
        for (v1, v2), cos in sorted(
                composition_candidates(train_recs, f1, f2).items()):
            label = f"{FIELD_LABEL[f1]} {v1} and {FIELD_LABEL[f2]} {v2}"
            q = QUESTION["composition_filter"].format(value=label)
            tid = f"D_v3_composition_{f1}_{f2}_{len(tasks):05d}"
            add(make_task(tid, q, sql_composition(f1, v1, f2, v2),
                          answer_type="set", target_columns=["company"],
                          fields_used=[f1, f2], values_used=[v1, v2],
                          logical_components={"op": "AND", "operands": [
                              leaf(f1, v1), leaf(f2, v2)]}, join_arity=2))

    return reg, train_recs, tasks, exec_failures, empty_skips


REQUIRED_FIELDS = ("task_id", "question", "operation_family", "fields_used",
                   "values_used", "logical_components", "logical_fingerprint",
                   "join_arity", "required_constructs", "gold_sql",
                   "answer_type", "target_columns", "entity_dependent", "split",
                   "train_kb_gold", "train_dev_kb_gold", "full_kb_gold")


def main() -> int:
    reg, train_recs, tasks, exec_failures, empty_skips = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    check("registry_frozen_before_generation", bool(reg.get("frozen_date")),
          f"HOLDOUT_REGISTRY_v3 {reg['policy_version']} dated {reg['frozen_date']}")
    check("nonzero_tasks", len(tasks) > 0, f"{len(tasks)} tasks")
    check("gold_100pct_execution", not exec_failures,
          f"0 execution failures across {len(tasks) + len(exec_failures)} "
          f"candidates" if not exec_failures
          else f"{len(exec_failures)} failed: {exec_failures[:3]}")
    check("unique_task_ids", len({t["task_id"] for t in tasks}) == len(tasks),
          f"{len(tasks)} unique task_ids")

    missing_fields = [t["task_id"] for t in tasks
                      if any(f not in t for f in REQUIRED_FIELDS)]
    check("required_fields_complete", not missing_fields,
          f"all {len(REQUIRED_FIELDS)} README-required fields present on "
          f"every task" if not missing_fields else f"{missing_fields[:5]}")

    byte_id_q = [t["task_id"] for t in tasks if not t["question"].strip()]
    check("nonempty_questions", not byte_id_q, "every question is non-blank")

    refingerprinted = {t["task_id"]: H.logical_fingerprint(t) for t in tasks}
    fp_mismatch = [tid for tid, fp in refingerprinted.items()
                  if fp != next(t["logical_fingerprint"] for t in tasks
                               if t["task_id"] == tid)]
    check("logical_fingerprint_reproducible", not fp_mismatch,
          "every stored fingerprint reproduces byte-identically from its own "
          "task metadata" if not fp_mismatch else f"{fp_mismatch[:5]}")

    refamily_mismatch = [t["task_id"] for t in tasks
                         if H.classify_operation(t["gold_sql"]) != t["operation_family"]]
    check("operation_family_matches_real_scanner", not refamily_mismatch,
          "every stored operation_family reproduces from "
          "holdout_v3.classify_operation(gold_sql), the authoritative gate "
          "(README:279)" if not refamily_mismatch else f"{refamily_mismatch[:5]}")

    held_out_pair = {tuple(sorted(h)) for h in
                     reg["composition_holdouts"]["held_out_sets"]}
    comp_violations = [t["task_id"] for t in tasks
                       if tuple(sorted(t["fields_used"])) in held_out_pair]
    check("composition_holdout_pair_never_generated", not comp_violations,
          f"the held-out composition {sorted(held_out_pair)} never appears as "
          f"a task's fields_used" if not comp_violations
          else f"{comp_violations[:5]}")

    topk_tasks = [t for t in tasks if t["answer_type"] == "top_k"]
    no_tiebreak = [t["task_id"] for t in topk_tasks
                  if len(re.findall(r"ORDER BY (.+?)(?:LIMIT|$)",
                                    t["gold_sql"], re.I)[0].split(",")) < 2]
    check("deterministic_tiebreak_on_ranking_tasks", not no_tiebreak,
          f"every one of {len(topk_tasks)} top_k tasks orders by metric plus "
          f"at least one tie-break column (README:510-513)"
          if not no_tiebreak else f"{no_tiebreak[:5]}")

    # row_id may appear only inside JOIN...ON clauses in this pool -- verify no
    # WHERE clause filters on it (README:541-543).
    row_id_bad = []
    for t in tasks:
        sql = t["gold_sql"]
        # Strip every "JOIN ... ON ..." clause, then check what's left for row_id
        stripped = re.sub(r"JOIN\s+\w+\s+\w+\s+ON\s+[^\n]*?(?=(JOIN|WHERE|GROUP|ORDER|$))",
                          " ", sql, flags=re.I)
        if re.search(r"\brow_id\b", stripped, re.I):
            row_id_bad.append(t["task_id"])
    check("no_row_id_where_filter", not row_id_bad,
          "row_id appears only inside JOIN...ON clauses, never a WHERE filter "
          "(README:541-543)" if not row_id_bad else f"{row_id_bad[:5]}")

    entity_dep_count = sum(1 for t in tasks if t["entity_dependent"])
    check("entity_dependent_flag_present", all("entity_dependent" in t for t in tasks),
          f"{entity_dep_count}/{len(tasks)} tasks are entity_dependent "
          f"(full_kb_gold != train_kb_gold)")

    by_family = defaultdict(int)
    for t in tasks:
        by_family[t["operation_family"]] += 1

    # --- Regression checks for the five confirmed post-approval audit findings ---
    check("no_empty_set_answer_tasks",
          not any(t["answer_type"] == "set" and not t["train_kb_gold"]["rows"]
                 for t in tasks),
          f"every set-answer task has >=1 train_kb_gold row "
          f"({len(empty_skips)} empty candidates excluded before reaching "
          f"the pool)")

    count_family_ids = {t["task_id"] for t in tasks
                        if t["task_id"].startswith(("D_v3_count_",
                                                    "D_v3_child_count_"))}
    distinct_mismatch = []
    for t in tasks:
        if t["task_id"] in count_family_ids:
            u = t["gold_sql"].upper()
            if "COUNT(*)" in u or "COUNT( * )" in u:
                distinct_mismatch.append(t["task_id"])
    check("count_uses_distinct_company_not_count_star", not distinct_mismatch,
          "every count/child_count task's gold_sql uses COUNT(DISTINCT "
          "company), never COUNT(*) (a multi-row company must count once, "
          "not once per row)" if not distinct_mismatch
          else f"{distinct_mismatch[:5]}")

    forbidden_agg = [t["task_id"] for t in tasks
                     if t["task_id"].startswith("D_v3_count_")
                     and t["fields_used"][0] not in AGGREGATABLE_FIELDS]
    check("no_aggregation_on_filter_only_fields", not forbidden_agg,
          f"no count task targets a field outside AGGREGATABLE_FIELDS "
          f"(address, primary_oems carry only 'filter' in "
          f"FIELD_SEMANTIC_OPERATIONS -- README:537-538)"
          if not forbidden_agg else f"{forbidden_agg[:5]}")

    sentinel_in_groupby = [t["task_id"] for t in tasks
                           if t["operation_family"] == "group_by"
                           and any(str(r[0]) in SENTINEL_VALUES
                                  for r in t["train_kb_gold"]["rows"])]
    check("no_sentinel_as_group_by_category", not sentinel_in_groupby,
          "no group_by_breakdown task's gold rows contain a frozen sentinel "
          "as a category value" if not sentinel_in_groupby
          else f"{sentinel_in_groupby[:5]}")

    cap_violations = [t["task_id"] for t in tasks
                      if t["answer_type"] == "set" and (
                          (t["join_arity"] >= 1 and
                           len(t["train_kb_gold"]["rows"]) > CROSS_TABLE_CAP) or
                          (t["join_arity"] == 0 and
                           len(t["train_kb_gold"]["rows"]) > LIST_CAP))]
    check("result_size_within_caps_by_join_arity", not cap_violations,
          f"every set-answer task's row count is within its arity-appropriate "
          f"cap (arity 0: <= {LIST_CAP}, arity >= 1: <= {CROSS_TABLE_CAP})"
          if not cap_violations else f"{cap_violations[:5]}")

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for t in tasks:
            fh.write(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n")
    sha = H.sha256_file(OUT)

    _audit(reg, tasks, by_family, checks, sha)

    print(f"\nAll Phase 12 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  tasks {len(tasks)}")
    return 0


def _audit(reg, tasks, by_family, checks, sha):
    L = ["# TASK_POOL_v3\n",
         "Phase 12 — `STRUCTURED_TASK_POOL_v3.jsonl`, the canonical source for "
         "C (train_kb_gold) and D (gold_sql), rendered in Phases 13-14.\n",
         "## Provenance\n", "```text",
         f"artifact          datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl",
         f"sha256            {sha}",
         f"generator         {GENERATOR_VERSION}",
         f"scope             candidate generation from train_kb (README:495)",
         f"holdout registry  {reg['policy_version']} frozen {reg['frozen_date']}",
         "```\n",
         "## Operation family distribution\n", "| operation_family | tasks | "
         "held out from C/D? |", "|---|--:|---|"]
    for fam in sorted(by_family):
        held = "YES" if fam in H.HELD_OUT_OPERATIONS else "no"
        L.append(f"| `{fam}` | {by_family[fam]} | {held} |")
    L += ["", f"**Total: {len(tasks)} tasks.**\n",
          "A held-out family's tasks remain in this pool (they are the source "
          "material for the Phase 22 operation-heldout probe); eligibility for "
          "C/D training is a Phase 13/14 computation, not a pool-generation "
          "exclusion, per README's own eligibility/training-target distinction.\n",
          "## Operation catalogue (documented scope decision)\n",
          "filter, count, child_filter, child_count, threshold_filter, "
          "group_by_breakdown, argmax_single, topk_employment, "
          "composition_filter. Fields drawn from `holdout_v3."
          "FIELD_SEMANTIC_OPERATIONS`, the frozen field/operation map — never a "
          "separately invented list. `product_or_service` (semantic_filter, "
          "free text), `location` (redundant with the derived `city`/`county` "
          "columns), `row_id` and `company` (no natural aggregate/filter shape) "
          "are out of scope for this catalogue. `limit_only` (LIMIT without "
          "ORDER BY) is not manufactured here — README never requires it of "
          "Phase 12, and a genuinely non-deterministic gold query would "
          "contradict this protocol's own tie-break requirements; the Phase 22 "
          "operation-heldout probe may need to construct it separately.\n",
          "## Composition holdout\n",
          f"held-out pair {reg['composition_holdouts']['held_out_sets']} — "
          "excluded from candidate generation entirely, not merely from "
          "training rendering, so it never reaches the pool at all.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        L.append(f"| `{n}` | {'PASS' if ok else 'FAIL'} | {d} |")
    L.append("")
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, H.HoldoutError) as e:
        print(f"\nPHASE 12 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
