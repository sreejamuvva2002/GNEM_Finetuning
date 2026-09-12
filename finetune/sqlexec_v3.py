"""Phase 7 -- scope-bound, read-only SQL executor.

Closes the silent-failure paths README Phase 7 names, all of which "produce
plausible numbers rather than errors".

SCOPE IS REQUIRED. `run_sql(sql, scope, *, db_path=...)` takes scope as a
required positional argument with no default. Omitting it is a TypeError; None,
an unknown string, a case variant and a non-string all raise ScopeError. There
is no unscoped convenience path and no implicit full_kb.

MODEL SQL STAYS SCOPE-NEUTRAL. The model writes `SELECT ... FROM companies`.
The executor -- not the model -- chooses which rows are visible. Physical names
like `train_kb_companies` are infrastructure and are never taught to a model.

TWO DISTINCT ROLES, deliberately separated:

    Phase 5 scoped views   authoritative source of scope MEMBERSHIP
    Phase 7 TEMP tables    execution ISOLATION surface

During trusted connection initialization the selected scoped rows are read from
the Phase 5 scoped view and MATERIALIZED into connection-local TEMP logical
tables -- `companies`, `certifications`, `processes`, `services`. Model and gold
SQL then execute against those TEMP tables only. After initialization, any read
from the `main` schema is structurally denied.

Initialization order matters and is fixed:

    1. open the frozen DB with mode=ro
    2. materialize the four TEMP logical tables from the Phase 5 scoped views
       (the only point at which `main` is read, and it is trusted setup)
    3. PRAGMA query_only = ON
    4. install the structural authorizer
    5. execute the model/gold SQL -- TEMP only

query_only is set AFTER materialization, because populating the TEMP tables is
itself a write to the temp schema.

STRUCTURAL AUTHORIZATION IS THE PRIMARY DEFENCE. `sqlite3.Connection.
set_authorizer` inspects every object the prepared statement actually touches,
so it cannot be fooled by aliases, quoting, CTEs, subqueries, comments or
formatting. Because a legitimate query reads only materialized TEMP tables, the
rule is one forgery-proof condition:

    legitimate read    READ  db=None    (TEMP logical table)   allow
    ANY bypass         READ  db='main'                         DENY

SOURCE CALLBACK NAMES ARE NOT TRUSTED AS AUTHORIZATION IDENTITY. A superseded
design keyed on `source in LOGICAL_TABLES` as proof that a read came from a
trusted binding. That was unsound: SQLite reports a user-defined CTE named
`companies` with `source == "companies"`, identically to a trusted binding, so
the check was forgeable by naming a CTE after a logical table. `source` is now
never consulted; authorization keys on the schema an object lives in, which a
query cannot forge by naming. Lexical validation is kept as defence in depth
only, never as the primary layer.

NO RESULT CAP. Complete results always. README permits a safety ceiling only if
it raises; none is authorized, so none is introduced -- and none is smuggled in
under another name.

NO SEMANTIC REWRITING. Scope binding is infrastructure. Nothing else about the
query is altered: no repair, no clause removal, no injected LIMIT, no ORDER BY
change, no reprojection, no result truncation. A malformed query is an error.

Not ported from v2 `finetune/sqlexec.py`: the unconditional
`from finetune.geo import register` (line 60), the `max_rows=200` fetch cap
(line 44), and the hard-coded default `db_path`. Ported: `mode=ro` and
`PRAGMA query_only = ON` (lines 54-57).
"""

from __future__ import annotations

import re
import math
import time
import sqlite3
from dataclasses import dataclass
from pathlib import Path

EXECUTOR_VERSION = "sqlexec_v3.1_A002"
DEFAULT_TIMEOUT_SECONDS = 5.0

KB_SCOPES = ("train_kb", "train_dev_kb", "full_kb")
LOGICAL_TABLES = ("companies", "certifications", "processes", "services")
PHYSICAL_VIEWS = {s: tuple(f"{s}_{t}" for t in LOGICAL_TABLES) for s in KB_SCOPES}
ALL_PHYSICAL_VIEWS = frozenset(v for vs in PHYSICAL_VIEWS.values() for v in vs)

# SQLite introspection surfaces. Model SQL may not read schema by any of these.
INTROSPECTION_TABLES = frozenset({
    "sqlite_master", "sqlite_schema", "sqlite_temp_master", "sqlite_temp_schema",
    "sqlite_sequence", "sqlite_stat1", "sqlite_stat4",
})


class ScopeError(ValueError):
    """Scope missing, None, unknown, or not a valid scope name."""


class SQLPolicyError(ValueError):
    """The statement is not an authorized read of the selected scope."""


class ConfigError(ValueError):
    """No explicit database path was supplied by configuration."""


@dataclass(frozen=True)
class SQLResult:
    columns: tuple[str, ...]
    rows: tuple[tuple, ...]
    scope: str
    row_count: int


# ---------------------------------------------------------------------------
# Lexical validation -- DEFENCE IN DEPTH ONLY. The authorizer is primary.
# ---------------------------------------------------------------------------
_WRITE_VERBS = ("insert", "update", "delete", "create", "drop", "alter",
                "replace", "vacuum", "attach", "detach", "reindex", "analyze",
                "begin", "commit", "rollback", "savepoint", "release", "trigger")


def _strip_sql_noise(sql: str) -> str:
    """Remove comments and collapse whitespace so trivial obfuscation of the
    lexical layer does not change what it sees. The authorizer does not depend
    on this."""
    # Lex literal spans before comments: semicolons and SQL-looking words
    # inside recorded text are data, not additional statements or commands.
    pattern = r"'(?:(?:'')|[^'])*'|\"(?:(?:\"\")|[^\"])*\"|`[^`]*`|\[[^\]]*\]|--[^\n]*|/\*.*?\*/"
    s = re.sub(pattern, " ", sql, flags=re.S)
    return re.sub(r"\s+", " ", s).strip()


def validate_sql_lexically(sql: str) -> None:
    if not isinstance(sql, str) or not sql.strip():
        raise SQLPolicyError("empty SQL")
    clean = _strip_sql_noise(sql)
    body = clean.rstrip(";")
    if ";" in body:
        raise SQLPolicyError("only a single statement may be executed")
    low = body.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise SQLPolicyError("only SELECT/WITH queries are permitted")
    for verb in _WRITE_VERBS:
        if re.search(rf"(?<![a-z_]){verb}(?![a-z_])", low):
            raise SQLPolicyError(f"statement verb {verb!r} is not permitted")
    if re.search(r"\bpragma\b", low) or re.search(r"\bpragma_[a-z_]+", low):
        raise SQLPolicyError("PRAGMA and pragma_* introspection are not permitted")
    for name in INTROSPECTION_TABLES:
        if re.search(rf"(?<![a-z_]){name}(?![a-z_])", low):
            raise SQLPolicyError(f"schema introspection via {name!r} is not permitted")
    for view in sorted(ALL_PHYSICAL_VIEWS):
        if re.search(rf"(?<![a-z_]){view}(?![a-z_])", low):
            raise SQLPolicyError(
                f"physical scoped view {view!r} is infrastructure and may not be "
                f"named by a query; use the logical table name")
    if re.search(r"(?<![a-z_])(main|temp)\s*\.", low):
        raise SQLPolicyError("schema-qualified references are not permitted")


# ---------------------------------------------------------------------------
# Structural authorization -- PRIMARY defence
# ---------------------------------------------------------------------------
def _make_authorizer(scope: str):
    """Per-object structural authorization.

    THE RULE: a legitimate query reads only the materialized temp bindings, so
    ANY read of the `main` schema is a bypass -- a raw base table, a physical
    scoped view of any scope, or either hidden behind a CTE, alias or subquery.
    `source` is deliberately never consulted, because a user CTE can be named
    after a logical table and forge it.
    """
    del scope  # membership is already materialized into the temp bindings

    def authorizer(action, arg1, arg2, db_name, source):
        # Reads only. PRAGMA (hence every pragma_* table-valued function),
        # ATTACH/DETACH and every write action are refused outright.
        if action not in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                          sqlite3.SQLITE_READ):
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_READ:
            if db_name == "main":
                return sqlite3.SQLITE_DENY
            if arg1 and arg1.lower() in INTROSPECTION_TABLES:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    return authorizer


def structural_precheck(con: sqlite3.Connection, sql: str, scope: str) -> None:
    """Statement-level structural authorization, using an EXPLAIN pre-pass.

    `EXPLAIN` *prepares* the statement -- firing the authorizer for every object
    it actually touches -- without executing it (verified: `EXPLAIN DELETE` does
    not delete). Recording those events lets the decision be made across the
    whole statement, which a stateless per-object callback cannot do.

    The invariant enforced here:

        trusted setup    may read `main`, but only while materializing the
                         selected Phase 5 scoped views into TEMP tables
        model/gold SQL   reads the TEMP logical tables
        user-time read   of the `main` schema -> denied

    `source` is not consulted: a user CTE can carry the same source name as a
    trusted binding, so it is not an authorization identity.
    """
    events: list[tuple] = []

    def recorder(action, arg1, arg2, db_name, source):
        events.append((action, arg1, arg2, db_name, source))
        return sqlite3.SQLITE_OK

    con.set_authorizer(recorder)
    try:
        con.execute("EXPLAIN " + sql).fetchall()
    except sqlite3.DatabaseError as e:
        raise SQLPolicyError(f"statement could not be prepared: {e}") from e
    finally:
        con.set_authorizer(_make_authorizer(scope))

    for action, arg1, _a2, db_name, _source in events:
        name = (arg1 or "").lower()
        if action not in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                          sqlite3.SQLITE_FUNCTION):
            raise SQLPolicyError(
                f"statement performs a non-read operation (action {action})")
        if name in INTROSPECTION_TABLES:
            raise SQLPolicyError(
                f"schema introspection via {name!r} is not permitted")
        # Forgery-proof: legitimate queries read only the materialized temp
        # bindings, so any `main`-schema read is a bypass regardless of how it
        # is wrapped or what any CTE is named.
        if action == sqlite3.SQLITE_READ and db_name == "main":
            kind = ("physical scoped view" if name in ALL_PHYSICAL_VIEWS
                    else "raw base table")
            raise SQLPolicyError(
                f"query reads {kind} main.{name}; only the scope-bound logical "
                f"tables ({', '.join(LOGICAL_TABLES)}) may be read")


def resolve_db_path(db_path) -> Path:
    """The database path must be supplied explicitly by configuration.

    There is no hard-coded default, no v2 fallback and no implicit discovery.
    """
    if db_path is None:
        raise ConfigError(
            "db_path must be supplied explicitly by the experiment/runtime "
            "configuration; there is no default database path and no fallback")
    p = Path(db_path)
    if not p.is_file():
        raise ConfigError(f"configured database does not exist: {p}")
    return p


def _validate_scope(scope) -> str:
    if scope is None:
        raise ScopeError(
            "SQL scope is required and must be named explicitly; got None. "
            f"Valid scopes: {', '.join(KB_SCOPES)}")
    if not isinstance(scope, str) or scope not in KB_SCOPES:
        raise ScopeError(
            f"unknown SQL scope {scope!r}; there is no default scope. "
            f"Valid scopes: {', '.join(KB_SCOPES)}")
    return scope


def open_scoped_connection(scope, db_path) -> sqlite3.Connection:
    """Read-only connection with the four logical names bound to `scope`."""
    scope = _validate_scope(scope)
    path = resolve_db_path(db_path)
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    # 2. TEMP scope bindings (before query_only -- creating them writes to temp).
    #
    # Populated FROM the Phase 5 scoped views, so those views remain the single
    # definition of what each scope contains and nothing is re-derived here.
    #
    # The rows are MATERIALIZED into temp tables rather than exposed through a
    # temp VIEW over the physical view (the SUPERSEDED design). That is a
    # deliberate security property,
    # not an optimization: afterwards a legitimate query reads ONLY the temp
    # schema and never touches `main`, which makes authorization independent of
    # `source`. `source` is not a trustworthy identity -- SQLite reports a user
    # CTE named `companies` with source == "companies", exactly as it reports
    # the trusted binding -- so any rule keyed on the source NAME is forgeable
    # by naming a CTE after a logical table.
    for logical, physical in zip(LOGICAL_TABLES, PHYSICAL_VIEWS[scope]):
        con.execute(f"CREATE TEMP TABLE {logical} AS SELECT * FROM {physical}")
    # 3. query_only, 4. per-object structural authorizer
    con.execute("PRAGMA query_only = ON")
    con.set_authorizer(_make_authorizer(scope))
    return con


def run_sql(sql, scope, *, db_path=None, timeout_seconds=DEFAULT_TIMEOUT_SECONDS) -> SQLResult:
    """Execute read-only SQL against an EXPLICIT scope.

        run_sql(sql)                  -> TypeError (scope is required)
        run_sql(sql, None)            -> ScopeError
        run_sql(sql, "full")          -> ScopeError
        run_sql(sql, "FULL_KB")       -> ScopeError
        run_sql(sql, "full_kb", db_path=cfg.db)   -> ok

    Returns the COMPLETE result set. No row cap, no truncation.
    """
    scope = _validate_scope(scope)
    if (isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
        raise ConfigError("timeout_seconds must be a finite positive number")
    validate_sql_lexically(sql)          # defence in depth
    con = open_scoped_connection(scope, db_path)
    # Cooperative SQLite VM deadline covers preparation, execution and fetching.
    # It does not impose a result cap or silently return partial rows.
    deadline = time.monotonic() + timeout_seconds
    expired = False

    def interrupt_if_expired():
        nonlocal expired
        expired = time.monotonic() >= deadline
        return int(expired)

    con.set_progress_handler(interrupt_if_expired, 1000)
    try:
        structural_precheck(con, sql, scope)   # statement-level, primary
        cur = con.execute(sql)                 # per-object authorizer still armed
        cols = tuple(d[0] for d in (cur.description or ()))
        rows = tuple(cur.fetchall())     # fetchall: never fetchmany(200)
        if interrupt_if_expired():
            raise TimeoutError("SQL execution exceeded its configured deadline")
        return SQLResult(columns=cols, rows=rows, scope=scope, row_count=len(rows))
    except SQLPolicyError as e:
        if expired:
            raise TimeoutError("SQL preparation exceeded its configured deadline") from e
        raise
    except sqlite3.DatabaseError as e:
        if expired:
            raise TimeoutError("SQL execution exceeded its configured deadline") from e
        if "not authorized" in str(e).lower():
            raise SQLPolicyError(
                f"query is not an authorized read of scope {scope!r}: {e}") from e
        raise
    finally:
        con.close()


def execute_pair(pred_sql, gold_sql, scope, *, db_path=None):
    """Execute prediction and gold through ONE scope argument.

    Prediction and gold must always execute in the same scope. Mixing them --
    a model querying all 205 rows while graded against a train-only gold --
    marks correct queries wrong for rows that genuinely exist, which looks like
    a SQL failure and is really a harness bug.

    There is deliberately no `pred_scope`/`gold_scope` pair here: one scope
    value is passed to both executions, so a mismatch is not expressible.
    """
    scope = _validate_scope(scope)
    gold = run_sql(gold_sql, scope, db_path=db_path)
    pred = run_sql(pred_sql, scope, db_path=db_path)
    if pred.scope != gold.scope:            # unreachable by construction; asserted
        raise ScopeError(
            f"prediction scope {pred.scope!r} != gold scope {gold.scope!r}; "
            f"prediction and gold must always execute in the same scope")
    return pred, gold


def assert_same_scope(pred_result, gold_result) -> None:
    """Loud failure if two already-executed results came from different scopes."""
    if pred_result.scope != gold_result.scope:
        raise ScopeError(
            f"scope mismatch: prediction executed in {pred_result.scope!r} but "
            f"gold in {gold_result.scope!r}. Refusing to score -- a scope "
            f"mismatch is a harness bug, not a model error.")
