"""Phase 6 fault-injection suite.

Each fault must be rejected. A gate that only passes on good input proves little.

Includes a NEGATIVE CONTROL for the leakage definition: a raw KB value that
happens to equal the eventual answer (e.g. `Employment: 500` when the answer is
`500`) must NOT be flagged. In an oracle-context baseline the correct row is
supplied deliberately, so its evidence is expected to answer the question.
Only a separate target/evaluation ARTIFACT is forbidden.

Committed artifacts are never modified: every fault runs on in-memory values or
temporary paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as kb                      # noqa: E402
import context_renderer_v3 as ctx       # noqa: E402
import phase6_context_budget as p6      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def record(name, ok, detail):
        results.append((name, bool(ok), detail))

    tok = p6.load_real_tokenizer()
    cfg = p6.resolve_context_config()

    # --- 1-3. Scope discipline -------------------------------------------
    try:
        ctx.render_oracle_context()               # type: ignore[call-arg]
        record("omitted_scope", False, "*** ACCEPTED ***")
    except TypeError as e:
        record("omitted_scope", True, f"TypeError: {str(e)[:64]}")

    try:
        ctx.render_oracle_context(None, 1)
        record("none_scope", False, "*** ACCEPTED ***")
    except ctx.ScopeError as e:
        record("none_scope", True, f"ScopeError: {str(e)[:58]}")

    try:
        ctx.render_oracle_context("full", 1)
        record("invalid_scope", False, "*** ACCEPTED ***")
    except ctx.ScopeError as e:
        record("invalid_scope", True, f"ScopeError: {str(e)[:58]}")

    test_ids = ({r.row_id for r in kb.load_kb("full_kb")}
                - {r.row_id for r in kb.load_kb("train_dev_kb")})
    rid = sorted(test_ids)[0]
    try:
        ctx.render_oracle_context("train_kb", rid)
        record("row_outside_requested_scope", False,
               f"*** test row {rid} RETURNED under train_kb ***")
    except ctx.ScopeError as e:
        record("row_outside_requested_scope", True,
               f"test row {rid} rejected: {str(e)[:52]}")

    # --- 4. Prompt over budget -------------------------------------------
    try:
        p6.assert_within_budget(cfg["usable_context"] - 1, cfg, "oversized")
        record("prompt_over_budget", False, "*** ACCEPTED ***")
    except p6.Gate as e:
        record("prompt_over_budget", True, f"Gate: {str(e)[:70]}")

    # Boundary: exactly at the limit passes, one token over fails.
    edge_ok = True
    try:
        p6.assert_within_budget(cfg["max_input_tokens"], cfg, "exact-fit")
    except p6.Gate:
        edge_ok = False
    edge_rejects = False
    try:
        p6.assert_within_budget(cfg["max_input_tokens"] + 1, cfg, "one-over")
    except p6.Gate:
        edge_rejects = True
    record("budget_boundary_exact", edge_ok and edge_rejects,
           f"{cfg['max_input_tokens']} accepted, {cfg['max_input_tokens'] + 1} rejected")

    # --- 5. Attempted silent truncation ----------------------------------
    tmp = Path(ROOT / "validation_v3" / "_fault_tmp.py")
    try:
        tmp.write_text(
            "def f(tok, text):\n"
            "    return tok(text, truncation=True, max_length=24576)\n",
            encoding="utf-8")
        hits = p6.scan_for_truncation([tmp])
        record("attempted_silent_truncation", len(hits) >= 1,
               f"scanner flagged {len(hits)} occurrence(s)")
    finally:
        tmp.unlink(missing_ok=True)

    # Negative control: prose documenting the prohibition must NOT be flagged.
    tmp2 = Path(ROOT / "validation_v3" / "_fault_tmp2.py")
    try:
        tmp2.write_text(
            '"""We never pass truncation=True or max_length=24576 anywhere."""\n'
            "# truncation=True is forbidden\n"
            "def g(tok, text):\n"
            "    return tok(text)\n",
            encoding="utf-8")
        hits2 = p6.scan_for_truncation([tmp2])
        record("truncation_scan_no_false_positive_on_prose", not hits2,
               "docstring/comment describing the rule is not flagged")
    finally:
        tmp2.unlink(missing_ok=True)

    # --- 6-9. Context content faults --------------------------------------
    clean = ctx.render_oracle_context("full_kb", 1)

    def artifact_hits(text: str) -> list[str]:
        low = text.casefold()
        return [m for m in p6.FORBIDDEN_ARTIFACT_MARKERS if m in low]

    def meta_hits(text: str) -> list[str]:
        low = text.casefold()
        return [f for f in ctx.FORBIDDEN_IN_CONTEXT
                if f in low or f.replace("_", " ") in low]

    record("forbidden_metadata_injection",
           bool(meta_hits(clean + "\nsplit_group: lund_international")),
           "split_group injection detected")
    record("gold_answer_annotation_injection",
           bool(artifact_hits(clean + "\nGold answer: Manufacturing Plant")),
           "explicit 'Gold answer:' annotation detected")
    record("gold_sql_injection",
           bool(artifact_hits(clean + "\ngold_sql: SELECT company FROM companies")),
           "gold_sql annotation detected")
    record("generated_qa_injection",
           bool(artifact_hits(clean + "\ngenerated_qa: Q: ...? A: ...")),
           "generated_qa annotation detected")
    record("evaluation_metadata_injection",
           bool(artifact_hits(clean + "\nanswer_type: scalar\ntarget_columns: [company]")),
           "answer_type/target_columns detected")

    # --- NEGATIVE CONTROL for the leakage definition ----------------------
    # A raw KB value equal to the eventual answer must NOT be treated as leakage.
    rec = next(r for r in kb.load_kb("full_kb") if r.row_id == 1)
    raw_answer_value = str(rec.employment)
    record("raw_kb_value_matching_answer_is_NOT_leakage",
           not artifact_hits(clean) and raw_answer_value in clean,
           f"context legitimately contains Employment {raw_answer_value} "
           f"with zero artifact markers")

    # --- 10. Frozen DB / hash drift ---------------------------------------
    orig = p6.EXPECTED_DB_SHA
    try:
        p6.EXPECTED_DB_SHA = "deadbeef" * 8
        p6.main()
        record("frozen_db_hash_drift", False, "*** NOT CAUGHT ***")
    except p6.Gate as e:
        record("frozen_db_hash_drift", True, f"Gate: {str(e).splitlines()[0][:60]}")
    except Exception as e:  # noqa: BLE001
        record("frozen_db_hash_drift", False, f"wrong error {type(e).__name__}: {e}")
    finally:
        p6.EXPECTED_DB_SHA = orig

    orig_t = kb.EXPECTED_CANONICAL_SHA
    try:
        kb.EXPECTED_CANONICAL_SHA = "deadbeef" * 8
        ctx.render_oracle_context("full_kb", 1)
        record("frozen_canonical_hash_drift", False, "*** NOT CAUGHT ***")
    except kb.IntegrityError as e:
        record("frozen_canonical_hash_drift", True,
               f"IntegrityError: {str(e).splitlines()[0][:52]}")
    finally:
        kb.EXPECTED_CANONICAL_SHA = orig_t

    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] fault:{name}: {detail}")
    missed = [n for n, ok, _ in results if not ok]
    if missed:
        print(f"\nFAULT SUITE FAILED — {len(missed)} not caught: {missed}", file=sys.stderr)
        return 1
    print(f"\nAll {len(results)} fault checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
