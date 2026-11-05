"""
Week 8 advisor review, Gate 1 analysis (see scripts/review_gate1.py for the
variants). Every statistic: cluster bootstrap over the scenario seed
(n_clusters = 50), 10,000 resamples, percentile interval; energy
percentages and per-driver means as ratios of totals recomputed inside each
resample (A2 rule, ev2gym_thesis/stats_utils.cluster_bootstrap_ratio).

Outputs (experiments/phase4_review/gate1/):
  gate1_side_by_side.csv   1.0x, 8 ports, AFAP and RR-TA, V0-V3
  gate1_capacity.csv       RR-TA (and AFAP) by variant x level x ports, with
                           the breaking criteria of the Final capacity brief
                           (old) and of the Week 8 brief C4 (new)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as ratio_ci

D = "experiments/phase4_review/gate1"
DEAD_STEPS = 2  # EV2Gym's spawner: a port is reusable 2 steps after the departure step (measured)
T = 96


def add_fields(df):
    df = df.copy()
    st = df.arrival_model == "station_poisson"
    for b in ("lower", "upper"):  # station rows: exact, both "bounds" equal the observed value
        df.loc[st, f"arrivals_rejected_{b}"] = df.loc[st, "arrivals_rejected"]
        df.loc[st, f"energy_offered_{b}_kwh"] = df.loc[st, "energy_offered_kwh"]
        df.loc[st, f"arrivals_offered_{b}"] = df.loc[st, "arrivals_offered"]
        df[f"undelivered_{b}"] = df[f"energy_offered_{b}_kwh"] - df.energy_delivered_kwh
        df[f"n_all_{b}"] = df.n_served + df[f"arrivals_rejected_{b}"]
        df[f"sum_s_all_{b}"] = df.average_user_satisfaction * df.n_served  # EV2Gym s, rejected = 0 (closure rule)
    df["sum_f"] = df.mean_f_served * df.n_served
    df["n_f_ok"] = df.service_level_served * df.n_served
    df["port_steps"] = df.ports * T
    df["blocked_port_steps"] = np.minimum(df.connected_port_steps + DEAD_STEPS * df.n_served, df.port_steps)
    return df


def ci(num, den, cl):
    r = ratio_ci(num, den, cl)
    return r["point_estimate"], r["ci_low"], r["ci_high"]


def summarize(g, afap=None):
    cl = g.seed.values
    one = np.ones(len(g))
    out = {"n_cases": len(g), "n_clusters": g.seed.nunique()}
    def put(name, num, den=None):
        p, lo, hi = ci(num, one if den is None else den, cl)
        out.update({name: p, f"{name}_ci_low": lo, f"{name}_ci_high": hi})
    for b in ("lower", "upper"):
        put(f"arrivals_offered_per_day_{b}", g[f"arrivals_offered_{b}"].values)
        put(f"energy_offered_kwh_per_day_{b}", g[f"energy_offered_{b}_kwh"].values)
        put(f"arrivals_rejected_per_day_{b}", g[f"arrivals_rejected_{b}"].values)
        put(f"dns_{b}", g[f"undelivered_{b}"].values, g[f"energy_offered_{b}_kwh"].values)
        put(f"mean_f_all_{b}", g.sum_f.values, g[f"n_all_{b}"].values)
        put(f"service_level_all_{b}", g.n_f_ok.values, g[f"n_all_{b}"].values)
        put(f"ev2gym_satisfaction_all_{b}", g[f"sum_s_all_{b}"].values, g[f"n_all_{b}"].values)
    put("evs_served_per_day", g.n_served.values)
    put("mean_f_served", g.sum_f.values, g.n_served.values)
    put("service_level_served", g.n_f_ok.values, g.n_served.values)
    put("ev2gym_satisfaction_served", (g.average_user_satisfaction * g.n_served).values, g.n_served.values)
    put("port_occupancy", g.connected_port_steps.values, g.port_steps.values)
    put("port_occupancy_incl_dead_time", g.blocked_port_steps.values, g.port_steps.values)
    put("energy_delivered_kwh_per_day", g.energy_delivered_kwh.values)
    put("overload_kwh_per_day", g.overload_kwh.values)
    put("days_with_overload_share", g.overload_day.astype(float).values)
    put("gross_margin_cop_per_day", g.gross_margin_cop.values)
    if afap is not None:
        a = afap.set_index("run_key").loc[g.run_key]
        put("ens_rel", (a.energy_delivered_kwh.values - g.energy_delivered_kwh.values), a.energy_delivered_kwh.values)
    per_seed_peak = g.groupby("seed").peak_station_kw.max().values
    out["peak_kw_p95_over_seeds"] = float(np.quantile(per_seed_peak, 0.95))
    rng = np.random.default_rng(0)
    boots = np.quantile(per_seed_peak[rng.integers(0, len(per_seed_peak), (10000, len(per_seed_peak)))], 0.95, axis=1)
    out["peak_kw_p95_ci_high"] = float(np.quantile(boots, 0.975))
    out["peak_kw_max"] = float(g.peak_station_kw.max())
    return out


def main():
    df = add_fields(pd.read_csv(os.path.join(D, "gate1_cases.csv")))
    df["run_key"] = df.variant + "|" + df.level.astype(str) + "|" + df.ports.astype(str) + "|" + \
        df.seed.astype(str) + "|" + df.eval_day
    rows = []
    for (v, lv, p), g in df.groupby(["variant", "level", "ports"]):
        afap = g[g.algorithm == "AFAP"]
        for arm, ga in g.groupby("algorithm"):
            r = {"variant": v, "level": lv, "ports": p, "algorithm": arm}
            r.update(summarize(ga, afap))
            rating = 100.0
            # Old criteria (Final capacity brief): EV2Gym satisfaction incl. rejected (lower-bound count) CI low >= 0.90,
            # DNS (lower bound) CI high <= 0.15, P95 peak CI high <= rating.
            r["old_broken_satisfaction"] = r["ev2gym_satisfaction_all_lower_ci_low"] < 0.90
            r["old_broken_dns"] = r["dns_lower_ci_high"] > 0.15
            r["broken_peak"] = r["peak_kw_p95_ci_high"] > rating + 1e-6
            r["old_meets_all"] = not (r["old_broken_satisfaction"] or r["old_broken_dns"] or r["broken_peak"])
            # Week 8 C4 criteria: DNS CI high <= 0.15 and mean f incl. rejected CI low >= 0.90 (A1 target).
            r["new_broken_dns"] = r["dns_lower_ci_high"] > 0.15
            r["new_broken_f"] = r["mean_f_all_lower_ci_low"] < 0.90
            r["new_meets_all"] = not (r["new_broken_dns"] or r["new_broken_f"] or r["broken_peak"])
            rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(D, "gate1_capacity.csv"), index=False)
    sbs = out[(out.level == 1.0) & (out.ports == 8)].sort_values(["algorithm", "variant"])
    sbs.to_csv(os.path.join(D, "gate1_side_by_side.csv"), index=False)
    cols = ["variant", "algorithm", "arrivals_offered_per_day_lower", "arrivals_offered_per_day_upper",
            "energy_offered_kwh_per_day_lower", "energy_offered_kwh_per_day_upper", "evs_served_per_day",
            "arrivals_rejected_per_day_lower", "arrivals_rejected_per_day_upper", "port_occupancy",
            "port_occupancy_incl_dead_time", "dns_lower", "dns_upper", "ens_rel", "mean_f_served",
            "mean_f_all_lower", "mean_f_all_upper", "service_level_all_lower", "ev2gym_satisfaction_all_lower",
            "overload_kwh_per_day", "gross_margin_cop_per_day", "energy_delivered_kwh_per_day"]
    pd.set_option("display.width", 250)
    print(sbs[cols].round(3).T.to_string())
    cap = out[out.algorithm == "RR-TA"][["variant", "level", "ports", "dns_lower", "dns_lower_ci_high",
                                         "mean_f_all_lower", "mean_f_all_lower_ci_low",
                                         "ev2gym_satisfaction_all_lower_ci_low", "peak_kw_p95_ci_high",
                                         "old_meets_all", "new_meets_all"]]
    print(cap.round(3).to_string())


if __name__ == "__main__":
    main()
