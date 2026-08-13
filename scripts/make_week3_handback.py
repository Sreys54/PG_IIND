"""
Builds thesis_docs/Week3_Parameter_Method_and_Implementation_Justification.md
by extracting code excerpts fresh from source (via scripts/build_week_doc.py)
every time it runs -- the document can never quote code that no longer
exists, same convention as scripts/make_week2_handback.py.

Usage: PYTHONPATH=. python scripts/make_week3_handback.py
Then:  PYTHONPATH=. python scripts/render_docx.py thesis_docs/Week3_Parameter_Method_and_Implementation_Justification.md thesis_docs/Week3_Parameter_Method_and_Implementation_Justification.docx
"""
import datetime

from scripts.build_week_doc import get_snippet
from ev2gym_thesis.registry import get_git_commit

OUT_PATH = "thesis_docs/Week3_Parameter_Method_and_Implementation_Justification.md"


def code_block(tag: str) -> str:
    s = get_snippet(tag)
    return (
        f"`{s['file']}:{s['start_line']}-{s['end_line']}`\n\n"
        f"```python\n{s['code']}\n```\n"
    )


def build_document() -> str:
    commit = get_git_commit()
    generated = datetime.datetime.utcnow().isoformat() + "Z"

    parts = []
    parts.append(f"""# Week 3 — Parameter, Method, and Implementation Justification

**Git commit:** `{commit}`
**Generated:** {generated} (regenerate with `PYTHONPATH=. python scripts/make_week3_handback.py` after any code change -- this document is built, not hand-maintained)

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
""")

    # -----------------------------------------------------------------
    # Part 1
    # -----------------------------------------------------------------
    parts.append("""## Part 1 -- Parameters and Methods

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
""")

    # -----------------------------------------------------------------
    # Part 2
    # -----------------------------------------------------------------
    parts.append(f"""## Part 2 -- Implementation

### `ev2gym_thesis/eval_protocol.py` (extended, not rewritten)

**Purpose:** adds `TRAIN_SEEDS`, disjoint-asserted against `SEEDS` at import
time, mirroring the `TRAIN_DAYS`/`EVAL_DAYS` disjointness already in place
from Week 2.

{code_block("train_seeds")}

{code_block("train_seeds_disjoint_assert")}

### `ev2gym_thesis/rl/` (new subpackage -- `ev2gym/rl_agent/*.py` was never touched)

**`env_factory.py`** -- environment construction for both training and
evaluation, using `config_utils.make_day_config` (Week 2's mechanism), so
RL and the Week 1-2 heuristics see identical scenarios on shared
(config, day, seed) cells.

{code_block("make_env")}

`TrainingDayCyclingEnv` samples a new day from `TRAIN_DAYS` (never
`EVAL_DAYS`) every `reset()`, since `EV2Gym` cannot vary its simulated day
across resets of the same instance without `config['random_day']=True`
(which samples uniformly across ~1.5 years, not restricted to `TRAIN_DAYS`):

{code_block("training_day_cycling_env_init")}

{code_block("training_day_cycling_env_sampling")}

**`config_rl.py`** -- every TD3 hyperparameter with a declared origin
(`"SB3 default"`, `"TD3 paper"`, or `"set for this project's CPU budget"`,
verbatim per constant):

{code_block("td3_hyperparams")}

{code_block("timesteps_confirmed")}

**`callbacks.py`** -- periodic checkpointing (resumable training) and a
CSV learning-curve log independent of stdout:

{code_block("make_checkpoint_callback")}

{code_block("learning_curve_callback")}

**`eval_utils.py`** -- loading a trained checkpoint for evaluation, refusing
to proceed silently if the VecNormalize statistics file is missing (the
classic bug that makes an agent "work in training, collapse in
evaluation"):

{code_block("load_trained_agent")}

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
`experiments/phase2_algorithms/models/TD3_vanilla_ts{{seed}}/manifest.json`.

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

{code_block("run_episode")}

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

{code_block("non_grid_notes_markers")}

Verified this does not affect `scripts/measure_degradation_by_ambient.py`,
which has its own independent inline `notes == ""` filter, not a call into
`main_grid_rows`.

### `ev2gym_thesis/figures.py` -- `total_reward` cross-family guardrail (Entregable 3) and `ALGORITHM_STYLE` (append-only)

Weeks 1-2's heuristic rows and Week 3's RL rows do not share a reward
function, so `total_reward` is not a comparable quantity between them.
This guardrail raises if a figure ever tries to compare it across rows
with different reward functions:

{code_block("total_reward_guardrail")}

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
""")

    return "\n".join(parts)


if __name__ == "__main__":
    content = build_document()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {OUT_PATH} ({len(content)} characters)")
