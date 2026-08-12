"""
Week 2 Deliverable 3: backfill the master results registry.

Runs AFAP and Round Robin on station_v0_bogota.yaml (the Week 1 reference
config) plus the 4 station-size sensitivity configs, at every (seed, day)
combination in ev2gym_thesis.eval_protocol (5 seeds x 10 eval days = 50 runs
per config/algorithm pair). Also backfills the two Week 1 single-day rows
(seed=42, 2022-01-17) from the already-committed baseline_afap.csv /
baseline_roundrobin.csv, tagged notes="week1_reference_day", WITHOUT
re-running station_v0_bogota.yaml under that specific (seed, day) -- that
reference case is not to be re-run or overwritten.

Usage:
    python scripts/backfill_registry.py            # dry run: report run
                                                     # count + timing estimate,
                                                     # do not execute
    python scripts/backfill_registry.py --execute   # actually run the backfill
"""
import argparse
import csv
import datetime
import os
import sys
import time

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS
from ev2gym_thesis.config_utils import make_day_config
from ev2gym_thesis.registry import (
    append_runs, save_timeseries, stats_to_row, get_git_commit, load_existing_keys,
)

BASE_CONFIG_DIR = "experiments/phase1_baseline/configs"
SENSITIVITY_DIR = f"{BASE_CONFIG_DIR}/station_sensitivity"
TMP_DAY_CONFIG_DIR = "experiments/phase1_baseline/configs/_tmp_day_configs"

# (config_name, path, n_ports, transformer_kw)
CONFIGS = [
    ("station_v0_bogota", f"{BASE_CONFIG_DIR}/station_v0_bogota.yaml", 8, 100),
    ("station_n02_tx100", f"{SENSITIVITY_DIR}/station_n02_tx100.yaml", 2, 100),
    ("station_n16_tx100", f"{SENSITIVITY_DIR}/station_n16_tx100.yaml", 16, 100),
    ("station_n02_tx025", f"{SENSITIVITY_DIR}/station_n02_tx025.yaml", 2, 25),
    ("station_n16_tx200", f"{SENSITIVITY_DIR}/station_n16_tx200.yaml", 16, 200),
]

ALGORITHMS = [
    (ChargeAsFastAsPossible, "ChargeAsFastAsPossible", "heuristic"),
    (RoundRobin, "RoundRobin", "heuristic"),
]

WEEK1_REFERENCE = {
    "ChargeAsFastAsPossible": "experiments/phase1_baseline/results/baseline_afap.csv",
    "RoundRobin": "experiments/phase1_baseline/results/baseline_roundrobin.csv",
}


def week1_reference_rows():
    """Backfill the Week 1 single-day rows without re-running them."""
    git_commit = get_git_commit()
    rows = []
    for algo_name, csv_path in WEEK1_REFERENCE.items():
        with open(csv_path) as f:
            ref = next(csv.DictReader(f))
        row = {
            "run_id": f"station_v0_bogota__{algo_name}__seed{ref['seed']}__week1ref",
            "timestamp_utc": "",  # not recorded at the time of the original Week 1 run
            "git_commit": git_commit,
            "config_name": "station_v0_bogota",
            "n_ports": 8,
            "transformer_kw": 100,
            "oversubscription_ratio": round(8 * 50 / 100, 3),
            "algorithm": algo_name,
            "algorithm_family": "heuristic",
            "seed": ref["seed"],
            "eval_day": ref["sim_date"].split(" ")[0],
            "sim_steps": 96,
            "runtime_s": "",
            "notes": "week1_reference_day",
            "total_ev_served": int(ref["total_ev_served"]),
            "total_profits": float(ref["total_profits"]),
            "total_energy_charged": float(ref["total_energy_charged"]),
            "total_energy_discharged": "",
            "average_user_satisfaction": float(ref["average_user_satisfaction"]),
            "power_tracker_violation": "",
            "tracking_error": "",
            "energy_tracking_error": "",
            "energy_user_satisfaction": "",
            "std_energy_user_satisfaction": "",
            "min_energy_user_satisfaction": "",
            "total_steps_min_emergency_battery_capacity_violation": "",
            "total_transformer_overload": float(ref["total_transformer_overload"]),
            "battery_degradation": "",
            "battery_degradation_calendar": "",
            "battery_degradation_cycling": "",
            "total_reward": "",
            "saved_grid_energy": "",
            "voltage_violation": "",
            "voltage_violation_counter": "",
        }
        rows.append(row)
    return rows


def run_single(config_name, config_path, n_ports, transformer_kw,
                algo_cls, algo_name, algo_family, seed, eval_day, git_commit):
    year, month, day = eval_day
    day_config_path = make_day_config(config_path, year, month, day, TMP_DAY_CONFIG_DIR)

    t0 = time.perf_counter()
    env = EV2Gym(config_file=day_config_path, seed=seed, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=seed)
    try:
        agent = algo_cls(env)
    except TypeError:
        agent = algo_cls()

    stats = None
    transformer_power_ts = []
    n_connected_ts = []
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        # Snapshot per-step, not just after the loop -- tr.current_power and
        # cs.n_evs_connected are overwritten every step, so capturing them
        # only once at the end (the original bug here) silently produced a
        # single final-step value mislabeled as a full time series.
        transformer_power_ts.append([tr.current_power for tr in env.transformers])
        n_connected_ts.append(sum(cs.n_evs_connected for cs in env.charging_stations))
        if done:
            break
    runtime_s = time.perf_counter() - t0

    eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
    run_id = f"{config_name}__{algo_name}__seed{seed}__{eval_day_str}"

    save_timeseries(
        run_id,
        station_power=env.current_power_usage.copy(),
        transformer_power=transformer_power_ts,
        n_connected_evs=n_connected_ts,
    )

    row = {
        "run_id": run_id,
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "git_commit": git_commit,
        "config_name": config_name,
        "n_ports": n_ports,
        "transformer_kw": transformer_kw,
        "oversubscription_ratio": round(n_ports * 50 / transformer_kw, 3),
        "algorithm": algo_name,
        "algorithm_family": algo_family,
        "seed": seed,
        "eval_day": eval_day_str,
        "sim_steps": env.simulation_length,
        "runtime_s": round(runtime_s, 4),
        "notes": "",
    }
    row.update(stats_to_row(stats))
    return row


def all_run_specs():
    specs = []
    for config_name, config_path, n_ports, transformer_kw in CONFIGS:
        for algo_cls, algo_name, algo_family in ALGORITHMS:
            for seed in SEEDS:
                for eval_day in EVAL_DAYS:
                    specs.append((config_name, config_path, n_ports, transformer_kw,
                                  algo_cls, algo_name, algo_family, seed, eval_day))
    return specs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true",
                         help="Actually run the backfill. Without this flag, "
                              "only reports the run count and a timing estimate.")
    parser.add_argument("--force", action="store_true",
                         help="Re-run and overwrite rows that already exist in the registry.")
    args = parser.parse_args()

    specs = all_run_specs()
    total_new_sim_runs = len(specs)

    if not args.execute:
        print(f"Configs: {len(CONFIGS)}, Algorithms: {len(ALGORITHMS)}, "
              f"Seeds: {len(SEEDS)}, Eval days: {len(EVAL_DAYS)}")
        print(f"Total NEW simulation runs required: {total_new_sim_runs}")
        print("Plus 2 backfilled Week 1 reference rows (read from existing "
              "CSVs, not re-run).")
        print(f"Total registry rows after backfill: {total_new_sim_runs + 2}")
        print("\nTiming one sample run to estimate total runtime...")

        git_commit = get_git_commit()
        sample_config_name, sample_path, sample_n, sample_tx = CONFIGS[1]  # station_n02_tx100
        t0 = time.perf_counter()
        run_single(sample_config_name, sample_path, sample_n, sample_tx,
                   ChargeAsFastAsPossible, "ChargeAsFastAsPossible", "heuristic",
                   seed=999, eval_day=(2022, 1, 3), git_commit=git_commit)
        sample_s = time.perf_counter() - t0

        est_total_s = sample_s * total_new_sim_runs
        print(f"Sample run ({sample_config_name}, AFAP, seed=999, 2022-01-03): {sample_s:.2f}s")
        print(f"Estimated total runtime for {total_new_sim_runs} runs: "
              f"{est_total_s:.1f}s (~{est_total_s/60:.1f} min), single-threaded, "
              f"linear extrapolation from one sample.")
        print("\nDid NOT write to the registry (dry run). Re-run with --execute to launch the backfill.")
        sys.exit(0)

    git_commit = get_git_commit()
    rows = week1_reference_rows()
    result = append_runs(rows, force=args.force)
    print(f"Week 1 reference rows: appended={result['appended']}, skipped={result['skipped']}")

    # Pre-filter against the registry BEFORE simulating, not just before
    # writing -- resuming a paused backfill must not re-run (only re-skip)
    # already-completed (config, algorithm, seed, eval_day) combos.
    existing_keys = load_existing_keys() if not args.force else set()
    skipped_precheck = 0

    for i, (config_name, config_path, n_ports, transformer_kw,
            algo_cls, algo_name, algo_family, seed, eval_day) in enumerate(specs):
        year, month, day = eval_day
        eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
        key = (config_name, algo_name, str(seed), eval_day_str)
        if key in existing_keys and not args.force:
            skipped_precheck += 1
            print(f"[{i+1}/{total_new_sim_runs}] {config_name}__{algo_name}__seed{seed}__{eval_day_str}: "
                  f"skipped (already in registry, not re-simulated)")
            continue

        row = run_single(config_name, config_path, n_ports, transformer_kw,
                          algo_cls, algo_name, algo_family, seed, eval_day, git_commit)
        result = append_runs([row], force=args.force)
        existing_keys.add(key)
        status = "appended" if result["appended"] else "skipped (already in registry)"
        print(f"[{i+1}/{total_new_sim_runs}] {row['run_id']}: {status}, "
              f"runtime={row['runtime_s']}s, total_ev_served={row['total_ev_served']}")

    print(f"\nBackfill complete. Pre-check skipped {skipped_precheck} already-completed "
          f"runs without re-simulating them.")
