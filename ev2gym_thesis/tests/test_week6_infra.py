"""
Week 7, Objective 4 (grid-enabled infrastructure study): tests calling real
production code.

Run: PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_week6_infra -v
"""
import os
import re
import tempfile
import unittest

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.grid import placement
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

NONGRID = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
GRID = "experiments/phase3_infra_replicability/configs/station_v0_bogota_grid.yaml"
TMP = tempfile.gettempdir() + "/w7_test_cfg"


def setUpModule():
    price_data_cache.enable()
    placement.enable()


# ---------------------------------------------------------------------------
# 1b: grid bring-up equivalence
# ---------------------------------------------------------------------------
class TestGridEquivalence(unittest.TestCase):
    def test_config_diff_is_only_the_intended_keys(self):
        a = open(NONGRID, encoding="utf-8").read().splitlines()
        b = open(GRID, encoding="utf-8").read().splitlines()
        strip = lambda ls: [l.split("#")[0].strip() for l in ls if l.split("#")[0].strip()]
        added = set(strip(b)) - set(strip(a))
        removed = set(strip(a)) - set(strip(b))
        self.assertEqual(removed, {"number_of_transformers: 1", "simulate_grid: False", "load_multiplier: 1"})
        self.assertEqual(added, {"number_of_transformers: -1", "simulate_grid: True", "load_multiplier: 1.0",
                                 "thesis_station_bus: 27"})

    def test_station_on_one_bus_with_100kw_limit(self):
        env = make_env(GRID, EVAL_DAYS[0], 0, day_config_dir=TMP)
        self.assertEqual(len(env.transformers), 33)
        self.assertEqual(set(env.cs_transformers), {placement.transformer_id_for_bus(27)})
        station = [tr for tr in env.transformers if len(tr.cs_ids)]
        self.assertEqual(len(station), 1)
        self.assertEqual(float(np.max(station[0].max_power)), 100.0)

    def test_grid_refuses_without_station_bus(self):
        txt = open(GRID, encoding="utf-8").read().replace("  thesis_station_bus: 27\n", "")
        path = os.path.join(tempfile.gettempdir(), "w7_nobus.yaml")
        open(path, "w", encoding="utf-8").write(txt)
        with self.assertRaises(KeyError):
            make_env(path, EVAL_DAYS[0], 0, day_config_dir=TMP)

    def test_equivalence_table_pinned(self):
        s = pd.read_csv("results/week7_grid_equivalence_summary.csv")
        self.assertEqual(set(s.metric), {"total_ev_served", "total_energy_charged", "total_transformer_overload",
                                         "average_user_satisfaction", "tracking_error"})
        self.assertTrue(s.within_tolerance.all())
        self.assertTrue((s.max_abs_diff == 0).all())
        self.assertTrue((s.n_cells == 40).all())


# ---------------------------------------------------------------------------
# 1c: RL compatibility -- identical observations, frozen VecNormalize
# ---------------------------------------------------------------------------
class TestRLCompatibility(unittest.TestCase):
    def test_final_model_sees_identical_observations_under_grid(self):
        from scripts.run_week7_grid import FINAL_RL_PATH
        from ev2gym_thesis.rl.eval_utils import load_trained_agent
        traj = {}
        for tag, cfg in [("nongrid", NONGRID), ("grid", GRID)]:
            env = make_env(cfg, EVAL_DAYS[0], 4, day_config_dir=TMP)
            model, vn = load_trained_agent(FINAL_RL_PATH, env)
            self.assertFalse(vn.training)
            self.assertFalse(vn.norm_reward)
            mean0 = vn.obs_rms.mean.copy()
            obs, _ = reset_for_evaluation(env, 4)
            obs_list, done = [], False
            while not done:
                obs_list.append(np.array(obs, dtype=float))
                action, _ = model.predict(vn.normalize_obs(obs), deterministic=True)
                obs, _, te, tr, stats = env.step(action)
                done = te or tr
            np.testing.assert_array_equal(mean0, vn.obs_rms.mean)  # frozen statistics never updated
            traj[tag] = (env.observation_space.shape, np.array(obs_list), stats["tracking_error"])
        self.assertEqual(traj["nongrid"][0], traj["grid"][0])
        np.testing.assert_array_equal(traj["nongrid"][1], traj["grid"][1])
        self.assertEqual(traj["nongrid"][2], traj["grid"][2])


# ---------------------------------------------------------------------------
# 1d: voltage metric definition
# ---------------------------------------------------------------------------
class TestVoltageMetric(unittest.TestCase):
    def test_library_band_is_plus_minus_5_percent(self):
        src = open("ev2gym/utilities/utils.py", encoding="utf-8").read()
        self.assertIn("np.sum(v_m < 0.95) + np.sum(v_m > 1.05)", src)
        self.assertIn("0.05 - np.abs(1-v_m)", src)

    def test_band_check_on_synthetic_voltages(self):
        v = np.ones((34, 4))
        v[26, 1] = 0.94   # bus 27, step 1: below band
        v[3, 2] = 1.06    # bus 4, step 2: above band
        v[:, 3] = 0.0     # an unsimulated step is excluded
        bc = band_check(v, station_bus=27)
        self.assertEqual(bc["n_steps"], 3)
        self.assertEqual(bc["n_bus_steps_outside"], 2)
        self.assertEqual(bc["n_steps_any_bus_outside"], 2)
        self.assertEqual(bc["worst_bus"], 27)
        self.assertEqual(bc["station_bus_steps_outside"], 1)
        self.assertAlmostEqual(bc["excursion_pu_steps"], 0.02, places=12)

    def test_band_check_agrees_with_library_on_every_probe_row(self):
        v = pd.read_csv("results/week7_voltage_probe.csv")
        self.assertTrue((v.lib_voltage_violation_counter == v.n_bus_steps_outside).all())
        self.assertLess((v.lib_voltage_violation + v.excursion_pu_steps).abs().max(), 1e-9)

    def test_probe_threshold_pinned(self):
        v = pd.read_csv("results/week7_voltage_probe.csv")
        tripping = v.groupby("load_multiplier").n_bus_steps_outside.apply(lambda s: (s > 0).any())
        self.assertFalse(tripping[0.7])
        self.assertTrue(tripping[0.8])


# ---------------------------------------------------------------------------
# Registry: migration, grid flag, probe rows
# ---------------------------------------------------------------------------
class TestRegistryGridFlag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv("results/master_results.csv", low_memory=False)

    def test_simulate_grid_is_last_column_and_prior_rows_false(self):
        self.assertEqual(self.df.columns[-1], "simulate_grid")
        nongrid = self.df[~self.df.config_name.str.contains("grid")]
        self.assertTrue(nongrid.simulate_grid.astype(str).eq("False").all())
        # Corrected 2026-10-06 (closure brief): the closure's Part C appended
        # 6,000 non-grid analysis rows (4,400 C1/C2 + 1,600 C2 constant-
        # demand), marked "closure_part=" in notes. The
        # pre-closure count stays pinned at 2,200 and the closure count is
        # pinned separately, so neither assertion gets weaker.
        closure = nongrid.notes.fillna("").str.contains("closure_part=")
        is_analysis = nongrid.analysis_row.astype(str) == "True"
        self.assertEqual(int((is_analysis & ~closure).sum()), 2200)
        self.assertEqual(int((is_analysis & closure).sum()), 6000)
        self.assertEqual(int(closure.sum()), 6000)

    def test_grid_rows_flagged(self):
        grid = self.df[self.df.config_name.str.contains("grid")]
        self.assertTrue(len(grid) > 0)
        self.assertTrue(grid.simulate_grid.astype(str).eq("True").all())

    def test_probe_rows_are_not_analysis_rows(self):
        probe = self.df[self.df.config_name.str.contains("_probe_")]
        self.assertEqual(len(probe), 200)
        self.assertTrue(probe.analysis_row.astype(str).eq("False").all())
        self.assertTrue(probe.notes.str.contains("probe=voltage_trip").all())


# ---------------------------------------------------------------------------
# Step 2: row count, full-scale equivalence, cluster bootstrap
# ---------------------------------------------------------------------------
GRID_SETTINGS = ["station_v0_bogota_grid", "station_v0_bogota_grid_spawn1.3", "station_v0_bogota_grid_spawn1.6",
                 "station_v0_bogota_grid_load1.3", "station_v0_bogota_grid_load1.6"]
GRID_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "MPC_TrackingG2V", "TD3_vanilla_extended_ts102",
             "Optimal_Oracle_Tracking"]


class TestStep2Grid(unittest.TestCase):
    def test_grid_row_count_pin(self):
        df = pd.read_csv("results/master_results.csv", low_memory=False)
        g = df[df.config_name.isin(GRID_SETTINGS)]
        self.assertEqual(len(g), 2500)
        self.assertTrue(g.analysis_row.astype(str).eq("True").all())
        self.assertTrue(g.simulate_grid.astype(str).eq("True").all())
        counts = g.groupby(["config_name", "algorithm"]).size()
        self.assertEqual(len(counts), 25)
        self.assertTrue((counts == 100).all())
        self.assertEqual(set(g.algorithm), set(GRID_ARMS))
        self.assertEqual(g.seed.astype(int).nunique(), 50)
        self.assertTrue(g.notes.str.contains("station_bus=27").all())
        rl = g[g.algorithm == "TD3_vanilla_extended_ts102"]
        self.assertTrue(rl.notes.str.contains("checkpoint_step=850000").all())

    def test_full_base_equivalence_all_arms(self):
        eq = pd.read_csv("results/week7_grid_base_equivalence_all_arms.csv")
        self.assertTrue(eq.identical.all())
        self.assertEqual(eq.max_abs_diff.max(), 0.0)
        self.assertEqual(int(eq.n_cells.iloc[0]), 500)
        self.assertEqual(int(eq.n_arms.iloc[0]), 5)

    def test_cluster_bootstrap_used_with_50_clusters(self):
        for f in ["week7_grid_master_comparison", "week7_grid_vs_roundrobin", "week7_grid_growth_effect",
                  "week7_voltage_attribution", "week7_grid_margin_bogota", "week7_target_compliance"]:
            t = pd.read_csv(f"results/{f}.csv")
            self.assertTrue((t.n_clusters == 50).all(), f)

    def test_mean_ci_is_the_cluster_bootstrap(self):
        from scripts.analyze_week7_infra import mean_ci
        from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        clusters = np.array([0, 0, 1, 1, 2, 2])
        pt, lo, hi, nc = mean_ci(x, clusters)
        ref = paired_cluster_bootstrap_ci(np.zeros(6), x, clusters, n_bootstrap=10_000, seed=0)
        self.assertEqual((pt, lo, hi, nc), (ref["point_estimate"], ref["ci_low"], ref["ci_high"], 3))

    def test_feeder_load_axis_leaves_station_metrics_unchanged(self):
        # Cell by cell, exactly (aggregated means can differ at 1e-15 from summation order).
        df = pd.read_csv("results/master_results.csv", low_memory=False)
        key = ["algorithm", "seed", "eval_day"]
        base = df[df.config_name == "station_v0_bogota_grid"].set_index(key).sort_index()
        for st in ["station_v0_bogota_grid_load1.3", "station_v0_bogota_grid_load1.6"]:
            other = df[df.config_name == st].set_index(key).sort_index()
            self.assertTrue(base.index.equals(other.index))
            for m in ["tracking_error", "total_energy_charged", "total_transformer_overload", "average_user_satisfaction"]:
                np.testing.assert_array_equal(base[m].astype(float).values, other[m].astype(float).values)
            # ...while the feeder voltage does change:
            self.assertFalse(np.array_equal(base.voltage_violation_counter.astype(float).values,
                                            other.voltage_violation_counter.astype(float).values))


if __name__ == "__main__":
    unittest.main()
