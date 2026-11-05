"""
Week 8 advisor review (2026-11-01), Gate 0: measured wall-clock time of one
evaluation case per arm, in both regimes, plus the TD3_safe gradient-update
cost, on this laptop. One process, one torch thread, nothing else running.

Cases: scenario seed 0, weekday (2022-01-17), through the same runner
functions every registry row was produced with. Nothing is written to any
registry; the timings go to experiments/phase4_review/gate0_timing.csv.

Usage:
  PYTHONPATH=. python scripts/review_gate0_timing.py
"""
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.demand import dc_sessions
from ev2gym_thesis.heuristics import RoundRobinTransformerCapped
from ev2gym_thesis.registry import get_git_commit

from scripts import evaluate_mpc, evaluate_oracle, evaluate_rl
from scripts import run_week7_grid as w7
from scripts.backfill_registry import run_single as heuristic_run_single

OUT = "experiments/phase4_review/gate0_timing.csv"
REGIMES = {
    "long": ("station_v0_bogota", "experiments/phase1_baseline/configs/station_v0_bogota.yaml"),
    "dc42_1.0x": ("station_v0_bogota_dc42_sp30",
                  "experiments/phase3_infra_replicability/configs/dwell/station_v0_bogota_dc42_sp30.yaml"),
}
SEED, DAY = 0, (2022, 1, 17)


def run_arm(arm, name, path, commit):
    if arm in ("ChargeAsFastAsPossible", "RoundRobin", "RoundRobin_TransformerCapped"):
        cls = {"ChargeAsFastAsPossible": ChargeAsFastAsPossible, "RoundRobin": RoundRobin,
               "RoundRobin_TransformerCapped": RoundRobinTransformerCapped}[arm]
        return heuristic_run_single(name, path, 8, 100, cls, arm, "heuristic", SEED, DAY, commit)
    if arm == "RandomPolicy":
        with w7._target_config(evaluate_rl, name, path):
            return evaluate_rl.eval_random_policy(SEED, DAY, commit)
    if arm in ("MPC_TrackingG2V", "MPC_EnergyMaxG2V"):
        with w7._target_config(evaluate_mpc, name, path):
            return evaluate_mpc.run_single("tracking" if arm == "MPC_TrackingG2V" else "energy_max", SEED, DAY, commit)
    if arm in ("Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced"):
        with w7._target_config(evaluate_oracle, name, path):
            return evaluate_oracle.run_single(SEED, DAY, commit, arm.split("_")[-1].lower())
    if arm == w7.FINAL_RL_NAME:
        with w7._target_config(evaluate_rl, name, path):
            return evaluate_rl.eval_td3(w7.FINAL_RL_NAME, w7.FINAL_RL_TRAIN_SEED, w7.FINAL_RL_PATH,
                                        w7.DEFAULT_REWARD_FN, SEED, DAY, commit)
    raise ValueError(arm)


ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "RoundRobin_TransformerCapped", "RandomPolicy",
        "MPC_TrackingG2V", "MPC_EnergyMaxG2V", "Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced",
        w7.FINAL_RL_NAME]


def td3_update_benchmark(n_updates=2000):
    """Seconds per TD3 gradient step with config_safe's network, batch and
    delays, on a filled buffer (the env is not involved)."""
    import gymnasium
    from stable_baselines3 import TD3
    from ev2gym_thesis.rl import config_safe as cfg

    class Dummy(gymnasium.Env):
        observation_space = gymnasium.spaces.Box(-10, 10, (40,), np.float32)
        action_space = gymnasium.spaces.Box(0, 1, (8,), np.float32)

        def reset(self, seed=None, options=None):
            return self.observation_space.sample(), {}

        def step(self, a):
            return self.observation_space.sample(), 0.0, False, False, {}

    m = TD3(cfg.POLICY, Dummy(), learning_rate=cfg.LEARNING_RATE, buffer_size=20_000, learning_starts=0,
            batch_size=cfg.BATCH_SIZE, tau=cfg.TAU, gamma=cfg.GAMMA, policy_delay=cfg.POLICY_DELAY,
            target_policy_noise=cfg.TARGET_POLICY_NOISE, target_noise_clip=cfg.TARGET_NOISE_CLIP,
            policy_kwargs={"net_arch": cfg.NET_ARCH}, device="cpu", seed=0)
    m.learn(5_000)  # fills the buffer (and trains 5,000 steps, discarded)
    t0 = time.perf_counter()
    m.train(gradient_steps=n_updates, batch_size=cfg.BATCH_SIZE)
    return (time.perf_counter() - t0) / n_updates


def main():
    w7.enable_process_hooks()
    commit = get_git_commit()
    rows = []
    for regime, (name, path) in REGIMES.items():
        model = dc_sessions.model_for_config(path)
        if model is not None:
            dc_sessions.enable(model)
        try:
            for arm in ARMS:
                t0 = time.perf_counter()
                row = run_arm(arm, name, path, commit)
                dt = time.perf_counter() - t0
                rows.append({"regime": regime, "arm": arm, "seconds": round(dt, 2),
                             "total_energy_charged": row["total_energy_charged"]})
                print(rows[-1], flush=True)
        finally:
            dc_sessions.disable()
    from scripts import dwell_ieee123_voltage as v123
    t0 = time.perf_counter()
    rec = v123.run_one(1.0, "ChargeAsFastAsPossible", SEED, DAY, commit)
    rows.append({"regime": "dc42_1.0x node_123 grid", "arm": "ChargeAsFastAsPossible",
                 "seconds": round(time.perf_counter() - t0, 2), "total_energy_charged": rec["total_energy_charged"]})
    print(rows[-1], flush=True)
    s = td3_update_benchmark()
    rows.append({"regime": "n/a", "arm": "TD3_safe gradient step (256x256, batch 256)", "seconds": round(s, 5),
                 "total_energy_charged": ""})
    print(rows[-1], flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    torch.set_num_threads(1)
    main()
