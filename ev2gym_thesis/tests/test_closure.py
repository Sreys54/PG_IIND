"""
Closure brief tests (Parts B, C, D, E). Every test calls production code or
reads the files that production code wrote; numbers pinned here are the
ones reported in thesis_docs/overnight_report.md (closure section).

Run: PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_closure
"""
import os
import unittest

import numpy as np
import pandas as pd

REG = "results/master_results.csv"
BASE_CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"


# ---------------------------------------------------------------------------
# Part B: censored arrivals and demand not served
# ---------------------------------------------------------------------------
class TestCensoringMechanism(unittest.TestCase):
    def test_wrapper_is_removed_after_use(self):
        import ev2gym.utilities.loaders as loaders
        from ev2gym_thesis.demand import censoring
        censoring.enable()
        self.assertIsNot(loaders.EV_spawner, censoring._ORIGINAL_EV_SPAWNER)
        censoring.disable()
        self.assertIs(loaders.EV_spawner, censoring._ORIGINAL_EV_SPAWNER)

    def test_replay_does_not_change_the_population_and_matches_registry(self):
        """scenario_demand asserts internally that the replay re-finds every
        spawned EV; the spawned count must equal the registry's
        total_ev_served for the same cell, and an env built without the
        wrapper must spawn the identical EV list."""
        from ev2gym_thesis.demand.censoring import scenario_demand
        from ev2gym_thesis.rl import price_data_cache
        from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
        price_data_cache.enable()
        tmp = f"experiments/phase3_infra_replicability/configs/closure/_tmp_test_censoring_pid{os.getpid()}"
        day, seed = (2022, 1, 17), 3
        cell = scenario_demand(BASE_CONFIG, day, seed, tmp)
        env = make_env(BASE_CONFIG, day, seed, day_config_dir=tmp)
        reset_for_evaluation(env, seed)
        plain = [(ev.location, ev.id, ev.time_of_arrival, ev.time_of_departure) for ev in env.EVs_profiles]
        self.assertEqual(cell["n_spawned"], len(plain))
        reg = pd.read_csv(REG, low_memory=False)
        row = reg[(reg.config_name == "station_v0_bogota") & (reg.algorithm == "RoundRobin")
                  & (reg.analysis_row.astype(str) == "True") & (reg.seed.astype(float) == seed)
                  & (reg.eval_day == "2022-01-17")]
        self.assertEqual(len(row), 1)
        self.assertEqual(int(float(row.total_ev_served.iloc[0])), cell["n_spawned"])
        self.assertLessEqual(cell["rejected_lower"], cell["rejected_upper"])

    def test_demand_not_served_formula(self):
        from ev2gym_thesis.demand.censoring import demand_not_served
        cell = {"energy_rejected_lower_kwh": 0.0, "requested_served_kwh": 100.0}
        self.assertEqual(demand_not_served(100.0, cell), 0.0)
        cell = {"energy_rejected_lower_kwh": 50.0, "requested_served_kwh": 150.0}
        self.assertAlmostEqual(demand_not_served(140.0, cell), (50 + 150 - 140) / 200)


@unittest.skipUnless(os.path.exists("results/closure_censoring_by_cell.csv"), "censoring table not built")
class TestCensoringTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = pd.read_csv("results/closure_censoring_by_cell.csv")

    def test_grid_complete(self):
        self.assertEqual(sorted(self.t.level.unique().tolist()), [0.25, 0.5, 0.75, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0])
        self.assertTrue((self.t.groupby("level").size() == 100).all())

    def test_bounds_ordered_and_rejections_grow_with_demand(self):
        self.assertTrue((self.t.rejected_lower <= self.t.rejected_upper).all())
        m = self.t.groupby("level").rejected_lower.mean()
        self.assertTrue(m.is_monotonic_increasing)
        self.assertGreater(m.loc[1.0], 0)  # the Checkpoint B rule fired on this

    def test_reference_level_pinned(self):
        g = self.t[self.t.level == 1.0]
        self.assertAlmostEqual(g.n_spawned.mean(), 13.44, places=2)
        self.assertAlmostEqual(g.rejected_lower.mean(), 8.90, places=2)


@unittest.skipUnless(os.path.exists("results/closure_demand_not_served.csv"), "DNS summary not built")
class TestDemandNotServedSummary(unittest.TestCase):
    def test_round_robin_reference_dns_pinned(self):
        d = pd.read_csv("results/closure_demand_not_served.csv")
        r = d[(d.level == 1.0) & (d.algorithm == "RoundRobin")].iloc[0]
        self.assertAlmostEqual(r.dns_lower_mean, 0.3458, places=4)
        self.assertGreater(r.dns_lower_ci_low, 0.15)  # target broken at the reference demand
        self.assertEqual(int(r.n_clusters), 50)


# ---------------------------------------------------------------------------
# Part C: configs, registry rows, thresholds, options
# ---------------------------------------------------------------------------
class TestClosureConfigs(unittest.TestCase):
    def test_variant_config_requires_prepare(self):
        from scripts.run_closure_capacity import variant_config
        with self.assertRaises(FileNotFoundError):
            variant_config(9.9, 8, 100.0)

    def test_constant_demand_variant_scales_spawn(self):
        from scripts.run_closure_capacity import variant_config
        name, path = variant_config(0.75, 12, 134.2, cd=True)
        self.assertEqual(name, "station_v0_bogota_sp22_p12_tx134.2_cd")
        txt = open(path, encoding="utf-8").read()
        self.assertIn("spawn_multiplier: 14.66666667", txt)
        self.assertIn("number_of_charging_stations: 12", txt)
        self.assertIn("max_power: 134.2", txt)

    def test_variant_differs_from_base_only_in_three_lines(self):
        from scripts.run_closure_capacity import variant_config
        _, path = variant_config(1.0, 10, 100.6)
        a = open(BASE_CONFIG, encoding="utf-8").read().splitlines()
        b = open(path, encoding="utf-8").read().splitlines()
        self.assertEqual(len(a), len(b))
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        self.assertEqual(len(diff), 3)


@unittest.skipUnless(os.path.exists(REG), "registry not present")
class TestClosureRegistryRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = pd.read_csv(REG, low_memory=False)
        cls.c = r[r.notes.fillna("").str.contains("closure_part=")]

    def test_counts_and_flags(self):
        self.assertEqual(len(self.c), 6000)
        self.assertTrue(self.c.analysis_row.astype(str).eq("True").all())
        self.assertTrue(self.c.simulate_grid.astype(str).eq("False").all())
        self.assertFalse(self.c.config_name.eq("station_v0_bogota").any())
        self.assertEqual(int(self.c.duplicated(["config_name", "algorithm", "seed", "eval_day"]).sum()), 0)

    def test_rl_only_on_the_reference_station(self):
        rl = self.c[self.c.algorithm == "TD3_vanilla_extended_ts102"]
        self.assertEqual(len(rl), 400)
        self.assertTrue(rl.config_name.str.match(r"^station_v0_bogota_sp\d+$").all())


@unittest.skipUnless(os.path.exists("results/closure_c1_breaking_levels.csv"), "C1 analysis not run")
class TestCapacityThresholds(unittest.TestCase):
    def test_breaking_levels_pinned(self):
        b = pd.read_csv("results/closure_c1_breaking_levels.csv").set_index("algorithm")
        self.assertEqual(b.loc["RoundRobin", "breaking_level"], 0.75)
        self.assertEqual(b.loc["RoundRobin", "first_criterion_broken"], "dns")
        self.assertEqual(b.loc["ChargeAsFastAsPossible", "breaking_level"], 0.5)
        self.assertEqual(b.loc["ChargeAsFastAsPossible", "first_criterion_broken"], "peak")
        self.assertEqual(b.loc["TD3_vanilla_extended_ts102", "breaking_level"], 0.5)
        self.assertTrue((b.n_clusters == 50).all())

    def test_round_robin_never_overloads_in_the_sweep(self):
        d = pd.read_csv("results/closure_c1_capacity_by_level.csv")
        rr = d[d.algorithm == "RoundRobin"]
        self.assertEqual(len(rr), 7)
        self.assertTrue((rr.total_transformer_overload_mean == 0).all())
        self.assertTrue((rr.peak_kw_p95_ci_high <= 100).all())

    def test_constant_demand_twelve_ports_close_the_gap_at_reference(self):
        c = pd.read_csv("results/closure_c2_options.csv")
        r = c[(c.level == 1.0) & (c.algorithm == "RoundRobin") & (c.ports == 12)
              & c.station_demand.str.startswith("constant") & (c.transformer_kw == 100.0)].iloc[0]
        self.assertLess(r.dns_lower_ci_high, 0.15)
        r10 = c[(c.level == 1.0) & (c.algorithm == "RoundRobin") & (c.ports == 10)
                & c.station_demand.str.startswith("constant") & (c.transformer_kw == 100.0)].iloc[0]
        self.assertGreater(r10.dns_lower_ci_high, 0.15)

    def test_bigger_transformer_changes_nothing_for_round_robin(self):
        c = pd.read_csv("results/closure_c2_options.csv")
        rr8 = c[(c.algorithm == "RoundRobin") & (c.ports == 8)]
        for lvl, g in rr8.groupby("level"):
            # identical to the cent (the 1.0x reference comes from the Step 2
            # rows, so float summation order differs in the last bits)
            self.assertLess(g.gross_margin_cop_mean.max() - g.gross_margin_cop_mean.min(), 0.005)
            self.assertLess(g.total_energy_charged_mean.max() - g.total_energy_charged_mean.min(), 1e-9)
            self.assertLess(g.dns_lower_mean.max() - g.dns_lower_mean.min(), 1e-12)


# ---------------------------------------------------------------------------
# Part D: city tariffs, time-of-use timing, lower demand
# ---------------------------------------------------------------------------
class TestCityTariffs(unittest.TestCase):
    def test_six_categoria_especial_cities(self):
        from ev2gym_thesis.prices.cities import CITIES
        self.assertEqual(set(CITIES), {"Bogota", "Medellin", "Cali", "Barranquilla", "Cartagena", "Bucaramanga"})

    def test_invariants_hold_where_checkable(self):
        from ev2gym_thesis.prices.cities import CITIES, invariants
        for city in CITIES:
            inv = invariants(city)
            if inv["sum_ok"] is not None:
                self.assertTrue(inv["sum_ok"], city)
            if inv["contribution_ok"] is not None:
                self.assertTrue(inv["contribution_ok"], city)

    def test_spreads_pinned(self):
        from ev2gym_thesis.prices.cities import spread
        self.assertAlmostEqual(spread("Bogota"), (877.5709 - 864.0163) / 864.0163)
        self.assertAlmostEqual(round(spread("Bogota"), 4), 0.0157)
        self.assertAlmostEqual(round(spread("Barranquilla"), 4), 0.1003)
        self.assertIsNone(spread("Bucaramanga"))

    def test_band_timing_starts_at_five(self):
        from ev2gym_thesis.prices.cities import energy_by_band, step_in_peak
        bands = [(9, 12), (18, 21)]
        self.assertFalse(step_in_peak(0, bands))      # 05:00
        self.assertTrue(step_in_peak(16, bands))      # 09:00
        self.assertFalse(step_in_peak(28, bands))     # 12:00
        self.assertTrue(step_in_peak(52, bands))      # 18:00
        self.assertFalse(step_in_peak(64, bands))     # 21:00
        peak, off = energy_by_band(np.ones(96) * 4.0, bands)
        self.assertAlmostEqual(peak, 24 * 1.0)        # 24 steps x 4 kW x 0.25 h
        self.assertAlmostEqual(peak + off, 96.0)


@unittest.skipUnless(os.path.exists("results/closure_multicity_rr_cost.csv"), "multicity analysis not run")
class TestMulticity(unittest.TestCase):
    def test_bogota_flat_cost_reproduces_week5(self):
        c = pd.read_csv("results/closure_multicity_rr_cost.csv")
        r = c[(c.city == "Bogota") & (c.retail_price_label == "1450_reference")].iloc[0]
        self.assertAlmostEqual(r.conceded_flat_cop_day, 551.9, places=1)
        self.assertEqual(int(r.n_clusters), 50)


@unittest.skipUnless(os.path.exists("results/closure_lower_demand_monotonicity.csv"), "D3 not run")
class TestLowerDemand(unittest.TestCase):
    def test_lower_demand_never_worse_on_average(self):
        d = pd.read_csv("results/closure_lower_demand_monotonicity.csv")
        dns = d[d.metric == "dns_lower"]
        self.assertTrue((dns.ci_low > 0).all())
        ov = d[d.metric == "total_transformer_overload"]
        self.assertTrue((ov.mean_low_demand == 0).all() and (ov.mean_high_demand == 0).all())


# ---------------------------------------------------------------------------
# Part E: no feeder-to-station feedback; feeder probe
# ---------------------------------------------------------------------------
class TestNoFeederFeedback(unittest.TestCase):
    def test_grid_step_runs_after_the_stations_and_only_stores_voltage(self):
        src = open("ev2gym/models/ev2gym_env.py", encoding="utf-8").read()
        step = src[src.index("def step(self, actions"):]
        self.assertLess(step.index("cs.step("), step.index("self.grid.step("))
        self.assertIn("self.node_voltage[:, self.current_step] = vm", step)
        for f in ["ev2gym/models/ev_charger.py", "ev2gym/models/transformer.py", "ev2gym/models/ev.py",
                  "ev2gym/baselines/heuristics.py", "ev2gym/rl_agent/state.py"]:
            self.assertNotIn("node_voltage", open(f, encoding="utf-8").read(), f)


@unittest.skipUnless(os.path.exists("results/closure_feeder_probe_summary.csv"), "feeder probe not run")
class TestFeederProbe(unittest.TestCase):
    def test_every_shipped_feeder_classified(self):
        s = pd.read_csv("results/closure_feeder_probe_summary.csv")
        self.assertEqual(set(s.iloc[:, 0]), {"node_25", "node_34", "node_69", "node_123"})


if __name__ == "__main__":
    unittest.main()
