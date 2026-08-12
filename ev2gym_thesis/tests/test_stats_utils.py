"""
Tests for ev2gym_thesis.stats_utils, verified against synthetic fixtures
with analytically known results -- deliberately NOT against
results/master_results.csv (still being backfilled as of writing; see
00_lab_log.md 2026-08-12). These must pass independently of whether the
backfill has finished.

Run with:
    PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_stats_utils -v
"""
import unittest

import numpy as np

from ev2gym_thesis.stats_utils import mean_ci, paired_bootstrap_ci


class TestMeanCI(unittest.TestCase):
    def test_known_closed_form(self):
        # values = [10,12,14,16,18]: mean=14, sample std(ddof=1)=sqrt(10),
        # sem=sqrt(10)/sqrt(5)=sqrt(2), z(0.95)=1.960
        # -> half-width = 1.960*sqrt(2) = 2.771857...
        values = [10, 12, 14, 16, 18]
        m, lo, hi = mean_ci(values, ci=0.95)
        self.assertAlmostEqual(m, 14.0, delta=1e-9)
        half_width = 1.960 * np.sqrt(2)
        self.assertAlmostEqual(lo, 14.0 - half_width, delta=1e-3)
        self.assertAlmostEqual(hi, 14.0 + half_width, delta=1e-3)

    def test_zero_variance_collapses_to_point(self):
        m, lo, hi = mean_ci([5, 5, 5, 5, 5], ci=0.95)
        self.assertEqual((m, lo, hi), (5.0, 5.0, 5.0))

    def test_single_sample_returns_point_interval(self):
        m, lo, hi = mean_ci([7.0], ci=0.95)
        self.assertEqual((m, lo, hi), (7.0, 7.0, 7.0))

    def test_unsupported_ci_level_raises(self):
        with self.assertRaises(ValueError):
            mean_ci([1, 2, 3], ci=0.5)


class TestPairedBootstrapCI(unittest.TestCase):
    def test_exact_zero_width_for_constant_offset(self):
        """b = a + 3 exactly, for varying a. If pairing were broken (a and b
        resampled independently instead of by shared index), this would NOT
        collapse to a zero-width interval, since a itself varies (1..5) --
        this is the discriminating test for correct pairing."""
        values_a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        values_b = values_a + 3.0
        result = paired_bootstrap_ci(values_a, values_b, n_bootstrap=2000,
                                      seed=0, statistic="diff")
        self.assertAlmostEqual(result["point_estimate"], 3.0, delta=1e-9)
        self.assertAlmostEqual(result["ci_low"], 3.0, delta=1e-9)
        self.assertAlmostEqual(result["ci_high"], 3.0, delta=1e-9)
        self.assertEqual(result["n_pairs"], 5)

    def test_exact_zero_width_for_constant_percentage(self):
        """b = 1.1*a with constant a -> pct diff = exactly 10% for every
        pair and every resample."""
        values_a = np.array([10.0] * 20)
        values_b = np.array([11.0] * 20)
        result = paired_bootstrap_ci(values_a, values_b, n_bootstrap=2000,
                                      seed=1, statistic="pct")
        self.assertAlmostEqual(result["point_estimate"], 10.0, delta=1e-9)
        self.assertAlmostEqual(result["ci_low"], 10.0, delta=1e-9)
        self.assertAlmostEqual(result["ci_high"], 10.0, delta=1e-9)

    def test_point_estimate_matches_manual_mean_diff(self):
        rng = np.random.default_rng(42)
        values_a = rng.normal(loc=100, scale=10, size=200)
        values_b = values_a + rng.normal(loc=5, scale=2, size=200)
        result = paired_bootstrap_ci(values_a, values_b, n_bootstrap=3000, seed=2)
        expected_point = float(np.mean(values_b - values_a))
        self.assertAlmostEqual(result["point_estimate"], expected_point, delta=1e-9)
        self.assertLessEqual(result["ci_low"], result["point_estimate"])
        self.assertGreaterEqual(result["ci_high"], result["point_estimate"])
        # true generating offset is 5 -- CI should comfortably contain it
        # with 200 pairs and a mean offset of 5 vs a per-pair sd of ~2
        self.assertLess(result["ci_low"], 5.0)
        self.assertGreater(result["ci_high"], 5.0)

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            paired_bootstrap_ci([1, 2, 3], [1, 2])

    def test_unknown_statistic_raises(self):
        with self.assertRaises(ValueError):
            paired_bootstrap_ci([1, 2], [3, 4], statistic="bogus", n_bootstrap=10)


if __name__ == "__main__":
    unittest.main()
