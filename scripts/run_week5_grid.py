"""
Week 5, Gate 4: the single, homogeneous grid pass for all 13 arms on the
corrected code (ev2gym/utilities/utils.py::generate_power_setpoints fixed,
MPCEnergyMaxG2V's price neutralized) -- SEEDS=range(0,50), EVAL_DAYS=2
representative days, per the Gate 4 decision. One pass, not a backfill:
the Week 2 duplicate-row problem was a backfill-after-the-fact mistake,
not repeated here.

Reuses the REAL production row-builders from each existing script, not
lookalikes:
  - scripts.backfill_registry.run_single (AFAP, RoundRobin)
  - scripts.evaluate_rl.eval_td3, eval_random_policy (6 TD3 + RandomPolicy)
  - scripts.evaluate_oracle.run_single (both Gurobi oracle variants)
  - scripts.evaluate_mpc.run_single (both MPC arms)

Every row gets day_type/scenario_id/analysis_row=True/superseded=False
added uniformly here (the four existing scripts' row-builders predate the
Week 5 schema and don't set these themselves). Dedup is analysis_row-aware
(scripts.evaluate_mpc.analysis_row_existing_keys): a stale pre-fix row
sharing the same (config, algorithm, seed, eval_day) key must not cause a
false skip.

Usage:
    PYTHONPATH=. python scripts/run_week5_grid.py            # dry run: report plan only
    PYTHONPATH=. python scripts/run_week5_grid.py --execute  # run the full grid
"""
import argparse
import sys
import time

from ev2gym.rl_agent.reward import SquaredTrackingErrorReward

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS, day_type
from ev2gym_thesis.registry import append_runs, get_git_commit

from scripts.backfill_registry import run_single as heuristic_run_single, ALGORITHMS as HEURISTIC_ALGORITHMS
from scripts.evaluate_rl import eval_td3, eval_random_policy, TD3_ALGORITHMS
from scripts.evaluate_oracle import run_single as oracle_run_single, VARIANTS as ORACLE_VARIANTS
from scripts.evaluate_mpc import run_single as mpc_run_single, VARIANTS as MPC_VARIANTS, analysis_row_existing_keys

REFERENCE_CONFIG_NAME = "station_v0_bogota"
REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"


def _with_week5_fields(row, seed, eval_day):
    dtype = day_type(eval_day)
    row["day_type"] = dtype
    row["scenario_id"] = f"{seed}_{dtype}"
    row["analysis_row"] = True
    row["superseded"] = False
    return row


def all_run_specs():
    """Returns a list of ("kind", label, seed, eval_day) tuples covering
    all 13 arms x 50 seeds x 2 days = 1300 cells."""
    specs = []
    for seed in SEEDS:
        for eval_day in EVAL_DAYS:
            specs.append(("heuristic_afap", None, seed, eval_day))
            specs.append(("heuristic_rr", None, seed, eval_day))
            for algo_name, train_seed, model_path, reward_fn in TD3_ALGORITHMS:
                specs.append(("td3", (algo_name, train_seed, model_path, reward_fn), seed, eval_day))
            specs.append(("random", None, seed, eval_day))
            for variant in ORACLE_VARIANTS:
                specs.append(("oracle", variant, seed, eval_day))
            for variant in MPC_VARIANTS:
                specs.append(("mpc", variant, seed, eval_day))
    return specs


def run_one(kind, payload, seed, eval_day, git_commit):
    if kind == "heuristic_afap":
        algo_cls, algo_name, algo_family = HEURISTIC_ALGORITHMS[0]
        row = heuristic_run_single(REFERENCE_CONFIG_NAME, REFERENCE_CONFIG_PATH, 8, 100,
                                    algo_cls, algo_name, algo_family, seed, eval_day, git_commit)
    elif kind == "heuristic_rr":
        algo_cls, algo_name, algo_family = HEURISTIC_ALGORITHMS[1]
        row = heuristic_run_single(REFERENCE_CONFIG_NAME, REFERENCE_CONFIG_PATH, 8, 100,
                                    algo_cls, algo_name, algo_family, seed, eval_day, git_commit)
    elif kind == "td3":
        algo_name, train_seed, model_path, reward_fn = payload
        row = eval_td3(algo_name, train_seed, model_path, reward_fn, seed, eval_day, git_commit)
    elif kind == "random":
        row = eval_random_policy(seed, eval_day, git_commit)
    elif kind == "oracle":
        row = oracle_run_single(seed, eval_day, git_commit, payload)
    elif kind == "mpc":
        row = mpc_run_single(payload, seed, eval_day, git_commit)
    else:
        raise ValueError(kind)
    return _with_week5_fields(row, seed, eval_day)


def algo_label(kind, payload):
    if kind == "heuristic_afap":
        return "ChargeAsFastAsPossible"
    if kind == "heuristic_rr":
        return "RoundRobin"
    if kind == "td3":
        return payload[0]
    if kind == "random":
        return "RandomPolicy"
    if kind == "oracle":
        return ORACLE_VARIANTS[payload]["algorithm_name"]
    if kind == "mpc":
        return MPC_VARIANTS[payload]["algorithm_name"]
    raise ValueError(kind)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    specs = all_run_specs()
    print(f"SEEDS={len(SEEDS)}, EVAL_DAYS={len(EVAL_DAYS)}, 13 arms -> {len(specs)} total cells")

    if not args.execute:
        print("Dry run only -- did NOT write to the registry. Re-run with --execute.")
        sys.exit(0)

    git_commit = get_git_commit()
    existing_keys = analysis_row_existing_keys()
    appended, skipped, errors = 0, 0, 0
    t_start = time.perf_counter()

    for i, (kind, payload, seed, eval_day) in enumerate(specs):
        algo_name = algo_label(kind, payload)
        year, month, day = eval_day
        eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
        key = (REFERENCE_CONFIG_NAME, algo_name, str(seed), eval_day_str)
        if key in existing_keys:
            skipped += 1
            continue

        try:
            row = run_one(kind, payload, seed, eval_day, git_commit)
        except SystemExit:
            print(f"[{i+1}/{len(specs)}] {algo_name}__seed{seed}__{eval_day_str}: "
                  f"Gurobi non-optimal, should have been caught internally -- re-raising")
            raise
        except Exception as exc:
            errors += 1
            print(f"[{i+1}/{len(specs)}] {algo_name}__seed{seed}__{eval_day_str}: ERROR: {exc}")
            continue

        result = append_runs([row], force=True)
        existing_keys.add(key)
        appended += result["appended"]
        if (i + 1) % 50 == 0 or (i + 1) == len(specs):
            elapsed = time.perf_counter() - t_start
            print(f"[{i+1}/{len(specs)}] appended={appended} skipped={skipped} errors={errors} "
                  f"elapsed={elapsed/60:.1f}min")

    print(f"\nGrid run complete. appended={appended}, skipped={skipped}, errors={errors}")
