# Week 3 — Parameter, Method, and Implementation Justification

**Git commit:** `2190ce39ddafeac3a25b4c59437e94459f2a2c57`
**Generated:** 2026-08-13T04:57:22.216728Z (regenerate with `PYTHONPATH=. python scripts/make_week3_handback.py` after any code change -- this document is built, not hand-maintained)

**Scope deviation, stated up front:** `PROJECT_ROADMAP.md` originally assigned
Week 3 to the Gurobi/MPC baseline. This was deliberately reversed before any
code was written: **Week 3 = RL baseline vanilla (TD3)**, Week 4 = a
perfect-information reference (free solver, no Gurobi) + PI-TD3, Week 5 =
the full comparison. Full reasoning in `thesis_docs/chapters/00_lab_log.md`'s
2026-08-12 Week 3 kickoff entry; the old MPC-first plan is marked
`[SUPERSEDED]` in `PROJECT_ROADMAP.md`, not deleted.

This document has two halves, in the same format as Week 2's: **Part 1**
(parameters and methods, validated/empirical/simplification labeling
convention) and **Part 2** (implementation, file by file, with code excerpts
extracted live from source).

## Part 1 -- Parameters and Methods

| Parameter | Value | Label | Justification |
|---|---|---|---|
| `TRAIN_SEEDS` | `[100, 101, 102]` | Empirically set inside this project | Three training seeds, sized against the confirmed ~4h CPU budget. Disjoint from `SEEDS` (scenario seeds) by construction and by an import-time assertion -- these are two different sources of randomness (scenario generation vs. agent training/exploration). |
| Reward function | `SqTrError_TrPenalty_UserIncentives` | Validated against external source (the function exists as-is in `ev2gym/rl_agent/reward.py`) | Chosen over the environment's bare default (`SquaredTrackingErrorReward`) because it also penalizes transformer overload and user dissatisfaction -- two of this thesis's three declared success axes; the bare default penalizes tracking error alone. Full comparison table in `thesis_docs/chapters/03_rl_baseline.md` S3.2. |
| State function | `PublicPST` | Validated against external source (the environment's own default) | The only one of `ev2gym/rl_agent/state.py`'s 5 functions that fits this project's Public/PST configuration (no price forecasts, no grid/voltage terms); not a comparison among equals since the other 4 don't apply. |
| Policy network architecture | `[64, 64]` | Simplification / declared limitation | Reduced from the SB3 default / TD3 paper's `[400, 300]`, sized for this project's CPU budget and this environment's much smaller (27-dim obs, 8-dim action) input than the paper's MuJoCo benchmarks. |
| Replay buffer size | `50,000` | Simplification / declared limitation | Reduced from SB3 default `1,000,000` -- at this project's timestep scale a 1e6 buffer would stay mostly empty. |
| `TOTAL_TIMESTEPS` | `60,000` per training seed | **User-confirmed 2026-08-12** (not a literature value) | Set after an explicit calibration run (5,000 timesteps, 18.09 steps/s measured) and a 4-candidate table (15k/30k/60k/90k) presented for the user's approval per `CLAUDE.md` rule 2 -- 60k was the largest candidate respecting both the ~75 min/seed and ~4h-total budgets the user gave. A drastic reduction against the PI-TD3/TD3 papers' 5-48h HPC training runs, stated as such, never presented as equivalent. |
| VecNormalize (obs + reward) | on, `clip_obs=10.0` | Empirically set inside this project | Design decision: this environment's observation mixes a 0/0.5/1 flag, energy in kWh, dwell time in steps, and power in kW in the same vector -- left unnormalized, the largest-magnitude features would dominate gradients. Evaluation always reloads saved statistics with `training=False, norm_reward=False`. |
| Deterministic evaluation (`predict(..., deterministic=True)`) | on | Empirically set inside this project | Isolates policy quality from training-time exploration noise for the Entregable 6 evaluation grid. |
| Day-sampling for training | round-robin over `TRAIN_DAYS` | Empirically set inside this project | Rejected alternative: `random.choice` with a fixed seed -- rejected because at this project's short training budget (at most a few hundred episodes against a 20-day pool), random sampling could by chance under- or over-represent some days; round-robin guarantees even coverage regardless of budget. |
| Random-policy control | `env.action_space.sample()`, action-space seeded with the scenario seed | Empirically set inside this project | Without this control, "TD3 beats AFAP" cannot be distinguished from "any policy that spreads power around beats AFAP at this station's 4:1 oversubscription ratio." Confirmed: the control's own overload (12.74 kWh) is worse than AFAP's (5.33 kWh), so this distinction is real, not academic. |

## Part 2 -- Implementation

### `ev2gym_thesis/eval_protocol.py` (extended, not rewritten)

**Purpose:** adds `TRAIN_SEEDS`, disjoint-asserted against `SEEDS` at import
time, mirroring the `TRAIN_DAYS`/`EVAL_DAYS` disjointness already in place
from Week 2.

`ev2gym_thesis/eval_protocol.py:42-50`

```python
# Empirically set inside this project (not a literature value): 3 training
# seeds, sized against the ~4h total CPU training budget confirmed for Week
# 3 (see thesis_docs/chapters/00_lab_log.md's Entregable 4 entry) -- 3 full
# TD3 training runs is what that budget allows while still letting every
# seed be reported (never just the best, see Entregable 5). Disjoint from
# SEEDS by construction (100s vs. single digits) and asserted below so an
# accidental overlap fails at import time rather than silently reusing a
# scenario seed as a training seed.
TRAIN_SEEDS = [100, 101, 102]
```


`ev2gym_thesis/eval_protocol.py:54-58`

```python
assert set(SEEDS).isdisjoint(set(TRAIN_SEEDS)), (
    "SEEDS and TRAIN_SEEDS overlap -- these are two different sources of "
    "randomness (scenario generation vs. agent training/exploration) and "
    "must stay disjoint so a seed value's meaning is unambiguous."
)
```


### `ev2gym_thesis/rl/` (new subpackage -- `ev2gym/rl_agent/*.py` was never touched)

**`env_factory.py`** -- environment construction for both training and
evaluation, using `config_utils.make_day_config` (Week 2's mechanism), so
RL and the Week 1-2 heuristics see identical scenarios on shared
(config, day, seed) cells.

`ev2gym_thesis/rl/env_factory.py:39-61`

```python
def make_env(config_path: str, day: tuple, scenario_seed: int,
             reward_fn=DEFAULT_REWARD_FN, state_fn=DEFAULT_STATE_FN,
             day_config_dir: str = EVAL_DAY_CONFIG_DIR) -> EV2Gym:
    """Build one EV2Gym instance for a single (config, day, scenario_seed)
    cell.

    Uses config_utils.make_day_config -- the exact same mechanism
    scripts/backfill_registry.py uses for AFAP/Round Robin -- so an RL agent
    evaluated on (config_path, day, scenario_seed) sees the literal same
    scenario a heuristic evaluated on that cell saw, not just a "similar"
    one. This is what makes the Entregable 6 comparison a paired comparison
    rather than an independent-sample one.
    """
    year, month, day_of_month = day
    day_config_path = make_day_config(config_path, year, month, day_of_month, day_config_dir)
    return EV2Gym(
        config_file=day_config_path,
        seed=scenario_seed,
        save_replay=False,
        save_plots=False,
        reward_function=reward_fn,
        state_function=state_fn,
    )
```


`TrainingDayCyclingEnv` samples a new day from `TRAIN_DAYS` (never
`EVAL_DAYS`) every `reset()`, since `EV2Gym` cannot vary its simulated day
across resets of the same instance without `config['random_day']=True`
(which samples uniformly across ~1.5 years, not restricted to `TRAIN_DAYS`):

`ev2gym_thesis/rl/env_factory.py:100-125`

```python
    def __init__(self, config_path: str, reward_fn=DEFAULT_REWARD_FN,
                 state_fn=DEFAULT_STATE_FN, sample_mode: str = "round_robin",
                 rng_seed: int = None, day_config_dir: str = TRAIN_DAY_CONFIG_DIR):
        super().__init__()
        if sample_mode not in ("round_robin", "random"):
            raise ValueError(f"Unknown sample_mode {sample_mode!r}; expected 'round_robin' or 'random'")
        if sample_mode == "random" and rng_seed is None:
            raise ValueError("sample_mode='random' requires an explicit rng_seed for reproducibility")

        self.config_path = config_path
        self.reward_fn = reward_fn
        self.state_fn = state_fn
        self.sample_mode = sample_mode
        self.day_config_dir = day_config_dir
        self._rng = random.Random(rng_seed)
        self._rr_index = 0
        self.days_seen = []  # every day sampled so far, for the anti-leakage test

        # Probe instance purely to publish action_space/observation_space
        # before the first reset() (SB3 needs these at construction time) --
        # neither space depends on which day is loaded, so any TRAIN_DAYS
        # day is representative.
        probe_env = self._build_env_for_day(TRAIN_DAYS[0], seed=0)
        self.action_space = probe_env.action_space
        self.observation_space = probe_env.observation_space
        self._env = probe_env
```


`ev2gym_thesis/rl/env_factory.py:129-147`

```python
    def _next_day(self) -> tuple:
        if self.sample_mode == "round_robin":
            day = TRAIN_DAYS[self._rr_index % len(TRAIN_DAYS)]
            self._rr_index += 1
        else:
            day = self._rng.choice(TRAIN_DAYS)
        assert day not in EVAL_DAYS, (
            f"Sampled day {day} is in EVAL_DAYS -- this must never happen "
            f"(train/eval leakage). TRAIN_DAYS/EVAL_DAYS disjointness is "
            f"already asserted at eval_protocol import time; reaching this "
            f"means TRAIN_DAYS itself was mutated after import."
        )
        self.days_seen.append(day)
        return day

    def reset(self, seed=None, options=None):
        day = self._next_day()
        self._env = self._build_env_for_day(day, seed=seed)
        return self._env.reset(seed=seed)
```


**`config_rl.py`** -- every TD3 hyperparameter with a declared origin
(`"SB3 default"`, `"TD3 paper"`, or `"set for this project's CPU budget"`,
verbatim per constant):

`ev2gym_thesis/rl/config_rl.py:64-81`

```python
POLICY = "MlpPolicy"          # SB3 default policy class for a flat vector observation
NET_ARCH = [64, 64]           # set for this project's CPU budget (reduced from SB3 default/TD3 paper [400, 300])
LEARNING_RATE = 1e-3          # SB3 default
GAMMA = 0.99                  # SB3 default
TAU = 0.005                   # SB3 default ("Polyak" target-network update rate)
TRAIN_FREQ = 1                # SB3 default (one env step per gradient-update opportunity)
GRADIENT_STEPS = 1            # SB3 default
POLICY_DELAY = 2              # SB3 default / TD3 paper (delayed policy updates, TD3's namesake mechanism)
TARGET_POLICY_NOISE = 0.2     # SB3 default / TD3 paper (target policy smoothing noise std)
TARGET_NOISE_CLIP = 0.5       # SB3 default / TD3 paper (target policy smoothing noise clip)
BATCH_SIZE = 256              # SB3 default
BUFFER_SIZE = 50_000          # set for this project's CPU budget (reduced from SB3 default 1,000,000)
LEARNING_STARTS = 500         # set for this project's CPU budget (increased from SB3 default 100)
ACTION_NOISE_SIGMA = 0.1      # TD3 paper (exploration noise, relative to this project's [0,1] action range)


def make_action_noise(n_actions: int) -> NormalActionNoise:
    return NormalActionNoise(mean=np.zeros(n_actions), sigma=ACTION_NOISE_SIGMA * np.ones(n_actions))
```


`ev2gym_thesis/rl/config_rl.py:109-124`

```python
# TOTAL_TIMESTEPS: confirmed by the user 2026-08-12 (per CLAUDE.md rule 2 --
# training wall-clock must be confirmed before any long run) after the
# Entregable 4 calibration below. Measured: 5,000 timesteps = 276.4s (18.09
# steps/s) on station_v0_bogota with these exact hyperparameters. 60,000
# timesteps/seed = ~55.3 min/seed, ~165.9 min (2.8h) for all 3 TRAIN_SEEDS --
# the largest of 4 presented candidates (15k/30k/60k/90k) that respects
# BOTH the user's stated ~75 min/seed ceiling and ~4h total budget (90k
# would have been 82.9 min/seed, breaking the per-seed ceiling). At this
# budget the agent sees each of the 20 TRAIN_DAYS dates ~31 times
# (round-robin cycling, see env_factory.TrainingDayCyclingEnv). This is a
# declared, drastic reduction against the PI-TD3/TD3 papers' HPC training
# budgets of 5-48 hours -- NOT presented as an equivalent training regime;
# see thesis_docs/chapters/00_lab_log.md's Entregable 4 entry for the full
# comparison and thesis_docs/chapters/03_rl_baseline.md for how this bounds
# what can be claimed about convergence.
TOTAL_TIMESTEPS = 60_000
```


**`callbacks.py`** -- periodic checkpointing (resumable training) and a
CSV learning-curve log independent of stdout:

`ev2gym_thesis/rl/callbacks.py:23-36`

```python
def make_checkpoint_callback(save_dir: str, save_freq_steps: int, name_prefix: str) -> CheckpointCallback:
    """Periodic checkpoint, including VecNormalize stats when the training
    env is VecNormalize-wrapped. save_freq_steps is in environment steps, as
    SB3's own CheckpointCallback expects (n_envs=1 in this project, so no
    save_freq // n_envs adjustment is needed -- see SB3's own docstring
    note about that adjustment, which only applies to n_envs > 1)."""
    os.makedirs(save_dir, exist_ok=True)
    return CheckpointCallback(
        save_freq=save_freq_steps,
        save_path=save_dir,
        name_prefix=name_prefix,
        save_replay_buffer=False,  # not needed for reproducing reported metrics; would bloat committed/regenerable artifacts for no evaluation benefit
        save_vecnormalize=True,
    )
```


`ev2gym_thesis/rl/callbacks.py:41-75`

```python
class LearningCurveCallback(BaseCallback):
    """Appends one row per log_freq_steps to a CSV: timesteps, the mean
    episode reward and mean episode length over SB3's own rolling
    ep_info_buffer (last <=100 completed episodes, SB3's standard window),
    and wall-clock seconds elapsed since training start. Written
    incrementally (flushed every row), not buffered in memory and written
    once at the end, so a crash or interruption doesn't lose the curve."""

    def __init__(self, csv_path: str, log_freq_steps: int, verbose: int = 0):
        super().__init__(verbose)
        self.csv_path = csv_path
        self.log_freq_steps = log_freq_steps
        self._start_time = None
        self._file = None
        self._writer = None

    def _on_training_start(self) -> None:
        self._start_time = time.time()
        os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
        self._file = open(self.csv_path, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["timesteps", "mean_episode_reward", "mean_episode_length", "elapsed_wall_clock_s"])

    def _on_step(self) -> bool:
        if self.num_timesteps % self.log_freq_steps == 0 and len(self.model.ep_info_buffer) > 0:
            mean_reward = sum(ep["r"] for ep in self.model.ep_info_buffer) / len(self.model.ep_info_buffer)
            mean_length = sum(ep["l"] for ep in self.model.ep_info_buffer) / len(self.model.ep_info_buffer)
            elapsed = time.time() - self._start_time
            self._writer.writerow([self.num_timesteps, mean_reward, mean_length, round(elapsed, 2)])
            self._file.flush()
        return True

    def _on_training_end(self) -> None:
        if self._file is not None:
            self._file.close()
```


**`eval_utils.py`** -- loading a trained checkpoint for evaluation, refusing
to proceed silently if the VecNormalize statistics file is missing (the
classic bug that makes an agent "work in training, collapse in
evaluation"):

`ev2gym_thesis/rl/eval_utils.py:30-60`

```python
def load_trained_agent(model_path: str, env, vecnormalize_path: str = None):
    """Load a TD3 model plus its VecNormalize statistics for evaluation.

    Raises FileNotFoundError loudly if the VecNormalize stats file doesn't
    exist next to the model checkpoint -- silently evaluating with
    mismatched (or default-initialized) normalization statistics is exactly
    the bug this function exists to make impossible.

    `env` must be a single, un-normalized environment (e.g. straight from
    env_factory.make_env); this function wraps it in DummyVecEnv +
    VecNormalize.load(...) and forces training=False, norm_reward=False --
    reward normalization is a training-time convenience only and must never
    affect evaluated/reported metrics.
    """
    if vecnormalize_path is None:
        vecnormalize_path = vecnormalize_path_for(model_path)
    if not os.path.exists(vecnormalize_path):
        raise FileNotFoundError(
            f"VecNormalize statistics file not found at {vecnormalize_path!r} "
            f"for checkpoint {model_path!r}. Evaluating a VecNormalize-trained "
            f"model without its saved statistics silently uses wrong-scale "
            f"observations -- refusing to proceed. Statistics are saved "
            f"automatically by ev2gym_thesis/rl/callbacks.py's "
            f"CheckpointCallback(save_vecnormalize=True)."
        )
    venv = DummyVecEnv([lambda: env])
    venv = VecNormalize.load(vecnormalize_path, venv)
    venv.training = False
    venv.norm_reward = False
    model = TD3.load(model_path, env=venv)
    return model, venv
```


### `scripts/calibrate_td3_timing.py` (Entregable 4)

Runs a fixed 5,000-timestep calibration with the real `config_rl.py`
hyperparameters and extrapolates to 4 candidate total-timestep budgets,
explicitly refusing to launch a longer run itself -- the script's own
output ends with a printed reminder that `CLAUDE.md` rule 2 requires the
user's explicit confirmation before any longer run.

### `scripts/train_td3.py` (Entregable 5)

Trains all 3 `TRAIN_SEEDS` sequentially (or a single seed via `--seed`, with
`--resume` support for an interrupted run). Per-run artifacts: model,
VecNormalize statistics, learning-curve CSV, and a manifest JSON (git
commit, config, reward/state function names, every hyperparameter,
timesteps, training seed, wall-clock, library versions) -- see
`experiments/phase2_algorithms/models/TD3_vanilla_ts{seed}/manifest.json`.

### `scripts/evaluate_rl.py` (Entregable 6)

Evaluates all 3 TD3 checkpoints plus the `RandomPolicy` control on the same
50-cell grid (`SEEDS` x `EVAL_DAYS`) used for AFAP/Round Robin, appending
`algorithm_family="rl"` rows to `results/master_results.csv` with
`notes` recording `reward=...,state=...,train_seed=...` per row (per
`03_rl_baseline.md` S3.5's registry-comparability requirement). Registry
key collision (3 training seeds vs. one `(config, algorithm, seed, day)`
dedup key) resolved by giving each training seed its own algorithm name:
`TD3_vanilla_ts100`/`_ts101`/`_ts102`.

**Real bug found and fixed during this deliverable** (see
`00_lab_log.md`'s 2026-08-13 entry for the full diagnosis): the original
TD3 evaluation stepped through `VecNormalize(DummyVecEnv([env]))`, and
SB3's `DummyVecEnv` auto-resets its underlying env INSIDE the same
`step()` call that returns the terminal transition -- silently wiping
`env.current_power_usage` before external code could read it for
timeseries capture. Confirmed empirically (`current_power_usage.sum()`
was `0.0` immediately after the episode loop, while the registry's own
scalar stats were correct throughout, since SB3 preserves the pre-reset
info dict). Fixed by stepping the raw env directly and manually applying
the loaded `VecNormalize`'s observation normalization:

`ev2gym_thesis/rl/eval_utils.py:65-85`

```python
def run_episode(model, venv, deterministic: bool = True) -> dict:
    """Runs exactly one episode on a (possibly VecNormalize-wrapped) vector
    env and returns the underlying EV2Gym instance's final stats dict.

    deterministic=True is used for every Entregable 6 evaluation run
    (documented design decision, thesis_docs/chapters/03_rl_baseline.md):
    evaluation must isolate policy quality from action-sampling noise, which
    training-time stochastic exploration would otherwise reintroduce into a
    number this thesis reports as "the agent's performance."
    """
    obs = venv.reset()
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=deterministic)
        obs, reward, done, info = venv.step(action)
        done = bool(done[0])
    # info[0]["terminal_observation"] is the pre-reset obs; the actual
    # EV2Gym stats dict is on the underlying (unwrapped) env after the
    # episode's final step, since EV2Gym's own _check_termination returns
    # self.stats as the info dict on the terminal step.
    return info[0]
```


### `scripts/analyze_rl_results.py` (Entregable 7)

Paired bootstrap (`stats_utils.paired_bootstrap_ci`, already written and
tested in Week 2 -- no new bootstrap code) of each TD3 training seed
against AFAP and Round Robin, plus a separate cross-training-seed
dispersion analysis (min/max/std across the 3 seeds' per-metric means,
holding the evaluation grid fixed) -- a genuinely different uncertainty
source from the scenario-level confidence intervals, kept apart rather than
pooled. Writes `results/rl_vs_baseline_bootstrap.csv` and
`results/rl_train_seed_dispersion.csv`.

### `ev2gym_thesis/registry_analysis.py` (Week 2 -> Week 3 contract change)

`main_grid_rows()` used to filter by `notes == ""`. Week 3's RL rows
legitimately use non-empty `notes` for reward/state/train_seed metadata, so
that filter silently excluded all 200 new RL rows. Fixed by filtering on an
explicit exclusion-marker set instead of "notes is non-empty":

`ev2gym_thesis/registry_analysis.py:36-45`

```python
# Week 3 contract change (see thesis_docs/chapters/00_lab_log.md's Week 3,
# Entregable 6 entry): main_grid_rows() used to filter by `notes == ""`,
# treating ANY non-empty notes value as "not part of the main grid" (Weeks
# 1-2 only ever used notes for exactly these two markers, so the two
# conventions were indistinguishable at the time). Week 3's RL rows
# legitimately use `notes` for real grid-row metadata (reward/state/
# train_seed, per 03_rl_baseline.md S3.5's registry-comparability
# requirement), so "non-empty notes" no longer implies "excluded from the
# grid" -- it now means EXACTLY one of these two explicit markers.
NON_GRID_NOTES_MARKERS = {"week1_reference_day", "pipeline_smoke_test_grid"}
```


Verified this does not affect `scripts/measure_degradation_by_ambient.py`,
which has its own independent inline `notes == ""` filter, not a call into
`main_grid_rows`.

### `ev2gym_thesis/figures.py` -- `total_reward` cross-family guardrail (Entregable 3) and `ALGORITHM_STYLE` (append-only)

Weeks 1-2's heuristic rows and Week 3's RL rows do not share a reward
function, so `total_reward` is not a comparable quantity between them.
This guardrail raises if a figure ever tries to compare it across rows
with different reward functions:

`ev2gym_thesis/figures.py:38-73`

```python
# Week 3, Entregable 3 (thesis_docs/chapters/03_rl_baseline.md S3.5):
# total_reward is computed under whichever reward_function an EV2Gym run was
# built with. Weeks 1-2's heuristic rows and Week 3+'s RL rows do NOT share
# a reward function (see that chapter section), so total_reward is not a
# comparable quantity across rows that used different ones -- comparing it
# anyway would silently plot apples against oranges under a shared axis
# label. New registry rows record their reward function by name in the
# `notes` column (e.g. "reward=SqTrError_TrPenalty_UserIncentives,..."); rows
# with no such marker (Weeks 1-2) used the environment's own default.
_DEFAULT_REWARD_FN_NAME = "SquaredTrackingErrorReward"  # EV2Gym.__init__'s own default, implicit for rows whose notes don't declare a reward function


def _reward_fn_name(row: dict) -> str:
    for part in (row.get("notes") or "").split(","):
        if part.startswith("reward="):
            return part.split("=", 1)[1]
    return _DEFAULT_REWARD_FN_NAME


def assert_total_reward_comparable(rows: list, metric: str = "total_reward") -> None:
    """No-op for any metric other than total_reward. For total_reward,
    raises if `rows` mixes runs built with different reward functions.
    Call this at the top of any per-metric loop in a figure-generating
    function, before computing/plotting values for that metric, so a future
    figure that adds total_reward to a comparison fails loudly instead of
    silently comparing incompatible values."""
    if metric != "total_reward":
        return
    reward_fns = {_reward_fn_name(r) for r in rows}
    if len(reward_fns) > 1:
        raise ValueError(
            f"Cannot compare/plot total_reward across rows built with "
            f"different reward functions: {sorted(reward_fns)}. See "
            f"thesis_docs/chapters/03_rl_baseline.md S3.5 -- total_reward is "
            f"only a comparable quantity within a single reward function."
        )
```


`ALGORITHM_STYLE` gained 4 new entries (`TD3_vanilla_ts100/101/102`,
`RandomPolicy`) by append only -- AFAP's and Round Robin's existing
color/marker were not touched.

### `scripts/make_figures.py` -- `f08` activated, 5 real bugs found by visual QA (Entregable 7)

`f08_learning_curves` was an inert stub since Week 2 (correctly skipping
until `algorithm_family=="rl"` rows existed); now reads each training run's
own `learning_curve.csv` directly, the same pattern `f09` already uses for
its own separate (non-registry) source file.

**Visual QA is mandatory, not optional** -- "ran without error" was not
"was correct" for 2 of the figures this week, matching Week 2's own
experience with `f05`/`f07`. Full list of the 5 bugs found and fixed
(timeseries corruption plus 4 figure-legibility issues once 6 algorithms
replaced 2) is in `00_lab_log.md`'s 2026-08-13 entry -- not repeated here
to avoid drift between two copies of the same list.

### `ev2gym_thesis/tests/test_rl_infrastructure.py` (Entregable 9)

8 tests, all passing, deliberately independent of whether a real trained
model exists yet (fresh/untrained TD3 instances are enough to test the
infrastructure's correctness): `TRAIN_SEEDS`/`SEEDS` and `TRAIN_DAYS`/
`EVAL_DAYS` disjointness, `TrainingDayCyclingEnv` never sampling an
`EVAL_DAYS` date (round-robin and random modes), a missing VecNormalize
statistics file failing loudly (`FileNotFoundError`, not a silent
evaluation with wrong-scale observations), and evaluation reproducibility
(same config/seed/day/model evaluated twice gives identical stats).

## Headline Results Summary

Full tables, the paired-bootstrap comparison, and the cross-training-seed
dispersion analysis are in `thesis_docs/chapters/03_rl_baseline.md`
(sections 3.8-3.10) and `00_lab_log.md`'s 2026-08-13 entry -- not repeated
in full here. Headline: TD3 matches Round Robin's near-elimination of
transformer overload (vs. AFAP's 5.33 kWh), confirmed against a
random-policy control that shows WORSE overload (12.74 kWh) than even
unmanaged AFAP -- proving this is a real learned behavior. This comes at a
real cost: lower and seed-inconsistent `total_ev_served`, materially lower
`min_energy_user_satisfaction` (down to 86.7% for the worst seed), and
worse tracking precision than the much simpler Round Robin heuristic.
Training wall-clock: 2.79h total (3 seeds), matching the calibration
estimate almost exactly. Learning curves show a weak-but-consistent
positive trend across all 3 seeds, not clean convergence -- reported as
the legitimate result of the declared reduced training budget, not
adjusted or hidden.
