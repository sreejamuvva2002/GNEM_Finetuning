"""Rejection coverage for the final-training release gate.

The gate is the only thing standing between `train_v3.py --variant X --seed N`
and 18 GPU runs, and it previously accepted any file with `approved: true` and an
EMPTY sha256 map. Every rejection path below is asserted, and no test ever writes
an approved release into the repository -- the release path is injected.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "finetune"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("train_v3", ROOT / "finetune/train_v3.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)


PROPOSAL = ROOT / T.PROPOSED_SCHEDULE
BENCHMARK = ROOT / T.Q42_BENCHMARK


def approval_file(directory, *, approved=True, benchmark_sha=None, raw=None):
    """Write a SYNTHETIC Q42 approval into a temp dir.

    Never written into the repository: a fabricated approval at the real path
    would unlock final training. Tests inject it through approval_path.
    """
    path = Path(directory) / "Q42_HUMAN_APPROVAL_A002.json"
    if raw is not None:
        path.write_text(raw)
        return path
    path.write_text(json.dumps({
        "approved": approved,
        "benchmark_sha256": benchmark_sha if benchmark_sha is not None else T.sha(BENCHMARK),
        "note": "synthetic test fixture; not a real adjudication",
    }))
    return path


def proposed_pairs():
    schedule = json.loads(PROPOSAL.read_text())["run_schedule"]
    return [{"variant": e["variant"], "seed": e["seed"]} for e in schedule]


def valid_release():
    """A release that should pass every check, built from the real tree."""
    return {
        "approved": True,
        "q42_approval": "approved",
        "sha256": {name: T.sha(ROOT / name) for name in T.REQUIRED_RELEASE_INPUTS},
        "run_schedule_source": T.PROPOSED_SCHEDULE,
        "run_schedule_sha256": T.sha(PROPOSAL),
        "run_schedule": proposed_pairs(),
    }


def mutate_seed(schedule, variant, old, new):
    out = [dict(e) for e in schedule]
    for entry in out:
        if entry["variant"] == variant and entry["seed"] == old:
            entry["seed"] = new
    return out


class ReleaseGate(unittest.TestCase):
    def setUpClass_noop(self):
        pass

    def check(self, release, variant="B_facts", seed=61, *, pin_approval=True, **approval):
        """Run the real gate against a temp release plus a SYNTHETIC approval.

        The approval lives only in the temp dir, so the release must pin its temp
        digest; `pin_approval=False` lets a test supply or omit that pin itself.
        """
        with tempfile.TemporaryDirectory() as d:
            ap = approval.pop("approval_path", None) or approval_file(d, **approval)
            if pin_approval and isinstance(release.get("sha256"), dict):
                release = dict(release, sha256=dict(release["sha256"]))
                release["sha256"][T.Q42_APPROVAL] = T.sha(ap)
            path = Path(d) / "release.json"
            path.write_text(json.dumps(release))
            T.check_release(variant, seed, release_path=path, approval_path=ap)

    # ---- the repository must currently be un-released ----
    def test_no_release_file_in_repository(self):
        self.assertFalse(T.RELEASE.exists(),
                         "an approved release exists; final training would be unblocked")

    def test_missing_release_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                T.check_release("B_facts", 61, release_path=Path(d) / "absent.json")

    # ---- a fully valid release passes ----
    def test_valid_release_accepted(self):
        self.check(valid_release())

    def test_valid_release_covers_all_eighteen_runs(self):
        schedule = valid_release()["run_schedule"]
        self.assertEqual(len(schedule), T.TOTAL_RUNS)
        for entry in schedule:
            self.check(valid_release(), entry["variant"], entry["seed"])

    # ---- approval ----
    def test_unapproved_refused(self):
        for value in (False, None, "yes", 1):
            r = valid_release(); r["approved"] = value
            with self.assertRaises(RuntimeError, msg=repr(value)):
                self.check(r)

    def test_q42_not_approved_refused(self):
        for value in ("pending", None, "", "PENDING_BY_USER"):
            r = valid_release(); r["q42_approval"] = value
            with self.assertRaises(RuntimeError, msg=repr(value)):
                self.check(r)

    # ---- the vacuous-freeze defect ----
    def test_empty_hash_map_refused(self):
        for value in ({}, None, [], "none"):
            r = valid_release(); r["sha256"] = value
            with self.assertRaises(RuntimeError, msg=repr(value)):
                self.check(r)

    def test_partial_hash_map_refused(self):
        for omitted in ("datasets_v3/train_B_facts_v3.jsonl",
                        "finetune/templates/qwen_a002.jinja",
                        "kb/GNEM_Final_Combined_Dataset.xlsx",
                        "datasets_v3/dev_structured_r2_v3.jsonl"):
            r = valid_release(); r["sha256"].pop(omitted)
            with self.assertRaises(RuntimeError, msg=omitted):
                self.check(r)

    def test_drifted_input_refused(self):
        r = valid_release()
        r["sha256"]["datasets_v3/train_B_facts_v3.jsonl"] = "0" * 64
        with self.assertRaises(RuntimeError):
            self.check(r)

    def test_pinned_but_missing_file_refused(self):
        r = valid_release()
        r["sha256"]["datasets_v3/does_not_exist_v3.jsonl"] = "0" * 64
        with self.assertRaises(RuntimeError):
            self.check(r)

    # ---- seed pre-registration ----
    def test_missing_schedule_refused(self):
        for value in (None, [], {}, "later"):
            r = valid_release(); r["run_schedule"] = value
            with self.assertRaises(RuntimeError, msg=repr(value)):
                self.check(r)

    def test_unscheduled_pair_refused(self):
        with self.assertRaises(RuntimeError):
            self.check(valid_release(), "B_facts", 99)
        with self.assertRaises(RuntimeError):
            self.check(valid_release(), "A_cpt", 62)

    def test_duplicate_pairs_refused(self):
        r = valid_release()
        r["run_schedule"][1] = dict(r["run_schedule"][0])
        with self.assertRaises(RuntimeError):
            self.check(r)

    def test_unknown_variant_refused(self):
        r = valid_release()
        r["run_schedule"][0] = {"variant": "E_mystery", "seed": 61}
        with self.assertRaises(RuntimeError):
            self.check(r)

    def test_primary_arm_below_three_seeds_refused(self):
        for arm in T.PRIMARY_ARMS:
            r = valid_release()
            keep = [e for e in r["run_schedule"] if e["variant"] != arm]
            r["run_schedule"] = keep + [{"variant": arm, "seed": 61},
                                        {"variant": arm, "seed": 62},
                                        {"variant": "BC", "seed": 62}]
            with self.assertRaises(RuntimeError, msg=arm):
                self.check(r, arm, 61)

    def test_wrong_total_run_count_refused(self):
        r = valid_release()
        r["run_schedule"] = r["run_schedule"] + [{"variant": "BC", "seed": 62}]
        with self.assertRaises(RuntimeError):
            self.check(r)

    # ---- Q42 approval must be EXTERNAL EVIDENCE, not a self-assertion ----
    def test_release_string_alone_does_not_unlock_training(self):
        """The defect this gate exists to close: flipping approved/q42_approval
        in a release once unlocked all 18 runs with no external evidence."""
        with tempfile.TemporaryDirectory() as d:
            rel = Path(d) / "release.json"
            rel.write_text(json.dumps(valid_release()))
            missing = Path(d) / "absent_approval.json"
            with self.assertRaises(RuntimeError) as caught:
                T.check_release("B_facts", 61, release_path=rel, approval_path=missing)
            self.assertIn("Q42", str(caught.exception))

    def test_approval_artifact_must_be_pinned_by_the_release(self):
        r = valid_release()
        r["sha256"].pop(T.Q42_APPROVAL, None)
        with self.assertRaises(RuntimeError):
            self.check(r, pin_approval=False)

    def test_benchmark_must_be_pinned_by_the_release(self):
        r = valid_release()
        r["sha256"].pop(T.Q42_BENCHMARK)
        with self.assertRaises(RuntimeError):
            self.check(r)

    def test_approval_pin_must_match_the_file(self):
        r = valid_release()
        r["sha256"][T.Q42_APPROVAL] = "0" * 64
        with self.assertRaises(RuntimeError):
            self.check(r, pin_approval=False)

    def test_unapproved_or_malformed_evidence_refused(self):
        for kwargs in ({"approved": False}, {"approved": None}, {"approved": "yes"},
                       {"approved": 1}):
            with self.assertRaises(RuntimeError, msg=repr(kwargs)):
                self.check(valid_release(), **kwargs)

    def test_evidence_must_be_a_json_object(self):
        for raw in ("not json at all", "[]", '"approved"', "null"):
            with self.assertRaises(RuntimeError, msg=raw):
                self.check(valid_release(), raw=raw)

    def test_stale_approval_naming_other_benchmark_bytes_refused(self):
        """An approval of a previous Q42 set must not certify the current one."""
        with self.assertRaises(RuntimeError):
            self.check(valid_release(), benchmark_sha="1" * 64)

    def test_valid_external_evidence_accepted(self):
        self.check(valid_release())

    def test_training_gate_is_no_weaker_than_the_evaluation_gate(self):
        """final_eval_v3.authorize() requires the same artifact; so must training."""
        train = Path(ROOT / "finetune/train_v3.py").read_text()
        self.assertIn("Q42_HUMAN_APPROVAL_A002.json", train)
        self.assertIn(T.Q42_BENCHMARK, T.REQUIRED_RELEASE_INPUTS)

    def test_no_approval_artifact_exists_in_the_repository(self):
        self.assertFalse((ROOT / T.Q42_APPROVAL).exists(),
                         "a Q42 approval artifact exists; final training would be unblocked")

    # ---- the pre-registered schedule must be honoured exactly ----
    def test_schedule_must_match_the_preregistered_proposal(self):
        """Counts and minimums alone let a release run undeclared seeds."""
        r = valid_release()
        r["run_schedule"] = mutate_seed(r["run_schedule"], "B_facts", 62, 999)
        with self.assertRaises(RuntimeError):
            self.check(r, "B_facts", 999)

    def test_schedule_source_required(self):
        for value in (None, "", "somewhere/else.json"):
            r = valid_release(); r["run_schedule_source"] = value
            with self.assertRaises(RuntimeError, msg=repr(value)):
                self.check(r)

    def test_schedule_hash_must_match(self):
        r = valid_release(); r["run_schedule_sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            self.check(r)

    def test_dropping_a_preregistered_run_refused(self):
        r = valid_release()
        dropped = [e for e in r["run_schedule"] if not (e["variant"] == "D_sql" and e["seed"] == 63)]
        r["run_schedule"] = dropped + [{"variant": "D_sql", "seed": 64}]
        with self.assertRaises(RuntimeError):
            self.check(r, "D_sql", 64)

    # ---- seed typing and range ----
    def test_non_integer_or_out_of_range_seeds_refused(self):
        for bad in (True, False, -5, 2 ** 40, "61", 61.0, None):
            r = valid_release()
            r["run_schedule"] = mutate_seed(r["run_schedule"], "C_answers", 61, bad)
            with self.assertRaises(RuntimeError, msg=repr(bad)):
                self.check(r, "C_answers", bad)

    def test_requested_seed_itself_must_be_a_valid_integer(self):
        for bad in (True, -1, 2 ** 32, "61"):
            with self.assertRaises(RuntimeError, msg=repr(bad)):
                self.check(valid_release(), "B_facts", bad)

    def test_valid_seed_helper_boundaries(self):
        self.assertTrue(T.valid_seed(0))
        self.assertTrue(T.valid_seed(2 ** 32 - 1))
        self.assertFalse(T.valid_seed(2 ** 32))
        self.assertFalse(T.valid_seed(-1))
        self.assertFalse(T.valid_seed(True))
        self.assertFalse(T.valid_seed(1.0))

    # ---- the proposal artifact itself ----
    def test_proposal_is_not_an_approved_release(self):
        doc = json.loads(PROPOSAL.read_text())
        self.assertNotIn("approved", doc)
        self.assertIn("NOT APPROVED", doc["status"])
        self.assertEqual(len(doc["run_schedule"]), T.TOTAL_RUNS)
        for entry in doc["run_schedule"]:
            self.assertTrue(T.valid_seed(entry["seed"]), entry)

    # ---- claim status matches the frozen Phase 0 record ----
    def test_arm_partition_matches_provenance(self):
        self.assertEqual(set(T.PRIMARY_ARMS) | set(T.DIAGNOSTIC_ARMS), set(T.FILES))
        self.assertFalse(set(T.PRIMARY_ARMS) & set(T.DIAGNOSTIC_ARMS))
        self.assertEqual(len(T.PRIMARY_ARMS) * 3 + len(T.DIAGNOSTIC_ARMS), T.TOTAL_RUNS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
