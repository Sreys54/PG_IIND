"""
Week 8 advisor review, C6: one master comparison table per demand level for
every C1 arm (DC regime, station-level arrivals, 8 ports, 100 kW), with CI
half-widths and the paired difference against RR-TA.

Statistics, the same everywhere (stated in every table): cluster bootstrap
over the scenario seed, n_clusters = 50, 10,000 resamples, percentile 95%
intervals, PER COMPARISON (no multiplicity adjustment; with 11 arms x 3
levels the reader should read a single interval, not a family). Energy
percentages and per-driver means are ratios of totals recomputed inside
each resample (A2 rule). Denominators: per day (the 100 cases are days).

Columns per arm: energy (kWh/day), ENS_rel = 1 - E_arm / E_AFAP, exact DNS,
mean energy satisfaction f including rejected drivers, service level
(share with f >= 0.9, incl. rejected), EV2Gym battery-level satisfaction
(served drivers), overload (kWh/day), days with overload (of 100), station
peak P95 and maximum over the 100 days (kW), gross energy margin
(COP/day, Bogota tariff), each with its paired difference vs RR-TA.
Targets re-evaluated per arm: mean f incl. rejected CI low >= 0.90, DNS CI
high <= 0.15, zero days with overload.

Input: experiments/phase4_review/C/c1_cases.csv (+ td3_cases.csv when it
exists). Output: results/review_C_master_<level>.csv and
results/review_C_dc_comparison.xlsx.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci

C = "experiments/phase4_review/C"
REF = "RR-TA"
STATS_NOTE = ("cluster bootstrap over scenario seed (n_clusters = 50), 10,000 resamples, percentile 95%, "
              "per comparison (no multiplicity adjustment); ratios of totals per resample")
ORDER = ["AFAP", "PS", "FIX12.5", "RR", "RR+S", "RR-TA", "Random+S", "TD3_safe", "MPC-soft", "MPC-soft-est",
         "Oracle-E"]


def level_of(name):
    return float(name.split("_poisson_")[1].split("x")[0])


def metrics(g):
    """{metric: (num, den)} per case, aligned on the case index."""
    one = np.ones(len(g))
    return {"energy_kwh_per_day": (g.energy_delivered_kwh.values, one),
            "dns_exact": ((g.energy_offered_kwh - g.energy_delivered_kwh).values, g.energy_offered_kwh.values),
            "mean_f_incl_rejected": (g.sum_f.values, (g.n_served + g.n_rejected).values),
            "service_level_incl_rejected": (g.n_f_ge_09.values, (g.n_served + g.n_rejected).values),
            "ev2gym_battery_level_satisfaction_served": ((g.mean_s_ev2gym_served * g.n_served).values,
                                                         g.n_served.values.astype(float)),
            "overload_kwh_per_day": (g.overload_kwh.values, one),
            "days_with_overload_share": (g.overload_day.astype(float).values, one),
            "gross_margin_cop_per_day": (g.gross_margin_cop.values, one)}


def master(cases, level):
    c = cases[np.isclose(cases.level, level)].copy()
    c = c.sort_values(["algorithm", "seed", "eval_day"])
    arms = [a for a in ORDER if a in set(c.algorithm)] + sorted(set(c.algorithm) - set(ORDER))
    by = {a: c[c.algorithm == a].set_index(["seed", "eval_day"]).sort_index() for a in arms}
    idx = by["AFAP"].index
    cl = idx.get_level_values("seed").values
    rows = []
    for a in arms:
        g = by[a].loc[idx]
        r = by[REF].loc[idx]
        o = {"level": level, "algorithm": a, "causal": bool(g.causal.iloc[0]), "n_cases": len(g)}
        ma, mr = metrics(g), metrics(r)
        for m, (num, den) in ma.items():
            x = rci(num, den, cl)
            d = rci(mr[m][0], mr[m][1], cl, num, den)
            o.update({m: x["point_estimate"], f"{m}_ci_halfwidth": (x["ci_high"] - x["ci_low"]) / 2,
                      f"{m}_ci_low": x["ci_low"], f"{m}_ci_high": x["ci_high"],
                      f"{m}_diff_vs_RR-TA": d["point_estimate"], f"{m}_diff_ci_low": d["ci_low"],
                      f"{m}_diff_ci_high": d["ci_high"]})
        e_afap = by["AFAP"].loc[idx].energy_delivered_kwh.values
        x = rci(e_afap - g.energy_delivered_kwh.values, e_afap, cl)
        o.update({"ens_rel": x["point_estimate"], "ens_rel_ci_low": x["ci_low"], "ens_rel_ci_high": x["ci_high"]})
        o["days_with_overload"] = int(g.overload_day.sum())
        o["peak_kw_p95"] = float(np.quantile(g.peak_station_kw, 0.95))
        o["peak_kw_max"] = float(g.peak_station_kw.max())
        o["target_satisfaction_met"] = bool(o["mean_f_incl_rejected_ci_low"] >= 0.90)
        o["target_dns_met"] = bool(o["dns_exact_ci_high"] <= 0.15)
        o["target_overload_met"] = o["days_with_overload"] == 0
        o["n_clusters"] = len(np.unique(cl))
        o["statistics"] = STATS_NOTE
        rows.append(o)
    return pd.DataFrame(rows)


def load_cases():
    parts = [pd.read_csv(f"{C}/c1_cases.csv")]
    if os.path.exists(f"{C}/td3_cases.csv"):
        t = pd.read_csv(f"{C}/td3_cases.csv")
        t = t[~t.algorithm.str.startswith("TD3_safe_long_")]  # long-budget sensitivity: scripts/review_C3_long.py
        # The carried model (results/review_td3_safe_selection.json, rule config_safe.CARRIED_MODEL_RULE,
        # validation only) is reported as "TD3_safe"; the other seeds keep TD3_safe_ts<seed> (dispersion).
        sel = "results/review_td3_safe_selection.json"
        if os.path.exists(sel):
            carried = f"TD3_safe_ts{json.load(open(sel))['carried_model']['train_seed']}"
            t.loc[t.algorithm == carried, "algorithm"] = "TD3_safe"
        parts.append(t)
    c = pd.concat(parts, ignore_index=True)
    c["level"] = c.config_name.map(level_of)
    return c


def main():
    cases = load_cases()
    out = []
    for lv in sorted(cases.level.unique()):
        t = master(cases, lv)
        t.to_csv(f"results/review_C_master_{lv:.1f}x.csv", index=False)
        out.append(t)
        print(t[["algorithm", "energy_kwh_per_day", "ens_rel", "dns_exact", "mean_f_incl_rejected",
                 "service_level_incl_rejected", "overload_kwh_per_day", "days_with_overload", "peak_kw_p95",
                 "gross_margin_cop_per_day"]].round(3).to_string())
    pd.concat(out).to_csv(f"{C}/C6_master_all_levels.csv", index=False)


if __name__ == "__main__":
    main()
