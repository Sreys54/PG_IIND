"""
Week 5, Part A: run the implied-price sanity check over the whole
registry, then (if it passes) write results/economics_cop.csv with
Colombian-peso economics for every row.

Per the Week 5 Gate 0 response (2026-09-08): if the implied-price check
finds a row outside its day's ENTSO-E band, or a zero-energy row with
nonzero total_profits, this script stops and reports rather than writing
the CSV -- that would mean total_profits and total_energy_charged are not
describing the same quantity, and the whole post-hoc-recompute premise
(Gate 0 section 5.2's price-independence finding) would need
re-examining before any Colombian economics number can be trusted.
"""
import sys

import pandas as pd

from ev2gym_thesis.registry import REGISTRY_PATH
from ev2gym_thesis.economics_recompute import (
    implied_price_check,
    recompute_all,
    write_economics_csv,
    ECONOMICS_CSV_PATH,
)


def main():
    registry = pd.read_csv(REGISTRY_PATH)
    print(f"Loaded {len(registry)} rows from {REGISTRY_PATH}")

    print("\n--- Implied-price sanity check (section 5.3a) ---")
    per_row, problems = implied_price_check(registry)
    print(f"Checked {len(per_row)} rows with nonzero total_energy_charged.")
    print("Implied EUR/kWh distribution:")
    print(per_row["implied_eur_per_kwh"].describe())

    if problems:
        print(f"\nFATAL: {len(problems)} row(s) failed the implied-price check:", file=sys.stderr)
        for p in problems[:20]:
            print(f"  {p}", file=sys.stderr)
        sys.exit(1)
    print("All rows passed: every implied price falls inside its simulated day's ENTSO-E band.")

    print("\n--- Recomputing Colombian-peso economics for every registry row ---")
    econ_df = recompute_all()
    out_path = write_economics_csv(econ_df)
    print(f"Wrote {len(econ_df)} rows -> {out_path}")

    main_grid = econ_df[econ_df["config_name"] == "station_v0_bogota"]
    print(f"\nstation_v0_bogota rows: {len(main_grid)} "
          f"(expected 552 = 550 SEEDSxEVAL_DAYS grid + 2 week1_reference_day legacy rows)")

    print("\nGross margin (COP), station_v0_bogota, by algorithm:")
    summary = main_grid.groupby("algorithm")["gross_margin_cop"].agg(["mean", "min", "max", "count"])
    print(summary.to_string())

    return econ_df


if __name__ == "__main__":
    main()
