"""Validation suite for the non-tautological structured development set.

Includes a meta-test: the anti-tautology detector is run against the LEGACY
dev_structured_v3.jsonl and must flag all 51 of its items. A checker that cannot
reproduce the original defect is not evidence that the replacement is free of it.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "finetune"))

import holdout_v3 as H          # noqa: E402
import kb_v3 as K               # noqa: E402
import leak_audit_v3 as L       # noqa: E402
import sqlexec_v3 as X          # noqa: E402

OUT = ROOT / "datasets_v3"
DB = OUT / "gnem_v3.sqlite"
DEST = OUT / "dev_structured_r2_v3.jsonl"
LEGACY = OUT / "dev_structured_v3.jsonl"


def load(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def satisfies(record, predicate):
    """Does one record satisfy EVERY clause of the predicate?"""
    for clause in predicate:
        field, value = clause["field"], clause["value"]
        if field in H.MULTIVALUED:
            if value not in H.terms(getattr(record, field), field):
                return False
        elif getattr(record, field) != value:
            return False
    return True


def gold_cells(task):
    return [str(c) for row in task["gold_value"]["rows"] for c in row]


def quoted_gold(task) -> list[str]:
    """Gold cells recoverable from the task's own question text."""
    question = task["question"]
    folded = question.casefold()
    hits = []
    for cell in gold_cells(task):
        if re.fullmatch(r"-?\d+", cell):
            if re.search(rf"(?<!\d){re.escape(cell)}(?!\d)", question):
                hits.append(cell)
        elif cell.casefold() in folded:
            hits.append(cell)
    return hits


class DevStructuredR2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = load(DEST)
        cls.legacy = load(LEGACY)
        cls.splits = L.row_splits()
        cls.records = K.load_kb("full_kb")
        cls.companies = {r.company for r in cls.records}
        cls.test_companies = {r.company for r in cls.records
                              if cls.splits[r.row_id] == "test"}
        registry = json.loads((OUT / "HOLDOUT_REGISTRY_A002.json").read_text())
        cls.held_sets = [set(s) for s in
                         registry["composition_holdouts"]["held_out_sets"]]

    # ---- the defect this set exists to remove ----
    def test_detector_reproduces_the_legacy_defect(self):
        flagged = [t for t in self.legacy if quoted_gold(t)]
        self.assertEqual(len(flagged), len(self.legacy),
                         "the legacy set is known to quote gold in every question")
        self.assertEqual(len(self.legacy), 51)

    def test_no_gold_value_appears_in_its_own_question(self):
        for t in self.tasks:
            self.assertEqual(quoted_gold(t), [], t["example_id"])

    def test_no_company_named_in_a_company_returning_question(self):
        for t in self.tasks:
            if t["target_columns"] == ["company"]:
                folded = t["question"].casefold()
                for name in self.companies:
                    self.assertNotIn(name.casefold(), folded, t["example_id"])

    # ---- development anchoring ----
    def test_every_task_has_a_development_anchor(self):
        """Drawing each value from dev data is not enough: the COMBINED predicate
        must describe at least one development record, or the set is not anchored
        on held-out entities at all."""
        for t in self.tasks:
            self.assertTrue(t["dev_anchor_row_ids"], t["example_id"])
            for row_id in t["dev_anchor_row_ids"]:
                self.assertEqual(self.splits[row_id], "dev", (t["example_id"], row_id))

    def test_anchor_row_ids_recomputed_independently(self):
        by_id = {r.row_id: r for r in self.records}
        for t in self.tasks:
            expected = sorted(rid for rid, rec in by_id.items()
                              if self.splits[rid] == "dev"
                              and satisfies(rec, t["predicate"]))
            self.assertEqual(sorted(t["dev_anchor_row_ids"]), expected, t["example_id"])

    def test_anchor_field_is_unambiguous(self):
        """`anchor_entity_split` listed the splits of matching records, which reads
        as identifying the anchor and did not. It must not come back."""
        for t in self.tasks:
            self.assertNotIn("anchor_entity_split", t, t["example_id"])
            self.assertIn("matching_record_splits", t)
            self.assertIn("dev", t["matching_record_splits"], t["example_id"])

    def test_predicate_matches_the_declared_fields(self):
        for t in self.tasks:
            fields = {c["field"] for c in t["predicate"]}
            self.assertEqual(fields, set(t["fields_used"]) - {"company"}, t["example_id"])

    # ---- frozen holdouts ----
    def test_no_test_company_in_question_or_gold(self):
        for t in self.tasks:
            folded = t["question"].casefold()
            for name in self.test_companies:
                self.assertNotIn(name.casefold(), folded, t["example_id"])
            self.assertFalse(set(gold_cells(t)) & self.test_companies, t["example_id"])

    def test_no_heldout_operation_construct(self):
        for t in self.tasks:
            self.assertEqual(H.operation_families_present(t["gold_sql"]), set(),
                             t["example_id"])
            self.assertEqual(t["operation_family"], "filter", t["example_id"])

    def test_heldout_composition_excluded(self):
        for t in self.tasks:
            component = set(t["fields_used"]) - {"company"}
            for held in self.held_sets:
                self.assertFalse(held <= component, (t["example_id"], sorted(component)))

    # ---- gold integrity ----
    def test_every_gold_reexecutes_exactly(self):
        for t in self.tasks:
            result = X.run_sql(t["gold_sql"], t["scope"], db_path=DB)
            self.assertEqual({"columns": list(result.columns),
                              "rows": [list(r) for r in result.rows]},
                             t["gold_value"], t["example_id"])

    def test_no_empty_gold(self):
        for t in self.tasks:
            self.assertTrue(t["gold_value"]["rows"], t["example_id"])

    # ---- no contamination of, or by, other artifacts ----
    def test_no_collision_with_training_pool_fewshot_or_probes(self):
        training = load(OUT / "train_D_sql_v3.jsonl")
        pool = load(OUT / "STRUCTURED_TASK_POOL_v3.jsonl")
        fewshot = json.loads((OUT / "FEWSHOT_MANIFEST_v3.json").read_text())["examples"]
        probes = []
        for name in ("probe_structured_train_v3.jsonl",
                     "probe_structured_paraphrase_v3.jsonl",
                     "probe_operation_heldout_v3.jsonl",
                     "probe_composition_heldout_v3.jsonl",
                     "probe_value_exposure_v3.jsonl", "probe_no_match_v3.jsonl"):
            probes += load(OUT / name)
        sqls = {r["gold_sql"] for r in training + pool + fewshot + probes if r.get("gold_sql")}
        fps = {r.get("logical_fingerprint") for r in pool + fewshot + probes}
        questions = {r["question"] for r in training + pool + probes}
        for t in self.tasks:
            self.assertNotIn(t["gold_sql"], sqls, t["example_id"])
            self.assertNotIn(t["logical_fingerprint"], fps, t["example_id"])
            self.assertNotIn(t["question"], questions, t["example_id"])

    # ---- metadata correctness ----
    def test_split_metadata_corrected(self):
        for t in self.tasks:
            self.assertNotIn("split", t, t["example_id"])
            self.assertEqual(t["task_split"], "dev", t["example_id"])
            self.assertEqual(t["scope"], "train_dev_kb", t["example_id"])
            self.assertIn("dev_anchor_row_ids", t)

    def test_unique_example_ids(self):
        ids = [t["example_id"] for t in self.tasks]
        self.assertEqual(len(ids), len(set(ids)))

    # ---- discriminating power ----
    def test_covers_join_arity_and_both_answer_types(self):
        arities = {t["join_arity"] for t in self.tasks}
        self.assertTrue({0, 1, 2} <= arities, arities)
        types = {t["answer_type"] for t in self.tasks}
        self.assertEqual(types, {"set", "scalar"})

    def test_answers_are_not_all_singletons(self):
        sets = [t for t in self.tasks if t["answer_type"] == "set"]
        multi = [t for t in sets if len(t["gold_value"]["rows"]) > 1]
        self.assertGreater(len(multi), len(sets) // 3,
                           "a set of near-singleton answers barely improves on the legacy set")

    def test_counts_are_not_all_identical(self):
        values = {t["gold_value"]["rows"][0][0] for t in self.tasks
                  if t["answer_type"] == "scalar"}
        self.assertGreater(len(values), 3, values)

    # ---- the legacy artifact must survive untouched ----
    def test_legacy_artifact_preserved(self):
        manifest = json.loads((OUT / "EVALUATION_INPUT_MANIFEST_A002.json").read_text())
        self.assertEqual(H.sha256_file(LEGACY), manifest["sha256"]["dev_structured_v3.jsonl"])


class DevTargetsFitTheTrainer(unittest.TestCase):
    """The set is only usable if train_v3.py can encode every target."""

    @classmethod
    def setUpClass(cls):
        from transformers import AutoTokenizer
        from phase10_build_a_cpt import load_real_tokenizer
        cls.tok, _ = load_real_tokenizer()
        cls.tasks = load(DEST)

    def test_every_dev_target_encodes_for_both_arm_types(self):
        from training_tokens_v3 import encode_chat, MAX_SEQUENCE_LENGTH
        from phase11_build_b_facts import CLOSED_BOOK_SYSTEM
        from phase14_build_d_sql import SQL_SYSTEM
        from phase13_build_c_answers import render_answer
        for sql_arm in (False, True):
            for t in self.tasks:
                answer = t["gold_sql"] if sql_arm else render_answer(
                    {"answer_type": t["answer_type"], "train_kb_gold": t["gold_value"],
                     "task_id": t["example_id"]})
                encoded = encode_chat(self.tok, [
                    {"role": "system", "content": SQL_SYSTEM if sql_arm else CLOSED_BOOK_SYSTEM},
                    {"role": "user", "content": t["question"]},
                    {"role": "assistant", "content": answer}])
                self.assertLessEqual(len(encoded["input_ids"]), MAX_SEQUENCE_LENGTH,
                                     t["example_id"])

    def test_counts_render_as_counts_not_company_lists(self):
        from phase13_build_c_answers import render_answer
        for t in self.tasks:
            if t["answer_type"] == "scalar":
                text = render_answer({"answer_type": "scalar",
                                      "train_kb_gold": t["gold_value"],
                                      "task_id": t["example_id"]})
                self.assertTrue(text.startswith("The answer is "), text)
                self.assertNotIn("The companies are", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
