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


# doc:begin non_grid_notes_markers
# Week 3 contract change (see thesis_docs/chapters/00_lab_log.md's Week 3,
# Entregable 6 entry): main_grid_rows() used to filter by `notes == ""`,
# treating ANY non-empty notes value as "not part of the main grid" (Weeks
# 1-2 only ever used notes for exactly these two markers, so the two
# conventions were indistinguishable at the time). Week 3's RL rows
# legitimately use `notes` for real grid-row metadata (reward/state/
# train_seed, per 03_rl_baseline.md S3.5's registry-comparability
# requirement), so "non-empty notes" no longer implies "excluded from the
# grid" -- it now means EXACTLY one of these two explicit markers.
NON_GRID_NOTES_MARKERS = {"week1_reference_day", "pipeline_smoke_test_grid"}
# doc:end non_grid_notes_markers


def main_grid_rows(rows: list, config_name: str = None) -> list:
    """Rows from the current statistical grid only.

    CORRECTED 2026-09-08 (Week 5, Gate 3/Gate 4 -- see
    thesis_docs/chapters/00_lab_log.md's 2026-09-08 entries): filters on
    `analysis_row == "True"` now, not the old NON_GRID_NOTES_MARKERS
    exclusion. The old (SEEDS=[0..4] x 10 EVAL_DAYS) grid was produced by
    a buggy `generate_power_setpoints` with a live ENTSO-E price
    dependency inside the control layer; every one of those rows is
    `superseded=True`, `analysis_row=False` after the Week 5 schema
    migration, so the old filter would now silently include stale data.
    `analysis_row` is the single, explicit source of truth for "belongs to
    a current, valid statistic or figure" -- NON_GRID_NOTES_MARKERS is
    kept below only for historical/debugging reference to the old rows,
    not used by this function. Configs other than `station_v0_bogota`
    (the sensitivity-sweep configs, the smoke test) have zero
    analysis_row=True rows as of Week 5 -- they were not part of the Gate
    4 regeneration and this function correctly returns nothing for them
    rather than falling back to their stale rows."""
    out = [r for r in rows if str(r.get("analysis_row")) == "True"]
    if config_name is not None:
        out = [r for r in out if r["config_name"] == config_name]
    return out
