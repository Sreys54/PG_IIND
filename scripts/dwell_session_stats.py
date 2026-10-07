"""
Final capacity brief, Parts A and B.2-B.4: what sessions the simulator
actually builds, under EV2Gym's own (Dutch) durations and under the DC
session-duration transform (ev2gym_thesis/demand/dc_sessions.py).

For every (variant, seed, day) cell of the 1.0x reference demand
(50 SEEDS x 2 EVAL_DAYS), the population is built exactly as an evaluation
run builds it (env_factory.make_env + reset_for_evaluation), with the
censoring replay on, so rejected arrivals are counted from the same draws.
Policy-independent: arrivals, durations and energy requested are fixed at
reset, before any action.

Outputs (post-processing; nothing is written to the registry):
  results/dwell_sessions_ev_level.csv   one row per spawned EV
  results/dwell_sessions_by_cell.csv    one row per cell
  results/dwell_a_session_summary.csv   per variant: duration mean [CI],
      median, P10, P90; energy requested mean [CI] and median; arrivals per
      day; mean port occupancy; n_clusters
  results/dwell_a_reference_comparison.csv  simulated vs external references

Means and their 95% CIs: paired_cluster_bootstrap_ci over the scenario seed
(EV-level rows clustered by seed, so the statistic is the pooled per-EV
mean), 10,000 draws, seed 0. Quantiles are pooled over all EVs (no CI).

Usage: PYTHONPATH=. python scripts/dwell_session_stats.py [--variants dutch,32,42,78]
"""
import argparse
import os

import numpy as np
import pandas as pd

from ev2gym_thesis.demand.dc_sessions import DwellModel, cell_sessions
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

BASE_CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
TMP = "experiments/phase3_infra_replicability/configs/dwell/_tmp_stats_day_configs"
EV_OUT = "results/dwell_sessions_ev_level.csv"
CELL_OUT = "results/dwell_sessions_by_cell.csv"
SUMMARY_OUT = "results/dwell_a_session_summary.csv"
REF_OUT = "results/dwell_a_reference_comparison.csv"
CV = 0.5

# External references (none is Colombian per-session data; see
# thesis_docs/sources/dwell_sessions/SOURCES_dwell.md).
REFERENCES = [
    ("Paid DC fast charging, US (EVWATTS, 1,412,050 sessions, 2020-2023, no Tesla)", 42.0, 22.0,
     "U.S. DOE VTO (2023), FOTW #1319"),
    ("Free DC fast charging, US (EVWATTS, 957,265 sessions)", 78.0, 40.7, "U.S. DOE VTO (2023), FOTW #1319"),
    ("DC fast charging, California survey (self-reported last session)", 32.0, None, "Hardman (2026), Findings"),
    ("Enel Colombia, Unicentro Bogota: 50% state of charge (announcement)", 27.5, None,
     "Blu Radio (2026): 'aproximadamente 25 a 30 minutos' (midpoint)"),
    ("Enel Colombia, Unicentro Bogota: full charge (announcement)", 60.0, None,
     "Blu Radio (2026): 'poco mas de una hora' (lower bound shown)"),
    ("Enel Colombia (2024): average to 100% (plausibility ceiling, Checkpoint A rule)", 90.0, None,
     "Enel Colombia (2024); page not retrievable, cited from the brief"),
]


def variant_model(v):
    return None if v == "dutch" else DwellModel(float(v), CV)


def build(variants):
    ev_rows, cell_rows = [], []
    for v in variants:
        model = variant_model(v)
        for seed in SEEDS:
            for day in EVAL_DAYS:
                recs, cens, facts = cell_sessions(BASE_CONFIG, day, seed, f"{TMP}_pid{os.getpid()}", model)
                ds = "%04d-%02d-%02d" % day
                T, P = facts["simulation_length"], int(facts["n_ports"])
                occ_steps = sum(min(r["departure_step"], T) - r["arrival_step"] for r in recs)
                for r in recs:
                    ev_rows.append({"variant": v, "seed": seed, "eval_day": ds, **r})
                cell_rows.append({
                    "variant": v, "seed": seed, "eval_day": ds, "timescale_min": facts["timescale"],
                    "n_ports": P, "n_spawned": len(recs), **{k: cens[k] for k in (
                        "rejected_lower", "rejected_upper", "dropped_late_horizon", "energy_rejected_lower_kwh",
                        "energy_rejected_upper_kwh", "requested_served_kwh")},
                    "mean_duration_min": float(np.mean([r["duration_min"] for r in recs])),
                    "mean_port_occupancy": occ_steps / (P * T)})
        print(f"variant {v}: {len(SEEDS) * len(EVAL_DAYS)} cells", flush=True)
    return pd.DataFrame(ev_rows), pd.DataFrame(cell_rows)


def mean_ci(x, clusters):
    r = paired_cluster_bootstrap_ci(np.zeros(len(x)), np.asarray(x, float), np.asarray(clusters),
                                    n_bootstrap=10_000, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def summarize(ev, cells):
    rows = []
    for v, g in ev.groupby("variant", sort=False):
        c = cells[cells.variant == v]
        d_pt, d_lo, d_hi, nc = mean_ci(g.duration_min, g.seed)
        e_pt, e_lo, e_hi, _ = mean_ci(g.energy_requested_kwh, g.seed)
        a_pt, a_lo, a_hi, _ = mean_ci(c.n_spawned, c.seed)
        o_pt, o_lo, o_hi, _ = mean_ci(c.mean_port_occupancy, c.seed)
        offered = c.n_spawned + c.rejected_lower
        f_pt, f_lo, f_hi, _ = mean_ci(offered, c.seed)
        rows.append({
            "variant": v, "target_mean_min": None if v == "dutch" else float(v), "cv": None if v == "dutch" else CV,
            "n_evs": len(g), "n_cells": len(c), "n_clusters": nc,
            "duration_mean_min": d_pt, "duration_mean_ci_low": d_lo, "duration_mean_ci_high": d_hi,
            "duration_median_min": g.duration_min.median(), "duration_p10_min": g.duration_min.quantile(0.10),
            "duration_p90_min": g.duration_min.quantile(0.90), "duration_min_min": g.duration_min.min(),
            "duration_max_min": g.duration_min.max(),
            "share_one_step_sessions": float((g.duration_min == c.timescale_min.iloc[0]).mean()),
            "energy_requested_mean_kwh": e_pt, "energy_requested_ci_low": e_lo, "energy_requested_ci_high": e_hi,
            "energy_requested_median_kwh": g.energy_requested_kwh.median(),
            "arrivals_spawned_per_day": a_pt, "arrivals_spawned_ci_low": a_lo, "arrivals_spawned_ci_high": a_hi,
            "arrivals_offered_lower_per_day": f_pt, "arrivals_offered_lower_ci_low": f_lo,
            "arrivals_offered_lower_ci_high": f_hi,
            "rejected_lower_per_day": c.rejected_lower.mean(), "rejected_upper_per_day": c.rejected_upper.mean(),
            "dropped_late_horizon_per_day": c.dropped_late_horizon.mean(),
            "mean_port_occupancy": o_pt, "mean_port_occupancy_ci_low": o_lo, "mean_port_occupancy_ci_high": o_hi,
            "realised_vs_target_mean_pct": None if v == "dutch" else 100 * (d_pt / float(v) - 1),
        })
    return pd.DataFrame(rows)


def reference_table(summary):
    dutch = summary[summary.variant == "dutch"].iloc[0]
    rows = [{"quantity": "EV2Gym 'public' scenario as configured (Dutch durations), 1.0x, 50 seeds x 2 days",
             "kind": "simulated", "mean_session_min": dutch.duration_mean_min,
             "mean_session_ci": f"[{dutch.duration_mean_ci_low:.1f}, {dutch.duration_mean_ci_high:.1f}]",
             "median_session_min": dutch.duration_median_min, "p10_min": dutch.duration_p10_min,
             "p90_min": dutch.duration_p90_min, "energy_per_session_kwh": dutch.energy_requested_mean_kwh,
             "ratio_sim_mean_to_reference": None, "source": "results/dwell_a_session_summary.csv",
             "n_clusters": int(dutch.n_clusters)}]
    for label, minutes, kwh, src in REFERENCES:
        rows.append({"quantity": label, "kind": "external reference, not Colombian session data"
                     if "Enel" not in label else "external reference (Enel Colombia statement, not session statistics)",
                     "mean_session_min": minutes, "mean_session_ci": None, "median_session_min": None,
                     "p10_min": None, "p90_min": None, "energy_per_session_kwh": kwh,
                     "ratio_sim_mean_to_reference": dutch.duration_mean_min / minutes, "source": src,
                     "n_clusters": None})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="dutch,32,42,78")
    a = ap.parse_args()
    price_data_cache.enable()
    ev, cells = build(a.variants.split(","))
    ev.to_csv(EV_OUT, index=False)
    cells.to_csv(CELL_OUT, index=False)
    s = summarize(ev, cells)
    s.to_csv(SUMMARY_OUT, index=False)
    if "dutch" in set(s.variant):
        reference_table(s).to_csv(REF_OUT, index=False)
    pd.set_option("display.width", 250)
    print(s.T.to_string())
