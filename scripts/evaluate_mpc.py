"""
Week 5, Part B, section 13: evaluate the two MPC arms on the SEEDS x
EVAL_DAYS grid, via env_factory.make_env / reset_for_evaluation -- the
same mechanism every other arm's evaluation uses.

--variant {tracking,energy_max} selects which controller runs (default:
both, via all_run_specs()); mirrors evaluate_oracle.py's --variant
convention rather than forking a second script.

Rows get algorithm_family="mpc" (already an allowed value in
ALGORITHM_FAMILIES). `notes` records solver, control horizon, the
information set from the Gate 1 audit, and the price basis, following the
existing `reward=...,state=...` convention so
`assert_total_reward_comparable` keeps working (total_reward is left
blank for both MPC arms, matching the oracle -- MPC bypasses
reward_function/state_function entirely, same as the Gurobi oracle,
S4.5's rule extended here).

Dedup pre-check against registry.load_existing_keys() happens BEFORE
simulating a cell, not at write time -- the Week 2 backfill lesson,
applied here too. Because this project's registry now distinguishes
analysis_row (Week 5, Gate 3/Gate 4), the dedup check here is
analysis_row-aware -- a stale (pre-fix) row sharing the same
(config, algorithm, seed, eval_day) key must NOT cause a skip.

Usage:
    PYTHONPATH=. python scripts/evaluate_mpc.py                          # dry run, both variants
    PYTHONPATH=. python scripts/evaluate_mpc.py --execute                # run both variants
    PYTHONPATH=. python scripts/evaluate_mpc.py --execute --variant tracking
"""
import argparse
import datetime
import sys
import time

import pandas as pd

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS, day_type
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from ev2gym_thesis.mpc.tracking_mpc import MPCTrackingG2V, DEFAULT_CONTROL_HORIZON
from ev2gym_thesis.mpc.energy_max_mpc import MPCEnergyMaxG2V, FLAT_PRICE_CONSTANT
from ev2gym_thesis.registry import append_runs, save_timeseries, stats_to_row, get_git_commit, REGISTRY_PATH

REFERENCE_CONFIG_NAME = "station_v0_bogota"
REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
N_PORTS = 8
TRANSFORMER_KW = 100

# doc:begin mpc_variants
VARIANTS = {
    "tracking": {
        "algorithm_name": "MPC_TrackingG2V",
        "agent_cls": MPCTrackingG2V,
        "notes": (f"reward=none,state=none,solver=gurobi,control_horizon={DEFAULT_CONTROL_HORIZON},"
                  f"objective=tracking_error,price_basis=none,"
                  f"info=causal_transformer_forecast+noncausal_departure_time+"
                  f"noncausal_arrival_within_horizon"),
    },
    "energy_max": {
        "algorithm_name": "MPC_EnergyMaxG2V",
        "agent_cls": MPCEnergyMaxG2V,
        "notes": (f"reward=none,state=none,solver=gurobi,control_horizon={DEFAULT_CONTROL_HORIZON},"
                  f"objective=flat_price_energy_delivery,price_basis=flat_constant_{FLAT_PRICE_CONSTANT},"
                  f"info=causal_transformer_forecast+noncausal_departure_time+"
                  f"noncausal_arrival_within_horizon"),
    },
}
# doc:end mpc_variants


def analysis_row_existing_keys() -> set:
    """analysis_row-aware dedup check -- a stale (superseded) row sharing
    the same (config, algorithm, seed, eval_day) key must not cause a
    skip; only a row already produced under the corrected setpoint/price
    code (analysis_row=True) counts as 'already done'."""
    import os
    if not os.path.exists(REGISTRY_PATH):
        return set()
    df = pd.read_csv(REGISTRY_PATH, dtype=str, keep_default_na=False)
    done = df[df["analysis_row"] == "True"]
    return set(zip(done["config_name"], done["algorithm"], done["seed"], done["eval_day"]))


def run_single(variant: str, seed, eval_day, git_commit):
    spec = VARIANTS[variant]
    algorithm_name = spec["algorithm_name"]
    year, month, day = eval_day
    eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
    dtype = day_type(eval_day)
    run_id = f"{REFERENCE_CONFIG_NAME}__{algorithm_name}__seed{seed}__{eval_day_str}"

    env = make_env(REFERENCE_CONFIG_PATH, eval_day, seed)
    reset_for_evaluation(env, seed)
    agent = spec["agent_cls"](env, control_horizon=DEFAULT_CONTROL_HORIZON)

    t0 = time.perf_counter()
    transformer_power_ts, n_connected_ts = [], []
    stats = None
    done = truncated = False
    while not done and not truncated:
        actions = agent.get_action(env)
        _, _, done, truncated, stats = env.step(actions)
        transformer_power_ts.append([tr.current_power for tr in env.transformers])
        n_connected_ts.append(sum(cs.n_evs_connected for cs in env.charging_stations))
    runtime_s = time.perf_counter() - t0

    save_timeseries(run_id, station_power=env.current_power_usage.copy(),
                     transformer_power=transformer_power_ts, n_connected_evs=n_connected_ts)

    row = {
        "run_id": run_id, "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "git_commit": git_commit, "config_name": REFERENCE_CONFIG_NAME,
        "n_ports": N_PORTS, "transformer_kw": TRANSFORMER_KW,
        "oversubscription_ratio": round(N_PORTS * 50 / TRANSFORMER_KW, 3),
        "algorithm": algorithm_name, "algorithm_family": "mpc", "seed": seed,
        "eval_day": eval_day_str, "sim_steps": 96, "runtime_s": round(runtime_s, 4),
        "notes": spec["notes"], "day_type": dtype,
        "scenario_id": f"{seed}_{dtype}", "analysis_row": True, "superseded": False,
    }
    row.update(stats_to_row(stats))
    row["total_reward"] = None  # undefined -- MPC bypasses reward_function/state_function, same as the oracle
    return row


def all_run_specs(variants=None):
    variants = variants or list(VARIANTS.keys())
    return [(v, seed, eval_day) for v in variants for seed in SEEDS for eval_day in EVAL_DAYS]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--variant", choices=list(VARIANTS.keys()), default=None,
                         help="Run only this variant. Default: both.")
    args = parser.parse_args()
    variants = [args.variant] if args.variant else list(VARIANTS.keys())

    specs = all_run_specs(variants)
    print(f"Variants: {variants}. Scenario seeds: {len(SEEDS)}, eval days: {len(EVAL_DAYS)}. "
          f"Total runs: {len(specs)}")

    if not args.execute:
        print("Dry run only -- did NOT write to the registry. Re-run with --execute.")
        sys.exit(0)

    git_commit = get_git_commit()
    existing_keys = analysis_row_existing_keys()
    appended_total, skipped_total = 0, 0

    for i, (variant, seed, eval_day) in enumerate(specs):
        algorithm_name = VARIANTS[variant]["algorithm_name"]
        year, month, day = eval_day
        eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
        key = (REFERENCE_CONFIG_NAME, algorithm_name, str(seed), eval_day_str)
        if key in existing_keys:
            skipped_total += 1
            print(f"[{i+1}/{len(specs)}] {algorithm_name}__seed{seed}__{eval_day_str}: skipped (already an analysis_row)")
            continue

        row = run_single(variant, seed, eval_day, git_commit)
        result = append_runs([row], force=True)  # force=True: bypass the raw-key dedup, which would false-skip on a stale superseded row sharing the same key
        existing_keys.add(key)
        appended_total += result["appended"]
        print(f"[{i+1}/{len(specs)}] {row['run_id']}: appended, runtime={row['runtime_s']}s, "
              f"tracking_error={row['tracking_error']:.1f}, overload={row['total_transformer_overload']:.4f}")

    print(f"\nMPC evaluation complete. appended={appended_total}, skipped={skipped_total}")
