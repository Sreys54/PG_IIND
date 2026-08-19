# Week 3 — Parameter, Method, and Implementation Justification

**Git commit:** `4a82315b68e2a106928ecba523b2cc15ca14e5c9`
**Generated:** 2026-08-19T03:49:55.472188Z (regenerate with `PYTHONPATH=. python scripts/make_week3_handback.py` after any code change -- this document is built, not hand-maintained)

**This build supersedes the 2026-08-13 build.** It carries a 2026-08-18
correction (below and in Part 2) that changes this week's headline
results. The original build is not separately preserved as a file, but
every number it held now has an explicit before/after in
`thesis_docs/chapters/00_lab_log.md`'s 2026-08-18 entry and
`results/master_results_prefix_week3_evaluation_bug.csv` (the 200
pre-correction rows, kept, not deleted).

**Correction, 2026-08-18 (found during Week 4 preflight, fixed on
`semana-3` per the project's branch discipline):** all 200
TD3/RandomPolicy evaluation episodes (Entregable 6) ran against an
uncontrolled, re-randomized scenario instead of the registered `(SEEDS x
EVAL_DAYS)` cell, because `scripts/evaluate_rl.py`'s evaluation steppers
called `env.reset()` with no seed. Fixed at the source
(`env_factory.reset_for_evaluation`, Part 2 below), all 200 episodes
re-run, and every downstream artifact (bootstrap CSVs, figures, this
document, `thesis_docs/chapters/03_rl_baseline.md`) regenerated from the
corrected data. **This reverses one headline conclusion:** the
random-policy control no longer shows worse transformer overload than
AFAP -- under the corrected data it shows significantly *better* overload
than AFAP and is statistically indistinguishable from TD3, so it no
longer supports "TD3 learned a real overload-avoidance behavior beyond
naive throttling." Full diagnosis, evidence, and old-vs-corrected numbers
in `00_lab_log.md`'s 2026-08-18 entry and `03_rl_baseline.md` S3.11.
**Trained model weights are unaffected -- no retraining was performed or
needed.**

**Scope deviation, stated up front:** `PROJECT_ROADMAP.md` originally assigned
Week 3 to the Gurobi/MPC baseline. This was deliberately reversed before any
code was written: **Week 3 = RL baseline vanilla (TD3)**, Week 4 = a
perfect-information reference (free solver, no Gurobi) + PI-TD3, Week 5 =
the full comparison. Full reasoning in `thesis_docs/chapters/00_lab_log.md`'s
2026-08-12 Week 3 kickoff entry; the old MPC-first plan is marked
`[SUPERSEDED]` in `PROJECT_ROADMAP.md`, not deleted.

This document has two halves, in the same format as Week 2's: **Part 1**
(parameters and methods, validated/empirical/simplification labeling
convention) and **Part 2** (implementation, file by file: Location,
Purpose, Design decision(s) with rejected alternatives, the actual code,
and a Walkthrough).

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
| `NON_GRID_NOTES_MARKERS` | `{"week1_reference_day", "pipeline_smoke_test_grid"}` | Empirically set inside this project (contract change from Week 2) | Week 2's `main_grid_rows()` filtered by `notes == ""`; Week 3's RL rows legitimately use non-empty `notes` for reward/state/train_seed metadata, so that filter silently excluded every RL row. Replaced with an explicit exclusion-marker set. |

## Part 2 -- Implementation

### `ev2gym_thesis/eval_protocol.py` (extended, not rewritten)

**Location:** `ev2gym_thesis/`, the same Week 2 module that already holds
`SEEDS`/`EVAL_DAYS`/`TRAIN_DAYS` -- extended in place rather than
introducing a second protocol module, for the same reason Week 2 chose one
importable module over per-config YAML values: every script must agree on
the same grid, and a second module would just split that single source of
truth in two.

**Purpose:** adds `TRAIN_SEEDS`, a second and conceptually distinct kind of
seed from `SEEDS`. `SEEDS` controls scenario generation (EV arrivals);
`TRAIN_SEEDS` controls the agent's network initialization and exploration
noise. Both are sources of randomness that must be reported, but they
answer different questions, so conflating them (e.g. reusing `SEEDS` for
training too) would make it impossible to later ask "how much does
performance vary across scenarios" separately from "how much does it vary
across training runs."

**Design decision -- disjoint value ranges (100s) plus an import-time
assertion, not just a code comment:** rejected relying on documentation
alone to keep the two seed pools apart. `TRAIN_SEEDS` values (100, 101,
102) are deliberately far from `SEEDS`' single-digit range, and an
`assert` at module level (mirroring `EVAL_DAYS`/`TRAIN_DAYS`'s existing
Week 2 pattern) makes an accidental overlap a hard import-time failure for
every script that imports this module, not a silent bug a reviewer would
have to notice by eye.

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


**Walkthrough:** the assertion runs once, at import time, exactly like
`EVAL_DAYS`/`TRAIN_DAYS`'s existing disjointness check from Week 2 -- any
script that imports `ev2gym_thesis.eval_protocol` gets the safety check
for free.

### `ev2gym_thesis/rl/` (new subpackage)

**Location:** new top-level subpackage `ev2gym_thesis/rl/` -- `ev2gym/rl_agent/*.py`
was never modified; this subpackage only imports the library's published
`reward_function`/`state_function` interface, per the same working rule
Week 1-2 already followed for `ev2gym_thesis/`.

**Purpose:** everything needed to train and evaluate a TD3 agent against
this project's Public/PST configuration, built so that Week 4's PI-TD3 can
be a drop-in reward/state module rather than a rewrite -- reward and state
logic (`env_factory.py`'s `DEFAULT_REWARD_FN`/`DEFAULT_STATE_FN`) is kept
separate from the training/evaluation wrapper (`config_rl.py`,
`callbacks.py`, `eval_utils.py`) specifically so swapping in a
physics-informed reward next week doesn't require touching the wrapper
code at all.

#### `ev2gym_thesis/rl/env_factory.py`

**Purpose:** environment construction for both training and evaluation.

**Design decision -- reuse `config_utils.make_day_config` (Week 2's
mechanism) instead of a new RL-specific day-override path:** rejected
writing a separate config-patching function for RL. Chosen: `make_env`
calls the exact same `config_utils.make_day_config` that
`scripts/backfill_registry.py` already uses for AFAP/Round Robin, so an RL
agent evaluated on `(config_path, day, scenario_seed)` sees the literal
same scenario a heuristic evaluated on that cell saw -- this is what makes
Entregable 6's comparison a paired comparison rather than an
independent-sample one.

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


**Design decision -- `TrainingDayCyclingEnv` builds a fresh `EV2Gym`
instance every episode, rather than mutating one long-lived instance's
internal date:** `EV2Gym` cannot vary its simulated day across resets of
the same instance unless `config['random_day']=True`, and that flag
samples uniformly across ~1.5 years with no way to restrict it to the
`TRAIN_DAYS` pool (verified by reading `ev2gym_env.py`'s `reset()`, not
assumed -- see the Week 3 preflight entry in `00_lab_log.md`). Rejected
alternative: directly mutating a single long-lived `EV2Gym` instance's
`sim_starting_date` attribute between resets. This would be cheaper (skips
re-reading the day-config YAML and the Netherlands price CSV every
episode) but relies on internal `EV2Gym` state that is not a published
interface and is not verified safe for every loader
(`load_transformers`, `load_ev_charger_profiles`, etc.) -- a correctness
risk not worth taking for the sake of the construction overhead, which the
Entregable 4 timing calibration measures directly (and which turned out to
dominate the measured 18.09 steps/s, per that entry).

`ev2gym_thesis/rl/env_factory.py:149-174`

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

`ev2gym_thesis/rl/env_factory.py:178-196`

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


**Design decision -- round-robin day sampling, not random-with-seed:**
rejected `random.choice` with a fixed RNG seed. Chosen: deterministic
cycling through `TRAIN_DAYS` in order. Reason: the Week 3 CPU budget caps
total training to at most a few hundred episodes per training seed against
a 20-day pool -- random sampling at that scale can by chance
under-represent or skip some days entirely, while round-robin guarantees
every `TRAIN_DAYS` date is seen an equal (+/-1) number of times regardless
of how many episodes the budget allows. `sample_mode="random"` is still
available (`rng_seed` required) for a future ablation, but is not the
default -- see the `_next_day` method above.

**Walkthrough:** the constructor builds one "probe" `EV2Gym` instance
purely to read off `action_space`/`observation_space` before the first
`reset()` (SB3 needs these at construction time); neither space depends on
which day is loaded, so any `TRAIN_DAYS` day is representative. `_next_day`
asserts every sampled day is absent from `EVAL_DAYS` as a second,
redundant safety net on top of the import-time assertion in
`eval_protocol.py` -- belt and suspenders against train/eval leakage, per
Entregable 9's explicit test requirement.

#### `ev2gym_thesis/rl/config_rl.py`

**Purpose:** every TD3 hyperparameter as a named constant with a declared
origin -- `"SB3 default"`, `"TD3 paper"`, or `"set for this project's CPU
budget"` -- verbatim per constant, so no hyperparameter in this project is
an unlabeled guess.

**Design decision -- read SB3's actual installed source rather than
assume defaults from memory:** every `"SB3 default"` label below was
confirmed by reading `stable_baselines3==2.9.0`'s own
`td3/td3.py`/`td3/policies.py` source directly (e.g. `net_arch=[400, 300]`
is the original TD3 paper's architecture, confirmed at
`td3/policies.py:141-145`), not recalled from memory or copied from
documentation that might be stale relative to the installed version.

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


**Design decision -- `TOTAL_TIMESTEPS` is a user-confirmed value, gated
behind a calibration run, not a default:** per `CLAUDE.md` rule 2 ("before
running anything that trains an RL agent, confirm the expected wall-clock
time with me"), this constant was left unset (`None`) until Entregable 4's
calibration produced a 4-candidate table and the user explicitly picked
one -- see `thesis_docs/chapters/00_lab_log.md`'s Entregable 4 entry for
the full table and reasoning.

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


**Walkthrough:** the largest deviations from SB3 defaults are all in one
direction -- smaller network, smaller buffer, more upfront random
exploration -- all justified by the same constraint (a CPU-only budget
measured in hours, not the papers' HPC-scale runs), stated individually
rather than as one blanket justification, so each can be independently
revisited if Week 4/5's budget changes.

#### `ev2gym_thesis/rl/callbacks.py`

**Purpose:** periodic checkpointing (training must be resumable -- if a
run is cut at hour 2 of a budgeted ~1h/seed run, it must not lose
everything) and a CSV learning-curve log independent of stdout.

**Design decision -- reuse SB3's own `CheckpointCallback` rather than
writing one:** SB3 already implements checkpoint saving correctly,
including a `save_vecnormalize=True` flag that saves the `VecNormalize`
running statistics alongside each checkpoint -- exactly the artifact
Entregable 5 requires next to every model file. Reimplementing this would
duplicate already-correct library code for no benefit.

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


**Design decision -- a custom `LearningCurveCallback`, since SB3 has no
built-in equivalent:** SB3's `Monitor` wrapper logs per-episode
reward/length/time to its own CSV format, but not indexed by training
timestep in the "timesteps -> mean reward" shape this project's learning
curves need. Custom callback, reading from SB3's own rolling
`ep_info_buffer` (the same buffer SB3's own console logging uses) rather
than maintaining a second, parallel reward-tracking mechanism.

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


**Walkthrough:** the CSV is opened and flushed every `log_freq_steps`, not
buffered in memory and written once at the end -- a crash mid-training
still leaves a partial, readable learning curve. **Bug found while
smoke-testing this callback, before the real training run** (see the
`scripts/evaluate_rl.py` section below for the analogous bug found during
evaluation): `ep_info_buffer` stayed empty in an early test because the
training env wasn't wrapped in `stable_baselines3.common.monitor.Monitor`
-- SB3 only populates that buffer from an `"episode"` info key `Monitor`
adds on episode end. Fixed at the source in `env_factory.make_training_env`
(now returns a `Monitor`-wrapped env), not per call site, so every current
and future caller gets the fix automatically.

#### `ev2gym_thesis/rl/eval_utils.py`

**Purpose:** loading a trained checkpoint for evaluation.

**Design decision -- fail loudly if `VecNormalize` statistics are
missing, rather than falling back to unnormalized evaluation:** this is
the classic bug that makes an agent "work in training, collapse in
evaluation" -- an agent trained against normalized observations, evaluated
against raw ones, sees inputs on a completely different scale than it
learned on, and the failure is silent (no exception, just bad numbers).
Rejected alternative: defaulting to `training=True` or skipping
normalization silently if the stats file is absent. Chosen: raise
`FileNotFoundError` immediately, naming the expected path and the
callback that should have produced it -- pinned by a test in Entregable 9
(`test_missing_vecnormalize_file_raises_file_not_found`).

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


**Walkthrough:** `env` must be a single, un-normalized environment (e.g.
straight from `env_factory.make_env`); this function does the
`DummyVecEnv` + `VecNormalize.load(...)` wrapping itself and forces
`training=False, norm_reward=False` -- reward normalization is a
training-time convenience only and must never leak into reported
evaluation metrics.

### `scripts/calibrate_td3_timing.py` (Entregable 4)

**Location:** `scripts/` -- an entry point, not imported elsewhere.

**Purpose:** produces the wall-clock-time table `CLAUDE.md` rule 2
requires before any long RL training run.

**Design decision -- a fixed 5,000-timestep run with the REAL `config_rl.py`
hyperparameters, not a toy configuration:** rejected calibrating with a
smaller/cheaper network or fewer episodes for speed -- that would measure
a different system than the one actually trained, making the extrapolation
unreliable. The script uses the exact same `TD3(...)` construction
`scripts/train_td3.py` uses, just for a smaller `total_timesteps`, and
explicitly refuses to launch anything longer itself -- its own final
printed line is a reminder that a longer run needs the user's confirmation,
not a suggestion to proceed.

**Walkthrough:** the measured throughput (18.09 steps/s) is dominated by
per-episode environment reconstruction (`TrainingDayCyclingEnv` rebuilds
`EV2Gym` -- including rereading the day-config YAML and the Netherlands
price CSV -- every episode, the accepted cost of the env_factory.py design
decision above), not TD3's own gradient-step cost; this is flagged as a
caveat on the number in `00_lab_log.md`, not silently absorbed into the
headline steps/s figure.

### `scripts/train_td3.py` (Entregable 5)

**Location:** `scripts/` -- entry point, imports from `ev2gym_thesis/rl/`.

**Purpose:** trains all 3 `TRAIN_SEEDS` sequentially (or a single seed via
`--seed`, with `--resume` support for an interrupted run), producing a
self-contained artifact directory per training seed.

**Design decision -- a manifest JSON per run, not just a saved model
file:** rejected relying on the training script's console output or the
git commit alone to reconstruct what a given checkpoint actually is.
Chosen: every run writes `manifest.json` alongside the model, capturing
the git commit, config path, reward/state function names, every
hyperparameter, timesteps, training seed, wall-clock, and library
versions -- so a checkpoint found months later is self-describing, not
dependent on remembering which commit produced it.

`scripts/train_td3.py:131-146`

```python
    manifest = {
        "run_name": name,
        "algorithm": "TD3",
        "algorithm_family": "rl",
        "train_seed": seed,
        "git_commit": get_git_commit(),
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "config_path": REFERENCE_CONFIG_PATH,
        "reward_function": DEFAULT_REWARD_FN.__name__,
        "state_function": DEFAULT_STATE_FN.__name__,
        "sample_mode": "round_robin",
        "train_days_pool_size": len(TRAIN_DAYS),
        "total_timesteps": config_rl.TOTAL_TIMESTEPS,
        "wall_clock_s": round(wall_clock_s, 2),
        "wall_clock_min": round(wall_clock_s / 60, 2),
        "resumed_from": resume_checkpoint,
```


**Design decision -- resumable via `--resume`, not restart-only:**
rejected treating an interrupted ~55-minute-per-seed run as a total loss.
`--resume <checkpoint.zip>` reloads the model and its `VecNormalize`
statistics (failing loudly per `eval_utils.load_trained_agent` if the
stats file is missing, same guard as evaluation) and continues training
for the remaining timesteps with `reset_num_timesteps=False`, so the
learning-curve CSV and checkpoint numbering stay continuous across the
interruption rather than restarting from zero.

**Walkthrough:** in practice all 3 seeds completed without needing
`--resume` (167.6 min total, see `00_lab_log.md`), so this path was
exercised only in testing, not in the real run -- worth stating plainly
rather than implying it was needed and silently wasn't.

### `scripts/evaluate_rl.py` (Entregable 6)

**Location:** `scripts/` -- entry point, mirrors
`scripts/backfill_registry.py`'s structure (dry-run by default,
`--execute` to actually run, pre-check against existing registry keys
before simulating).

**Purpose:** evaluates all 3 TD3 checkpoints plus a `RandomPolicy`
negative control on the same 50-cell grid used for AFAP/Round Robin,
appending `algorithm_family="rl"` rows to `results/master_results.csv`.

**Design decision -- one algorithm name per training seed, to resolve a
registry key collision:** `DEDUP_KEY_COLUMNS = (config_name, algorithm,
seed, eval_day)` uses the SCENARIO seed (`SEEDS`), not the training seed --
with 3 training seeds sharing one algorithm name, their rows would collide
under the same dedup key. Rejected alternative: adding `train_seed` to
`DEDUP_KEY_COLUMNS` (rejected because it would change `REGISTRY_COLUMNS`'
schema, which the Week 3 brief explicitly said to avoid without asking
first). Chosen: `TD3_vanilla_ts100`/`_ts101`/`_ts102` as three distinct
algorithm names, with the training seed still recorded in `notes` for
traceability.

`scripts/evaluate_rl.py:53-63`

```python
# DEDUP_KEY_COLUMNS = (config_name, algorithm, seed, eval_day) uses the
# SCENARIO seed, not the training seed -- so a single "TD3_vanilla"
# algorithm name would collide across all 3 training seeds on every
# (seed, eval_day) cell. Each training seed gets its own algorithm name
# instead.
TD3_ALGORITHMS = [
    ("TD3_vanilla_ts100", 100, f"{MODELS_DIR}/TD3_vanilla_ts100/final_model.zip"),
    ("TD3_vanilla_ts101", 101, f"{MODELS_DIR}/TD3_vanilla_ts101/final_model.zip"),
    ("TD3_vanilla_ts102", 102, f"{MODELS_DIR}/TD3_vanilla_ts102/final_model.zip"),
]
RANDOM_POLICY_ALGORITHM = "RandomPolicy"
```


**Real bug found and fixed during this deliverable, recorded because "it
ran without error" was not "it was correct" -- exactly Week 2's
`f05`/`f07` experience, repeating here for a different reason:** the
original TD3 evaluation stepped episodes through
`VecNormalize(DummyVecEnv([env]))`. SB3's `DummyVecEnv` auto-resets its
underlying env INSIDE the same `step()` call that returns the terminal
transition (standard VecEnv semantics -- the point is that the next
`reset()` call isn't needed) -- so by the time external code read
`env.current_power_usage` after the episode loop to save a timeseries,
the env had already been silently reset to a fresh, all-zero state. This
was caught by `f01_power_profile.png`'s mandatory visual QA: TD3's plotted
power curve was flat at zero for the entire reference day, even though
that exact cell's own registry row correctly reported 13 EVs served.
Confirmed empirically before writing the fix, not guessed at:
`env.current_power_usage.sum()` was `0.0` and `env.current_step` was `0`
immediately after the episode loop, while the auto-preserved `info` dict's
`total_ev_served` was still correctly `13` -- because SB3 preserves the
pre-reset info dict specifically for this reason, the registry's SCALAR
metrics were never affected by this bug, only the SAVED TIMESERIES were.

Rejected fix: patching around the auto-reset (e.g. reading state one step
earlier, or disabling `DummyVecEnv`'s auto-reset via a subclass). Chosen
fix: bypass the `VecEnv`/`VecNormalize` wrapper entirely for evaluation
rollouts -- step the raw `EV2Gym` env directly (identical to how
`RandomPolicy` was already being evaluated) and manually apply the loaded
`VecNormalize`'s observation normalization before each `model.predict()`
call. Confirmed to produce IDENTICAL scalar stats to the original
VecEnv-based stepper (same deterministic policy, same environment -- only
the timeseries-corrupting side effect changes), so no previously-reported
number needed correcting, only the corrupted timeseries files (all 150 for
the 3 TD3 checkpoints) needed regenerating.

`scripts/evaluate_rl.py:131-148`

```python
    def __init__(self, model, venv, env, scenario_seed: int):
        self.model = model
        self.venv = venv  # loaded VecNormalize instance, used only for its normalize_obs() stats -- never stepped
        self.env = env
        self.scenario_seed = scenario_seed

    def reset(self):
        obs, _ = reset_for_evaluation(self.env, self.scenario_seed)
        return obs

    def act(self, obs):
        norm_obs = self.venv.normalize_obs(obs)
        action, _ = self.model.predict(norm_obs, deterministic=True)
        return action

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        return obs, reward, (terminated or truncated), info
```


**Walkthrough:** `_TD3Stepper.act` normalizes the raw observation manually
via `venv.normalize_obs(obs)` (the loaded `VecNormalize` instance's own
method, used here purely for its stored statistics, never for stepping)
before calling `model.predict(..., deterministic=True)`; `.step` then
steps the raw `env` directly, so `env.current_power_usage`,
`env.transformers`, and `env.charging_stations` all remain live and
readable for timeseries capture at every step, including the last one.

**Second, more serious bug in the same file, found 2026-08-18 (Week 4
preflight, fixed on `semana-3`): the SCENARIO itself, not just post-episode
timeseries capture, was wrong for all 200 evaluation episodes.**
`_TD3Stepper.reset()` and `_RandomPolicyStepper.reset()` both called
`env.reset()` (the latter passed `seed=None` explicitly, on the documented
but incorrect belief that "the scenario seed already applied via `make_env`'s
`EV2Gym(seed=...)`"). `EV2Gym.reset(seed=None)` draws a **fresh**
`np.random.randint(0, 1_000_000)` and regenerates `self.EVs_profiles` from
scratch -- it does not fall back to the construction-time seed. Reproduced
directly:

```
construction (seed=0, 2022-01-17): 14 EVs, first arrival/departure (11, 37), (11, 32), (11, 36)
after stepper.reset() [no seed]:   16 EVs, first arrival/departure (14, 33), (15, 38), (15, 41)
after env.reset(seed=0) explicit:  matches construction exactly
```

So every one of the 200 TD3/RandomPolicy evaluation episodes ran against
an uncontrolled, re-randomized scenario instead of its registered `(SEEDS x
EVAL_DAYS)` cell -- corrupting the scalar stats themselves this time, not
just the timeseries (contrast with the bug above). `scripts/backfill_registry.py`
(AFAP/Round Robin) was checked with the identical population-diff method,
not assumed correct: confirmed unaffected, since it already re-calls
`env.reset(seed=seed)` explicitly.

**Rejected fix: patching `.reset()` in each of the two stepper classes.**
Rejected because that is two chances to make the same mistake again, and
Week 4 was about to add a third (an oracle stepper). **Chosen fix: a single
shared helper, `env_factory.reset_for_evaluation`, that every stepper must
call instead of `env.reset()` directly** -- it requires `scenario_seed`
explicitly and asserts (not comments) that the post-reset EV population
matches construction.

`ev2gym_thesis/rl/env_factory.py:66-110`

```python
def _ev_population_signature(env) -> list:
    """A comparable summary of the EV arrival scenario an env instance
    currently holds. Used only to verify reset_for_evaluation's determinism
    guarantee, not a general-purpose utility."""
    return [
        (ev.time_of_arrival, ev.time_of_departure, ev.battery_capacity, ev.desired_capacity)
        for ev in env.EVs_profiles
    ]


def reset_for_evaluation(env, scenario_seed: int):
    """The only sanctioned way to start an evaluation episode on an env built
    by make_env(). Every evaluation stepper (TD3, RandomPolicy, and the
    Week 4 oracle's) must call this instead of env.reset() directly.

    Week 3 correction (see thesis_docs/chapters/00_lab_log.md): plain
    gymnasium Env.reset(seed=None) -- which is what env.reset() and
    env.reset(seed=None) both do -- makes EV2Gym draw a FRESH
    np.random.randint(0, 1_000_000) and regenerate self.EVs_profiles from
    scratch; it does NOT fall back to reusing the seed the env was
    constructed with. scripts/evaluate_rl.py's _TD3Stepper and
    _RandomPolicyStepper both called reset this way, so all 200 of Week 3's
    TD3/RandomPolicy evaluation episodes silently ran against a
    re-randomized scenario instead of the (config, day, scenario_seed) cell
    their registry row claims -- confirmed empirically (14 EVs at
    construction vs. 16 EVs with completely different arrival/departure
    times, after one bare env.reset()).

    The population check below is a real, always-on assertion, not a
    comment -- the entire point of this bug is that "the code looks right"
    was already tried once and was wrong. scripts/backfill_registry.py's
    AFAP/Round Robin runs were unaffected (they already pass seed=seed
    explicitly), confirmed with the same population-diff method.
    """
    construction_population = _ev_population_signature(env)
    obs, info = env.reset(seed=scenario_seed)
    post_reset_population = _ev_population_signature(env)
    assert post_reset_population == construction_population, (
        f"reset_for_evaluation: EV population after reset(seed={scenario_seed}) "
        f"does not match the population env was constructed with -- the "
        f"evaluated scenario would silently diverge from the (config, day, "
        f"scenario_seed) cell this run is registered under. This is exactly "
        f"the Week 3 bug documented in 00_lab_log.md; do not bypass this check."
    )
    return obs, info
```


**Walkthrough:** `_ev_population_signature` reduces an env's current
`EVs_profiles` to a comparable list of `(arrival, departure, battery
capacity, desired capacity)` tuples. `reset_for_evaluation` snapshots that
signature before resetting, resets with the real seed, snapshots again, and
asserts equality -- so if a future call site ever bypasses the explicit
seed again, the assertion fires on the very first evaluation episode
instead of silently corrupting 200 registry rows a second time. Both
`_TD3Stepper.reset()` and `_RandomPolicyStepper.reset()` were changed to
call this helper (each now stores `scenario_seed` as an attribute to do
so); neither calls `env.reset()` directly any more.

**Also removed as part of this correction:** `ev2gym_thesis/rl/eval_utils.py`'s
`run_episode` function, whose docstring claimed it was "used for every
Entregable 6 evaluation run." Grepped: zero call sites anywhere in the
repo -- dead code, superseded by `_TD3Stepper`/`_run_and_capture`, deleted
rather than left as a false claim.

### `scripts/analyze_rl_results.py` (Entregable 7)

**Location:** `scripts/` -- entry point, writes
`results/rl_vs_baseline_bootstrap.csv` and
`results/rl_train_seed_dispersion.csv`.

**Purpose:** paired bootstrap of each TD3 training seed against AFAP and
Round Robin, plus a cross-training-seed dispersion analysis.

**Design decision -- reuse `stats_utils.paired_bootstrap_ci` (already
written and tested in Week 2), write no new bootstrap code:** the pairing
logic (resample matched `(seed, eval_day)` cells together, not independent
samples) is identical to what Week 2's figures already needed -- there was
no RL-specific reason to reimplement it.

**Design decision -- cross-training-seed dispersion reported as a
SEPARATE analysis from the scenario-level confidence intervals, not
folded into them:** these are two genuinely different questions. "How much
does one training seed's measured performance vary across the 50
evaluation cells" (scenario dispersion, captured by the paired-bootstrap
CI) is not the same question as "how much does the AVERAGE over those 50
cells itself vary across 3 independent training runs" (training-seed
dispersion). Pooling them into one number would understate the real
uncertainty -- reporting only the scenario-level CI for one arbitrarily
chosen training seed would hide the fact that a different training seed's
CI can be centered on a visibly different value.

`scripts/analyze_rl_results.py:89-103`

```python
    dispersion_report = []
    for metric in METRICS:
        per_seed_means = []
        for algo in TD3_ALGOS:
            vals = np.array([r[metric] for r in grid if r["algorithm"] == algo and r[metric] is not None])
            per_seed_means.append(float(np.mean(vals)))
        per_seed_means = np.array(per_seed_means)
        spread = per_seed_means.max() - per_seed_means.min()
        rel_spread_pct = (spread / abs(per_seed_means.mean()) * 100) if per_seed_means.mean() != 0 else float("nan")
        dispersion_report.append({
            "metric": metric,
            "mean_ts100": per_seed_means[0], "mean_ts101": per_seed_means[1], "mean_ts102": per_seed_means[2],
            "spread_max_minus_min": spread, "std_across_seeds": per_seed_means.std(),
            "relative_spread_pct": rel_spread_pct,
        })
```


**Walkthrough:** for each metric, the 3 training seeds' per-metric means
are collected into a 3-element array; `spread` (max-min) and `std` are
reported alongside a `relative_spread_pct` normalized against the mean
across seeds. One metric (`total_transformer_overload`) produces a
misleadingly large relative-spread number (300%) purely because two of the
three seeds are exactly `0.0` -- flagged explicitly in `00_lab_log.md`
as a division-by-near-zero artifact, not reported as a literal claim.

### `ev2gym_thesis/registry_analysis.py` (Week 2 -> Week 3 contract change)

**Location:** `ev2gym_thesis/` -- shared by `scripts/make_figures.py` and
`scripts/analyze_rl_results.py`.

**Purpose:** `main_grid_rows()` filters the registry down to the balanced
evaluation grid, excluding the Week 1 single-day historical rows and the
grid smoke test.

**Design decision -- filter by an explicit exclusion-marker set, not by
"notes is non-empty":** Week 2's original implementation filtered by
`notes == ""`, which happened to work because Weeks 1-2 only ever used
`notes` for exactly two special-case markers (`week1_reference_day`,
`pipeline_smoke_test_grid`) -- "notes is empty" and "notes is not one of
these two markers" were indistinguishable at the time. Week 3's RL rows
break that coincidence: they legitimately use non-empty `notes` for real
grid-row metadata (reward/state/train_seed, required by
`03_rl_baseline.md` S3.5's registry-comparability rule), so the old filter
silently excluded all 200 new RL rows from every figure and analysis.
Rejected alternative: giving RL rows empty `notes` and tracking
reward/state/train_seed some other way -- rejected because `notes` is the
schema's designated place for exactly this kind of per-row metadata, and
the Week 3 brief explicitly said not to add new registry columns without
asking first.

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


**Walkthrough:** verified this change two ways before trusting it: (1) the
two Week 1 reference rows (`notes="week1_reference_day"`) and the grid
smoke test row are still correctly excluded after the change (checked
directly: `week1_reference_day` rows found = 2, matching the known Week
1/2 count); (2) `station_v0_bogota` now returns exactly 300 main-grid rows
(50 cells x 6 algorithms: AFAP, Round Robin, 3 TD3 seeds, RandomPolicy),
not 100 (which is what the old, broken filter would have returned). Also
confirmed this change does NOT affect
`scripts/measure_degradation_by_ambient.py`, which has its own independent
inline `notes == ""` filter, not a call into `main_grid_rows` -- so Week
2's degradation-by-ambient results are unaffected by this contract change.

### `ev2gym_thesis/figures.py` -- `total_reward` guardrail (Entregable 3) and `ALGORITHM_STYLE` additions

**Location:** `ev2gym_thesis/figures.py`, the same Week 2 module that
already holds `ALGORITHM_STYLE`/`write_caption`.

**Purpose:** Weeks 1-2's heuristic rows and Week 3's RL rows do not share
a reward function (AFAP/Round Robin used the environment's default,
TD3/RandomPolicy used `SqTrError_TrPenalty_UserIncentives`), so
`total_reward` is not a comparable quantity between them -- comparing it
anyway would silently plot apples against oranges under one shared axis
label.

**Design decision -- a guardrail function called at the top of every
per-metric plotting loop, not a one-time check:** rejected relying on
remembering not to add `total_reward` to `METRICS_FOR_BARS`. Chosen: a
function that no-ops for every metric except `total_reward`, and raises if
`total_reward` rows mix reward functions, wired into
`scripts/make_figures.py`'s `f02`/`f05`/`f07` per-metric loops. Currently
inert (no figure plots `total_reward` yet), but fails loudly the moment
anyone adds it without checking -- a guardrail against a future mistake,
not a fix to an existing bug.

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


**Walkthrough:** `_reward_fn_name` reads the `reward=...` marker out of a
row's `notes` field, falling back to the environment's own default name
for rows with no such marker (Weeks 1-2's heuristic rows). The guardrail
then just checks whether more than one distinct reward-function name
appears among the rows being compared.

`ALGORITHM_STYLE` gained 4 new entries this week
(`TD3_vanilla_ts100/101/102`, `RandomPolicy`) by append only, per the
project's standing convention -- AFAP's and Round Robin's existing
color/marker were not touched. Three distinct shades of green were chosen
for the 3 TD3 seeds (same algorithm, different training runs -- grouped by
hue, distinguished by marker) and a neutral gray for the random-policy
control, so it never visually competes with the algorithms actually being
compared.

### `scripts/make_figures.py` -- `f08` activated, 5 real bugs found by visual QA (Entregable 7)

**Location:** `scripts/make_figures.py` -- the same Week 2 entry point,
extended in place.

**Purpose:** `f08_learning_curves` was an inert stub since Week 2
(correctly skipping until `algorithm_family=="rl"` rows existed).

**Design decision -- `f08` reads each training run's own
`learning_curve.csv` directly, not the main registry:** the registry has
no reward-vs-timesteps time series column (each row is one completed
run's final stats, not a training trajectory). Same pattern `f09` already
established for `results/degradation_by_ambient.csv` -- a figure reading
its own separate, non-registry source file when the registry schema
genuinely doesn't fit the data.

**Visual QA is mandatory, not optional -- "ran without error" was not "was
correct" for 5 of this week's figures**, matching (and exceeding) Week 2's
own experience with `f05`/`f07`:

1. **TD3 timeseries were entirely zeroed out** (`f01_power_profile.png`).
   Root cause and fix already described in full under
   `scripts/evaluate_rl.py` above -- not repeated here.
2. **`f02_metrics_bars` and `f04_distributions`: x-axis labels overlapped
   into an unreadable run-on string.** 6 algorithm names (AFAP, Round
   Robin, 3 TD3 seeds, RandomPolicy) at a font size and figure width sized
   for 2. Fixed with rotated labels (`f02`) and rotated labels plus a
   width that scales with algorithm count (`f04`, `figsize=(max(6, 1.3 *
   len(algos)), 4.5)`).
3. **`f05_vs_baseline`: title text was clipped at the figure's right
   edge**, and had large, ever-growing wasted top/bottom margins. Same
   underlying failure mode as Week 2's title-cutoff bug, different
   trigger -- Week 2's fix (widen the figure) doesn't generalize, because
   this time the title itself grew (it enumerated 5 algorithm names
   instead of 1) while `fig.subplots_adjust`'s margins were fixed
   FRACTIONS of a figure whose height now scales with algorithm count (25
   rows instead of 5), so 15% of a much taller figure is a much larger
   absolute blank margin. Fixed two ways: the title no longer enumerates
   every algorithm by name (the per-row y-axis labels already carry
   `(algorithm)` whenever more than one non-baseline algorithm is
   present, making the title's list redundant), and margins are now fixed
   INCHES (converted to a fraction of the actual figure height at
   creation time), not fixed fractions.
4. **`f06_size_sensitivity`: TD3/RandomPolicy appeared as disconnected
   single dots at the 8-port reference point only.** They were never run
   across the station-size sweep -- a declared Week 3 scope limitation
   (the CPU budget didn't cover training across sizes too) -- so plotting
   them on a "sensitivity vs. port count" figure implied a size trend that
   doesn't exist. Fixed by restricting this figure to algorithms actually
   present on a non-reference sweep config (`station_n02_tx100`), which
   naturally excludes TD3/RandomPolicy without hardcoding their names --
   any future algorithm that similarly skips the size sweep is
   automatically excluded too.

**Walkthrough (bug 3, the most involved fix):** the fix computes
`top_margin_in`/`bottom_margin_in` as fixed inch quantities (0.7in/0.6in)
and converts them to `fig.subplots_adjust(top=1 - top_margin_in /
fig_height, bottom=bottom_margin_in / fig_height)` at the point `fig_height`
is actually known -- so the absolute blank space stays roughly constant
whether the figure has 5 rows or 25.

### `ev2gym_thesis/tests/test_rl_infrastructure.py` (Entregable 9)

**Location:** `ev2gym_thesis/tests/`, alongside Week 2's
`test_stats_utils.py`/`test_degradation_bogota.py`.

**Purpose:** originally 8 tests covering the RL infrastructure added this
week; **10 as of the 2026-08-18 correction** (2 added, see below).

**Design decision -- deliberately independent of whether a real trained
model exists yet:** rejected writing these tests against Entregable 5's
actual trained checkpoints (which wouldn't exist until after the
Entregable 4 confirmation gate, and would make the tests only runnable
post-training). Chosen: fresh, untrained `TD3` instances (built with a
tiny `net_arch` for speed) are enough to test the infrastructure's
correctness -- reproducibility, leakage-prevention, and fail-loudly
behavior don't depend on the model actually having learned anything. This
is why these tests could be (and were) run and passing before training
ever started.

**Walkthrough:** the 4 original test classes cover, respectively: (1)
`TRAIN_SEEDS`/`SEEDS` and `TRAIN_DAYS`/`EVAL_DAYS` disjointness (pins the
values the module-level assertions were checked against, so a future edit
that silently narrows either pool without breaking disjointness still gets
caught); (2) `TrainingDayCyclingEnv` never sampling an `EVAL_DAYS` date,
in both `round_robin` and `random` modes, over enough resets to exercise a
full lap-plus-wraparound of `TRAIN_DAYS`; (3) `load_trained_agent` raising
`FileNotFoundError` when the `VecNormalize` stats file is absent; (4)
evaluation reproducibility.

**Correction, 2026-08-18: item (4) was a green test that certified the
exact property that turned out to be violated in production, and this is
worth explaining in full rather than quietly fixing.** Its original claim
-- *"the same `(config, scenario_seed, eval_day, model)` evaluated twice
via the same deterministic-predict loop produces byte-identical stats"* --
was TRUE of the test's own code, and FALSE of `scripts/evaluate_rl.py`'s
actual `_TD3Stepper`, which is exactly the contradiction that exposed the
bug above. Diagnosis: the test built its own hand-rolled `run_once(env)`
loop calling `env.reset(seed=seed)` directly -- a correct call, but a
**parallel reimplementation** of the evaluation loop, never the
`_TD3Stepper`/`_run_and_capture` objects `scripts/evaluate_rl.py` actually
runs in production. It certified "deterministic scenario generation, when
you pass the seed correctly" -- never in question -- not "the production
stepper passes the seed correctly" -- the actual bug. **General rule
extracted and applied project-wide:** every test in this project must
exercise the real call path used in production, not a lookalike of it.
The other 7 (now 9) tests were audited against this rule and found clean
(each already calls the real production class/function directly -- see
`00_lab_log.md`'s 2026-08-18 entry for the full per-test audit). Fixed by
rewriting the test to construct and call `scripts.evaluate_rl._TD3Stepper`
and `_run_and_capture` directly. Two new tests added:
`TestResetForEvaluation.test_reset_for_evaluation_reproduces_construction_scenario`
(pins the fix at the smallest grain) and
`test_bare_reset_would_have_diverged` (pins the failure mode itself, so a
future change to EV2Gym's upstream `reset()` semantics would be flagged,
not silently made moot).

## Library Choices (additions this week)

| Library | Used for | Why this one | Rejected alternative |
|---|---|---|---|
| `stable-baselines3` (2.9.0) | TD3 implementation, `VecNormalize`, `CheckpointCallback`, `Monitor` | The project's existing Week 3 preflight already confirmed `EV2Gym` is fully Gymnasium-API-compliant with no shim needed; SB3 is the standard, actively maintained implementation the source papers themselves build on (PI-TD3 extends TD3's SB3-style actor-critic update). A real pipeline dependency (unlike `gurobipy`), added to `requirements.txt`. | Writing TD3 from scratch -- rejected as unnecessary reimplementation risk for a well-established algorithm; a custom RL library -- rejected, no reason to maintain one for a single algorithm. |
| `torch` (>=2.8, CPU) | SB3's backend | Already present in the environment (SB3's own dependency); CPU-only per the confirmed CPU-only training budget -- no GPU was used or assumed. | -- |

## References (additions this week)

**[Primary]**

- Fujimoto, S., van Hoof, H., and Meger, D. (2018), "Addressing Function
  Approximation Error in Actor-Critic Methods" (the TD3 paper) -- cited for
  the algorithm's namesake mechanisms (delayed policy updates, target
  policy smoothing, twin critics), its default network architecture
  ([400, 300], confirmed still SB3's own default by reading
  `stable_baselines3/td3/policies.py:141-145` directly), and its
  exploration-noise recipe (N(0, 0.1) Gaussian action noise).
- Stable-Baselines3 documentation and source (`stable_baselines3==2.9.0`,
  installed in this environment) -- every `"SB3 default"` label in this
  document's Part 1 table and `config_rl.py` was confirmed by reading the
  installed package's own source (`td3/td3.py`, `td3/policies.py`,
  `common/off_policy_algorithm.py`, `common/callbacks.py`), not recalled
  from documentation that might be stale relative to this exact version.

**Cross-reference:** the PI-TD3 paper (`pi_td3_paper.pdf`) and its
Algorithm 1 / reward Eq. 14 are the basis for Week 4's planned physics-informed
ablation on top of this week's vanilla-TD3 wrapper -- not implemented this
week, referenced here only to record why TD3 (not SAC) was chosen as this
week's vanilla baseline (S3.1 of `thesis_docs/chapters/03_rl_baseline.md`).

## Headline Results Summary

**Corrected 2026-08-18 -- this section previously reported a conclusion
the corrected data does not support; see the correction note at the top of
this document and `03_rl_baseline.md` S3.11.** Full tables, the
paired-bootstrap comparison, and the cross-training-seed dispersion
analysis are in `thesis_docs/chapters/03_rl_baseline.md` (sections
3.8-3.11) and `00_lab_log.md`'s 2026-08-18 entry -- not repeated in full
here to avoid drift between two copies of the same numbers.

Corrected headline: TD3 reduces transformer overload relative to unmanaged
AFAP (significant for 2 of 3 seeds) but is significantly **worse** than
Round Robin on overload for all 3 seeds (was reported as matching it).
The random-policy control -- corrected -- shows significantly **lower**
overload than AFAP (0.22 kWh vs. AFAP's 5.33 kWh) and is statistically
indistinguishable from TD3 (seed 100); it no longer supports "TD3 learned
a real overload-avoidance behavior beyond naive throttling," which was
this chapter's original headline claim. `total_ev_served` is now
identical across every algorithm (the "lower/seed-inconsistent" finding
was itself a correction-era artifact). `min_energy_user_satisfaction`
remains a real cost and is now larger than originally reported (down to
78.3% for the worst seed, vs. the pre-correction 86.7%). Training itself
is unaffected by this correction: wall-clock 2.79h total (3 seeds),
matching the calibration estimate almost exactly; learning curves show a
weak-but-consistent positive trend across all 3 seeds, not clean
convergence -- reported as the legitimate result of the declared reduced
training budget, not adjusted or hidden.
