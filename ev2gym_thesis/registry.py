"""
Append-only master results registry (Week 2, Deliverable 3).

results/master_results.csv is the single source of truth for every figure
and table in the thesis from here on. Rows are never overwritten or
rewritten in place -- append_runs() only ever adds new rows, and skips
rows that already exist for the same (config_name, algorithm, seed,
eval_day) unless force=True.

Per-step time series (aggregate station power, transformer load, number of
connected EVs) are saved alongside each row to results/timeseries/{run_id}.npz
so figures can be regenerated without re-running the simulation. These are
NOT committed to git (see .gitignore) -- they are regenerable from the
registry row's (config_name, seed, eval_day) alone, consistent with the
project's "large binaries stay out of git" convention.
"""
import csv
import os
import subprocess

import numpy as np

REGISTRY_PATH = "results/master_results.csv"
TIMESERIES_DIR = "results/timeseries"

# doc:begin registry_schema
ALGORITHM_FAMILIES = {"heuristic", "mpc", "rl", "optimal"}

# doc:begin week5_schema_additions
# Added 2026-09-08 (Week 5, Gate 3/Gate 4 -- see
# thesis_docs/chapters/00_lab_log.md's 2026-09-08 entries):
#   day_type      -- "weekday"/"weekend", ev2gym_thesis.eval_protocol.day_type
#   scenario_id   -- f"{seed}_{day_type}", the actual independent-draw unit
#                    (Gate 3 finding: the day axis within a category is
#                    redundant, so (seed, day_type) -- not (seed, eval_day)
#                    -- is the unit that matters).
#   analysis_row  -- True only for rows produced by the corrected
#                    generate_power_setpoints (Gate 4); every statistic and
#                    figure from Week 5 onward reads ONLY analysis_row=True.
#   superseded    -- True for every row produced before the Gate 4 fix
#                    (ev2gym/utilities/utils.py::generate_power_setpoints
#                    had a live ENTSO-E price dependency in the setpoint
#                    target itself, not just in total_profits). Kept as
#                    provenance, per the project's append-only convention
#                    -- never deleted, never mixed into any statistic.
# doc:end week5_schema_additions
META_COLUMNS = [
    "run_id", "timestamp_utc", "git_commit", "config_name", "n_ports",
    "transformer_kw", "oversubscription_ratio", "algorithm",
    "algorithm_family", "seed", "eval_day", "sim_steps", "runtime_s",
    "notes", "day_type", "scenario_id", "analysis_row", "superseded",
]

# Every scalar in env.step() stats (see CLAUDE.md's confirmed stats key
# list). action_mask and voltage_violation_counter_per_step are excluded:
# both are per-port/per-step arrays, not per-run scalars.
#
# doc:begin total_profits_semantics
# CORRECTION, 2026-09-08 (Week 5 Gate 0 audit -- see
# thesis_docs/chapters/00_lab_log.md's 2026-09-08 entry and
# thesis_docs/chapters/05_algorithm_comparison.md): `total_profits` is NOT
# a profit or revenue figure. Traced to source
# (ev2gym/models/ev_charger.py:178,194,207 and
# ev2gym/utilities/loaders.py:392-461): it is the NEGATED cost of energy
# purchased by the operator, in EUR, priced against EV2Gym's default
# Netherlands ENTSO-E day-ahead series -- not Colombian prices, and not a
# revenue collected from any EV driver (EV2Gym has no concept of a retail
# tariff charged to the user at all). Under this project's
# `v2g_enabled: False` config, no row has ever recorded a discharge
# action, so every value in this column is <= 0 by construction (verified
# empirically across all 552 station_v0_bogota rows, not just argued
# structurally). Superseded by results/economics_cop.csv
# (ev2gym_thesis/economics_recompute.py) for ALL profitability/revenue/cost
# reporting from Week 5 onward -- that table uses explicit, unambiguous
# names (`retail_revenue_cop`, `energy_purchase_cost_cop`,
# `gross_margin_cop`) precisely because "profit" was the word that let this
# column be misread as a revenue figure in Weeks 1-4. This registry column
# itself is left untouched (raw simulator output, EUR, ENTSO-E-priced) --
# it is documented here, not mutated, per the Week 5 Gate 0 response's
# explicit instruction to preserve the audit trail.
# doc:end total_profits_semantics
STATS_COLUMNS = [
    "total_ev_served", "total_profits", "total_energy_charged",
    "total_energy_discharged", "average_user_satisfaction",
    "power_tracker_violation", "tracking_error", "energy_tracking_error",
    "energy_user_satisfaction", "std_energy_user_satisfaction",
    "min_energy_user_satisfaction",
    "total_steps_min_emergency_battery_capacity_violation",
    "total_transformer_overload", "battery_degradation",
    "battery_degradation_calendar", "battery_degradation_cycling",
    "total_reward", "saved_grid_energy", "voltage_violation",
    "voltage_violation_counter",
]

REGISTRY_COLUMNS = META_COLUMNS + STATS_COLUMNS
DEDUP_KEY_COLUMNS = ("config_name", "algorithm", "seed", "eval_day")
# doc:end registry_schema


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def _coerce_scalar(value):
    """Coerce a stats value to a plain Python scalar for CSV storage.

    EV2Gym stats values are sometimes numpy scalars (e.g. np.int64) and,
    only when simulate_grid=True, some fields (saved_grid_energy,
    voltage_violation) come back as small arrays or tuples instead of
    scalars (confirmed via scripts/smoke_test_grid.py: voltage_violation
    came back as a 1-tuple of np.float64 under simulate_grid=True). All of
    our current Phase 2 configs use simulate_grid=False, where these are
    already scalars; the array/tuple branch below is a documented fallback
    (sum), relevant only to future simulate_grid=True (Objectives 4-5) data.
    """
    if isinstance(value, (list, tuple, np.ndarray)):
        return float(np.sum(value))
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def stats_to_row(stats: dict) -> dict:
    return {col: _coerce_scalar(stats.get(col)) for col in STATS_COLUMNS}


def load_existing_keys() -> set:
    """Public accessor so callers (e.g. scripts/backfill_registry.py) can
    skip already-completed (config_name, algorithm, seed, eval_day) combos
    BEFORE running an expensive simulation, not just before writing."""
    if not os.path.exists(REGISTRY_PATH):
        return set()
    with open(REGISTRY_PATH, newline="") as f:
        reader = csv.DictReader(f)
        return {
            tuple(row[k] for k in DEDUP_KEY_COLUMNS) for row in reader
        }


# doc:begin append_runs
def append_runs(rows: list, force: bool = False) -> dict:
    """Validate and append rows to the master registry. Never overwrites.

    Returns {"appended": n, "skipped": n} so callers can report what
    actually happened rather than assuming every row was written.
    """
    for row in rows:
        missing = set(REGISTRY_COLUMNS) - set(row.keys())
        extra = set(row.keys()) - set(REGISTRY_COLUMNS)
        if missing or extra:
            raise ValueError(
                f"Row schema mismatch for run_id={row.get('run_id')!r}: "
                f"missing={missing}, unexpected={extra}. "
                f"Registry schema is REGISTRY_COLUMNS in ev2gym_thesis/registry.py "
                f"-- update both the writer and this schema together."
            )
        if row["algorithm_family"] not in ALGORITHM_FAMILIES:
            raise ValueError(
                f"algorithm_family={row['algorithm_family']!r} not in {ALGORITHM_FAMILIES}"
            )

    existing_keys = load_existing_keys() if not force else set()
    file_exists = os.path.exists(REGISTRY_PATH)

    appended, skipped = 0, 0
    os.makedirs(os.path.dirname(REGISTRY_PATH) or ".", exist_ok=True)
    with open(REGISTRY_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            key = tuple(str(row[k]) for k in DEDUP_KEY_COLUMNS)
            if key in existing_keys and not force:
                skipped += 1
                continue
            writer.writerow(row)
            existing_keys.add(key)
            appended += 1

    return {"appended": appended, "skipped": skipped}
# doc:end append_runs


def save_timeseries(run_id: str, station_power, transformer_power, n_connected_evs) -> str:
    os.makedirs(TIMESERIES_DIR, exist_ok=True)
    path = f"{TIMESERIES_DIR}/{run_id}.npz"
    np.savez(
        path,
        station_power=np.asarray(station_power),
        transformer_power=np.asarray(transformer_power),
        n_connected_evs=np.asarray(n_connected_evs),
    )
    return path
