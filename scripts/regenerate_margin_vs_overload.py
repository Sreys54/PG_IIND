"""
Closure brief, Part A.2: regenerate results/week5_margin_vs_overload.csv from
the CURRENT statistical rows (analysis_row=True, station_v0_bogota, 50 seeds
x 2 day types), with the same columns as the stale file.

The original file (used by 05 S5.1 and S5.8: Round Robin 503.9 COP/day,
AFAP overload 13.25 kWh) predates the Week 5 Gate 4 grid regeneration and had
no generator script in the repo. This script is that generator. Margins use
Week 5's own economics (analyze_week5_results.load_economics_df, Bogota
constants). A cluster-bootstrap companion with CIs and n_clusters is written
to results/closure_margin_vs_overload_ci.csv.

Usage: PYTHONPATH=. python scripts/regenerate_margin_vs_overload.py
"""
import datetime

import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci
from scripts import analyze_week5_results as w5

OUT = "results/week5_margin_vs_overload.csv"
OUT_CI = "results/closure_margin_vs_overload_ci.csv"


def main():
    e = w5.load_economics_df()
    e = e[e.algorithm.isin(w5.ALL_ALGOS)].copy()
    e["seed"] = e.seed.astype(int)
    for c in ["total_transformer_overload", "average_user_satisfaction"]:
        e[c] = e[c].astype(float)
    afap = e[e.algorithm == "ChargeAsFastAsPossible"]
    g = e.groupby("algorithm").agg(mean_margin=("gross_margin_cop", "mean"),
                                   mean_overload=("total_transformer_overload", "mean"),
                                   mean_satisfaction=("average_user_satisfaction", "mean")).reset_index()
    a = g[g.algorithm == "ChargeAsFastAsPossible"].iloc[0]
    g["margin_foregone_vs_afap_cop"] = a.mean_margin - g.mean_margin
    g["overload_avoided_vs_afap_kwh"] = a.mean_overload - g.mean_overload
    g["cop_per_kwh_overload_avoided"] = np.where(g.overload_avoided_vs_afap_kwh > 0,
                                                 g.margin_foregone_vs_afap_cop / g.overload_avoided_vs_afap_kwh, np.nan)
    g = g.sort_values("margin_foregone_vs_afap_cop")
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        f.write(f"# Regenerated {datetime.date.today()} by scripts/regenerate_margin_vs_overload.py from the current "
                f"analysis rows (50 seeds x 2 day types); supersedes the stale pre-Gate-4 version.\n")
        g.to_csv(f, index=False)
    rows = []
    for arm in g.algorithm:
        b = e[e.algorithm == arm]
        m = afap.merge(b, on=["seed", "day_type"], suffixes=("_a", "_b"))
        rm = paired_cluster_bootstrap_ci(m.gross_margin_cop_a, m.gross_margin_cop_b, m.seed, n_bootstrap=10_000, seed=0)
        ro = paired_cluster_bootstrap_ci(m.total_transformer_overload_a, m.total_transformer_overload_b, m.seed,
                                         n_bootstrap=10_000, seed=0)
        rows.append({"algorithm": arm, "margin_foregone_vs_afap_cop": -rm["point_estimate"],
                     "foregone_ci_low": -rm["ci_high"], "foregone_ci_high": -rm["ci_low"],
                     "overload_avoided_vs_afap_kwh": -ro["point_estimate"],
                     "avoided_ci_low": -ro["ci_high"], "avoided_ci_high": -ro["ci_low"], "n_clusters": rm["n_clusters"]})
    pd.DataFrame(rows).to_csv(OUT_CI, index=False)
    print(g.round(3).to_string(index=False))
    print(pd.DataFrame(rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
