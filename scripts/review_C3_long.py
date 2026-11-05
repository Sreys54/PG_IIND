"""
Week 8 advisor review, C3 long-budget sensitivity (config_safe doc
long_budget_sensitivity, pre-registered 2026-11-03 before the runs).

  --select   per seed: the last checkpoint (2,000,000 steps) and the best
             validation value over the whole run; writes
             results/review_td3_safe_long_selection.json and prints the
             --td3 arguments for scripts/review_C_run.py --plan td3
  --analyze  after the test grid: each long-budget arm minus the carried
             TD3_safe model, minus RR-TA and minus PS, per level (energy kWh/day, exact
             DNS, mean f incl. rejected, 95% CIs) ->
             results/review_C3_long_budget.csv

The carried TD3_safe model is unchanged whatever this gives (rule 3 of the
doc block). Statistics: cluster bootstrap over the scenario seed
(n_clusters = 50), 10,000 resamples, percentile 95%, per comparison; ratios
of totals per resample.

Usage:
  PYTHONPATH=. python scripts/review_C3_long.py --select
  PYTHONPATH=. python scripts/review_C_run.py --plan td3 --td3 <printed args> --state service_causal
  PYTHONPATH=. python scripts/review_C_run.py --plan td3 --merge
  PYTHONPATH=. python scripts/review_C3_long.py --analyze
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.rl import config_safe as cfg
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
from scripts.review_C6_tables import level_of

ROOT = "C:/ev2gym_runs/w8_td3_safe_long"
SEL = "results/review_td3_safe_long_selection.json"
OUT = "results/review_C3_long_budget.csv"
C = "experiments/phase4_review/C"
STATS = ("cluster bootstrap over scenario seed (n_clusters = 50), 10,000 resamples, percentile 95%, "
         "per comparison; ratios of totals per resample")


def select(seeds=(100, 101, 102)):
    out = {"rule": cfg.LONG_BUDGET_RULE, "budget_steps": cfg.LONG_BUDGET_STEPS, "seeds": {}}
    args = []
    for s in seeds:
        name = f"TD3_safe_dc42_ts{s}"
        st = json.load(open(f"{ROOT}/models/{name}/state.json"))
        v = pd.read_csv(f"{ROOT}/logs/{name}_validation.csv")
        last, best = v.iloc[-1], v.loc[v.criterion_value.idxmax()]
        out["seeds"][s] = {"stop_reason": st.get("stop_reason"), "last_step": int(last.timesteps),
                           "last_validation_energy_kwh": float(last.criterion_value),
                           "last_checkpoint": last.checkpoint_path.replace("\\", "/"),
                           "bestval_step": int(best.timesteps),
                           "bestval_validation_energy_kwh": float(best.criterion_value),
                           "bestval_checkpoint": best.checkpoint_path.replace("\\", "/"),
                           "convergence_step_c3_rule": (int(v.timesteps.iloc[st["conv_eval_index"]])
                                                        if st.get("conv_eval_index") is not None else None)}
        args += [f"TD3_safe_long_last_ts{s}={out['seeds'][s]['last_checkpoint']}",
                 f"TD3_safe_long_bestval_ts{s}={out['seeds'][s]['bestval_checkpoint']}"]
    json.dump(out, open(SEL, "w"), indent=2)
    print(json.dumps(out, indent=2))
    print(" ".join(f'"{a}"' for a in args))


def metrics(g):
    one = np.ones(len(g))
    return {"energy_kwh_per_day": (g.energy_delivered_kwh.values, one),
            "dns_exact": ((g.energy_offered_kwh - g.energy_delivered_kwh).values, g.energy_offered_kwh.values),
            "mean_f_incl_rejected": (g.sum_f.values, (g.n_served + g.n_rejected).values)}


def analyze():
    carried = f"TD3_safe_ts{json.load(open('results/review_td3_safe_selection.json'))['carried_model']['train_seed']}"
    c = pd.concat([pd.read_csv(f"{C}/c1_cases.csv"), pd.read_csv(f"{C}/td3_cases.csv")], ignore_index=True)
    c["level"] = c.config_name.map(level_of)
    rows = []
    for lv in sorted(c.level.unique()):
        g = c[np.isclose(c.level, lv)]
        by = {a: x.set_index(["seed", "eval_day"]).sort_index() for a, x in g.groupby("algorithm")}
        idx = by[carried].index
        cl = idx.get_level_values("seed").values
        for arm in sorted(a for a in by if a.startswith("TD3_safe_long_")):
            ma = metrics(by[arm].loc[idx])
            row = {"level": lv, "algorithm": arm, "days_with_overload": int(by[arm].overload_day.sum()),
                   "peak_kw_max": float(by[arm].peak_station_kw.max())}
            for m, (num, den) in ma.items():
                r = rci(num, den, cl)
                row.update({m: r["point_estimate"], f"{m}_ci_low": r["ci_low"], f"{m}_ci_high": r["ci_high"]})
                for ref, tag in [(carried, "TD3_safe"), ("RR-TA", "RR-TA"), ("PS", "PS")]:
                    mr = metrics(by[ref].loc[idx])
                    d = rci(mr[m][0], mr[m][1], cl, num, den)
                    row.update({f"{m}_minus_{tag}": d["point_estimate"], f"{m}_minus_{tag}_ci_low": d["ci_low"],
                                f"{m}_minus_{tag}_ci_high": d["ci_high"]})
            row.update({"n_clusters": len(np.unique(cl)), "statistics": STATS})
            rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(OUT, index=False)
    pd.set_option("display.width", 250)
    print(t[["level", "algorithm", "energy_kwh_per_day", "energy_kwh_per_day_minus_TD3_safe",
             "energy_kwh_per_day_minus_RR-TA", "dns_exact", "mean_f_incl_rejected", "days_with_overload"]].round(3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102])
    a = ap.parse_args()
    if a.select:
        select(tuple(a.seeds))
    if a.analyze:
        analyze()
