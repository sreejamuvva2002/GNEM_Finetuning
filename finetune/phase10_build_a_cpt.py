"""Phase 10: complete, source-qualified training-record passages under A-002.

Every eligible record includes all source attributes except internal Certification
Count. Missingness is explicit evidence of a source limitation. Repeated records
remain attributable observations, not presumed separate facilities. No deliberate
value withholding or silent list truncation is permitted. Training uses train_kb;
leak_audit_v3 separately verifies held-out company exclusion.

LM token budgets are distinct from the chat arms' assistant-label budgets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H       # noqa: E402
import kb_v3 as KB            # noqa: E402
import leak_audit_v3 as LA    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "datasets_v3" / "train_A_cpt_v3.jsonl"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_A_CPT_v3.md"
GENERATOR_VERSION = "a_cpt_v3.2_A002"

TOKENIZER_ID = "Qwen/Qwen2.5-14B-Instruct"
TOKENIZER_REVISION = "cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8"
EXPECTED_TOKENIZER_JSON_SHA = (
    "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539")

SENTINELS = {"Not specified", "Not applicable", H.CERT_SENTINEL}

# Scalar fields rendered as prose. `certification_count` is deliberately absent:
# README forbids it as a target, and Phase 5 already excludes it from the
# model-facing schema.
SCALAR_SENTENCES = [
    ("category", "{company} is classified in the {v} category."),
    ("industry_group", "Its industry group is {v}."),
    ("location", "It is located at {v}."),
    ("address", "Its address is {v}."),
    ("primary_facility_type", "The site is a {v}."),
    ("ev_supply_chain_role", "Its EV supply chain role is {v}."),
    ("primary_oems", "Its primary OEMs are recorded as {v}."),
    ("supplier_or_affiliation_type", "Its supplier or affiliation type is {v}."),
    ("employment", "The dataset records employment of {v}."),
    ("product_or_service", "Its product or service is {v}."),
    ("ev_battery_relevant", "EV or battery relevance is recorded as {v}."),
    ("classification_method", "The classification method is {v}."),
]
MULTI_SENTENCES = [
    ("processes", "Recorded processes are {v}."),
    ("services", "Recorded services are {v}."),
    ("certifications", "Recorded certifications are {v}."),
]


class Gate(Exception):
    """A Phase 10 invariant failed. No artifact is written."""


def render_passage(rec, held) -> tuple[str, set[str]]:
    """One canonical passage. Deterministic field order, fixed sentences."""
    if any(held.values()):
        raise Gate("A-002 forbids deliberate value omissions")
    fields = ("company",) + tuple(f for f, _ in SCALAR_SENTENCES + MULTI_SENTENCES)
    parts = [f"Source record {rec.row_id} in the GNEM dataset. These are recorded observations; "
             "repeated company records may disagree and do not establish separate facilities."]
    for field in fields:
        value = getattr(rec, field)
        label = field.replace("_", " ")
        if value is None or str(value).strip() in SENTINELS:
            parts.append(f"Recorded {label}: {value}. This indicates missing or inapplicable "
                         "source evidence, not proof of real-world absence.")
        else:
            parts.append(f"Recorded {label}: {value}.")
    parts.append("Employment scope and date are not established here; recorded certifications "
                 "do not independently establish current validity or customer qualification.")
    return " ".join(parts), set()


def build():
    reg = H.load_registry()
    held = H.held_out_values(reg)
    recs = KB.load_kb("train_kb")          # train-side only, Phase 4 contract
    rows, dropped = [], {f: 0 for f in H.MULTIVALUED}
    for rec in sorted(recs, key=lambda r: r.row_id):
        text, drop = render_passage(rec, held)
        for f in drop:
            dropped[f] += 1
        rows.append({"example_id": f"A_{rec.row_id:04d}", "row_id": rec.row_id,
                     "company": rec.company, "text": text,
                     "omitted_fields": sorted(drop)})
    return reg, held, recs, rows, dropped


def load_real_tokenizer():
    """The real Qwen tokenizer at the pinned revision, or a gate failure.

    No estimator, no substitute model's tokenizer -- finetune/
    phase6_context_budget.py precedent, reused verbatim here.
    """
    try:
        from transformers import AutoTokenizer
    except ImportError as e:
        raise Gate(
            "transformers is unavailable, so the real Qwen tokenizer cannot be "
            f"established. Phase 10 does NOT substitute an estimator. ({e})")
    tok_json = None
    try:
        from huggingface_hub import hf_hub_download
        tok_json = Path(hf_hub_download(
            TOKENIZER_ID, "tokenizer.json", revision=TOKENIZER_REVISION,
            local_files_only=True))
    except Exception as e:  # noqa: BLE001
        raise Gate(f"could not locate cached tokenizer.json for {TOKENIZER_ID} "
                   f"@ {TOKENIZER_REVISION}: {type(e).__name__}: {e}")
    got_sha = H.sha256_file(tok_json)
    if got_sha != EXPECTED_TOKENIZER_JSON_SHA:
        raise Gate(
            f"tokenizer.json hash mismatch -- expected "
            f"{EXPECTED_TOKENIZER_JSON_SHA}, got {got_sha}. Refusing to use a "
            f"drifted tokenizer for the LM-token budget.")
    try:
        tok = AutoTokenizer.from_pretrained(
            TOKENIZER_ID, revision=TOKENIZER_REVISION, local_files_only=True)
    except Exception as e:  # noqa: BLE001
        raise Gate(f"could not load {TOKENIZER_ID} @ {TOKENIZER_REVISION} "
                   f"from the local cache: {type(e).__name__}: {e}")
    if not tok.chat_template:
        raise Gate("tokenizer has no chat template")
    return tok, got_sha


def lm_token_counts(tok, texts: list[str]) -> dict:
    """A uses manual stream chunking with full-sequence LM loss -- plain
    tokenization of the passage text, no chat template, no special tokens
    reserved for a turn structure that doesn't apply here."""
    lens = [len(tok(t, add_special_tokens=False)["input_ids"]) for t in texts]
    lens.sort()
    return {"total": sum(lens), "min": lens[0], "median": lens[len(lens) // 2],
            "p95": lens[int(0.95 * len(lens))], "max": lens[-1]}


def main() -> int:
    reg, held, recs, rows, dropped = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    check("registry_frozen_before_generation", bool(reg.get("frozen_date")),
          f"HOLDOUT_REGISTRY_v3 {reg['policy_version']} dated {reg['frozen_date']}")
    check("one_passage_per_row", len(rows) == len(recs) == 148,
          f"{len(rows)} passages for {len(recs)} train rows (one each)")
    check("unique_example_ids", len({r["example_id"] for r in rows}) == len(rows),
          f"{len(rows)} unique ids")

    texts = [r["text"] for r in rows]
    dupes = len(texts) - len(set(texts))
    check("no_duplicate_passages", dupes == 0, f"{dupes} duplicate passages")

    # HARD ASSERT: no dev/test company anywhere in the plain text.
    leaked = LA.companies_leaked_in(texts)
    other_co = LA.non_train_companies()
    check("zero_heldout_or_dev_companies_present", not leaked,
          f"0 of {len(other_co)} dev/test companies appear in the plain text"
          if not leaked else f"LEAKED: {leaked[:5]}")

    # Phase 4 static check, re-run against THIS generator's own source, as
    # required for every later training-data phase.
    static_rep = KB.static_check_no_training_generator_reaches_full_kb(
        [Path(__file__)])
    check("static_check_generator_never_reaches_full_kb",
          static_rep["scanned_count"] > 0 and static_rep["violation_count"] == 0,
          static_rep["proves"])

    # sentinels never become substantive facts
    blob = "\n".join(texts)
    sent_hits = sorted(s for s in SENTINELS if s in blob)
    check("sentinel_evidence_qualified", all("not proof of real-world absence" in t for t in texts if any(v in t for v in SENTINELS)),
          "Not specified / Not applicable / None identified after search absent"
          if not sent_hits else f"{sent_hits}")

    check("no_certification_count_target", "ertification count" not in blob.lower()
          and "certification_count" not in blob,
          "Certification Count never rendered")

    # exposure ledger satisfied, on the FINAL rendered strings
    rep = H.scan_strings(texts, reg)
    H.assert_value_scan_verified(rep)
    check("exposure_count_zero", rep["total_exposures"] == 0,
          f"0 held-out literals across {rep['strings_scanned']} rendered passages")

    # omission accounting must match the registry's predicted collateral
    for f in H.MULTIVALUED:
        exp = reg["value_holdouts"][f]["train_rows_lost"]
        check(f"omitted_fields_match_registry_{f}", dropped[f] == exp,
              f"{dropped[f]} rows omit {f} == registry train_rows_lost {exp}")

    # Denominator is rows that actually CARRY the attribute (H.attribute_totals),
    # not all 148 train rows -- certifications has sentinel-only rows that never
    # carried the attribute to begin with. This is the same denominator the
    # registry itself used at Phase 9; recomputed independently here rather than
    # trusted, then cross-checked against the frozen figure below.
    h_recs, h_split = H.load_kb()
    attr_totals, _ = H.attribute_totals(h_recs, h_split)
    cov = {f: 100.0 * (attr_totals[f] - dropped[f]) / attr_totals[f]
          for f in H.MULTIVALUED}
    check("coverage_floor_holds",
          all(cov[f] >= H.COVERAGE_FLOOR_PCT for f in H.MULTIVALUED),
          " · ".join(f"{f} {cov[f]:.1f}%" for f in cov))
    for f in H.MULTIVALUED:
        exp_cov = reg["value_holdouts"][f]["remaining_attribute_coverage_rows_pct"]
        check(f"coverage_matches_registry_prediction_{f}",
              abs(cov[f] - exp_cov) < 0.01,
              f"{cov[f]:.2f}% recomputed == {exp_cov}% frozen at Phase 9")

    # LM-token budget -- real pinned tokenizer, no estimator (gate failure if
    # unavailable, per finetune/phase6_context_budget.py precedent).
    tok, tok_json_sha = load_real_tokenizer()
    check("real_tokenizer_loaded_at_pinned_revision", True,
          f"{TOKENIZER_ID} @ {TOKENIZER_REVISION} (Qwen2Tokenizer, "
          f"local_files_only=True)")
    check("tokenizer_json_sha_matches_expected",
          tok_json_sha == EXPECTED_TOKENIZER_JSON_SHA, tok_json_sha)
    tokinfo = lm_token_counts(tok, texts)

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    sha = H.sha256_file(OUT)
    _audit(reg, rows, dropped, cov, checks, sha, tokinfo, rep, static_rep)
    _update_ledger(sha, rep)

    print(f"\nAll Phase 10 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  passages {len(rows)} · LM tokens {tokinfo['total']} "
          f"· chars {sum(len(t) for t in texts)}")
    return 0


def _update_ledger(sha, rep):
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    led["arms"]["A"] = {"scanned": True, "exposure_count": rep["total_exposures"],
                        "artifact": "datasets_v3/train_A_cpt_v3.jsonl",
                        "sha256": sha, "strings_scanned": rep["strings_scanned"],
                        "phase": 10}
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _audit(reg, rows, dropped, cov, checks, sha, tok, rep, static_rep):
    L = ["# DATASET_A_CPT_v3\n",
         "Phase 10 — `train_A_cpt_v3.jsonl`, continued pre-training passages.\n",
         "## Provenance\n", "```text",
         f"artifact          datasets_v3/train_A_cpt_v3.jsonl",
         f"sha256            {sha}",
         f"generator         {GENERATOR_VERSION}",
         f"scope             train_kb (Phase 4 contract)",
         f"holdout registry  {reg['policy_version']} frozen {reg['frozen_date']}",
         "```\n",
         "## Composition\n", "```text",
         f"passages                {len(rows)}   (one canonical passage per train row)",
         f"renderings per row      1             (Phase 0 decision; v2's three are retired)",
         "```\n",
         "**Known interpretation limit (README Phase 10).** A one-passage A has weaker "
         "phrasing diversity than v2's three renderings, so it is *expected* to "
         "underperform on `probe_fact_paraphrase_v3` relative to a three-rendering A. "
         "That is a design consequence, never a finding about CPT.\n",
         "## Budget — LM tokens\n", "```text",
         f"tokenizer     {TOKENIZER_ID} @ {TOKENIZER_REVISION[:12]}",
         f"passage tokens before EOS   {tok['total']}",
         f"min / median / p95 / max   {tok['min']} / {tok['median']} / "
         f"{tok['p95']} / {tok['max']}", "```\n",
         f"Trainer appends one EOS per passage: {tok['total'] + len(rows)} input tokens, maximum passage length {tok['max'] + 1}. Manual 1,024-token stream chunking is used with **full-sequence LM loss**, a different "
         "objective from the chat variants' `assistant_only_loss=True`. This budget "
         "is reported in LM tokens and is **never** placed on the "
         "completion-token axis.\n",
         "## Holdout omissions (omit the item, never truncate the truth)\n",
         "| attribute | rows omitting the field | remaining coverage | registry predicted |",
         "|---|--:|--:|--:|"]
    for f in H.MULTIVALUED:
        L.append(f"| `{f}` | {dropped[f]} | {cov[f]:.1f}% | "
                 f"{reg['value_holdouts'][f]['train_rows_lost']} |")
    L += ["",
          "A-002 removes deliberate value exclusions. Every training-record field is "
          "rendered, including source-qualified missingness. Complete lists are retained.\n",
          "## Exposure\n", "```text",
          f"strings scanned   {rep['strings_scanned']}   (final rendered passages)",
          f"exposure_count    {rep['total_exposures']}",
          "```\n",
          "## Phase 4 static check (re-run for this generator)\n", "```text",
          f"scanned            {static_rep['scanned_files']}",
          f"violation_count    {static_rep['violation_count']}",
          f"proves             {static_rep['proves']}",
          "```\n",
          "Full-KB access needed for the dev/test-company leak check (below) lives in "
          "`finetune/leak_audit_v3.py`, a separate validation-only module deliberately "
          "excluded from this scan -- it is never a training-target source.\n",
          "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        L.append(f"| `{n}` | {'PASS' if ok else 'FAIL'} | {d} |")
    L.append("")
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, H.HoldoutError) as e:
        print(f"\nPHASE 10 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
