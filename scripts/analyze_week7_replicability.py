"""
Week 7, Objective 5 (replicability in Medellin): tariff transfer without new
simulations (3c), the transferability classification (3b) and the demand
mapping decision (3d).

3c recomputes Colombian-peso economics from energy already in the registry
-- the non-grid statistical rows (Week 5's 13 arms + the final RL model) and
the Step 2 grid rows -- under Bogota's Week 5 constants and Medellin's EPM
constants, with ev2gym_thesis.prices.colombia.compute_row_economics (the
same pure function Week 5 used), and verifies programmatically that the
margin ranking of the arms does not depend on the tariff under a flat price.

Usage: PYTHONPATH=. python scripts/analyze_week7_replicability.py
"""
import itertools

import numpy as np
import pandas as pd

from ev2gym_thesis.prices import colombia as bog
from ev2gym_thesis.prices import medellin as med
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

from scripts import analyze_week5_results as w5
from scripts import run_week7_grid as w7

N_BOOT = 10_000
NONGRID_ARMS = w5.ALL_ALGOS + [w7.FINAL_RL_NAME]

# doc:begin price_scenarios
PRICE_SCENARIOS = {
    "bogota_base": (bog.RETAIL_TARIFF_COP_PER_KWH, bog.ENERGY_PURCHASE_COST_COP_PER_KWH),
    "medellin_base": (med.RETAIL_TARIFF_COP_PER_KWH_MEDELLIN_SENSITIVITY, med.ENERGY_PURCHASE_COST_COP_PER_KWH_MEDELLIN),
    "medellin_cost_fuera_de_punta": (med.RETAIL_TARIFF_COP_PER_KWH_MEDELLIN_SENSITIVITY,
                                     med.EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION),
    "medellin_cost_monomio_x1.20": (med.RETAIL_TARIFF_COP_PER_KWH_MEDELLIN_SENSITIVITY,
                                    round(med.EPM_NIVEL2_CU_MONOMIO_SIN_CONTRIBUCION * med.CONTRIBUTION_FACTOR, 4)),
}
for city, cost in [("bogota", bog.ENERGY_PURCHASE_COST_COP_PER_KWH), ("medellin", med.ENERGY_PURCHASE_COST_COP_PER_KWH_MEDELLIN)]:
    for sign, f in [("minus20", 1 - bog.RETAIL_TARIFF_SENSITIVITY_FRACTION), ("plus20", 1 + bog.RETAIL_TARIFF_SENSITIVITY_FRACTION)]:
        PRICE_SCENARIOS[f"{city}_retail_{sign}"] = (round(1450.0 * f, 4), cost)
# doc:end price_scenarios


def datasets():
    reg = pd.read_csv("results/master_results.csv", low_memory=False)
    reg = reg[reg.analysis_row.astype(str) == "True"].copy()
    reg["seed"] = reg.seed.astype(int)
    reg["total_energy_charged"] = reg.total_energy_charged.astype(float)
    out = {"nongrid": reg[(reg.config_name == "station_v0_bogota") & reg.algorithm.isin(NONGRID_ARMS)]}
    for st in w7.SETTINGS:
        g = reg[(reg.config_name == w7.config_name_for(st)) & (reg.simulate_grid.astype(str) == "True")]
        if len(g):
            out[f"grid_{st}"] = g
    return out


def _econ(energy, prices):
    retail, cost = prices
    return np.array([bog.compute_row_economics(e, retail, cost)["gross_margin_cop"] for e in energy])


# doc:begin tariff_transfer
def tariff_transfer(ds):
    rows, cost_rows = [], []
    for name, df in ds.items():
        afap = df[df.algorithm == "ChargeAsFastAsPossible"]
        for scen, prices in PRICE_SCENARIOS.items():
            for arm in sorted(df.algorithm.unique()):
                b = df[df.algorithm == arm]
                m = afap.merge(b, on=["seed", "day_type"], suffixes=("_a", "_b"))
                ma, mb = _econ(m.total_energy_charged_a, prices), _econ(m.total_energy_charged_b, prices)
                r = paired_cluster_bootstrap_ci(ma, mb, m.seed.values, n_bootstrap=N_BOOT, seed=0)
                mean = paired_cluster_bootstrap_ci(np.zeros(len(mb)), mb, m.seed.values, n_bootstrap=N_BOOT, seed=0)
                rows.append({"dataset": name, "price_scenario": scen, "retail_cop_per_kwh": prices[0],
                             "purchase_cost_cop_per_kwh": prices[1], "algorithm": arm,
                             "mean_energy_kwh_per_day": m.total_energy_charged_b.mean(),
                             "gross_margin_cop_per_day": mean["point_estimate"],
                             "margin_ci_low": mean["ci_low"], "margin_ci_high": mean["ci_high"],
                             "margin_conceded_vs_afap_cop_per_day": -r["point_estimate"],
                             "conceded_ci_low": -r["ci_high"], "conceded_ci_high": -r["ci_low"],
                             "n_clusters": r["n_clusters"]})
    t = pd.DataFrame(rows)
    t.to_csv("results/week7_replicability_margin.csv", index=False)
    # The cost of respecting the transformer limit: margin Round Robin concedes vs. AFAP, both cities side by side.
    side = t[t.price_scenario.isin(["bogota_base", "medellin_base"]) & t.algorithm.isin(
        ["RoundRobin", "MPC_TrackingG2V", w7.FINAL_RL_NAME, "Optimal_Oracle_Tracking"])]
    piv = side.pivot_table(index=["dataset", "algorithm"], columns="price_scenario",
                           values=["margin_conceded_vs_afap_cop_per_day", "conceded_ci_low", "conceded_ci_high"]).reset_index()
    piv.columns = ["_".join([c for c in col if c]) for col in piv.columns]
    piv["n_clusters"] = side.groupby(["dataset", "algorithm"]).n_clusters.first().values
    piv.to_csv("results/week7_cost_of_transformer_limit_two_cities.csv", index=False)
    return t, piv
# doc:end tariff_transfer


# doc:begin ranking_invariance
def ranking_invariance(t):
    """Under a flat price, margin = energy x (retail - cost), so with
    retail > cost the margin ranking must equal the energy ranking for every
    price scenario. Checked on the computed table, not assumed."""
    rows = []
    for (name, scen), g in t.groupby(["dataset", "price_scenario"]):
        by_margin = list(g.sort_values("gross_margin_cop_per_day", ascending=False).algorithm)
        by_energy = list(g.sort_values("mean_energy_kwh_per_day", ascending=False).algorithm)
        unit = g.retail_cop_per_kwh.iloc[0] - g.purchase_cost_cop_per_kwh.iloc[0]
        rows.append({"dataset": name, "price_scenario": scen, "unit_margin_cop_per_kwh": unit,
                     "ranking_by_margin": " > ".join(by_margin), "same_as_energy_ranking": by_margin == by_energy})
    out = pd.DataFrame(rows)
    base = out.groupby("dataset").ranking_by_margin.nunique()
    out["ranking_identical_across_all_price_scenarios"] = out.dataset.map(base == 1)
    out.to_csv("results/week7_ranking_invariance.csv", index=False)
    assert out.same_as_energy_ranking.all() and out.ranking_identical_across_all_price_scenarios.all(), out
    return out
# doc:end ranking_invariance


# doc:begin transfer_classification
TRANSFER_CLASSIFICATION = [
    ("Energy purchase cost (CU, Nivel 2 commercial, with contribution)", "city-specific and replaced",
     "Enel Colombia, Aug 2026: 865.7615 COP/kWh (monomial)", "EPM, Sep 2026: 923.92 COP/kWh (Punta; 917.58 Fuera de Punta)",
     "Both invariant-checked (Week 5 tolerances)."),
    ("Retail EV charging price", "city-specific but unavailable, therefore kept and declared",
     "Enel, Aug 2025: 1,450 COP/kWh", "Not published by EPM; Bogota's 1,450 used as a labelled sensitivity",
     "No competitor price substituted (pairing rule)."),
    ("Intraday price spread (Punta vs Fuera de Punta)", "city-specific and replaced",
     "1.57% (Week 5)", "0.69% (EPM Sep 2026)", "Below Bogota's; no price-signal control warranted in either city."),
    ("EV arrival/departure distributions", "city-specific but unavailable, therefore kept and declared",
     "EV2Gym's Dutch public-charging data", "Same Dutch data", "No Colombian session-level dataset available for either city."),
    ("EV fleet specification (70 kWh, 50 kW AC/DC limit)", "city-independent",
     "station_v0_bogota.yaml", "Same", "Same national vehicle market; one homogeneous spec in both."),
    ("Station: 8 ports, 100 kW local transformer", "city-independent",
     "station_v0_bogota.yaml", "Same", "A station design, not a city property; the guidelines are about this design."),
    ("Feeder abstraction (EV2Gym 34-node feeder, station at bus 27)", "city-specific but unavailable, therefore kept and declared",
     "RL-ADN 34-node feeder", "Same", "No EPM or Enel feeder model is public; the same abstract feeder is used in both."),
    ("Demand level (EVs per station per day)", "city-specific but unavailable, therefore kept and declared",
     "spawn_multiplier 30 (Week 1 sizing)", "Not mapped (see demand mapping)",
     "City EV registrations differ (Medellin/Bogota = 0.40 Jan-Aug 2025) but no source gives per-station demand."),
    ("Climate / ambient temperature", "city-specific but unavailable, therefore kept and declared",
     "Not modelled by EV2Gym in the main grid", "Not modelled", "Week 2 degradation study was Bogota-only; not transferred."),
    ("National regulation (RETIE voltage band, Res. 40223/2021 connectors, CREG CU method)", "city-independent",
     "National", "National", "Applies identically in both cities."),
]
# doc:end transfer_classification


def demand_mapping():
    """3d: city EV registrations (Andi-Fenalco via El Colombiano, 2025-09-10)."""
    med_reg, bog_reg = 2148, 5358   # Jan-Aug 2025 registrations
    med_aug, bog_aug = 367, 722     # Aug 2025
    rows = [{"quantity": "EV registrations Jan-Aug 2025", "medellin": med_reg, "bogota": bog_reg,
             "ratio_medellin_over_bogota": med_reg / bog_reg},
            {"quantity": "EV registrations Aug 2025", "medellin": med_aug, "bogota": bog_aug,
             "ratio_medellin_over_bogota": med_aug / bog_aug},
            {"quantity": "Public charging points (Medellin ~30, source above; Bogota >=67 Enel X chargers, Week 1, lower bound)",
             "medellin": 30, "bogota": 67, "ratio_medellin_over_bogota": 30 / 67}]
    out = pd.DataFrame(rows)
    out["supports_per_station_demand_mapping"] = False
    out.to_csv("results/week7_demand_mapping.csv", index=False)
    return out


if __name__ == "__main__":
    ds = datasets()
    print({k: len(v) for k, v in ds.items()})
    t, piv = tariff_transfer(ds)
    print(ranking_invariance(t)[["dataset", "price_scenario", "same_as_energy_ranking",
                                 "ranking_identical_across_all_price_scenarios"]].to_string(index=False))
    pd.DataFrame(TRANSFER_CLASSIFICATION, columns=["model_input", "classification", "bogota_value", "medellin_value",
                                                  "note"]).to_csv("results/week7_transfer_classification.csv", index=False)
    print(demand_mapping().to_string(index=False))
    print(piv.to_string(index=False))
