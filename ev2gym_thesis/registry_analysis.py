"""
Shared registry-loading helpers for scripts/make_figures.py. Centralizes
the "exclude the grid smoke test, coerce numeric fields" logic so every
figure filters the registry the same way.
"""
import csv

from ev2gym_thesis.registry import REGISTRY_PATH, STATS_COLUMNS

NUMERIC_META_COLUMNS = ["n_ports", "transformer_kw", "oversubscription_ratio", "seed", "sim_steps"]


def _coerce_row(row: dict) -> dict:
    out = dict(row)
    for col in NUMERIC_META_COLUMNS + STATS_COLUMNS:
        val = out.get(col, "")
        if val == "":
            out[col] = None
            continue
        try:
            out[col] = float(val)
        except (TypeError, ValueError):
            pass  # leave non-numeric as-is (shouldn't happen for these columns)
    return out


def load_registry(exclude_smoke_test: bool = True) -> list:
    with open(REGISTRY_PATH, newline="") as f:
        rows = [_coerce_row(r) for r in csv.DictReader(f)]
    if exclude_smoke_test:
        rows = [r for r in rows if r["notes"] != "pipeline_smoke_test_grid"]
    return rows


def main_grid_rows(rows: list, config_name: str = None) -> list:
    """Rows from the balanced 5-seed x 10-day evaluation grid only (excludes
    the Week 1 single-day historical rows and the grid smoke test)."""
    out = [r for r in rows if r["notes"] == ""]
    if config_name is not None:
        out = [r for r in out if r["config_name"] == config_name]
    return out
