"""
Week 2 Deliverable 6.4 "MEDIR, NO SUPONER": measure Bogota-calibrated
calendar degradation, with real dispersion (not a single run), across the
registry's evaluation grid.

Design decision: writes to a SEPARATE file, results/degradation_by_ambient.csv,
rather than adding an ambient_scenario column to results/master_results.csv.
Reason: the same "don't mix scenario types in the comparison registry"
principle already applied to simulate_grid True/False (see
thesis_docs/chapters/02_model_validation.md) applies here -- adding a new
dimension to the Phase 2 algorithm-comparison registry after the fact would
fragment its evaluation grid and complicate every filter downstream. This
file is keyed by run_id, so it can always be joined back to
master_results.csv for analysis.

Each registry row is RE-SIMULATED (same config+seed+day -> deterministic,
identical result) because per-EV session data (historic_soc, active_steps)
needed by the degradation wrapper is not persisted anywhere -- only
aggregate stats are in the registry.

Usage:
    python scripts/measure_degradation_by_ambient.py --scope reference   # dry run, 100 rows
    python scripts/measure_degradation_by_ambient.py --scope full        # dry run, 500 rows
    python scripts/measure_degradation_by_ambient.py --scope full --execute
"""
import argparse
import csv
import os
import sys
import time

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.degradation_bogota import recompute_calendar_degradation
from ev2gym_thesis.ambient_bogota import outdoor_ambient_c, underground_ambient_c
from ev2gym_thesis.config_utils import make_day_config
from ev2gym_thesis.registry import get_git_commit

REGISTRY_PATH = "results/master_results.csv"
OUTPUT_PATH = "results/degradation_by_ambient.csv"
TMP_DAY_CONFIG_DIR = "experiments/phase1_baseline/configs/_tmp_day_configs"

BASE_CONFIG_DIR = "experiments/phase1_baseline/configs"
SENSITIVITY_DIR = f"{BASE_CONFIG_DIR}/station_sensitivity"
CONFIG_PATHS = {
    "station_v0_bogota": f"{BASE_CONFIG_DIR}/station_v0_bogota.yaml",
    "station_n02_tx100": f"{SENSITIVITY_DIR}/station_n02_tx100.yaml",
    "station_n16_tx100": f"{SENSITIVITY_DIR}/station_n16_tx100.yaml",
    "station_n02_tx025": f"{SENSITIVITY_DIR}/station_n02_tx025.yaml",
    "station_n16_tx200": f"{SENSITIVITY_DIR}/station_n16_tx200.yaml",
}
ALGO_CLASSES = {
    "ChargeAsFastAsPossible": ChargeAsFastAsPossible,
    "RoundRobin": RoundRobin,
}

# (scenario_name, ambient_profile_fn or None, delta_t_charging_c)
# "default" reuses ev.py's own theta=298.15K result directly -- no wrapper call.
AMBIENT_SCENARIOS = [
    ("default", None, 0.0),
    ("bogota_outdoor", outdoor_ambient_c, 0.0),
    ("bogota_outdoor_plus5", outdoor_ambient_c, 5.0),
    ("bogota_underground", underground_ambient_c, 0.0),
]

OUTPUT_COLUMNS = [
    "run_id", "config_name", "algorithm", "seed", "eval_day", "ambient_scenario",
    "n_evs_with_session", "sum_d_cal", "sum_d_cal_point_estimate", "jensen_gap_pct",
    "sum_d_cyc_unchanged",
]


def load_registry_rows():
    rows = []
    with open(REGISTRY_PATH, newline="") as f:
        for row in csv.DictReader(f):
            if row["notes"] == "pipeline_smoke_test_grid":
                continue  # excluded per 02_model_validation.md
            if row["config_name"] not in CONFIG_PATHS:
                continue
            rows.append(row)
    return rows


def existing_output_run_ids():
    if not os.path.exists(OUTPUT_PATH):
        return set()
    with open(OUTPUT_PATH, newline="") as f:
        return {r["run_id"] for r in csv.DictReader(f) if r["ambient_scenario"] == "default"}


def measure_one(registry_row):
    config_name = registry_row["config_name"]
    algo_name = registry_row["algorithm"]
    seed = int(registry_row["seed"])
    eval_day_str = registry_row["eval_day"]
    year, month, day = (int(x) for x in eval_day_str.split("-"))

    config_path = CONFIG_PATHS[config_name]
    day_config_path = make_day_config(config_path, year, month, day, TMP_DAY_CONFIG_DIR)

    env = EV2Gym(config_file=day_config_path, seed=seed, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=seed)
    algo_cls = ALGO_CLASSES[algo_name]
    try:
        agent = algo_cls(env)
    except TypeError:
        agent = algo_cls()

    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break

    sim_starting_date = env.sim_starting_date
    timescale = env.timescale

    results = []
    for scenario_name, profile_fn, delta_t in AMBIENT_SCENARIOS:
        n_with_session = 0
        sum_d_cal = 0.0
        sum_d_cal_point = 0.0
        sum_d_cyc = 0.0
        for ev in env.EVs:
            if not ev.historic_soc:
                continue
            d_cal_orig, d_cyc_orig = ev.get_battery_degradation()
            sum_d_cyc += d_cyc_orig

            if scenario_name == "default":
                sum_d_cal += d_cal_orig
                sum_d_cal_point += d_cal_orig
                n_with_session += 1
                continue

            r = recompute_calendar_degradation(
                ev, sim_starting_date, timescale, profile_fn, delta_t_charging_c=delta_t)
            if r is None:
                continue
            sum_d_cal += r["d_cal"]
            sum_d_cal_point += r["d_cal_point_estimate"]
            n_with_session += 1

        jensen_gap_pct = ((sum_d_cal - sum_d_cal_point) / sum_d_cal * 100) if sum_d_cal else float("nan")
        results.append({
            "run_id": registry_row["run_id"],
            "config_name": config_name,
            "algorithm": algo_name,
            "seed": seed,
            "eval_day": eval_day_str,
            "ambient_scenario": scenario_name,
            "n_evs_with_session": n_with_session,
            "sum_d_cal": sum_d_cal,
            "sum_d_cal_point_estimate": sum_d_cal_point,
            "jensen_gap_pct": jensen_gap_pct,
            "sum_d_cyc_unchanged": sum_d_cyc,
        })
    return results


def append_output(rows):
    file_exists = os.path.exists(OUTPUT_PATH)
    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--scope", choices=["reference", "full"], default="full",
                         help="'reference' = only station_v0_bogota's 100 backfill rows "
                              "(~10 min); 'full' = all 500 rows across all 5 configs (~45-50 min)")
    args = parser.parse_args()

    registry_rows = load_registry_rows()
    if args.scope == "reference":
        registry_rows = [r for r in registry_rows
                          if r["config_name"] == "station_v0_bogota" and r["notes"] == ""]

    total = len(registry_rows)

    if not args.execute:
        print(f"Scope: {args.scope}. Registry rows to re-simulate and measure: {total}")
        print("Each is re-run once, then measured under 4 ambient scenarios: "
              + ", ".join(s[0] for s in AMBIENT_SCENARIOS))
        t0 = time.perf_counter()
        measure_one(registry_rows[0])
        sample_s = time.perf_counter() - t0
        est_total_s = sample_s * total
        print(f"Sample run: {sample_s:.2f}s")
        print(f"Estimated total runtime: {est_total_s:.1f}s (~{est_total_s/60:.1f} min), "
              f"linear extrapolation from one sample.")
        print("Did NOT write output (dry run). Re-run with --execute to launch.")
        sys.exit(0)

    existing = existing_output_run_ids()
    appended, skipped = 0, 0
    for i, registry_row in enumerate(registry_rows):
        if registry_row["run_id"] in existing:
            skipped += 1
            print(f"[{i+1}/{total}] {registry_row['run_id']}: skipped (already measured)")
            continue
        rows = measure_one(registry_row)
        append_output(rows)
        existing.add(registry_row["run_id"])
        appended += 1
        default_row = next(r for r in rows if r["ambient_scenario"] == "default")
        outdoor_row = next(r for r in rows if r["ambient_scenario"] == "bogota_outdoor")
        print(f"[{i+1}/{total}] {registry_row['run_id']}: measured 4 scenarios "
              f"(default sum_d_cal={default_row['sum_d_cal']:.4e}, "
              f"outdoor sum_d_cal={outdoor_row['sum_d_cal']:.4e})")

    print(f"\nDone. appended={appended}, skipped={skipped}")
