"""
Last run, analysis of Parts 2, 3 and 5.1 (post-processing only; nothing is
written to any registry). Everything uses 42-minute DC sessions, 8 ports
and 100 kW, at 1.0x / 1.3x / 1.6x (configs station_v0_bogota_dc42_sp{30,39,48}).

Part 2: MPC_TrackingG2V and Optimal_Oracle_Tracking (non-causal upper bounds:
both know departure times) against the transformer-aware Round Robin
(RoundRobin_TransformerCapped).
  - Each arm's compliance metrics: scripts/analyze_dwell_capacity.py::summarize.
  - Paired differences (bound minus transformer-aware Round Robin) by
    paired_cluster_bootstrap_ci over the scenario seed (n_clusters = 50),
    for DNS, satisfaction counting rejected arrivals, energy delivered,
    overload and margin.
  - MPC infeasibility: the count of "INFEASIBLE at step" lines that the
    thesis wrapper (ev2gym_thesis/mpc/tracking_mpc.py) prints. Each is a step
    where it applied zero power. Counted from the worker logs.
  -> results/dwell_last_bounds_vs_rrta.csv

Part 3: node_123 voltage (scripts/dwell_ieee123_voltage.py), the closure E2
method:
  - the drop in the feeder's daily minimum voltage relative to the idle run of
    the same (level, seed, day);
  - the transformer-aware Round Robin's reduction of that drop vs AFAP, as a
    ratio of seed sums, with a seed-resampling CI;
  - a check that station energy at every level equals the non-grid dwell rows
    (EV2Gym has no feedback from the feeder to the station).
  -> results/dwell_last_voltage_node123.csv

Part 5.1: the final compliance table, 6 arms x 3 levels, statuses met /
not met / not evaluable (with reason).
  -> results/dwell_last_final_compliance.csv

Usage: PYTHONPATH=. python scripts/analyze_last_run.py
"""
import glob
import os
import re

import numpy as np
import pandas as pd

from scripts import analyze_dwell_capacity as adc
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

RR_TA = "RoundRobin_TransformerCapped"
BOUNDS = ["MPC_TrackingG2V", "Optimal_Oracle_Tracking"]
FINAL_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", RR_TA, "MPC_TrackingG2V", "Optimal_Oracle_Tracking",
              "TD3_vanilla_extended_ts102"]
LABEL = {"ChargeAsFastAsPossible": "AFAP", "RoundRobin": "Round Robin (EV2Gym, follows the setpoint)",
         RR_TA: "Round Robin, transformer-aware (recommended)", "MPC_TrackingG2V": "MPC_TrackingG2V (upper bound, non-causal)",
         "Optimal_Oracle_Tracking": "Optimal_Oracle_Tracking (upper bound, non-causal)",
         "TD3_vanilla_extended_ts102": "Final RL model (out of its training distribution)"}
CONFIGS = {"station_v0_bogota_dc42_sp30": 1.0, "station_v0_bogota_dc42_sp39": 1.3, "station_v0_bogota_dc42_sp48": 1.6}
SHARDS = "experiments/phase3_infra_replicability/results/dwell_shards"
TMP = "experiments/phase3_infra_replicability/results/dwell_shards/_last_reference_rows.csv"


def load_reference_rows():
    reg = pd.read_csv(adc.REG, low_memory=False)
    reg[reg.config_name.isin(CONFIGS)].to_csv(TMP, index=False)
    adc.REG = TMP  # adc.load() reads only the three reference configs
    try:
        return adc.load()
    finally:
        adc.REG = "results/dwell_registry.csv"


def ci(a, b, clusters):
    r = paired_cluster_bootstrap_ci(np.asarray(a, float), np.asarray(b, float), np.asarray(clusters),
                                    n_bootstrap=10_000, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def mpc_infeasible_steps():
    n = 0
    for p in glob.glob(f"{SHARDS}/last_bounds_*.log"):
        n += len(re.findall(r"INFEASIBLE at step", open(p, encoding="utf-8", errors="replace").read()))
    return n


# doc:begin last_bounds
def bounds_table(m):
    rows = []
    n_inf = mpc_infeasible_steps()
    for lvl in (1.0, 1.3, 1.6):
        sub = m[m.level == lvl]
        ref = sub[sub.algorithm == RR_TA]
        for arm in [RR_TA] + BOUNDS:
            g = sub[sub.algorithm == arm]
            assert len(g) == 100, (lvl, arm, len(g))
            row = {"level": lvl, "algorithm": arm, "label": LABEL[arm], **adc.summarize(g, 100.0)}
            if arm != RR_TA:
                p = ref.merge(g, on=["seed", "eval_day"], suffixes=("_ref", ""))
                for col in ["dns_lower", "sat_all_arrivals", "total_energy_charged", "total_transformer_overload",
                            "gross_margin_cop"]:
                    pt, lo, hi, _ = ci(p[col + "_ref"], p[col], p.seed)
                    row.update({f"diff_{col}_vs_rrta": pt, f"diff_{col}_ci_low": lo, f"diff_{col}_ci_high": hi})
            rows.append(row)
    out = pd.DataFrame(rows)
    n_mpc = len(m[m.algorithm == "MPC_TrackingG2V"])
    out["mpc_infeasible_steps_all_levels"] = np.where(out.algorithm == "MPC_TrackingG2V", n_inf, np.nan)
    out["mpc_infeasible_share_of_steps"] = np.where(out.algorithm == "MPC_TrackingG2V", n_inf / (96 * n_mpc), np.nan)
    out.to_csv("results/dwell_last_bounds_vs_rrta.csv", index=False)
    return out
# doc:end last_bounds


# doc:begin last_voltage
def voltage_table():
    d = pd.read_csv("results/dwell_ieee123_voltage_by_run.csv")
    idle = d[d.algorithm == "idle"].set_index(["level", "seed", "eval_day"])
    runs = d[d.algorithm != "idle"].copy()
    runs["idle_min_v"] = [idle.loc[(l, s, e), "min_voltage_pu"] for l, s, e in zip(runs.level, runs.seed, runs.eval_day)]
    runs["delta_min_v"] = runs.min_voltage_pu - runs.idle_min_v
    reg = pd.read_csv("results/dwell_registry.csv", low_memory=False)
    reg = reg[reg.config_name.isin(CONFIGS)].assign(level=lambda x: x.config_name.map(CONFIGS),
                                                     seed=lambda x: x.seed.astype(float).astype(int))
    chk = runs.merge(reg[["level", "algorithm", "seed", "eval_day", "total_energy_charged"]],
                     on=["level", "algorithm", "seed", "eval_day"], suffixes=("", "_nongrid"))
    max_diff = float((chk.total_energy_charged - chk.total_energy_charged_nongrid).abs().max())
    assert len(chk) == len(runs) and max_diff < 1e-6, (len(chk), len(runs), max_diff)
    rows = []
    for (lvl, arm), g in runs.groupby(["level", "algorithm"]):
        r = paired_cluster_bootstrap_ci(np.zeros(len(g)), g.delta_min_v.values, g.seed.values, n_bootstrap=10_000, seed=0)
        rows.append({"level": lvl, "algorithm": arm, "n_runs": len(g), "n_clusters": r["n_clusters"],
                     "idle_cells_out_of_band": int((idle.loc[lvl].n_bus_steps_outside > 0).sum()),
                     "cells_out_of_band": int((g.n_bus_steps_outside > 0).sum()),
                     "band_compliance_all_cells": bool((g.n_bus_steps_outside == 0).all()),
                     "min_voltage_pu_worst": g.min_voltage_pu.min(), "min_voltage_pu_mean": g.min_voltage_pu.mean(),
                     "station_bus_min_voltage_pu_worst": g.station_bus_min_voltage_pu.min(),
                     "delta_min_v_mean": r["point_estimate"], "delta_min_v_ci_low": r["ci_low"],
                     "delta_min_v_ci_high": r["ci_high"], "margin_to_band_pu_worst": g.min_voltage_pu.min() - 0.95,
                     "station_energy_max_abs_diff_vs_nongrid_kwh": max_diff})
    out = pd.DataFrame(rows)
    red = []
    for lvl in sorted(runs.level.unique()):
        a = runs[(runs.level == lvl) & (runs.algorithm == "ChargeAsFastAsPossible")]
        r = runs[(runs.level == lvl) & (runs.algorithm == RR_TA)]
        p = a.merge(r, on=["seed", "eval_day"], suffixes=("_a", "_r"))
        A, R = p.groupby("seed").delta_min_v_a.sum(), p.groupby("seed").delta_min_v_r.sum()
        rng = np.random.default_rng(0)
        boots = [1 - R[s].sum() / A[s].sum() for s in (rng.choice(A.index.values, len(A)) for _ in range(10_000))]
        red.append({"level": lvl, "rrta_reduction_vs_afap": 1 - R.sum() / A.sum(),
                    "reduction_ci_low": float(np.quantile(boots, 0.025)),
                    "reduction_ci_high": float(np.quantile(boots, 0.975))})
    out = out.merge(pd.DataFrame(red), on="level", how="left")
    out.loc[out.algorithm != RR_TA, ["rrta_reduction_vs_afap", "reduction_ci_low", "reduction_ci_high"]] = np.nan
    out.to_csv("results/dwell_last_voltage_node123.csv", index=False)
    return out
# doc:end last_voltage


# doc:begin last_compliance
def final_compliance(m, volt):
    adc.ARMS = FINAL_ARMS
    comp = adc.compliance(m)  # writes results/dwell_e_target_compliance.csv (now with all six arms)
    comp["label"] = comp.algorithm.map(LABEL)
    v = volt.set_index(["level", "algorithm"])
    status, reason = [], []
    for _, r in comp.iterrows():
        if (r.level, r.algorithm) in v.index:
            x = v.loc[(r.level, r.algorithm)]
            status.append("met on node_123" if x.band_compliance_all_cells else "not met on node_123")
            reason.append(f"node_123 (in band idle), bus 115, weekday only, 50 seeds: {int(x.cells_out_of_band)}/50 "
                          f"cells out of band, lowest bus {x.min_voltage_pu_worst:.4f} p.u.")
        else:
            status.append("not evaluated")
            reason.append("not rerun on node_123 under DC sessions (the brief's Part 3 covers AFAP and the "
                          "transformer-aware Round Robin); the 34-node feeder is out of band when idle")
    comp["voltage_status"], comp["voltage_reason"] = status, reason
    comp.to_csv("results/dwell_last_final_compliance.csv", index=False)
    return comp
# doc:end last_compliance


def main():
    m = load_reference_rows()
    b = bounds_table(m)
    v = voltage_table()
    c = final_compliance(m, v)
    os.remove(TMP)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 40)
    print(b[["level", "algorithm", "dns_lower_mean", "dns_lower_ci_high", "sat_all_arrivals_mean", "sat_all_arrivals_ci_low",
             "total_energy_charged_mean", "cells_with_overload", "peak_kw_p95", "gross_margin_cop_mean",
             "diff_dns_lower_vs_rrta", "diff_dns_lower_ci_low", "diff_dns_lower_ci_high",
             "diff_gross_margin_cop_vs_rrta", "diff_gross_margin_cop_ci_low", "diff_gross_margin_cop_ci_high",
             "mpc_infeasible_share_of_steps"]].round(4).to_string(index=False))
    print(v.round(5).to_string(index=False))
    print(c[["level", "algorithm", "sat_served_status", "sat_all_arrivals_status", "sat_all_arrivals_mean",
             "ens_rel_served_status", "ens_rel_served_pct", "dns_status", "dns_lower_mean", "transformer_status",
             "cells_with_overload", "voltage_status"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
