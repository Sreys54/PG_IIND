"""
Week 5, Part A: post-hoc Colombian-peso economics recompute over the
existing registry, plus the implied-price sanity check that stands in for
a reconciliation check (see the Week 5 Gate 0 response, 2026-09-08: a
recompute-and-compare-to-itself check "cannot fail in a way that indicates
a real problem" -- replaced with the check below, which can).

Why a post-hoc recompute is valid at all, not re-simulation: every
algorithm family in this project's registry (heuristic, rl, optimal) was
verified to be price-independent by reading its actual reward/objective
function from source (Week 5 Gate 0 report, section 5.2) -- no control
decision anywhere in the 552-row station_v0_bogota registry depends on the
price series, so the price series can be swapped after the fact using only
each row's already-recorded total_energy_charged.
"""
import os

import pandas as pd

from ev2gym_thesis.registry import REGISTRY_PATH
from ev2gym_thesis.prices.colombia import (
    compute_row_economics,
    RETAIL_TARIFF_COP_PER_KWH,
    RETAIL_TARIFF_RETRIEVAL_DATE,
    ENERGY_PURCHASE_COST_COP_PER_KWH,
    ENERGY_PURCHASE_COST_TARIFF_MONTH,
    ENERGY_PURCHASE_COST_WITH_CONTRIBUTION,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECONOMICS_CSV_PATH = os.path.join(REPO_ROOT, "results", "economics_cop.csv")
PRICE_CSV_PATH = os.path.join(REPO_ROOT, "ev2gym", "data", "Netherlands_day-ahead-2015-2024.csv")
DEDUP_KEY_COLUMNS = ("config_name", "algorithm", "seed", "eval_day")


def load_price_day_ranges() -> pd.DataFrame:
    """Per-calendar-day [min, max] EUR/kWh from the ENTSO-E series EV2Gym
    ships (ev2gym/utilities/loaders.py:load_electricity_prices divides the
    raw EUR/MWhe column by 1000 -- replicated exactly here, not re-derived).
    Used only to sanity-check that the registry's existing `total_profits`
    (an energy-weighted average of that day's hourly price, since charging
    only ever happens under v2g_enabled=False) is dimensionally consistent
    with `total_energy_charged` -- see implied_price_check below."""
    df = pd.read_csv(PRICE_CSV_PATH)
    df["dt"] = pd.to_datetime(df["Datetime (UTC)"], format="mixed")
    df["date"] = df["dt"].dt.date.astype(str)
    df["price_eur_per_kwh"] = df["Price (EUR/MWhe)"] / 1000.0
    return df.groupby("date")["price_eur_per_kwh"].agg(["min", "max"])


def implied_price_check(registry_df: pd.DataFrame, tolerance: float = 1e-6):
    """Section 5.3(a) of the Week 5 brief: for every row, |total_profits| /
    total_energy_charged must be a plausible EUR/kWh price for that row's
    simulated day -- specifically, within that day's own [min, max] hourly
    price band (total_profits is charge_price-weighted by
    per-step-charged-energy, so it must lie inside the day's price range
    whenever every step's charged energy is >= 0, which holds under
    v2g_enabled=False; see ev2gym/models/ev_charger.py:178).

    Returns (per_row_df, problems) -- problems is a list of dicts, one per
    row that fails the check (zero energy with nonzero profit, day missing
    from the price CSV, or implied price outside the day's band). An empty
    problems list means every row in registry_df passed.
    """
    ranges = load_price_day_ranges()
    rows = []
    problems = []
    for _, row in registry_df.iterrows():
        energy = row["total_energy_charged"]
        profit = row["total_profits"]
        day = str(row["eval_day"])
        key = {k: row[k] for k in DEDUP_KEY_COLUMNS}

        if energy == 0:
            if abs(profit) > tolerance:
                problems.append({**key, "issue": "zero total_energy_charged but nonzero total_profits",
                                  "total_profits": profit})
            continue

        implied_eur_per_kwh = abs(profit) / energy

        if day not in ranges.index:
            problems.append({**key, "issue": f"eval_day {day} not found in price CSV"})
            continue

        lo, hi = ranges.loc[day, "min"], ranges.loc[day, "max"]
        in_range = (lo - tolerance) <= implied_eur_per_kwh <= (hi + tolerance)
        rows.append({**key, "total_energy_charged": energy, "total_profits": profit,
                     "implied_eur_per_kwh": implied_eur_per_kwh,
                     "day_min_eur_per_kwh": lo, "day_max_eur_per_kwh": hi,
                     "in_range": in_range})
        if not in_range:
            problems.append({**key, "issue": "implied price outside day's ENTSO-E band",
                              "implied_eur_per_kwh": implied_eur_per_kwh,
                              "day_min_eur_per_kwh": lo, "day_max_eur_per_kwh": hi})

    return pd.DataFrame(rows), problems


def recompute_all(registry_path: str = REGISTRY_PATH,
                   retail_tariff_cop_per_kwh: float = RETAIL_TARIFF_COP_PER_KWH,
                   purchase_cost_cop_per_kwh: float = ENERGY_PURCHASE_COST_COP_PER_KWH) -> pd.DataFrame:
    """Every row in the registry (all configs, all algorithm families) gets
    a Colombian-economics row -- this is a strictly wider scope than the
    550-row station_v0_bogota evaluation grid the Week 5 statistics use,
    deliberately: the recompute is a pure function of total_energy_charged
    (see ev2gym_thesis/prices/colombia.compute_row_economics), so nothing
    about it depends on a row being part of that grid, the same reasoning
    the brief applied to station_v0_bogota's own 2 legacy rows extended to
    every other config in the registry (station_n02_tx100 etc.,
    v2ggrid_smoke_test) so nothing is left silently inconsistent.
    """
    registry = pd.read_csv(registry_path)
    records = []
    for _, row in registry.iterrows():
        econ = compute_row_economics(row["total_energy_charged"],
                                      retail_tariff_cop_per_kwh=retail_tariff_cop_per_kwh,
                                      purchase_cost_cop_per_kwh=purchase_cost_cop_per_kwh)
        record = {k: row[k] for k in DEDUP_KEY_COLUMNS}
        record["algorithm_family"] = row["algorithm_family"]
        record["total_energy_charged_kwh"] = row["total_energy_charged"]
        record.update(econ)
        record["retail_tariff_cop_per_kwh"] = retail_tariff_cop_per_kwh
        record["retail_tariff_month"] = RETAIL_TARIFF_RETRIEVAL_DATE
        record["energy_purchase_cost_cop_per_kwh"] = purchase_cost_cop_per_kwh
        record["cu_tariff_month"] = ENERGY_PURCHASE_COST_TARIFF_MONTH
        record["cu_with_contribution"] = ENERGY_PURCHASE_COST_WITH_CONTRIBUTION
        records.append(record)
    return pd.DataFrame.from_records(records)


def write_economics_csv(df: pd.DataFrame, out_path: str = ECONOMICS_CSV_PATH):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path
