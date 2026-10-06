"""
Week 6, Part 0: extended training of the selected TD3 arm to convergence.

Same algorithm, hyperparameters, reward, state, config and training seeds as
the original 60,000-step run (scripts/train_td3.py::build_model is called
unchanged); only the budget and the monitoring differ -- see
ev2gym_thesis/rl/extended_training.py.

One training seed per process, so the three seeds run as independent
processes. Stops at convergence + CONFIRMATION_MARGIN_STEPS, or
DEADLINE_SAFETY_MARGIN_S before --deadline, or at --max-steps (calibration
and tests only), whichever comes first.

Usage:
    PYTHONPATH=. python scripts/train_td3_extended.py --seed 100 --deadline 2026-09-29T10:30:00-05:00
    PYTHONPATH=. python scripts/train_td3_extended.py --seed 100 --deadline ... --resume      # resume from latest replay-buffer save
    PYTHONPATH=. python scripts/train_td3_extended.py --seed 100 --deadline ... --max-steps 5000 --eval-freq 5000 --output-root <dir>   # timing calibration
"""
import argparse
import datetime
import glob
import json
import os
import pickle
import platform
import re
import sys
import time

import gymnasium
import numpy as np
import stable_baselines3
import torch
from stable_baselines3 import TD3
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ev2gym_thesis.eval_protocol import TRAIN_SEEDS, TRAIN_DAYS
from ev2gym_thesis.registry import get_git_commit
from ev2gym_thesis.rl import config_rl
from ev2gym_thesis.rl import extended_training as et
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.rl.env_factory import DEFAULT_STATE_FN
from scripts import train_td3

MODELS_DIR = "experiments/phase2_algorithms/models"
LOG_DIR = "experiments/phase2_algorithms/results/week6_part0"
UNBOUNDED_TIMESTEPS = 10_000_000  # learn() upper bound; the callback decides when to stop


def run_name(seed, reward_key):
    return f"{train_td3.ARM_NAMES[reward_key]}_extended_ts{seed}"


def make_seed_logging_venv(reward_fn, train_seed):
    env = Monitor(et.SeedLoggingTrainingEnv(config_path=train_td3.REFERENCE_CONFIG_PATH,
                                            reward_fn=reward_fn, sample_mode="round_robin",
                                            day_config_dir=et.day_config_dirs_for(train_seed)[0]))
    return env, DummyVecEnv([lambda: env])


# doc:begin build_extended_model
def build_model(seed, reward_fn):
    """scripts/train_td3.py::build_model's exact TD3/VecNormalize
    construction, with the Monitor-wrapped TrainingDayCyclingEnv swapped for
    SeedLoggingTrainingEnv (identical reset/step, plus scenario logging).
    The swap is done by monkeypatching train_td3.make_training_env for the
    duration of the call, so the hyperparameter wiring is not duplicated."""
    original = train_td3.make_training_env
    holder = {}

    def _factory(config_path, reward_fn=reward_fn, sample_mode="round_robin", **_):
        env, _venv = make_seed_logging_venv(reward_fn, seed)
        holder["env"] = env
        return env
    train_td3.make_training_env = _factory
    try:
        model, _, venv = train_td3.build_model(seed, save_dir=None, reward_fn=reward_fn)
    finally:
        train_td3.make_training_env = original
    return model, venv
# doc:end build_extended_model


# doc:begin resume
def latest_resume_point(model_dir):
    """Latest step S with a replay buffer, its auxiliary state, a model
    checkpoint and VecNormalize stats all present."""
    steps = []
    for p in glob.glob(os.path.join(model_dir, "replay_buffers", "replay_buffer_*_steps.pkl")):
        s = int(re.search(r"replay_buffer_(\d+)_steps\.pkl$", p).group(1))
        aux = os.path.join(model_dir, "replay_buffers", f"resume_aux_{s}_steps.pkl")
        ckpt = glob.glob(os.path.join(model_dir, "checkpoints", f"*_{s}_steps.zip"))
        if os.path.exists(aux) and ckpt and os.path.exists(ckpt[0].replace(".zip", "_vecnormalize.pkl")):
            steps.append((s, p, aux, ckpt[0]))
    if not steps:
        raise FileNotFoundError(f"No complete resume point (buffer + aux + checkpoint + vecnormalize) under {model_dir}")
    return max(steps)


def _truncate_csv(path, key, max_value):
    if not os.path.exists(path):
        return
    import pandas as pd
    df = pd.read_csv(path)
    df[df[key] <= max_value].to_csv(path, index=False)


def resume_model(model_dir, log_dir, name, reward_fn, train_seed):
    step, buf, aux_path, ckpt = latest_resume_point(model_dir)
    _, dummy = make_seed_logging_venv(reward_fn, train_seed)
    venv = VecNormalize.load(ckpt.replace(".zip", "_vecnormalize.pkl"), dummy)
    venv.training = True
    venv.norm_reward = config_rl.VECNORMALIZE_NORM_REWARD
    model = TD3.load(ckpt, env=venv)
    # TD3.load -> _setup_model -> set_random_seed(train_seed) queues the
    # training seed on the DummyVecEnv, so the first post-resume episode
    # would silently re-run scenario seed 100/101/102 and reseed the global
    # RNG restored below (caught by the resume smoke test). Clear the queue:
    # the next reset then draws from the restored generator, as an
    # uninterrupted run would.
    dummy._reset_seeds()
    model.load_replay_buffer(buf)
    with open(aux_path, "rb") as f:
        aux = pickle.load(f)
    train_env = venv.venv.envs[0].unwrapped
    train_env._rr_index = aux["rr_index"]
    np.random.set_state(aux["rng"]["np"])
    import random
    random.setstate(aux["rng"]["py"])
    torch.set_rng_state(aux["rng"]["torch"])
    with open(os.path.join(model_dir, "state.json")) as f:
        state = json.load(f)
    # Roll persistent state and CSV logs back to the resume point: anything
    # logged after `step` belongs to the interrupted segment, which is
    # re-trained, not spliced.
    state["evals"] = [e for e in state["evals"] if e["timesteps"] <= step]
    if state["conv_eval_index"] is not None and state["conv_eval_index"] >= len(state["evals"]):
        state["conv_eval_index"] = None
    _truncate_csv(os.path.join(log_dir, f"{name}_validation.csv"), "timesteps", step)
    _truncate_csv(os.path.join(log_dir, f"{name}_episodes.csv"), "timesteps_at_end", step)
    ep_csv = os.path.join(log_dir, f"{name}_episodes.csv")
    state["episode_index"] = sum(1 for _ in open(ep_csv)) - 1 if os.path.exists(ep_csv) else 0
    if state["evals"]:
        state["wall_clock_offset_s"] = state["evals"][-1]["wall_clock_s"]
    state["stop_reason"] = None
    state.setdefault("resumes", []).append({"from_step": step, "utc": datetime.datetime.utcnow().isoformat()})
    assert model.num_timesteps == step, (model.num_timesteps, step)
    return model, venv, state, step
# doc:end resume


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--reward", choices=list(train_td3.REWARD_FNS), default="vanilla")
    p.add_argument("--deadline", required=True, help="ISO-8601 with offset, e.g. 2026-09-29T10:30:00-05:00")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--max-steps", type=int, default=None, help="calibration/tests only")
    p.add_argument("--eval-freq", type=int, default=et.EVAL_FREQ_STEPS)
    p.add_argument("--buffer-freq", type=int, default=et.REPLAY_BUFFER_SAVE_FREQ_STEPS)
    p.add_argument("--torch-threads", type=int, default=None)
    p.add_argument("--output-root", default=None, help="override models/log roots (calibration/tests)")
    p.add_argument("--price-cache", action="store_true",
                   help="opt-in: reuse EV2Gym's parsed price table across env instances (ev2gym_thesis/rl/price_data_cache.py)")
    p.add_argument("--n-validation-cells", type=int, default=None, help="tests only: use the first N validation cells")
    a = p.parse_args(argv)

    # doc:begin keep_awake
    # Gate 1 finding: this machine's active power plan idles to sleep after
    # 300 s on AC ("Sleep after", powercfg STANDBYIDLE), and Windows counts
    # user input, not CPU load, toward that timer -- an unattended overnight
    # run would be suspended. ES_CONTINUOUS | ES_SYSTEM_REQUIRED asks Windows
    # not to idle-sleep while THIS process runs; it lapses automatically when
    # the process exits and leaves the user's power settings untouched. It
    # does not override an explicit sleep (lid close, power button).
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    # doc:end keep_awake
    if a.seed not in TRAIN_SEEDS:
        raise ValueError(f"seed {a.seed} not in TRAIN_SEEDS={TRAIN_SEEDS}")
    if a.torch_threads:
        torch.set_num_threads(a.torch_threads)
    if a.price_cache:
        price_data_cache.enable()
    deadline = datetime.datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:
        raise ValueError("--deadline must carry a UTC offset")
    reward_fn = train_td3.REWARD_FNS[a.reward]
    name = run_name(a.seed, a.reward)
    models_root = os.path.join(a.output_root, "models") if a.output_root else MODELS_DIR
    log_dir = os.path.join(a.output_root, "logs") if a.output_root else LOG_DIR
    model_dir = os.path.join(models_root, name)
    cells = et.VALIDATION_CELLS[:a.n_validation_cells] if a.n_validation_cells else None

    print(et.disjointness_proof(), flush=True)
    if a.resume:
        model, venv, state, step = resume_model(model_dir, log_dir, name, reward_fn, a.seed)
        print(f"[{name}] resumed at {step} steps", flush=True)
    else:
        if os.path.exists(os.path.join(model_dir, "state.json")):
            raise FileExistsError(f"{model_dir} already holds a run; use --resume or move it away")
        os.makedirs(model_dir, exist_ok=True)
        model, venv = build_model(a.seed, reward_fn)
        state = None

    cb = et.ExtendedTrainingCallback(
        run_name=name, model_dir=model_dir, log_dir=log_dir, reward_fn=reward_fn,
        deadline_epoch_s=deadline.timestamp(), eval_freq=a.eval_freq, buffer_freq=a.buffer_freq,
        max_steps=a.max_steps, cells=cells, state=state,
        validation_day_config_dir=et.day_config_dirs_for(a.seed)[1])

    manifest = {
        "run_name": name, "algorithm": "TD3", "train_seed": a.seed, "reward_arm": a.reward,
        "reward_function": reward_fn.__name__, "state_function": DEFAULT_STATE_FN.__name__,
        "config_path": train_td3.REFERENCE_CONFIG_PATH, "sample_mode": "round_robin",
        "train_days_pool_size": len(TRAIN_DAYS), "git_commit": get_git_commit(),
        "launched_utc": datetime.datetime.utcnow().isoformat(), "deadline": a.deadline,
        "stop_at_epoch_s": deadline.timestamp() - et.DEADLINE_SAFETY_MARGIN_S,
        "eval_freq": a.eval_freq, "buffer_freq": a.buffer_freq, "max_steps": a.max_steps,
        "n_validation_cells": len(cells) if cells else len(et.VALIDATION_CELLS),
        "selection_criterion": et.SELECTION_CRITERION,
        "convergence_rule": {"window": et.CONVERGENCE_WINDOW, "rel_mean_tol": et.CONVERGENCE_REL_MEAN_TOL,
                             "rel_std_tol": et.CONVERGENCE_REL_STD_TOL, "consecutive": et.CONVERGENCE_CONSECUTIVE,
                             "confirmation_steps": et.CONFIRMATION_MARGIN_STEPS},
        "torch_threads": torch.get_num_threads(), "price_cache": price_data_cache.is_enabled(), "pid": os.getpid(), "resumed": a.resume,
        "hyperparameters": {k: getattr(config_rl, k) for k in (
            "POLICY", "NET_ARCH", "LEARNING_RATE", "BUFFER_SIZE", "LEARNING_STARTS", "BATCH_SIZE", "TAU",
            "GAMMA", "TRAIN_FREQ", "GRADIENT_STEPS", "POLICY_DELAY", "TARGET_POLICY_NOISE",
            "TARGET_NOISE_CLIP", "ACTION_NOISE_SIGMA")},
        "library_versions": {"python": platform.python_version(), "torch": torch.__version__,
                             "stable_baselines3": stable_baselines3.__version__,
                             "gymnasium": gymnasium.__version__, "numpy": np.__version__},
        "platform": platform.platform(), "processor": platform.processor(),
    }
    with open(os.path.join(model_dir, f"manifest_launch_{int(time.time())}.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    t0 = time.perf_counter()
    model.learn(total_timesteps=UNBOUNDED_TIMESTEPS, callback=cb,
                reset_num_timesteps=not a.resume, log_interval=None)
    cb.finalize()
    print(f"[{name}] stopped: {cb.state['stop_reason']} at {model.num_timesteps} steps, "
          f"this segment {time.perf_counter() - t0:.1f}s, conv_eval_index={cb.state['conv_eval_index']}, "
          f"primary_step={cb.state['primary_step']}", flush=True)


if __name__ == "__main__":
    main()
