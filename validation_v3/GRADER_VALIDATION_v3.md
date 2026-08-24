# GRADER_VALIDATION_v3

Phase 7 — SQL execution and grading. README: this gate **blocks the canonical structured task pool, C and D generation, every structured probe, the Q42 revalidation, and final evaluation**.

## Provenance

```text
datasets_v3/gnem_v3.sqlite   7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b
finetune/sqlexec_v3.py       2825c2a30c0d8a0691f3f4231c47d592967232e85e881044989d0519d3687e84   (sqlexec_v3.0)
finetune/grade_v3.py         619b9350e38ac976ad5ce9d4ba377fdcc4504e00b9ac34ef49fa47f6931b4cbd   (grade_v3.0)
```

## Scope contract

Valid scopes: `train_kb`, `train_dev_kb`, `full_kb`. `run_sql(sql, scope, *, db_path=...)` takes scope as a **required positional argument with no default**, so omitting it is a `TypeError` before any query runs — there is no implicit full-KB execution path.

| rejected input | outcome |
|---|---|
| omitted scope | `TypeError` |
| `None` | `ScopeError` |
| `"full"` | `ScopeError` |
| `"FULL_KB"` | `ScopeError` |
| `"train"` | `ScopeError` |
| non-string (`int`) | `ScopeError` |

**Database path is configuration-driven.** `db_path` has no default and no fallback: omitting it raises `ConfigError`. There is no hard-coded path and no v2 database fallback.

## Scope binding

Model and gold SQL stay **scope-neutral** — `SELECT ... FROM companies`. The executor binds the four logical names to the selected scope's Phase 5 views as connection-local TEMP views, so the model never emits, and is never taught, a physical name like `train_kb_companies`.

Initialization order is fixed:

```text
1. open frozen DB with mode=ro
2. create the four TEMP logical scope bindings
3. PRAGMA query_only = ON
4. install the structural authorizer
5. execute model/gold SQL
```

`query_only` is set **after** the TEMP views, because creating them is itself a write to the temp schema.

## Structural authorization (primary defence)

`sqlite3.Connection.set_authorizer` inspects every object the prepared statement actually touches, so it cannot be evaded by aliases, quoting, CTEs, subqueries, comments or formatting. Lexical validation is retained as **defence in depth only**.

Scoped rows are **materialized into temp tables**, populated from the Phase 5 scoped views. That is a security property, not an optimization: afterwards a legitimate query reads only the temp schema and never touches `main`, so the rule reduces to one forgery-proof condition:

```text
legitimate read    READ arg1='companies'  db=None    (temp binding)   allow
ANY bypass         READ ...               db='main'                    DENY
```

**`source` is deliberately never consulted.** An earlier design keyed on `source in LOGICAL_TABLES` as evidence that a read came from the trusted binding. That is unsound: SQLite reports a user-defined CTE named `companies` with `source == "companies"`, identically to the trusted binding, so the check was forgeable by naming a CTE after a logical table. Review found a working structural-only bypass, `WITH companies AS (SELECT * FROM train_kb_companies) SELECT COUNT(*) FROM companies`, which returned 148 instead of being denied. The mechanism was redesigned rather than patched: the schema an object lives in cannot be forged by naming, so authorization now keys on it alone.

Materialization preserves the data exactly — all 12 scope x table combinations are row- and column-identical to their Phase 5 views, including NULL city/county and the AVS trailing-space address.

### Deny surface

- all 4 raw base tables via `main.`
- all 12 Phase 5 physical scoped views
- `sqlite_master`, `sqlite_schema`, `sqlite_temp_master`, `sqlite_temp_schema`
- `pragma_*` table-valued functions and direct `PRAGMA`
- `ATTACH` / `DETACH` and every write verb
- quoted, schema-qualified, comment-obfuscated and CTE-wrapped variants

- CTE-name collisions wrapping every physical view

**46 bypass vectors tested; all blocked** — including **19 CTE-name-collision vectors** covering all four logical names against every scope's physical views, plus nested, quoted, aliased, subquery-wrapped, joined and comment-obfuscated forms. All remain blocked with the lexical layer disabled, so the structural layer is the primary defence and not a backstop.

## Scope results

| scope | logical `companies` rows | child tables |
|---|---|---|
| `train_kb` | 148 | all child `row_id`s within the scoped parents |
| `train_dev_kb` | 165 | all child `row_id`s within the scoped parents |
| `full_kb` | 205 | all child `row_id`s within the scoped parents |

Membership is verified by identity, not merely by count: `train_kb` ⊂ `train_dev_kb` ⊂ `full_kb`, and zero test rows are reachable under `train_kb`.

## Prediction/gold scope invariant

`execute_pair(pred_sql, gold_sql, scope)` passes **one** scope value to both executions, so `pred_scope=train_kb, gold_scope=full_kb` is not expressible in the ordinary scoring path. `assert_same_scope` additionally raises `ScopeError` on any mismatched pair before a score exists — a scope mismatch is a harness bug, not a model error.

## SQL safety and result cap

Defence in depth: `mode=ro` + `PRAGMA query_only=ON` + authorizer + single-read-statement validation. INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/REPLACE/VACUUM/ATTACH/DETACH and writable PRAGMAs are all rejected, and the database SHA is unchanged after the write battery.

**No result cap.** No `max_rows`, no `fetchmany`, no injected `LIMIT`. A `full_kb` query over `companies` returns **205 rows, not 200**, and `certifications` returns all **662**.

**No semantic rewriting.** Scope binding is infrastructure; nothing else about a query is altered — no repair, clause removal, injected `LIMIT`, `ORDER BY` change, reprojection, or result truncation.

## Prompt truncation

v3 never ported the historical `truncation=True, max_length=24576` evaluator path, so Phase 7 **proves its absence** rather than inventing a migration. The Phase 6 budget is reused, not reinvented:

```text
usable context   32768
max_new_tokens   1024
max input        31744
```

Also proven absent from the Phase 7 paths: the v2 geo registration, the `max_rows=200` cap, and any v2 database fallback.

## Grader metadata contract

`answer_type` and `target_columns` are **supplied by the generator** and never inferred from question wording, predicted SQL, gold SQL, prediction contents or gold result shape. Missing or invalid metadata raises `GraderMetadataError` — there is no fallback.

### Frozen answer-type semantics

| type | rule |
|---|---|
| `set` | project target columns, then dedupe; order irrelevant |
| `scalar` | exactly one scalar-compatible target column and one row |
| `top_k` | order and length preserved; **never** set-deduped |
| `multi_part` | every required part correct; partial is not correct |

### Multi-part encoding is NOT frozen here

README freezes multi-part SEMANTICS (every required part must be correct) but not a serialization for declaring parts. This grader treats each entry of target_columns as one required part -- the minimal reading consistent with the frozen semantics. This is deliberately NOT a permanent generator format; freezing that representation belongs to the phase that owns task metadata, not to Phase 7.

## Two metrics, genuinely distinct

- **`task_result_correctness`** (primary)
- **`strict_result_schema_accuracy`** (secondary)

Divergence fixture: prediction returns the right values with an extra column: task_result_correctness=1.0 but strict_result_schema_accuracy=0.0. The reverse case is also covered — right schema, wrong values — so the secondary metric can never stand in for the primary.

## Degenerate-prediction battery

| prediction | expected | status | task_result_correctness |
|---|---|---|---|
| empty string | `generation_failure` | `generation_failure` | 0.0 |
| whitespace only | `generation_failure` | `generation_failure` | 0.0 |
| None | `generation_failure` | `generation_failure` | 0.0 |
| refusal | `invalid_output` | `invalid_output` | 0.0 |
| refusal as AI | `invalid_output` | `invalid_output` | 0.0 |
| irrelevant noise | `parse_failure` | `parse_failure` | 0.0 |
| malformed SQL | `SQL_error` | `SQL_error` | 0.0 |
| incomplete SQL | `SQL_error` | `SQL_error` | 0.0 |
| write attempt | `parse_failure` | `parse_failure` | 0.0 |
| bypass attempt | `SQL_error` | `SQL_error` | 0.0 |
| truncated_output | `truncated_output` | `truncated_output` | 0.0 |
| v2 empty-vs-empty-gold | `not correct` | `generation_failure` | 0.0 |
| valid query, empty result | `graded normally` | `correct` | 1.0 |

**The v2 regression is fixed.** `v2 finetune/grade.py:170` returned 1.0 when prediction and gold were both empty; an empty, refusing, noisy or malformed prediction therefore scored perfectly on an empty-gold item. Here a degenerate prediction is classified by its own explicit status **before** any comparison, so it can never coincide with an empty gold.

`truncated_output` originates **only** from explicit generation-stop metadata, never inferred from what the text looks like. When set, the parser and executor are not invoked and no normal correctness is computed.

Every item receives exactly one status from the frozen vocabulary: `correct`, `incorrect`, `generation_failure`, `parse_failure`, `SQL_error`, `timeout`, `truncated_output`, `invalid_output`.

## Validation

| check | result | detail |
|---|---|---|
| `frozen_db_sha_unchanged` | PASS | 7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b |
| `omitted_scope_rejected` | PASS | TypeError: run_sql() missing 1 required positional argument: 'scope' |
| `scope_rejected_None` | PASS | ScopeError |
| `scope_rejected_'full'` | PASS | ScopeError |
| `scope_rejected_'FULL_KB'` | PASS | ScopeError |
| `scope_rejected_int` | PASS | ScopeError |
| `scope_rejected_'train'` | PASS | ScopeError |
| `db_path_required` | PASS | ConfigError: db_path must be supplied explicitly by the experiment/runt |
| `scope_train_kb_companies` | PASS | 148 == 148 |
| `scope_train_dev_kb_companies` | PASS | 165 == 165 |
| `scope_full_kb_companies` | PASS | 205 == 205 |
| `child_membership_train_kb` | PASS | all child row_ids within 148 scoped parents |
| `child_membership_train_dev_kb` | PASS | all child row_ids within 165 scoped parents |
| `child_membership_full_kb` | PASS | all child row_ids within 205 scoped parents |
| `train_kb_excludes_dev_and_test` | PASS | train 148 ⊂ train_dev 165 ⊂ full 205; 0 of 40 test rows visible in train_kb |
| `full_bypass_matrix_blocked` | PASS | 46 vectors blocked (4 base tables, 12 physical views, 19 CTE-name collisions, 4 schema tables, pragma TVFs, PRAGMA/ATTACH, quoted/comment forms) |
| `cte_name_collision_blocked_structurally` | PASS | 19 CTE-name-collision vectors denied by the structural layer with lexical validation disabled |
| `structural_layers_alone_block_all_bypasses` | PASS | lexical layer disabled; 46 vectors still denied by the EXPLAIN pre-check + per-object authorizer |
| `structural_layers_allow_legitimate_sql` | PASS | bare/alias/CTE/nested-CTE/subquery/quoted/3-table-join all permitted |
| `all_write_operations_rejected` | PASS | 10 mutating operations rejected |
| `db_sha_unchanged_after_write_attempts` | PASS | 7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b |
| `no_row_cap_returns_all_205` | PASS | 205 rows returned, not 200 |
| `no_row_cap_on_child_table` | PASS | 662 certification rows returned, not 200 |
| `no_geo_import` | PASS | no geo registration anywhere in the executor path |
| `no_max_rows_cap` | PASS | no max_rows and no fetchmany; fetchall only |
| `no_prompt_truncation` | PASS | no truncation=True / max_length= in Phase 7 paths |
| `no_v2_db_fallback` | PASS | no v2 database fallback |
| `phase6_budget_reused_not_reinvented` | PASS | usable 32768, reserved 1024, max input 31744 (frozen in Phase 6) |
| `execute_pair_uses_one_scope` | PASS | one scope argument drives both executions; a mismatch is not expressible |
| `scope_mismatch_raises` | PASS | ScopeError: scope mismatch: prediction executed in 'full_kb' but gold in 'trai |
| `metadata_missing_answer_type` | PASS | GraderMetadataError |
| `metadata_missing_target_columns` | PASS | GraderMetadataError |
| `metadata_invalid_answer_type` | PASS | GraderMetadataError |
| `metadata_empty_target_columns` | PASS | GraderMetadataError |
| `metadata_non-list_target_columns` | PASS | GraderMetadataError |
| `metadata_scalar_with_2_columns` | PASS | GraderMetadataError |
| `set_order_irrelevant` | PASS | set: 2 distinct predicted vs 2 gold |
| `set_duplicates_deduped` | PASS | set: 2 distinct predicted vs 2 gold |
| `set_missing_member_incorrect` | PASS | set: 1 distinct predicted vs 2 gold |
| `scalar_exact_match` | PASS | scalar: 5 vs 5 |
| `scalar_multi_row_rejected` | PASS | scalar requires exactly one row, prediction returned 2 |
| `scalar_empty_rejected` | PASS | scalar requires exactly one row, prediction returned 0 |
| `topk_exact_order_correct` | PASS | top_k: length 3 vs 3, order preserved |
| `topk_wrong_order_incorrect` | PASS | top_k: length 3 vs 3, order differs |
| `topk_wrong_length_incorrect` | PASS | top_k: length 2 vs 3, order differs |
| `topk_never_set_deduped` | PASS | top_k: length 4 vs 3, order differs |
| `multipart_all_parts_correct` | PASS | multi_part: all parts correct |
| `multipart_partial_is_not_correct` | PASS | multi_part: 1/2 parts wrong (county) -- partial is not correct |
| `metrics_differ_semantic_right_schema_wrong` | PASS | task=1.0 schema=0.0 |
| `metrics_agree_when_both_right` | PASS | both 1.0 |
| `schema_right_values_wrong` | PASS | task=0.0 schema=1.0 |
| `degenerate_empty_string` | PASS | status=generation_failure (expected generation_failure), task=0.0 |
| `degenerate_whitespace_only` | PASS | status=generation_failure (expected generation_failure), task=0.0 |
| `degenerate_None` | PASS | status=generation_failure (expected generation_failure), task=0.0 |
| `degenerate_refusal` | PASS | status=invalid_output (expected invalid_output), task=0.0 |
| `degenerate_refusal_as_AI` | PASS | status=invalid_output (expected invalid_output), task=0.0 |
| `degenerate_irrelevant_noise` | PASS | status=parse_failure (expected parse_failure), task=0.0 |
| `degenerate_malformed_SQL` | PASS | status=SQL_error (expected SQL_error), task=0.0 |
| `degenerate_incomplete_SQL` | PASS | status=SQL_error (expected SQL_error), task=0.0 |
| `degenerate_write_attempt` | PASS | status=parse_failure (expected parse_failure), task=0.0 |
| `degenerate_bypass_attempt` | PASS | status=SQL_error (expected SQL_error), task=0.0 |
| `degenerate_truncated_output` | PASS | status=truncated_output (expected truncated_output), task=0.0 |
| `v2_regression_empty_pred_empty_gold_not_1_0` | PASS | status=generation_failure, task=0.0 (v2 grade.py:170 returned 1.0 here) |
| `valid_query_empty_result_still_graded` | PASS | status=correct -- a real query is graded, not short-circuited |
| `truncated_output_never_parsed` | PASS | status=truncated_output: truncated_output: prediction not parsed or executed |
| `every_status_in_frozen_vocabulary` | PASS | 13 outcomes, all within 8 frozen statuses |
