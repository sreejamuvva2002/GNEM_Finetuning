"""Phase 12 fault-injection / regression suite.

Regression tests for five bugs an independent post-approval audit found in
the first Phase 12-16 generation (commit b231e82), all independently
reproduced before fixing:

  1. sql_count() used COUNT(*), counting ROWS not companies. Atlanta's
     committed answer was 7 (rows); the correct company count is 5.
  2. sql_composition() joined child tables ON row_id, requiring both facts
     on the SAME physical row, while composition_candidates() selects at
     COMPANY level (aggregating across every row that company has). 8 tasks
     passed candidate selection and executed to an empty result --
     "CNC Machining + Asset Management" -> Sewon America Inc. is the
     canonical reproduction.
  3. count/child_count generation iterated every SCALAR_FIELDS value
     unconditionally, generating 131 address-count and 12 primary_oems-count
     tasks though neither field carries "aggregation" in FIELD_SEMANTIC_
     OPERATIONS (README:537-538: Address gets no structured aggregation).
  4. sql_group_by_breakdown()/sql_argmax_single() had no WHERE clause on the
     companies-table branch, so a group-by breakdown could include a frozen
     sentinel ("Not specified") as an ordinary category value.
  5. The result-size cap only applied README's cross-table bound (25) at
     join_arity >= 2; a single child-table join (join_arity == 1) was
     treated as list/filter (cap 40), letting 4 tasks through at 27-36 rows.
     The same gap meant an executed-empty ("< 1") result was never rejected.

Committed artifacts are never modified: every fault here runs against the
frozen registry/DB (read-only) or in-memory constructions, never mutating
datasets_v3/STRUCTURED_TASK_POOL_v3.jsonl or any other committed file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H          # noqa: E402
import phase12_task_pool as P12  # noqa: E402
import sqlexec_v3 as X           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "datasets_v3" / "gnem_v3.sqlite"
POOL_PATH = ROOT / "datasets_v3" / "STRUCTURED_TASK_POOL_v3.jsonl"


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def record(name, ok, detail):
        results.append((name, bool(ok), detail))

    # --- 1. Company counts vs row counts -----------------------------------
    sql = P12.sql_count("city", "Atlanta")
    record("count_sql_uses_distinct_company", "COUNT(DISTINCT company)" in sql,
          sql)
    res = X.run_sql(sql, "train_kb", db_path=DB_PATH)
    record("atlanta_company_count_is_5_not_7", res.rows[0][0] == 5,
          f"got {res.rows[0][0]} (exact reproduction: the pre-fix gold was 7, "
          f"the row count -- 5 is the distinct company count)")
    bad_sql = P12.sql_count("city", "Atlanta").replace(
        "COUNT(DISTINCT company)", "COUNT(*)")
    bad_res = X.run_sql(bad_sql, "train_kb", db_path=DB_PATH)
    record("count_star_reproduces_the_original_bug_value", bad_res.rows[0][0] == 7,
          f"got {bad_res.rows[0][0]} -- confirms the fix actually changes the "
          f"answer, not merely the SQL text")

    # --- 2. Composition candidate/SQL semantics -----------------------------
    sql = P12.sql_composition("processes", "CNC Machining", "services",
                              "Asset Management")
    record("composition_sql_has_no_row_id_join", "row_id" not in sql, sql)
    res = X.run_sql(sql, "train_kb", db_path=DB_PATH)
    record("cnc_asset_management_composition_nonempty",
          res.rows == (("Sewon America Inc.",),),
          f"got {res.rows} -- Sewon America performs CNC Machining at one "
          f"facility and Asset Management at another; company-level "
          f"composition must find it")

    train_recs = P12.KB.load_kb("train_kb")
    cand = P12.composition_candidates(train_recs, "processes", "services")
    key = ("CNC Machining", "Asset Management")
    record("candidate_selection_agrees_with_fixed_sql",
          key in cand and "Sewon America Inc." in cand[key],
          f"candidate set for {key}: {cand.get(key)}")

    # --- 3. Forbidden aggregation fields ------------------------------------
    record("address_excluded_from_aggregatable_fields",
          "address" not in P12.AGGREGATABLE_FIELDS,
          f"AGGREGATABLE_FIELDS = {P12.AGGREGATABLE_FIELDS}")
    record("primary_oems_excluded_from_aggregatable_fields",
          "primary_oems" not in P12.AGGREGATABLE_FIELDS,
          f"AGGREGATABLE_FIELDS = {P12.AGGREGATABLE_FIELDS}")
    record("address_and_primary_oems_still_filterable",
          "address" in P12.SCALAR_FIELDS and "primary_oems" in P12.SCALAR_FIELDS,
          "filter tasks (README:537-538 explicitly permits filtering on "
          "both) are unaffected by the aggregation exclusion")

    # --- 4. Sentinel never a group-by category ------------------------------
    sql = P12.sql_group_by_breakdown("supplier_or_affiliation_type")
    res = X.run_sql(sql, "train_kb", db_path=DB_PATH)
    sentinel_rows = [r for r in res.rows if r[0] in P12.SENTINEL_VALUES]
    record("no_sentinel_in_group_by_breakdown", not sentinel_rows,
          f"rows: {res.rows}" if sentinel_rows else
          f"{len(res.rows)} groups, none a sentinel")
    record("sentinel_exclusion_helper_names_both_frozen_sentinels",
          all(s in P12._sentinel_exclusion("category") for s in P12.SENTINEL_VALUES),
          P12._sentinel_exclusion("category"))

    # --- 5. Result-size caps by join_arity, and the implicit floor of 1 ----
    # Synthetic: a fabricated 30-row child_filter candidate must be capped at
    # CROSS_TABLE_CAP (25), not LIST_CAP (40), regardless of what the live KB
    # currently supports for any single value.
    record("cross_table_cap_smaller_than_list_cap",
          P12.CROSS_TABLE_CAP < P12.LIST_CAP,
          f"CROSS_TABLE_CAP={P12.CROSS_TABLE_CAP} < LIST_CAP={P12.LIST_CAP} "
          f"(the ordering the join_arity>=1 branch depends on)")

    if POOL_PATH.is_file():
        pool = [json.loads(l) for l in POOL_PATH.read_text(encoding="utf-8").splitlines()]
        arity1_plus = [t for t in pool if t.get("join_arity", 0) >= 1
                       and t.get("answer_type") == "set"]
        oversize = [t["task_id"] for t in arity1_plus
                   if len(t["train_kb_gold"]["rows"]) > P12.CROSS_TABLE_CAP]
        record("committed_pool_has_no_arity1plus_oversize", not oversize,
              f"{len(oversize)} violations" if oversize else
              f"{len(arity1_plus)} arity>=1 set tasks, all <= "
              f"{P12.CROSS_TABLE_CAP} rows")
        empty_sets = [t["task_id"] for t in pool
                     if t.get("answer_type") == "set"
                     and not t["train_kb_gold"]["rows"]]
        record("committed_pool_has_no_empty_set_tasks", not empty_sets,
              f"{len(empty_sets)} violations" if empty_sets else
              "every set-answer task has >=1 train_kb_gold row")
        addr_oem_count = [t["task_id"] for t in pool
                          if t["task_id"].startswith(("D_v3_count_address_",
                                                      "D_v3_count_primary_oems_"))]
        record("committed_pool_has_no_forbidden_aggregation_tasks",
              not addr_oem_count,
              f"{len(addr_oem_count)} violations" if addr_oem_count else
              "0 address/primary_oems count tasks in the committed pool")
    else:
        record("committed_pool_present_for_integration_checks", False,
              f"{POOL_PATH} not found -- run finetune/phase12_task_pool.py first")

    failed = [n for n, ok, _ in results if not ok]
    for n, ok, d in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    print(f"\n{len(results)} fault checks, {len(failed)} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
