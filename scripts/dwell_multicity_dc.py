"""
Last run, Part 4: the closure D2 two-band cost recomputed from the DC runs'
15-minute station power profiles (post-processing only).

Runs:
  - results/dwell_registry.csv, config station_v0_bogota_dc42_sp30 (42-min DC
    sessions, 1.0x, 8 ports, 100 kW), 50 seeds x 2 days;
  - AFAP against the transformer-aware Round Robin
    (RoundRobin_TransformerCapped);
  - each run's station power from results/timeseries/<run_id>.npz.

Method: scripts/analyze_closure_multicity.py::attach_bands and ::city_tables,
reused unchanged (same six cities, the same tariffs from
ev2gym_thesis/prices/cities.py, the same retail prices, the same paired
cluster bootstrap). city_tables pairs AFAP with the rows labelled
"RoundRobin", so the transformer-aware arm's rows are passed under that
label. This is the only adaptation, and the output column names keep the
closure's "rr_" prefix for that arm.

Under a flat tariff, Proposition 7.1 (07 S7.3a) holds unchanged:
margin = energy x (retail - cost). It is not recomputed here; the flat
columns are a by-product of reusing city_tables.

Output: results/dwell_multicity_dc_cost.csv
Usage: PYTHONPATH=. python scripts/dwell_multicity_dc.py
"""
import os

import pandas as pd

from scripts.analyze_closure_multicity import attach_bands, city_tables

CONFIG = "station_v0_bogota_dc42_sp30"
RR_TA = "RoundRobin_TransformerCapped"
OUT = "results/dwell_multicity_dc_cost.csv"


def load_runs():
    r = pd.read_csv("results/dwell_registry.csv", low_memory=False)
    r = r[(r.config_name == CONFIG) & r.algorithm.isin(["ChargeAsFastAsPossible", RR_TA])].copy()
    r["seed"] = r.seed.astype(float).astype(int)
    r["total_energy_charged"] = r.total_energy_charged.astype(float)
    assert all(os.path.exists(f"results/timeseries/{x}.npz") for x in r.run_id)
    assert len(r) == 200, len(r)
    r["algorithm"] = r.algorithm.replace({RR_TA: "RoundRobin"})  # city_tables' pairing label (docstring)
    return r


def main():
    runs = attach_bands(load_runs())
    _, cost = city_tables(runs)
    cost.insert(0, "session_model", "DC 42 min")
    cost.insert(1, "comparison", "AFAP vs Round Robin, transformer-aware")
    cost.to_csv(OUT, index=False)
    pd.set_option("display.width", 250)
    print(cost[["city", "retail_price_label", "conceded_flat_cop_day", "conceded_flat_ci_low", "conceded_flat_ci_high",
                "conceded_tou_cop_day", "conceded_tou_ci_low", "conceded_tou_ci_high", "conceded_tou_share_of_afap",
                "afap_peak_share", "rr_peak_share", "n_clusters"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
