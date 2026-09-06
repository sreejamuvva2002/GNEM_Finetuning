"""Phase 8 gate -- drive the whole v3 stack from synthetic fixtures.

CLAUDE.md 33 makes the gate functional: known-correct and known-wrong synthetic
fixtures must pass through parsing, grading, statistics, error analysis and
report generation without touching retired components.

Everything here is a deterministic synthetic fixture. No real probe, dataset,
prediction, test item or Q42 content is created, read or reported. No model is
loaded. Test/Q42 remain LOCKED_UNTIL_PHASE_40.

A failing gate writes no artifact.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_records_v3 as R      # noqa: E402
import eval_report_v3 as RPT     # noqa: E402
import eval_stats_v3 as ST       # noqa: E402
import eval_verify_v3 as V       # noqa: E402
import grade_v3 as G             # noqa: E402
import sqlexec_v3 as X           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "datasets_v3" / "gnem_v3.sqlite"
FIX_DIR = ROOT / "validation_v3" / "fixtures_v3"
OUT_AUDIT = ROOT / "validation_v3" / "EVAL_STACK_VALIDATION_v3.md"

FROZEN = {
    "datasets_v3/gnem_v3.sqlite":
        "7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b",
    "finetune/sqlexec_v3.py":
        "a6c06b71dd97541997bedc2202e1980ab2e4cdd721aaf20ff43eacfda876c461",
    # Updated for the Phase 9 correction (multi-part grading, D.9/D.17/D.20).
    # Only these two are actually pinned here as an executable preflight gate
    # -- eval_records_v3.py/eval_verify_v3.py are pinned separately, only in
    # the STACK_MODULES hash table below (self-updating documentation, not an
    # executable gate); an earlier version of this comment/plan conflated the
    # two lists.
    "finetune/grade_v3.py":
        "1051a161ac848ad058dda424417e296571404e6fd5dbe10174994cea7df0c6aa",
    "finetune/phase7_grader_tests.py":
        "bcdbdbb67211321c8ebd50e2d5a8eeb6908c5fb7b7b692a8cf028ba76b16d8b6",
}

# Retired concepts that must appear nowhere in the active Phase 8 stack.
RETIRED = ("latitude", "longitude", "geocod", "distance", "radius", "nearest",
           "probe_geo", "probe_relationship", "graph_edges", "router",
           "D_sql_k0", "D_sql_k5", "D_sql_k25", "REPORT_ORDER", "BDR")

STACK_MODULES = ("eval_records_v3.py", "eval_stats_v3.py", "eval_report_v3.py",
                 "eval_verify_v3.py")


class Gate(Exception):
    """A Phase 8 invariant failed. No artifact is written."""


def sha256_file(p: Path) -> str:
    return R.sha256_file(p)


def _rec(example_id, family, status, task, schema, *, answer_type="set",
         target_columns=("company",), condition="fixture_condition",
         raw="SELECT company FROM companies", parsed=None, sql=None,
         result=None, gold=("A",), error_type=None, error_detail=None,
         seed=None, adapter=None, parts=None, regrade_outcome=None,
         grader_version=None, grader_sha256=None) -> R.EvalRecord:
    # `gold`: either the legacy bare-list retention shape (kept for existing
    # fixtures) or, when regrade-recomputation evidence is needed (Phase 9
    # correction), a {"columns":[...], "rows":[...]} dict -- passed through
    # unchanged when it's already a dict. `result` (execution_result) was
    # always passed through as-is.
    gold_val = gold if (gold is None or isinstance(gold, dict)) else list(gold)
    return R.EvalRecord(
        example_id=example_id, family=family, condition=condition,
        question=f"synthetic fixture question for {example_id}",
        raw_output=raw, parsed_output=parsed, generated_sql=sql,
        execution_result=result, gold=gold_val,
        answer_type=answer_type,
        target_columns=list(target_columns) if target_columns else None,
        task_result_correctness=task, strict_result_schema_accuracy=schema,
        status=status, error_type=error_type, error_detail=error_detail,
        prompt_hash=hashlib.sha256(example_id.encode()).hexdigest()[:16],
        adapter_hash=adapter, seed=seed,
        grader_version=grader_version or G.GRADER_VERSION,
        grader_sha256=grader_sha256 or FROZEN["finetune/grade_v3.py"],
        parts=tuple(parts) if parts else None,
        regrade_outcome=regrade_outcome)


def build_fixtures() -> list[R.EvalRecord]:
    """The minimum set that exercises the stack thoroughly."""
    f = []
    # --- known-correct across the frozen answer types --------------------
    f.append(_rec("fx01_set_correct", "factual_recall", "correct", 1.0, 1.0))
    f.append(_rec("fx02_scalar_correct", "structured_heldin", "correct", 1.0, 1.0,
                  answer_type="scalar", target_columns=("n",), gold=(5,)))
    f.append(_rec("fx03_topk_correct", "structured_heldin", "correct", 1.0, 1.0,
                  answer_type="top_k", gold=("A", "B", "C")))
    f.append(_rec("fx04_multipart_correct", "structured_paraphrase", "correct",
                  1.0, 1.0, answer_type="multi_part",
                  target_columns=("company", "county")))
    # --- known-wrong ------------------------------------------------------
    f.append(_rec("fx05_set_incorrect", "factual_recall", "incorrect", 0.0, 1.0))
    f.append(_rec("fx06_topk_order_wrong", "structured_heldin", "incorrect",
                  0.0, 1.0, answer_type="top_k", gold=("A", "B", "C"),
                  error_type="order", error_detail="top_k order differs"))
    # --- the two metrics must be able to disagree, in BOTH directions -----
    f.append(_rec("fx07_task_ok_schema_wrong", "structured_heldin", "correct",
                  1.0, 0.0, error_detail="extra column in result"))
    f.append(_rec("fx08_task_wrong_schema_ok", "structured_heldin", "incorrect",
                  0.0, 1.0, error_detail="right shape, wrong values"))
    # --- every failure status --------------------------------------------
    f.append(_rec("fx09_generation_failure", "factual_recall",
                  "generation_failure", 0.0, 0.0, raw="",
                  error_type="generation_failure", error_detail="empty output"))
    f.append(_rec("fx10_parse_failure", "structured_heldin", "parse_failure",
                  0.0, 0.0, raw="banana banana", error_type="parse_failure",
                  error_detail="not a SELECT/WITH query"))
    f.append(_rec("fx11_sql_error", "structured_heldin", "SQL_error", 0.0, 0.0,
                  raw="SELECT FROM WHERE", error_type="SQL_error",
                  error_detail="malformed SQL"))
    f.append(_rec("fx12_timeout", "structured_heldin", "timeout", 0.0, 0.0,
                  error_type="timeout", error_detail="execution deadline"))
    f.append(_rec("fx13_truncated_output", "structured_heldin",
                  "truncated_output", 0.0, 0.0, raw="SELECT company FROM comp",
                  error_type="truncated_output",
                  error_detail="stopped at max_new_tokens; not parsed"))
    f.append(_rec("fx14_invalid_output", "factual_recall", "invalid_output",
                  0.0, 0.0, raw="I cannot answer that.",
                  error_type="invalid_output", error_detail="refusal"))
    # --- a GENUINE valid empty result is graded on its merits -------------
    f.append(_rec("fx15_valid_empty_result", "no_match", "correct", 1.0, 1.0,
                  raw="SELECT company FROM companies WHERE row_id = -1",
                  sql="SELECT company FROM companies WHERE row_id = -1",
                  result=[], gold=[]))
    # --- multi-seed trained condition, for the stats plumbing -------------
    for i, seed in enumerate((11, 22, 33)):
        f.append(_rec(f"fx16_seed{seed}", "factual_recall",
                      "correct" if i < 2 else "incorrect",
                      1.0 if i < 2 else 0.0, 1.0,
                      condition="B_facts", seed=seed, adapter=f"ad{seed:04d}"))

    # Regrade-recomputation fixtures (fx17-fx20) live ONLY in
    # _regrade_correction_checks(), not in this shared list: they're built
    # with retained evidence that deliberately DISAGREES with their recorded
    # status, which would break this list's `regrade_reproduces_metrics`
    # check (a legitimate invariant for these 16 ordinary fixtures, none of
    # which carry disagreeing retained evidence).
    return f


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    # ---- frozen pre-flight ------------------------------------------------
    for rel, expected in FROZEN.items():
        actual = sha256_file(ROOT / rel)
        if actual != expected:
            raise Gate(f"{rel} drifted: {actual}")
    check("phase7_frozen_hashes_unchanged", True,
          "DB, executor, grader and Phase 7 tests all match")

    fixtures = build_fixtures()
    expected_count = len(fixtures)

    # ---- record schema ----------------------------------------------------
    check("record_schema_carries_retention_fields",
          all(f in R.REQUIRED_FIELDS for f in
              ("example_id", "question", "raw_output", "parsed_output",
               "generated_sql", "execution_result", "gold", "prompt_hash",
               "adapter_hash", "grader_version", "grader_sha256")),
          f"{len(R.REQUIRED_FIELDS)} fields incl. every README Phase 40 "
          f"retention field; never scores alone")
    check("status_vocabulary_sourced_from_phase7",
          R.STATUSES is G.STATUSES,
          f"{len(R.STATUSES)} statuses imported from the frozen grader, not redeclared")

    # ---- verification -----------------------------------------------------
    families = sorted({f.family for f in fixtures})
    vres = V.verify(fixtures, expected_count=expected_count,
                    expected_families=families,
                    grader_sha256=FROZEN["finetune/grade_v3.py"])
    check("verify_accepts_good_fixture", vres["passed"],
          f"{vres['n_records']} records, {vres['unique_example_ids']} unique ids, "
          f"exactly-one-status holds")

    # ---- summary / denominators ------------------------------------------
    summary = RPT.summarize(fixtures, expected_count=expected_count)
    check("denominator_invariant_scored_plus_failed",
          summary["denominator_invariant"]["holds"],
          f"scored {summary['scored']} + failed {summary['failed']} == "
          f"expected {expected_count}")
    check("all_eight_statuses_represented",
          sum(1 for v in summary["status_counts"].values() if v) == 8,
          f"{sorted(k for k, v in summary['status_counts'].items() if v)}")
    check("failures_counted_in_denominator",
          summary["task_result_correctness"]["denominator"] == expected_count,
          f"denominator {expected_count} includes all {summary['failed']} failures")

    # ---- the two metrics stay distinct, both directions -------------------
    a = next(r for r in fixtures if r.example_id == "fx07_task_ok_schema_wrong")
    b = next(r for r in fixtures if r.example_id == "fx08_task_wrong_schema_ok")
    check("metrics_distinct_task_ok_schema_wrong",
          a.task_result_correctness == 1.0 and a.strict_result_schema_accuracy == 0.0,
          "task=1.0 schema=0.0")
    check("metrics_distinct_task_wrong_schema_ok",
          b.task_result_correctness == 0.0 and b.strict_result_schema_accuracy == 1.0,
          "task=0.0 schema=1.0")
    check("metrics_not_merged",
          summary["task_result_correctness"]["value"]
          != summary["strict_result_schema_accuracy"]["value"],
          f"primary {summary['task_result_correctness']['value']:.3f} != "
          f"secondary {summary['strict_result_schema_accuracy']['value']:.3f}")

    # ---- per-family -------------------------------------------------------
    check("per_family_metrics_data_driven",
          set(summary["families"]) == set(families) and len(families) >= 4,
          f"{len(families)} families discovered from records: {families}")
    extra = fixtures + [_rec("fx99_new_family", "brand_new_family_v3",
                             "correct", 1.0, 1.0)]
    s2 = RPT.summarize(extra, expected_count=len(extra))
    check("new_family_needs_no_code_edit",
          "brand_new_family_v3" in s2["families"],
          "a previously unseen family appears with no REPORT_ORDER edit")

    # ---- error analysis ---------------------------------------------------
    errors = RPT.error_analysis(fixtures)
    check("error_analysis_distinguishes_classes",
          errors["distinguished_classes"]["incorrect_valid_prediction"] >= 1
          and all(errors["distinguished_classes"][s] >= 1 for s in
                  ("generation_failure", "parse_failure", "SQL_error",
                   "timeout", "truncated_output", "invalid_output")),
          f"{errors['n_failures']} failures grouped by status, family and answer_type")

    # ---- statistics -------------------------------------------------------
    stats_demo = _stats_demo()
    check("stats_per_seed_and_mean_sd", stats_demo["mean_sd"]["n"] == 3,
          f"per-seed {stats_demo['per_seed']}, mean±SD n=3")
    check("stats_refuses_baseline_sd", stats_demo["baseline_sd_refused"],
          "a deterministic baseline is refused an SD (README:976-979)")
    check("stats_paired_bootstrap_deterministic",
          stats_demo["bootstrap_reproducible"],
          f"identical CI across runs at seed {ST.BOOTSTRAP_SEED}")
    check("stats_effect_size_and_holm",
          stats_demo["effect_size"] is not None and stats_demo["holm_monotonic"],
          "effect size computed; Holm adjustment monotonic")
    check("stats_mcnemar_present_cited", stats_demo["mcnemar"]["n_discordant"] >= 0,
          "McNemar implemented as secondary evidence (README:973)")
    check("stats_split_group_weighting_cited",
          stats_demo["split_group"]["n_groups"] == 2
          and stats_demo["split_group"]["n_items_excluded"] == 1,
          "average within split_group then across groups; aggregate item "
          "excluded as undefined (CLAUDE.md:847-854)")
    check("stats_hierarchical_bootstrap_deferred",
          not hasattr(ST, "hierarchical_bootstrap"),
          "not implemented: absent from the live protocol, so deferred not invented")

    # ---- regrade ----------------------------------------------------------
    regraded = V.regrade(fixtures, grader_sha256=FROZEN["finetune/grade_v3.py"])
    check("regrade_preserves_raw_and_gold",
          all(o.raw_output == n.raw_output and o.gold == n.gold
              and o.question == n.question
              for o, n in zip(fixtures, regraded)),
          "raw prediction, gold and question carried through untouched")
    check("regrade_records_grader_provenance",
          all(r.grader_version == G.GRADER_VERSION for r in regraded),
          f"every regraded record stamped {G.GRADER_VERSION}")
    rs = RPT.summarize(regraded, expected_count=expected_count)
    check("regrade_reproduces_metrics",
          rs["denominator_invariant"]["holds"]
          and rs["status_counts"] == summary["status_counts"],
          "status distribution identical after regrade")

    # ---- Phase 7 executor is the only SQL path ---------------------------
    sql_res = X.run_sql("SELECT COUNT(*) FROM companies", "train_kb", db_path=DB)
    check("sql_fixtures_use_phase7_executor", sql_res.rows[0][0] == 148,
          "SQL fixture path calls the approved Phase 7 executor (train_kb=148); "
          "no second execution implementation exists")
    stack_src = "\n".join((ROOT / "finetune" / m).read_text(encoding="utf-8")
                          for m in STACK_MODULES)
    check("no_duplicate_sql_execution_in_stack",
          "sqlite3.connect" not in stack_src,
          "no module in the reporting stack opens its own database connection")

    # ---- sealed-test guard ------------------------------------------------
    seal = _seal_checks(fixtures)
    for name, ok, detail in seal:
        check(name, ok, detail)

    # ---- retired components ----------------------------------------------
    # Scan EXECUTABLE CODE, not prose: a docstring explaining that the stack
    # deliberately avoids v2's REPORT_ORDER must not be flagged as depending on
    # it. Same reasoning as the Phase 6 truncation scanner.
    stack_code = _code_only(stack_src)
    hits = sorted({t for t in RETIRED if t.lower() in stack_code.lower()})
    prose_only = sorted({t for t in RETIRED
                         if t.lower() in stack_src.lower()
                         and t.lower() not in stack_code.lower()})
    check("no_retired_component_dependency", not hits,
          f"none of {len(RETIRED)} retired concepts appear in executable code"
          + (f"; mentioned only in prose explaining their avoidance: {prose_only}"
             if prose_only else "")
          if not hits else f"{hits}")
    check("no_v2_runtime_path",
          "GNEM-Router-RAG-pipeline" not in stack_src
          and "gnem" + ".sqlite" not in stack_src,
          "no v2 repository path and no v2 database fallback")

    # ---- faults -----------------------------------------------------------
    faults = _fault_checks(fixtures, expected_count)
    for name, ok, detail in faults:
        check(name, ok, detail)

    # ---- Phase 9 correction: regrade recomputation + insufficient-evidence
    regrade_checks = _regrade_correction_checks()
    for name, ok, detail in regrade_checks:
        check(name, ok, detail)

    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    failed = [n for n, ok, _ in checks if not ok]
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    # ---- artifacts --------------------------------------------------------
    FIX_DIR.mkdir(parents=True, exist_ok=True)
    rec_sha = R.write_records(FIX_DIR / "fixture_records_v3.jsonl", fixtures)
    # Explicit, deterministic provenance for the JSONL, which cannot carry a
    # banner of its own -- so synthetic status does not depend on directory name.
    fixtures_manifest = {
        "artifact": "fixture_records_v3.jsonl",
        "provenance": "SYNTHETIC VALIDATION FIXTURE — NOT EXPERIMENTAL RESULTS",
        "contains_experimental_results": False,
        "contains_real_test_or_q42_content": False,
        "description": ("deterministic synthetic evaluation records generated by "
                        "the Phase 8 gate to validate the reporting stack; no "
                        "model was run and no real probe exists"),
        "schema_version": R.RECORDS_VERSION,
        "item_count": len(fixtures),
        "sha256": rec_sha,
        "generated_by": "finetune/phase8_eval_stack_tests.py",
    }
    man_sha = RPT.write_json(FIX_DIR / "fixtures_manifest_v3.json", fixtures_manifest)
    sum_sha = RPT.write_json(FIX_DIR / "summary_v3.json", summary)
    err_sha = RPT.write_json(FIX_DIR / "error_analysis_v3.json", errors)
    provenance = {
        "phase": "8 (synthetic fixture validation)",
        "records_module": R.RECORDS_VERSION,
        "stats_module": ST.STATS_VERSION,
        "report_module": RPT.REPORT_VERSION,
        "verify_module": V.VERIFY_VERSION,
        "grader": f"{G.GRADER_VERSION} {FROZEN['finetune/grade_v3.py'][:16]}…",
        "executor": f"{X.EXECUTOR_VERSION} {FROZEN['finetune/sqlexec_v3.py'][:16]}…",
        "fixture_records_sha256": rec_sha,
    }
    skeleton = RPT.render_report_skeleton(summary, errors, stats_demo=_stats_render(stats_demo),
                                          provenance=provenance)
    (FIX_DIR / "REPORT_v3.md").write_text(skeleton, encoding="utf-8")
    rep_sha = sha256_file(FIX_DIR / "REPORT_v3.md")

    _write_audit(checks, faults, summary, errors, stats_demo, provenance,
                 rec_sha, sum_sha, err_sha, rep_sha, expected_count, families,
                 man_sha)

    print(f"All Phase 8 gates passed ({len(checks)} checks).")
    print(f"  fixtures {expected_count} · families {len(families)} · "
          f"statuses {sum(1 for v in summary['status_counts'].values() if v)}/8")
    print(f"  skeleton {FIX_DIR.relative_to(ROOT)}/REPORT_v3.md  (synthetic)")
    return 0


def _code_only(src: str) -> str:
    """Strip string literals and comments so prose is not scanned as code."""
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


def _stats_demo() -> dict:
    per_seed = {11: 0.80, 22: 0.84, 33: 0.82}
    ms = ST.mean_sd(per_seed.values())
    try:
        ST.mean_sd([0.7, 0.7], deterministic=True)
        baseline_refused = False
    except ST.StatsUsageError:
        baseline_refused = True
    diffs = [1.0, 0.0, 1.0, -1.0, 0.0, 1.0, 1.0, 0.0]
    bs1 = ST.paired_bootstrap(diffs)
    bs2 = ST.paired_bootstrap(diffs)
    pv = {"B_vs_base": 0.01, "D_vs_base_sql": 0.04, "BD_vs_Drepeat": 0.20}
    adj = ST.holm(pv)
    mc = ST.mcnemar([(1, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    sg = ST.split_group_weighted(
        {"i1": 1.0, "i2": 0.0, "i3": 1.0, "agg1": 1.0},
        {"i1": "g1", "i2": "g1", "i3": "g2"},
        entity_attributable={"i1": True, "i2": True, "i3": True, "agg1": False})
    return {
        "per_seed": ST.per_seed_scores(per_seed)["per_seed"],
        "mean_sd": ms,
        "baseline_sd_refused": baseline_refused,
        "bootstrap": bs1,
        "bootstrap_reproducible": bs1 == bs2,
        "effect_size": ST.effect_size(diffs),
        "holm": adj,
        "holm_monotonic": list(adj.values()) == sorted(adj.values()),
        "mcnemar": mc,
        "split_group": sg,
        "item_weighted": ST.item_weighted({"i1": 1.0, "i2": 0.0, "i3": 1.0}),
    }


def _stats_render(d: dict) -> dict:
    return {
        "per-seed scores": d["per_seed"],
        "mean +/- SD": f"{d['mean_sd']['mean']:.4f} +/- {d['mean_sd']['sd']:.4f} (n={d['mean_sd']['n']})",
        "baseline SD": "refused (deterministic condition)",
        "effect size (d_z)": f"{d['effect_size']:.4f}",
        "paired bootstrap 95% CI": f"[{d['bootstrap']['ci_low']:.4f}, {d['bootstrap']['ci_high']:.4f}]",
        "bootstrap items": d["bootstrap"]["n_items"],
        "Holm-adjusted": {k: round(v, 4) for k, v in d["holm"].items()},
        "McNemar p (secondary)": round(d["mcnemar"]["p_value"], 4),
        "split_group-weighted": f"{d['split_group']['split_group_weighted']:.4f} "
                                f"over {d['split_group']['n_groups']} groups",
        "item-weighted": d["item_weighted"]["rendered"],
    }


def _seal_checks(fixtures) -> list[tuple[str, bool, str]]:
    """Sealed-boundary tests. SYNTHETIC ARTIFACTS ONLY.

    No real test or Q42 prediction, example, gold, score or error case is
    created, read, reported or inferred anywhere in this function.
    """
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        td = Path(tmp)

        def entry(path, kind, artifact_id, count, note):
            return {"artifact_id": artifact_id,
                    "canonical_path": R.ClassificationAuthority.canonicalize(path),
                    "artifact_kind": kind, "sha256": R.sha256_file(path),
                    "schema_version": R.RECORDS_VERSION, "item_count": count,
                    "provenance": note}

        def manifest(entries, path, version="fixture-1"):
            RPT.write_json(path, {"schema": R.TRUSTED_MANIFEST_SCHEMA,
                                  "version": version, "artifacts": entries})
            return path

        # --- synthetic artifacts -------------------------------------------
        dev_path = td / "dev_results.jsonl"
        R.write_records(dev_path, fixtures)
        sealed_devlook = td / "sealed_devlooking.jsonl"
        R.write_records(sealed_devlook,
                        [_rec("sx_devlook", "factual_recall", "correct", 1.0, 1.0)])
        sealed_future = td / "sealed_future.jsonl"
        R.write_records(sealed_future,
                        [_rec("sx_future", "brand_new_future_family", "correct",
                              1.0, 1.0)])
        # Deliberately unparseable, to prove authorization precedes parsing.
        sealed_unparseable = td / "sealed_unparseable.jsonl"
        sealed_unparseable.write_text("<<<NOT-JSON-AT-ALL>>>\n", encoding="utf-8")

        trusted = manifest([
            entry(dev_path, R.DEV_KIND, "fx_dev_001", len(fixtures),
                  "synthetic Phase 8 dev fixture"),
            entry(sealed_devlook, R.SEALED_KIND, "fx_sealed_devlook", 1,
                  "synthetic sealed fixture; records declare a dev family"),
            entry(sealed_future, R.SEALED_KIND, "fx_sealed_future", 1,
                  "synthetic sealed fixture; records declare an unknown family"),
            entry(sealed_unparseable, R.SEALED_KIND, "fx_sealed_unparseable", 1,
                  "synthetic sealed fixture; deliberately unparseable bytes"),
        ], td / "trusted_artifacts_v3.json")
        auth = R._install_trusted_authority_for_fixtures(trusted)

        def refuses(path):
            try:
                R.load_dev_results(path)
                return False, "*** LOADED ***"
            except R.SealError as e:
                return True, f"SealError: {str(e)[:52]}"
            except Exception as e:  # noqa: BLE001
                return False, f"wrong error {type(e).__name__}: {e}"

        ok, d = refuses(sealed_devlook)
        out.append(("seal01_sealed_artifact_with_dev_family_denied", ok,
                    f"{d} (records claim family=factual_recall)"))
        ok, d = refuses(sealed_future)
        out.append(("seal02_sealed_artifact_with_future_family_denied", ok, d))

        unregistered = td / "unregistered.jsonl"
        R.write_records(unregistered, fixtures[:1])
        ok, d = refuses(unregistered)
        out.append(("seal03_unregistered_artifact_fails_closed", ok,
                    f"{d} -- unknown never becomes dev"))

        ok, d = refuses(sealed_unparseable)
        out.append(("seal04_classification_before_parsing", ok,
                    f"{d} -- unparseable bytes never reached a JSON parser"))

        meta = R.sealed_metadata(sealed_unparseable)
        out.append(("seal05_sealed_metadata_does_not_parse_records",
                    meta["records_parsed"] is False and meta["item_count"] == 1,
                    "metadata returned for an UNPARSEABLE sealed artifact; "
                    "item_count came from the trusted manifest. Raw bytes are "
                    "read for hash verification; records are never parsed"))

        keys = set(meta)
        allowed = {"artifact_id", "artifact_path", "sha256", "item_count",
                   "schema_version", "provenance", "artifact_kind",
                   "records_parsed"}
        out.append(("seal06_metadata_exposes_no_family",
                    "families" not in keys and "family" not in keys,
                    f"keys: {sorted(keys)}"))
        out.append(("seal07_metadata_exposes_no_condition",
                    "conditions" not in keys and "condition" not in keys,
                    "no condition field"))
        forbidden = {"status", "statuses", "status_counts", "scores",
                     "task_result_correctness", "strict_result_schema_accuracy",
                     "error_type", "error_types", "answer_type", "questions",
                     "gold", "execution_result"}
        out.append(("seal08_metadata_exposes_no_score_status_error",
                    not (keys & forbidden) and keys <= allowed,
                    "no status, score, error or answer-type distribution"))

        import os
        cwd = Path.cwd()
        try:
            os.chdir(td)
            rel_kind, _ = auth.classify(Path("sealed_devlooking.jsonl"))
            dotted_kind, _ = auth.classify(Path(".") / "sealed_devlooking.jsonl")
        finally:
            os.chdir(cwd)
        abs_kind, _ = auth.classify(sealed_devlook.resolve())
        out.append(("seal09_relative_and_absolute_paths_same_identity",
                    abs_kind == rel_kind == dotted_kind == R.SEALED_KIND,
                    "absolute, relative and dotted spellings all classify sealed"))

        link = td / "innocent_looking_dev_results.jsonl"
        try:
            link.symlink_to(sealed_devlook)
            link_kind, _ = auth.classify(link)
            ok, d = refuses(link)
            out.append(("seal10_symlink_to_sealed_remains_sealed",
                        ok and link_kind == R.SEALED_KIND,
                        f"{d} -- symlink resolves to the sealed artifact"))
        except OSError:
            out.append(("seal10_symlink_to_sealed_remains_sealed", False,
                        "symlink unsupported on this filesystem"))

        copied = td / "copy_of_dev_results.jsonl"
        shutil.copyfile(dev_path, copied)
        ok, d = refuses(copied)
        copied_kind, _ = auth.classify(copied)
        out.append(("seal11_copied_artifact_fails_closed",
                    ok and copied_kind == R.UNKNOWN_KIND,
                    f"{d} -- identical bytes at an unregistered path stay unknown"))

        tampered = td / "tampered.jsonl"
        R.write_records(tampered, fixtures)
        t_manifest = manifest([entry(tampered, R.DEV_KIND, "fx_tamper",
                                     len(fixtures), "synthetic")],
                              td / "tamper_manifest.json")
        R._install_trusted_authority_for_fixtures(t_manifest)
        R.write_records(tampered, fixtures[:2])          # bytes now differ
        ok, d = refuses(tampered)
        out.append(("seal11b_hash_mismatch_fails_closed", ok,
                    f"{d} -- registered path, unregistered bytes"))
        R._install_trusted_authority_for_fixtures(trusted)   # restore

        loaded = R.load_dev_results(dev_path)
        out.append(("seal12_registered_dev_artifact_loads",
                    len(loaded) == len(fixtures),
                    f"{len(loaded)} dev records loaded via the trusted authority"))

        # ---- TRUST-BOUNDARY REGRESSIONS ---------------------------------
        # T1. the exact relabel the review used: an ordinary caller cannot
        # supply an authority that calls a sealed artifact dev.
        import inspect
        sig_load = str(inspect.signature(R.load_dev_results))
        sig_meta = str(inspect.signature(R.sealed_metadata))
        no_authority_param = not any(
            t in sig_load + sig_meta
            for t in ("registry", "authority", "manifest", "unseal",
                      "allow_test", "bypass_seal", "force"))
        relabel_blocked = True
        try:
            # The supported API takes no authority, so relabeling has nowhere
            # to attach. Attempting to pass one is a TypeError.
            R.load_dev_results(sealed_devlook, object())     # type: ignore
            relabel_blocked = False
        except TypeError:
            pass
        except R.SealError:
            pass
        out.append(("trust01_caller_cannot_supply_authority",
                    no_authority_param and relabel_blocked,
                    f"load_dev_results{sig_load} and sealed_metadata{sig_meta} "
                    f"accept no registry/authority/unseal argument"))

        # T2. an authority cannot be mutated after construction.
        mutations = []
        try:
            auth.register(entry(sealed_devlook, R.DEV_KIND, "x", 1, "n"))
            mutations.append("register() exists")
        except AttributeError:
            pass
        try:
            auth._by_path[str(sealed_devlook.resolve())] = None
            mutations.append("_by_path mutable")
        except TypeError:
            pass
        try:
            auth._manifest_version = "tampered"
            mutations.append("attribute reassignable")
        except R.ManifestError:
            pass
        out.append(("trust02_authority_is_immutable", not mutations,
                    "no register(); mapping is read-only; attribute assignment "
                    "raises ManifestError"
                    if not mutations else f"{mutations}"))

        # T3. a sealed artifact stays sealed even if a caller writes a manifest
        # that relabels it -- because the supported API does not consult it.
        rogue = manifest([entry(sealed_devlook, R.DEV_KIND, "fx_sealed_devlook",
                                1, "caller claims this is dev")],
                         td / "rogue_manifest.json")
        ok, d = refuses(sealed_devlook)
        out.append(("trust03_rogue_manifest_not_consulted_by_dev_api", ok,
                    f"{d} -- a caller-authored manifest has no supported route "
                    f"into the dev loader"))

        # T4. conflicting trusted-manifest entries are rejected, not merged.
        conflicts = []
        for label, entries in (
                ("same path, different kind",
                 [entry(sealed_devlook, R.SEALED_KIND, "a", 1, "n"),
                  entry(sealed_devlook, R.DEV_KIND, "b", 1, "n")]),
                ("same artifact_id, different kind",
                 [entry(sealed_devlook, R.SEALED_KIND, "same_id", 1, "n"),
                  entry(dev_path, R.DEV_KIND, "same_id", len(fixtures), "n")])):
            mp = manifest(entries, td / f"conflict_{len(conflicts)}.json")
            try:
                R._build_authority_from_manifest(mp)
                conflicts.append(label)
            except R.ManifestError:
                pass
        out.append(("trust04_conflicting_manifest_rejected", not conflicts,
                    "same-path and same-artifact_id conflicts both raise "
                    "ManifestError; no last-write-wins"
                    if not conflicts else f"accepted: {conflicts}"))

        # T5. malformed manifests are rejected.
        bad = []
        for label, doc in (
                ("unknown schema", {"schema": "something_else", "artifacts": []}),
                ("missing field", {"schema": R.TRUSTED_MANIFEST_SCHEMA,
                                   "artifacts": [{"artifact_id": "x"}]}),
                ("extra field", {"schema": R.TRUSTED_MANIFEST_SCHEMA,
                                 "artifacts": [{**entry(dev_path, R.DEV_KIND, "x",
                                                        len(fixtures), "n"),
                                                "rogue": 1}]}),
                ("bad kind", {"schema": R.TRUSTED_MANIFEST_SCHEMA,
                              "artifacts": [{**entry(dev_path, "superuser", "x",
                                                     len(fixtures), "n")}]})):
            mp = td / f"bad_{len(bad)}.json"
            RPT.write_json(mp, doc)
            try:
                R._build_authority_from_manifest(mp)
                bad.append(label)
            except R.ManifestError:
                pass
        out.append(("trust05_malformed_manifest_rejected", not bad,
                    "unknown schema, missing field, extra field and invalid "
                    "artifact_kind all raise ManifestError"
                    if not bad else f"accepted: {bad}"))

        # T6. manifest provenance is deterministic and recorded.
        a1 = R._build_authority_from_manifest(trusted)
        a2 = R._build_authority_from_manifest(trusted)
        # The synthetic manifest embeds temporary canonical paths, so its hash
        # necessarily varies per run. Report the RELATION the check actually
        # tests -- two builds agree -- rather than the absolute value, which
        # would make the committed audit non-deterministic.
        out.append(("trust06_manifest_provenance_deterministic",
                    a1.manifest_sha256 == a2.manifest_sha256
                    and a1.artifact_ids() == a2.artifact_ids()
                    and len(a1.manifest_sha256) == 64,
                    f"two builds of the same manifest agree on a 64-hex sha256 "
                    f"and on {len(a1.artifact_ids())} artifacts in deterministic "
                    f"order (value omitted: the synthetic manifest embeds "
                    f"temporary paths)"))

        # T7. with no authority initialized, dev loading refuses.
        saved = R._AUTHORITY
        try:
            R._AUTHORITY = None
            try:
                R.load_dev_results(dev_path)
                uninit_ok = False
            except R.ManifestError:
                uninit_ok = True
            except R.SealError:
                uninit_ok = True
        finally:
            R._AUTHORITY = saved
        out.append(("trust07_no_authority_fails_closed", uninit_ok,
                    "an uninitialized authority refuses dev loading rather than "
                    "defaulting open"))

        src = _code_only((ROOT / "finetune" / "eval_records_v3.py")
                         .read_text(encoding="utf-8"))
        out.append(("seal14_family_not_used_for_classification",
                    ".family" not in src and "SEALED_FAMILY_MARKERS" not in src,
                    "no record field participates in classification; identity "
                    "is canonical path + registered hash"))
    return out


def _fault_checks(fixtures, expected_count) -> list[tuple[str, bool, str]]:
    out = []

    def expect_raise(name, fn, exc, detail):
        try:
            fn()
            out.append((name, False, f"*** NOT RAISED *** {detail}"))
        except exc as e:
            out.append((name, True, f"{type(e).__name__}: {str(e)[:56]}"))
        except Exception as e:  # noqa: BLE001
            out.append((name, False, f"wrong error {type(e).__name__}: {e}"))

    dupe = fixtures + [fixtures[0]]
    expect_raise("fault_duplicate_example_id",
                 lambda: V.verify(dupe, expected_count=len(dupe)),
                 V.VerificationError, "duplicate id accepted")
    expect_raise("fault_expected_count_mismatch",
                 lambda: V.verify(fixtures, expected_count=expected_count + 1),
                 V.VerificationError, "count mismatch accepted")
    expect_raise("fault_denominator_mismatch",
                 lambda: RPT.summarize(fixtures, expected_count=expected_count + 5),
                 RPT.DenominatorError, "denominator mismatch accepted")
    expect_raise("fault_unsupported_family_dropped",
                 lambda: V.verify(fixtures, expected_count=expected_count,
                                  expected_families=["factual_recall"]),
                 V.VerificationError, "unsupported family silently dropped")
    expect_raise("fault_invalid_status",
                 lambda: _rec("bad", "f", "totally_made_up", 0.0, 0.0),
                 R.RecordSchemaError, "invalid status accepted")
    expect_raise("fault_status_score_contradiction",
                 lambda: _rec("bad2", "f", "incorrect", 1.0, 1.0),
                 R.RecordSchemaError, "incorrect item with perfect score accepted")
    expect_raise("fault_missing_required_field",
                 lambda: R.from_dict({"example_id": "x"}),
                 R.RecordSchemaError, "missing fields accepted")
    expect_raise("fault_stale_result_schema",
                 lambda: R.from_dict({**fixtures[0].to_dict(),
                                      "legacy_v2_field": "geo"}),
                 R.RecordSchemaError, "stale/unsupported schema accepted")
    expect_raise("fault_mismatched_grader_provenance",
                 lambda: V.verify(fixtures, expected_count=expected_count,
                                  grader_sha256="deadbeef" * 8),
                 V.VerificationError, "wrong grader build accepted")

    corrupted = R.from_dict({**fixtures[0].to_dict(), "prompt_hash": ""})
    expect_raise("fault_corrupted_record_missing_provenance",
                 lambda: V.verify([corrupted] + fixtures[1:],
                                  expected_count=expected_count),
                 V.VerificationError, "record without prompt hash accepted")
    return out


def _regrade_correction_checks() -> list[tuple[str, bool, str]]:
    """Phase 9 correction (D.12/D.21): prove regrade genuinely recomputes from
    retained evidence, prove insufficient evidence preserves historical
    provenance byte-identically, and exercise the full serialize -> reload ->
    regrade -> verify -> report path on a MIXED batch containing one
    insufficient-evidence record.
    """
    out = []

    def rec(name, ok, detail):
        out.append((name, bool(ok), detail))

    def expect_raise(name, fn, exc, detail):
        try:
            fn()
            out.append((name, False, f"*** NOT RAISED *** {detail}"))
        except exc as e:
            out.append((name, True, f"{type(e).__name__}: {str(e)[:70]}"))
        except Exception as e:  # noqa: BLE001
            out.append((name, False, f"wrong error {type(e).__name__}: {e}"))

    fx17 = _rec("fx17_regrade_disagrees_with_stale_score", "structured_heldin",
               "correct", 1.0, 1.0,
               raw="SELECT company FROM companies WHERE row_id = 1",
               sql="SELECT company FROM companies WHERE row_id = 1",
               result={"columns": ["company"], "rows": [["WRONG_COMPANY"]]},
               gold={"columns": ["company"], "rows": [["RIGHT_COMPANY"]]})
    fx18 = _rec("fx18_insufficient_evidence_preserves_old_provenance",
               "structured_heldin", "correct", 1.0, 1.0,
               raw="SELECT company FROM companies WHERE row_id = 2",
               sql="SELECT company FROM companies WHERE row_id = 2",
               result=None, gold=None,
               grader_version="grade_v3.0", grader_sha256="deadbeef" * 8)
    mp_parts = ({"part_id": "count", "answer_type": "scalar",
                "target_columns": ["n"]},
               {"part_id": "companies", "answer_type": "set",
                "target_columns": ["company"]})
    fx19 = _rec("fx19_multipart_regrade_recomputes", "structured_paraphrase",
               "correct", 1.0, 1.0, answer_type="multi_part",
               target_columns=("n", "company"), parts=mp_parts,
               result={"parts": {
                   "count": {"columns": ["n"], "rows": [[2]]},
                   "companies": {"columns": ["company"],
                                "rows": [["A"], ["WRONG"]]}}},
               gold={"parts": {
                   "count": {"columns": ["n"], "rows": [[2]]},
                   "companies": {"columns": ["company"],
                                "rows": [["A"], ["B"]]}}})
    fx20 = _rec("fx20_multipart_missing_one_part_evidence",
               "structured_paraphrase", "correct", 1.0, 1.0,
               answer_type="multi_part", target_columns=("n", "company"),
               parts=mp_parts,
               result={"parts": {"count": {"columns": ["n"], "rows": [[2]]}}},
               gold={"parts": {"count": {"columns": ["n"], "rows": [[2]]}}})

    mixed_batch = [fx17, fx18, fx19, fx20]
    rec("pre_regrade_all_start_unregraded",
        all(r.regrade_outcome is None for r in mixed_batch),
        "no record carries a regrade_outcome before regrade() runs")

    current_sha = FROZEN["finetune/grade_v3.py"]
    regraded = V.regrade(mixed_batch, grader_sha256=current_sha)
    by_id = {r.example_id: r for r in regraded}

    r17 = by_id["fx17_regrade_disagrees_with_stale_score"]
    rec("regrade_recomputes_and_disagrees_with_stale_score",
        r17.status == "incorrect" and r17.task_result_correctness == 0.0
        and r17.regrade_outcome == "recomputed"
        and r17.grader_sha256 == current_sha,
        f"stale score was 'correct'; genuine recomputation from retained "
        f"evidence (WRONG_COMPANY vs RIGHT_COMPANY) now correctly says "
        f"'{r17.status}' -- proves regrade recomputes rather than re-stamping")

    r18 = by_id["fx18_insufficient_evidence_preserves_old_provenance"]
    rec("insufficient_evidence_preserves_status_and_scores",
        r18.status == "correct" and r18.task_result_correctness == 1.0
        and r18.strict_result_schema_accuracy == 1.0,
        "status/scores byte-identical to pre-regrade despite no retained "
        "execution_result/gold")
    rec("insufficient_evidence_preserves_grader_provenance",
        r18.grader_version == "grade_v3.0" and r18.grader_sha256 == "deadbeef" * 8,
        "grader_version/grader_sha256 NOT re-stamped to the current build -- "
        "a record must never claim to originate from a grader that never "
        "actually evaluated it")
    rec("insufficient_evidence_outcome_flagged",
        r18.regrade_outcome == "insufficient_evidence",
        "regrade_outcome correctly distinguishes this from a real recompute")

    r19 = by_id["fx19_multipart_regrade_recomputes"]
    rec("multipart_regrade_recomputes_and_disagrees",
        r19.status == "incorrect" and r19.task_result_correctness == 0.0
        and r19.regrade_outcome == "recomputed",
        f"one part's retained evidence disagrees (WRONG vs B); multi-part "
        f"regrade correctly recomputes to '{r19.status}'")

    r20 = by_id["fx20_multipart_missing_one_part_evidence"]
    rec("multipart_missing_one_part_is_insufficient_not_partial",
        r20.regrade_outcome == "insufficient_evidence"
        and r20.status == "correct" and r20.task_result_correctness == 1.0,
        "a single part lacking retained evidence makes the WHOLE item "
        "insufficient_evidence, never a partial recompute; original score "
        "preserved untouched")

    # assert_fully_regraded: strict whitelist, not a blacklist
    expect_raise("assert_fully_regraded_rejects_mixed_batch",
                lambda: V.assert_fully_regraded(regraded,
                                                expected_grader_sha256=current_sha),
                V.VerificationError,
                "a batch containing insufficient_evidence records must not "
                "be certifiable as fully regraded")

    fully_recomputable = [fx17, fx19]
    fully_regraded = V.regrade(fully_recomputable, grader_sha256=current_sha)
    try:
        V.assert_fully_regraded(fully_regraded, expected_grader_sha256=current_sha)
        rec("assert_fully_regraded_accepts_genuine_full_coverage", True,
            "a batch where every record is genuinely recomputed under the "
            "current grader passes")
    except V.VerificationError as e:
        rec("assert_fully_regraded_accepts_genuine_full_coverage", False,
            f"wrongly rejected: {e}")

    never_regraded = [fx17]
    expect_raise("assert_fully_regraded_rejects_never_regraded",
                lambda: V.assert_fully_regraded(never_regraded,
                                                expected_grader_sha256=current_sha),
                V.VerificationError,
                "regrade_outcome is None (never regraded) must not pass -- "
                "a whitelist rejects this, not only the known-bad blacklist value")

    stale_stamped = V.regrade([fx17], grader_sha256="stale_build_sha")
    expect_raise("assert_fully_regraded_rejects_stale_grader_build",
                lambda: V.assert_fully_regraded(stale_stamped,
                                                expected_grader_sha256=current_sha),
                V.VerificationError,
                "'recomputed' under a DIFFERENT (stale) grader build must not "
                "pass as fresh under the CURRENT one")

    cov = V.regrade_coverage(regraded)
    rec("regrade_coverage_accounts_for_every_record",
        cov == {"recomputed": 2, "insufficient_evidence": 2,
               "not_yet_regraded": 0, "total": 4},
        f"{cov}")

    # ---- full path: serialize -> reload -> regrade -> verify -> report ----
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "mixed_batch.jsonl"
        R.write_records(path, mixed_batch)
        reloaded = [R.from_dict(json.loads(line))
                   for line in path.read_text(encoding="utf-8").splitlines()]
        rec("full_path_reload_preserves_records",
            len(reloaded) == 4
            and all(r.regrade_outcome is None for r in reloaded),
            "serialized/reloaded records are unregraded, matching what was written")

        reloaded_regraded = V.regrade(reloaded, grader_sha256=current_sha)
        vres = V.verify(reloaded_regraded, expected_count=4)
        rec("full_path_verify_passes_structurally", vres["passed"],
            "structural verification passes on the regraded mixed batch "
            "(verify does not itself judge regrade completeness)")

        rpt_summary = RPT.summarize(reloaded_regraded, expected_count=4)
        rec("full_path_report_shows_mixed_coverage",
            rpt_summary["regrade_coverage"] == {
                "recomputed": 2, "insufficient_evidence": 2,
                "not_yet_regraded": 0, "total": 4},
            f"{rpt_summary['regrade_coverage']}")
        expect_raise("full_path_cannot_certify_fully_regraded",
                    lambda: V.assert_fully_regraded(
                        reloaded_regraded, expected_grader_sha256=current_sha),
                    V.VerificationError,
                    "end-to-end: a report built from this reloaded, regraded, "
                    "mixed batch still cannot claim full regrade coverage")

    # ---- second independent-audit round: report certification must check
    # grader IDENTITY, not merely count recomputed==total (reproduced: a
    # record regraded under a STALE grader build previously rendered "fully
    # regraded under the current grader").
    stale_grader_rec = _rec("stale_grader_fx", "structured_heldin", "correct",
                           1.0, 1.0, grader_version="grade_v3.0",
                           grader_sha256="STALE_OLD_GRADER_SHA")
    stale_regraded = V.regrade([stale_grader_rec], grader_sha256="STALE_OLD_GRADER_SHA")
    rpt_summary_stale = RPT.summarize(
        stale_regraded, expected_count=1,
        expected_grader_sha256=current_sha)
    rec("report_certification_checks_grader_identity_not_just_counts",
        rpt_summary_stale["fully_regraded_certified"] is False,
        f"a record 'recomputed' under a stale grader build must NOT certify "
        f"as fully regraded under the current one: "
        f"fully_regraded_certified={rpt_summary_stale['fully_regraded_certified']}")
    skeleton_stale = RPT.render_report_skeleton(
        rpt_summary_stale, RPT.error_analysis(stale_regraded),
        stats_demo={}, provenance={})
    rec("report_renders_not_fully_regraded_for_stale_grader",
        "NOT fully regraded" in skeleton_stale,
        "the rendered report text must say NOT fully regraded, not falsely "
        "claim certification")

    genuine_fx = _rec("genuine_fx", "structured_heldin", "correct", 1.0, 1.0,
                      raw="SELECT company FROM companies WHERE row_id = 1",
                      sql="SELECT company FROM companies WHERE row_id = 1",
                      result={"columns": ["company"], "rows": [["X"]]},
                      gold={"columns": ["company"], "rows": [["X"]]})
    genuinely_current = V.regrade([genuine_fx], grader_sha256=current_sha)
    rpt_summary_genuine = RPT.summarize(
        genuinely_current, expected_count=1,
        expected_grader_sha256=current_sha)
    rec("report_certifies_when_genuinely_fully_regraded",
        rpt_summary_genuine["fully_regraded_certified"] is True,
        "a record recomputed under the actual current grader build correctly "
        "certifies as fully regraded")
    rec("report_omits_certification_when_not_requested",
        RPT.summarize(genuinely_current, expected_count=1)
        ["fully_regraded_certified"] is None,
        "omitting expected_grader_sha256 makes no fully-regraded claim "
        "either way (safer default than assuming completeness)")

    # ---- multi-part regrade must preserve the extra-statement penalty -----
    mp_item_extra = {"answer_type": "multi_part", "target_columns": ["n"],
                     "parts": [{"part_id": "p1", "answer_type": "scalar",
                               "target_columns": ["n"]}]}
    fresh = G.grade_structured(mp_item_extra, "SELECT 1 AS n; SELECT 2",
                              {"p1": "SELECT 1 AS n"}, "train_kb", db_path=DB)
    rec("fresh_grading_penalizes_extra_statement",
        fresh.task_result_correctness == 1.0
        and fresh.strict_result_schema_accuracy == 0.0,
        f"task={fresh.task_result_correctness} schema={fresh.strict_result_schema_accuracy}")
    fx_extra = _rec("fx21_multipart_extra_statement_retained", "structured_paraphrase",
                    fresh.status, fresh.task_result_correctness,
                    fresh.strict_result_schema_accuracy,
                    answer_type="multi_part", target_columns=("n",),
                    parts=tuple(mp_item_extra["parts"]),
                    result={"parts": {"p1": {"columns": ["n"], "rows": [[1]]}},
                           "extra_present": fresh.metrics.get("extra_present")},
                    gold={"parts": {"p1": {"columns": ["n"], "rows": [[1]]}}})
    regraded_extra = V.regrade([fx_extra], grader_sha256=current_sha)[0]
    rec("regrade_preserves_extra_statement_penalty",
        regraded_extra.task_result_correctness == 1.0
        and regraded_extra.strict_result_schema_accuracy == 0.0
        and regraded_extra.regrade_outcome == "recomputed",
        f"regrading from retained evidence (with extra_present retained "
        f"alongside per-part evidence) reproduces the SAME strict-schema "
        f"penalty fresh grading applied: task={regraded_extra.task_result_correctness} "
        f"schema={regraded_extra.strict_result_schema_accuracy}")

    return out


def _write_audit(checks, faults, summary, errors, stats_demo, provenance,
                 rec_sha, sum_sha, err_sha, rep_sha, expected_count, families,
                 man_sha):
    mod = {m: sha256_file(ROOT / "finetune" / m) for m in STACK_MODULES}
    mod["phase8_eval_stack_tests.py"] = sha256_file(Path(__file__).resolve())
    L = ["# EVAL_STACK_VALIDATION_v3\n",
         "Phase 8 — build the v3 evaluation and reporting stack.\n",
         "> **This filename is a Phase 8 implementation/provenance convention.** "
         "`README.md` and `CLAUDE.md` do not prescribe a dedicated Phase 8 "
         "validation-artifact filename. README was not amended to name it.\n",
         "> Every number in this document comes from **deterministic synthetic "
         "fixtures**. Nothing here is an experimental result.\n",
         "## Frozen Phase 7 inputs\n", "```text"]
    for rel, sha in FROZEN.items():
        L.append(f"{rel:34} {sha}")
    L += ["```\n", "## Stack modules\n", "```text"]
    for m, sha in mod.items():
        L.append(f"finetune/{m:32} {sha}")
    L += ["```\n",
         "Rebuilt v3-native rather than ported. v2's stack is 4,213 lines and "
         "`report.py` alone carries 111 retired-concept references; README Phase 8 "
         "warns that recreating it \"would add risk rather than remove it\". Only "
         "the statistical METHODS were carried across as concepts, reimplemented "
         "against the v3 schema — no v2 file was copied.\n",
         "## Fixture manifest\n", "```text",
         f"validation_v3/fixtures_v3/fixture_records_v3.jsonl   {rec_sha}",
         f"validation_v3/fixtures_v3/fixtures_manifest_v3.json  {man_sha}",
         f"validation_v3/fixtures_v3/summary_v3.json            {sum_sha}",
         f"validation_v3/fixtures_v3/error_analysis_v3.json     {err_sha}",
         f"validation_v3/fixtures_v3/REPORT_v3.md               {rep_sha}",
         f"fixture item count                                   {expected_count}",
         f"families                                             {', '.join(families)}",
         "```\n",
         "The fixture-local `REPORT_v3.md` is a **skeleton** carrying a synthetic "
         "banner. The authoritative repo-root `REPORT_v3.md` is created only at "
         "**Phase 42** and does not exist yet.\n",
         "## Result-record schema\n",
         f"{len(R.REQUIRED_FIELDS)} fields, covering every README Phase 40 "
         "retention requirement — `example_id`, question, raw output, parsed "
         "output, generated SQL, execution result, gold, score, error type, "
         "adapter hash, prompt hash — plus the frozen Phase 7 grading metadata. "
         "README's rule is explicit: **never scores alone**.\n", "```text",
         "  " + ", ".join(R.REQUIRED_FIELDS), "```\n",
         "The status vocabulary is imported from the frozen Phase 7 grader rather "
         "than redeclared, so the two cannot drift apart.\n",
         "## Status and denominator accounting\n", "```text",
         f"expected item count   {summary['expected_item_count']}",
         f"scored                {summary['scored']}",
         f"failed                {summary['failed']}",
         f"scored + failed       {summary['denominator_invariant']['scored_plus_failed']}",
         f"invariant holds       {summary['denominator_invariant']['holds']}",
         "```\n",
         "| status | count |", "|---|---|"]
    for s, c in summary["status_counts"].items():
        L.append(f"| `{s}` | {c} |")
    L += ["",
          "All eight frozen statuses are exercised. Every item ends in exactly one, "
          "and non-success counts against the denominator — no item disappears, "
          "counts twice, or silently becomes correct.\n",
          "## Primary and secondary metrics\n",
          "| metric | role | fixture value |", "|---|---|---|",
          f"| `task_result_correctness` | **primary** | "
          f"{summary['task_result_correctness']['rendered']} |",
          f"| `strict_result_schema_accuracy` | secondary | "
          f"{summary['strict_result_schema_accuracy']['rendered']} |",
          "",
          "Fixtures prove the two can diverge in **both** directions — "
          "`fx07` is task-correct with a wrong schema, `fx08` is task-wrong with a "
          "correct schema — so the secondary can never stand in for the primary.\n",
          "## Per-family metrics\n",
          "| family | n | correct | incorrect | failed | task | schema |",
          "|---|---|---|---|---|---|---|"]
    for fam, m in summary["families"].items():
        L.append(f"| `{fam}` | {m['n_items']} | {m['correct']} | {m['incorrect']} | "
                 f"{m['failed']} | {m['task_result_correctness']:.1%} | "
                 f"{m['strict_result_schema_accuracy']:.1%} |")
    L += ["",
          "Families are discovered from the records. A previously unseen family "
          "(`brand_new_family_v3`) appears in the summary with **no code edit**, "
          "which is the property v2's hard-coded `REPORT_ORDER` lacked.\n",
          "## Error analysis\n",
          f"{errors['n_failures']} synthetic failures grouped by status, family and "
          "`answer_type`, distinguishing the frozen outcome classes:\n",
          "| class | count |", "|---|---|"]
    for k, v in errors["distinguished_classes"].items():
        if v:
            L.append(f"| `{k}` | {v} |")
    L += ["",
          "No scientific error taxonomy is invented from probes that do not exist.\n",
          "## Statistical plumbing\n",
          "Every method maps to an explicit live-protocol requirement. Nothing is "
          "included because v2 had it.\n",
          "| method | frozen requirement |", "|---|---|",
          "| per-seed scores | README:972, CLAUDE.md:826 |",
          "| mean ± SD | README:972, CLAUDE.md:827 |",
          "| effect size | README:972, CLAUDE.md:828 |",
          "| paired item-level bootstrap | README:972, CLAUDE.md:829 |",
          "| exact denominators | README:972, CLAUDE.md §28 |",
          "| Holm correction | README:974 |",
          "| McNemar (secondary) | README:973 |",
          "| split-group weighting | README:990-991, CLAUDE.md:847-854 |",
          "",
          "**Deferred: hierarchical bootstrap.** v2 implemented it; the live "
          "protocol never mentions it, so it is not introduced here.\n",
          "Fixture outputs (synthetic inputs, no significance claim):\n", "```text"]
    for k, v in _stats_render(stats_demo).items():
        L.append(f"{k:26} {v}")
    L += ["```\n",
          "A deterministic baseline is **refused** an SD rather than reported as "
          "0.0, per README:976-979. Split-group weighting averages within group "
          "then across groups unweighted, and excludes the non-attributable "
          "aggregate item as undefined.\n",
          "## Verification and regrade\n",
          "Verify checks expected count, unique `example_id`, exactly-one-status, "
          "required fields, provenance, denominator integrity, duplicates and "
          "silently dropped families. Regrade re-runs the frozen Phase 7 grader "
          "over retained raw predictions, carries the raw prediction, gold and "
          "question through untouched, and stamps grader version and hash — it "
          "never repairs SQL, changes gold, or overwrites without provenance.\n",
          "## Sealed-test guard\n",
          "Test and Q42 remain `LOCKED_UNTIL_PHASE_40`. Validated with **synthetic "
          "sealed fixtures only** — no real test or Q42 prediction, example, gold, "
          "score or error case was created, read, reported or inferred.\n",
          "### Correction history — two successive defects, both reproduced\n",
          "**Stage 1 — the original family-based design (fail-open).** The first "
          "Phase 8 candidate inferred sealing from `family` strings **inside the "
          "records**. Independent review demonstrated three failures, all "
          "reproduced before the redesign:\n",
          "1. a sealed artifact whose records declared `family = factual_recall` "
          "was **accepted** by `load_dev_results` — content classified itself\n"
          "2. `classify_result_set(\"brand_new_future_family\")` returned `dev` — "
          "an unknown future family silently defaulted **open**\n"
          "3. `sealed_metadata` **parsed sealed records** to compute `families` and "
          "`conditions`, exceeding the pre-Phase-40 metadata boundary\n",
          "**Stage 1 root cause:** the sealing decision was attached to what the "
          "artifact said about itself rather than to the artifact, and the default "
          "for an unrecognised value was open rather than closed.\n",
          "**Stage 2 — the first registry redesign (still caller-controlled).** "
          "Replacing family strings with an `ArtifactRegistry` fixed content-based "
          "classification, but the registry was **constructed and passed by the "
          "caller**. Independent review reproduced two further bypasses: an "
          "ordinary caller could build a second registry declaring the same sealed "
          "path as `dev` and load it, and could mutate an existing registry in "
          "place via `register(...)`. The trust boundary had merely moved from "
          "caller-controlled *family* to caller-controlled *registry declaration*. "
          "**This stage was not sufficient, and the audit does not present it as "
          "though it were.**\n",
          "**Stage 3 — trusted authority (current).** Classification now comes "
          "from a frozen manifest loaded by one internal factory into an immutable "
          "authority. Ordinary dev/report code may QUERY classification and cannot "
          "redefine it.\n",
          "### The current design: trusted, immutable classification authority\n",
          "```text",
          "identify artifact (resolved canonical path)",
          "    -> trusted registry lookup + integrity hash",
          "    -> classification: dev | sealed | unknown",
          "    -> sealed or unknown  -> REFUSE",
          "    -> only an authorized dev artifact is opened and parsed",
          "```\n",
          "`family`, `condition`, `status`, filename keywords and record contents "
          "take **no part** in the security decision. Identity is the resolved "
          "canonical path plus the registered SHA256; the manifest predeclares "
          "`item_count`, so metadata never requires opening sealed content.\n",
          "**Classify-before-parse is proved, not asserted.** One synthetic sealed "
          "fixture contains deliberately unparseable bytes "
          "(`<<<NOT-JSON-AT-ALL>>>`). It raises `SealError`, never a JSON error — "
          "so authorization demonstrably happened before any parser ran. "
          "`sealed_metadata` returns full metadata for that same unparseable "
          "artifact. That is possible because it reads raw bytes only to verify "
          "the registered hash and **never parses record content**.\n",
          "### Trust boundary\n",
          "```text",
          "frozen trusted manifest",
          "    -> internal factory (_build_authority_from_manifest)",
          "    -> validated deterministically, conflicts rejected",
          "    -> IMMUTABLE authority",
          "    -> dev/report code QUERIES it; cannot redefine it",
          "```\n",
          "`load_dev_results(path)` and `sealed_metadata(path)` take **no** "
          "registry, authority, manifest, unseal, allow_test, bypass_seal or force "
          "argument, so a caller has nowhere to attach a competing authority. The "
          "authority exposes no `register`, its mappings are read-only, and "
          "attribute assignment raises. Conflicting manifest entries — the same "
          "path with different kinds, or the same `artifact_id` with a different "
          "path/hash/kind — are rejected rather than resolved last-write-wins. An "
          "uninitialized authority refuses rather than defaulting open.\n",
          "**Threat model, stated accurately.** This is a workflow-integrity and "
          "accidental-leakage boundary, not a sandbox against hostile code. "
          "Arbitrary Python with full module and filesystem access can always "
          "reach private names; Phase 8 does not claim otherwise. The guarantee is "
          "the narrower one the protocol needs: **the normal supported dev/report "
          "API offers no route to reinterpret a sealed artifact as dev.** Phase 8 "
          "fixtures stand up synthetic trusted environments through an explicitly "
          "underscore-prefixed, fixture-only hook that is not part of that API.\n",
          "The synthetic `trusted_artifacts_v3.json` used by the gate validates the "
          "ARCHITECTURE only. It is not, and does not claim to be, the future real "
          "test manifest.\n",
          "**Fail closed.** An unregistered artifact, a copied artifact at a new "
          "path, and a registered path whose bytes no longer match its hash all "
          "classify `unknown` and are refused. Unknown never becomes dev.\n",
          "**Path identity.** Absolute, relative and dotted spellings resolve to "
          "one identity, and a symlink pointing at a registered sealed artifact "
          "remains sealed.\n",
          "**Restricted metadata contract.** `sealed_metadata` may read raw bytes "
          "for integrity hashing but never parses or exposes evaluation-record "
          "content. It returns exactly: "
          "`artifact_id`, `artifact_path`, `sha256`, `item_count`, "
          "`schema_version`, `provenance`, `artifact_kind`, `records_parsed`. "
          "No family, condition, status, score, error type, answer type, "
          "question, gold, SQL or execution result — and no per-family or "
          "score distribution.\n",
          "**No pre-Phase-40 unseal capability.** There is no `unseal` parameter "
          "on any dev or library API; a generic boolean switch would also unlock "
          "real sealed output later. The real unblind authority belongs to the "
          "Phase 40 entry point (`CLAUDE.md` §23) and is deliberately not created "
          "here.\n",
          "The seal boundary is enforced at **ingress**. `summarize` and "
          "`error_analysis` are pure computations over already-authorized records "
          "and deliberately no longer re-derive sealing from record content, "
          "since that is the unsound check this replaced.\n",
          "## Retired components\n",
          f"None of {len(RETIRED)} retired concepts appear in the stack, and no v2 "
          "repository path or v2 database fallback exists. The stack opens no "
          "database connection of its own: SQL fixtures call the approved Phase 7 "
          "executor.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        L.append(f"| `{name}` | {'PASS' if ok else 'FAIL'} | {detail} |")
    L += ["", "## Fault tests\n", "| fault | rejected | how |", "|---|---|---|"]
    for name, ok, detail in faults:
        L.append(f"| `{name}` | {'yes' if ok else '**NO**'} | {detail} |")
    L.append("")
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Gate as exc:
        print(f"\nPHASE 8 GATE FAILURE: {exc}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
