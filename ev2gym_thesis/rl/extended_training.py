"""
Week 6, Part 0: extended training of the selected RL policy to convergence.

This module holds everything the extended run needs beyond Week 3's
training stack (ev2gym_thesis/rl/config_rl.py, env_factory.py), which it
imports unchanged -- the only things that change relative to the original
60,000-step runs are the training budget and the monitoring:

- VALIDATION_SEEDS / VALIDATION_DAYS: a fixed 20-cell validation set,
  disjoint from EVAL_DAYS/SEEDS (the final evaluation grid) and from every
  scenario seed a training episode can draw (see disjointness_proof()).
- convergence_index(): the pre-registered convergence rule, as a pure
  function so it can be unit-tested on synthetic curves.
- SeedLoggingTrainingEnv: TrainingDayCyclingEnv plus a record of which
  (day, scenario seed) each training episode actually ran on.
- ExtendedTrainingCallback: deterministic validation every EVAL_FREQ_STEPS,
  per-evaluation checkpoint, periodic replay-buffer save, per-episode
  training-reward log, convergence tracking and the stopping rule.

Never touches ev2gym/models/*.py or ev2gym/rl_agent/*.py.
"""
import csv
import datetime
import json
import os
import pickle
import random
import time

import gymnasium as gym
import numpy as np
import torch
from stable_baselines3.common.callbacks import BaseCallback

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS, TRAIN_DAYS, TRAIN_SEEDS, day_type
from ev2gym_thesis.rl.env_factory import TrainingDayCyclingEnv, make_env, reset_for_evaluation

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
VALIDATION_DAY_CONFIG_DIR = "experiments/phase2_algorithms/configs/_tmp_validation_day_configs"
TRAIN_DAY_CONFIG_DIR_EXTENDED = "experiments/phase2_algorithms/configs/_tmp_train_day_configs"


# doc:begin per_process_day_config_dirs
def day_config_dirs_for(train_seed: int) -> tuple:
    """(training, validation) per-day YAML directories for one training
    process. config_utils.make_day_config rewrites the same
    <dir>/<config>__<date>.yaml on every call without locking, so concurrent
    processes sharing a directory can read a file another process is
    half-way through writing -- this crashed one of three parallel seeds
    during Gate 1 calibration (yaml.load returned None). The files written
    are byte-identical whichever directory they land in; only the location
    is per-process."""
    return (f"{TRAIN_DAY_CONFIG_DIR_EXTENDED}_ts{train_seed}", f"{VALIDATION_DAY_CONFIG_DIR}_ts{train_seed}")
# doc:end per_process_day_config_dirs

# doc:begin train_scenario_seed_range
# Scenario seeds a training episode can run on. TrainingDayCyclingEnv.reset()
# is called by SB3 with seed=None after the first episode, and EV2Gym then
# draws `self.seed = np.random.randint(0, 1000000)` (ev2gym/models/
# ev2gym_env.py, reset(), line 247 at commit 23468f3) -- numpy's randint
# upper bound is exclusive, so every such draw lies in [0, 999_999]. The
# very first training episode is instead seeded explicitly by SB3 with the
# training seed itself (DummyVecEnv.seed(train_seed)), i.e. 100, 101 or 102.
TRAIN_SCENARIO_SEED_LOW = 0
TRAIN_SCENARIO_SEED_HIGH_EXCLUSIVE = 1_000_000
# doc:end train_scenario_seed_range

# doc:begin validation_set
# Labelled assumption (Week 6 Part 0, Gate 1): 10 validation seeds placed
# just above EV2Gym's unseeded-draw range, so no training episode can ever
# run on a validation scenario -- disjointness by construction, not by
# luck. All values are < 2**32, which np.random.seed() requires.
VALIDATION_SEEDS = list(range(1_000_000, 1_000_010))

# One weekday and one weekend date, disjoint from both EVAL_DAYS and
# TRAIN_DAYS. EV2Gym's EV population depends on (scenario seed, weekday vs.
# weekend) only (Week 5 Gate 3), and neither the reward
# (SqTrError_TrPenalty_UserIncentives) nor the state (PublicPST) reads the
# calendar date, so the specific date adds no information -- choosing dates
# outside both pools just makes the validation cells disjoint from the
# evaluation grid on both axes, not only on the seed axis.
VALIDATION_DAYS = [
    (2022, 1, 31),   # Monday (weekday)
    (2022, 3, 12),   # Saturday (weekend)
]
VALIDATION_CELLS = [(s, d) for s in VALIDATION_SEEDS for d in VALIDATION_DAYS]
# doc:end validation_set

# doc:begin extended_training_constants
EVAL_FREQ_STEPS = 10_000              # validation + checkpoint cadence (brief)
REPLAY_BUFFER_SAVE_FREQ_STEPS = 50_000  # replay-buffer save cadence (brief)
CONVERGENCE_WINDOW = 5                # W, in evaluations (= 50,000 steps)
CONVERGENCE_REL_MEAN_TOL = 0.02       # |mean(last W) - mean(prev W)| / |mean(prev W)| < 2%
CONVERGENCE_REL_STD_TOL = 0.05        # std(last W) / |mean(last W)| < 5%
CONVERGENCE_CONSECUTIVE = 3           # both conditions on 3 consecutive evaluations
CONFIRMATION_MARGIN_STEPS = 100_000   # keep training this long after convergence
DEADLINE_SAFETY_MARGIN_S = 15 * 60    # stop this long before the hard deadline, leaving time for final validation + saves

# Selection criterion -- CONFIRMED by the user at Gate 1 (2026-09-28): the
# validation-set mean tracking_error drives convergence and checkpoint
# selection; total_transformer_overload and energy_user_satisfaction are
# logged at every validation as secondary metrics and reported alongside.
# S5.8 names no trained winner (no RL arm beat Round Robin); TD3_vanilla is
# the best RL arm on S5.6's tracking-error ranking, not an overall winner.
SELECTION_CRITERION = "tracking_error"
SELECTION_CRITERION_LOWER_IS_BETTER = True

VALIDATION_LOG_METRICS = [
    "total_reward", "energy_user_satisfaction", "average_user_satisfaction",
    "total_transformer_overload", "tracking_error", "total_energy_charged",
]
# doc:end extended_training_constants


# ---------------------------------------------------------------------------
# Disjointness proof
# ---------------------------------------------------------------------------
# doc:begin disjointness_proof
def disjointness_proof() -> dict:
    """Checks, and returns as a printable dict, that the validation set is
    disjoint from (a) the final evaluation grid and (b) every scenario seed a
    training episode can run on. Raises AssertionError if any check fails."""
    val_seeds, eval_seeds = set(VALIDATION_SEEDS), set(SEEDS)
    first_episode_seeds = set(TRAIN_SEEDS)
    checks = {
        "validation_seeds": f"{min(val_seeds)}..{max(val_seeds)} (n={len(val_seeds)})",
        "eval_seeds (SEEDS)": f"{min(eval_seeds)}..{max(eval_seeds)} (n={len(eval_seeds)})",
        "training draw range": f"[{TRAIN_SCENARIO_SEED_LOW}, {TRAIN_SCENARIO_SEED_HIGH_EXCLUSIVE}) plus first-episode seeds {sorted(first_episode_seeds)}",
        "validation intersect eval seeds": sorted(val_seeds & eval_seeds),
        "validation intersect TRAIN_SEEDS": sorted(val_seeds & first_episode_seeds),
        "min(validation) >= training draw upper bound": min(val_seeds) >= TRAIN_SCENARIO_SEED_HIGH_EXCLUSIVE,
        "max(validation) < 2**32": max(val_seeds) < 2 ** 32,
        "validation days intersect EVAL_DAYS": sorted(set(VALIDATION_DAYS) & set(EVAL_DAYS)),
        "validation days intersect TRAIN_DAYS": sorted(set(VALIDATION_DAYS) & set(TRAIN_DAYS)),
        "validation day types": sorted(day_type(d) for d in VALIDATION_DAYS),
        "n validation cells": len(VALIDATION_CELLS),
    }
    assert checks["validation intersect eval seeds"] == []
    assert checks["validation intersect TRAIN_SEEDS"] == []
    assert checks["min(validation) >= training draw upper bound"]
    assert checks["max(validation) < 2**32"]
    assert checks["validation days intersect EVAL_DAYS"] == []
    assert checks["validation days intersect TRAIN_DAYS"] == []
    assert checks["validation day types"] == ["weekday", "weekend"]
    assert checks["n validation cells"] == 20
    return checks
# doc:end disjointness_proof


# ---------------------------------------------------------------------------
# Convergence rule
# ---------------------------------------------------------------------------
# doc:begin convergence_rule
def convergence_conditions_at(m, k, window=CONVERGENCE_WINDOW,
                              rel_mean_tol=CONVERGENCE_REL_MEAN_TOL,
                              rel_std_tol=CONVERGENCE_REL_STD_TOL) -> bool:
    """True iff both window conditions hold at evaluation index k (0-based),
    using m[k-W+1 .. k] as "last W" and m[k-2W+1 .. k-W] as "previous W".
    False if fewer than 2W evaluations are available up to k.
    std is the sample standard deviation (ddof=1)."""
    m = np.asarray(m, dtype=float)
    if k < 2 * window - 1 or k >= len(m):
        return False
    last = m[k - window + 1:k + 1]
    prev = m[k - 2 * window + 1:k - window + 1]
    mean_last, mean_prev = last.mean(), prev.mean()
    if mean_prev == 0 or mean_last == 0:
        raise ValueError("Relative convergence thresholds are undefined for a zero-mean window; "
                         "the selection criterion must be bounded away from zero.")
    cond_mean = abs(mean_last - mean_prev) / abs(mean_prev) < rel_mean_tol
    cond_std = last.std(ddof=1) / abs(mean_last) < rel_std_tol
    return bool(cond_mean and cond_std)


def convergence_index(m, window=CONVERGENCE_WINDOW, rel_mean_tol=CONVERGENCE_REL_MEAN_TOL,
                      rel_std_tol=CONVERGENCE_REL_STD_TOL, consecutive=CONVERGENCE_CONSECUTIVE):
    """Index (0-based) of the evaluation at which convergence is DECLARED --
    the last of the first run of `consecutive` evaluations on which both
    window conditions hold -- or None if the rule is never satisfied. The
    earliest possible declaration is index 2W - 1 + consecutive - 1 (=11
    with the defaults, i.e. the 12th evaluation, 120,000 steps)."""
    run = 0
    for k in range(len(m)):
        if convergence_conditions_at(m, k, window, rel_mean_tol, rel_std_tol):
            run += 1
            if run >= consecutive:
                return k
        else:
            run = 0
    return None
# doc:end convergence_rule


# doc:begin checkpoint_selection
def select_primary_index(m, conv_idx, lower_is_better=SELECTION_CRITERION_LOWER_IS_BETTER):
    """Primary checkpoint rule: the evaluation with the best criterion value
    among those at or after the convergence declaration. None if the seed
    never converged (the brief leaves that case to the user)."""
    if conv_idx is None:
        return None
    window = np.asarray(m[conv_idx:], dtype=float)
    best = int(np.argmin(window) if lower_is_better else np.argmax(window))
    return conv_idx + best
# doc:end checkpoint_selection


# ---------------------------------------------------------------------------
# Training env that records the scenario each episode ran on
# ---------------------------------------------------------------------------
# doc:begin seed_logging_env
class SeedLoggingTrainingEnv(TrainingDayCyclingEnv):
    """TrainingDayCyclingEnv with identical reset/step behaviour, plus the
    realised (day, scenario seed) of the current episode attached to the
    terminal step's info dict -- read on the terminal step because SB3's
    DummyVecEnv auto-resets inside that same step() call, after which the
    wrapped env already holds the NEXT episode."""

    # doc:begin eval_seed_guard
    # Leakage guard (user-approved at Gate 1, implemented here, NOT in
    # ev2gym/): an unseeded training draw lands in [0, 999_999] and can hit
    # an evaluation scenario seed (SEEDS = 0..49) with probability 5e-5 per
    # episode -- ~4 expected hits over a multi-million-step run. If the
    # realised seed is an evaluation seed, the episode's env is rebuilt for
    # the SAME day with seed=None, which continues EV2Gym's own draw chain
    # from the (already reseeded) global generator; the rejected seed is
    # recorded. Effect on the training distribution: 50 of 10^6 seed values
    # excluded. Validation seeds need no guard (>= 10^6, unreachable).
    forbidden_scenario_seeds = frozenset(SEEDS)

    def reset(self, seed=None, options=None):
        out = super().reset(seed=seed, options=options)
        self.current_day = self.days_seen[-1]
        self.current_rejected_seeds = []
        while int(self._env.seed) in self.forbidden_scenario_seeds:
            self.current_rejected_seeds.append(int(self._env.seed))
            self._env = self._build_env_for_day(self.current_day, seed=None)
            out = self._env.reset(seed=None)
        self.current_scenario_seed = int(self._env.seed)
        return out
    # doc:end eval_seed_guard

    def step(self, action):
        obs, reward, terminated, truncated, info = self._env.step(action)
        if terminated or truncated:
            info = dict(info)
            info["train_day"] = "%04d-%02d-%02d" % self.current_day
            info["train_scenario_seed"] = self.current_scenario_seed
            info["rejected_eval_seed_draws"] = ";".join(map(str, self.current_rejected_seeds))
        return obs, reward, terminated, truncated, info
# doc:end seed_logging_env


# ---------------------------------------------------------------------------
# Deterministic validation
# ---------------------------------------------------------------------------
def _rng_snapshot():
    return {"np": np.random.get_state(), "py": random.getstate(), "torch": torch.get_rng_state()}


def _rng_restore(snap):
    np.random.set_state(snap["np"])
    random.setstate(snap["py"])
    torch.set_rng_state(snap["torch"])


# doc:begin load_frozen_checkpoint
def load_frozen_checkpoint(ckpt_path, spaces_venv):
    """Load a saved checkpoint and its sidecar VecNormalize statistics for
    validation, FROZEN: training=False (running mean/var never updated) and
    norm_reward=False -- the same settings eval_utils.load_trained_agent
    enforces for the Week 5 evaluation path. Validation therefore scores the
    exact artifact written to disk and never touches the training
    normaliser. `spaces_venv` is any DummyVecEnv with the right spaces
    (VecNormalize.load needs one to attach to; it is never stepped)."""
    from stable_baselines3 import TD3
    from stable_baselines3.common.vec_env import VecNormalize
    from ev2gym_thesis.rl.eval_utils import vecnormalize_path_for
    vn_path = vecnormalize_path_for(ckpt_path)
    if not os.path.exists(vn_path):
        raise FileNotFoundError(f"VecNormalize stats missing next to {ckpt_path!r}: {vn_path!r}")
    vn = VecNormalize.load(vn_path, spaces_venv)
    vn.training = False
    vn.norm_reward = False
    return TD3.load(ckpt_path, device="cpu"), vn
# doc:end load_frozen_checkpoint


# doc:begin run_validation
def run_validation(model, venv, reward_fn, cells=None, day_config_dir=VALIDATION_DAY_CONFIG_DIR) -> dict:
    """Deterministic (no exploration noise) evaluation of a policy on the
    fixed validation cells. In training, `model`/`venv` come from
    load_frozen_checkpoint() on the checkpoint just saved (frozen
    VecNormalize); normalize_obs() only reads the statistics.

    Uses the Week 5 evaluation path's own pieces -- env_factory.make_env and
    reset_for_evaluation, and the same deterministic predict call as
    scripts/evaluate_rl.py's _TD3Stepper -- not a separate reimplementation
    of the environment or the episode loop.

    EV2Gym calls np.random.seed()/random.seed() on construction and reset,
    i.e. it reseeds the GLOBAL generators that also drive the training
    scenario chain, the exploration noise and replay-buffer sampling. All
    three generator states are snapshotted before and restored after, so
    running the monitor does not change the training trajectory.
    """
    cells = VALIDATION_CELLS if cells is None else cells
    snap = _rng_snapshot()
    per_cell = []
    try:
        for scenario_seed, day in cells:
            env = make_env(REFERENCE_CONFIG_PATH, day, scenario_seed, reward_fn=reward_fn,
                           day_config_dir=day_config_dir)
            obs, _ = reset_for_evaluation(env, scenario_seed)
            done, stats = False, None
            while not done:
                action, _ = model.predict(venv.normalize_obs(obs), deterministic=True)
                obs, _, terminated, truncated, stats = env.step(action)
                done = terminated or truncated
            per_cell.append({k: float(stats[k]) for k in VALIDATION_LOG_METRICS})
    finally:
        _rng_restore(snap)
    return {k: float(np.mean([c[k] for c in per_cell])) for k in VALIDATION_LOG_METRICS} | {"n_cells": len(per_cell)}
# doc:end run_validation


# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------
VALIDATION_CSV_FIELDS = (["eval_index", "timesteps", "wall_clock_s", "validation_wall_clock_s",
                          "criterion_name", "criterion_value"] + VALIDATION_LOG_METRICS
                         + ["n_cells", "train_steps_per_s_since_last_eval", "conditions_hold", "converged",
                            "checkpoint_path"])
EPISODE_CSV_FIELDS = ["episode_index", "timesteps_at_end", "wall_clock_s", "train_day",
                      "train_scenario_seed", "scenario_seed_in_eval_seeds", "rejected_eval_seed_draws",
                      "episode_reward_raw", "episode_length"]
BUFFERS_KEPT = 2  # user decision at Gate 1: keep the last 2 replay buffers per seed


class ExtendedTrainingCallback(BaseCallback):
    """See module docstring. All paths and cadences are constructor
    arguments so the test suite can drive a tiny run; production values are
    the module constants above."""

    def __init__(self, run_name, model_dir, log_dir, reward_fn, deadline_epoch_s,
                 eval_freq=EVAL_FREQ_STEPS, buffer_freq=REPLAY_BUFFER_SAVE_FREQ_STEPS,
                 confirmation_steps=CONFIRMATION_MARGIN_STEPS, safety_margin_s=DEADLINE_SAFETY_MARGIN_S,
                 max_steps=None, cells=None, state=None, validation_day_config_dir=VALIDATION_DAY_CONFIG_DIR,
                 verbose=1):
        super().__init__(verbose)
        self.run_name = run_name
        self.model_dir = model_dir
        self.ckpt_dir = os.path.join(model_dir, "checkpoints")
        self.buffer_dir = os.path.join(model_dir, "replay_buffers")
        self.val_csv = os.path.join(log_dir, f"{run_name}_validation.csv")
        self.ep_csv = os.path.join(log_dir, f"{run_name}_episodes.csv")
        self.reward_fn = reward_fn
        self.deadline_epoch_s = deadline_epoch_s
        self.eval_freq = eval_freq
        self.buffer_freq = buffer_freq
        self.confirmation_steps = confirmation_steps
        self.safety_margin_s = safety_margin_s
        self.max_steps = max_steps
        self.cells = cells
        self.validation_day_config_dir = validation_day_config_dir
        # Persistent state (restored on resume).
        self.state = state or {"evals": [], "episode_index": 0, "wall_clock_offset_s": 0.0,
                               "conv_eval_index": None, "stop_reason": None}
        self._t0 = None
        for d in (self.ckpt_dir, self.buffer_dir, log_dir):
            os.makedirs(d, exist_ok=True)

    # -- helpers -----------------------------------------------------------
    def wall_clock_s(self):
        return self.state["wall_clock_offset_s"] + (time.time() - self._t0)

    def _append_csv(self, path, fields, row):
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if new:
                w.writeheader()
            w.writerow(row)

    def _train_env(self):
        return self.training_env.venv.envs[0].unwrapped

    def criterion_series(self):
        return [e["criterion_value"] for e in self.state["evals"]]

    def checkpoint_path(self, step):
        return os.path.join(self.ckpt_dir, f"{self.run_name.lower()}_{step}_steps.zip")

    # -- persistence -------------------------------------------------------
    def save_checkpoint(self, step):
        path = self.checkpoint_path(step)
        self.model.save(path)
        self.training_env.save(path.replace(".zip", "_vecnormalize.pkl"))
        return path

    def save_replay_buffer(self, step):
        """Replay buffer + generator states + round-robin day index, written
        to a temp name then renamed, so an interruption mid-write never
        leaves a truncated file under the final name."""
        buf = os.path.join(self.buffer_dir, f"replay_buffer_{step}_steps.pkl")
        self.model.save_replay_buffer(buf + ".tmp")
        os.replace(buf + ".tmp", buf)
        aux = {"rng": _rng_snapshot(), "rr_index": self._train_env()._rr_index,
               "days_seen_len": len(self._train_env().days_seen), "step": step}
        with open(os.path.join(self.buffer_dir, f"resume_aux_{step}_steps.pkl"), "wb") as f:
            pickle.dump(aux, f)
        self.save_state()
        # Rotation (Gate 1 decision): keep only the BUFFERS_KEPT newest
        # buffer/aux pairs; older model checkpoints are all kept (small).
        saved = sorted(int(n.split("_")[2]) for n in os.listdir(self.buffer_dir)
                       if n.startswith("replay_buffer_") and n.endswith("_steps.pkl"))
        for old in saved[:-BUFFERS_KEPT]:
            for n in (f"replay_buffer_{old}_steps.pkl", f"resume_aux_{old}_steps.pkl"):
                try:
                    os.remove(os.path.join(self.buffer_dir, n))
                except FileNotFoundError:
                    pass

    def save_state(self):
        s = dict(self.state)
        s["wall_clock_offset_s"] = self.wall_clock_s()
        s["num_timesteps"] = self.num_timesteps
        tmp = os.path.join(self.model_dir, "state.json.tmp")
        with open(tmp, "w") as f:
            json.dump(s, f, indent=2, default=str)
        os.replace(tmp, os.path.join(self.model_dir, "state.json"))

    # -- core --------------------------------------------------------------
    def _spaces_venv(self):
        """DummyVecEnv over a stub with the training spaces -- only for
        VecNormalize.load to attach to; never reset or stepped."""
        from stable_baselines3.common.vec_env import DummyVecEnv
        obs_space, act_space = self.training_env.observation_space, self.training_env.action_space

        class _SpacesOnly(gym.Env):
            observation_space, action_space = obs_space, act_space
        return DummyVecEnv([_SpacesOnly])

    def evaluate_now(self):
        """Save checkpoint (+ VecNormalize sidecar) FIRST, then score that
        saved artifact with frozen statistics. The whole load+validate block
        runs under one RNG snapshot: TD3.load itself calls set_random_seed,
        which would otherwise reseed the training generators."""
        t_eval = time.time()
        ckpt = self.save_checkpoint(self.num_timesteps)
        snap = _rng_snapshot()
        try:
            eval_model, eval_vn = load_frozen_checkpoint(ckpt, self._spaces_venv())
            res = run_validation(eval_model, eval_vn, self.reward_fn, self.cells,
                                 day_config_dir=self.validation_day_config_dir)
        finally:
            _rng_restore(snap)
        val_wall = time.time() - t_eval
        wall = self.wall_clock_s()
        prev = self.state["evals"][-1] if self.state["evals"] else None
        prev_step, prev_wall = (prev["timesteps"], prev["wall_clock_s"]) if prev else (self.state.get("segment_start_step", 0), self.state.get("segment_start_wall_s", 0.0))
        train_s = max(wall - prev_wall - val_wall, 1e-9)
        entry = {"eval_index": len(self.state["evals"]), "timesteps": self.num_timesteps,
                 "wall_clock_s": round(wall, 2),
                 "validation_wall_clock_s": round(val_wall, 2),
                 "criterion_name": SELECTION_CRITERION, "criterion_value": res[SELECTION_CRITERION],
                 **{k: res[k] for k in VALIDATION_LOG_METRICS}, "n_cells": res["n_cells"],
                 "train_steps_per_s_since_last_eval": round((self.num_timesteps - prev_step) / train_s, 2),
                 "checkpoint_path": ckpt}
        self.state["evals"].append(entry)
        m = self.criterion_series()
        k = len(m) - 1
        entry["conditions_hold"] = convergence_conditions_at(m, k)
        if self.state["conv_eval_index"] is None:
            ci = convergence_index(m)
            if ci is not None:
                self.state["conv_eval_index"] = ci
        entry["converged"] = self.state["conv_eval_index"] is not None
        self._append_csv(self.val_csv, VALIDATION_CSV_FIELDS, entry)
        self.save_state()
        if self.verbose:
            print(f"[{self.run_name}] eval {k} @ {self.num_timesteps} steps: "
                  f"{SELECTION_CRITERION}={res[SELECTION_CRITERION]:.2f} | "
                  f"overload={res['total_transformer_overload']:.3f} kWh, "
                  f"energy_user_sat={res['energy_user_satisfaction']:.2f} | "
                  f"{entry['train_steps_per_s_since_last_eval']} steps/s, validation {val_wall:.1f}s, "
                  f"converged={entry['converged']}", flush=True)

    def _on_training_start(self):
        self._t0 = time.time()
        self.state["segment_start_step"] = self.num_timesteps
        self.state["segment_start_wall_s"] = self.state["wall_clock_offset_s"]

    def _on_step(self) -> bool:
        for done, info in zip(self.locals["dones"], self.locals["infos"]):
            if done and "episode" in info:
                seed = info.get("train_scenario_seed")
                self._append_csv(self.ep_csv, EPISODE_CSV_FIELDS, {
                    "episode_index": self.state["episode_index"], "timesteps_at_end": self.num_timesteps,
                    "wall_clock_s": round(self.wall_clock_s(), 2), "train_day": info.get("train_day"),
                    "train_scenario_seed": seed,
                    "scenario_seed_in_eval_seeds": seed in set(SEEDS) if seed is not None else None,
                    "rejected_eval_seed_draws": info.get("rejected_eval_seed_draws", ""),
                    "episode_reward_raw": info["episode"]["r"], "episode_length": info["episode"]["l"]})
                self.state["episode_index"] += 1

        if self.num_timesteps % self.eval_freq == 0:
            self.evaluate_now()
        if self.num_timesteps % self.buffer_freq == 0:
            self.save_replay_buffer(self.num_timesteps)

        ci = self.state["conv_eval_index"]
        if ci is not None:
            conv_step = self.state["evals"][ci]["timesteps"]
            if self.num_timesteps >= conv_step + self.confirmation_steps:
                self.state["stop_reason"] = "converged_plus_confirmation"
                return False
        if time.time() >= self.deadline_epoch_s - self.safety_margin_s:
            self.state["stop_reason"] = "deadline"
            return False
        if self.max_steps is not None and self.num_timesteps >= self.max_steps:
            self.state["stop_reason"] = "max_steps"
            return False
        return True

    def finalize(self):
        """Called by the training script after model.learn() returns: makes
        sure the last step has a validation score and a checkpoint, and
        saves the final model, VecNormalize stats and replay buffer."""
        if not self.state["evals"] or self.state["evals"][-1]["timesteps"] != self.num_timesteps:
            self.evaluate_now()
        if self.state["stop_reason"] is None:
            self.state["stop_reason"] = "learn_returned"
        final = os.path.join(self.model_dir, "final_model.zip")
        self.model.save(final)
        self.training_env.save(final.replace(".zip", "_vecnormalize.pkl"))
        self.save_replay_buffer(self.num_timesteps)
        m = self.criterion_series()
        ci = self.state["conv_eval_index"]
        pi = select_primary_index(m, ci)
        self.state["primary_eval_index"] = pi
        self.state["primary_step"] = self.state["evals"][pi]["timesteps"] if pi is not None else None
        self.state["last_step"] = self.num_timesteps
        self.state["finished_utc"] = datetime.datetime.utcnow().isoformat()
        self.save_state()
