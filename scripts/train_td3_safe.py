"""
Week 8: train the redesigned, projected TD3 agent ("TD3_safe").

What differs from the Weeks 3-6 agents (ev2gym_thesis/rl/config_safe.py has
the full justification):
  - the transformer limit is a hard constraint (ev2gym_thesis/rl/safety.py),
    applied in training, validation and evaluation alike;
  - the reward is ServedEnergyReward (return = energy delivered, so it
    minimises demand not served), or CappedTrackingReward with --reward tracking;
  - the state is ServiceState (adds each EV's state of charge);
  - the hyperparameters are the TD3 reference implementation's;
  - the regime is explicit: --regime dc42 (42-minute DC sessions, default) or
    long (EV2Gym's native sessions).

Reused unchanged: the validation set, convergence rule, checkpoint selection,
leakage guard, checkpoint/replay-buffer/state persistence and keep-awake of
the Week 6 extended run (ev2gym_thesis/rl/extended_training.py), and the
price-data cache. One training seed per process. Stops at convergence +
100,000 steps, before --deadline, or at --max-steps, whichever comes first.

CLAUDE.md rule 2: a real training run needs the user's explicit agreement on
the wall-clock budget first. --max-steps with a small value is for
calibration and smoke tests only.

Usage:
  PYTHONPATH=. python scripts/train_td3_safe.py --seed 100 --deadline 2026-10-26T08:00:00-05:00 --price-cache --torch-threads 1
  PYTHONPATH=. python scripts/train_td3_safe.py --seed 100 --deadline ... --resume
  PYTHONPATH=. python scripts/train_td3_safe.py --seed 100 --deadline ... --max-steps 5000 --eval-freq 5000 --output-root %TEMP%/ev8t   # calibration
"""
import argparse
import datetime
import json
import os
import pickle
import platform
import random
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

from ev2gym_thesis.demand import dc_sessions, station_arrivals
from ev2gym_thesis.eval_protocol import TRAIN_SEEDS, TRAIN_DAYS
from ev2gym_thesis.registry import get_git_commit
from ev2gym_thesis.rl import config_safe as cfg
from ev2gym_thesis.rl import extended_training as et
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.rl.safe_training import SafeTrainingEnv
from ev2gym_thesis.rl.safety import safe_step

MODELS_DIR = "experiments/phase2_algorithms/models"
LOG_DIR = "experiments/phase2_algorithms/results/week8_safe_rl"
UNBOUNDED_TIMESTEPS = 10_000_000  # learn() upper bound; the callback decides when to stop


def run_name(regime, reward, seed):
    return f"{cfg.arm_name(regime, reward)}_ts{seed}"


def enable_regime(regime):
    """Install the regime's demand model process-wide, before any EV2Gym is
    built (training env, its probe, validation envs). Week 8 review: dc42 is
    the station-level arrival generator at 1.0x (config_safe.enable_regime)."""
    return cfg.enable_regime(regime)


# doc:begin validation_step_fn
def validation_step_fn(env, action):
    """safe_step plus, on the terminal step, the Week 8 review extras in the
    stats dict: the three post-hoc terms of the retired reward and the A1
    service metrics (config_safe.VALIDATION_EXTRA_METRICS). Read-only: the
    recorder only observes the step."""
    from ev2gym_thesis.demand import station_arrivals
    from ev2gym_thesis.metrics import service
    if getattr(env, "_rec", None) is None or env.current_step == 0:
        env._rec = {"seed": env.seed, "sim_date": str(env.sim_date), "timescale": env.timescale,
                    "steps": [], "evs": []}
    out = list(safe_step(env, action))
    service._post_step(env)
    terminated, truncated, stats = out[2], out[3], out[4]
    if terminated or truncated:
        rec = env._rec
        tot = service.episode_totals(rec)
        stats = dict(stats)
        stats.update({"old_r_tracking": tot["r_tracking"], "old_r_overload": tot["r_overload"],
                      "old_r_user": tot["r_user"]})
        if getattr(env, "_sa", None) is not None:
            dem = station_arrivals.episode_demand(env, float(stats["total_energy_charged"]))
            summ = service.service_summary([e["f"] for e in rec["evs"] + rec.get("connected_at_end", [])],
                                           dem["arrivals_rejected"])
            stats.update({"dns_exact": dem["dns_exact"], "mean_f_all": summ["mean_f_all"],
                          "service_level_all": summ["service_level_all"],
                          "arrivals_rejected": dem["arrivals_rejected"]})
        out[4] = stats
    return tuple(out)
# doc:end validation_step_fn


def make_venv(config_path, reward_fn, train_seed):
    env = Monitor(SafeTrainingEnv(config_path=config_path, reward_fn=reward_fn, state_fn=cfg.STATE_FN,
                                  sample_mode="round_robin",
                                  day_config_dir=et.day_config_dirs_for(train_seed)[0] + "_safe"))
    return DummyVecEnv([lambda: env])


# doc:begin build_safe_model
def build_model(config_path, reward_fn, seed):
    venv = VecNormalize(make_venv(config_path, reward_fn, seed), norm_obs=cfg.VECNORMALIZE_NORM_OBS,
                        norm_reward=cfg.VECNORMALIZE_NORM_REWARD, clip_obs=cfg.VECNORMALIZE_CLIP_OBS,
                        gamma=cfg.VECNORMALIZE_GAMMA)
    model = TD3(cfg.POLICY, venv, learning_rate=cfg.LEARNING_RATE, buffer_size=cfg.BUFFER_SIZE,
                learning_starts=cfg.LEARNING_STARTS, batch_size=cfg.BATCH_SIZE, tau=cfg.TAU, gamma=cfg.GAMMA,
                train_freq=cfg.TRAIN_FREQ, gradient_steps=cfg.GRADIENT_STEPS, policy_delay=cfg.POLICY_DELAY,
                target_policy_noise=cfg.TARGET_POLICY_NOISE, target_noise_clip=cfg.TARGET_NOISE_CLIP,
                action_noise=cfg.make_action_noise(venv.action_space.shape[0]),
                policy_kwargs=dict(net_arch=cfg.NET_ARCH), seed=seed, verbose=0, device="cpu")
    return model, venv
# doc:end build_safe_model


def resume_model(model_dir, log_dir, name, config_path, reward_fn, train_seed):
    """The Week 6 resume procedure (scripts/train_td3_extended.py::resume_model)
    on this run's environment: latest complete resume point, frozen-free
    VecNormalize, replay buffer, RNG states and round-robin day index."""
    from scripts.train_td3_extended import latest_resume_point, _truncate_csv
    step, buf, aux_path, ckpt = latest_resume_point(model_dir)
    dummy = make_venv(config_path, reward_fn, train_seed)
    venv = VecNormalize.load(ckpt.replace(".zip", "_vecnormalize.pkl"), dummy)
    venv.training = True
    venv.norm_reward = cfg.VECNORMALIZE_NORM_REWARD
    model = TD3.load(ckpt, env=venv, device="cpu")
    dummy._reset_seeds()  # see train_td3_extended.resume_model: TD3.load re-queues the training seed
    model.load_replay_buffer(buf)
    with open(aux_path, "rb") as f:
        aux = pickle.load(f)
    venv.venv.envs[0].unwrapped._rr_index = aux["rr_index"]
    np.random.set_state(aux["rng"]["np"])
    random.setstate(aux["rng"]["py"])
    torch.set_rng_state(aux["rng"]["torch"])
    with open(os.path.join(model_dir, "state.json")) as f:
        state = json.load(f)
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


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--regime", choices=list(cfg.REGIME_CONFIGS), default=cfg.DEFAULT_REGIME)
    p.add_argument("--reward", choices=list(cfg.REWARD_FNS), default=cfg.DEFAULT_REWARD)
    p.add_argument("--deadline", required=True, help="ISO-8601 with offset, e.g. 2026-10-26T08:00:00-05:00")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--max-steps", type=int, default=None,
                   help="calibration/tests; with --fixed-budget, the fixed training budget")
    p.add_argument("--fixed-budget", action="store_true",
                   help="Week 8 long-budget sensitivity (config_safe doc long_budget_sensitivity): no convergence "
                        "stop, train to --max-steps (required); the carried model is unaffected")
    p.add_argument("--eval-freq", type=int, default=et.EVAL_FREQ_STEPS)
    p.add_argument("--buffer-freq", type=int, default=et.REPLAY_BUFFER_SAVE_FREQ_STEPS)
    p.add_argument("--torch-threads", type=int, default=None)
    p.add_argument("--output-root", default=None, help="override models/log roots (calibration/tests)")
    p.add_argument("--price-cache", action="store_true")
    p.add_argument("--state", choices=list(cfg.STATE_FNS), default=None,
                   help="Week 8 review: observation function (default config_safe.STATE_FN)")
    p.add_argument("--n-validation-cells", type=int, default=None, help="tests only: use the first N validation cells")
    a = p.parse_args(argv)

    if sys.platform == "win32":  # keep-awake for this process only (train_td3_extended.py, Gate 1 finding)
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    if a.seed not in TRAIN_SEEDS:
        raise ValueError(f"seed {a.seed} not in TRAIN_SEEDS={TRAIN_SEEDS}")
    if a.torch_threads:
        torch.set_num_threads(a.torch_threads)
    if a.price_cache:
        price_data_cache.enable()
    deadline = datetime.datetime.fromisoformat(a.deadline)
    if deadline.tzinfo is None:
        raise ValueError("--deadline must carry a UTC offset")

    if a.fixed_budget and not a.max_steps:
        raise ValueError("--fixed-budget needs --max-steps")
    if a.state:
        cfg.STATE_FN = cfg.STATE_FNS[a.state]
    config_path = enable_regime(a.regime)
    reward_fn = cfg.REWARD_FNS[a.reward]
    criterion, lower_is_better = cfg.SELECTION[a.reward]
    name = run_name(a.regime, a.reward, a.seed)
    models_root = os.path.join(a.output_root, "models") if a.output_root else MODELS_DIR
    log_dir = os.path.join(a.output_root, "logs") if a.output_root else LOG_DIR
    model_dir = os.path.join(models_root, name)
    cells = et.VALIDATION_CELLS[:a.n_validation_cells] if a.n_validation_cells else None

    print(et.disjointness_proof(), flush=True)
    if a.resume:
        model, venv, state, step = resume_model(model_dir, log_dir, name, config_path, reward_fn, a.seed)
        print(f"[{name}] resumed at {step} steps", flush=True)
    else:
        if os.path.exists(os.path.join(model_dir, "state.json")):
            raise FileExistsError(f"{model_dir} already holds a run; use --resume or move it away")
        os.makedirs(model_dir, exist_ok=True)
        model, venv = build_model(config_path, reward_fn, a.seed)
        state = None

    cb = et.ExtendedTrainingCallback(
        run_name=name, model_dir=model_dir, log_dir=log_dir, reward_fn=reward_fn,
        deadline_epoch_s=deadline.timestamp(), eval_freq=a.eval_freq, buffer_freq=a.buffer_freq,
        max_steps=a.max_steps, cells=cells, state=state,
        confirmation_steps=float("inf") if a.fixed_budget else et.CONFIRMATION_MARGIN_STEPS,
        validation_day_config_dir=et.day_config_dirs_for(a.seed)[1] + "_safe",
        criterion=criterion, lower_is_better=lower_is_better,
        log_metrics=cfg.VALIDATION_LOG_METRICS + (cfg.VALIDATION_EXTRA_METRICS if a.regime == "dc42" else []),
        validation_kwargs={"config_path": config_path, "state_fn": cfg.STATE_FN, "step_fn": validation_step_fn})

    manifest = {
        "run_name": name, "algorithm": "TD3", "design": "safe (hard transformer constraint)",
        "train_seed": a.seed, "regime": a.regime, "config_path": config_path,
        "session_model": (lambda m: None if m is None else {"mean_min": m.mean_min, "cv": m.cv})(
            dc_sessions.model_for_config(config_path)),
        "arrival_model": (lambda sp: "ev2gym_spawner" if sp is None else {
            "model": station_arrivals.ARRIVAL_MODEL, "arrivals_per_day": sp.arrivals_per_day,
            "dwell_mean_min": sp.dwell.mean_min, "dwell_cv": sp.dwell.cv, "level": sp.level,
            "extra_connected_steps": sp.extra_connected_steps, "dead_time_steps": sp.dead_time_steps})(
            station_arrivals.spec_for_config(config_path)),
        "selection_rule": cfg.SELECTION_RULE_VERSION, "carried_model_rule": cfg.CARRIED_MODEL_RULE,
        "reward_function": reward_fn.__name__, "state_function": cfg.STATE_FN.__name__,
        "safety_layer": "ev2gym_thesis/rl/safety.py::project_actions (budget 0.999 x rating)",
        "sample_mode": "round_robin", "train_days_pool_size": len(TRAIN_DAYS), "git_commit": get_git_commit(),
        "launched_utc": datetime.datetime.utcnow().isoformat(), "deadline": a.deadline,
        "stop_at_epoch_s": deadline.timestamp() - et.DEADLINE_SAFETY_MARGIN_S,
        "eval_freq": a.eval_freq, "buffer_freq": a.buffer_freq, "max_steps": a.max_steps,
        "fixed_budget": a.fixed_budget,
        "long_budget_rule": cfg.LONG_BUDGET_RULE if a.fixed_budget else None,
        "n_validation_cells": len(cells) if cells else len(et.VALIDATION_CELLS),
        "selection_criterion": criterion, "selection_lower_is_better": lower_is_better,
        "convergence_rule": {"window": et.CONVERGENCE_WINDOW, "rel_mean_tol": et.CONVERGENCE_REL_MEAN_TOL,
                             "rel_std_tol": et.CONVERGENCE_REL_STD_TOL, "consecutive": et.CONVERGENCE_CONSECUTIVE,
                             "confirmation_steps": et.CONFIRMATION_MARGIN_STEPS},
        "torch_threads": torch.get_num_threads(), "price_cache": price_data_cache.is_enabled(),
        "pid": os.getpid(), "resumed": a.resume, "hyperparameters": cfg.hyperparameters_dict(),
        "library_versions": {"python": platform.python_version(), "torch": torch.__version__,
                             "stable_baselines3": stable_baselines3.__version__,
                             "gymnasium": gymnasium.__version__, "numpy": np.__version__},
        "platform": platform.platform(), "processor": platform.processor(),
    }
    with open(os.path.join(model_dir, f"manifest_launch_{int(time.time())}.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    t0 = time.perf_counter()
    model.learn(total_timesteps=UNBOUNDED_TIMESTEPS, callback=cb, reset_num_timesteps=not a.resume,
                log_interval=None)
    cb.finalize()
    # Week 8 review C3 selection rule (config_safe, doc safe_selection_rule): best at/after
    # convergence, else best over the whole run (non-convergence reported as a result).
    fi = cfg.final_index(cb.criterion_series(), cb.state["conv_eval_index"], lower_is_better)
    cb.state.update({"final_eval_index": fi, "final_step": cb.state["evals"][fi]["timesteps"],
                     "final_checkpoint": cb.state["evals"][fi]["checkpoint_path"],
                     "final_rule": cfg.SELECTION_RULE_VERSION,
                     "converged": cb.state["conv_eval_index"] is not None})
    cb.save_state()
    print(f"[{name}] stopped: {cb.state['stop_reason']} at {model.num_timesteps} steps, "
          f"this segment {time.perf_counter() - t0:.1f}s, conv_eval_index={cb.state['conv_eval_index']}, "
          f"primary_step={cb.state['primary_step']}, final_step={cb.state['final_step']}", flush=True)


if __name__ == "__main__":
    main()
