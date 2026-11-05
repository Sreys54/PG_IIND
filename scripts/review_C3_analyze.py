"""
Week 8 advisor review, C3 analysis: the carried TD3_safe model against the
causal arms that answer the advisor's question (does the RL agent beat a
random policy, and a simple heuristic, under the same safety layer?), and
the dispersion over the three training seeds.

Inputs: experiments/phase4_review/C/c1_cases.csv, td3_cases.csv and
results/review_td3_safe_selection.json (carried model chosen on validation
only; the test grid never enters the selection).
Outputs:
  results/review_C3_td3_safe_comparisons.csv  TD3_safe minus {RR-TA, PS, Random+S, RR+S,
                                              MPC-soft-est} per level: energy (kWh/day),
                                              exact DNS, mean f incl. rejected, with 95% CIs
  results/review_C3_td3_safe_seeds.csv        per training seed and level: the same metrics
                                              (point estimate and CI), validation value,
                                              final step
Statistics: cluster bootstrap over the scenario seed (n_clusters = 50),
10,000 resamples, percentile 95%, per comparison; ratios of totals inside
each resample.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
from scripts.review_C6_tables import level_of

C = "experiments/phase4_review/C"
SEL = "results/review_td3_safe_selection.json"
OTHERS = ["RR-TA", "PS", "Random+S", "RR+S", "MPC-soft-est"]
STATS = ("cluster bootstrap over scenario seed (n_clusters = 50), 10,000 resamples, percentile 95%, "
         "per comparison; ratios of totals per resample")


def metrics(g):
    one = np.ones(len(g))
    return {"energy_kwh_per_day": (g.energy_delivered_kwh.values, one),
            "dns_exact": ((g.energy_offered_kwh - g.energy_delivered_kwh).values, g.energy_offered_kwh.values),
            "mean_f_incl_rejected": (g.sum_f.values, (g.n_served + g.n_rejected).values)}


def main():
    sel = json.load(open(SEL))
    carried = f"TD3_safe_ts{sel['carried_model']['train_seed']}"
    c = pd.concat([pd.read_csv(f"{C}/c1_cases.csv"), pd.read_csv(f"{C}/td3_cases.csv")], ignore_index=True)
    c["level"] = c.config_name.map(level_of)
    comp, seeds = [], []
    for lv in sorted(c.level.unique()):
        g = c[np.isclose(c.level, lv)]
        by = {a: x.set_index(["seed", "eval_day"]).sort_index() for a, x in g.groupby("algorithm")}
        idx = by[carried].index
        cl = idx.get_level_values("seed").values
        mt = metrics(by[carried].loc[idx])
        for o in OTHERS:
            mo = metrics(by[o].loc[idx])
            row = {"level": lv, "reference": "TD3_safe", "other": o}
            for m, (num, den) in mt.items():
                r = rci(mo[m][0], mo[m][1], cl, num, den)
                row.update({f"{m}_td3_minus_other": r["point_estimate"], f"{m}_diff_ci_low": r["ci_low"],
                            f"{m}_diff_ci_high": r["ci_high"]})
            row.update({"n_clusters": len(np.unique(cl)), "statistics": STATS})
            comp.append(row)
        for s, info in sel["seeds"].items():
            arm = f"TD3_safe_ts{s}"
            if arm not in by:
                continue
            row = {"level": lv, "train_seed": int(s), "carried_model": arm == carried,
                   "final_step": info["final_step"], "validation_energy_kwh": info["validation_energy_kwh"]}
            for m, (num, den) in metrics(by[arm].loc[idx]).items():
                r = rci(num, den, cl)
                row.update({m: r["point_estimate"], f"{m}_ci_low": r["ci_low"], f"{m}_ci_high": r["ci_high"]})
            row.update({"days_with_overload": int(by[arm].overload_day.sum()),
                        "peak_kw_max": float(by[arm].peak_station_kw.max()), "n_clusters": len(np.unique(cl)),
                        "statistics": STATS})
            seeds.append(row)
    pd.DataFrame(comp).to_csv("results/review_C3_td3_safe_comparisons.csv", index=False)
    pd.DataFrame(seeds).to_csv("results/review_C3_td3_safe_seeds.csv", index=False)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(comp).drop(columns="statistics").round(4).to_string())
    print(pd.DataFrame(seeds).drop(columns="statistics").round(4).to_string())


if __name__ == "__main__":
    main()
