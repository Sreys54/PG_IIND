"""
Week 7, Objective 5 (replicability in Medellin): tests calling real
production code.

Run: PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_replicability -v
"""
import os
import unittest

import pandas as pd

from ev2gym_thesis.prices import colombia as bog
from ev2gym_thesis.prices import medellin as med

EPM_PDF = "thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf"


class TestEPMTariffInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pdfplumber
        with pdfplumber.open(EPM_PDF) as pdf:
            cls.parsed = med.parse_epm_nivel2(pdf.pages[0].extract_text())

    def test_parsed_values_match_constants(self):
        self.assertEqual(self.parsed["punta"]["con_contribucion"], med.EPM_NIVEL2_PUNTA_CON_CONTRIBUCION)
        self.assertEqual(self.parsed["fuera_punta"]["con_contribucion"], med.EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION)
        self.assertEqual(self.parsed["punta"]["sin_contribucion"], med.EPM_NIVEL2_PUNTA_SIN_CONTRIBUCION)
        self.assertEqual(self.parsed["fuera_punta"]["sin_contribucion"], med.EPM_NIVEL2_FUERA_PUNTA_SIN_CONTRIBUCION)
        self.assertEqual(self.parsed["cu_monomio_sin_contribucion"], med.EPM_NIVEL2_CU_MONOMIO_SIN_CONTRIBUCION)

    def test_both_invariants_hold_on_both_periods(self):
        for period in ("punta", "fuera_punta"):
            c = med.check_invariants(self.parsed[period])
            self.assertTrue(c["sum_ok"], (period, c))
            self.assertTrue(c["contribution_ok"], (period, c))

    def test_invariants_detect_a_wrong_row(self):
        bad = dict(self.parsed["punta"], G=self.parsed["punta"]["G"] + 1.0)
        self.assertFalse(med.check_invariants(bad)["sum_ok"])
        bad = dict(self.parsed["punta"], con_contribucion=self.parsed["punta"]["sin_contribucion"] * 1.19)
        self.assertFalse(med.check_invariants(bad)["contribution_ok"])

    def test_week5_tolerances_reused(self):
        self.assertEqual((med.SUM_TOLERANCE, med.CONTRIBUTION_FACTOR, med.CONTRIBUTION_TOLERANCE), (0.01, 1.20, 0.001))

    def test_base_cost_is_the_conservative_validated_rate(self):
        self.assertEqual(med.ENERGY_PURCHASE_COST_COP_PER_KWH_MEDELLIN,
                         max(med.EPM_NIVEL2_PUNTA_CON_CONTRIBUCION, med.EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION))
        self.assertFalse(med.RETAIL_TARIFF_MEDELLIN_IS_PUBLISHED)
        self.assertEqual(med.RETAIL_TARIFF_COP_PER_KWH_MEDELLIN_SENSITIVITY, bog.RETAIL_TARIFF_COP_PER_KWH)
        self.assertAlmostEqual(med.INTRADAY_SPREAD_MEDELLIN, (923.92 - 917.58) / 917.58)


class TestRankingInvariance(unittest.TestCase):
    def test_ranking_identical_across_all_price_scenarios(self):
        r = pd.read_csv("results/week7_ranking_invariance.csv")
        self.assertTrue(r.same_as_energy_ranking.all())
        self.assertTrue(r.ranking_identical_across_all_price_scenarios.all())
        self.assertGreaterEqual(r.price_scenario.nunique(), 8)
        self.assertIn("nongrid", set(r.dataset))

    def test_ranking_function_on_synthetic_table(self):
        from scripts.analyze_week7_replicability import ranking_invariance
        rows = []
        for scen, (retail, cost) in {"a": (1450, 865.76), "b": (1450, 923.92), "c": (1160, 923.92)}.items():
            for arm, e in [("X", 200.0), ("Y", 190.0), ("Z", 201.0)]:
                rows.append({"dataset": "synthetic", "price_scenario": scen, "retail_cop_per_kwh": retail,
                             "purchase_cost_cop_per_kwh": cost, "algorithm": arm, "mean_energy_kwh_per_day": e,
                             "gross_margin_cop_per_day": e * (retail - cost)})
        import tempfile
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "results"))
            os.chdir(d)
            try:
                out = ranking_invariance(pd.DataFrame(rows))
            finally:
                os.chdir(cwd)
        self.assertTrue(out.same_as_energy_ranking.all())
        self.assertEqual(out.ranking_by_margin.iloc[0], "Z > X > Y")

    def test_margin_ratio_between_cities_is_the_unit_margin_ratio(self):
        t = pd.read_csv("results/week7_replicability_margin.csv")
        t = t[(t.dataset == "nongrid") & (t.algorithm == "RoundRobin")].set_index("price_scenario")
        ratio = t.loc["medellin_base", "margin_conceded_vs_afap_cop_per_day"] / t.loc["bogota_base", "margin_conceded_vs_afap_cop_per_day"]
        expected = (1450 - med.ENERGY_PURCHASE_COST_COP_PER_KWH_MEDELLIN) / (1450 - bog.ENERGY_PURCHASE_COST_COP_PER_KWH)
        self.assertAlmostEqual(ratio, expected, places=9)
        self.assertEqual(int(t.loc["bogota_base", "n_clusters"]), 50)


class TestSourceFiles(unittest.TestCase):
    def test_sources_exist(self):
        self.assertTrue(os.path.exists(EPM_PDF))
        self.assertGreater(os.path.getsize(EPM_PDF), 100_000)
        src = open("thesis_docs/sources/SOURCES_week7.md", encoding="utf-8").read()
        self.assertIn("9.PublicacionTarifasSeptiembre162026_ANT_OM.pdf", src)
        self.assertIn("Accessed:", src)
        self.assertIn("negative result", src.lower())


if __name__ == "__main__":
    unittest.main()
