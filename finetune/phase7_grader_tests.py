"""Phase 7 gate -- executor and grader unit/fault suite, then the audit.

Synthetic fixtures only. Phase 7 does not generate the structured task pool, C/D
datasets, probes or Q42, and runs no model inference. Infrastructure-level
full_kb row counts are used; no real test prediction, per-item test correctness,
or Q42 content is inspected or logged.

A failing gate writes no artifact.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sqlexec_v3 as X      # noqa: E402
import grade_v3 as G        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "datasets_v3" / "gnem_v3.sqlite"
OUT_AUDIT = ROOT / "validation_v3" / "GRADER_VALIDATION_v3.md"

EXPECTED_DB_SHA = "7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b"
EXPECTED_SCOPE_ROWS = {"train_kb": 148, "train_dev_kb": 165, "full_kb": 205}

# Phase 6 frozen budget, reused rather than reinvented.
USABLE_CONTEXT, MAX_NEW_TOKENS = 32768, 1024
MAX_INPUT_TOKENS = USABLE_CONTEXT - MAX_NEW_TOKENS


class Gate(Exception):
    """A Phase 7 invariant failed. No artifact is written."""


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    db_sha = sha256_file(DB)
    if db_sha != EXPECTED_DB_SHA:
        raise Gate(f"frozen database drifted: {db_sha}")
    check("frozen_db_sha_unchanged", True, db_sha)

    # ================= scope is required, no default =====================
    try:
        X.run_sql("SELECT 1")                       # type: ignore[call-arg]
        check("omitted_scope_rejected", False, "*** ACCEPTED ***")
    except TypeError as e:
        check("omitted_scope_rejected", True, f"TypeError: {str(e)[:62]}")
    for bad, label in ((None, "None"), ("full", "'full'"),
                       ("FULL_KB", "'FULL_KB'"), (123, "int"),
                       ("train", "'train'")):
        try:
            X.run_sql("SELECT 1", bad, db_path=DB)
            check(f"scope_rejected_{label}", False, "*** ACCEPTED ***")
        except X.ScopeError:
            check(f"scope_rejected_{label}", True, "ScopeError")

    # ================= db_path must be explicit ==========================
    try:
        X.run_sql("SELECT COUNT(*) FROM companies", "full_kb")
        check("db_path_required", False, "*** defaulted ***")
    except X.ConfigError as e:
        check("db_path_required", True, f"ConfigError: {str(e)[:58]}")

    # ================= scope membership ==================================
    for scope, expected in EXPECTED_SCOPE_ROWS.items():
        r = X.run_sql("SELECT COUNT(*) FROM companies", scope, db_path=DB)
        check(f"scope_{scope}_companies", r.rows[0][0] == expected,
              f"{r.rows[0][0]} == {expected}")

    # child tables must be limited to the same row_ids as their scope
    for scope in X.KB_SCOPES:
        parent = {r[0] for r in X.run_sql(
            "SELECT row_id FROM companies", scope, db_path=DB).rows}
        leaks = {}
        for child in ("certifications", "processes", "services"):
            cids = {r[0] for r in X.run_sql(
                f"SELECT DISTINCT row_id FROM {child}", scope, db_path=DB).rows}
            if not cids <= parent:
                leaks[child] = len(cids - parent)
        check(f"child_membership_{scope}", not leaks,
              f"all child row_ids within {len(parent)} scoped parents"
              if not leaks else f"{leaks}")

    # non-leakage by identity, not merely by count
    train = {r[0] for r in X.run_sql("SELECT row_id FROM companies",
                                     "train_kb", db_path=DB).rows}
    full = {r[0] for r in X.run_sql("SELECT row_id FROM companies",
                                    "full_kb", db_path=DB).rows}
    tdev = {r[0] for r in X.run_sql("SELECT row_id FROM companies",
                                    "train_dev_kb", db_path=DB).rows}
    check("train_kb_excludes_dev_and_test",
          train < tdev < full and not (train & (full - tdev)),
          f"train {len(train)} ⊂ train_dev {len(tdev)} ⊂ full {len(full)}; "
          f"0 of {len(full - tdev)} test rows visible in train_kb")

    # ================= bypass matrix (authorizer = primary) ==============
    bypasses = []
    for t in X.LOGICAL_TABLES:
        bypasses.append((f"main.{t}", f"SELECT COUNT(*) FROM main.{t}"))
    for scope in X.KB_SCOPES:
        for v in X.PHYSICAL_VIEWS[scope]:
            bypasses.append((v, f"SELECT COUNT(*) FROM {v}"))
    for t in ("sqlite_master", "sqlite_schema", "sqlite_temp_master",
              "sqlite_temp_schema"):
        bypasses.append((t, f"SELECT COUNT(*) FROM {t}"))
    # CTE-NAME-COLLISION MATRIX. A user CTE may be named after a logical table,
    # so `source == "companies"` is NOT proof that a read came from the trusted
    # binding. Every logical name x every scope's physical view, plus nested,
    # quoted, aliased and subquery wrappings.
    cte_collisions = []
    for scope in X.KB_SCOPES:
        for logical, physical in zip(X.LOGICAL_TABLES, X.PHYSICAL_VIEWS[scope]):
            cte_collisions.append((
                f"CTE {logical} <- {physical}",
                f"WITH {logical} AS (SELECT * FROM {physical}) "
                f"SELECT COUNT(*) FROM {logical}"))
    cte_collisions += [
        ("CTE nested chain",
         "WITH companies AS (SELECT * FROM train_kb_companies), "
         "x AS (SELECT * FROM companies) SELECT COUNT(*) FROM x"),
        ("CTE quoted",
         'WITH "companies" AS (SELECT * FROM "train_kb_companies") '
         'SELECT COUNT(*) FROM "companies"'),
        ("CTE aliased",
         "WITH companies AS (SELECT * FROM train_kb_companies AS z) "
         "SELECT COUNT(*) FROM companies c"),
        ("CTE over subquery",
         "WITH companies AS (SELECT * FROM (SELECT * FROM full_kb_companies)) "
         "SELECT COUNT(*) FROM companies"),
        ("CTE over main base table",
         "WITH companies AS (SELECT * FROM main.companies) "
         "SELECT COUNT(*) FROM companies"),
        ("CTE join collision",
         "WITH companies AS (SELECT * FROM train_kb_companies), "
         "processes AS (SELECT * FROM train_kb_processes) "
         "SELECT COUNT(*) FROM companies c JOIN processes p ON c.row_id=p.row_id"),
        ("CTE comment obfuscated",
         "WITH companies AS (SELECT * /*x*/ FROM train_kb_companies) "
         "SELECT COUNT(*) FROM companies"),
    ]
    bypasses += cte_collisions
    bypasses += [
        ("pragma_table_info", "SELECT * FROM pragma_table_info('companies')"),
        ("pragma_database_list", "SELECT * FROM pragma_database_list"),
        ("PRAGMA", "PRAGMA table_info(companies)"),
        ("ATTACH", "ATTACH DATABASE ':memory:' AS m"),
        ("quoted main", 'SELECT COUNT(*) FROM "main"."companies"'),
        ("CTE over main", "WITH x AS (SELECT * FROM main.companies) SELECT COUNT(*) FROM x"),
        ("comment obfuscated", "SELECT COUNT(*) /*x*/ FROM main.companies"),
    ]
    leaked = [n for n, sql in bypasses
              if _executes(sql, "train_kb")]
    check("full_bypass_matrix_blocked", not leaked,
          f"{len(bypasses)} vectors blocked (4 base tables, 12 physical views, "
          f"{len(cte_collisions)} CTE-name collisions, 4 schema tables, pragma "
          f"TVFs, PRAGMA/ATTACH, quoted/comment forms)"
          if not leaked else f"LEAKED: {leaked}")

    # authorizer alone, with lexical validation bypassed
    auth_leaked, auth_legit = [], []
    def _structural_only(sql):
        """Run through BOTH structural layers with the LEXICAL layer disabled."""
        c = X.open_scoped_connection("train_kb", DB)
        try:
            X.structural_precheck(c, sql, "train_kb")
            return c.execute(sql).fetchall()
        finally:
            c.close()

    for n, sql in bypasses:
        try:
            _structural_only(sql)
            auth_leaked.append(n)
        except (sqlite3.DatabaseError, X.SQLPolicyError):
            pass
    con = X.open_scoped_connection("train_kb", DB)
    try:
        for label, sql in (
                ("bare", "SELECT COUNT(*) FROM companies"),
                ("alias", "SELECT COUNT(*) FROM companies c"),
                ("CTE", "WITH x AS (SELECT * FROM companies) SELECT COUNT(*) FROM x"),
                ("nested CTE", "WITH a AS (SELECT * FROM companies), "
                               "b AS (SELECT * FROM a) SELECT COUNT(*) FROM b"),
                ("subquery", "SELECT COUNT(*) FROM (SELECT * FROM companies)"),
                ("quoted", 'SELECT COUNT(*) FROM "companies"'),
                ("3-table join", "SELECT COUNT(*) FROM companies c "
                                 "JOIN processes p ON c.row_id=p.row_id "
                                 "JOIN services s ON c.row_id=s.row_id")):
            try:
                _structural_only(sql)
            except (sqlite3.DatabaseError, X.SQLPolicyError):
                auth_legit.append(label)
    finally:
        con.close()
    cte_leaked = [n for n, sql in cte_collisions
                  if _survives_structural(sql)]
    check("cte_name_collision_blocked_structurally", not cte_leaked,
          f"{len(cte_collisions)} CTE-name-collision vectors denied by the "
          f"structural layer with lexical validation disabled"
          if not cte_leaked else f"LEAKED: {cte_leaked}")

    check("structural_layers_alone_block_all_bypasses", not auth_leaked,
          f"lexical layer disabled; {len(bypasses)} vectors still denied by the "
          f"EXPLAIN pre-check + per-object authorizer"
          if not auth_leaked else f"LEAKED: {auth_leaked}")
    check("structural_layers_allow_legitimate_sql", not auth_legit,
          "bare/alias/CTE/nested-CTE/subquery/quoted/3-table-join all permitted"
          if not auth_legit else f"WRONGLY DENIED: {auth_legit}")

    # ================= read-only ==========================================
    writes = [("INSERT", "INSERT INTO companies VALUES (999)"),
              ("UPDATE", "UPDATE companies SET company='x'"),
              ("DELETE", "DELETE FROM companies"),
              ("DROP", "DROP TABLE companies"),
              ("CREATE", "CREATE TABLE z(a)"),
              ("ALTER", "ALTER TABLE companies ADD COLUMN z TEXT"),
              ("REPLACE", "REPLACE INTO companies VALUES (999)"),
              ("VACUUM", "VACUUM"),
              ("DETACH", "DETACH DATABASE m"),
              ("PRAGMA writable_schema", "PRAGMA writable_schema=ON")]
    wrote = [n for n, sql in writes if _executes(sql, "full_kb")]
    check("all_write_operations_rejected", not wrote,
          f"{len(writes)} mutating operations rejected" if not wrote else f"{wrote}")
    check("db_sha_unchanged_after_write_attempts",
          sha256_file(DB) == EXPECTED_DB_SHA, sha256_file(DB))

    # ================= no result cap =====================================
    r = X.run_sql("SELECT row_id, company FROM companies", "full_kb", db_path=DB)
    check("no_row_cap_returns_all_205", r.row_count == 205,
          f"{r.row_count} rows returned, not 200")
    rc = X.run_sql("SELECT row_id, standard_family FROM certifications",
                   "full_kb", db_path=DB)
    check("no_row_cap_on_child_table", rc.row_count == 662,
          f"{rc.row_count} certification rows returned, not 200")

    # ================= absence proofs ====================================
    srcs = [ROOT / "finetune" / "sqlexec_v3.py", ROOT / "finetune" / "grade_v3.py"]
    joined = "\n".join(p.read_text(encoding="utf-8") for p in srcs)
    code_only = _code_only(joined)
    check("no_geo_import", "finetune.geo" not in code_only and "import geo" not in code_only,
          "no geo registration anywhere in the executor path")
    check("no_max_rows_cap",
          not re.search(r"max_rows", code_only) and not re.search(r"fetchmany", code_only),
          "no max_rows and no fetchmany; fetchall only")
    check("no_prompt_truncation",
          not re.search(r"truncation\s*=\s*True", code_only)
          and not re.search(r"max_length\s*=\s*\d+", code_only),
          "no truncation=True / max_length= in Phase 7 paths")
    check("no_v2_db_fallback", "gnem" + ".sqlite" not in code_only,
          "no v2 database fallback")
    check("phase6_budget_reused_not_reinvented",
          MAX_INPUT_TOKENS == 31744 and USABLE_CONTEXT == 32768,
          f"usable {USABLE_CONTEXT}, reserved {MAX_NEW_TOKENS}, max input "
          f"{MAX_INPUT_TOKENS} (frozen in Phase 6)")

    # ================= prediction/gold same-scope ========================
    q = "SELECT company FROM companies WHERE row_id = 1"
    try:
        p_, g_ = X.execute_pair(q, q, "train_kb", db_path=DB)
        same_ok = p_.scope == g_.scope == "train_kb"
    except Exception:  # noqa: BLE001
        same_ok = False
    check("execute_pair_uses_one_scope", same_ok,
          "one scope argument drives both executions; a mismatch is not expressible")

    pred_full = X.run_sql(q, "full_kb", db_path=DB)
    gold_train = X.run_sql(q, "train_kb", db_path=DB)
    try:
        X.assert_same_scope(pred_full, gold_train)
        check("scope_mismatch_raises", False, "*** SCORED ANYWAY ***")
    except X.ScopeError as e:
        check("scope_mismatch_raises", True, f"ScopeError: {str(e)[:66]}")

    # ================= grader metadata contract ==========================
    for label, item in (("missing answer_type", {"target_columns": ["company"]}),
                        ("missing target_columns", {"answer_type": "set"}),
                        ("invalid answer_type",
                         {"answer_type": "fuzzy", "target_columns": ["company"]}),
                        ("empty target_columns",
                         {"answer_type": "set", "target_columns": []}),
                        ("non-list target_columns",
                         {"answer_type": "set", "target_columns": "company"}),
                        ("scalar with 2 columns",
                         {"answer_type": "scalar", "target_columns": ["a", "b"]})):
        try:
            G.validate_item_metadata(item)
            check(f"metadata_{label.replace(' ', '_')}", False, "*** ACCEPTED ***")
        except G.GraderMetadataError:
            check(f"metadata_{label.replace(' ', '_')}", True, "GraderMetadataError")

    # ================= frozen answer-type semantics ======================
    sem, sem_detail = _answer_type_semantics()
    for name, ok, detail in sem:
        check(name, ok, detail)

    # ================= degenerate battery ================================
    battery, battery_rows = _degenerate_battery()
    for name, ok, detail in battery:
        check(name, ok, detail)

    # ================= multi-part grading (multipart_result_v1) ==========
    multipart, multipart_rows = _multipart_battery()
    for name, ok, detail in multipart:
        check(name, ok, detail)

    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    failed = [n for n, ok, _ in checks if not ok]
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    _write_audit(db_sha, checks, battery_rows, sem_detail, bypasses,
                 cte_collisions, multipart_rows)
    print(f"\nAll Phase 7 gates passed ({len(checks)} checks).")
    print(f"  executor {X.EXECUTOR_VERSION}  sha256 {sha256_file(srcs[0])}")
    print(f"  grader   {G.GRADER_VERSION}  sha256 {sha256_file(srcs[1])}")
    return 0


def _survives_structural(sql: str, scope: str = "train_kb") -> bool:
    """True if the statement runs with the LEXICAL layer disabled."""
    c = X.open_scoped_connection(scope, DB)
    try:
        X.structural_precheck(c, sql, scope)
        c.execute(sql).fetchall()
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        c.close()


def _executes(sql: str, scope: str) -> bool:
    """True if the statement produced a result (i.e. was NOT blocked)."""
    try:
        X.run_sql(sql, scope, db_path=DB)
        return True
    except Exception:  # noqa: BLE001
        return False


def _code_only(src: str) -> str:
    """Strip strings/comments so prohibition prose is not a false positive."""
    import io
    import tokenize as tk
    out = []
    try:
        for t in tk.generate_tokens(io.StringIO(src).readline):
            if t.type not in (tk.STRING, tk.COMMENT):
                out.append(t.string)
    except (tk.TokenError, IndentationError):
        return src
    return " ".join(out)


def _res(cols, rows, scope="train_kb"):
    return X.SQLResult(columns=tuple(cols), rows=tuple(rows), scope=scope,
                       row_count=len(rows))


def _answer_type_semantics():
    out, detail = [], {}

    # SET: project then dedupe; order irrelevant
    gold = _res(("company",), [("A",), ("B",)])
    r = G.compare_results(_res(("company",), [("B",), ("A",)]), gold, "set", ("company",))
    out.append(("set_order_irrelevant", r.status == "correct", r.detail))
    r = G.compare_results(_res(("company",), [("A",), ("A",), ("B",)]), gold,
                          "set", ("company",))
    out.append(("set_duplicates_deduped", r.status == "correct", r.detail))
    r = G.compare_results(_res(("company",), [("A",)]), gold, "set", ("company",))
    out.append(("set_missing_member_incorrect", r.status == "incorrect", r.detail))

    # SCALAR: exactly one scalar-compatible row
    gold_s = _res(("n",), [(5,)])
    r = G.compare_results(_res(("n",), [(5,)]), gold_s, "scalar", ("n",))
    out.append(("scalar_exact_match", r.status == "correct", r.detail))
    r = G.compare_results(_res(("n",), [(5,), (6,)]), gold_s, "scalar", ("n",))
    out.append(("scalar_multi_row_rejected", r.status == "incorrect", r.detail))
    r = G.compare_results(_res(("n",), []), gold_s, "scalar", ("n",))
    out.append(("scalar_empty_rejected", r.status == "incorrect", r.detail))

    # TOP-K: order and length preserved, never set-deduped
    gold_k = _res(("company",), [("A",), ("B",), ("C",)])
    r = G.compare_results(_res(("company",), [("A",), ("B",), ("C",)]), gold_k,
                          "top_k", ("company",))
    out.append(("topk_exact_order_correct", r.status == "correct", r.detail))
    r = G.compare_results(_res(("company",), [("B",), ("A",), ("C",)]), gold_k,
                          "top_k", ("company",))
    out.append(("topk_wrong_order_incorrect", r.status == "incorrect", r.detail))
    r = G.compare_results(_res(("company",), [("A",), ("B",)]), gold_k,
                          "top_k", ("company",))
    out.append(("topk_wrong_length_incorrect", r.status == "incorrect", r.detail))
    r = G.compare_results(_res(("company",), [("A",), ("A",), ("B",), ("C",)]),
                          gold_k, "top_k", ("company",))
    out.append(("topk_never_set_deduped", r.status == "incorrect", r.detail))

    # MULTI-PART: every part required
    gold_m = _res(("company", "county"), [("A", "Hall County"), ("B", "Cobb County")])
    r = G.compare_results(_res(("company", "county"),
                               [("A", "Hall County"), ("B", "Cobb County")]),
                          gold_m, "multi_part", ("company", "county"))
    out.append(("multipart_all_parts_correct", r.status == "correct", r.detail))
    r = G.compare_results(_res(("company", "county"),
                               [("A", "Hall County"), ("B", "WRONG")]),
                          gold_m, "multi_part", ("company", "county"))
    out.append(("multipart_partial_is_not_correct", r.status == "incorrect", r.detail))

    # the two metrics genuinely differ
    r = G.compare_results(_res(("company", "extra"), [("A", 1), ("B", 2)]),
                          _res(("company",), [("A",), ("B",)]), "set", ("company",))
    out.append(("metrics_differ_semantic_right_schema_wrong",
                r.task_result_correctness == 1.0 and r.strict_result_schema_accuracy == 0.0,
                f"task={r.task_result_correctness} schema={r.strict_result_schema_accuracy}"))
    detail["metrics_divergence"] = (
        "prediction returns the right values with an extra column: "
        "task_result_correctness=1.0 but strict_result_schema_accuracy=0.0")
    r = G.compare_results(_res(("company",), [("A",), ("B",)]),
                          _res(("company",), [("A",), ("B",)]), "set", ("company",))
    out.append(("metrics_agree_when_both_right",
                r.task_result_correctness == 1.0 and r.strict_result_schema_accuracy == 1.0,
                "both 1.0"))
    r = G.compare_results(_res(("company",), [("Z",)]),
                          _res(("company",), [("A",)]), "set", ("company",))
    out.append(("schema_right_values_wrong",
                r.task_result_correctness == 0.0 and r.strict_result_schema_accuracy == 1.0,
                f"task={r.task_result_correctness} schema={r.strict_result_schema_accuracy}"))
    return out, detail


def _degenerate_battery():
    """The frozen battery, including the v2 empty-gold regression."""
    item = {"answer_type": "set", "target_columns": ["company"]}
    empty_gold = "SELECT company FROM companies WHERE row_id = -1"
    rows, out = [], []

    cases = [
        ("empty string", "", None, "generation_failure"),
        ("whitespace only", "   \n ", None, "generation_failure"),
        ("None", None, None, "generation_failure"),
        ("refusal", "I cannot answer that question.", None, "invalid_output"),
        ("refusal as AI", "As an AI, I'm unable to help.", None, "invalid_output"),
        ("irrelevant noise", "banana banana banana", None, "parse_failure"),
        ("malformed SQL", "SELECT FROM WHERE", None, "SQL_error"),
        ("incomplete SQL", "SELECT company FROM", None, "SQL_error"),
        ("write attempt", "DELETE FROM companies", None, "parse_failure"),
        ("bypass attempt", "SELECT company FROM main.companies", None, "SQL_error"),
        ("truncated_output", "SELECT company FROM comp", True, "truncated_output"),
    ]
    for label, pred, stopped, expected in cases:
        r = G.grade_structured(item, pred, empty_gold, "train_kb", db_path=DB,
                               stopped_at_max_new_tokens=bool(stopped))
        ok = r.status == expected and r.task_result_correctness == 0.0
        out.append((f"degenerate_{label.replace(' ', '_')}", ok,
                    f"status={r.status} (expected {expected}), "
                    f"task={r.task_result_correctness}"))
        rows.append((label, expected, r.status, r.task_result_correctness))

    # THE v2 REGRESSION: empty prediction + empty gold must NOT score 1.0
    r = G.grade_structured(item, "", empty_gold, "train_kb", db_path=DB)
    out.append(("v2_regression_empty_pred_empty_gold_not_1_0",
                r.task_result_correctness == 0.0 and r.status != "correct",
                f"status={r.status}, task={r.task_result_correctness} "
                f"(v2 grade.py:170 returned 1.0 here)"))
    rows.append(("v2 empty-vs-empty-gold", "not correct", r.status,
                 r.task_result_correctness))

    # a genuinely empty gold with a valid query that also returns nothing is
    # still evaluated on its merits, not auto-1.0 by both being empty
    r = G.grade_structured(item, empty_gold, empty_gold, "train_kb", db_path=DB)
    out.append(("valid_query_empty_result_still_graded",
                r.status in ("correct", "incorrect"),
                f"status={r.status} -- a real query is graded, not short-circuited"))
    rows.append(("valid query, empty result", "graded normally", r.status,
                 r.task_result_correctness))

    # truncated output must never be parsed or executed
    r = G.grade_structured(item, "SELECT company FROM companies", empty_gold,
                           "train_kb", db_path=DB, stopped_at_max_new_tokens=True)
    out.append(("truncated_output_never_parsed",
                r.status == "truncated_output" and "not parsed" in r.detail,
                f"status={r.status}: {r.detail[:52]}"))

    # exactly one status, always from the frozen vocabulary
    out.append(("every_status_in_frozen_vocabulary",
                all(s in G.STATUSES for _, _, s, _ in rows),
                f"{len(rows)} outcomes, all within {len(G.STATUSES)} frozen statuses"))
    return out, rows


def _multipart_battery():
    """Real, heterogeneous multi-part grading against the frozen DB --
    scalar + set parts as independent keyed results, per multipart_result_v1.
    """
    out, rows = [], []
    item = {
        "answer_type": "multi_part",
        "target_columns": ["n", "company"],
        "parts": [
            {"part_id": "count", "answer_type": "scalar", "target_columns": ["n"]},
            {"part_id": "companies", "answer_type": "set", "target_columns": ["company"]},
        ],
    }
    gold_sql = {
        "count": "SELECT COUNT(*) AS n FROM certifications "
                "WHERE standard_family = 'ISO 26262'",
        "companies": "SELECT company FROM certifications "
                    "WHERE standard_family = 'ISO 26262'",
    }
    good = gold_sql["count"] + "; " + gold_sql["companies"]

    r = G.grade_structured(item, good, gold_sql, "train_kb", db_path=DB)
    out.append(("multipart_heterogeneous_all_correct",
               r.status == "correct" and r.task_result_correctness == 1.0
               and r.strict_result_schema_accuracy == 1.0,
               r.detail))
    rows.append(("scalar+set, both correct", "correct", r.status,
                r.task_result_correctness))

    wrong_second = gold_sql["count"] + "; SELECT company FROM certifications " \
                                       "WHERE standard_family = 'AS9100'"
    r = G.grade_structured(item, wrong_second, gold_sql, "train_kb", db_path=DB)
    out.append(("multipart_one_part_wrong_is_incorrect",
               r.status == "incorrect" and r.task_result_correctness == 0.0
               and r.strict_result_schema_accuracy == 1.0,
               r.detail))
    rows.append(("scalar correct, set wrong", "incorrect", r.status,
                r.task_result_correctness))

    r = G.grade_structured(item, gold_sql["count"], gold_sql, "train_kb", db_path=DB)
    out.append(("multipart_omitted_statement_is_parse_failure",
               r.status == "parse_failure" and r.task_result_correctness == 0.0,
               r.detail))
    rows.append(("second statement omitted", "parse_failure", r.status,
                r.task_result_correctness))

    r = G.grade_structured(item, good, gold_sql, "train_kb", db_path=DB,
                           stopped_at_max_new_tokens=True)
    out.append(("multipart_truncation_checked_before_any_split_or_execution",
               r.status == "truncated_output"
               and "before any part is split" in r.detail,
               r.detail))
    rows.append(("whole response truncated", "truncated_output", r.status,
                r.task_result_correctness))

    extra = good + "; SELECT 1"
    r = G.grade_structured(item, extra, gold_sql, "train_kb", db_path=DB)
    out.append(("multipart_extra_statement_correct_but_schema_fails",
               r.status == "correct" and r.task_result_correctness == 1.0
               and r.strict_result_schema_accuracy == 0.0,
               r.detail))
    rows.append(("extra undeclared statement", "correct/schema-fail", r.status,
                r.task_result_correctness))

    try:
        G.grade_structured({"answer_type": "multi_part", "target_columns": ["n"]},
                          good, gold_sql, "train_kb", db_path=DB)
        out.append(("multipart_missing_parts_metadata_fails_closed", False,
                   "*** NOT RAISED ***"))
    except G.GraderMetadataError as e:
        out.append(("multipart_missing_parts_metadata_fails_closed", True,
                   f"GraderMetadataError: {str(e)[:60]}"))

    # D.20 positional pairing: out-of-order statements grade against the
    # WRONG declared part (parts[] order is authoritative, not content-matched)
    swapped = gold_sql["companies"] + "; " + gold_sql["count"]
    r = G.grade_structured(item, swapped, gold_sql, "train_kb", db_path=DB)
    out.append(("multipart_positional_pairing_is_literal_not_smart",
               r.status in ("SQL_error", "incorrect", "invalid_output"),
               f"swapped statement order grades against the wrong declared "
               f"part rather than being silently reordered: status={r.status}"))
    rows.append(("statements emitted out of declared order",
                "graded positionally (likely fails)", r.status,
                r.task_result_correctness))

    # duplicate part_id in declared metadata is a task-authoring error
    dup_item = dict(item, parts=[item["parts"][0], item["parts"][0]])
    try:
        G.grade_structured(dup_item, good, gold_sql, "train_kb", db_path=DB)
        out.append(("multipart_duplicate_part_id_fails_closed", False,
                   "*** NOT RAISED ***"))
    except G.GraderMetadataError as e:
        out.append(("multipart_duplicate_part_id_fails_closed", True,
                   f"GraderMetadataError: {str(e)[:60]}"))

    # a genuine semicolon inside a quoted string must not be mistaken for a
    # statement boundary
    lit_cases = [
        ("SELECT 1; SELECT 2", ["SELECT 1", "SELECT 2"]),
        ("SELECT 'a;b'; SELECT 2", ["SELECT 'a;b'", "SELECT 2"]),
    ]
    lit_ok = all(G.split_top_level_statements(sql) == expected
                for sql, expected in lit_cases)
    out.append(("multipart_semicolon_in_literal_not_a_boundary", lit_ok,
               "quote-aware statement splitting confirmed"))

    # Second independent-audit round: reproduced-and-fixed bugs -------------
    bracket_ok = G.split_top_level_statements("SELECT [a;b]; SELECT 2") == \
        ["SELECT [a;b]", "SELECT 2"]
    out.append(("multipart_semicolon_in_bracket_identifier_not_a_boundary",
               bracket_ok,
               "a semicolon inside a bracket-quoted identifier [a;b] must not "
               "be mistaken for a statement boundary"))

    # answer_type="multi_part" with a plain STRING gold_sql must fail closed,
    # not silently fall through to the legacy single-query path (reproduced:
    # this previously scored 'correct'/1.0/1.0 with no parts[] ever checked).
    try:
        G.grade_structured({"answer_type": "multi_part", "target_columns": ["company"]},
                          "SELECT company FROM companies WHERE row_id=1",
                          "SELECT company FROM companies WHERE row_id=1",
                          "train_kb", db_path=DB)
        out.append(("multipart_string_gold_sql_fails_closed", False,
                   "*** NOT RAISED -- silently graded via the legacy path ***"))
    except G.GraderMetadataError as e:
        out.append(("multipart_string_gold_sql_fails_closed", True,
                   f"GraderMetadataError: {str(e)[:70]}"))

    # A dict gold_sql with a non-multi_part answer_type is equally invalid.
    try:
        G.grade_structured({"answer_type": "set", "target_columns": ["n"]},
                          "SELECT 1", {"p1": "SELECT 1"}, "train_kb", db_path=DB)
        out.append(("dict_gold_sql_requires_multipart_answer_type", False,
                   "*** NOT RAISED ***"))
    except G.GraderMetadataError as e:
        out.append(("dict_gold_sql_requires_multipart_answer_type", True,
                   f"GraderMetadataError: {str(e)[:70]}"))

    # A part with empty target_columns previously projected zero columns,
    # making any two same-row-count results compare equal regardless of
    # actual values (999 scored "correct" against gold 1). Now fails closed
    # via per-part metadata validation, before any execution.
    bad_part_item = {"answer_type": "multi_part", "target_columns": ["n"],
                     "parts": [{"part_id": "p1", "answer_type": "set",
                               "target_columns": []}]}
    try:
        G.grade_structured(bad_part_item, "SELECT 999 AS n",
                          {"p1": "SELECT 1 AS n"}, "train_kb", db_path=DB)
        out.append(("multipart_part_empty_target_columns_fails_closed", False,
                   "*** NOT RAISED -- scored despite meaningless comparison ***"))
    except G.GraderMetadataError as e:
        out.append(("multipart_part_empty_target_columns_fails_closed", True,
                   f"GraderMetadataError: {str(e)[:70]}"))

    # TimeoutError must classify as 'timeout', never generic 'SQL_error'.
    orig_execute_pair = X.execute_pair

    def _boom(*_a, **_k):
        raise TimeoutError("synthetic executor deadline")
    X.execute_pair = _boom
    try:
        r_single = G.grade_structured({"answer_type": "set", "target_columns": ["n"]},
                                     "SELECT 1 AS n", "SELECT 1 AS n",
                                     "train_kb", db_path=DB)
        out.append(("single_query_timeout_classified_correctly",
                   r_single.status == "timeout",
                   f"status={r_single.status} (expected timeout, not SQL_error)"))
        mp_item = {"answer_type": "multi_part", "target_columns": ["n"],
                  "parts": [{"part_id": "p1", "answer_type": "scalar",
                            "target_columns": ["n"]}]}
        r_multi = G.grade_structured(mp_item, "SELECT 1 AS n", {"p1": "SELECT 1 AS n"},
                                    "train_kb", db_path=DB)
        out.append(("multipart_timeout_classified_correctly",
                   r_multi.status == "timeout",
                   f"status={r_multi.status} (expected timeout, not SQL_error)"))
    finally:
        X.execute_pair = orig_execute_pair

    return out, rows


def _write_audit(db_sha, checks, battery_rows, sem_detail, bypasses,
                 cte_collisions, multipart_rows) -> None:
    ex = sha256_file(ROOT / "finetune" / "sqlexec_v3.py")
    gr = sha256_file(ROOT / "finetune" / "grade_v3.py")
    L = ["# GRADER_VALIDATION_v3\n",
         "Phase 7 — SQL execution and grading. README: this gate **blocks the "
         "canonical structured task pool, C and D generation, every structured "
         "probe, the Q42 revalidation, and final evaluation**.\n",
         "## Provenance\n", "```text",
         f"datasets_v3/gnem_v3.sqlite   {db_sha}",
         f"finetune/sqlexec_v3.py       {ex}   ({X.EXECUTOR_VERSION})",
         f"finetune/grade_v3.py         {gr}   ({G.GRADER_VERSION})",
         "```\n",
         "## Scope contract\n",
         f"Valid scopes: {', '.join(f'`{s}`' for s in X.KB_SCOPES)}. "
         "`run_sql(sql, scope, *, db_path=...)` takes scope as a **required "
         "positional argument with no default**, so omitting it is a `TypeError` "
         "before any query runs — there is no implicit full-KB execution path.\n",
         "| rejected input | outcome |", "|---|---|",
         "| omitted scope | `TypeError` |", "| `None` | `ScopeError` |",
         "| `\"full\"` | `ScopeError` |", "| `\"FULL_KB\"` | `ScopeError` |",
         "| `\"train\"` | `ScopeError` |", "| non-string (`int`) | `ScopeError` |",
         "",
         "**Database path is configuration-driven.** `db_path` has no default and "
         "no fallback: omitting it raises `ConfigError`. There is no hard-coded "
         "path and no v2 database fallback.\n",
         "## Scope binding\n",
         "Model and gold SQL stay **scope-neutral** — `SELECT ... FROM companies`. "
         "The model never emits, and is never taught, a physical name like "
         "`train_kb_companies`.\n",
         "Two roles are deliberately separated:\n",
         "| component | role |", "|---|---|",
         "| Phase 5 scoped views | authoritative source of scope **membership** |",
         "| Phase 7 TEMP logical tables | execution **isolation** surface |",
         "",
         "During trusted connection initialization the selected scoped rows are read "
         "from the Phase 5 scoped view and **materialized into connection-local TEMP "
         "logical tables** (`companies`, `certifications`, `processes`, `services`). "
         "Model and gold SQL then execute against those TEMP tables only, and after "
         "initialization any read of the `main` schema is structurally denied.\n",
         "Initialization order is fixed:\n", "```text",
         "1. open frozen DB with mode=ro",
         "2. materialize the four TEMP logical tables from the Phase 5 scoped views",
         "   (the only point at which `main` is read -- trusted setup)",
         "3. PRAGMA query_only = ON",
         "4. install the structural authorizer",
         "5. execute model/gold SQL -- TEMP only",
         "```\n",
         "`query_only` is set **after** materialization, because populating the TEMP "
         "tables is itself a write to the temp schema.\n",
         "## Structural authorization (primary defence)\n",
         "`sqlite3.Connection.set_authorizer` inspects every object the prepared "
         "statement actually touches, so it cannot be evaded by aliases, quoting, "
         "CTEs, subqueries, comments or formatting. Lexical validation is retained "
         "as **defence in depth only**.\n",
         "Scoped rows are **materialized into temp tables**, populated from the "
         "Phase 5 scoped views. That is a security property, not an optimization: "
         "afterwards a legitimate query reads only the temp schema and never "
         "touches `main`, so the rule reduces to one forgery-proof condition:\n",
         "```text",
         "legitimate read    READ  db=None    (materialized TEMP logical table)  allow",
         "ANY bypass         READ  db='main'                                      DENY",
         "```\n",
         "**Source callback names are not trusted as authorization identity.** "
         "A superseded design keyed on `source in LOGICAL_TABLES` as evidence that "
         "a read came from a trusted binding. That is unsound: SQLite reports a user-defined CTE named "
         "`companies` with `source == \"companies\"`, identically to the trusted "
         "binding, so the check was forgeable by naming a CTE after a logical "
         "table. Review found a working structural-only bypass, "
         "`WITH companies AS (SELECT * FROM train_kb_companies) SELECT COUNT(*) "
         "FROM companies`, which returned 148 instead of being denied. The "
         "mechanism was redesigned rather than patched: the schema an object "
         "lives in cannot be forged by naming, so authorization now keys on it "
         "alone.\n",
         "**The earlier Phase 7 audit overstated the structural guarantee.** It "
         "claimed every bypass was blocked with lexical validation disabled; that "
         "held for the vectors then tested, but the CTE-name-collision class was "
         "untested and would have passed. This record is kept deliberately — the "
         "audit should show what was wrong, not only what is now right.\n",
         "Materialization preserves the data exactly — all 12 scope x table "
         "combinations are row- and column-identical to their Phase 5 views, "
         "including NULL city/county and the AVS trailing-space address.\n",
         "### Deny surface\n",
         f"- all 4 raw base tables via `main.`\n"
         f"- all 12 Phase 5 physical scoped views\n"
         f"- `sqlite_master`, `sqlite_schema`, `sqlite_temp_master`, "
         f"`sqlite_temp_schema`\n"
         f"- `pragma_*` table-valued functions and direct `PRAGMA`\n"
         f"- `ATTACH` / `DETACH` and every write verb\n"
         f"- quoted, schema-qualified, comment-obfuscated and CTE-wrapped variants\n",
         f"- CTE-name collisions wrapping every physical view\n",
         f"**{len(bypasses)} bypass vectors tested; all blocked** — including "
         f"**{len(cte_collisions)} CTE-name-collision vectors** covering all four "
         "logical names against every scope's physical views, plus nested, "
         "quoted, aliased, subquery-wrapped, joined and comment-obfuscated "
         "forms. All remain blocked with the lexical layer disabled, so the "
         "structural layer is the primary defence and not a backstop.\n",
         "## Scope results\n",
         "| scope | logical `companies` rows | child tables |", "|---|---|---|"]
    for s, n in EXPECTED_SCOPE_ROWS.items():
        L.append(f"| `{s}` | {n} | all child `row_id`s within the scoped parents |")
    L += ["",
          "Membership is verified by identity, not merely by count: "
          "`train_kb` ⊂ `train_dev_kb` ⊂ `full_kb`, and zero test rows are "
          "reachable under `train_kb`.\n",
          "## Prediction/gold scope invariant\n",
          "`execute_pair(pred_sql, gold_sql, scope)` passes **one** scope value to "
          "both executions, so `pred_scope=train_kb, gold_scope=full_kb` is not "
          "expressible in the ordinary scoring path. `assert_same_scope` "
          "additionally raises `ScopeError` on any mismatched pair before a score "
          "exists — a scope mismatch is a harness bug, not a model error.\n",
          "## SQL safety and result cap\n",
          "Defence in depth: `mode=ro` + `PRAGMA query_only=ON` + authorizer + "
          "single-read-statement validation. INSERT/UPDATE/DELETE/CREATE/DROP/"
          "ALTER/REPLACE/VACUUM/ATTACH/DETACH and writable PRAGMAs are all "
          "rejected, and the database SHA is unchanged after the write battery.\n",
          "**No result cap.** No `max_rows`, no `fetchmany`, no injected `LIMIT`. "
          "A `full_kb` query over `companies` returns **205 rows, not 200**, and "
          "`certifications` returns all **662**.\n",
          "**No semantic rewriting.** Scope binding is infrastructure; nothing else "
          "about a query is altered — no repair, clause removal, injected `LIMIT`, "
          "`ORDER BY` change, reprojection, or result truncation.\n",
          "## Prompt truncation\n",
          "v3 never ported the historical `truncation=True, max_length=24576` "
          "evaluator path, so Phase 7 **proves its absence** rather than inventing "
          "a migration. The Phase 6 budget is reused, not reinvented:\n", "```text",
          f"usable context   {USABLE_CONTEXT}",
          f"max_new_tokens   {MAX_NEW_TOKENS}",
          f"max input        {MAX_INPUT_TOKENS}",
          "```\n",
          "Also proven absent from the Phase 7 paths: the v2 geo registration, the "
          "`max_rows=200` cap, and any v2 database fallback.\n",
          "## Grader metadata contract\n",
          "`answer_type` and `target_columns` are **supplied by the generator** and "
          "never inferred from question wording, predicted SQL, gold SQL, "
          "prediction contents or gold result shape. Missing or invalid metadata "
          "raises `GraderMetadataError` — there is no fallback.\n",
          "### Frozen answer-type semantics\n",
          "| type | rule |", "|---|---|",
          "| `set` | project target columns, then dedupe; order irrelevant |",
          "| `scalar` | exactly one scalar-compatible target column and one row |",
          "| `top_k` | order and length preserved; **never** set-deduped |",
          "| `multi_part` | every required part correct; partial is not correct |",
          "",
          "### Multi-part encoding (Phase 9 correction: now frozen)\n",
          f"{G.MULTI_PART_ENCODING_NOTE}\n",
          "### Multi-part battery (real DB execution)\n",
          "| case | expected | status | task_result_correctness |",
          "|---|---|---|---|"]
    for label, expected, status, score in multipart_rows:
        L.append(f"| {label} | `{expected}` | `{status}` | {score} |")
    L += ["",
          "## Two metrics, genuinely distinct\n",
          f"- **`task_result_correctness`** (primary)\n"
          f"- **`strict_result_schema_accuracy`** (secondary)\n",
          f"Divergence fixture: {sem_detail.get('metrics_divergence', '')}. The "
          "reverse case is also covered — right schema, wrong values — so the "
          "secondary metric can never stand in for the primary.\n",
          "## Degenerate-prediction battery\n",
          "| prediction | expected | status | task_result_correctness |",
          "|---|---|---|---|"]
    for label, expected, status, score in battery_rows:
        L.append(f"| {label} | `{expected}` | `{status}` | {score} |")
    L += ["",
          "**The v2 regression is fixed.** `v2 finetune/grade.py:170` returned 1.0 "
          "when prediction and gold were both empty; an empty, refusing, noisy or "
          "malformed prediction therefore scored perfectly on an empty-gold item. "
          "Here a degenerate prediction is classified by its own explicit status "
          "**before** any comparison, so it can never coincide with an empty gold.\n",
          "`truncated_output` originates **only** from explicit generation-stop "
          "metadata, never inferred from what the text looks like. When set, the "
          "parser and executor are not invoked and no normal correctness is "
          "computed.\n",
          f"Every item receives exactly one status from the frozen vocabulary: "
          f"{', '.join(f'`{s}`' for s in G.STATUSES)}.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        L.append(f"| `{name}` | {'PASS' if ok else 'FAIL'} | {detail} |")
    L.append("")
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Gate as exc:
        print(f"\nPHASE 7 GATE FAILURE: {exc}", file=sys.stderr)
        print("No artifact written. No gate weakened.", file=sys.stderr)
        raise SystemExit(1)
