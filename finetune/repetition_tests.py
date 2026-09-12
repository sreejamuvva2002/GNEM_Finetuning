"""Regression coverage for BD partial-cycle repetition.

History: repetition originally cycled from index 0, so every extra copy was
join_arity 1. Stratifying by arity fixed that axis but left the task-kind axis
badly skewed -- count tasks sort before filter tasks, so within arity 0 the extra
copies were 39% count against a 9% source share, and no filter task was ever
repeated. Both axes are now stratified jointly, and within a stratum the order is
a keyed digest rather than a lexicographic prefix.
"""
import collections
import json
import unittest
from pathlib import Path

from phase16_build_bd import repeat_to_budget, stratum_key, stratum_order, task_kind

ROOT = Path(__file__).resolve().parent.parent
MIXTURES = ('train_BD_controlled_v3.jsonl', 'train_D_repeat_budgetmatched_v3.jsonl')


# 120 items x 10 tokens = 1200 per complete cycle. A budget of 1500 leaves a
# 300-token residual (30 whole examples) to distribute; 1200 exactly would leave
# none and would test nothing.
CYCLE = 1200
BUDGET = 1500


def synthetic():
    """Two kinds inside one arity, so an arity-only sampler cannot pass."""
    rows = []
    for arity, kind, n in ((0, 'count', 30), (0, 'filter', 50), (1, 'child', 20), (2, 'composition', 20)):
        for i in range(n):
            rows.append({'example_id': f'{kind}-{arity}-{i:03d}',
                         'task_id': f'D_v3_{kind}_x_{i:05d}',
                         'join_arity': arity, '_completion_tokens': 10})
    return rows


class Repetition(unittest.TestCase):

    def test_every_source_and_every_complete_cycle_retained(self):
        rows = synthetic()
        out, diag = repeat_to_budget(rows, BUDGET)
        self.assertEqual({r['source_example_id'] for r in out}, {r['example_id'] for r in rows})
        self.assertEqual(len({r['example_id'] for r in out}), len(out))
        counts = collections.Counter(r['source_example_id'] for r in out)
        self.assertGreaterEqual(min(counts.values()), diag['full_cycles'])

    def test_partial_cycle_balanced_jointly_across_arity_and_kind(self):
        rows = synthetic()
        out, diag = repeat_to_budget(rows, BUDGET)
        counts = collections.Counter(r['source_example_id'] for r in out)
        base = min(counts.values())
        extras = [k for k, v in counts.items() if v > base]
        by = collections.Counter(k.rsplit('-', 2)[0] for k in extras)
        total = sum(by.values())
        for kind, n in (('count', 30), ('filter', 50), ('child', 20), ('composition', 20)):
            self.assertAlmostEqual(by[kind] / total, n / 120, delta=0.05, msg=kind)

    def test_arity_alone_would_not_have_caught_the_kind_skew(self):
        """A sampler balanced on arity but ordered lexicographically inside it
        gives arity 0 entirely to `count`. Assert the real sampler does not."""
        rows = synthetic()
        out, _ = repeat_to_budget(rows, BUDGET)
        counts = collections.Counter(r['source_example_id'] for r in out)
        base = min(counts.values())
        extras = [k for k, v in counts.items() if v > base]
        arity0 = [k for k in extras if k.split('-')[1] == '0']
        kinds = {k.rsplit('-', 2)[0] for k in arity0}
        self.assertIn('filter', kinds, 'filter tasks must be repeatable')
        self.assertIn('count', kinds)

    def test_within_stratum_order_is_not_lexicographic(self):
        rows = synthetic()
        members = [r for r in rows if stratum_key(r) == ('structured', '0', 'filter')]
        ordered = [r['example_id'] for r in stratum_order(members)]
        lexicographic = sorted(r['example_id'] for r in members)
        self.assertNotEqual(ordered, lexicographic)
        self.assertEqual(sorted(ordered), lexicographic, 'ordering must be a permutation')

    def test_within_stratum_order_is_deterministic(self):
        rows = synthetic()
        members = [r for r in rows if stratum_key(r) == ('structured', '0', 'filter')]
        self.assertEqual([r['example_id'] for r in stratum_order(members)],
                         [r['example_id'] for r in stratum_order(list(reversed(members)))])

    def test_diagnostics_report_deviation_and_rounding(self):
        out, diag = repeat_to_budget(synthetic(), CYCLE + 5)
        self.assertIn('strata', diag)
        self.assertGreaterEqual(diag['whole_example_overshoot'], 0)
        self.assertIn('rounding_note', diag)
        for key, d in diag['strata'].items():
            self.assertIn('token_deviation', d, key)
            self.assertIn('source_token_share', d, key)

    def test_factual_items_stratify_by_attribute(self):
        self.assertEqual(stratum_key({'example_id': 'B_x', 'attribute': 'category'}),
                         ('factual', 'category'))
        self.assertEqual(stratum_key({'example_id': 'D_x', 'task_id': 'D_v3_count_a_00001',
                                      'join_arity': 0}), ('structured', '0', 'count'))
        self.assertEqual(task_kind({'task_id': 'D_v3_composition_a_00001'}), 'composition')

    def test_rejects_degenerate_sources(self):
        with self.assertRaises(Exception):
            repeat_to_budget([], 100)
        with self.assertRaises(Exception):
            repeat_to_budget([{'example_id': 'a', '_completion_tokens': 0}], 100)

    # ---- committed mixtures ----
    def test_committed_mixtures_cover_every_arity_and_kind(self):
        for name in MIXTURES:
            rows = [json.loads(l) for l in (ROOT / 'datasets_v3' / name).read_text().splitlines()]
            d = [r for r in rows if 'join_arity' in r]
            counts = collections.Counter(r.get('source_example_id', r['example_id']) for r in d)
            base = min(counts.values())
            repeated = [r for r in d if counts[r.get('source_example_id', r['example_id'])] > base]
            self.assertEqual({r['join_arity'] for r in repeated}, {0, 1, 2}, name)
            kinds = {task_kind(r) for r in repeated}
            self.assertIn('filter', kinds, f'{name}: filter tasks still never repeated')
            self.assertIn('count', kinds, name)
            self.assertIn('composition', kinds, name)

    def test_committed_mixtures_retain_every_source_exactly(self):
        d_ids = {json.loads(l)['example_id']
                 for l in (ROOT / 'datasets_v3/train_D_sql_v3.jsonl').read_text().splitlines()}
        b_ids = {json.loads(l)['example_id']
                 for l in (ROOT / 'datasets_v3/train_B_facts_v3.jsonl').read_text().splitlines()}
        for name, expected in (('train_BD_controlled_v3.jsonl', b_ids | d_ids),
                               ('train_D_repeat_budgetmatched_v3.jsonl', d_ids)):
            rows = [json.loads(l) for l in (ROOT / 'datasets_v3' / name).read_text().splitlines()]
            self.assertEqual({r.get('source_example_id', r['example_id']) for r in rows}, expected, name)
            self.assertEqual(len({r['example_id'] for r in rows}), len(rows), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
