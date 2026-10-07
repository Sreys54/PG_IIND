"""
Closure brief, Part F: the final target-compliance table, at the reference
demand (1.0x; Week 7 Step 2 base-setting rows, identical to the non-grid
rows on every station metric), for the five Objective 4 arms.

Targets and their operationalisation (each judged on the CI side that is
hardest to claim; n_clusters = 50):
  1. Satisfaction > 90%, as before: served EVs only (average_user_satisfaction,
     CI lower bound > 0.90).
  2. Satisfaction > 90%, on demand not served: rejected arrivals count with
     satisfaction 0, so the per-cell value is
     average_user_satisfaction x n_spawned / (n_spawned + rejected_lower)
     (lower rejection bound, i.e. the most favourable reading).
  3. Energy target "< 15%", as before: ENS_rel vs AFAP on served EVs
     (Week 7 definition, CI upper bound < 15%).
  4. Energy target "< 15%", on demand not served (lower bound, CI upper
     bound < 15%).
  5. Transformer within rating: zero overload in every one of the 100 cells.
  6. Voltage +/-5% (RETIE band). Not evaluable on the 34-node feeder, which
     is out of band at the station bus with the station idle (06 S6.2). The
     123-bus feeder shipped with EV2Gym is in band with the station idle
     (results/closure_feeder_probe_summary.csv), so for AFAP and Round Robin,
     the two arms the brief reruns there, compliance is evaluated on it at
     1.0x (results/closure_ieee123_voltage.csv): met only if no bus leaves the
     band in any of the 100 cells. The other arms were not rerun on node_123
     and stay "not evaluable".

Usage: PYTHONPATH=. python scripts/closure_target_compliance.py
"""
import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "MPC_TrackingG2V", "TD3_vanilla_extended_ts102",
        "Optimal_Oracle_Tracking"]
OUT = "results/closure_target_compliance.csv"


def mean_ci(x, clusters):
    r = paired_cluster_bootstrap_ci(np.zeros(len(x)), np.asarray(x, float), np.asarray(clusters),
                                    n_bootstrap=10_000, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def main():
    d = pd.read_csv("results/closure_demand_not_served_by_run.csv")
    d = d[(d.level == 1.0) & d.algorithm.isin(ARMS)]
    reg = pd.read_csv("results/master_results.csv", low_memory=False)[
        ["run_id", "average_user_satisfaction", "total_transformer_overload"]]
    d = d.merge(reg, on="run_id", how="left")
    d["sat_all_arrivals"] = d.average_user_satisfaction * d.n_spawned / (d.n_spawned + d.rejected_lower)
    w7 = pd.read_csv("results/week7_target_compliance.csv")
    w7 = w7[w7.setting == "base"].set_index("algorithm")
    probe = pd.read_csv("results/closure_feeder_probe_summary.csv")
    qualifying = probe[probe.qualifies_in_band_idle.astype(str) == "True"].iloc[:, 0].tolist()
    v123 = pd.read_csv("results/closure_ieee123_voltage.csv")
    v123 = v123[v123.level == 1.0].set_index("algorithm")
    rows = []
    for arm in ARMS:
        g = d[d.algorithm == arm]
        assert len(g) == 100, (arm, len(g))
        s_pt, s_lo, s_hi, nc = mean_ci(g.average_user_satisfaction, g.seed)
        a_pt, a_lo, a_hi, _ = mean_ci(g.sat_all_arrivals, g.seed)
        n_pt, n_lo, n_hi, _ = mean_ci(g.dns_lower, g.seed)
        ov_cells = int((g.total_transformer_overload > 0).sum())
        rows.append({
            "algorithm": arm, "n_runs": len(g), "n_clusters": nc,
            "sat_served_mean": s_pt, "sat_served_ci_low": s_lo, "sat_served_met": s_lo > 0.90,
            "sat_all_arrivals_mean": a_pt, "sat_all_arrivals_ci_low": a_lo, "sat_all_arrivals_met": a_lo > 0.90,
            "ens_rel_pct": w7.loc[arm, "ens_rel_point_pct"], "ens_rel_ci_high_pct": w7.loc[arm, "ens_rel_ci_high_pct"],
            "ens_rel_met": bool(w7.loc[arm, "ens_target_met_ci_upper_lt_15pct"]),
            "dns_lower_mean": n_pt, "dns_lower_ci_high": n_hi, "dns_met": n_hi < 0.15,
            "cells_with_overload": ov_cells, "transformer_met": ov_cells == 0,
            "voltage_status": (("met on node_123" if bool(v123.loc[arm, "band_compliance_all_cells"]) else "not met on node_123")
                               if arm in v123.index else "not evaluable"),
            "voltage_reason": ((f"node_123 (in band idle), station on bus 115, 1.0x, weekday only: "
                                f"{int(v123.loc[arm, 'cells_out_of_band'])}/{int(v123.loc[arm, 'n_runs'])} "
                                f"cells out of band, lowest bus voltage {v123.loc[arm, 'min_voltage_pu_worst']:.4f} p.u.")
                               if arm in v123.index else
                               "34-node feeder out of band at the station bus with the station idle (78/100 base cells); "
                               f"not rerun on the qualifying feeder(s) {qualifying} (brief E2 covers AFAP and Round Robin)"),
            "voltage_station_adds_outside_cells": int(w7.loc[arm, "voltage_cells_station_adds_outside_samples"]),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    pd.set_option("display.width", 250)
    print(out.drop(columns=["voltage_reason"]).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
