"""Regression coverage for the independently observed zero-variance effect bug."""
import json
import math
import unittest
import eval_stats_v3 as S

class PairedEffectTests(unittest.TestCase):
    def test_constant_effects_preserve_direction_without_false_zero(self):
        for delta in (-1.0, 0.0, 1.0):
            with self.subTest(delta=delta):
                diffs = [delta] * 3
                payload = {'raw_mean_difference': S.mean(diffs),
                           'standardized_effect': S.effect_size(diffs)}
                restored = json.loads(json.dumps(payload, allow_nan=False))
                self.assertEqual(restored['raw_mean_difference'], delta)
                self.assertIsNone(restored['standardized_effect'])

    def test_known_sample_standard_deviation(self):
        # These samples have mean +/-2 and sample SD exactly 1.
        self.assertAlmostEqual(S.effect_size([1, 2, 3]), 2.0)
        self.assertAlmostEqual(S.effect_size([-3, -2, -1]), -2.0)
        self.assertEqual(S.effect_size([-1, 0, 1]), 0.0)

    def test_positive_rescaling_does_not_change_standardized_effect(self):
        self.assertAlmostEqual(S.effect_size([0.1, 0.2, 0.3]),
                               S.effect_size([1, 2, 3]))
        self.assertAlmostEqual(S.effect_size(iter([1, 2, 3])), 2.0)

    def test_undersized_and_nonfinite_samples_refused(self):
        for diffs in ([], [1], [0, math.nan], [0, math.inf], [-math.inf, 1]):
            with self.subTest(diffs=diffs):
                with self.assertRaises(S.StatsUsageError):
                    S.effect_size(diffs)

if __name__ == '__main__':
    unittest.main(verbosity=2)
