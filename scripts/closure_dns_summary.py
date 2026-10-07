"""
Closure brief, Parts B/C: demand not served (DNS) per arm and demand level,
joining the policy-independent censoring table
(results/closure_censoring_by_cell.csv) to each arm's energy delivered.

Sources of energy delivered:
  - Step 2 grid rows (registry, simulate_grid=True): levels 1.0 / 1.3 / 1.6
    (settings base / spawn1.3 / spawn1.6; Axis 2 is identical to base);
  - Part C rows (registry, config_name station_v0_bogota_sp<N>): other levels.

DNS = (E_rejected + R_served - E_delivered) / (E_rejected + R_served), lower
and upper rejection bounds (ev2gym_thesis/demand/censoring.py). Per arm and
level: mean and 95% CI by paired_cluster_bootstrap_ci over the scenario seed
(n_clusters printed), plus the mean rejected-arrival counts.

Usage: PYTHONPATH=. python scripts/closure_dns_summary.py
"""
import numpy as np
import pandas as pd

from ev2gym_thesis.demand.censoring import demand_not_served
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

STEP2 = {"station_v0_bogota_grid": 1.0, "station_v0_bogota_grid_spawn1.3": 1.3, "station_v0_bogota_grid_spawn1.6": 1.6}
OUT = "results/closure_demand_not_served.csv"


def level_rows():
    reg = pd.read_csv("results/master_results.csv", low_memory=False)
    reg = reg[reg.analysis_row.astype(str) == "True"].copy()
    step2 = reg[reg.config_name.isin(STEP2)].copy()
    step2["level"] = step2.config_name.map(STEP2)
    step2["source"] = "week7_step2_grid"
    partc = reg[reg.config_name.str.match(r"^station_v0_bogota_sp\d+$")].copy()
    partc["level"] = partc.notes.str.extract(r"demand_level=([0-9.]+)")[0].astype(float)
    partc["source"] = "closure_part_c"
    out = pd.concat([step2, partc], ignore_index=True)
    out["seed"] = out.seed.astype(int)
    out["total_energy_charged"] = out.total_energy_charged.astype(float)
    return out


def ci(x, clusters):
    r = paired_cluster_bootstrap_ci(np.zeros(len(x)), np.asarray(x, float), np.asarray(clusters), n_bootstrap=10_000, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def main():
    cens = pd.read_csv("results/closure_censoring_by_cell.csv")
    runs = level_rows()
    m = runs.merge(cens, on=["level", "seed", "eval_day"], how="inner")
    for b in ("lower", "upper"):
        m[f"dns_{b}"] = [demand_not_served(e, r, b) for e, (_, r) in zip(m.total_energy_charged, m.iterrows())]
    m["shortfall_served_kwh"] = m.requested_served_kwh - m.total_energy_charged
    m[["run_id", "config_name", "level", "algorithm", "seed", "eval_day", "total_energy_charged", "n_spawned",
       "rejected_lower", "rejected_upper", "dropped_late_horizon", "energy_rejected_lower_kwh",
       "energy_rejected_upper_kwh", "requested_served_kwh", "shortfall_served_kwh", "dns_lower", "dns_upper"]
      ].to_csv("results/closure_demand_not_served_by_run.csv", index=False)
    rows = []
    for (lvl, arm), g in m.groupby(["level", "algorithm"]):
        row = {"level": lvl, "algorithm": arm, "n_runs": len(g)}
        for col in ["dns_lower", "dns_upper", "rejected_lower", "rejected_upper", "n_spawned",
                    "energy_rejected_lower_kwh", "shortfall_served_kwh"]:
            pt, lo, hi, nc = ci(g[col], g.seed)
            row.update({f"{col}_mean": pt, f"{col}_ci_low": lo, f"{col}_ci_high": hi})
        row["n_clusters"] = nc
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["level", "algorithm"])
    out.to_csv(OUT, index=False)
    print(out[["level", "algorithm", "dns_lower_mean", "dns_lower_ci_low", "dns_lower_ci_high", "dns_upper_mean",
               "rejected_lower_mean", "n_spawned_mean", "n_clusters"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
