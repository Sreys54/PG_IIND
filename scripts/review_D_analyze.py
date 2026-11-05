"""
Week 8 advisor review, Block D analysis: each sensitivity against the C1 base
run of the same arm, level, seed and day (same stream except D2, whose 5-min
step draws its own Poisson counts per 5-min step; paired by scenario seed
all the same). Metrics: energy, exact DNS, mean f incl. rejected, service
level, port occupancy, rejected drivers, margin; the paired difference
(sensitivity minus base) with 95% cluster-bootstrap CIs (scenario seed,
n_clusters = 50, 10,000 resamples, per comparison, ratios of totals).
Output: results/review_D_summary.csv
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
from scripts.review_C6_tables import level_of

PART = {"d1": "D1 load-dependent departure (cap 90 min)", "d2": "D2 5-minute step", "d3": "D3 22 kWh per session"}


def mets(g):
    one = np.ones(len(g))
    return {"energy_kwh_per_day": (g.energy_delivered_kwh.values, one),
            "offered_kwh_per_day": (g.energy_offered_kwh.values, one),
            "dns_exact": ((g.energy_offered_kwh - g.energy_delivered_kwh).values, g.energy_offered_kwh.values),
            "mean_f_incl_rejected": (g.sum_f.values, (g.n_served + g.n_rejected).values),
            "service_level_incl_rejected": (g.n_f_ge_09.values, (g.n_served + g.n_rejected).values),
            "rejected_per_day": (g.n_rejected.values.astype(float), one),
            "port_occupancy": (g.port_occupancy.values, one),
            "gross_margin_cop_per_day": (g.gross_margin_cop.values, one)}


def main():
    base = pd.read_csv("experiments/phase4_review/C/c1_cases.csv")
    base["level"] = base.config_name.map(level_of)
    d = pd.read_csv("experiments/phase4_review/D/D_cases.csv")
    rows = []
    for (part, lv, arm), g in d.groupby(["part", "level", "algorithm"]):
        b = base[np.isclose(base.level, lv) & (base.algorithm == arm)].set_index(["seed", "eval_day"]).sort_index()
        g = g.set_index(["seed", "eval_day"]).sort_index().loc[b.index]
        cl = b.index.get_level_values("seed").values
        o = {"sensitivity": PART[part], "level": lv, "algorithm": arm, "n_cases": len(g)}
        mb, ms = mets(b), mets(g)
        for m in mb:
            x = rci(*ms[m], cl)
            dd = rci(mb[m][0], mb[m][1], cl, ms[m][0], ms[m][1])
            o.update({m: x["point_estimate"], f"{m}_base": rci(*mb[m], cl)["point_estimate"],
                      f"{m}_diff": dd["point_estimate"], f"{m}_diff_ci_low": dd["ci_low"],
                      f"{m}_diff_ci_high": dd["ci_high"]})
        o["meets_targets"] = bool(rci(*ms["dns_exact"], cl)["ci_high"] <= 0.15 and
                                  rci(*ms["mean_f_incl_rejected"], cl)["ci_low"] >= 0.90)
        o["n_clusters"] = len(np.unique(cl))
        rows.append(o)
    out = pd.DataFrame(rows)
    out.to_csv("results/review_D_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(out[["sensitivity", "level", "algorithm", "dns_exact", "dns_exact_base", "dns_exact_diff", "dns_exact_diff_ci_low",
               "dns_exact_diff_ci_high", "mean_f_incl_rejected", "mean_f_incl_rejected_base", "port_occupancy",
               "port_occupancy_base", "meets_targets"]].round(4).to_string())


if __name__ == "__main__":
    main()
