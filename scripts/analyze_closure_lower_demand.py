"""
Closure brief, Part D3: does lower demand ever worsen overload or demand not
served under Round Robin? Paired by (scenario seed, day) between consecutive
demand levels 0.5x -> 0.733x -> 1.0x (8 ports, 100 kW), from
results/closure_demand_not_served_by_run.csv (DNS, lower bound) and the
registry (overload, satisfaction). Cluster bootstrap over the seed.

Usage: PYTHONPATH=. python scripts/analyze_closure_lower_demand.py
"""
import pandas as pd

from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

LEVELS = [0.5, 0.75, 1.0]   # 0.75 = spawn 22 = 0.733x
OUT = "results/closure_lower_demand_monotonicity.csv"


def main():
    d = pd.read_csv("results/closure_demand_not_served_by_run.csv")
    reg = pd.read_csv("results/master_results.csv", low_memory=False)[
        ["run_id", "total_transformer_overload", "average_user_satisfaction"]]
    d = d.merge(reg, on="run_id", how="left")
    d = d[d.algorithm == "RoundRobin"]
    rows = []
    for lo, hi in zip(LEVELS[:-1], LEVELS[1:]):
        a = d[d.level == lo].set_index(["seed", "eval_day"])
        b = d[d.level == hi].set_index(["seed", "eval_day"])
        p = a.join(b, lsuffix="_lo", rsuffix="_hi", how="inner").reset_index()
        assert len(p) == 100, (lo, hi, len(p))
        for col in ["dns_lower", "total_transformer_overload", "average_user_satisfaction"]:
            r = paired_cluster_bootstrap_ci(p[col + "_lo"], p[col + "_hi"], p.seed, n_bootstrap=10_000, seed=0)
            rows.append({"from_level": lo, "to_level": hi, "metric": col,
                         "mean_low_demand": p[col + "_lo"].mean(), "mean_high_demand": p[col + "_hi"].mean(),
                         "diff_high_minus_low": r["point_estimate"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                         "cells_where_lower_demand_is_worse": int(
                             ((p[col + "_lo"] < p[col + "_hi"]) if col == "average_user_satisfaction"
                              else (p[col + "_lo"] > p[col + "_hi"])).sum()),
                         "n_clusters": r["n_clusters"]})
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
