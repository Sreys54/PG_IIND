"""
Week 8 advisor review, Block C tests (brief C deliverables): the safety
layer is never exceeded by any arm that has it; Oracle-E delivers at least
the energy of every causal arm on every case; MPC-soft is never infeasible;
and the A3 consistency rule on every Block C case (margin = E (p - c)
within 0.5%, DNS = 1 - E / E_offered within 0.5 points).

The simulation-level checks run on two cases each (fast); the result-level
checks read experiments/phase4_review/C/c1_cases.csv when it exists (they
are skipped before the C1 grid has been run).

Run: python -m unittest ev2gym_thesis.tests.test_review_C
"""
import os
import unittest

import numpy as np
import pandas as pd

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.mpc import operator_mpc as om
from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from scripts import review_dc

C1 = "experiments/phase4_review/C/c1_cases.csv"
TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "w8_test_c")
CAUSAL = ["AFAP", "PS", "FIX12.5", "RR-TA", "Random+S", "MPC-soft-est"]
BUDGET_KW = 0.999 * 100.0
# FIX12.5 uses the full 100 kW (8 x 12.5 kW, what an installer would set), while every
# projected arm and Oracle-E keep the common 0.999 margin; the dominance check allows
# that 0.1 kW margin over the day (0.1 kW x 96 steps x 0.25 h = 2.4 kWh) for FIX12.5 only.
FIX_TOL_KWH = 0.001 * 100.0 * 96 * 0.25


class TestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        review_dc.DAY_CONFIG_DIR = TMP
        cls.cfg = rc.write_config(1.6, out_dir=TMP)

    def test_safety_layer_never_exceeded_and_oracle_upper_bound(self):
        for seed in (1, 7):
            energy = {}
            for arm in ["PS", "RR+S", "Random+S", "RR-TA", "MPC-soft", "MPC-soft-est", "Oracle-E", "FIX12.5"] + ["AFAP"]:
                row, ex = review_dc.run_case(arm, self.cfg, seed, (2022, 1, 17), "station")
                energy[arm] = ex["energy_delivered_kwh"]
                if arm != "AFAP":
                    cap = 100.0 if arm == "FIX12.5" else BUDGET_KW
                    self.assertLessEqual(ex["peak_station_kw"], cap + 1e-4, (arm, seed))
                    self.assertEqual(ex["overload_kwh"], 0.0, (arm, seed))
            for arm in CAUSAL:
                if arm != "AFAP":  # AFAP ignores the transformer, so it is not bounded by a 100 kW oracle
                    tol = FIX_TOL_KWH if arm == "FIX12.5" else 1e-3
                    self.assertGreaterEqual(energy["Oracle-E"] + tol, energy[arm], (arm, seed))

    def test_mpc_soft_never_infeasible(self):
        om.STATS.update({"solves": 0, "non_optimal": 0})
        for arm in ("MPC-soft", "MPC-soft-est"):
            review_dc.run_case(arm, self.cfg, 2, (2022, 3, 5), "station")
        self.assertGreater(om.STATS["solves"], 0)
        self.assertEqual(om.STATS["non_optimal"], 0)


@unittest.skipUnless(os.path.exists(C1), "C1 grid not run yet")
class TestC1Results(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = pd.read_csv(C1)

    def test_safety_layer_never_exceeded(self):
        # arms with the safety layer, or transformer-aware by design; AFAP and EV2Gym's RR ignore the rating
        g = self.c[(self.c.safety_layer == "proportional") |
                   self.c.algorithm.isin(["RR-TA", "MPC-soft", "MPC-soft-est", "Oracle-E"])]
        self.assertTrue((g.peak_station_kw <= BUDGET_KW + 1e-4).all())
        self.assertTrue((self.c[self.c.algorithm == "FIX12.5"].peak_station_kw <= 100.0 + 1e-4).all())
        self.assertTrue((g.overload_kwh == 0).all())

    def test_oracle_e_dominates_causal_arms(self):
        p = self.c.pivot_table(index=["config_name", "seed", "eval_day"], columns="algorithm",
                               values="energy_delivered_kwh")
        for arm in [a for a in CAUSAL if a != "AFAP" and a in p.columns]:
            tol = FIX_TOL_KWH if arm == "FIX12.5" else 1e-3
            self.assertTrue((p["Oracle-E"] + tol >= p[arm]).all(), arm)

    def test_margin_and_dns_consistency(self):
        unit = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
        c = self.c
        self.assertTrue((np.abs(c.gross_margin_cop - c.energy_delivered_kwh * unit)
                         <= 0.005 * np.abs(c.energy_delivered_kwh * unit) + 1e-9).all())
        self.assertTrue((np.abs(c.dns_exact - (1 - c.energy_delivered_kwh / c.energy_offered_kwh)) <= 0.005).all())


TD3 = "experiments/phase4_review/C/td3_cases.csv"
SEL = "results/review_td3_safe_selection.json"


@unittest.skipUnless(os.path.exists(TD3) and os.path.exists(SEL) and os.path.exists(C1), "C3 not run yet")
class TestC3Results(unittest.TestCase):
    """C3: the selection follows the pre-registered rules (computed from each
    seed's validation log, never typed), the test grid is complete, TD3_safe
    never exceeds the safety budget, and Oracle-E dominates it."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.sel = json.load(open(SEL))
        t = pd.read_csv(TD3)
        cls.t_all = t
        cls.t = t[t.algorithm.str.match(r"^TD3_safe_ts\d+$")]  # C3 seeds; long-budget arms checked below

    def test_selection_rules(self):
        from ev2gym_thesis.rl import config_safe as cfg
        best = None
        for seed, info in self.sel["seeds"].items():
            v = pd.read_csv(f"experiments/phase2_algorithms/models/TD3_safe_dc42_ts{seed}/validation.csv")
            conv = int(np.flatnonzero(v.timesteps.values == info["convergence_step"])[0])
            fi = cfg.final_index(v.criterion_value.values, conv, lower_is_better=False)
            self.assertEqual(int(v.timesteps.iloc[fi]), info["final_step"])
            self.assertTrue(os.path.exists(info["checkpoint"]))
            self.assertTrue(os.path.exists(info["checkpoint"].replace(".zip", "_vecnormalize.pkl")))
            if best is None or info["validation_energy_kwh"] > self.sel["seeds"][best]["validation_energy_kwh"]:
                best = seed
        self.assertEqual(str(self.sel["carried_model"]["train_seed"]), str(best))

    def test_grid_complete_and_safe(self):
        self.assertEqual(len(self.t), 100 * 3 * len(self.sel["seeds"]))
        self.assertEqual(self.t.run_id.nunique(), len(self.t))
        self.assertTrue((self.t.safety_layer == "proportional").all())
        self.assertTrue((self.t.peak_station_kw <= BUDGET_KW + 1e-4).all())
        self.assertTrue((self.t.overload_kwh == 0).all())
        self.assertTrue((self.t_all.peak_station_kw <= BUDGET_KW + 1e-4).all())  # long-budget arms too

    def test_oracle_e_dominates_td3_safe(self):
        c1 = pd.read_csv(C1)
        o = c1[c1.algorithm == "Oracle-E"].set_index(["config_name", "seed", "eval_day"]).energy_delivered_kwh
        for arm, g in self.t_all.groupby("algorithm"):
            x = g.set_index(["config_name", "seed", "eval_day"]).energy_delivered_kwh
            self.assertTrue((o.loc[x.index] + 1e-3 >= x).all(), arm)


LONG_SEL = "results/review_td3_safe_long_selection.json"
LONG_CSV = "results/review_C3_long_budget.csv"


@unittest.skipUnless(os.path.exists(LONG_SEL) and os.path.exists(LONG_CSV) and os.path.exists(TD3), "long budget not run")
class TestC3LongBudget(unittest.TestCase):
    """The long-budget sensitivity follows its pre-registered rule
    (config_safe doc long_budget_sensitivity) and leaves the carried model
    untouched."""

    def test_rule_and_carried_model(self):
        import json
        from ev2gym_thesis.rl import config_safe as cfg
        sel = json.load(open(LONG_SEL))
        self.assertEqual(sel["budget_steps"], cfg.LONG_BUDGET_STEPS)
        for seed, x in sel["seeds"].items():
            self.assertEqual(x["last_step"], cfg.LONG_BUDGET_STEPS)
            self.assertEqual(x["stop_reason"], "max_steps")
            self.assertGreaterEqual(x["bestval_validation_energy_kwh"], x["last_validation_energy_kwh"])
        carried = json.load(open(SEL))["carried_model"]
        self.assertEqual((int(carried["train_seed"]), carried["final_step"]), (100, 150000))

    def test_complete_and_safe(self):
        t = pd.read_csv(TD3)
        t = t[t.algorithm.str.startswith("TD3_safe_long_")]
        self.assertEqual(len(t), 2 * 3 * 300)
        self.assertTrue((t.overload_kwh == 0).all())
        lb = pd.read_csv(LONG_CSV)
        self.assertEqual(len(lb), 6 * 3)


if __name__ == "__main__":
    unittest.main()
