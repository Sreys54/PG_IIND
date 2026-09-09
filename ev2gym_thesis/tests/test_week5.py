"""
Week 5, Part A tests: Colombian price constants, the Enel tariff parser's
two invariants (against the real stored PDFs, not fixtures), the registry
grid-count assertion, and the economics recompute against a hand-computed
reference cell.

Per the project's standing rule (extracted from the Week 3 evaluation-bug
correction): every test here calls the real production function, not a
lookalike reimplementation.
"""
import os
import unittest

import pandas as pd

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS, day_to_date
from ev2gym_thesis.registry import REGISTRY_PATH
from ev2gym_thesis.prices.colombia import (
    RETAIL_TARIFF_COP_PER_KWH,
    ENERGY_PURCHASE_COST_COP_PER_KWH,
    ENERGY_PURCHASE_COST_CONTRIBUTION_FACTOR,
    compute_row_economics,
)
from ev2gym_thesis.economics_recompute import implied_price_check
from scripts.fetch_enel_tariffs import (
    MONTH_ORDER,
    MONTH_FILES,
    OUT_DIR,
    extract_month,
    validate_invariants,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPriceConstants(unittest.TestCase):
    """Section 8: the price constants are the approved values with their
    origin labels."""

    def test_retail_tariff_is_approved_value(self):
        self.assertEqual(RETAIL_TARIFF_COP_PER_KWH, 1450.0)

    def test_energy_purchase_cost_is_approved_value(self):
        # August 2026, Nivel 2, with contribution -- hand-verified by the
        # user before this project extracted anything programmatically.
        self.assertAlmostEqual(ENERGY_PURCHASE_COST_COP_PER_KWH, 865.7615, places=4)

    def test_contribution_factor_matches_regulatory_20_percent(self):
        self.assertAlmostEqual(ENERGY_PURCHASE_COST_CONTRIBUTION_FACTOR, 1.20, places=2)


class TestEnelTariffParserInvariants(unittest.TestCase):
    """Section 8: the tariff parser's two invariants hold on the stored
    PDFs -- calls the real extract_month/validate_invariants from
    scripts/fetch_enel_tariffs.py against the actual downloaded files, not
    a reimplementation."""

    @classmethod
    def setUpClass(cls):
        for month, filename in MONTH_FILES.items():
            pdf_path = os.path.join(OUT_DIR, f"2026-{month}.pdf")
            if not os.path.exists(pdf_path):
                raise unittest.SkipTest(
                    f"{pdf_path} not present -- run scripts/fetch_enel_tariffs.py first."
                )

    def test_all_eight_months_pass_both_invariants(self):
        for month in MONTH_ORDER:
            pdf_path = os.path.join(OUT_DIR, f"2026-{month}.pdf")
            row = extract_month(pdf_path, month)
            # validate_invariants raises RuntimeError on failure -- a clean
            # call here IS the assertion.
            validate_invariants(month, row)

    def test_january_matches_hand_verified_reference(self):
        row = extract_month(os.path.join(OUT_DIR, "2026-enero.pdf"), "enero")
        self.assertAlmostEqual(row["cu_sin_contribucion"], 605.4596, places=3)
        self.assertAlmostEqual(row["cu_con_contribucion"], 726.5515, places=3)

    def test_august_matches_hand_verified_reference(self):
        row = extract_month(os.path.join(OUT_DIR, "2026-agosto.pdf"), "agosto")
        self.assertAlmostEqual(row["cu_sin_contribucion"], 721.4679, places=3)
        self.assertAlmostEqual(row["cu_con_contribucion"], 865.7615, places=3)

    def test_february_manual_reading_also_satisfies_invariants(self):
        # The one month with no extractable text layer for its CU table --
        # confirms the manual-transcription fallback is not exempt from
        # the same validation every regex-extracted month goes through.
        row = extract_month(os.path.join(OUT_DIR, "2026-febrero.pdf"), "febrero")
        self.assertEqual(row["extraction_method"], "manual_visual_read_600dpi_crop")
        validate_invariants("febrero", row)


class TestRegistryGridCount(unittest.TestCase):
    """CORRECTED 2026-09-09 (Week 5, Gate 3/Gate 4 -- see
    thesis_docs/chapters/00_lab_log.md's 2026-09-08/09 entries): this
    class used to assert the PRE-Gate-4 grid shape (550 rows = 11
    algorithms x 50 cells, 5-seed x 10-EVAL_DAYS). That grid was produced
    by a buggy `generate_power_setpoints` with a live ENTSO-E price
    dependency inside the control layer -- every one of those rows is now
    `superseded=True`, kept as provenance, never statistically used. The
    current statistical grid is `analysis_row=True`: 13 algorithms x 100
    cells (50 seeds x 2 day types) = 1300 rows, on the Gate-4-corrected
    code. If either number moves later, this test fails instead of a
    table silently shifting."""

    @classmethod
    def setUpClass(cls):
        cls.registry = pd.read_csv(REGISTRY_PATH)
        cls.main = cls.registry[cls.registry["config_name"] == "station_v0_bogota"]
        cls.analysis = cls.main[cls.main["analysis_row"] == True]

    def test_analysis_grid_is_1300_rows_13_algorithms(self):
        eval_day_strs = {str(day_to_date(d)) for d in EVAL_DAYS}
        grid = self.analysis[
            self.analysis["seed"].isin(SEEDS) & self.analysis["eval_day"].isin(eval_day_strs)
        ]
        self.assertEqual(len(grid), 1300, "SEEDS x EVAL_DAYS grid must be exactly 13 algorithms x 100 cells")
        self.assertEqual(grid["algorithm"].nunique(), 13)
        self.assertIn("MPC_TrackingG2V", set(grid["algorithm"]))
        self.assertIn("MPC_EnergyMaxG2V", set(grid["algorithm"]))

    def test_every_analysis_row_algorithm_has_exactly_100_rows(self):
        counts = self.analysis.groupby("algorithm").size()
        self.assertEqual(len(counts), 13)
        self.assertTrue((counts == 100).all(), counts[counts != 100].to_dict())

    def test_every_analysis_row_is_not_superseded(self):
        self.assertTrue((self.analysis["superseded"] == False).all())

    def test_pre_gate4_rows_are_all_superseded_and_excluded_from_analysis(self):
        stale = self.main[self.main["analysis_row"] == False]
        self.assertTrue((stale["superseded"] == True).all())
        # The 2 legacy Week 1 reference-day rows are part of this stale set,
        # kept as provenance, never deleted:
        legacy = stale[stale["notes"] == "week1_reference_day"]
        self.assertEqual(len(legacy), 2)
        self.assertSetEqual(set(legacy["algorithm"]), {"ChargeAsFastAsPossible", "RoundRobin"})


class TestSetpointPriceIndependence(unittest.TestCase):
    """Gate 4: the fix that made the day axis genuinely redundant. Calls
    the real production path (env_factory.make_env + reset_for_evaluation),
    not a reimplementation."""

    def test_setpoints_identical_across_same_category_dates(self):
        from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
        import numpy as np
        cfg = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
        env1 = make_env(cfg, (2022, 1, 17), 0)
        reset_for_evaluation(env1, 0)
        env2 = make_env(cfg, (2022, 2, 14), 0)  # a different weekday, same seed
        reset_for_evaluation(env2, 0)
        self.assertTrue(np.array_equal(env1.power_setpoints, env2.power_setpoints))

    def test_mpc_energy_max_ch_prices_are_flat(self):
        from ev2gym_thesis.mpc.energy_max_mpc import MPCEnergyMaxG2V, FLAT_PRICE_CONSTANT
        from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
        import numpy as np
        cfg = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
        env = make_env(cfg, (2022, 1, 17), 0)
        reset_for_evaluation(env, 0)
        agent = MPCEnergyMaxG2V(env, control_horizon=10)
        self.assertTrue(np.all(agent.ch_prices == FLAT_PRICE_CONSTANT))
        self.assertTrue(np.all(agent.disch_prices == 0.0))


class TestMPCInformationSet(unittest.TestCase):
    """Gate 1 audit assertion: both MPC arms are G2V-only (no discharge
    decision variable), and both are built on the unmodified `MPC` base
    class whose EV-population bookkeeping is non-causal -- pinning the
    causality declaration this project's chapter makes, on the real
    resolved objects, not by inspection of the docstring."""

    @classmethod
    def setUpClass(cls):
        from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
        from ev2gym_thesis.mpc.tracking_mpc import MPCTrackingG2V
        from ev2gym_thesis.mpc.energy_max_mpc import MPCEnergyMaxG2V
        cfg = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
        cls.env_a = make_env(cfg, (2022, 1, 17), 0)
        reset_for_evaluation(cls.env_a, 0)
        cls.tracking_agent = MPCTrackingG2V(cls.env_a, control_horizon=10)

        cls.env_b = make_env(cfg, (2022, 1, 17), 0)
        reset_for_evaluation(cls.env_b, 0)
        cls.energy_max_agent = MPCEnergyMaxG2V(cls.env_b, control_horizon=10)

    def test_g2v_only_no_discharge_variable(self):
        # G2V-only formulations set nb == na (one decision variable per
        # port per horizon step); V2G formulations set nb = 2*na.
        self.assertEqual(self.tracking_agent.nb, self.tracking_agent.na)
        self.assertEqual(self.energy_max_agent.nb, self.energy_max_agent.na)

    def test_both_arms_know_full_ev_population_at_construction(self):
        # MPC.__init__ (unmodified) builds self.u/self.x_final for the
        # WHOLE simulation length from env.EVs_profiles at construction --
        # the non-causal information source this project's chapter
        # declares. Confirmed directly on the resolved object.
        n_evs = len(self.env_a.EVs_profiles)
        self.assertEqual(self.tracking_agent.EV_number, n_evs)
        self.assertEqual(self.tracking_agent.departure_times.shape[0], n_evs)
        # departure_times are populated (not zero/unset) for every EV,
        # confirming they are known at construction, not causally revealed:
        self.assertTrue((self.tracking_agent.departure_times > 0).all())


class TestEconomicsRecompute(unittest.TestCase):
    """Section 8: the recompute function reproduces a hand-computed cell."""

    def test_week1_reference_cell_afap_hand_computed(self):
        # From results/master_results.csv: ChargeAsFastAsPossible,
        # seed=42, eval_day=2022-01-17, total_energy_charged=240.926874
        energy_kwh = 240.926874
        result = compute_row_economics(energy_kwh)
        expected_revenue = energy_kwh * 1450.0
        expected_cost = energy_kwh * 865.7615
        self.assertAlmostEqual(result["retail_revenue_cop"], expected_revenue, places=4)
        self.assertAlmostEqual(result["energy_purchase_cost_cop"], expected_cost, places=4)
        self.assertAlmostEqual(result["gross_margin_cop"], expected_revenue - expected_cost, places=4)
        # Hand-computed to the peso, independent of the function's own arithmetic:
        self.assertAlmostEqual(result["gross_margin_cop"], 140758.76, places=1)

    def test_zero_energy_gives_zero_everything(self):
        result = compute_row_economics(0.0)
        self.assertEqual(result["retail_revenue_cop"], 0.0)
        self.assertEqual(result["energy_purchase_cost_cop"], 0.0)
        self.assertEqual(result["gross_margin_cop"], 0.0)


class TestImpliedPriceCheck(unittest.TestCase):
    """Section 5.3(a): every row's implied EUR/kWh must fall inside its
    simulated day's ENTSO-E band -- the real reconciliation check, run
    against the real registry (or a controlled subset of it)."""

    def test_week1_reference_rows_pass(self):
        registry = pd.read_csv(REGISTRY_PATH)
        ref_rows = registry[
            (registry["config_name"] == "station_v0_bogota") &
            (registry["notes"] == "week1_reference_day")
        ]
        self.assertEqual(len(ref_rows), 2)
        per_row, problems = implied_price_check(ref_rows)
        self.assertEqual(problems, [])
        self.assertTrue((per_row["in_range"]).all())


class TestENSComplianceKnownAnswer(unittest.TestCase):
    """Section 18: target-compliance function against a known answer.
    AFAP-vs-AFAP is a known-answer case with no synthetic fixture needed
    (ENS_rel by definition is exactly 0% for the baseline against itself)
    -- checked against the real production output
    (results/week5_ens_compliance.csv, scripts/analyze_week5_results.py),
    not a reimplementation of the formula."""

    def test_afap_ens_rel_is_exactly_zero(self):
        path = "results/week5_ens_compliance.csv"
        if not os.path.exists(path):
            raise unittest.SkipTest(f"{path} not present -- run scripts/analyze_week5_results.py first.")
        df = pd.read_csv(path)
        afap = df[df["algorithm"] == "ChargeAsFastAsPossible"].iloc[0]
        self.assertAlmostEqual(afap["ENS_rel_point_pct"], 0.0, places=6)
        self.assertAlmostEqual(afap["ENS_rel_ci_low_pct"], 0.0, places=6)
        self.assertAlmostEqual(afap["ENS_rel_ci_high_pct"], 0.0, places=6)
        self.assertTrue(bool(afap["ENS_rel_pass_15pct_ci_upper_bound"]))

    def test_every_arm_passes_the_15_percent_target(self):
        path = "results/week5_ens_compliance.csv"
        if not os.path.exists(path):
            raise unittest.SkipTest(f"{path} not present -- run scripts/analyze_week5_results.py first.")
        df = pd.read_csv(path)
        self.assertEqual(len(df), 13)
        self.assertTrue(df["ENS_rel_pass_15pct_ci_upper_bound"].all(),
                         df[~df["ENS_rel_pass_15pct_ci_upper_bound"]]["algorithm"].tolist())
        self.assertTrue((df["ENS_rel_ci_high_pct"] < 15.0).all())


if __name__ == "__main__":
    unittest.main()
