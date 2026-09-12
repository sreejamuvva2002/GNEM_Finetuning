"""Build a NON-TAUTOLOGICAL structured development set (dev_structured_r2_v3.jsonl).

Why this exists
---------------
`dev_structured_v3.jsonl` asks, for all 51 items, "Which recorded company is named
X and has <field> recorded as V?" with gold `[[X]]`. The complete gold answer is
quoted inside its own question, so the task is solvable by echoing the prompt: both
SQL baselines score 51/51 and the set cannot discriminate between arms. It is also
the eval-loss signal `train_v3.py` uses to select checkpoints for C_answers, D_sql,
D_repeat_budgetmatched and half of BC/BD_*, so every final run would select on a
degenerate objective.

The original set and its results are PRESERVED unchanged as historical artifacts.
This builder writes a new file; it never edits the old one.

Construction
------------
Every task's COMBINED predicate must be satisfied by at least one held-out
DEVELOPMENT record, whose row IDs are retained in `dev_anchor_row_ids`. Drawing each
value from dev data separately is not sufficient: a conjunction of two dev-observed
values can describe only training or test records, which would make the "anchored on
a development record" claim false. Candidates with no dev anchor are skipped.

No task names a company. The answer is the set (or count) of companies carrying the
predicate, so the gold cannot be recovered from the question text. Execution scope is
`train_dev_kb`, matching the original set.

Frozen holdouts respected (asserted, fail-closed):
  * operation holdouts -- argmax_topk / group_by / limit_only must not appear in
    any rendered gold_sql, so selecting on dev loss cannot tune toward the sealed
    operation probe;
  * composition holdout -- the {certifications, processes} pair is excluded; the
    two non-held-out arity-2 pairs are used instead;
  * company holdout -- the frozen split is untouched and no test-split company
    name appears in any question;
  * no logical_fingerprint, gold_sql or question collides with the training D set,
    the task pool, the reserved few-shot sources, or any sealed probe.

Split metadata is corrected: `make_task` hardcodes `split: "train"`, which the old
dev file inherited while asking exclusively about dev-split companies. Here that key
is replaced by `task_split` (always "dev") and `anchor_entity_split` (the split of
the record the attribute value was drawn from).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "finetune"))

import holdout_v3 as H          # noqa: E402
import kb_v3 as K               # noqa: E402
import leak_audit_v3 as L       # noqa: E402
import phase12_task_pool as P   # noqa: E402
import sqlexec_v3 as X          # noqa: E402

OUT = ROOT / "datasets_v3"
DB = OUT / "gnem_v3.sqlite"
DEST = OUT / "dev_structured_r2_v3.jsonl"
LEGACY = OUT / "dev_structured_v3.jsonl"
SCOPE = "train_dev_kb"
FAMILY = "dev_structured_r2"
GENERATOR = "dev_structured_r2_v3.2_A002"

# Per-generator caps keep the set balanced and deterministic; no RNG is used.
SCALAR_FIELDS = ("location", "industry_group", "category", "ev_supply_chain_role",
                 "classification_method")
CAP_SET = 8          # arity-0 company lists per scalar field
CAP_COUNT = 6        # arity-0 counts per scalar field
CAP_CHILD_SET = 10   # arity-1 company lists per child field
CAP_CHILD_COUNT = 6  # arity-1 counts per child field
CAP_COMP = 14        # arity-2 compositions per allowed pair
CAP_MIXED = 5        # arity-1 scalar-attribute + child-membership conjunctions per pair

# Scalar attributes usable as the non-child half of a mixed conjunction.
MIXED_SCALARS = ("category", "industry_group", "ev_supply_chain_role",
                 "classification_method")


def phrase(field: str) -> str:
    return field.replace("_", " ")


def run(sql: str):
    return X.run_sql(sql, SCOPE, db_path=DB)


def sql_scalar_child(scalar_field, scalar_value, child_field, child_value) -> str:
    """Companies matching a scalar attribute AND a child-table membership.

    This is a NEW COMBINATION OF FAMILIAR OPERATIONS: record-level child joins and
    scalar equality filters each appear in training, but their conjunction does not
    appear in the pool. That is what makes multi-company development answers
    available without reproducing a trained query. It is not a claim that the
    combined form is in-distribution for the trained arms -- whether a model
    generalises to the conjunction is exactly what the development set measures.
    """
    table, column = P.CHILD_TABLES[child_field], P.CHILD_COLUMN[child_field]
    return (f"SELECT DISTINCT c.company FROM companies c JOIN {table} x ON "
            f"x.row_id = c.row_id WHERE c.{scalar_field} = {P.sql_lit(scalar_value)} "
            f"AND x.{column} = {P.sql_lit(child_value)} ORDER BY c.company")


def satisfies(record, predicate) -> bool:
    """Does one record satisfy EVERY clause of the task's predicate?"""
    for field, value in predicate:
        if field in H.MULTIVALUED:
            if value not in H.terms(getattr(record, field), field):
                return False
        elif getattr(record, field) != value:
            return False
    return True


def build_task(identifier, question, sql, fields, values, answer_type, columns,
               predicate, dev_records, all_records, splits):
    """Returns the task, or None when no development record satisfies `predicate`."""
    anchors = sorted(r.row_id for r in dev_records if satisfies(r, predicate))
    if not anchors:
        return None
    arity = len(re.findall(r"\bJOIN\b", H._strip_sql_noise(sql), re.I))
    task = P.make_task(identifier, question, sql, answer_type=answer_type,
                       target_columns=columns, fields_used=fields,
                       values_used=values,
                       logical_components={"op": "query", "field": "sql", "value": sql},
                       join_arity=arity)
    result = run(sql)
    task.pop("split", None)          # hardcoded "train"; wrong for a dev artifact
    # dev_anchor_row_ids identifies the ACTUAL anchors. matching_record_splits is
    # merely descriptive -- it says which splits contain a satisfying record, and
    # must never be read as identifying the anchor.
    task.update(example_id=identifier, family=FAMILY, scope=SCOPE,
                task_split="dev", dev_anchor_row_ids=anchors,
                predicate=[{"field": f, "value": v} for f, v in predicate],
                matching_record_splits=sorted({splits[r.row_id] for r in all_records
                                               if satisfies(r, predicate)}),
                generator=GENERATOR, entity_dependent=True,
                gold_value={"columns": list(result.columns),
                            "rows": [list(r) for r in result.rows]})
    task["logical_fingerprint"] = H.logical_fingerprint(task)
    return task


def gold_strings(task) -> list[str]:
    return [str(cell) for row in task["gold_value"]["rows"] for cell in row]


def assert_not_tautological(task, company_names):
    """The defining invariant: the answer must not be recoverable from the prompt."""
    question = task["question"]
    folded = question.casefold()
    for cell in gold_strings(task):
        if re.fullmatch(r"-?\d+", cell):
            # A count must not appear as a standalone token ("1" inside "ISO 14001" is fine).
            assert not re.search(rf"(?<!\d){re.escape(cell)}(?!\d)", question), \
                (task["example_id"], "numeric gold appears in question", cell)
        else:
            assert cell.casefold() not in folded, \
                (task["example_id"], "gold value appears in question", cell)
    # Stronger guarantee for company-returning tasks: no company name at all.
    if task["target_columns"] == ["company"]:
        for name in company_names:
            assert name.casefold() not in folded, \
                (task["example_id"], "company name appears in question", name)


def main() -> int:
    splits = L.row_splits()
    records = K.load_kb("full_kb")
    dev = [r for r in records if splits[r.row_id] == "dev"]
    assert len(dev) == 17, f"expected the frozen 17 development rows, found {len(dev)}"

    registry = json.loads((OUT / "HOLDOUT_REGISTRY_A002.json").read_text())
    held_sets = [set(s) for s in registry["composition_holdouts"]["held_out_sets"]]
    company_names = {r.company for r in records}
    test_names = {r.company for r in records if splits[r.row_id] == "test"}

    # Collision sets are loaded BEFORE generation. A development query that
    # reproduces a training query would make checkpoint selection reward
    # memorisation of a trained item, so such candidates are skipped at the
    # source rather than aborting the build.
    training = [json.loads(s) for s in (OUT / "train_D_sql_v3.jsonl").read_text().splitlines()]
    pool = [json.loads(s) for s in (OUT / "STRUCTURED_TASK_POOL_v3.jsonl").read_text().splitlines()]
    fewshot = json.loads((OUT / "FEWSHOT_MANIFEST_v3.json").read_text())["examples"]
    probes = []
    for name in ("probe_structured_train_v3.jsonl", "probe_structured_paraphrase_v3.jsonl",
                 "probe_operation_heldout_v3.jsonl", "probe_composition_heldout_v3.jsonl",
                 "probe_value_exposure_v3.jsonl", "probe_no_match_v3.jsonl"):
        probes += [json.loads(s) for s in (OUT / name).read_text().splitlines()]
    taken_sql = {r["gold_sql"] for r in training + pool + fewshot + probes if r.get("gold_sql")}
    taken_fp = {r.get("logical_fingerprint") for r in pool + fewshot + probes}
    taken_q = {r["question"] for r in training + pool + probes}

    tasks = []
    skipped = Counter()

    def accept(task) -> bool:
        """Reject unanchored candidates and any that reproduce trained,
        reserved or sealed content."""
        if task is None:
            skipped["no_development_anchor"] += 1
            return False
        if task["gold_sql"] in taken_sql:
            skipped["gold_sql_collision"] += 1
            return False
        if task["logical_fingerprint"] in taken_fp:
            skipped["fingerprint_collision"] += 1
            return False
        if task["question"] in taken_q:
            skipped["question_collision"] += 1
            return False
        tasks.append(task)
        return True

    # --- arity 0: company lists and counts conditioned on a scalar attribute ---
    for field in SCALAR_FIELDS:
        values = sorted({getattr(r, field) for r in dev} - set(P.SENTINEL_VALUES))
        listed = counted = 0
        for value in values:
            anchor = sorted({splits[r.row_id] for r in records
                             if getattr(r, field) == value})
            if listed < CAP_SET:
                sql = P.sql_filter(field, value)
                if 0 < len(run(sql).rows) <= P.LIST_CAP:
                    if accept(build_task(
                            f"DEVR2_list_{field}_{listed}",
                            f"Which companies are recorded with {phrase(field)} {value}?",
                            sql, [field, "company"], [value], "set", ["company"],
                            [(field, value)], dev, records, splits)):
                        listed += 1
            if counted < CAP_COUNT:
                sql = P.sql_count(field, value)
                if run(sql).rows[0][0] > 0:
                    if accept(build_task(
                            f"DEVR2_count_{field}_{counted}",
                            f"How many distinct companies are recorded with {phrase(field)} {value}?",
                            sql, [field, "company"], [value], "scalar", ["n"],
                            [(field, value)], dev, records, splits)):
                        counted += 1

    # --- arity 1: child-table membership ---
    for field in H.MULTIVALUED:
        values = sorted({v for r in dev for v in H.terms(getattr(r, field), field)})
        listed = counted = 0
        for value in values:
            anchor = sorted({splits[r.row_id] for r in records
                             if value in H.terms(getattr(r, field), field)})
            if listed < CAP_CHILD_SET:
                sql = P.sql_child_filter(field, value)
                if 0 < len(run(sql).rows) <= P.CROSS_TABLE_CAP:
                    if accept(build_task(
                            f"DEVR2_child_{field}_{listed}",
                            f"Which companies have {phrase(field)} recorded as {value}?",
                            sql, [field, "company"], [value], "set", ["company"],
                            [(field, value)], dev, records, splits)):
                        listed += 1
            if counted < CAP_CHILD_COUNT:
                sql = P.sql_child_count(field, value)
                if run(sql).rows[0][0] > 0:
                    if accept(build_task(
                            f"DEVR2_childcount_{field}_{counted}",
                            f"How many distinct companies have {phrase(field)} recorded as {value}?",
                            sql, [field, "company"], [value], "scalar", ["n"],
                            [(field, value)], dev, records, splits)):
                        counted += 1

    # --- arity 1: scalar attribute AND child membership -------------------
    # The single-field generators above survive collision filtering only where the
    # value is nearly unique, which leaves every set answer a singleton. This shape
    # restores multi-company answers; candidates with more than one matching company
    # are preferred so the set is not dominated by one-row golds.
    for scalar_field in MIXED_SCALARS:
        scalar_values = sorted({getattr(r, scalar_field) for r in dev}
                               - set(P.SENTINEL_VALUES))
        for child_field in H.MULTIVALUED:
            child_values = sorted({v for r in dev
                                   for v in H.terms(getattr(r, child_field), child_field)})
            candidates = []
            for scalar_value in scalar_values:
                for child_value in child_values:
                    sql = sql_scalar_child(scalar_field, scalar_value,
                                           child_field, child_value)
                    matched = len(run(sql).rows)
                    if 0 < matched <= P.CROSS_TABLE_CAP:
                        candidates.append((matched == 1, -matched, scalar_value,
                                           child_value, sql))
            made = 0
            for _, _, scalar_value, child_value, sql in sorted(candidates):
                if made >= CAP_MIXED:
                    break
                if accept(build_task(
                        f"DEVR2_mixed_{scalar_field}_{child_field}_{made}",
                        f"Which companies are recorded with {phrase(scalar_field)} "
                        f"{scalar_value} and have {phrase(child_field)} recorded as "
                        f"{child_value}?",
                        sql, [scalar_field, child_field, "company"],
                        [scalar_value, child_value], "set", ["company"],
                        [(scalar_field, scalar_value), (child_field, child_value)],
                        dev, records, splits)):
                    made += 1

    # --- arity 2: compositions, excluding the held-out pair ---
    for f1, f2 in (("processes", "services"), ("services", "certifications")):
        assert not any(h <= {f1, f2} for h in held_sets), (f1, f2)
        pairs = sorted({(v1, v2) for r in dev
                        for v1 in H.terms(getattr(r, f1), f1)
                        for v2 in H.terms(getattr(r, f2), f2)})
        made = 0
        for v1, v2 in pairs:
            if made >= CAP_COMP:
                break
            sql = P.sql_composition(f1, v1, f2, v2)
            if 0 < len(run(sql).rows) <= P.CROSS_TABLE_CAP:
                if accept(build_task(
                        f"DEVR2_comp_{f1}_{f2}_{made}",
                        f"Which companies have both {phrase(f1)} recorded as {v1} and "
                        f"{phrase(f2)} recorded as {v2}?",
                        sql, [f1, f2, "company"], [v1, v2], "set", ["company"],
                        [(f1, v1), (f2, v2)], dev, records, splits)):
                    made += 1

    # ---------------- fail-closed gates ----------------
    assert tasks, "no development tasks were generated"
    assert len({t["example_id"] for t in tasks}) == len(tasks), "duplicate example_id"

    for t in tasks:
        assert not H.operation_families_present(t["gold_sql"]), \
            (t["example_id"], "held-out operation construct present")
        assert t["operation_family"] == "filter", (t["example_id"], t["operation_family"])
        assert t["scope"] == SCOPE and t["task_split"] == "dev"
        assert "split" not in t, (t["example_id"], "misleading split key retained")
        assert t["gold_value"]["rows"], (t["example_id"], "empty gold")
        component = set(t["fields_used"]) - {"company"}
        assert not any(h <= component for h in held_sets), \
            (t["example_id"], "held-out composition present", sorted(component))
        assert t["dev_anchor_row_ids"], (t["example_id"], "no development anchor")
        assert all(splits[i] == "dev" for i in t["dev_anchor_row_ids"]), t["example_id"]
        assert "anchor_entity_split" not in t, (t["example_id"], "ambiguous anchor field")
        assert_not_tautological(t, company_names)
        for name in test_names:
            assert name.casefold() not in t["question"].casefold(), \
                (t["example_id"], "test company named", name)

    # Re-assert the acceptance filter over the committed set.
    for t in tasks:
        assert t["gold_sql"] not in taken_sql, (t["example_id"], "gold_sql collides")
        assert t["logical_fingerprint"] not in taken_fp, (t["example_id"], "fingerprint collides")
        assert t["question"] not in taken_q, (t["example_id"], "question collides")

    DEST.write_text("".join(json.dumps(t, sort_keys=True, ensure_ascii=False) + "\n"
                            for t in tasks))

    legacy_n = len(LEGACY.read_text().splitlines())
    arity = Counter(t["join_arity"] for t in tasks)
    answer = Counter(t["answer_type"] for t in tasks)
    answer_rows = Counter(len(t["gold_value"]["rows"]) for t in tasks
                          if t["answer_type"] == "set")
    multi_row = sum(v for k, v in answer_rows.items() if k > 1)
    counts = Counter(t["gold_value"]["rows"][0][0] for t in tasks
                     if t["answer_type"] == "scalar")
    report = {
        "artifact": "datasets_v3/dev_structured_r2_v3.jsonl",
        "generator": GENERATOR,
        "sha256": H.sha256_file(DEST),
        "tasks": len(tasks),
        "join_arity": dict(sorted(arity.items())),
        "answer_type": dict(answer),
        "set_answer_sizes": dict(sorted(answer_rows.items())),
        "set_answers_with_multiple_companies": multi_row,
        "count_answer_range": [min(counts), max(counts)] if counts else None,
        "candidates_skipped": dict(skipped),
        "registry_sha256": registry_sha(registry),
        "supersedes_for_checkpoint_selection": "datasets_v3/dev_structured_v3.jsonl",
        "legacy_preserved": {"path": "datasets_v3/dev_structured_v3.jsonl",
                             "tasks": legacy_n,
                             "sha256": H.sha256_file(LEGACY)},
        "gates": [
            "no held-out operation construct in any gold_sql",
            "held-out {certifications, processes} composition excluded",
            "no gold cell value appears in its own question",
            "no company name appears in any company-returning question",
            "no test-split company named in any question",
            "no gold_sql / fingerprint / question collision with training, pool, few-shot or probes",
            "scope train_dev_kb; task_split=dev; misleading split key removed",
            "every task's COMBINED predicate is satisfied by >=1 development record, "
            "whose row IDs are retained in dev_anchor_row_ids",
        ],
        "model_inference_performed": False,
    }
    (ROOT / "validation_v3" / "DEV_STRUCTURED_R2_v3.md").write_text(render(report, tasks))
    print(json.dumps({k: v for k, v in report.items() if k != "gates"}, indent=2))
    return 0


def registry_sha(registry) -> str:
    return H.sha256_file(OUT / "HOLDOUT_REGISTRY_A002.json")


def render(report, tasks) -> str:
    lines = ["# DEV_STRUCTURED_R2_v3", "",
             "Non-tautological structured development set. The original "
             "`dev_structured_v3.jsonl` and every result computed from it are preserved "
             "unchanged as historical artifacts.", "",
             "## Why the original set was replaced", "",
             "All 51 original items quote their complete gold answer inside the question "
             "(*\"Which recorded company is named X and has &lt;field&gt; recorded as V?\"* "
             "with gold `[[X]]`), so both SQL baselines scored 51/51 and the set could not "
             "discriminate between arms. It was also the checkpoint-selection eval signal in "
             "`train_v3.py`.", "",
             "## Composition", "",
             f"```text", f"tasks            {report['tasks']}",
             f"join_arity       {report['join_arity']}",
             f"answer_type      {report['answer_type']}",
             f"multi-company set answers  {report['set_answers_with_multiple_companies']}"
             f" of {report['answer_type'].get('set', 0)}",
             f"count answers range        {report['count_answer_range']}",
             f"sha256           {report['sha256']}", "```", "",
             "## Development anchoring", "",
             "Each task's COMBINED predicate is satisfied by at least one held-out "
             "development record, and those row IDs are stored in `dev_anchor_row_ids`. "
             "Drawing each value from development data separately is NOT sufficient: a "
             "conjunction of two dev-observed values can describe only training or test "
             "records. An earlier revision of this set contained 14 such tasks; they are "
             "now rejected at generation. `matching_record_splits` is descriptive only "
             "-- it reports which splits contain a satisfying record and never "
             "identifies the anchor.", "",
             "## Query shapes", "",
             "The arity-1 `mixed` tasks pair a scalar attribute filter with a "
             "record-level child-table join. Both operations appear in training "
             "individually; their **conjunction does not appear in the task pool**. "
             "These are therefore NEW COMBINATIONS OF FAMILIAR OPERATIONS. That is what "
             "makes multi-company development answers available without reproducing a "
             "trained query, and it is deliberately not a claim that the combined form "
             "is in-distribution for the trained arms -- whether a model generalises to "
             "the conjunction is part of what the set measures. Candidates whose gold "
             "SQL reproduced a trained query were skipped at generation rather than "
             "reworded.", "",
             "## Gates (all fail-closed assertions in the builder)", ""]
    lines += [f"- {g}" for g in report["gates"]]
    lines += ["", "## Examples", ""]
    for t in tasks[:3] + tasks[-2:]:
        lines.append(f"- `{t['example_id']}` (arity {t['join_arity']}, {t['answer_type']}): "
                     f"{t['question']} -> {len(t['gold_value']['rows'])} row(s)")
    lines += ["", "This artifact is development-only. No model inference was performed by "
              "this builder, no protected probe was read for scoring, and Q42 approval and "
              "the final training release remain outstanding.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
