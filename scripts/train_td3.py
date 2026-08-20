"""
Week 3, Entregable 5: train TD3 vanilla on station_v0_bogota, once per
training seed in TRAIN_SEEDS. Never modifies ev2gym/rl_agent/*.py; only
uses ev2gym_thesis/rl/*. Extended Week 4: --reward {vanilla,tracking_only}
selects the arm -- one script, not a fork, same reasoning as
scripts/calibrate_td3_timing.py's flag. "pi" is deliberately NOT an option
here: both PI-TD3 reward designs were falsified before training (see
thesis_docs/chapters/04_oracle_and_pitd3.md S4.3) -- reward_pi.py stays in
the repo as evidence, not as a trainable arm.

All 3 training seeds are trained -- reporting only the best is explicitly
prohibited by the Week 3 brief (RL is notoriously seed-sensitive; this is
the standard failure mode for non-reproducible RL results in this
literature). Each seed's run is independent and produces its own artifact
directory, manifest, and learning curve.

Usage:
    PYTHONPATH=. python scripts/train_td3.py                            # train all TRAIN_SEEDS, vanilla
    PYTHONPATH=. python scripts/train_td3.py --reward tracking_only      # train all TRAIN_SEEDS, TD3_TrackingOnly
    PYTHONPATH=. python scripts/train_td3.py --seed 100                  # train a single seed
    PYTHONPATH=. python scripts/train_td3.py --seed 100 --resume experiments/phase2_algorithms/models/TD3_vanilla_ts100/checkpoints/td3_vanilla_ts100_30000_steps.zip
"""
import argparse
import datetime
import json
import os
import platform
import time

import gymnasium
import numpy as np
import stable_baselines3
import torch
from stable_baselines3 import TD3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from ev2gym.rl_agent.reward import SquaredTrackingErrorReward

from ev2gym_thesis.rl import config_rl
from ev2gym_thesis.rl.callbacks import make_callbacks
from ev2gym_thesis.rl.env_factory import make_training_env, DEFAULT_REWARD_FN, DEFAULT_STATE_FN
from ev2gym_thesis.rl.eval_utils import vecnormalize_path_for
from ev2gym_thesis.eval_protocol import TRAIN_SEEDS, TRAIN_DAYS
from ev2gym_thesis.registry import get_git_commit

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
MODELS_DIR = "experiments/phase2_algorithms/models"

# doc:begin reward_arms
REWARD_FNS = {"vanilla": DEFAULT_REWARD_FN, "tracking_only": SquaredTrackingErrorReward}
ARM_NAMES = {"vanilla": "TD3_vanilla", "tracking_only": "TD3_TrackingOnly"}
# doc:end reward_arms


def run_name(seed: int, reward_key: str = "vanilla") -> str:
    return f"{ARM_NAMES[reward_key]}_ts{seed}"


def build_model(seed: int, save_dir: str, reward_fn=DEFAULT_REWARD_FN):
    train_env = make_training_env(REFERENCE_CONFIG_PATH, reward_fn=reward_fn, sample_mode="round_robin")
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
        verbose=1,
        tensorboard_log=None,
    )
    return model, train_env, venv


def train_one_seed(seed: int, reward_key: str = "vanilla", resume_checkpoint: str = None):
    reward_fn = REWARD_FNS[reward_key]
    name = run_name(seed, reward_key)
    save_dir = os.path.join(MODELS_DIR, name)
    checkpoint_dir = os.path.join(save_dir, "checkpoints")
    os.makedirs(save_dir, exist_ok=True)

    if resume_checkpoint:
        print(f"[{name}] Resuming from {resume_checkpoint}")
        vecnorm_path = vecnormalize_path_for(resume_checkpoint)
        if not os.path.exists(vecnorm_path):
            raise FileNotFoundError(
                f"Cannot resume: VecNormalize stats not found at {vecnorm_path!r} "
                f"next to checkpoint {resume_checkpoint!r}."
            )
        train_env = make_training_env(REFERENCE_CONFIG_PATH, reward_fn=reward_fn, sample_mode="round_robin")
        venv = DummyVecEnv([lambda: train_env])
        venv = VecNormalize.load(vecnorm_path, venv)
        venv.training = True
        venv.norm_reward = config_rl.VECNORMALIZE_NORM_REWARD
        model = TD3.load(resume_checkpoint, env=venv)
        timesteps_done = model.num_timesteps
    else:
        model, train_env, venv = build_model(seed, save_dir, reward_fn=reward_fn)
        timesteps_done = 0

    remaining_timesteps = config_rl.TOTAL_TIMESTEPS - timesteps_done
    if remaining_timesteps <= 0:
        print(f"[{name}] Already at/past TOTAL_TIMESTEPS ({timesteps_done}/{config_rl.TOTAL_TIMESTEPS}), nothing to do.")
        return

    callbacks = make_callbacks(
        checkpoint_dir=checkpoint_dir,
        checkpoint_freq_steps=config_rl.CHECKPOINT_FREQ_STEPS,
        name_prefix=name.lower(),
        learning_curve_csv_path=os.path.join(save_dir, "learning_curve.csv"),
        learning_curve_log_freq_steps=config_rl.LEARNING_CURVE_LOG_FREQ_STEPS,
    )

    print(f"[{name}] Training for {remaining_timesteps} more timesteps "
          f"(target {config_rl.TOTAL_TIMESTEPS}, already done {timesteps_done})...")
    t0 = time.perf_counter()
    model.learn(total_timesteps=remaining_timesteps, callback=callbacks,
                reset_num_timesteps=(resume_checkpoint is None))
    wall_clock_s = time.perf_counter() - t0

    final_model_path = os.path.join(save_dir, "final_model.zip")
    final_vecnorm_path = vecnormalize_path_for(final_model_path)
    model.save(final_model_path)
    venv.save(final_vecnorm_path)

    # doc:begin manifest_reproducibility_artifact
    manifest = {
        "run_name": name,
        "algorithm": "TD3",
        "algorithm_family": "rl",
        "train_seed": seed,
        "git_commit": get_git_commit(),
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "config_path": REFERENCE_CONFIG_PATH,
        "reward_arm": reward_key,
        "reward_function": reward_fn.__name__,
        "state_function": DEFAULT_STATE_FN.__name__,
        "sample_mode": "round_robin",
        "train_days_pool_size": len(TRAIN_DAYS),
        "total_timesteps": config_rl.TOTAL_TIMESTEPS,
        "wall_clock_s": round(wall_clock_s, 2),
        "wall_clock_min": round(wall_clock_s / 60, 2),
        "resumed_from": resume_checkpoint,
        # doc:end manifest_reproducibility_artifact
        # (hyperparameters/vecnormalize/library_versions dicts continue
        # below in the real file, omitted from the hand-back excerpt --
        # full manifest also nests every TD3 hyperparameter from
        # config_rl.py, VecNormalize settings, and library versions
        # (torch/SB3/gymnasium/numpy).)
        "hyperparameters": {
            "policy": config_rl.POLICY,
            "net_arch": config_rl.NET_ARCH,
            "learning_rate": config_rl.LEARNING_RATE,
            "buffer_size": config_rl.BUFFER_SIZE,
            "learning_starts": config_rl.LEARNING_STARTS,
            "batch_size": config_rl.BATCH_SIZE,
            "tau": config_rl.TAU,
            "gamma": config_rl.GAMMA,
            "train_freq": config_rl.TRAIN_FREQ,
            "gradient_steps": config_rl.GRADIENT_STEPS,
            "policy_delay": config_rl.POLICY_DELAY,
            "target_policy_noise": config_rl.TARGET_POLICY_NOISE,
            "target_noise_clip": config_rl.TARGET_NOISE_CLIP,
            "action_noise_sigma": config_rl.ACTION_NOISE_SIGMA,
        },
        "vecnormalize": {
            "norm_obs": config_rl.VECNORMALIZE_NORM_OBS,
            "norm_reward": config_rl.VECNORMALIZE_NORM_REWARD,
            "clip_obs": config_rl.VECNORMALIZE_CLIP_OBS,
            "gamma": config_rl.VECNORMALIZE_GAMMA,
        },
        "library_versions": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stable_baselines3": stable_baselines3.__version__,
            "gymnasium": gymnasium.__version__,
            "numpy": np.__version__,
        },
    }
    manifest_path = os.path.join(save_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[{name}] Done. wall_clock={wall_clock_s:.1f}s ({wall_clock_s/60:.2f} min). "
          f"Saved: {final_model_path}, {final_vecnorm_path}, {manifest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=None,
                         help="Train only this training seed (must be in TRAIN_SEEDS). Default: train all TRAIN_SEEDS sequentially.")
    parser.add_argument("--reward", choices=list(REWARD_FNS.keys()), default="vanilla",
                         help="Which arm to train (default: vanilla, Week 3's arm).")
    parser.add_argument("--resume", type=str, default=None,
                         help="Path to a checkpoint .zip to resume from (requires --seed).")
    args = parser.parse_args()

    if args.resume and args.seed is None:
        parser.error("--resume requires --seed")

    seeds = [args.seed] if args.seed is not None else list(TRAIN_SEEDS)
    for s in seeds:
        if s not in TRAIN_SEEDS:
            raise ValueError(f"seed {s} is not in TRAIN_SEEDS={TRAIN_SEEDS}")

    for seed in seeds:
        train_one_seed(seed, reward_key=args.reward, resume_checkpoint=args.resume if seed == args.seed else None)

    print(f"\nAll requested training seeds complete (arm={ARM_NAMES[args.reward]}).")
