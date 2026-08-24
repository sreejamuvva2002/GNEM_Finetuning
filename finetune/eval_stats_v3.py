"""Phase 8 -- statistical plumbing, mapped to the live protocol.

Every method here exists because the CURRENT README/CLAUDE contract requires it.
Nothing is included merely because v2 had it; the v2 repository is historical
reference material, not the scientific protocol.

    method                        frozen requirement
    ---------------------------   ------------------------------------------
    per-seed scores               README:972, CLAUDE.md:826
    mean +/- SD                   README:972, CLAUDE.md:827
    effect size                   README:972, CLAUDE.md:828
    paired item-level bootstrap   README:972, CLAUDE.md:829
    exact denominators            README:972, CLAUDE.md 28
    Holm correction               README:974
    McNemar (secondary)           README:973
    split-group weighting         README:990-991, CLAUDE.md:847-854

DELIBERATELY NOT IMPLEMENTED: hierarchical bootstrap. v2 had it; the live
protocol never mentions it, so it is deferred rather than introduced here.

Phase 8 exercises these on synthetic fixtures to prove the plumbing behaves.
No significance claim is made on fixture data, and no Phase 39/41 decision is
preempted -- these are interfaces, not findings.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict

STATS_VERSION = "eval_stats_v3.0"
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 20260824   # fixed, so bootstrap output is reproducible


class StatsUsageError(ValueError):
    """A statistic was requested in a way the protocol forbids."""


def mean(xs) -> float:
    xs = list(xs)
    if not xs:
        raise StatsUsageError("mean of an empty sample is undefined")
    return sum(xs) / len(xs)


def mean_sd(xs, *, deterministic: bool = False) -> dict:
    """Mean and sample SD (README:972, CLAUDE.md:827).

    `deterministic=True` marks a condition that decodes greedily at temperature
    0. README:976-979: such a condition "has exactly **one** inference result and
    no spread at all", and the report must "never report a baseline standard
    deviation". Requesting an SD for one is refused rather than silently
    reported as 0.0.
    """
    xs = list(xs)
    if not xs:
        raise StatsUsageError("mean_sd of an empty sample is undefined")
    if deterministic:
        if len(xs) != 1:
            raise StatsUsageError(
                f"a deterministic condition has exactly one result, got {len(xs)}")
        return {"mean": xs[0], "sd": None, "n": 1, "deterministic": True,
                "note": "greedy at temperature 0; no spread exists"}
    if len(xs) < 2:
        return {"mean": xs[0], "sd": None, "n": 1, "deterministic": False,
                "note": "SD undefined for n=1"}
    m = mean(xs)
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
    return {"mean": m, "sd": sd, "n": len(xs), "deterministic": False}


def effect_size(diffs) -> float:
    """Standardized paired effect size (Cohen's d_z). README:972."""
    diffs = list(diffs)
    if len(diffs) < 2:
        raise StatsUsageError("effect size needs at least two paired items")
    m = mean(diffs)
    sd = math.sqrt(sum((d - m) ** 2 for d in diffs) / (len(diffs) - 1))
    return 0.0 if sd == 0 else m / sd


def paired_bootstrap(diffs, *, n: int = BOOTSTRAP_N, seed: int = BOOTSTRAP_SEED,
                     alpha: float = 0.05) -> dict:
    """Paired ITEM-LEVEL bootstrap of the mean difference. README:972.

    Resamples items (not seeds), which is what "paired item-level bootstrap
    effect estimates" means. Deterministic for a fixed seed.
    """
    diffs = list(diffs)
    if not diffs:
        raise StatsUsageError("paired bootstrap needs at least one paired item")
    rng = random.Random(seed)
    k = len(diffs)
    means = []
    for _ in range(n):
        means.append(sum(diffs[rng.randrange(k)] for _ in range(k)) / k)
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[min(n - 1, int((1 - alpha / 2) * n))]
    return {"observed_mean_diff": mean(diffs), "ci_low": lo, "ci_high": hi,
            "n_items": k, "n_resamples": n, "alpha": alpha, "seed": seed}


def mcnemar(pairs) -> dict:
    """McNemar on predeclared BINARY comparisons. README:973 ("secondary").

    `pairs` is an iterable of (a_correct, b_correct) booleans for the same item.
    Exact binomial on the discordant pairs; no continuity fudge.
    """
    b = c = 0
    for a_ok, b_ok in pairs:
        if bool(a_ok) and not bool(b_ok):
            b += 1
        elif bool(b_ok) and not bool(a_ok):
            c += 1
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "n_discordant": 0, "p_value": 1.0,
                "note": "no discordant pairs"}
    # exact two-sided binomial p at q=0.5
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / (2 ** n)
    return {"b": b, "c": c, "n_discordant": n,
            "p_value": min(1.0, 2 * tail),
            "role": "secondary evidence (README:973)"}


def holm(pvalues: dict) -> dict:
    """Holm correction across PRIMARY comparisons. README:974."""
    if not pvalues:
        return {}
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out, running = {}, 0.0
    for i, (name, p) in enumerate(ordered):
        adj = min(1.0, (m - i) * p)
        running = max(running, adj)      # enforce monotonicity
        out[name] = running
    return out


def split_group_weighted(item_scores: dict, group_of: dict,
                         *, entity_attributable: dict) -> dict:
    """Split-group-weighted score. README:990-991, CLAUDE.md:847-854.

    CLAUDE.md 28 fixes the procedure: average item scores WITHIN each
    `split_group`, then average the group scores equally.

    Applies ONLY to entity-attributable items. CLAUDE.md:854 and README:996-999
    are explicit that it is undefined for global aggregate questions, which
    belong to no split group; those are reported item-weighted only. Items
    marked non-attributable are excluded and counted, never silently folded in.
    """
    groups = defaultdict(list)
    excluded = 0
    for ex_id, score in item_scores.items():
        if not entity_attributable.get(ex_id, False):
            excluded += 1
            continue
        g = group_of.get(ex_id)
        if g is None:
            raise StatsUsageError(
                f"item {ex_id!r} is entity-attributable but has no split_group")
        groups[g].append(score)
    if not groups:
        return {"split_group_weighted": None, "n_groups": 0,
                "n_items_used": 0, "n_items_excluded": excluded,
                "note": "no entity-attributable items; undefined by protocol"}
    per_group = {g: mean(v) for g, v in groups.items()}
    return {
        "split_group_weighted": mean(per_group.values()),
        "n_groups": len(per_group),
        "n_items_used": sum(len(v) for v in groups.values()),
        "n_items_excluded": excluded,
        "note": ("average within split_group, then across groups unweighted "
                 "(CLAUDE.md 28); aggregate questions excluded by protocol"),
    }


def item_weighted(item_scores: dict) -> dict:
    """Plain item-weighted score with an EXACT denominator (CLAUDE.md 28)."""
    if not item_scores:
        raise StatsUsageError("item_weighted of an empty set is undefined")
    n = len(item_scores)
    correct = sum(item_scores.values())
    return {"item_weighted": correct / n, "n_items": n,
            "numerator": correct, "denominator": n,
            "rendered": f"{correct:g} / {n} = {correct / n:.1%}"}


def per_seed_scores(by_seed: dict) -> dict:
    """Per-seed scores reported individually before any aggregate. README:972."""
    if not by_seed:
        raise StatsUsageError("no seeds supplied")
    return {"per_seed": {int(s): v for s, v in sorted(by_seed.items())},
            "n_seeds": len(by_seed)}
