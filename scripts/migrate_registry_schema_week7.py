"""
Week 7 (Objective 4): one-time, user-authorized schema migration adding the
`simulate_grid` column to results/master_results.csv.

Every row that exists before this migration was produced with
simulate_grid=False (Weeks 1-6, all non-grid), so the new column is set to
"False" for all of them. No existing field is changed: the script reads the
file as text (dtype=str, no NA conversion), appends the column, writes it
back with the csv module's own CRLF line terminator (the format append_runs
writes), and then re-reads both files and asserts, column by column and row
by row, that every pre-existing value is identical to the backup. It refuses
to run twice.

Usage: PYTHONPATH=. python scripts/migrate_registry_schema_week7.py <backup_path>
"""
import csv
import shutil
import sys

import pandas as pd

from ev2gym_thesis.registry import REGISTRY_PATH, REGISTRY_COLUMNS


def main(backup_path):
    old = pd.read_csv(REGISTRY_PATH, dtype=str, keep_default_na=False)
    if "simulate_grid" in old.columns:
        raise SystemExit("simulate_grid already present -- migration already applied, not re-running.")
    shutil.copyfile(REGISTRY_PATH, backup_path)
    new = old.copy()
    new["simulate_grid"] = "False"
    assert list(new.columns) == REGISTRY_COLUMNS, (list(new.columns), REGISTRY_COLUMNS)
    with open(REGISTRY_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        w.writeheader()
        for rec in new.to_dict("records"):
            w.writerow(rec)

    before = pd.read_csv(backup_path, dtype=str, keep_default_na=False)
    after = pd.read_csv(REGISTRY_PATH, dtype=str, keep_default_na=False)
    assert len(before) == len(after), (len(before), len(after))
    for col in before.columns:
        assert (before[col] == after[col]).all(), f"column {col} changed"
    assert (after["simulate_grid"] == "False").all()
    print(f"Migrated {len(after)} rows: added simulate_grid=False; all {len(before.columns)} "
          f"pre-existing columns verified identical to {backup_path}.")


def fix_smoke_test_flag(backup_path):
    """CORRECTION (2026-10-05, found by test_week6_infra.TestRegistryGridFlag):
    main() assumed every pre-Week-7 row was non-grid. One was not: the
    Week 2 de-risking smoke test (config_name 'v2ggrid_smoke_test',
    notes 'pipeline_smoke_test_grid', scripts/smoke_test_grid.py) ran with
    simulate_grid=True. This sets the NEW simulate_grid field of that row
    only to True; every other field of every row is verified unchanged."""
    before = pd.read_csv(REGISTRY_PATH, dtype=str, keep_default_na=False)
    shutil.copyfile(REGISTRY_PATH, backup_path)
    mask = before["notes"] == "pipeline_smoke_test_grid"
    assert mask.sum() == 1 and before.loc[mask, "config_name"].iloc[0] == "v2ggrid_smoke_test"
    after = before.copy()
    after.loc[mask, "simulate_grid"] = "True"
    with open(REGISTRY_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        w.writeheader()
        for rec in after.to_dict("records"):
            w.writerow(rec)
    check = pd.read_csv(REGISTRY_PATH, dtype=str, keep_default_na=False)
    for col in before.columns:
        if col == "simulate_grid":
            assert (before.loc[~mask, col] == check.loc[~mask, col]).all()
        else:
            assert (before[col] == check[col]).all(), f"column {col} changed"
    print(f"Set simulate_grid=True on the 1 smoke-test row; all other values of {len(check)} rows verified unchanged.")


if __name__ == "__main__":
    if sys.argv[1] == "--fix-smoke-test-flag":
        fix_smoke_test_flag(sys.argv[2])
    else:
        main(sys.argv[1])
