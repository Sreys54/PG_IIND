"""
Week 8 advisor review, Block A tests.

  - A1: the advisor's check on the stored grid -- for served EVs, EV2Gym's
    battery-level satisfaction s equals 1 - (R/C)(1 - f); aggregated over
    each arm's 100 long-dwell cases, the observed mean s matches
    1 - (sum R / sum C)(1 - sum e / sum R) within 0.5 points;
  - A3: on every row of the economics registry (results/economics_cop.csv),
    margin = E (p - c) within 0.5% using the row's own p and c; on every
    Table IV source row (results/dwell_c2_growth_options.csv), margin =
    E x 584.24 within 0.5%; on every per-case DC row of the Week 8 registry
    extras, DNS = 1 - E / E_offered within 0.5 points;
  - A2: the ratio-of-totals bootstrap equals the pooled ratio at its point
    estimate, and the three numbers the advisor recomputed are reproduced.
The A1 check reads experiments/phase4_review/A/A_cases.csv (skipped before
the re-simulation has been merged).

Run: python -m unittest ev2gym_thesis.tests.test_review_A
"""
import os
import unittest

import numpy as np
import pandas as pd

from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio

A_CASES = "experiments/phase4_review/A/A_cases.csv"
UNIT = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH


@unittest.skipUnless(os.path.exists(A_CASES), "A re-simulation not merged yet")
class TestAdvisorSatisfactionCheck(unittest.TestCase):
    def test_s_equals_one_minus_r_over_c_times_one_minus_f(self):
        c = pd.read_csv(A_CASES)
        for (regime, arm), g in c.groupby(["regime", "algorithm"]):
            pred = 1 - (g.sum_requested_kwh.sum() / g.sum_battery_kwh.sum()) * (
                1 - g.sum_delivered_kwh.sum() / g.sum_requested_kwh.sum())
            obs = g.sum_s_ev2gym.sum() / g.n_served_rec.sum()
            self.assertLess(abs(pred - obs), 0.005, (regime, arm, pred, obs))


class TestMarginAndDnsConsistency(unittest.TestCase):
    def test_economics_registry_margin(self):
        e = pd.read_csv("results/economics_cop.csv")
        expected = e.total_energy_charged_kwh * (e.retail_tariff_cop_per_kwh - e.energy_purchase_cost_cop_per_kwh)
        self.assertTrue((np.abs(e.gross_margin_cop - expected) <= 0.005 * np.abs(expected) + 1e-9).all())

    def test_table_iv_source_margin(self):
        o = pd.read_csv("results/dwell_c2_growth_options.csv")
        expected = o.total_energy_charged_mean * UNIT
        self.assertTrue((np.abs(o.gross_margin_cop_mean - expected) <= 0.005 * expected).all())

    def test_review_registry_per_case_dns(self):
        paths = [p for p in ("experiments/phase4_review/C/c1_cases.csv", "experiments/phase4_review/gate1/gate1_cases.csv")
                 if os.path.exists(p)]
        if not paths:
            self.skipTest("no Week 8 DC cases yet")
        for p in paths:
            c = pd.read_csv(p)
            c = c[c.arrival_model == "station_poisson"]
            self.assertTrue((np.abs(c.dns_exact - (1 - c.energy_delivered_kwh / c.energy_offered_kwh)) <= 0.005).all(), p)
            self.assertTrue((np.abs(c.gross_margin_cop - c.energy_delivered_kwh * UNIT)
                             <= 0.005 * c.energy_delivered_kwh * UNIT + 1e-9).all(), p)


class TestAggregationRule(unittest.TestCase):
    def test_ratio_of_totals_point_estimate(self):
        rng = np.random.default_rng(3)
        num, den = rng.random(100), 1 + rng.random(100)
        r = cluster_bootstrap_ratio(num, den, np.repeat(np.arange(50), 2), n_bootstrap=500)
        self.assertAlmostEqual(r["point_estimate"], num.sum() / den.sum())
        self.assertEqual(r["n_clusters"], 50)

    def test_advisor_numbers_reproduced(self):
        m = pd.read_csv("results/master_results.csv", low_memory=False)
        g = m[(m.analysis_row == True) & (m.config_name == "station_v0_bogota")]
        te = g.pivot_table(index=["seed", "eval_day"], columns="algorithm", values="tracking_error")
        red_ratio_of_totals = 1 - te.RoundRobin.sum() / te.ChargeAsFastAsPossible.sum()
        red_mean_of_ratios = (1 - te.RoundRobin / te.ChargeAsFastAsPossible).mean()
        self.assertAlmostEqual(red_mean_of_ratios, 0.755, delta=0.0005)      # the text's 75.5%
        self.assertAlmostEqual(red_ratio_of_totals, 0.7586, delta=0.0005)    # the advisor's 75.8%


if __name__ == "__main__":
    unittest.main()
