"""
Barranquilla two-band cost of the 100 kW limit in the DC regime, recomputed
with the station-level arrival generator on the same 100 scenarios as
Table VII of the paper (advisor's final comments, 2026-11-17, task 5).

Replaces the 9,230 / 9,619 COP/day figures of Section VII-C, which came from
EV2Gym's per-port generator.

Step 1 (simulation). The original C1 run did not store per-step station power,
so AFAP and RR-TA are re-run at 1.0x (8 ports, 100 kW, station-level Poisson
arrivals, config station_v0_bogota_dc42_poisson_1.00x_p8_tr100) on
SEEDS x EVAL_DAYS = 100 cases each, recording the per-step power. Every rerun
is checked against energy_delivered_kwh in experiments/phase4_review/C/c1_cases.csv
and the script stops if any case differs by more than 1e-6 kWh.

Step 2 (post-processing). Air-e September 2026, voltage level 2, two-band
option (peak 17:00-22:00) vs. the flat tariff, retail price 1,450 COP/kWh.
Cost of the limit = margin(AFAP) - margin(RR-TA), per scenario. Intervals:
cluster bootstrap over the scenario seed (n_clusters = 50, 10,000 resamples,
ratio of totals, ev2gym_thesis.stats_utils.cluster_bootstrap_ratio).
Sanity check: the flat cost must reproduce Table VII (18,801 COP/day).

Outputs (experiments/phase4_review/C/):
  barranquilla_two_band_power.csv   per-step power, 200 cases x 96 steps
  barranquilla_two_band_check.csv   rerun vs. stored energy, per case
  barranquilla_two_band_dc.csv/.xlsx  summary with 95% intervals

Usage (from the repository root):
  PYTHONPATH=. python scripts/barranquilla_two_band_dc.py            # rerun + analysis
  PYTHONPATH=. python scripts/barranquilla_two_band_dc.py --analyze  # reuse saved power
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.prices.cities import CITIES, step_in_peak
from ev2gym_thesis.prices.colombia import RETAIL_TARIFF_COP_PER_KWH as PRICE
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio
from ev2gym_thesis.xlsx_export import (MIXED_UNIT_4DP_FORMAT,
                                       COUNT_FORMAT, export_formatted_xlsx)

OUT = "experiments/phase4_review/C"
CONFIG = "experiments/phase4_review/configs/station_v0_bogota_dc42_poisson_1.00x_p8_tr100.yaml"
ARMS = ("AFAP", "RR-TA")
N_STEPS = 96
STEP_H = 0.25
TABLE_VII_FLAT_COST = 18801.0
POWER_CSV = f"{OUT}/barranquilla_two_band_power.csv"
CHECK_CSV = f"{OUT}/barranquilla_two_band_check.csv"
SUMMARY_CSV = f"{OUT}/barranquilla_two_band_dc.csv"


def rerun():
    """Re-run the 200 cases and store the per-step station power (kW)."""
    from scripts import review_dc
    review_dc.process_hooks()
    ref = pd.read_csv(f"{OUT}/c1_cases.csv").set_index("run_id")
    power_rows, check_rows = [], []
    for arm in ARMS:
        for s in SEEDS:
            for d in EVAL_DAYS:
                row, ex = review_dc.run_case(arm, CONFIG, s, d, "station")
                steps = review_dc.LAST_RECORD["episode"]["steps"]
                p = np.array([st["power_kw"] for st in steps], float)
                rid = row["run_id"]
                e_ref = float(ref.loc[rid, "energy_delivered_kwh"])
                e_ts = float(np.clip(p, 0, None).sum() * STEP_H)
                check_rows.append(dict(run_id=rid, arm=arm, seed=s,
                                       eval_day="%04d-%02d-%02d" % d, n_steps=len(p),
                                       e_stored=e_ref, e_rerun=ex["energy_delivered_kwh"],
                                       e_timeseries=e_ts))
                power_rows.append(dict(run_id=rid, arm=arm, seed=s,
                                       eval_day="%04d-%02d-%02d" % d,
                                       **{f"p_{k:03d}": v for k, v in enumerate(p)}))
                print(arm, s, d, round(e_ref, 4), round(e_ts, 4), flush=True)
    chk = pd.DataFrame(check_rows)
    chk.to_csv(CHECK_CSV, index=False)
    pd.DataFrame(power_rows).to_csv(POWER_CSV, index=False)
    err = max((chk.e_rerun - chk.e_stored).abs().max(),
              (chk.e_timeseries - chk.e_stored).abs().max())
    print(f"max |rerun - stored| = {err:.3e} kWh over {len(chk)} cases")
    if len(chk) != 2 * len(SEEDS) * len(EVAL_DAYS) or err > 1e-6:
        sys.exit("STOP: reruns do not reproduce the stored C1 energies.")


def energy_matrix(pw, arm):
    rows = pw[pw.arm == arm].sort_values(["seed", "eval_day"])
    p = rows[[f"p_{k:03d}" for k in range(N_STEPS)]].to_numpy(float)
    return np.clip(p, 0, None) * STEP_H, rows.seed.to_numpy()


def analyze():
    pw = pd.read_csv(POWER_CSV)
    t = CITIES["Barranquilla"]
    tou = t["tou"]
    c_flat, c_peak, c_off = t["flat_con"], tou["peak_con"], tou["offpeak_con"]
    peak = np.array([step_in_peak(k, tou["peak_hours"]) for k in range(N_STEPS)])
    c_t = np.where(peak, c_peak, c_off)
    print(f"price {PRICE}, flat {c_flat}, peak {c_peak}, off-peak {c_off}, "
          f"spread {100 * (c_peak - c_off) / c_off:.2f}%, peak steps {peak.sum()}")

    e_afap, cl = energy_matrix(pw, "AFAP")
    e_rrta, cl2 = energy_matrix(pw, "RR-TA")
    assert (cl == cl2).all() and e_afap.shape == (len(SEEDS) * len(EVAL_DAYS), N_STEPS)

    margin_2b = lambda e: (e * (PRICE - c_t)).sum(axis=1)
    margin_fl = lambda e: (e * (PRICE - c_flat)).sum(axis=1)
    cost_2b = margin_2b(e_afap) - margin_2b(e_rrta)
    cost_fl = margin_fl(e_afap) - margin_fl(e_rrta)
    ones = np.ones(len(cost_2b))

    results = [
        ("cost_two_band_cop_day", cluster_bootstrap_ratio(cost_2b, ones, cl)),
        ("cost_flat_cop_day", cluster_bootstrap_ratio(cost_fl, ones, cl)),
        ("two_band_minus_flat_cop_day",
         cluster_bootstrap_ratio(cost_fl, ones, cl, num_b=cost_2b, den_b=ones)),
        ("afap_peak_energy_share",
         cluster_bootstrap_ratio(e_afap[:, peak].sum(1), e_afap.sum(1), cl)),
        ("rrta_peak_energy_share",
         cluster_bootstrap_ratio(e_rrta[:, peak].sum(1), e_rrta.sum(1), cl)),
    ]
    flat = results[1][1]["point_estimate"]
    if abs(flat - TABLE_VII_FLAT_COST) > 0.5:
        sys.exit(f"STOP: flat cost {flat:.2f} does not reproduce Table VII ({TABLE_VII_FLAT_COST}).")
    two_band = results[0][1]["point_estimate"]

    summary = pd.DataFrame([dict(quantity=k, point=r["point_estimate"], ci_low=r["ci_low"],
                                 ci_high=r["ci_high"], n_clusters=r["n_clusters"])
                            for k, r in results])
    summary.to_csv(SUMMARY_CSV, index=False)
    export_formatted_xlsx(
        SUMMARY_CSV, SUMMARY_CSV.replace(".csv", ".xlsx"),
        column_labels={
            "quantity": "Quantity (cost rows in COP per simulated day; share rows as a 0-1 fraction of delivered energy)",
            "point": "Point Estimate, Ratio of Totals",
            "ci_low": "95% CI Lower Bound (cluster bootstrap)",
            "ci_high": "95% CI Upper Bound (cluster bootstrap)",
            "n_clusters": "Number of Clusters (scenario seeds)",
        },
        number_formats={
            "Point Estimate, Ratio of Totals": MIXED_UNIT_4DP_FORMAT,
            "95% CI Lower Bound (cluster bootstrap)": MIXED_UNIT_4DP_FORMAT,
            "95% CI Upper Bound (cluster bootstrap)": MIXED_UNIT_4DP_FORMAT,
            "Number of Clusters (scenario seeds)": COUNT_FORMAT,
        },
        sheet_name="barranquilla_two_band")

    for k, r in results:
        print(f"{k}: {r['point_estimate']:.4f} [{r['ci_low']:.4f}, {r['ci_high']:.4f}] "
              f"n_clusters={r['n_clusters']}")
    print(f"two-band vs flat: {100 * (two_band - flat) / flat:+.2f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true", help="skip the rerun, reuse the saved power")
    args = ap.parse_args()
    if not args.analyze:
        rerun()
    analyze()
