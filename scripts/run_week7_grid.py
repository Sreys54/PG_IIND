"""
Week 7, Objective 4 (Step 2, also used for the 1d probes and 1e timing):
grid-enabled evaluation of the five fixed arms over the growth settings.

Arms (fixed by the brief): ChargeAsFastAsPossible, RoundRobin,
MPC_TrackingG2V, the final RL model (TD3_vanilla_extended_ts102 @ 850k), and
Optimal_Oracle_Tracking (the Week 5 oracle variant used in S5.6's tracking
optimality gap) as the upper bound.

Settings (two one-at-a-time axes, not a cross product; 5 distinct):
  base      spawn_multiplier 30 (1.0x), load_multiplier 1.0   (both axes)
  spawn1.3  spawn_multiplier 39 (1.3x), load_multiplier 1.0   (Axis 1, station demand)
  spawn1.6  spawn_multiplier 48 (1.6x), load_multiplier 1.0   (Axis 1)
  load1.3   spawn_multiplier 30,        load_multiplier 1.3   (Axis 2, feeder background)
  load1.6   spawn_multiplier 30,        load_multiplier 1.6   (Axis 2)

Reuses the REAL row builders, never re-implementations:
  scripts.backfill_registry.run_single   (AFAP, RoundRobin; config is a parameter)
  scripts.evaluate_mpc.run_single        (MPC_TrackingG2V)
  scripts.evaluate_oracle.run_single     (Optimal_Oracle_Tracking)
  scripts.evaluate_rl.eval_td3           (final RL model)
The last three read a module-level REFERENCE_CONFIG_PATH/NAME; for the
duration of one call they are pointed at the grid config of the setting
(`_target_config`) and restored afterwards.

Per-bus voltages are captured by wrapping the `get_statistics` name that
ev2gym_env.py imported (it runs once, at episode end) and checked with
ev2gym_thesis.grid.voltage.band_check; the per-run voltage summary goes to a
separate CSV (no new registry columns beyond simulate_grid).

Concurrency: each worker process writes its rows to its own shard CSV under
experiments/phase3_infra_replicability/results/shards/ -- never to the
registry. `--merge` appends all shards to results/master_results.csv once,
through append_runs, with analysis_row-aware dedup. Resumable: a worker skips
cells already present in its shard.

Usage:
  PYTHONPATH=. python scripts/run_week7_grid.py --worker 0 --n-workers 3 --seeds 30
  PYTHONPATH=. python scripts/run_week7_grid.py --merge
  PYTHONPATH=. python scripts/run_week7_grid.py --timing          (1e: one cell per arm)
  PYTHONPATH=. python scripts/run_week7_grid.py --probe ...       (1d, analysis_row=False)
"""
import argparse
import contextlib
import csv
import datetime
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ev2gym.models.ev2gym_env as _env_module
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.grid import placement
from ev2gym_thesis.grid.voltage import band_check
from ev2gym_thesis.registry import REGISTRY_COLUMNS, append_runs, get_git_commit
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.rl.env_factory import DEFAULT_REWARD_FN

from scripts import evaluate_mpc, evaluate_oracle, evaluate_rl
from scripts.backfill_registry import run_single as heuristic_run_single
from scripts.run_week5_grid import _with_week5_fields

BASE_GRID_CONFIG = "experiments/phase3_infra_replicability/configs/station_v0_bogota_grid.yaml"
CONFIG_DIR = "experiments/phase3_infra_replicability/configs"
OUT_DIR = "experiments/phase3_infra_replicability/results"
SHARD_DIR = f"{OUT_DIR}/shards"
VOLTAGE_TS_DIR = "results/timeseries/week7_voltage"
STATION_BUS = 27
BASE_SPAWN_MULTIPLIER = 30

# doc:begin week7_settings
SETTINGS = {
    "base": {"spawn_factor": 1.0, "load_multiplier": 1.0, "axes": ["axis1_station_demand", "axis2_feeder_background"]},
    "spawn1.3": {"spawn_factor": 1.3, "load_multiplier": 1.0, "axes": ["axis1_station_demand"]},
    "spawn1.6": {"spawn_factor": 1.6, "load_multiplier": 1.0, "axes": ["axis1_station_demand"]},
    "load1.3": {"spawn_factor": 1.0, "load_multiplier": 1.3, "axes": ["axis2_feeder_background"]},
    "load1.6": {"spawn_factor": 1.0, "load_multiplier": 1.6, "axes": ["axis2_feeder_background"]},
}
# doc:end week7_settings

# doc:begin final_rl_model
FINAL_RL_NAME = "TD3_vanilla_extended_ts102"
FINAL_RL_TRAIN_SEED = 102
FINAL_RL_STEP = 850_000
FINAL_RL_PATH = ("experiments/phase2_algorithms/models/TD3_vanilla_extended_ts102/checkpoints/"
                 "td3_vanilla_extended_ts102_850000_steps.zip")
# doc:end final_rl_model

ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "MPC_TrackingG2V", FINAL_RL_NAME, "Optimal_Oracle_Tracking"]


def config_name_for(setting: str, probe: dict = None) -> str:
    if probe:
        return f"station_v0_bogota_grid_probe_sp{probe['spawn_multiplier']}_lm{probe['load_multiplier']}"
    return "station_v0_bogota_grid" if setting == "base" else f"station_v0_bogota_grid_{setting}"


def write_config(name: str, spawn_multiplier: int, load_multiplier: float) -> str:
    """Derive a setting's YAML from the base grid config by changing only
    spawn_multiplier and load_multiplier (text replacement keeps every
    comment and every other key byte-identical)."""
    src = open(BASE_GRID_CONFIG, encoding="utf-8").read()
    old_sp = next(l for l in src.splitlines() if l.startswith("spawn_multiplier:"))
    old_lm = next(l for l in src.splitlines() if l.strip().startswith("load_multiplier:"))
    new = src.replace(old_sp, f"spawn_multiplier: {spawn_multiplier} # Week 7 growth setting (base 30)")
    new = new.replace(old_lm, f"  load_multiplier: {load_multiplier} # Week 7 growth setting (base 1.0)")
    path = f"{CONFIG_DIR}/{name}.yaml"
    if name == "station_v0_bogota_grid":
        return BASE_GRID_CONFIG
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return path


def setting_config(setting: str):
    s = SETTINGS[setting]
    name = config_name_for(setting)
    return name, write_config(name, int(round(BASE_SPAWN_MULTIPLIER * s["spawn_factor"])), s["load_multiplier"])


# ---------------------------------------------------------------------------
# Voltage capture
# ---------------------------------------------------------------------------
_ORIGINAL_GET_STATISTICS = _env_module.get_statistics
LAST_VOLTAGE = {}


def _capturing_get_statistics(env):
    stats = _ORIGINAL_GET_STATISTICS(env)
    if env.simulate_grid:
        LAST_VOLTAGE["v"] = np.array(env.node_voltage, copy=True)
    return stats


# doc:begin per_process_day_configs
def _per_process_day_configs():
    """config_utils.make_day_config rewrites <dir>/<config>__<date>.yaml on
    every call without locking. scripts/backfill_registry.py, env_factory.make_env
    and oracle/replay_utils all write to SHARED directories, so parallel
    workers can read a file another worker is half-way through writing --
    this crashed one Week 7 worker ('NoneType' config). Same failure as
    Week 6 Part 0. Every module's make_day_config name is redirected to a
    per-process sibling directory (<dir>_pid<PID>); the files written are
    byte-identical, only the location changes."""
    import ev2gym_thesis.config_utils as cu
    import ev2gym_thesis.rl.env_factory as ef
    import ev2gym_thesis.oracle.replay_utils as ru
    import scripts.backfill_registry as br
    original = cu.make_day_config
    if getattr(original, "_per_process", False):
        return

    def make_day_config(base_config_path, year, month, day, out_dir):
        return original(base_config_path, year, month, day, f"{out_dir}_pid{os.getpid()}")
    make_day_config._per_process = True
    for mod in (cu, ef, ru, br):
        mod.make_day_config = make_day_config

    # Oracle replays are named sim_<date>_<random seeded by the scenario
    # seed>, so two workers on the same seed (different settings) could write
    # the same file name. Per-process replay directories rule that out; the
    # replay contents are unchanged.
    def build_g2v_replay_for_cell(config_path, day, scenario_seed):
        pid = os.getpid()
        raw = ru.generate_replay(config_path, day, scenario_seed,
                                 replay_dir=ru.RAW_REPLAY_DIR.rstrip("/") + f"_pid{pid}/")
        return ru.force_g2v(raw, out_dir=ru.G2V_REPLAY_DIR.rstrip("/") + f"_pid{pid}/")
    evaluate_oracle.build_g2v_replay_for_cell = build_g2v_replay_for_cell
# doc:end per_process_day_configs


def enable_process_hooks():
    torch.set_num_threads(1)
    price_data_cache.enable()
    placement.enable()
    _per_process_day_configs()
    _env_module.get_statistics = _capturing_get_statistics
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


@contextlib.contextmanager
def _target_config(module, name, path):
    old = (module.REFERENCE_CONFIG_NAME, module.REFERENCE_CONFIG_PATH)
    module.REFERENCE_CONFIG_NAME, module.REFERENCE_CONFIG_PATH = name, path
    try:
        yield
    finally:
        module.REFERENCE_CONFIG_NAME, module.REFERENCE_CONFIG_PATH = old


# doc:begin run_cell
def run_cell(arm, cfg_name, cfg_path, seed, day, commit):
    LAST_VOLTAGE.clear()
    if arm == "ChargeAsFastAsPossible":
        row = heuristic_run_single(cfg_name, cfg_path, 8, 100, ChargeAsFastAsPossible, arm, "heuristic", seed, day, commit)
    elif arm == "RoundRobin":
        row = heuristic_run_single(cfg_name, cfg_path, 8, 100, RoundRobin, arm, "heuristic", seed, day, commit)
    elif arm == "MPC_TrackingG2V":
        with _target_config(evaluate_mpc, cfg_name, cfg_path):
            row = evaluate_mpc.run_single("tracking", seed, day, commit)
    elif arm == FINAL_RL_NAME:
        with _target_config(evaluate_rl, cfg_name, cfg_path):
            row = evaluate_rl.eval_td3(FINAL_RL_NAME, FINAL_RL_TRAIN_SEED, FINAL_RL_PATH, DEFAULT_REWARD_FN,
                                       seed, day, commit)
        row["notes"] += f",checkpoint_step={FINAL_RL_STEP},final_rl_model=author_decision_2026-10-05"
    elif arm == "Optimal_Oracle_Tracking":
        with _target_config(evaluate_oracle, cfg_name, cfg_path):
            row = evaluate_oracle.run_single(seed, day, commit, "tracking")
    else:
        raise ValueError(arm)
    row = _with_week5_fields(row, seed, day)
    row["simulate_grid"] = True
    v = LAST_VOLTAGE.get("v")
    if v is None:
        raise RuntimeError(f"{row['run_id']}: no grid voltage captured -- was the env built with simulate_grid=True?")
    return row, v
# doc:end run_cell


def voltage_record(row, v, setting):
    bc = band_check(v, station_bus=STATION_BUS)
    os.makedirs(VOLTAGE_TS_DIR, exist_ok=True)
    np.savez_compressed(f"{VOLTAGE_TS_DIR}/{row['run_id']}.npz", node_voltage=v)
    return {"run_id": row["run_id"], "config_name": row["config_name"], "setting": setting,
            "algorithm": row["algorithm"], "seed": row["seed"], "eval_day": row["eval_day"],
            "day_type": row.get("day_type"), "lib_voltage_violation": row["voltage_violation"],
            "lib_voltage_violation_counter": row["voltage_violation_counter"], **bc}


def _append_csv(path, rec, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rec))
        if new:
            w.writeheader()
        w.writerow(rec)


def all_specs(settings, n_seeds):
    return [(st, arm, seed, day) for st in settings for seed in SEEDS[:n_seeds] for day in EVAL_DAYS for arm in ARMS]


# doc:begin worker
def worker(idx, n_workers, settings, n_seeds):
    enable_process_hooks()
    commit = get_git_commit()
    cfgs = {st: setting_config(st) for st in settings}
    shard = f"{SHARD_DIR}/registry_rows_w{idx}.csv"
    vshard = f"{SHARD_DIR}/voltage_w{idx}.csv"
    done = set()
    if os.path.exists(shard):
        d = pd.read_csv(shard, dtype=str, keep_default_na=False)
        done = set(zip(d.config_name, d.algorithm, d.seed, d.eval_day))
    specs = [s for i, s in enumerate(all_specs(settings, n_seeds)) if i % n_workers == idx]
    t0 = time.time()
    for k, (st, arm, seed, day) in enumerate(specs):
        cfg_name, cfg_path = cfgs[st]
        key = (cfg_name, arm, str(seed), "%04d-%02d-%02d" % day)
        if key in done:
            continue
        tc = time.time()
        row, v = run_cell(arm, cfg_name, cfg_path, seed, day, commit)
        row["notes"] = (row["notes"] or "") + (f",grid_setting={st},station_bus={STATION_BUS},"
                                                f"spawn_multiplier={int(round(BASE_SPAWN_MULTIPLIER * SETTINGS[st]['spawn_factor']))},"
                                                f"load_multiplier={SETTINGS[st]['load_multiplier']}")
        _append_csv(shard, {c: row.get(c) for c in REGISTRY_COLUMNS}, REGISTRY_COLUMNS)
        _append_csv(vshard, voltage_record(row, v, st))
        done.add(key)
        with open(f"{SHARD_DIR}/progress_w{idx}.json", "w") as f:
            json.dump({"worker": idx, "done_in_this_run": k + 1, "of": len(specs), "last": list(key),
                       "last_cell_s": round(time.time() - tc, 2), "elapsed_s": round(time.time() - t0, 1),
                       "utc": datetime.datetime.utcnow().isoformat()}, f)
    print(f"worker {idx}: finished {len(specs)} cells in {time.time() - t0:.0f}s", flush=True)
# doc:end worker


# doc:begin merge
def merge():
    """Append every shard row to the registry exactly once (dedup on the
    registry's own key), and concatenate the voltage shards."""
    from scripts.evaluate_mpc import analysis_row_existing_keys
    existing = analysis_row_existing_keys()
    rows = []
    for p in sorted(glob.glob(f"{SHARD_DIR}/registry_rows_w*.csv")):
        rows += pd.read_csv(p, dtype=str, keep_default_na=False).to_dict("records")
    todo = []
    for r in rows:
        key = (r["config_name"], r["algorithm"], str(r["seed"]), r["eval_day"])
        if key not in existing:
            for c in ("analysis_row", "superseded", "simulate_grid"):
                r[c] = r[c] == "True"
            todo.append(r)
            existing.add(key)
    res = append_runs(todo, force=True) if todo else {"appended": 0}
    vs = [pd.read_csv(p) for p in sorted(glob.glob(f"{SHARD_DIR}/voltage_w*.csv"))]
    if vs:
        pd.concat(vs, ignore_index=True).drop_duplicates("run_id").to_csv("results/week7_voltage_by_run.csv", index=False)
    print(f"merge: {len(rows)} shard rows, appended {res['appended']}")
# doc:end merge


def timing():
    """1e: one grid cell per arm, end to end, at the base setting (seed 0, weekday)."""
    enable_process_hooks()
    commit = get_git_commit()
    name, path = setting_config("base")
    out = []
    for arm in ARMS:
        t = time.time()
        row, v = run_cell(arm, name, path, 0, EVAL_DAYS[0], commit)
        out.append({"arm": arm, "seconds": round(time.time() - t, 2), "tracking_error": row["tracking_error"],
                    "total_transformer_overload": row["total_transformer_overload"],
                    "notes_status": "status=OPTIMAL" in str(row["notes"]) if "Oracle" in arm else ""})
        print(out[-1], flush=True)
    pd.DataFrame(out).to_csv(f"{OUT_DIR}/week7_timing_one_cell.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int)
    ap.add_argument("--n-workers", type=int, default=1)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--settings", default=",".join(SETTINGS))
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--timing", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge()
    elif a.timing:
        timing()
    else:
        worker(a.worker, a.n_workers, a.settings.split(","), a.seeds)
