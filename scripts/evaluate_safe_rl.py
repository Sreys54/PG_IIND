"""
Week 8: evaluate a trained TD3_safe checkpoint on the final evaluation grid
(SEEDS 0-49 x EVAL_DAYS = 100 cells per demand level), with the same
transformer projection, state and reward the policy was trained with.

The cells are the ones every other arm was evaluated on, built the same way
(env_factory.make_env + reset_for_evaluation), so the comparison with AFAP,
both Round Robins and the bounds is paired by (seed, day):
  - regime dc42: the dwell brief's DC configs (scripts/run_dwell_capacity.py
    ::variant_config) at the requested demand levels; compare with
    results/dwell_registry.csv;
  - regime long: station_v0_bogota.yaml at 1.0x; compare with the
    analysis rows of results/master_results.csv.

Rows use the master registry schema and row conventions (stats_to_row,
_with_week5_fields) and go to a SEPARATE file, results/safe_rl_registry.csv,
so no existing registry is ever written. Demand not served is computed
afterwards from each cell's policy-independent censoring record
(results/dwell_censoring_by_cell.csv for dc42), as for every other arm.

Usage:
  PYTHONPATH=. python scripts/evaluate_safe_rl.py --model <ckpt.zip> --arm TD3_safe_dc42_ts100 --train-seed 100 --regime dc42             # dry run
  PYTHONPATH=. python scripts/evaluate_safe_rl.py --model <ckpt.zip> --arm TD3_safe_dc42_ts100 --train-seed 100 --regime dc42 --execute
"""
import argparse
import csv
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ev2gym_thesis.demand import dc_sessions
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.registry import REGISTRY_COLUMNS, get_git_commit, save_timeseries, stats_to_row
from ev2gym_thesis.rl import config_safe as cfg
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from ev2gym_thesis.rl.eval_utils import load_trained_agent
from ev2gym_thesis.rl.safety import safe_step

from scripts.run_week5_grid import _with_week5_fields

SAFE_REGISTRY = "results/safe_rl_registry.csv"
N_PORTS, TRANSFORMER_KW = 8, 100


def cell_config(regime, level):
    if regime == "dc42":
        from scripts.run_dwell_capacity import variant_config
        return variant_config(level, 42)
    assert level == 1.0, "the long-dwell regime is evaluated at the reference demand only"
    return "station_v0_bogota", cfg.REGIME_CONFIGS["long"]


# doc:begin eval_safe_cell
def eval_cell(model_path, arm, train_seed, regime, reward_key, level, seed, day, commit, day_config_dir):
    cfg_name, cfg_path = cell_config(regime, level)
    reward_fn = cfg.REWARD_FNS[reward_key]
    env = make_env(cfg_path, day, seed, reward_fn=reward_fn, state_fn=cfg.STATE_FN, day_config_dir=day_config_dir)
    model, venv = load_trained_agent(model_path, env)
    t0 = time.perf_counter()
    obs, _ = reset_for_evaluation(env, seed)
    done, stats, tr_power, n_conn, active = False, None, [], [], 0
    while not done:
        action, _ = model.predict(venv.normalize_obs(obs), deterministic=True)
        obs, _, terminated, truncated, stats, pinfo = safe_step(env, action)
        active += int(pinfo["active"])
        tr_power.append([tr.current_power for tr in env.transformers])
        n_conn.append(sum(cs.n_evs_connected for cs in env.charging_stations))
        done = terminated or truncated
    runtime = time.perf_counter() - t0
    ds = "%04d-%02d-%02d" % day
    run_id = f"{cfg_name}__{arm}__seed{seed}__{ds}"
    save_timeseries(run_id, station_power=env.current_power_usage.copy(), transformer_power=tr_power,
                    n_connected_evs=n_conn)
    row = {"run_id": run_id, "timestamp_utc": datetime.datetime.utcnow().isoformat(), "git_commit": commit,
           "config_name": cfg_name, "n_ports": N_PORTS, "transformer_kw": TRANSFORMER_KW,
           "oversubscription_ratio": round(N_PORTS * 50 / TRANSFORMER_KW, 3), "algorithm": arm,
           "algorithm_family": "rl", "seed": seed, "eval_day": ds, "sim_steps": env.simulation_length,
           "runtime_s": round(runtime, 4),
           "notes": (f"design=safe_hard_transformer_constraint,reward={reward_fn.__name__},"
                     f"state={cfg.STATE_FN.__name__},train_seed={train_seed},regime={regime},demand_level={level},"
                     f"checkpoint={os.path.basename(model_path)},projection_active_steps={active}")}
    row.update(stats_to_row(stats))
    row = _with_week5_fields(row, seed, day)
    row["simulate_grid"] = False
    return row
# doc:end eval_safe_cell


def existing_keys(path=SAFE_REGISTRY):
    if not os.path.exists(path):
        return set()
    with open(path, newline="") as f:
        return {(r["config_name"], r["algorithm"], r["seed"], r["eval_day"]) for r in csv.DictReader(f)}


def append_row(row, path=SAFE_REGISTRY):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        if new:
            w.writeheader()
        w.writerow({c: row.get(c) for c in REGISTRY_COLUMNS})


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--arm", required=True, help="registry algorithm name, e.g. TD3_safe_dc42_ts100")
    p.add_argument("--train-seed", type=int, required=True)
    p.add_argument("--regime", choices=list(cfg.REGIME_CONFIGS), default=cfg.DEFAULT_REGIME)
    p.add_argument("--reward", choices=list(cfg.REWARD_FNS), default=cfg.DEFAULT_REWARD)
    p.add_argument("--levels", default="1.0,1.3,1.6")
    p.add_argument("--n-seeds", type=int, default=len(SEEDS))
    p.add_argument("--execute", action="store_true")
    a = p.parse_args(argv)

    levels = [float(x) for x in a.levels.split(",")]
    cells = [(lvl, s, d) for lvl in levels for s in SEEDS[:a.n_seeds] for d in EVAL_DAYS]
    print(f"{a.arm}: {len(levels)} level(s) x {a.n_seeds} seeds x {len(EVAL_DAYS)} days = {len(cells)} cells -> {SAFE_REGISTRY}")
    if not a.execute:
        print("Dry run only -- nothing written. Re-run with --execute.")
        return
    import torch
    torch.set_num_threads(1)  # standing fact: one torch thread per process (numerics depend on it)
    price_data_cache.enable()
    if a.regime == "dc42":
        dc_sessions.enable(dc_sessions.model_for_config(cfg.REGIME_CONFIGS["dc42"]))  # the 42-minute sidecar
    commit, done = get_git_commit(), existing_keys()
    day_dir = f"experiments/phase2_algorithms/configs/_tmp_eval_day_configs_safe_pid{os.getpid()}"
    try:
        for k, (lvl, s, d) in enumerate(cells):
            cfg_name, _ = cell_config(a.regime, lvl)
            key = (cfg_name, a.arm, str(s), "%04d-%02d-%02d" % d)
            if key in done:
                continue
            row = eval_cell(a.model, a.arm, a.train_seed, a.regime, a.reward, lvl, s, d, commit, day_dir)
            append_row(row)
            done.add(key)
            print(f"[{k + 1}/{len(cells)}] {row['run_id']}: energy={row['total_energy_charged']:.1f} kWh, "
                  f"overload={row['total_transformer_overload']}", flush=True)
    finally:
        dc_sessions.disable()


if __name__ == "__main__":
    main()
