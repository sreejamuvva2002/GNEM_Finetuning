"""Phase 15 -- build `train_BC_facts_answers_v3.jsonl`.

README Phase 15: "Deterministic union of the frozen B and C files. Never
regenerate variants inside BC." So this generator does exactly one thing: read
the two frozen files byte-for-byte and concatenate them, B then C, in a fixed
documented order. It computes nothing, renders nothing, and touches no KB
scope or holdout registry -- there is no new model-visible content here that
wasn't already scanned and frozen at Phase 11/13.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
B_PATH = ROOT / "datasets_v3" / "train_B_facts_v3.jsonl"
C_PATH = ROOT / "datasets_v3" / "train_C_answers_v3.jsonl"
OUT = ROOT / "datasets_v3" / "train_BC_facts_answers_v3.jsonl"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_BC_v3.md"
GENERATOR_VERSION = "bc_v3.0"


class Gate(Exception):
    """A Phase 15 invariant failed. No artifact is written."""


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    b_lines = B_PATH.read_text(encoding="utf-8").splitlines()
    c_lines = C_PATH.read_text(encoding="utf-8").splitlines()
    b_items = [json.loads(l) for l in b_lines]
    c_items = [json.loads(l) for l in c_lines]
    return b_lines, c_lines, b_items, c_items


def main() -> int:
    reg = H.load_registry()
    b_lines, c_lines, b_items, c_items = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    # Correction (post-approval audit, confirmed): the original ledger update
    # copied forward B/C's PREVIOUSLY recorded exposure_count/strings_scanned
    # without verifying those source files hadn't drifted since Phase 11/13,
    # and without re-scanning anything itself -- a stale or hand-edited B/C
    # would silently certify as exposure_count 0. Fixed two ways: (1) verify
    # current B/C sha256 against the ledger's own recorded values before
    # trusting them at all; (2) actually re-scan every rendered string in
    # this file (not merely inherit a prior verdict), same rigor as every
    # other arm.
    led = json.loads((ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json")
                     .read_text(encoding="utf-8"))
    b_sha_now, c_sha_now = sha256_file(B_PATH), sha256_file(C_PATH)
    check("source_hashes_match_ledger",
          b_sha_now == led["arms"]["B"]["sha256"]
          and c_sha_now == led["arms"]["C"]["sha256"],
          f"B {b_sha_now[:12]}.. == ledger {led['arms']['B']['sha256'][:12]}.. "
          f"and C {c_sha_now[:12]}.. == ledger {led['arms']['C']['sha256'][:12]}.. "
          f"-- refusing to inherit a prior exposure verdict for drifted source")

    check("b_and_c_frozen_and_nonempty", len(b_items) > 0 and len(c_items) > 0,
          f"B: {len(b_items)} items · C: {len(c_items)} items")

    ids = [i["example_id"] for i in b_items] + [i["example_id"] for i in c_items]
    check("no_example_id_collision", len(ids) == len(set(ids)),
          f"{len(set(ids))} unique ids across {len(ids)} total (B and C use "
          f"disjoint 'B_'/'C_' prefixes by construction)")

    check("no_variant_regeneration",
          all(l1 == l2 for l1, l2 in
             zip(sorted(b_lines), sorted(json.dumps(i, ensure_ascii=False,
                                                    sort_keys=True) for i in b_items))),
          "every B line, re-serialized identically, matches the frozen file "
          "byte-for-byte -- nothing was regenerated, only concatenated")

    render_texts = []
    for i in b_items + c_items:
        render_texts.append(i["messages"][0]["content"])
        render_texts.append(i["messages"][1]["content"])
        render_texts.append(i["messages"][2]["content"])
    rep = H.scan_strings(render_texts, reg)
    H.assert_value_scan_verified(rep)
    check("exposure_count_zero_rescanned", rep["total_exposures"] == 0,
          f"0 held-out literals across {rep['strings_scanned']} strings, "
          f"RE-SCANNED here (not inherited from B/C's ledger entries)")

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for line in b_lines:
            fh.write(line + "\n")
        for line in c_lines:
            fh.write(line + "\n")
    sha = sha256_file(OUT)

    _update_ledger(sha, rep)
    _audit(b_items, c_items, checks, sha, rep)

    print(f"\nAll Phase 15 gates passed.")
    print(f"  {OUT.relative_to(ROOT)}  sha256 {sha}")
    print(f"  items {len(b_items) + len(c_items)} (B {len(b_items)} + C {len(c_items)})")
    return 0


def _update_ledger(sha, rep):
    """Correction: this now records a REAL re-scan of BC's own rendered
    strings (rep, computed in main() via H.scan_strings), not a copy-forward
    of B/C's prior counts -- see the source_hashes_match_ledger and
    exposure_count_zero_rescanned checks in main()."""
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    led["arms"]["BC"] = {
        "scanned": True, "exposure_count": rep["total_exposures"],
        "artifact": "datasets_v3/train_BC_facts_answers_v3.jsonl",
        "sha256": sha, "strings_scanned": rep["strings_scanned"],
        "phase": 15,
        "note": "re-scanned directly against the holdout registry, not "
               "inherited from B/C's ledger entries (post-approval audit "
               "correction)",
    }
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _audit(b_items, c_items, checks, sha, rep):
    L = ["# DATASET_BC_v3\n",
         "Phase 15 — `train_BC_facts_answers_v3.jsonl`, the deterministic "
         "union of the frozen B and C files. Never a regenerated variant.\n",
         "## Provenance\n", "```text",
         f"artifact          datasets_v3/train_BC_facts_answers_v3.jsonl",
         f"sha256            {sha}",
         f"generator         {GENERATOR_VERSION}",
         f"source B          datasets_v3/train_B_facts_v3.jsonl "
         f"sha256 {sha256_file(B_PATH)}",
         f"source C          datasets_v3/train_C_answers_v3.jsonl "
         f"sha256 {sha256_file(C_PATH)}",
         "```\n",
         f"## Composition\n",
         f"B: {len(b_items)} items (order 1-{len(b_items)}) + "
         f"C: {len(c_items)} items (order {len(b_items)+1}-"
         f"{len(b_items)+len(c_items)}) = {len(b_items)+len(c_items)} total, "
         f"B first then C, fixed order.\n",
         "## Exposure (re-scanned, not inherited)\n",
         "Correction (post-approval audit): an earlier version of this "
         "generator copied forward B/C's previously recorded "
         "exposure_count/strings_scanned without verifying those source "
         "files hadn't drifted, and without scanning anything itself. This "
         "build verifies current B/C sha256 against the ledger's recorded "
         "values first, then re-scans every rendered string in the "
         "concatenated file directly.\n",
         "```text",
         f"strings scanned   {rep['strings_scanned']}   (system prompt + "
         f"question + answer, every B and C item)",
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
    except Gate as e:
        print(f"\nPHASE 15 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
