"""Phase 16 -- BD datasets and budget manifests.

README Phase 16 produces four things:

  train_BD_facts_sql_v3.jsonl   frozen B + D, natural recipe (README-named)
  BD_controlled                 B and D balanced ~50/50 by SUPERVISED
                                 COMPLETION tokens (assistant_only_loss=True,
                                 so only the assistant turn's tokens carry
                                 gradient -- README:17,559-561)
  D_repeat_budgetmatched         pure D, repeated (cycled), matched to
                                 BD_controlled's TOTAL supervised-token budget
  BD_COMPOSITION_v3.md          B attribute mix + D operation/join_arity mix,
                                 for BD_controlled AND BD_full, plus standalone
                                 B and D

BD_full IS train_BD_facts_sql_v3.jsonl: "the full eligible v3 recipe -- every
B and D example surviving the split, holdout and exposure-ledger exclusions"
(README:569-572). Both B and D are already that exact eligible set by
construction (Phases 11/14), so BD_full is their deterministic union, exactly
like Phase 15's BC -- no new exclusion logic here.

TOKEN COUNTING uses the real pinned Qwen tokenizer (finetune/
phase10_build_a_cpt.load_real_tokenizer, reused verbatim -- same hash-verified
loader, no estimator, no substitution). Supervised completion tokens =
len(tokenize(full chat text)) - len(tokenize(prompt-only text with
add_generation_prompt=True)) -- the standard way to isolate what an
assistant-only-loss mask actually trains on.

WHAT'S FROZEN vs WHAT'S NOT. README asks for "optimizer steps, effective
passes" in the report. Those require a batch size and epoch count, which are
Phase 24 dev-tuned hyperparameters this repository has not yet chosen (README
Phase 24: checkpoint selection, learning rate, epochs, LoRA rank are ALL dev
decisions). Fabricating a batch size here to produce a step count would be
exactly the kind of unstated-parameter invention CLAUDE.md forbids. This
report gives the formula and the inputs (total tokens, example counts) and
explicitly defers the numeric step/pass count to Phase 24 -- a documented
scope boundary, not an omission.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import holdout_v3 as H                                    # noqa: E402
from phase10_build_a_cpt import (EXPECTED_TOKENIZER_JSON_SHA,  # noqa: E402
                                 load_real_tokenizer)

ROOT = Path(__file__).resolve().parent.parent
B_PATH = ROOT / "datasets_v3" / "train_B_facts_v3.jsonl"
D_PATH = ROOT / "datasets_v3" / "train_D_sql_v3.jsonl"
OUT_FULL = ROOT / "datasets_v3" / "train_BD_facts_sql_v3.jsonl"
OUT_CONTROLLED = ROOT / "datasets_v3" / "train_BD_controlled_v3.jsonl"
OUT_REPEAT = ROOT / "datasets_v3" / "train_D_repeat_budgetmatched_v3.jsonl"
OUT_MANIFEST = ROOT / "datasets_v3" / "BD_SAMPLING_MANIFEST_v3.json"
OUT_COMPOSITION = ROOT / "validation_v3" / "BD_COMPOSITION_v3.md"
OUT_AUDIT = ROOT / "validation_v3" / "DATASET_BD_v3.md"
GENERATOR_VERSION = "bd_v3.0"


class Gate(Exception):
    """A Phase 16 invariant failed. No artifact is written."""


def completion_and_total_tokens(tok, messages: list[dict]) -> tuple[int, int]:
    full_text = tok.apply_chat_template(messages, tokenize=False,
                                        add_generation_prompt=False)
    prompt_text = tok.apply_chat_template(messages[:-1], tokenize=False,
                                          add_generation_prompt=True)
    full_n = len(tok(full_text, add_special_tokens=False)["input_ids"])
    prompt_n = len(tok(prompt_text, add_special_tokens=False)["input_ids"])
    return full_n - prompt_n, full_n


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def with_tokens(tok, items: list[dict]) -> list[dict]:
    out = []
    for i in items:
        comp, total = completion_and_total_tokens(tok, i["messages"])
        j = dict(i)
        j["_completion_tokens"] = comp
        j["_total_tokens"] = total
        out.append(j)
    return out


def greedy_fill(items_sorted: list[dict], budget: int) -> list[dict]:
    """Deterministic prefix fill: add items (in the given fixed order) until
    the running completion-token total would first meet or exceed `budget`,
    then keep whichever of {stop just before, stop just after} lands closer
    to `budget` -- a documented, reproducible sampling rule, not a random
    draw (README asks for '~50/50', not an exact split)."""
    running, taken = 0, []
    for it in items_sorted:
        if running >= budget:
            break
        taken.append(it)
        running += it["_completion_tokens"]
    if len(taken) > 1 and abs(running - budget) > abs(
            (running - taken[-1]["_completion_tokens"]) - budget):
        taken = taken[:-1]
    return taken


def repeat_to_budget(items_sorted: list[dict], budget: int) -> list[dict]:
    """Cycle through `items_sorted` from the start, repeating, until the
    cumulative completion-token total first meets or exceeds `budget`. Each
    repeated copy keeps its source content and task_id (traceable) but gets a
    distinct example_id (repeat cycle suffix) so the file has no duplicate
    ids despite duplicate content -- duplicate CONTENT is the entire point
    (README:566-567: 'the same SQL information repeated to match exposure')."""
    out, running, cycle, i = [], 0, 0, 0
    n = len(items_sorted)
    if n == 0:
        raise Gate("repeat_to_budget: empty source set")
    while running < budget:
        src = items_sorted[i % n]
        if i > 0 and i % n == 0:
            cycle += 1
        copy = dict(src)
        copy["example_id"] = f"{src['example_id']}__rep{i // n}"
        out.append(copy)
        running += src["_completion_tokens"]
        i += 1
    return out


def build():
    reg = H.load_registry()
    tok, tok_sha = load_real_tokenizer()

    b_raw, d_raw = load(B_PATH), load(D_PATH)
    b = with_tokens(tok, b_raw)
    d = with_tokens(tok, d_raw)

    b_sorted = sorted(b, key=lambda i: i["example_id"])
    d_sorted = sorted(d, key=lambda i: i["example_id"])

    b_total_comp = sum(i["_completion_tokens"] for i in b)
    d_total_comp = sum(i["_completion_tokens"] for i in d)

    # BD_full: deterministic union, exactly like Phase 15's BC.
    bd_full = b_sorted + d_sorted

    # BD_controlled: ~50/50 by supervised completion tokens. The smaller
    # standalone total is the natural anchor (using it in full, since
    # upsampling B would mean repeating FACTUAL QA -- not what README asks
    # for; only D gets a repeat variant, by name, in this phase).
    if b_total_comp <= d_total_comp:
        anchor, anchor_total, other_sorted = b_sorted, b_total_comp, d_sorted
        anchor_name, other_name = "B", "D"
    else:
        anchor, anchor_total, other_sorted = d_sorted, d_total_comp, b_sorted
        anchor_name, other_name = "D", "B"
    other_sample = greedy_fill(other_sorted, anchor_total)
    bd_controlled = (anchor + other_sample if anchor_name == "B"
                     else other_sample + anchor)
    controlled_total = anchor_total + sum(i["_completion_tokens"]
                                          for i in other_sample)

    # D_repeat_budgetmatched: pure D, cycled to BD_controlled's total budget.
    d_repeat = repeat_to_budget(d_sorted, controlled_total)

    return {
        "reg": reg, "tok_sha": tok_sha,
        "b": b, "d": d, "b_sorted": b_sorted, "d_sorted": d_sorted,
        "b_total_comp": b_total_comp, "d_total_comp": d_total_comp,
        "bd_full": bd_full,
        "bd_controlled": bd_controlled, "controlled_total": controlled_total,
        "anchor_name": anchor_name, "other_name": other_name,
        "other_sample": other_sample,
        "d_repeat": d_repeat,
    }


def strip_internal(items: list[dict]) -> list[dict]:
    return [{k: v for k, v in i.items()
            if k not in ("_completion_tokens", "_total_tokens")} for i in items]


def write_jsonl(path: Path, items: list[dict]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for i in strip_internal(items):
            fh.write(json.dumps(i, ensure_ascii=False, sort_keys=True) + "\n")
    return H.sha256_file(path)


def attribute_mix(items: list[dict]) -> dict[str, float]:
    tot = sum(i["_completion_tokens"] for i in items) or 1
    by = defaultdict(int)
    for i in items:
        by[i["attribute"]] += i["_completion_tokens"]
    return {k: round(100.0 * v / tot, 2) for k, v in sorted(by.items())}


def d_family_mix(items: list[dict]) -> dict[str, float]:
    tot = sum(i["_completion_tokens"] for i in items) or 1
    by = defaultdict(int)
    for i in items:
        by[i["operation_family"]] += i["_completion_tokens"]
    return {k: round(100.0 * v / tot, 2) for k, v in sorted(by.items())}


def d_arity_mix(items: list[dict]) -> dict[str, float]:
    tot = sum(i["_completion_tokens"] for i in items) or 1
    by = defaultdict(int)
    for i in items:
        by[str(i["join_arity"])] += i["_completion_tokens"]
    return {k: round(100.0 * v / tot, 2) for k, v in sorted(by.items())}


def main() -> int:
    st = build()
    checks: list[tuple[str, bool, str]] = []

    def check(n, ok, d):
        checks.append((n, bool(ok), d))

    check("registry_frozen_before_generation", bool(st["reg"].get("frozen_date")),
          f"HOLDOUT_REGISTRY_v3 {st['reg']['policy_version']}")

    b_ids = {i["example_id"] for i in st["b"]}
    d_ids = {i["example_id"] for i in st["d"]}
    full_ids = {i["example_id"] for i in st["bd_full"]}
    check("bd_full_is_exact_union_of_b_and_d", full_ids == b_ids | d_ids
          and len(st["bd_full"]) == len(st["b"]) + len(st["d"]),
          f"{len(st['bd_full'])} items = {len(st['b'])} B + {len(st['d'])} D, "
          f"no additions or omissions")

    controlled_b = [i for i in st["bd_controlled"] if i["example_id"] in b_ids]
    controlled_d = [i for i in st["bd_controlled"] if i["example_id"] in d_ids]
    check("bd_controlled_items_are_genuine_b_or_d",
          len(controlled_b) + len(controlled_d) == len(st["bd_controlled"]),
          f"{len(controlled_b)} from B + {len(controlled_d)} from D = "
          f"{len(st['bd_controlled'])}, no fabricated items")

    b_ctrl_tok = sum(i["_completion_tokens"] for i in controlled_b)
    d_ctrl_tok = sum(i["_completion_tokens"] for i in controlled_d)
    balance_ratio = min(b_ctrl_tok, d_ctrl_tok) / max(b_ctrl_tok, d_ctrl_tok)
    check("bd_controlled_approximately_50_50", balance_ratio >= 0.95,
          f"B {b_ctrl_tok} / D {d_ctrl_tok} supervised completion tokens "
          f"(ratio {balance_ratio:.3f}, target >= 0.95 for '~50/50')")

    check("bd_controlled_uses_full_anchor_arm",
          (len(controlled_b) == len(st["b"]) if st["anchor_name"] == "B"
           else len(controlled_d) == len(st["d"])),
          f"the smaller-total arm ({st['anchor_name']}) is used in full "
          f"({len(st['b']) if st['anchor_name']=='B' else len(st['d'])} items), "
          f"never subsampled downward")

    d_repeat_ids_src = {i["example_id"].split("__rep")[0] for i in st["d_repeat"]}
    check("d_repeat_is_pure_d_content", d_repeat_ids_src <= d_ids,
          "every D_repeat_budgetmatched item's source id traces to a real D "
          "item; no B content present")
    d_repeat_tok = sum(i["_completion_tokens"] for i in st["d_repeat"])
    check("d_repeat_matches_controlled_budget",
          abs(d_repeat_tok - st["controlled_total"]) <= max(
              i["_completion_tokens"] for i in st["d"]),
          f"D_repeat_budgetmatched {d_repeat_tok} supervised tokens vs "
          f"BD_controlled {st['controlled_total']} (within one item's worth "
          f"of exact, since repetition proceeds in whole-item units)")

    check("real_tokenizer_used", st["tok_sha"] == EXPECTED_TOKENIZER_JSON_SHA,
          "tokenizer.json hash matches the frozen Phase 6/10 expectation - "
          "no estimator, no substitution")

    failed = [n for n, ok, _ in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")
    if failed:
        raise Gate(f"{len(failed)} gate(s) failed: {failed}")

    sha_full = write_jsonl(OUT_FULL, st["bd_full"])
    sha_ctrl = write_jsonl(OUT_CONTROLLED, st["bd_controlled"])
    sha_rep = write_jsonl(OUT_REPEAT, st["d_repeat"])

    manifest = {
        "generator": GENERATOR_VERSION,
        "tokenizer": {"model": "Qwen/Qwen2.5-14B-Instruct",
                     "revision": "cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8",
                     "tokenizer_json_sha256": st["tok_sha"]},
        "standalone": {
            "B": {"examples": len(st["b"]), "supervised_completion_tokens": st["b_total_comp"],
                 "total_tokens": sum(i["_total_tokens"] for i in st["b"])},
            "D": {"examples": len(st["d"]), "supervised_completion_tokens": st["d_total_comp"],
                 "total_tokens": sum(i["_total_tokens"] for i in st["d"])},
        },
        "bd_full": {
            "artifact": "datasets_v3/train_BD_facts_sql_v3.jsonl", "sha256": sha_full,
            "examples": len(st["bd_full"]),
            "supervised_completion_tokens": st["b_total_comp"] + st["d_total_comp"],
            "total_tokens": sum(i["_total_tokens"] for i in st["bd_full"]),
            "note": "the full eligible v3 recipe: every B and D example "
                   "surviving split/holdout/exposure exclusions, no sampling",
        },
        "bd_controlled": {
            "artifact": "datasets_v3/train_BD_controlled_v3.jsonl", "sha256": sha_ctrl,
            "examples": len(st["bd_controlled"]),
            "b_examples": len(controlled_b), "d_examples": len(controlled_d),
            "b_supervised_completion_tokens": b_ctrl_tok,
            "d_supervised_completion_tokens": d_ctrl_tok,
            "balance_ratio": round(balance_ratio, 4),
            "total_tokens": sum(i["_total_tokens"] for i in st["bd_controlled"]),
            "sampling_method": "deterministic prefix fill over the non-anchor "
                               "arm, sorted by example_id, stopped at the "
                               "nearest completion-token match to the anchor "
                               "arm's total",
        },
        "d_repeat_budgetmatched": {
            "artifact": "datasets_v3/train_D_repeat_budgetmatched_v3.jsonl",
            "sha256": sha_rep, "examples": len(st["d_repeat"]),
            "supervised_completion_tokens": d_repeat_tok,
            "total_tokens": sum(i["_total_tokens"] for i in st["d_repeat"]),
            "target_budget": st["controlled_total"],
            "sampling_method": "D cycled from its example_id-sorted order, "
                               "repeating, until the completion-token budget "
                               "is met",
        },
        "optimizer_steps_and_effective_passes": (
            "NOT computed here. steps = total_supervised_tokens / "
            "(batch_size * assistant_only_loss ? completion_tokens_per_step : "
            "total_tokens_per_step); both batch_size and epoch count are "
            "Phase 24 dev-tuned hyperparameters not yet frozen by this "
            "repository. Reporting a specific step count now would require "
            "inventing those parameters -- deferred to Phase 24's actual "
            "training config rather than fabricated here."),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True,
                                       ensure_ascii=False) + "\n", encoding="utf-8")

    _update_ledger(sha_full)
    _composition(st, controlled_b, controlled_d)
    _audit(st, controlled_b, controlled_d, checks, sha_full, sha_ctrl, sha_rep)

    print(f"\nAll Phase 16 gates passed.")
    print(f"  {OUT_FULL.relative_to(ROOT)}  sha256 {sha_full}  "
         f"({len(st['bd_full'])} items)")
    print(f"  {OUT_CONTROLLED.relative_to(ROOT)}  sha256 {sha_ctrl}  "
         f"({len(st['bd_controlled'])} items, B {b_ctrl_tok} / D {d_ctrl_tok} tok)")
    print(f"  {OUT_REPEAT.relative_to(ROOT)}  sha256 {sha_rep}  "
         f"({len(st['d_repeat'])} items, {d_repeat_tok} tok)")
    return 0


def _update_ledger(sha_full):
    """BD_full/BD_controlled/D_repeat all draw exclusively from B and D
    content already independently verified exposure_count 0 at Phase 11/14
    (README's exposure_policy arm list names BD, not BD_full/controlled/
    repeat separately) -- no new strings, no new scan."""
    p = ROOT / "datasets_v3" / "FACT_EXPOSURE_LEDGER_v3.json"
    led = json.loads(p.read_text(encoding="utf-8"))
    b_scanned = led["arms"]["B"]["strings_scanned"]
    d_scanned = led["arms"]["D"]["strings_scanned"]
    led["arms"]["BD"] = {
        "scanned": True, "exposure_count": 0,
        "artifact": "datasets_v3/train_BD_facts_sql_v3.jsonl",
        "sha256": sha_full, "strings_scanned": b_scanned + d_scanned,
        "phase": 16,
        "note": "union of B and D, both independently verified "
               "exposure_count 0 at Phase 11/14; BD_controlled and "
               "D_repeat_budgetmatched are subsets/repeats of this same "
               "already-scanned content, introducing no new strings",
    }
    p.write_text(json.dumps(led, indent=2, sort_keys=True,
                            ensure_ascii=False) + "\n", encoding="utf-8")


def _composition(st, controlled_b, controlled_d):
    L = ["# BD_COMPOSITION_v3\n",
         "Phase 16 — composition of B/D mixtures by SUPERVISED COMPLETION "
         "tokens (assistant_only_loss=True), not raw example counts.\n",
         "## B attribute mix (share of B's supervised completion tokens)\n",
         "| source | " + " | ".join(sorted({i["attribute"] for i in st["b"]})) + " |",
         "|---|" + "---|" * len({i["attribute"] for i in st["b"]})]

    def row(label, items):
        mix = attribute_mix(items) if items and "attribute" in items[0] else {}
        attrs = sorted({i["attribute"] for i in st["b"]})
        return f"| {label} | " + " | ".join(f"{mix.get(a, 0.0)}%" for a in attrs) + " |"

    L.append(row("standalone B", st["b"]))
    L.append(row("B share of BD_full", st["b"]))
    L.append(row("B share of BD_controlled", controlled_b))
    L += ["",
          "BD_full uses all of B unchanged, so its B-mix is identical to "
          "standalone B by construction. BD_controlled's B-mix is identical "
          "here too because B is the anchor arm (never subsampled) in this "
          "run -- reported separately regardless, so a future run where D is "
          "the smaller arm doesn't silently reuse a stale identity.\n",
          "## D operation_family mix (share of D's supervised completion tokens)\n",
          "| source | " + " | ".join(sorted({i["operation_family"] for i in st["d"]})) + " |",
          "|---|" + "---|" * len({i["operation_family"] for i in st["d"]})]

    def famrow(label, items):
        mix = d_family_mix(items) if items else {}
        fams = sorted({i["operation_family"] for i in st["d"]})
        return f"| {label} | " + " | ".join(f"{mix.get(f, 0.0)}%" for f in fams) + " |"

    L.append(famrow("standalone D", st["d"]))
    L.append(famrow("D share of BD_full", st["d"]))
    L.append(famrow("D share of BD_controlled", controlled_d))
    L += ["",
          "Only `filter` survives D's eligibility gate (Phase 13/14 excludes "
          "argmax_topk/group_by), so this axis is trivially 100% in every "
          "row -- reported anyway, since a future eligibility change should "
          "show up here rather than be silently assumed away.\n",
          "## D join_arity mix (share of D's supervised completion tokens)\n",
          "| source | " + " | ".join(str(k) for k in
                                    sorted({i["join_arity"] for i in st["d"]})) + " |",
          "|---|" + "---|" * len({i["join_arity"] for i in st["d"]})]

    def aritrow(label, items):
        mix = d_arity_mix(items) if items else {}
        arities = sorted({i["join_arity"] for i in st["d"]})
        return f"| {label} | " + " | ".join(f"{mix.get(str(a), 0.0)}%"
                                           for a in arities) + " |"

    L.append(aritrow("standalone D", st["d"]))
    L.append(aritrow("D share of BD_full", st["d"]))
    L.append(aritrow("D share of BD_controlled", controlled_d))
    L += ["",
          "If BD_controlled's join_arity mix drifts from standalone D's, "
          "that is a finding about the deterministic example_id-order sampler "
          "(README:577-582), reported here rather than hidden inside a "
          "single aggregate total.\n"]
    OUT_COMPOSITION.write_text("\n".join(L), encoding="utf-8")


def _audit(st, controlled_b, controlled_d, checks, sha_full, sha_ctrl, sha_rep):
    L = ["# DATASET_BD_v3\n",
         "Phase 16 — BD datasets and budget manifests.\n",
         "## Artifacts\n", "```text",
         f"train_BD_facts_sql_v3.jsonl          sha256 {sha_full}",
         f"train_BD_controlled_v3.jsonl         sha256 {sha_ctrl}",
         f"train_D_repeat_budgetmatched_v3.jsonl sha256 {sha_rep}",
         f"BD_SAMPLING_MANIFEST_v3.json, BD_COMPOSITION_v3.md",
         "```\n",
         "## Standalone totals (supervised completion tokens, real tokenizer)\n",
         "```text",
         f"B   {len(st['b']):5d} examples   {st['b_total_comp']:7d} tokens",
         f"D   {len(st['d']):5d} examples   {st['d_total_comp']:7d} tokens",
         "```\n",
         "v2 reference (context only, not a v3 target): B ~89.3k supervised "
         "chars, D ~71.2k, BD ~160.4k. v3's own KB, task pool and eligibility "
         "rules are different in scale and composition, so these numbers are "
         "not expected to match, and are not treated as a target here.\n",
         "## BD_controlled\n", "```text",
         f"B   {len(controlled_b):5d} examples   "
         f"{sum(i['_completion_tokens'] for i in controlled_b):7d} tokens (full B, anchor arm)",
         f"D   {len(controlled_d):5d} examples   "
         f"{sum(i['_completion_tokens'] for i in controlled_d):7d} tokens (subsampled)",
         "```\n",
         "## D_repeat_budgetmatched\n", "```text",
         f"{len(st['d_repeat']):5d} examples (D cycled/repeated)   "
         f"{sum(i['_completion_tokens'] for i in st['d_repeat']):7d} tokens",
         "```\n",
         "## Optimizer steps / effective passes\n",
         "Not computed. Both batch_size and epoch count are Phase 24 "
         "dev-tuned hyperparameters not yet frozen — reporting a step count "
         "now would require inventing them. See BD_SAMPLING_MANIFEST_v3.json's "
         "`optimizer_steps_and_effective_passes` note for the formula.\n",
         "## Validation\n", "| check | result | detail |", "|---|---|---|"]
    for n, ok, d in checks:
        L.append(f"| `{n}` | {'PASS' if ok else 'FAIL'} | {d} |")
    L.append("")
    OUT_AUDIT.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Gate, H.HoldoutError) as e:
        print(f"\nPHASE 16 GATE FAILURE: {e}", file=sys.stderr)
        print("No artifact written.", file=sys.stderr)
        raise SystemExit(1)
