"""Phase 10 -- build `train_A_cpt_v3.jsonl`.

README Phase 10: one canonical plain-text passage per row (the Phase 0 decision;
v2's three renderings are retired). Real factual fields only. No
`Certification Count` target; no sentence that turns a sentinel into a
substantive fact; held-out values omitted per the exposure ledger.

OMIT THE ITEM, NEVER TRUNCATE THE TRUTH. If a row's multi-valued field contains
a held-out value, the WHOLE field is omitted from that row's passage. Emitting
the remaining terms would teach an incomplete fact.

SENTINELS ARE NOT FACTS. `Not specified`, `Not applicable` and `None identified
after search` are never rendered as substantive claims -- the sentence is simply
not written. `None identified after search` means zero credential evidence in
this frozen dataset, not a real-world negative.

Train-side only: A is built from `train_kb` through the frozen Phase 4 contract.
The hard assert README demands is that no dev or test company appears anywhere in
the plain text, which carries no split metadata and is where a leak hides best.

Budget is reported in LM TOKENS (packing=True, full-sequence LM loss) and never
placed on the chat arms' completion-token axis.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H   # noqa: E402
import kb_v3 as KB       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "datasets_v3" / "train_A_cpt_v3.jsonl"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_A_CPT_v3.md"
GENERATOR_VERSION = "a_cpt_v3.0"

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


def omitted_fields(rec, held) -> set[str]:
    """Multi-valued fields the exposure policy removes from this row entirely."""
    out = set()
    for f in H.MULTIVALUED:
        ts = set(H.terms(getattr(rec, f), f))
        if ts & set(held[f]):
            out.add(f)
    return out


def render_passage(rec, held) -> tuple[str, set[str]]:
    """One canonical passage. Deterministic field order, fixed sentences."""
    drop = omitted_fields(rec, held)
    parts = [f"{rec.company} is a company in the Georgia new-energy mobility "
             f"supply chain."]
    for field, tmpl in SCALAR_SENTENCES:
        v = getattr(rec, field)
        if v is None or (isinstance(v, str) and v.strip() in SENTINELS):
            continue          # a sentinel is never rendered as a substantive fact
        parts.append(tmpl.format(company=rec.company, v=v))
    for field, tmpl in MULTI_SENTENCES:
        if field in drop:
            continue          # omit the whole field, never truncate the truth
        v = getattr(rec, field)
        if not v or v.strip() in SENTINELS:
            continue
        parts.append(tmpl.format(v=v))
    return " ".join(parts), drop


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

    # HARD ASSERT: no dev/test company anywhere in the plain text
    all_recs = KB.load_kb("full_kb")
    train_co = {r.company for r in recs}
    other_co = {r.company for r in all_recs} - train_co
    blob = "\n".join(texts)
    leaked = sorted(c for c in other_co if c in blob)
    check("zero_heldout_or_dev_companies_present", not leaked,
          f"0 of {len(other_co)} dev/test companies appear in the plain text"
          if not leaked else f"LEAKED: {leaked[:5]}")

    # sentinels never become substantive facts
    sent_hits = sorted(s for s in SENTINELS if s in blob)
    check("no_sentinel_rendered_as_fact", not sent_hits,
          "Not specified / Not applicable / None identified after search absent"
          if not sent_hits else f"{sent_hits}")

    check("no_certification_count_target", "ertification count" not in blob.lower()
          and "certification_count" not in blob,
          "Certification Count never rendered")

    # exposure ledger satisfied, on the FINAL rendered strings
    rep = H.scan_strings(texts, reg)
    H.assert_zero_exposure(rep, "A")
    check("exposure_count_zero", rep["total_exposures"] == 0,
          f"0 held-out literals across {rep['strings_scanned']} rendered passages")

    # omission accounting must match the registry's predicted collateral
    for f in H.MULTIVALUED:
        exp = reg["value_holdouts"][f]["train_rows_lost"]
        check(f"omitted_fields_match_registry_{f}", dropped[f] == exp,
              f"{dropped[f]} rows omit {f} == registry train_rows_lost {exp}")

    cov = {f: 100.0 * (len(recs) - dropped[f]) / len(recs) for f in H.MULTIVALUED}
    check("coverage_floor_holds",
          all(cov[f] >= H.COVERAGE_FLOOR_PCT or f == "certifications"
              for f in H.MULTIVALUED),
          " · ".join(f"{f} {cov[f]:.1f}%" for f in cov))

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
    tok = _tokens(texts)
    _audit(reg, rows, dropped, cov, checks, sha, tok, rep)
    _update_ledger(reg, sha, rep)

    print(f"\nAll Phase 10 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  passages {len(rows)} · LM tokens {tok['total'] if tok else 'n/a'} "
          f"· chars {sum(len(t) for t in texts)}")
    return 0


def _tokens(texts):
    """LM-token budget with the real Qwen tokenizer, if available."""
    try:
        from transformers import AutoTokenizer
    except ImportError:
        return None
    tok = AutoTokenizer.from_pretrained(
        "Qwen/Qwen2.5-14B-Instruct",
        revision="cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8", local_files_only=True)
    lens = [len(tok(t, add_special_tokens=False)["input_ids"]) for t in texts]
    lens.sort()
    return {"total": sum(lens), "min": lens[0], "median": lens[len(lens) // 2],
            "p95": lens[int(0.95 * len(lens))], "max": lens[-1],
            "tokenizer": "Qwen/Qwen2.5-14B-Instruct@cf98f3b3"}


def _update_ledger(reg, sha, rep):
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    led["arms"]["A"] = {"scanned": True, "exposure_count": rep["total_exposures"],
                        "artifact": "datasets_v3/train_A_cpt_v3.jsonl",
                        "sha256": sha, "strings_scanned": rep["strings_scanned"],
                        "phase": 10}
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _audit(reg, rows, dropped, cov, checks, sha, tok, rep):
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
         "## Budget — LM tokens\n"]
    if tok:
        L += ["```text",
              f"tokenizer     {tok['tokenizer']}",
              f"total LM tokens   {tok['total']}",
              f"min / median / p95 / max   {tok['min']} / {tok['median']} / "
              f"{tok['p95']} / {tok['max']}", "```\n",
              "A trains under `packing=True` with **full-sequence LM loss**, a different "
              "objective from the chat variants' `assistant_only_loss=True`. This budget "
              "is reported in LM tokens and is **never** placed on the "
              "completion-token axis.\n"]
    else:
        L += ["Tokenizer unavailable in this interpreter; run under `.venv-v3` for the "
              "LM-token budget.\n"]
    L += ["## Holdout omissions (omit the item, never truncate the truth)\n",
          "| attribute | rows omitting the field | remaining coverage | registry predicted |",
          "|---|--:|--:|--:|"]
    for f in H.MULTIVALUED:
        L.append(f"| `{f}` | {dropped[f]} | {cov[f]:.1f}% | "
                 f"{reg['value_holdouts'][f]['train_rows_lost']} |")
    L += ["",
          "A row whose multi-valued field contains a held-out value has that **whole "
          "field** omitted from its passage. Emitting the surviving terms would teach "
          "an incomplete fact.\n",
          "## Exposure\n", "```text",
          f"strings scanned   {rep['strings_scanned']}   (final rendered passages)",
          f"exposure_count    {rep['total_exposures']}",
          "```\n",
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
