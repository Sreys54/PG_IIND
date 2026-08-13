"""
Week 3, Entregable 6: evaluate the 3 trained TD3 checkpoints plus a
random-policy negative control on the SAME 50-cell grid (SEEDS x
EVAL_DAYS) already used for AFAP/Round Robin in Weeks 1-2 -- via
ev2gym_thesis.rl.env_factory.make_env, the identical config_utils
day-override mechanism backfill_registry.py uses, so this is a paired
comparison over literally identical scenarios, not merely similar ones.

Deterministic evaluation (predict(..., deterministic=True) for TD3): per
thesis_docs/chapters/03_rl_baseline.md, this isolates policy quality from
training-time exploration noise, which is a training concern, not an
evaluation one.

Random-policy control: without it, "TD3 beats AFAP" cannot be
distinguished from "any policy that spreads power around beats AFAP in
this 4:1-oversubscribed configuration" -- the control is what turns the
comparison into evidence the agent learned something (Week 3 brief S6).
Its action_space is seeded with the scenario seed so it is reproducible
per (seed, eval_day) cell, consistent with how every other source of
randomness in this project is seed-controlled.

Registry key collision, resolved per the brief: DEDUP_KEY_COLUMNS =
(config_name, algorithm, seed, eval_day) uses the SCENARIO seed (SEEDS),
not the training seed -- so each of the 3 training seeds gets its own
algorithm name (TD3_vanilla_ts100/_ts101/_ts102) rather than colliding
under one "TD3_vanilla" name. No aggregated/averaged rows are written here
-- the registry stores individual runs only; aggregation is Entregable 7's
job.

Usage:
    PYTHONPATH=. python scripts/evaluate_rl.py             # dry run: report plan, do not execute
    PYTHONPATH=. python scripts/evaluate_rl.py --execute    # actually run the evaluation
"""
import argparse
import datetime
import sys
import time

import numpy as np

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS, TRAIN_SEEDS
from ev2gym_thesis.rl.env_factory import make_env, DEFAULT_REWARD_FN, DEFAULT_STATE_FN
from ev2gym_thesis.rl.eval_utils import load_trained_agent, vecnormalize_path_for
from ev2gym_thesis.registry import append_runs, save_timeseries, stats_to_row, get_git_commit, load_existing_keys

REFERENCE_CONFIG_NAME = "station_v0_bogota"
REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
N_PORTS = 8
TRANSFORMER_KW = 100
MODELS_DIR = "experiments/phase2_algorithms/models"

TD3_ALGORITHMS = [
    ("TD3_vanilla_ts100", 100, f"{MODELS_DIR}/TD3_vanilla_ts100/final_model.zip"),
    ("TD3_vanilla_ts101", 101, f"{MODELS_DIR}/TD3_vanilla_ts101/final_model.zip"),
    ("TD3_vanilla_ts102", 102, f"{MODELS_DIR}/TD3_vanilla_ts102/final_model.zip"),
]
RANDOM_POLICY_ALGORITHM = "RandomPolicy"


def _notes_for(train_seed=None):
    base = f"reward={DEFAULT_REWARD_FN.__name__},state={DEFAULT_STATE_FN.__name__}"
    return base + (f",train_seed={train_seed}" if train_seed is not None else ",control=random_policy")


def _unwrap_ev2gym(venv):
    """venv is VecNormalize(DummyVecEnv([env])); the raw EV2Gym instance
    (for per-step timeseries capture, matching scripts/backfill_registry.py's
    pattern) lives at venv.venv.envs[0]."""
    return venv.venv.envs[0]


def _run_and_capture(step_fn, env) -> tuple:
    """Runs one episode via step_fn(obs) -> action, capturing per-step
    transformer_power/n_connected_evs the same way
    scripts/backfill_registry.py does (per-step snapshot, not a single
    final-step read -- see that script's comment on the bug this avoids)."""
    obs = step_fn.reset()
    done = False
    stats = None
    transformer_power_ts = []
    n_connected_ts = []
    while not done:
        action = step_fn.act(obs)
        obs, reward, done, info = step_fn.step(action)
        transformer_power_ts.append([tr.current_power for tr in env.transformers])
        n_connected_ts.append(sum(cs.n_evs_connected for cs in env.charging_stations))
        stats = info
    return stats, transformer_power_ts, n_connected_ts


class _TD3Stepper:
    """Runs a TD3 model against the RAW (non-VecEnv) env, manually applying
    the loaded VecNormalize's observation normalization before each
    model.predict() call.

    Deliberately does NOT step through the VecEnv/VecNormalize wrapper
    returned by load_trained_agent: SB3's DummyVecEnv auto-resets its
    underlying env INSIDE the same step() call that returns the terminal
    transition (standard VecEnv semantics, so the next reset() isn't
    needed), which silently wipes env.current_power_usage/env.transformers/
    env.charging_stations before external code can read them for timeseries
    capture -- caught by f01_power_profile's visual QA (Week 3, Entregable
    7: TD3's plotted power curve was flat at zero for the whole day despite
    the episode's own stats correctly reporting 13 EVs served), not assumed
    or guessed at. Confirmed empirically that scalar evaluation metrics
    (info dict) are UNAFFECTED by this bug -- SB3 preserves the pre-reset
    info/stats dict via its own terminal-observation handling -- only the
    saved per-step timeseries were corrupted; this stepper's stats are
    identical to the original VecEnv-stepper's, only the timeseries
    capture changes.
    """

    def __init__(self, model, venv, env):
        self.model = model
        self.venv = venv  # loaded VecNormalize instance, used only for its normalize_obs() stats -- never stepped
        self.env = env

    def reset(self):
        obs, _ = self.env.reset()
        return obs

    def act(self, obs):
        norm_obs = self.venv.normalize_obs(obs)
        action, _ = self.model.predict(norm_obs, deterministic=True)
        return action

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        return obs, reward, (terminated or truncated), info


class _RandomPolicyStepper:
    """A control policy: samples uniformly from the env's own action_space,
    seeded with the scenario seed for reproducibility. No model, no
    VecNormalize -- runs the raw EV2Gym env directly, same protocol as
    scripts/backfill_registry.py's heuristics."""

    def __init__(self, env, scenario_seed: int):
        self.env = env
        self.env.action_space.seed(scenario_seed)

    def reset(self):
        obs, _ = self.env.reset(seed=None)  # scenario seed already applied via make_env's EV2Gym(seed=...)
        return obs

    def act(self, obs):
        return self.env.action_space.sample()

    def step(self, action):
        obs, reward, done, truncated, info = self.env.step(action)
        return obs, reward, done, info


def eval_td3(algo_name, train_seed, model_path, seed, eval_day, git_commit):
    year, month, day = eval_day
    eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
    env = make_env(REFERENCE_CONFIG_PATH, eval_day, seed)
    model, venv = load_trained_agent(model_path, env)

    t0 = time.perf_counter()
    stepper = _TD3Stepper(model, venv, env)
    stats, transformer_power_ts, n_connected_ts = _run_and_capture(stepper, env)
    runtime_s = time.perf_counter() - t0

    run_id = f"{REFERENCE_CONFIG_NAME}__{algo_name}__seed{seed}__{eval_day_str}"
    save_timeseries(run_id, station_power=env.current_power_usage.copy(),
                     transformer_power=transformer_power_ts, n_connected_evs=n_connected_ts)

    row = {
        "run_id": run_id, "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "git_commit": git_commit, "config_name": REFERENCE_CONFIG_NAME,
        "n_ports": N_PORTS, "transformer_kw": TRANSFORMER_KW,
        "oversubscription_ratio": round(N_PORTS * 50 / TRANSFORMER_KW, 3),
        "algorithm": algo_name, "algorithm_family": "rl", "seed": seed,
        "eval_day": eval_day_str, "sim_steps": 96, "runtime_s": round(runtime_s, 4),
        "notes": _notes_for(train_seed),
    }
    row.update(stats_to_row(stats))
    return row


def eval_random_policy(seed, eval_day, git_commit):
    year, month, day = eval_day
    eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
    env = make_env(REFERENCE_CONFIG_PATH, eval_day, seed)

    t0 = time.perf_counter()
    stepper = _RandomPolicyStepper(env, scenario_seed=seed)
    stats, transformer_power_ts, n_connected_ts = _run_and_capture(stepper, env)
    runtime_s = time.perf_counter() - t0

    run_id = f"{REFERENCE_CONFIG_NAME}__{RANDOM_POLICY_ALGORITHM}__seed{seed}__{eval_day_str}"
    save_timeseries(run_id, station_power=env.current_power_usage.copy(),
                     transformer_power=transformer_power_ts, n_connected_evs=n_connected_ts)

    row = {
        "run_id": run_id, "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "git_commit": git_commit, "config_name": REFERENCE_CONFIG_NAME,
        "n_ports": N_PORTS, "transformer_kw": TRANSFORMER_KW,
        "oversubscription_ratio": round(N_PORTS * 50 / TRANSFORMER_KW, 3),
        "algorithm": RANDOM_POLICY_ALGORITHM, "algorithm_family": "rl", "seed": seed,
        "eval_day": eval_day_str, "sim_steps": 96, "runtime_s": round(runtime_s, 4),
        "notes": _notes_for(train_seed=None),
    }
    row.update(stats_to_row(stats))
    return row


def all_run_specs():
    specs = []
    for algo_name, train_seed, model_path in TD3_ALGORITHMS:
        for seed in SEEDS:
            for eval_day in EVAL_DAYS:
                specs.append(("td3", algo_name, train_seed, model_path, seed, eval_day))
    for seed in SEEDS:
        for eval_day in EVAL_DAYS:
            specs.append(("random", RANDOM_POLICY_ALGORITHM, None, None, seed, eval_day))
    return specs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true",
                         help="Actually run the evaluation. Without this flag, only reports the plan.")
    args = parser.parse_args()

    specs = all_run_specs()
    print(f"TD3 checkpoints: {len(TD3_ALGORITHMS)}, scenario seeds: {len(SEEDS)}, eval days: {len(EVAL_DAYS)}")
    print(f"Total runs: {len(TD3_ALGORITHMS)} x {len(SEEDS)} x {len(EVAL_DAYS)} (TD3) "
          f"+ {len(SEEDS)} x {len(EVAL_DAYS)} (RandomPolicy) = {len(specs)}")

    if not args.execute:
        print("Dry run only -- did NOT write to the registry. Re-run with --execute.")
        sys.exit(0)

    git_commit = get_git_commit()
    existing_keys = load_existing_keys()
    appended_total, skipped_total = 0, 0

    for i, (kind, algo_name, train_seed, model_path, seed, eval_day) in enumerate(specs):
        year, month, day = eval_day
        eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
        key = (REFERENCE_CONFIG_NAME, algo_name, str(seed), eval_day_str)
        if key in existing_keys:
            skipped_total += 1
            print(f"[{i+1}/{len(specs)}] {algo_name}__seed{seed}__{eval_day_str}: skipped (already in registry)")
            continue

        if kind == "td3":
            row = eval_td3(algo_name, train_seed, model_path, seed, eval_day, git_commit)
        else:
            row = eval_random_policy(seed, eval_day, git_commit)

        result = append_runs([row])
        existing_keys.add(key)
        appended_total += result["appended"]
        skipped_total += result["skipped"]
        print(f"[{i+1}/{len(specs)}] {row['run_id']}: appended, runtime={row['runtime_s']}s, "
              f"total_ev_served={row['total_ev_served']}, "
              f"total_transformer_overload={row['total_transformer_overload']}")

    print(f"\nEvaluation complete. appended={appended_total}, skipped={skipped_total}")
