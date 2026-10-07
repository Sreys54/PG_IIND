"""
Closure brief, Part E3: exactly how the Week 7 "37%" voltage result is
computed, with a CI on the ratio itself.

Definition (scripts/analyze_week7_infra.py::voltage_attribution):
  per run, delta_min_voltage = (minimum per-unit voltage over all 34 buses and
  all simulated steps of the arm's run) - (the same minimum for the
  idle-station run of the same setting, seed and day).
  "Contribution" = that delta (<= 0: the station lowers the feeder minimum).
  Reduction of Round Robin vs AFAP = 1 - sum(delta_RR) / sum(delta_AFAP) over
  the 100 paired base-setting runs (a ratio of means).
CI: the ratio's CI resamples the 50 scenario seeds with replacement (10,000
draws, seed 0) -- the same cluster unit as paired_cluster_bootstrap_ci, which
gives the CI of the paired difference.

Usage: PYTHONPATH=. python scripts/closure_voltage_contribution.py
"""
import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

OUT = "results/closure_voltage_contribution.csv"


def main():
    m = pd.read_csv("results/week7_voltage_attribution_by_run.csv")
    rows = []
    for setting, b in m.groupby("setting"):
        a = b[b.algorithm == "ChargeAsFastAsPossible"]
        r = b[b.algorithm == "RoundRobin"]
        p = a.merge(r, on=["seed", "eval_day"], suffixes=("_a", "_r"))
        d = paired_cluster_bootstrap_ci(p.delta_min_voltage_pu_a, p.delta_min_voltage_pu_r, p.seed,
                                        n_bootstrap=10_000, seed=0)
        g = p.groupby("seed")
        A, R = g.delta_min_voltage_pu_a.sum(), g.delta_min_voltage_pu_r.sum()
        rng = np.random.default_rng(0)
        seeds = A.index.values
        boots = []
        for _ in range(10_000):
            s = rng.choice(seeds, len(seeds))
            boots.append(1 - R[s].sum() / A[s].sum())
        rows.append({"setting": setting, "n_pairs": len(p), "n_clusters": d["n_clusters"],
                     "afap_delta_min_v_mean": p.delta_min_voltage_pu_a.mean(),
                     "rr_delta_min_v_mean": p.delta_min_voltage_pu_r.mean(),
                     "diff_rr_minus_afap": d["point_estimate"], "diff_ci_low": d["ci_low"], "diff_ci_high": d["ci_high"],
                     "rr_reduction_vs_afap": 1 - R.sum() / A.sum(),
                     "reduction_ci_low": float(np.quantile(boots, 0.025)),
                     "reduction_ci_high": float(np.quantile(boots, 0.975)),
                     "afap_runs_worst_bus_is_station_bus": int((p.worst_bus_a == 27).sum())})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out.round(5).to_string(index=False))


if __name__ == "__main__":
    main()
