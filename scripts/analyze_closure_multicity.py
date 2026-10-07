"""
Closure brief, Part D2: the tariff transfer to every municipality of
categoria especial (ev2gym_thesis/prices/cities.py), on the non-grid
statistical rows (station_v0_bogota, analysis_row=True, 50 seeds x 2 days).

Per city:
  - invariants (component sum, contribution factor), spread, generation share;
  - unit margin (retail - flat cost) at 1,450 COP/kWh and at the operator's
    own per-kWh charging price where one is published;
  - Round Robin's cost of the 100 kW limit (margin conceded vs. AFAP, COP per
    day) under the flat cost, and under the operator's two-band
    time-of-use option, computed from each run's per-step station power
    (results/timeseries/<run_id>.npz; 15-min steps from 05:00);
  - whether the ranking of the arms by margin equals their ranking by energy
    under the time-of-use cost (the D1 proposition holds exactly only under a
    flat cost; this checks how far it survives a two-band cost).
Paired cluster bootstrap over the scenario seed, n_clusters reported.

Usage: PYTHONPATH=. python scripts/analyze_closure_multicity.py
"""
import os

import numpy as np
import pandas as pd

from ev2gym_thesis.prices import cities as C
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

RETAIL_REFERENCE = 1450.0
OUT_CITIES = "results/closure_multicity_tariffs.csv"
OUT_COST = "results/closure_multicity_rr_cost.csv"
OUT_RANK = "results/closure_multicity_tou_ranking.csv"


def load_runs():
    r = pd.read_csv("results/master_results.csv", low_memory=False)
    r = r[(r.analysis_row.astype(str) == "True") & (r.config_name == "station_v0_bogota")].copy()
    r["seed"] = r.seed.astype(float).astype(int)
    r["total_energy_charged"] = r.total_energy_charged.astype(float)
    r = r[[os.path.exists(f"results/timeseries/{x}.npz") for x in r.run_id]]
    return r


def attach_bands(runs):
    """kWh in each city's peak band. The energy from the timeseries must
    match the registry's total_energy_charged (no V2G in this project)."""
    power = {rid: np.load(f"results/timeseries/{rid}.npz")["station_power"] for rid in runs.run_id}
    runs["energy_ts"] = [float(np.clip(power[x], 0, None).sum() * C.STEP_HOURS) for x in runs.run_id]
    for city, c in C.CITIES.items():
        if c["tou"]:
            runs[f"peak_kwh_{city}"] = [C.energy_by_band(power[x], c["tou"]["peak_hours"])[0] for x in runs.run_id]
    return runs


def ci(a, b, clusters):
    r = paired_cluster_bootstrap_ci(a, b, clusters, n_bootstrap=10_000, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


# doc:begin multicity_cost
def city_tables(runs):
    afap = runs[runs.algorithm == "ChargeAsFastAsPossible"]
    rr = runs[runs.algorithm == "RoundRobin"]
    p = afap.merge(rr, on=["seed", "eval_day"], suffixes=("_a", "_r"))
    assert len(p) == 100
    tariff_rows, cost_rows = [], []
    for city, c in C.CITIES.items():
        inv = C.invariants(city)
        sp = C.spread(city)
        tariff_rows.append({
            "city": city, "operator": c["operator"], "sheet_month": c["sheet_month"], "source": c["source"],
            "cu_nivel2_sin_contribucion": c["cu_sin"], "flat_cost_con_contribucion": c["flat_con"],
            "flat_cost_status": c["flat_con_status"],
            "tou_option": c["tou"]["name"] if c["tou"] else None,
            "tou_peak_hours": ";".join(f"{a}-{b}" for a, b in c["tou"]["peak_hours"]) if c["tou"] else None,
            "tou_peak_con": c["tou"]["peak_con"] if c["tou"] else None,
            "tou_offpeak_con": c["tou"]["offpeak_con"] if c["tou"] else None,
            "intraday_spread": sp, "generation_share": C.generation_share(city),
            "component_sum": inv["component_sum"], "component_sum_abs_diff": inv["sum_abs_diff"],
            "component_sum_ok": inv["sum_ok"], "contribution_max_rel_diff": inv["contribution_max_rel_diff"],
            "contribution_ok": inv["contribution_ok"],
            "unit_margin_at_1450": RETAIL_REFERENCE - c["flat_con"],
            "operator_charging_price": c["charging_price"],
            "unit_margin_at_operator_price": (c["charging_price"] - c["flat_con"]) if c["charging_price"] else None,
            "charging_price_source": c["charging_price_source"], "unavailable": "; ".join(c["unavailable"]),
        })
        prices = [("1450_reference", RETAIL_REFERENCE)]
        if c["charging_price"] and c["charging_price"] != RETAIL_REFERENCE:
            prices.append(("operator_price", c["charging_price"]))
        for label, price in prices:
            flat_a = p.total_energy_charged_a * (price - c["flat_con"])
            flat_r = p.total_energy_charged_r * (price - c["flat_con"])
            row = {"city": city, "retail_price_label": label, "retail_price": price}
            pt, lo, hi, nc = ci(flat_r, flat_a, p.seed)  # a - r = margin conceded
            row.update(conceded_flat_cop_day=pt, conceded_flat_ci_low=lo, conceded_flat_ci_high=hi,
                       conceded_flat_share_of_afap=pt / flat_a.mean(), n_clusters=nc)
            if c["tou"]:
                t = c["tou"]
                k = f"peak_kwh_{city}"
                tou = lambda e, pk: pk * (price - t["peak_con"]) + (e - pk) * (price - t["offpeak_con"])
                tou_a = tou(p.energy_ts_a, p[k + "_a"])
                tou_r = tou(p.energy_ts_r, p[k + "_r"])
                pt, lo, hi, _ = ci(tou_r, tou_a, p.seed)
                row.update(conceded_tou_cop_day=pt, conceded_tou_ci_low=lo, conceded_tou_ci_high=hi,
                           conceded_tou_share_of_afap=pt / tou_a.mean(),
                           afap_peak_share=float((p[k + "_a"] / p.energy_ts_a).mean()),
                           rr_peak_share=float((p[k + "_r"] / p.energy_ts_r).mean()))
            cost_rows.append(row)
    return pd.DataFrame(tariff_rows), pd.DataFrame(cost_rows)
# doc:end multicity_cost


def tou_ranking(runs):
    """Mean margin per arm under each city's two-band cost (1,450 retail):
    is the ranking by margin still the ranking by energy?"""
    out = []
    for city, c in C.CITIES.items():
        if not c["tou"]:
            continue
        t = c["tou"]
        k = f"peak_kwh_{city}"
        m = runs.assign(margin=runs[k] * (RETAIL_REFERENCE - t["peak_con"])
                        + (runs.energy_ts - runs[k]) * (RETAIL_REFERENCE - t["offpeak_con"]))
        g = m.groupby("algorithm").agg(energy=("energy_ts", "mean"), margin=("margin", "mean"))
        by_e = list(g.sort_values("energy", ascending=False).index)
        by_m = list(g.sort_values("margin", ascending=False).index)
        out.append({"city": city, "n_arms": len(g), "ranking_by_energy": ";".join(by_e),
                    "ranking_by_tou_margin": ";".join(by_m), "same_ranking": by_e == by_m,
                    "n_positions_differing": int(sum(a != b for a, b in zip(by_e, by_m)))})
    return pd.DataFrame(out)


def main():
    runs = attach_bands(load_runs())
    diff = (runs.energy_ts - runs.total_energy_charged).abs().max()
    print(f"timeseries energy vs registry: max abs diff {diff:.6f} kWh over {len(runs)} runs, "
          f"{runs.algorithm.nunique()} arms")
    assert diff < 1e-3, "timeseries energy does not reproduce total_energy_charged"
    tariffs, cost = city_tables(runs)
    rank = tou_ranking(runs)
    tariffs.to_csv(OUT_CITIES, index=False)
    cost.to_csv(OUT_COST, index=False)
    rank.to_csv(OUT_RANK, index=False)
    pd.set_option("display.width", 250)
    print(tariffs[["city", "sheet_month", "cu_nivel2_sin_contribucion", "flat_cost_con_contribucion", "intraday_spread",
                   "generation_share", "component_sum_ok", "contribution_ok", "unit_margin_at_1450",
                   "unit_margin_at_operator_price"]].round(4).to_string(index=False))
    print(cost.round(3).to_string(index=False))
    print(rank[["city", "n_arms", "same_ranking", "n_positions_differing"]].to_string(index=False))


if __name__ == "__main__":
    main()
