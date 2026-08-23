"""Phase 6 gate -- context renderer and token budget.

Budget assertion, exactly as frozen:

    measured_input_tokens + max_new_tokens <= usable_context
    usable_context = min(model configured context, evaluator max_seq_length)

NOT `input_tokens < tokenizer.model_max_length`. The tokenizer advertises
131072 while the model config supports 32768 -- believing the advertisement is
precisely the model/evaluator mismatch this gate exists to prevent.

Token counts come from the REAL Qwen tokenizer at the pinned revision, loaded
with local_files_only=True. No estimator, no other model's tokenizer, no silent
substitution. The real chat template is applied so the measurement covers the
complete prompt, not just the context block.

NO SILENT TRUNCATION ANYWHERE. Tokenization is called without truncation, and a
source scan rejects truncation/slicing/clipping in the Phase 6 code paths. An
over-budget prompt raises.

Phase 6 measures all 205 frozen rows as STRUCTURAL RENDERER FIXTURES. It does
not claim that future factual probes are validated -- those do not exist yet and
must be re-checked with this same budget checker when generated.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kb_v3 as kb                    # noqa: E402
import context_renderer_v3 as ctx     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "datasets_v3" / "gnem_v3.sqlite"
OUT_AUDIT = ROOT / "validation_v3" / "CONTEXT_BUDGET_v3.md"

EXPECTED_DB_SHA = "7437c746cb118f3d5bb9edcc34f500e0c9f764358a19fa05766dc526d63bb08b"

# ---- Frozen model / tokenizer identity ------------------------------------
TOKENIZER_ID = "Qwen/Qwen2.5-14B-Instruct"
TOKENIZER_REVISION = "cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8"
EXPECTED_TOKENIZER_JSON_SHA = (
    "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539")

# ---- Frozen context budget -------------------------------------------------
EVALUATOR_MAX_SEQ_LENGTH = 32768      # frozen in Phase 6
MAX_NEW_TOKENS = 1024                 # reserved before any prompt is accepted
EXPECTED_MODEL_CONTEXT = 32768        # asserted against the real config.json

# Deterministic structural fixtures. These exercise the renderer and the
# template overhead. They are NOT probes: no gold answer, no answer_type, no
# target_columns, no evaluation label is stored or emitted anywhere.
FIXTURE_QUESTIONS = (
    "What is the primary facility type of this company?",
    "Which county is this company located in?",
    "Which certifications does this company hold?",
)

# Explicit gold-answer / evaluation ARTIFACTS that must never appear in a
# rendered context. Deliberately annotation markers -- not raw factual values.
# A raw KB fact that happens to contain the eventual answer (e.g.
# "Employment: 500") is legitimate evidence in an oracle-context baseline.
FORBIDDEN_ARTIFACT_MARKERS = (
    "gold answer", "gold_answer", "expected answer", "expected_answer",
    "correct answer", "correct_answer", "gold sql", "gold_sql",
    "answer_type", "target_columns", "probe_id", "is_correct",
    "correctness", "evaluation label", "eval_label", "generated qa",
    "generated_qa", "train_kb_gold", "train_dev_kb_gold", "full_kb_gold",
)
# Phase 5 physical view names must never reach a prompt.
PHYSICAL_VIEW_NAMES = tuple(
    f"{s}_{t}" for s in kb.KB_SCOPES
    for t in ("companies", "certifications", "processes", "services"))


class Gate(Exception):
    """A Phase 6 invariant failed. No artifact is written."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_real_tokenizer():
    """The real Qwen tokenizer at the pinned revision, or a gate failure."""
    try:
        from transformers import AutoTokenizer
    except ImportError as e:
        raise Gate(
            "transformers is unavailable, so the real Qwen tokenizer cannot be "
            "established. Phase 6 does NOT substitute an estimator or another "
            f"model's tokenizer. ({e})")
    try:
        tok = AutoTokenizer.from_pretrained(
            TOKENIZER_ID, revision=TOKENIZER_REVISION, local_files_only=True)
    except Exception as e:  # noqa: BLE001
        raise Gate(f"could not load {TOKENIZER_ID} @ {TOKENIZER_REVISION} "
                   f"from the local cache: {type(e).__name__}: {e}")
    if not tok.chat_template:
        raise Gate("tokenizer has no chat template; complete-prompt measurement "
                   "would be wrong")
    return tok


def resolve_context_config() -> dict:
    """Read the model's real context from config.json -- never the tokenizer's
    advertised model_max_length, and never a hard-coded guess."""
    from huggingface_hub import hf_hub_download
    cfg_path = Path(hf_hub_download(TOKENIZER_ID, "config.json",
                                    revision=TOKENIZER_REVISION,
                                    local_files_only=True))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    model_ctx = cfg.get("max_position_embeddings")
    if model_ctx is None:
        raise Gate("config.json has no max_position_embeddings; usable context "
                   "cannot be established from the real configuration")
    if model_ctx != EXPECTED_MODEL_CONTEXT:
        raise Gate(f"model configured context {model_ctx} != expected "
                   f"{EXPECTED_MODEL_CONTEXT}; budget must not be invented")
    tok_json = Path(hf_hub_download(TOKENIZER_ID, "tokenizer.json",
                                    revision=TOKENIZER_REVISION,
                                    local_files_only=True))
    return {
        "model_configured_context": model_ctx,
        "evaluator_max_seq_length": EVALUATOR_MAX_SEQ_LENGTH,
        "usable_context": min(model_ctx, EVALUATOR_MAX_SEQ_LENGTH),
        "max_new_tokens": MAX_NEW_TOKENS,
        "max_input_tokens": min(model_ctx, EVALUATOR_MAX_SEQ_LENGTH) - MAX_NEW_TOKENS,
        "tokenizer_json_sha256": sha256_file(tok_json),
        "config_json_path": str(cfg_path),
    }


def count_prompt_tokens(tok, messages: list[dict]) -> int:
    """Token length of the COMPLETE prompt, chat template included.

    Tokenized WITHOUT truncation -- passing truncation=True here is exactly the
    silent cut the protocol forbids.
    """
    text = tok.apply_chat_template(messages, tokenize=False,
                                   add_generation_prompt=True)
    ids = tok(text, add_special_tokens=False)["input_ids"]
    return len(ids)


def assert_within_budget(n_input: int, cfg: dict, what: str) -> None:
    """Reserve generation tokens BEFORE accepting a prompt. Raise, never trim."""
    if n_input + cfg["max_new_tokens"] > cfg["usable_context"]:
        raise Gate(
            f"{what}: {n_input} input + {cfg['max_new_tokens']} reserved = "
            f"{n_input + cfg['max_new_tokens']} exceeds usable context "
            f"{cfg['usable_context']}. A prompt that does not fit is a FAILURE, "
            f"never a truncation.")


def scan_for_truncation(paths) -> list[str]:
    """Reject silent truncation/slicing/clipping in the Phase 6 code paths.

    Scans EXECUTABLE CODE, not raw text: string literals, docstrings and
    comments are stripped via `tokenize` first. A regex over raw text would flag
    a docstring that merely *documents* the prohibition -- which is a false
    positive that would push future authors to stop describing the rule.
    """
    import io
    import tokenize as _tk

    patterns = (
        (r"truncation\s*=\s*True", "tokenizer truncation"),
        (r"max_length\s*=\s*\d+", "max_length slicing"),
        (r"\.truncate\(", "explicit truncate call"),
        (r"input_ids\s*\[\s*:\s*\d+", "token-id slicing"),
        (r"\[\s*:\s*\d{3,}\s*\]", "long literal clipping"),
    )
    hits = []
    for path in paths:
        path = Path(path)
        if not path.is_file():
            continue
        src = path.read_text(encoding="utf-8")
        # Rebuild the file with STRING/COMMENT tokens blanked, preserving lines.
        lines = src.splitlines()
        code_lines = list(lines)
        try:
            for tok_ in _tk.generate_tokens(io.StringIO(src).readline):
                if tok_.type in (_tk.STRING, _tk.COMMENT):
                    (r1, c1), (r2, c2) = tok_.start, tok_.end
                    for r in range(r1 - 1, min(r2, len(code_lines))):
                        line = code_lines[r]
                        a = c1 if r == r1 - 1 else 0
                        b = c2 if r == r2 - 1 else len(line)
                        code_lines[r] = line[:a] + " " * (b - a) + line[b:]
        except (_tk.TokenError, IndentationError):
            code_lines = lines  # unparseable: fall back to strict raw scan
        for n, code in enumerate(code_lines, 1):
            for pat, why in patterns:
                if re.search(pat, code):
                    hits.append(f"{path.relative_to(ROOT)}:{n}: {why}: "
                                f"{lines[n - 1].strip()[:70]}")
    return hits


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail):
        checks.append((name, bool(ok), detail))

    # ---- Frozen inputs ---------------------------------------------------
    db_sha = sha256_file(DB)
    if db_sha != EXPECTED_DB_SHA:
        raise Gate(f"Phase 5 database drifted\n  expected {EXPECTED_DB_SHA}\n"
                   f"  actual   {db_sha}")
    check("phase5_db_sha_unchanged", db_sha == EXPECTED_DB_SHA, db_sha)
    hashes = kb.frozen_input_hashes()
    check("phase2_3_4_hashes_unchanged", True,
          f"canonical {hashes['canonical_records_v3.jsonl'][:12]}… · "
          f"split {hashes['company_split_groups_v3.csv'][:12]}… · "
          f"kb_v3 {hashes['kb_v3.py'][:12]}…")

    tok = load_real_tokenizer()
    cfg = resolve_context_config()
    check("real_tokenizer_loaded_at_pinned_revision", True,
          f"{TOKENIZER_ID} @ {TOKENIZER_REVISION[:12]}… ({type(tok).__name__}, "
          f"local_files_only=True)")
    check("tokenizer_json_sha_matches_expected",
          cfg["tokenizer_json_sha256"] == EXPECTED_TOKENIZER_JSON_SHA,
          cfg["tokenizer_json_sha256"])
    check("real_chat_template_used", bool(tok.chat_template),
          "tokenizer.chat_template applied via apply_chat_template")
    check("advertised_limit_not_used_for_budget",
          tok.model_max_length != cfg["usable_context"],
          f"tokenizer advertises {tok.model_max_length}; budget uses "
          f"{cfg['usable_context']} from config.json")
    check("usable_context_equation",
          cfg["usable_context"] == min(cfg["model_configured_context"],
                                       cfg["evaluator_max_seq_length"]),
          f"min({cfg['model_configured_context']}, "
          f"{cfg['evaluator_max_seq_length']}) = {cfg['usable_context']}")
    check("max_input_tokens_reserves_generation",
          cfg["max_input_tokens"] == cfg["usable_context"] - cfg["max_new_tokens"],
          f"{cfg['usable_context']} - {cfg['max_new_tokens']} = "
          f"{cfg['max_input_tokens']}")

    # ---- Render every frozen row as a structural fixture -----------------
    rows = kb.load_kb("full_kb")
    contexts, prompts = {}, []
    for rec in rows:
        c = ctx.render_oracle_context("full_kb", rec.row_id)
        contexts[rec.row_id] = c
        for q in FIXTURE_QUESTIONS:
            msgs = ctx.build_ctx_oracle_prompt("full_kb", rec.row_id, q)
            n = count_prompt_tokens(tok, msgs)
            assert_within_budget(n, cfg, f"row {rec.row_id}")
            prompts.append((rec.row_id, rec.company, q, n))
    check("all_205_rows_rendered", len(contexts) == 205, f"{len(contexts)} contexts")
    check("all_fixture_prompts_within_budget", True,
          f"{len(prompts)} fixture prompts, all satisfying input + "
          f"{cfg['max_new_tokens']} <= {cfg['usable_context']}")

    ctx_tokens = {rid: len(tok(c, add_special_tokens=False)["input_ids"])
                  for rid, c in contexts.items()}
    p_tokens = [n for _, _, _, n in prompts]
    worst_rid = max(ctx_tokens, key=lambda r: ctx_tokens[r])
    worst_prompt = max(prompts, key=lambda x: x[3])
    overhead = min(p_tokens) - min(ctx_tokens.values())

    # ---- Raw-fact-only: forbidden ARTIFACTS, not raw values --------------
    artifact_hits = []
    for rid, c in contexts.items():
        low = c.casefold()
        for marker in FORBIDDEN_ARTIFACT_MARKERS:
            if marker in low:
                artifact_hits.append((rid, marker))
    check("no_gold_answer_or_evaluation_artifacts", not artifact_hits,
          "no gold-answer/gold-SQL/generated-QA/answer_type/target_columns/"
          "correctness annotation in any context"
          if not artifact_hits else f"{artifact_hits[:5]}")

    meta_hits = []
    for rid, c in contexts.items():
        low = c.casefold()
        for f in ctx.FORBIDDEN_IN_CONTEXT:
            if f.replace("_", " ") in low or f in low:
                meta_hits.append((rid, f))
    check("no_infrastructure_metadata_in_context", not meta_hits,
          "split/split_group/certification_count/lat/long/graph absent"
          if not meta_hits else f"{meta_hits[:5]}")

    view_hits = [(rid, v) for rid, c in contexts.items()
                 for v in PHYSICAL_VIEW_NAMES if v in c]
    check("no_physical_scoped_view_names_in_context", not view_hits,
          f"none of {len(PHYSICAL_VIEW_NAMES)} Phase 5 view names appear")

    # Raw KB evidence IS preserved -- the point of an oracle-context baseline.
    canon_ok = all(
        f"Employment{ctx.LABEL_SEP}{r.employment}" in contexts[r.row_id]
        and f"Company{ctx.LABEL_SEP}{r.company}" in contexts[r.row_id]
        for r in rows)
    check("raw_kb_facts_preserved_in_context", canon_ok,
          "canonical values render verbatim; evidence that answers a question is "
          "expected in an oracle-context baseline and is NOT leakage")

    sentinel_rows = [r for r in rows if r.certifications ==
                     "None identified after search"]
    check("zero_certification_rows_render_frozen_sentinel",
          all("Certifications: None identified after search" in contexts[r.row_id]
              for r in sentinel_rows),
          f"{len(sentinel_rows)} row(s) render the frozen state; no certification "
          f"fact manufactured")

    # ---- Duplicate-render guard -------------------------------------------
    dup = [rid for rid, c in contexts.items()
           if c.count("Processes: ") != 1 or c.count("Services: ") != 1
           or c.count("Certifications: ") != 1]
    check("multivalued_fields_rendered_exactly_once", not dup,
          f"{len(dup)} row(s) rendering a multi-valued field more than once")

    # ---- Determinism -------------------------------------------------------
    again = {r.row_id: ctx.render_oracle_context("full_kb", r.row_id) for r in rows}
    check("rendering_deterministic_in_process", again == contexts,
          "byte-identical on repeat render")
    sub = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys;sys.path.insert(0,'finetune');import context_renderer_v3 as c;"
         "print(c.render_oracle_context('full_kb', 10))"],
        cwd=ROOT, capture_output=True, text=True)
    check("rendering_deterministic_across_process",
          sub.returncode == 0 and sub.stdout.rstrip("\n") == contexts[10],
          "fresh interpreter reproduces byte-identical output")

    # ---- Scope discipline --------------------------------------------------
    scope_fail = []
    for bad in (None, "full", "FULL_KB", 123):
        try:
            ctx.render_oracle_context(bad, 1)
            scope_fail.append(bad)
        except ctx.ScopeError:
            pass
    check("explicit_scope_required", not scope_fail,
          "None/unknown/case-variant/non-string all rejected")

    train_ids = {r.row_id for r in kb.load_kb("train_kb")}
    test_ids = {r.row_id for r in rows} - {r.row_id for r in kb.load_kb("train_dev_kb")}
    cross = []
    for rid in sorted(test_ids):
        try:
            ctx.render_oracle_context("train_kb", rid)
            cross.append(rid)
        except ctx.ScopeError:
            pass
    check("cross_scope_row_request_rejected", not cross,
          f"all {len(test_ids)} test rows rejected under scope='train_kb'")
    check("in_scope_rows_still_render",
          ctx.render_oracle_context("train_kb", sorted(train_ids)[0]) != "",
          f"{len(train_ids)} train rows renderable under train_kb")

    # ---- Truncation scan ---------------------------------------------------
    hits = scan_for_truncation([
        ROOT / "finetune" / "context_renderer_v3.py",
        ROOT / "finetune" / "phase6_context_budget.py",
    ])
    check("no_silent_truncation_in_phase6_paths", not hits,
          "no truncation=True / max_length slicing / clipping"
          if not hits else f"{hits[:3]}")

    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    failed = [n for n, ok, _ in checks if not ok]
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    renderer_sha = sha256_file(ROOT / "finetune" / "context_renderer_v3.py")
    env = _env_provenance()
    _write_audit(hashes, db_sha, renderer_sha, env, cfg, tok, checks,
                 ctx_tokens, p_tokens, prompts, worst_rid, worst_prompt,
                 overhead, rows)

    print("\nAll Phase 6 gates passed.")
    print(f"  renderer {ctx.RENDERER_VERSION}  sha256 {renderer_sha}")
    print(f"  usable_context {cfg['usable_context']} = min("
          f"{cfg['model_configured_context']}, {cfg['evaluator_max_seq_length']}) · "
          f"max_new_tokens {cfg['max_new_tokens']} · max input {cfg['max_input_tokens']}")
    print(f"  worst context: row {worst_rid} {ctx_tokens[worst_rid]} tokens · "
          f"worst fixture prompt: row {worst_prompt[0]} {worst_prompt[3]} tokens")
    print(f"  margin: {cfg['max_input_tokens'] - worst_prompt[3]} tokens")
    return 0


def _env_provenance() -> dict:
    import transformers, tokenizers, huggingface_hub, jinja2  # noqa: E401
    return {
        "environment_path": ".venv-v3",
        "python": sys.version.split()[0],
        "transformers": transformers.__version__,
        "tokenizers": tokenizers.__version__,
        "huggingface_hub": huggingface_hub.__version__,
        "jinja2": jinja2.__version__,
    }


def _write_audit(hashes, db_sha, renderer_sha, env, cfg, tok, checks,
                 ctx_tokens, p_tokens, prompts, worst_rid, worst_prompt,
                 overhead, rows) -> None:
    spec = ctx.rendering_spec()
    by_row = {r.row_id: r for r in rows}
    L = ["# CONTEXT_BUDGET_v3\n",
         "Phase 6 — context renderer and token budget for **`base_ctx_oracle`**.\n",
         "`base_ctx_oracle` is an **oracle-context baseline** — a "
         "**retrieval-grounded factual upper bound**. The correct row is supplied by "
         "construction, so it measures grounded answering, not retrieval quality. It "
         "is never a RAG baseline, a retrieval-system benchmark, or a retriever "
         "benchmark. It applies to **factual probes only**; global structured "
         "questions compare against `base_sql` / `base_sql_5shot`, which are not "
         "implemented in this phase.\n",
         "## Frozen inputs\n", "```text",
         f"datasets_v3/gnem_v3.sqlite   {db_sha}",
         f"canonical_records_v3.jsonl   {hashes['canonical_records_v3.jsonl']}",
         f"company_split_groups_v3.csv  {hashes['company_split_groups_v3.csv']}",
         f"finetune/kb_v3.py            {hashes['kb_v3.py']}",
         "```\n",
         "## Renderer\n", "```text",
         f"version   {spec['renderer_version']}",
         f"file      finetune/context_renderer_v3.py",
         f"sha256    {renderer_sha}",
         "```\n",
         "The hash is computed **externally**, over the finalized file; a renderer "
         "cannot contain its own final hash.\n",
         "### Frozen rendering spec\n", "```json",
         json.dumps(spec, indent=2, ensure_ascii=False), "```\n",
         "Multi-valued fields are rendered **exactly once**, as child-fact sections. "
         "The Phase 4 allowlist contains them, so the scalar projection explicitly "
         "excludes them rather than rendering the same evidence twice.\n",
         "## Environment and tokenizer provenance\n", "```text",
         f"environment path   {env['environment_path']}  (repo-local, git-ignored, never committed)",
         f"python             {env['python']}",
         f"transformers       {env['transformers']}",
         f"tokenizers         {env['tokenizers']}",
         f"huggingface_hub    {env['huggingface_hub']}",
         f"jinja2             {env['jinja2']}",
         f"model/tokenizer    {TOKENIZER_ID}",
         f"revision           {TOKENIZER_REVISION}",
         f"tokenizer class    {type(tok).__name__}",
         f"tokenizer.json     {cfg['tokenizer_json_sha256']}",
         f"load mode          local_files_only=True",
         "```\n",
         "The v2 repository's `.venv-ft` is deliberately **not** used: that path is "
         "the frozen v2 reference repository, and `CLAUDE.md` §7 forbids a runtime "
         "dependency on it. No tokenizer or revision was substituted.\n",
         "## Context-budget equation\n", "```text",
         f"tokenizer advertised max_model_length   {tok.model_max_length}   INFORMATIONAL ONLY — not used",
         f"model configured context                {cfg['model_configured_context']}   config.json max_position_embeddings",
         f"evaluator max_seq_length                {cfg['evaluator_max_seq_length']}   frozen in Phase 6",
         "-" * 74,
         f"usable_context = min(model, evaluator) = {cfg['usable_context']}",
         f"max_new_tokens (reserved)              = {cfg['max_new_tokens']}",
         f"maximum input tokens                   = {cfg['max_input_tokens']}",
         "",
         f"every accepted prompt satisfies:  input + {cfg['max_new_tokens']} <= {cfg['usable_context']}",
         "```\n",
         "The tokenizer advertising "
         f"{tok.model_max_length} while the model supports "
         f"{cfg['model_configured_context']} is exactly the model/evaluator mismatch "
         "this assertion exists to surface. Generation tokens are reserved **before** "
         "a prompt is accepted; an over-budget prompt raises.\n",
         "## Prompt-family measurements\n",
         "| family | applicability | status | cases | min | median | p95 | max | +max_new | usable | margin | result |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    p95 = sorted(p_tokens)[int(0.95 * len(p_tokens))]
    L.append(f"| `base_ctx_oracle` | factual probes only | **implemented & measured** | "
             f"{len(p_tokens)} | {min(p_tokens)} | {int(statistics.median(p_tokens))} | "
             f"{p95} | {max(p_tokens)} | {max(p_tokens) + cfg['max_new_tokens']} | "
             f"{cfg['usable_context']} | "
             f"{cfg['usable_context'] - max(p_tokens) - cfg['max_new_tokens']} | PASS |")
    L += ["",
          "### What is validated now vs. later\n",
          "**Validated now:**\n",
          f"- all 205 rendered row contexts (structural renderer fixtures)",
          f"- chat-template + system + instruction overhead: **{overhead} tokens**",
          f"- worst-case renderer envelope (below)\n",
          "**To be revalidated later:** every actual factual probe/question when it is "
          "generated. Those questions do not exist yet, so Phase 6 makes **no claim** "
          "that they are validated. Later probe generation must run every real prompt "
          "through this same budget checker.\n",
          "```text",
          f"worst-case rendered context tokens   {ctx_tokens[worst_rid]}",
          f"fixed template/system overhead       {overhead}",
          f"maximum input allowance              {cfg['max_input_tokens']}",
          f"remaining future question allowance  "
          f"{cfg['max_input_tokens'] - ctx_tokens[worst_rid] - overhead}",
          "```\n",
          "## Worst-case rendered row\n",
          "The true maximum under the frozen KB — not a smaller, cleaner example. No "
          "gold answer is exposed.\n", "```text",
          f"largest rendered context   row_id {worst_rid}  "
          f"{by_row[worst_rid].company}",
          f"                           {ctx_tokens[worst_rid]} context tokens",
          f"largest fixture prompt     row_id {worst_prompt[0]}  {worst_prompt[1]}",
          f"                           {worst_prompt[3]} complete-prompt tokens",
          f"                           + {cfg['max_new_tokens']} reserved = "
          f"{worst_prompt[3] + cfg['max_new_tokens']}",
          f"remaining margin           "
          f"{cfg['usable_context'] - worst_prompt[3] - cfg['max_new_tokens']} tokens",
          "```\n",
          "## Oracle retrieval is not answer leakage\n",
          "The row is deliberately the correct one, so its raw evidence is **expected** "
          "to contain what a question asks for — `Employment: 500` is legitimate even "
          "when the eventual answer is `500`. Rejecting that would reject the baseline "
          "itself.\n",
          "What is forbidden is a separate **target/evaluation artifact**. The gate "
          "scans for annotation markers, not raw values:\n", "```text",
          "  " + ", ".join(FORBIDDEN_ARTIFACT_MARKERS[:8]),
          "  " + ", ".join(FORBIDDEN_ARTIFACT_MARKERS[8:]),
          "```\n",
          "Also absent: `split`, `split_group`, `certification_count`, latitude, "
          "longitude, graph metadata, and every Phase 5 physical scoped-view name. No "
          "outside knowledge enriches the context.\n",
          "## Truncation checks\n",
          "**No silent truncation anywhere.** Tokenization runs without truncation, and "
          "a source scan of the Phase 6 code paths rejects `truncation=True`, "
          "`max_length=` slicing, `.truncate(`, token-id slicing and long literal "
          "clipping. An over-budget prompt raises a gate failure; it is never trimmed, "
          "and no row or field is dropped to make it fit.\n",
          "Phase 7 separately owns removing the historical evaluator's "
          "`truncation=True, max_length=24576`; that migration is not performed here.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for name, ok, detail in checks:
        L.append(f"| `{name}` | {'PASS' if ok else 'FAIL'} | {detail} |")
    L.append("")
    OUT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, kb.IntegrityError) as exc:
        print(f"\nPHASE 6 GATE FAILURE: {exc}", file=sys.stderr)
        print("No artifact written. No rule weakened, no prompt truncated.",
              file=sys.stderr)
        raise SystemExit(1)
