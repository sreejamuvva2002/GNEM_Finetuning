"""Phase 8 -- summary, per-family metrics, error analysis, report skeleton.

DENOMINATOR DISCIPLINE. Every expected item ends in exactly one status, and
non-success counts against the denominator (README Phase 40). The hard assert
is `scored + failed == expected probe size`. Failure statuses are never dropped
from a denominator, never counted twice, and never silently become zero or
correct.

TWO METRICS, NEVER MERGED. `task_result_correctness` is primary and
`strict_result_schema_accuracy` secondary (README Phase 7). They are reported
side by side; there is no combined "accuracy".

DATA-DRIVEN FAMILIES. Families are discovered from the records themselves, so
adding a v3 probe family requires no edit to a hard-coded report order. v2's
`REPORT_ORDER` is exactly the coupling this avoids.

DEV-FACING ONLY. Nothing in this module accepts an unseal parameter, so it is
structurally incapable of reading sealed test/Q42 output.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import eval_records_v3 as R

REPORT_VERSION = "eval_report_v3.0"

SYNTHETIC_BANNER = (
    "SYNTHETIC VALIDATION FIXTURE — NOT EXPERIMENTAL RESULTS")


class DenominatorError(ValueError):
    """Item accounting does not reconcile against the expected count."""


def summarize(records, *, expected_count: int) -> dict:
    """Summary with exact denominators and every failure status counted."""
    recs = list(records)
    if any(R.classify_result_set(r.family) == R.SEALED_KIND for r in recs):
        raise R.SealError(
            "dev-facing summarization refused: records contain a sealed family")

    status_counts = Counter(r.status for r in recs)
    # Exactly-one-status accounting: each record contributes to exactly one bin.
    scored = status_counts["correct"] + status_counts["incorrect"]
    failed = sum(status_counts[s] for s in R.FAILURE_STATUSES)
    total = scored + failed
    if total != len(recs):
        raise DenominatorError(
            f"status bins sum to {total} but there are {len(recs)} records; "
            f"an item was double-counted or lost")
    if total != expected_count:
        raise DenominatorError(
            f"scored ({scored}) + failed ({failed}) = {total} != expected "
            f"probe size ({expected_count})")

    n = len(recs)
    task = sum(r.task_result_correctness for r in recs)
    schema = sum(r.strict_result_schema_accuracy for r in recs)
    return {
        "report_version": REPORT_VERSION,
        "provenance": "synthetic validation fixture; not experimental results",
        "expected_item_count": expected_count,
        "scored": scored,
        "correct": status_counts["correct"],
        "incorrect": status_counts["incorrect"],
        "failed": failed,
        "status_counts": {s: status_counts.get(s, 0) for s in R.STATUSES},
        "denominator_invariant": {
            "scored_plus_failed": total,
            "expected": expected_count,
            "holds": total == expected_count,
        },
        # Primary and secondary, kept distinct and both over the full denominator.
        "task_result_correctness": {
            "value": task / n, "numerator": task, "denominator": n,
            "rendered": f"{task:g} / {n} = {task / n:.1%}", "role": "primary"},
        "strict_result_schema_accuracy": {
            "value": schema / n, "numerator": schema, "denominator": n,
            "rendered": f"{schema:g} / {n} = {schema / n:.1%}", "role": "secondary"},
        "families": per_family(recs),
    }


def per_family(records) -> dict:
    """Per-family metrics, discovered from the data rather than a fixed order."""
    by_family = defaultdict(list)
    for r in records:
        by_family[r.family].append(r)
    out = {}
    for fam in sorted(by_family):
        rs = by_family[fam]
        n = len(rs)
        task = sum(r.task_result_correctness for r in rs)
        schema = sum(r.strict_result_schema_accuracy for r in rs)
        counts = Counter(r.status for r in rs)
        out[fam] = {
            "n_items": n,
            "correct": counts["correct"],
            "incorrect": counts["incorrect"],
            "failed": sum(counts[s] for s in R.FAILURE_STATUSES),
            "status_counts": {s: counts.get(s, 0) for s in R.STATUSES if counts.get(s)},
            "task_result_correctness": task / n,
            "strict_result_schema_accuracy": schema / n,
            "denominator": n,
            "rendered": f"{task:g} / {n} = {task / n:.1%}",
        }
    return out


def error_analysis(records) -> dict:
    """Group failures by status, family, and answer_type.

    Deliberately minimal: no scientific error taxonomy is invented from probes
    that do not exist yet. It distinguishes the frozen outcome classes and
    nothing more.
    """
    recs = list(records)
    if any(R.classify_result_set(r.family) == R.SEALED_KIND for r in recs):
        raise R.SealError("dev-facing error analysis refused on sealed records")

    failures = [r for r in recs if r.status != "correct"]
    by_status, by_family, by_answer_type = (defaultdict(list), defaultdict(Counter),
                                            defaultdict(Counter))
    for r in failures:
        by_status[r.status].append(r.example_id)
        by_family[r.family][r.status] += 1
        by_answer_type[r.answer_type or "(none)"][r.status] += 1

    return {
        "report_version": REPORT_VERSION,
        "provenance": "synthetic validation fixture; not experimental results",
        "n_failures": len(failures),
        "distinguished_classes": {
            "incorrect_valid_prediction": sum(
                1 for r in failures if r.status == "incorrect"),
            "generation_failure": sum(
                1 for r in failures if r.status == "generation_failure"),
            "parse_failure": sum(
                1 for r in failures if r.status == "parse_failure"),
            "SQL_error": sum(1 for r in failures if r.status == "SQL_error"),
            "timeout": sum(1 for r in failures if r.status == "timeout"),
            "truncated_output": sum(
                1 for r in failures if r.status == "truncated_output"),
            "invalid_output": sum(
                1 for r in failures if r.status == "invalid_output"),
        },
        "by_status": {k: sorted(v) for k, v in sorted(by_status.items())},
        "by_family": {k: dict(v) for k, v in sorted(by_family.items())},
        "by_answer_type": {k: dict(v) for k, v in sorted(by_answer_type.items())},
    }


def render_report_skeleton(summary: dict, errors: dict, *, stats_demo: dict,
                           provenance: dict) -> str:
    """Render the REPORT_v3 skeleton.

    Proves the reporting layer renders. It contains NO GNEM findings: every
    number below comes from synthetic fixtures, and the banner says so.
    """
    L = [f"# REPORT_v3 (SKELETON)\n",
         f"> **{SYNTHETIC_BANNER}**",
         ">",
         "> Generated by the Phase 8 fixture run to prove the reporting layer "
         "renders. Every number below comes from deterministic synthetic "
         "fixtures. This file contains **no GNEM findings** and states no "
         "experimental result.",
         ">",
         "> The authoritative `REPORT_v3.md` is created only at **Phase 42**, at "
         "the repository root. This fixture-local file is not that report and "
         "never becomes it.\n",
         "## Provenance\n", "```text"]
    for k, v in provenance.items():
        L.append(f"{k:28} {v}")
    L += ["```\n",
          "## Item accounting (synthetic)\n", "```text",
          f"expected item count   {summary['expected_item_count']}",
          f"scored                {summary['scored']}",
          f"failed                {summary['failed']}",
          f"scored + failed       {summary['denominator_invariant']['scored_plus_failed']}"
          f"   invariant holds: {summary['denominator_invariant']['holds']}",
          "```\n",
          "| status | count |", "|---|---|"]
    for s, c in summary["status_counts"].items():
        L.append(f"| `{s}` | {c} |")
    L += ["",
          "Every item ends in exactly one status, and non-success counts against "
          "the denominator.\n",
          "## Metrics (synthetic)\n",
          "| metric | role | value | denominator |", "|---|---|---|---|",
          f"| `task_result_correctness` | **primary** | "
          f"{summary['task_result_correctness']['rendered']} | "
          f"{summary['task_result_correctness']['denominator']} |",
          f"| `strict_result_schema_accuracy` | secondary | "
          f"{summary['strict_result_schema_accuracy']['rendered']} | "
          f"{summary['strict_result_schema_accuracy']['denominator']} |",
          "",
          "The two are reported separately and never merged into a single "
          "\"accuracy\".\n",
          "## Per-family metrics (synthetic)\n",
          "| family | n | correct | incorrect | failed | task | schema |",
          "|---|---|---|---|---|---|---|"]
    for fam, m in summary["families"].items():
        L.append(f"| `{fam}` | {m['n_items']} | {m['correct']} | {m['incorrect']} | "
                 f"{m['failed']} | {m['task_result_correctness']:.1%} | "
                 f"{m['strict_result_schema_accuracy']:.1%} |")
    L += ["",
          "Families are discovered from the records, so adding a v3 family "
          "requires no edit to a hard-coded report order.\n",
          "## Error analysis (synthetic)\n",
          "| failure class | count |", "|---|---|"]
    for k, v in errors["distinguished_classes"].items():
        if v:
            L.append(f"| `{k}` | {v} |")
    L += ["",
          "## Statistical plumbing (synthetic inputs)\n",
          "Exercised to prove the functions behave. **No significance claim is "
          "made on fixture data.**\n", "```text"]
    for k, v in stats_demo.items():
        L.append(f"{k:26} {v}")
    L += ["```\n",
          "## Sealed-test posture\n",
          "Test and Q42 remain `LOCKED_UNTIL_PHASE_40`. Dev-facing reporting "
          "cannot request an unseal — the parameter does not exist on any "
          "dev API — and this library cannot read sealed content at all. "
          "Pre-Phase-40 auditing sees only counts, hashes, paths and "
          "provenance.\n"]
    return "\n".join(L)


def write_json(path, obj) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True,
                               ensure_ascii=False) + "\n", encoding="utf-8")
    return R.sha256_file(path)
