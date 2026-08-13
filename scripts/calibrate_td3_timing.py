"""
Week 3, Entregable 4: time-calibrate TD3 training on station_v0_bogota.

Runs a fixed CALIBRATION_TIMESTEPS-step training run (config_rl's real
hyperparameters, not a toy configuration) and reports wall-clock time, then
extrapolates linearly to candidate total-timestep budgets. This script does
NOT run the full Week 3 training -- it exists to produce the table
CLAUDE.md rule 2 requires before any long RL training run, and the results
below are meant to be pasted into a request for the user's explicit
go-ahead. Do not raise TOTAL_TIMESTEPS in ev2gym_thesis/rl/config_rl.py or
launch a longer run based on this script alone.

Usage:
    PYTHONPATH=. python scripts/calibrate_td3_timing.py
"""
import time

from stable_baselines3 import TD3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from ev2gym_thesis.rl import config_rl
from ev2gym_thesis.rl.env_factory import make_training_env
from ev2gym_thesis.eval_protocol import TRAIN_DAYS, TRAIN_SEEDS

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
EPISODE_LENGTH_STEPS = 96  # station_v0_bogota.yaml: simulation_length

# Candidate total-timestep budgets to present for confirmation. Chosen after
# seeing this run's measured steps/sec so the accompanying wall-clock
# estimates land at legible round numbers, not to hit a predetermined
# target.
CANDIDATE_BUDGETS = [15_000, 30_000, 60_000, 90_000]


def build_model(seed: int):
    train_env = make_training_env(REFERENCE_CONFIG_PATH, sample_mode="round_robin")
    venv = DummyVecEnv([lambda: train_env])
    venv = VecNormalize(
        venv,
        norm_obs=config_rl.VECNORMALIZE_NORM_OBS,
        norm_reward=config_rl.VECNORMALIZE_NORM_REWARD,
        clip_obs=config_rl.VECNORMALIZE_CLIP_OBS,
        gamma=config_rl.VECNORMALIZE_GAMMA,
    )
    n_actions = train_env.action_space.shape[0]
    model = TD3(
        config_rl.POLICY,
        venv,
        learning_rate=config_rl.LEARNING_RATE,
        buffer_size=config_rl.BUFFER_SIZE,
        learning_starts=config_rl.LEARNING_STARTS,
        batch_size=config_rl.BATCH_SIZE,
        tau=config_rl.TAU,
        gamma=config_rl.GAMMA,
        train_freq=config_rl.TRAIN_FREQ,
        gradient_steps=config_rl.GRADIENT_STEPS,
        policy_delay=config_rl.POLICY_DELAY,
        target_policy_noise=config_rl.TARGET_POLICY_NOISE,
        target_noise_clip=config_rl.TARGET_NOISE_CLIP,
        action_noise=config_rl.make_action_noise(n_actions),
        policy_kwargs=dict(net_arch=config_rl.NET_ARCH),
        seed=seed,
        verbose=0,
    )
    return model, train_env


if __name__ == "__main__":
    seed = TRAIN_SEEDS[0]
    print(f"Calibrating TD3 for {config_rl.CALIBRATION_TIMESTEPS} timesteps "
          f"(train_seed={seed}, real config_rl.py hyperparameters, "
          f"station_v0_bogota, round-robin day cycling over {len(TRAIN_DAYS)} TRAIN_DAYS)...")

    model, train_env = build_model(seed)

    t0 = time.perf_counter()
    model.learn(total_timesteps=config_rl.CALIBRATION_TIMESTEPS)
    elapsed_s = time.perf_counter() - t0

    steps_per_s = config_rl.CALIBRATION_TIMESTEPS / elapsed_s
    n_episodes_calibration = len(train_env.unwrapped.days_seen)  # make_training_env Monitor-wraps the env; days_seen lives on the underlying TrainingDayCyclingEnv

    print(f"\nCalibration run: {config_rl.CALIBRATION_TIMESTEPS} timesteps in "
          f"{elapsed_s:.1f}s ({elapsed_s/60:.2f} min) = {steps_per_s:.2f} steps/s")
    print(f"Episodes completed during calibration: {n_episodes_calibration} "
          f"(episode length {EPISODE_LENGTH_STEPS} steps)")
    print(f"TRAIN_DAYS pool size: {len(TRAIN_DAYS)}")

    print("\nLinear extrapolation to candidate total-timestep budgets "
          "(per training seed; this project uses 3 training seeds, see TRAIN_SEEDS):")
    print(f"{'timesteps':>10} | {'est. time':>12} | {'episodes':>9} | {'x per TRAIN_DAYS day':>21} | {'x3 seeds total time':>20}")
    for budget in CANDIDATE_BUDGETS:
        est_s = budget / steps_per_s
        n_episodes = budget / EPISODE_LENGTH_STEPS
        times_per_day = n_episodes / len(TRAIN_DAYS)
        total_3seeds_s = est_s * 3
        print(f"{budget:>10} | {est_s/60:>9.1f} min | {n_episodes:>9.1f} | "
              f"{times_per_day:>21.2f} | {total_3seeds_s/60:>17.1f} min")

    print("\nSTOP: per CLAUDE.md rule 2, do not launch a training run longer "
          "than this calibration without the user's explicit confirmation "
          "of the chosen total-timestep budget.")
