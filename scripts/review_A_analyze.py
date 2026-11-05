"""
Week 8 advisor review, Block A analysis, from the instrumented re-simulation
(scripts/review_A_resim.py -> experiments/phase4_review/A/A_cases.csv) and
the stored censoring files.

Statistics: cluster bootstrap over the scenario seed (n_clusters = 50),
10,000 resamples, percentile intervals, per comparison (no multiplicity
adjustment in Block A; stated in every sheet). Energy percentages and
per-driver means are ratios of totals recomputed inside each resample
(A2 rule, ev2gym_thesis/stats_utils.cluster_bootstrap_ratio).

Rejected drivers (A1, A7): EV2Gym's spawner never generates them, so their
number is the censoring reconstruction's bound: lower (only arrivals no free
port could absorb) and upper (every successful draw on a blocked port);
long-dwell from results/closure_censoring_by_cell.csv (level 1.0), DC from
results/dwell_censoring_by_cell.csv (8 ports, 100 kW).

Output CSVs: experiments/phase4_review/A/A1_*.csv, A4_*.csv, A7_*.csv,
A8_*.csv (assembled into results/review_A_post_processing.xlsx by
scripts/review_A_workbook.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci

D = "experiments/phase4_review/A"
UNIT_MARGIN = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
DC_SPAWN = {1.0: 30, 1.3: 39, 1.6: 48}
STATS_NOTE = "cluster bootstrap over scenario seed, 10,000 resamples, percentile, per comparison"
# EV2Gym's total_transformer_overload sums the overload kW of every step (ev2gym_env.py line 526,
# utils.py line 26) without the step length: at 15-min steps it is 4 x the energy in kWh
# (verified on all 1,310 re-simulated cases with overload: ratio 4.000). Converted here.
KW_STEPS_TO_KWH = 15 / 60


def load():
    c = pd.read_csv(os.path.join(D, "A_cases.csv"))
    long_c = pd.read_csv("results/closure_censoring_by_cell.csv")
    long_c = long_c[np.isclose(long_c.level, 1.0)][["seed", "eval_day", "rejected_lower", "rejected_upper",
                                                    "energy_rejected_lower_kwh", "energy_rejected_upper_kwh",
                                                    "requested_served_kwh"]].assign(regime="long", level=1.0)
    dc = pd.read_csv("results/dwell_censoring_by_cell.csv")
    dc = dc[(dc.dwell_mean_min == 42) & (dc.ports == 8) & (dc.transformer_kw == 100) & (~dc.constant_demand)]
    dc = dc[dc.level.isin(DC_SPAWN)][["level", "seed", "eval_day", "rejected_lower", "rejected_upper",
                                      "energy_rejected_lower_kwh", "energy_rejected_upper_kwh",
                                      "requested_served_kwh"]].assign(regime="dc")
    cens = pd.concat([long_c, dc]).drop_duplicates(["regime", "level", "seed", "eval_day"])
    c = c.merge(cens, on=["regime", "level", "seed", "eval_day"], how="left", validate="many_to_one")
    assert c.rejected_lower.notna().all(), "a case without its censoring row"
    assert (np.abs(c.requested_served_kwh - c.sum_requested_kwh) < 1e-6 * c.sum_requested_kwh.clip(lower=1)).all()
    return c


def put(out, name, num, den, cl, num_b=None, den_b=None):
    r = rci(num, den, cl, num_b, den_b)
    out.update({name: r["point_estimate"], f"{name}_ci_low": r["ci_low"], f"{name}_ci_high": r["ci_high"]})
    out["n_clusters"] = r["n_clusters"]


# doc:begin A1_A7
def a1_a7(c):
    rows = []
    for (regime, lv, arm), g in c.groupby(["regime", "level", "algorithm"]):
        cl = g.seed.values
        o = {"regime": regime, "level": lv, "algorithm": arm, "n_cases": len(g)}
        n = g.n_served_rec.values.astype(float)
        put(o, "mean_f_served", g.sum_f.values, n, cl)
        put(o, "service_level_served", g.n_f_ge_09.values, n, cl)
        put(o, "ev2gym_satisfaction_served", g.sum_s_ev2gym.values, n, cl)
        for b in ("lower", "upper"):
            nall = n + g[f"rejected_{b}"].values
            put(o, f"mean_f_all_{b}", g.sum_f.values, nall, cl)
            put(o, f"service_level_all_{b}", g.n_f_ge_09.values, nall, cl)
            put(o, f"ev2gym_satisfaction_all_{b}", g.sum_s_ev2gym.values, nall, cl)
            offered = g[f"energy_rejected_{b}_kwh"].values + g.requested_served_kwh.values
            put(o, f"dns_{b}", offered - g.total_energy_charged.values, offered, cl)
            put(o, f"rejected_per_day_{b}", g[f"rejected_{b}"].values, np.ones(len(g)), cl)
        put(o, "energy_kwh_per_day", g.total_energy_charged.values, np.ones(len(g)), cl)
        put(o, "overload_kwh_per_day", g.total_transformer_overload.values * KW_STEPS_TO_KWH, np.ones(len(g)), cl)
        o["days_with_overload"] = int((g.total_transformer_overload > 0).sum())
        # Advisor's check (3.3): s = 1 - (R/C)(1 - f) per EV; aggregated over served EVs,
        # mean s vs 1 - (sum R / sum C)(1 - sum e / sum R)
        o["advisor_check_s_predicted"] = float(1 - (g.sum_requested_kwh.sum() / g.sum_battery_kwh.sum())
                                              * (1 - g.sum_delivered_kwh.sum() / g.sum_requested_kwh.sum()))
        o["advisor_check_s_observed"] = float(g.sum_s_ev2gym.sum() / n.sum())
        # Targets (anteproyecto), new metric: mean f incl. rejected (lower-bound count) CI low >= 0.90;
        # DNS (lower bound) CI high <= 0.15; zero transformer overload.
        o["target_satisfaction_met"] = bool(o["mean_f_all_lower_ci_low"] >= 0.90)
        o["target_dns_met"] = bool(o["dns_lower_ci_high"] <= 0.15)
        o["target_overload_met"] = bool(o["days_with_overload"] == 0)
        o["statistics"] = STATS_NOTE
        rows.append(o)
    return pd.DataFrame(rows)
# doc:end A1_A7


# doc:begin A4
TD3_PAIRS = [  # (seed, 60k arm, later checkpoint arm, label)
    (100, "TD3_vanilla_new60k_ts100", "TD3_vanilla_extended_ts100", "rule-selected 400k"),
    (100, "TD3_vanilla_new60k_ts100", "TD3_vanilla_extended_last_ts100", "last 480k"),
    (101, "TD3_vanilla_new60k_ts101", "TD3_vanilla_extended_ts101", "rule-selected 630k"),
    (101, "TD3_vanilla_new60k_ts101", "TD3_vanilla_extended_last_ts101", "last 660k"),
    (102, "TD3_vanilla_new60k_ts102", "TD3_vanilla_extended_ts102", "rule-selected 850k (final model)"),
    (102, "TD3_vanilla_new60k_ts102", "TD3_vanilla_extended_last_ts102", "last 910k"),
]
TERMS = ["r_tracking", "r_overload", "r_user", "sq_dev_min_target", "tracking_error"]
FINAL = "TD3_vanilla_extended_ts102"
BASELINES = ["ChargeAsFastAsPossible", "RoundRobin", "RoundRobin_TransformerCapped", "RandomPolicy",
             "MPC_TrackingG2V"]


def a4(c):
    L = c[c.regime == "long"].copy()
    L["reward_total"] = L.r_tracking + L.r_overload + L.r_user
    piv = {m: L.pivot_table(index=["seed", "eval_day"], columns="algorithm", values=m)
           for m in TERMS + ["reward_total", "total_energy_charged", "average_user_satisfaction",
                             "total_transformer_overload"]}
    cl = piv["reward_total"].index.get_level_values("seed").values
    one = np.ones(len(cl))
    per_arm = []
    for arm in piv["reward_total"].columns:
        o = {"algorithm": arm}
        for m in TERMS + ["reward_total"]:
            put(o, m, piv[m][arm].values, one, cl)
        per_arm.append(o)
    diffs = []
    for s, a60, later, label in TD3_PAIRS:
        o = {"train_seed": s, "from": a60, "to": later, "to_label": label}
        for m in TERMS + ["reward_total"]:
            put(o, f"diff_{m}", piv[m][a60].values, one, cl, piv[m][later].values, one)
        diffs.append(o)
    vs = []
    for b in BASELINES:
        o = {"baseline": b, "vs": FINAL}
        put(o, "reward_baseline_minus_td3", piv["reward_total"][FINAL].values, one, cl,
            piv["reward_total"][b].values, one)
        o["baseline_beats_td3_on_its_own_reward"] = bool(o["reward_baseline_minus_td3_ci_low"] > 0)
        vs.append(o)
    return pd.DataFrame(per_arm), pd.DataFrame(diffs), pd.DataFrame(vs)


def a4_td3_vs_random():
    """Paired TD3 850k vs Random on the six Table II metrics (registry rows)."""
    m = pd.read_csv("results/master_results.csv", low_memory=False)
    m = m[(m.analysis_row == True) & (m.config_name == "station_v0_bogota")]
    p = {k: m.pivot_table(index=["seed", "eval_day"], columns="algorithm", values=k)
         for k in ["total_energy_charged", "average_user_satisfaction", "total_transformer_overload",
                   "tracking_error"]}
    cl = p["total_energy_charged"].index.get_level_values("seed").values
    one = np.ones(len(cl))
    E = p["total_energy_charged"]
    rows = []
    for name, a, b, den_a, den_b in [
        ("energy_kwh_per_day", E["RandomPolicy"], E[FINAL], one, one),
        ("ev2gym_satisfaction", p["average_user_satisfaction"]["RandomPolicy"],
         p["average_user_satisfaction"][FINAL], one, one),
        ("ens_rel_ratio_of_totals", E["ChargeAsFastAsPossible"] - E["RandomPolicy"],
         E["ChargeAsFastAsPossible"] - E[FINAL], E["ChargeAsFastAsPossible"], E["ChargeAsFastAsPossible"]),
        ("overload_kwh_per_day", p["total_transformer_overload"]["RandomPolicy"] * KW_STEPS_TO_KWH,
         p["total_transformer_overload"][FINAL] * KW_STEPS_TO_KWH, one, one),
        ("tracking_error_kw2", p["tracking_error"]["RandomPolicy"], p["tracking_error"][FINAL], one, one),
        ("gross_margin_cop_per_day", E["RandomPolicy"] * UNIT_MARGIN, E[FINAL] * UNIT_MARGIN, one, one)]:
        r = rci(np.asarray(a, float), np.asarray(den_a, float), cl, np.asarray(b, float), np.asarray(den_b, float))
        ra = rci(np.asarray(a, float), np.asarray(den_a, float), cl)
        rb = rci(np.asarray(b, float), np.asarray(den_b, float), cl)
        rows.append({"metric": name, "random": ra["point_estimate"], "td3_final": rb["point_estimate"],
                     "diff_td3_minus_random": r["point_estimate"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                     "significant": bool(r["ci_low"] > 0 or r["ci_high"] < 0), "n_clusters": r["n_clusters"],
                     "statistics": STATS_NOTE})
    return pd.DataFrame(rows)
# doc:end A4


def a8_dc_peaks(c):
    rows = []
    for (lv, arm), g in c[c.regime == "dc"].groupby(["level", "algorithm"]):
        peak_day = g.peak_station_kw.values
        rows.append({"level": lv, "algorithm": arm, "n_cases": len(g),
                     "peak_kw_p95_over_cases": float(np.quantile(peak_day, 0.95)),
                     "peak_kw_max_over_cases": float(peak_day.max()),
                     "peak_kw_mean": float(peak_day.mean()),
                     "days_above_rating": int((g.overload_steps > 0).sum()),
                     "days_peak_above_100kw": int((peak_day > 100.0 + 1e-6).sum())})
    return pd.DataFrame(rows)


def main():
    c = load()
    a1_a7(c).to_csv(os.path.join(D, "A1_A7_service_and_dns.csv"), index=False)
    per_arm, diffs, vs = a4(c)
    per_arm.to_csv(os.path.join(D, "A4_reward_terms_by_arm.csv"), index=False)
    diffs.to_csv(os.path.join(D, "A4_reward_terms_850k_minus_60k.csv"), index=False)
    vs.to_csv(os.path.join(D, "A4_posthoc_reward_vs_td3.csv"), index=False)
    a4_td3_vs_random().to_csv(os.path.join(D, "A4_td3_vs_random.csv"), index=False)
    a8_dc_peaks(c).to_csv(os.path.join(D, "A8_dc_peaks.csv"), index=False)
    print("done")


if __name__ == "__main__":
    main()
