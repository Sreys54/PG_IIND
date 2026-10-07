"""
Closure brief, Part E2 analysis: voltage of AFAP and Round Robin on EV2Gym's
123-bus feeder (station on bus 115), which is inside the +/-5% band with the
station idle -- so absolute band compliance is evaluable here, unlike on the
34-node feeder.

Per level x arm (50 runs, 50 seeds x the weekday EVAL_DAY only -- the
weekend day is excluded, see scripts/closure_ieee123_voltage.py; cluster bootstrap over the
seed, n_clusters reported):
  - cells with any bus outside 0.95-1.05 p.u. (absolute compliance: met only
    if 0 of 100 cells);
  - minimum voltage over all buses and steps; the station bus's minimum;
  - the drop in the feeder minimum relative to the idle run of the same
    (seed, day), and Round Robin's reduction of that drop vs AFAP (ratio of
    means, seed-resampled CI);
  - station metrics vs the non-grid rows of the same cell (asserted equal at
    1.0x: EV2Gym has no feeder-to-station feedback).

Usage: PYTHONPATH=. python scripts/analyze_closure_ieee123.py
"""
import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

OUT = "results/closure_ieee123_voltage.csv"


def mean_ci(x, clusters):
    r = paired_cluster_bootstrap_ci(np.zeros(len(x)), np.asarray(x, float), np.asarray(clusters),
                                    n_bootstrap=10_000, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def main():
    d = pd.read_csv("results/closure_ieee123_voltage_by_run.csv")
    idle = d[d.algorithm == "idle"].set_index(["level", "seed", "eval_day"])
    runs = d[d.algorithm != "idle"].copy()
    # idle baseline matched per (level, seed, day): see closure_ieee123_voltage.py
    runs["idle_min_v"] = [idle.loc[(l, s, e), "min_voltage_pu"] for l, s, e in zip(runs.level, runs.seed, runs.eval_day)]
    runs["delta_min_v"] = runs.min_voltage_pu - runs.idle_min_v

    # no-feedback check: station energy at 1.0x equals the non-grid registry rows
    reg = pd.read_csv("results/master_results.csv", low_memory=False)
    reg = reg[(reg.config_name == "station_v0_bogota") & (reg.analysis_row.astype(str) == "True")]
    reg = reg.assign(seed=reg.seed.astype(float).astype(int))[["algorithm", "seed", "eval_day", "total_energy_charged"]]
    m = runs[runs.level == 1.0].merge(reg, on=["algorithm", "seed", "eval_day"], suffixes=("", "_nongrid"))
    diff = (m.total_energy_charged - m.total_energy_charged_nongrid.astype(float)).abs().max()
    print(f"1.0x station energy vs non-grid rows: {len(m)} runs, max abs diff {diff:.6g} kWh")
    assert len(m) == 100 and diff < 1e-6

    rows = []
    for (lvl, arm), g in runs.groupby(["level", "algorithm"]):
        dv, lo, hi, nc = mean_ci(g.delta_min_v, g.seed)
        rows.append({"level": lvl, "algorithm": arm, "n_runs": len(g), "n_clusters": nc,
                     "idle_cells_out_of_band": int((idle.loc[lvl].n_bus_steps_outside > 0).sum()),
                     "cells_out_of_band": int((g.n_bus_steps_outside > 0).sum()),
                     "bus_steps_out_of_band_total": int(g.n_bus_steps_outside.sum()),
                     "band_compliance_all_cells": bool((g.n_bus_steps_outside == 0).all()),
                     "min_voltage_pu_worst": g.min_voltage_pu.min(), "min_voltage_pu_mean": g.min_voltage_pu.mean(),
                     "station_bus_min_voltage_pu_worst": g.station_bus_min_voltage_pu.min(),
                     "delta_min_v_mean": dv, "delta_min_v_ci_low": lo, "delta_min_v_ci_high": hi,
                     "margin_to_band_pu_worst": g.min_voltage_pu.min() - 0.95})
    out = pd.DataFrame(rows)
    red = []
    for lvl in sorted(runs.level.unique()):
        a = runs[(runs.level == lvl) & (runs.algorithm == "ChargeAsFastAsPossible")]
        r = runs[(runs.level == lvl) & (runs.algorithm == "RoundRobin")]
        p = a.merge(r, on=["seed", "eval_day"], suffixes=("_a", "_r"))
        A, R = p.groupby("seed").delta_min_v_a.sum(), p.groupby("seed").delta_min_v_r.sum()
        rng = np.random.default_rng(0)
        boots = [1 - R[s].sum() / A[s].sum() for s in (rng.choice(A.index.values, len(A)) for _ in range(10_000))]
        red.append({"level": lvl, "rr_reduction_vs_afap": 1 - R.sum() / A.sum(),
                    "reduction_ci_low": float(np.quantile(boots, 0.025)),
                    "reduction_ci_high": float(np.quantile(boots, 0.975))})
    out = out.merge(pd.DataFrame(red), on="level", how="left")
    out.loc[out.algorithm != "RoundRobin", ["rr_reduction_vs_afap", "reduction_ci_low", "reduction_ci_high"]] = np.nan
    out.to_csv(OUT, index=False)
    pd.set_option("display.width", 250)
    print(out.round(5).to_string(index=False))


if __name__ == "__main__":
    main()
