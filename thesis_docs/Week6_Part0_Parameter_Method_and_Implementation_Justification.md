# Week 6, Part 0 — Parameter, Method, and Implementation Justification: Extended Training of the Selected RL Policy

**Status: complete (2026-09-28). The final-model decision was taken by the
author on 2026-10-05: seed 102 extended, primary checkpoint (see below).** This document follows the Week 5
mechanism: a hand-maintained Markdown record rendered to `.docx` by
`scripts/render_docx.py` (plain black text, bold section titles, no Word
Heading styles). No `scripts/make_week5_handback.py` exists in the repo, so
none was mirrored.

**Scope.** At the advisor's request, the best already-trained RL arm was
trained until its learning curve stabilised, so that a single RL model can
be carried into Objectives 4 and 5. This is Part 0 of Week 6 and precedes
the grid-enabled (IEEE 34-bus) phase. `simulate_grid` stays `False`, and
nothing in `ev2gym/models/` or `ev2gym/rl_agent/` was touched.

## Headline Results Summary

**Verdict: extended training degraded the model on its pre-registered
selection criterion.**

- **Tracking error.** All three training seeds met the convergence rule
  (at 380k, 560k and 810k steps) and stopped by themselves after 2.2–3.7 h.
  In every seed, though, the plateau they converged to has a higher
  validation tracking error than the policy had at 30k–70k steps. On the
  final 100-cell test grid, the extended primary checkpoints have 33%
  higher tracking error than the new run's own 60,000-step checkpoints:
  +10,701, 95% cluster-bootstrap CI [+9,042, +12,472], n_clusters = 50.
- **Transformer overload.** Statistically unchanged (+0.74 kWh, CI
  [−1.98, +3.40]).
- **User outcomes.** These improved:
  - average satisfaction +1.8 points;
  - minimum energy satisfaction 83 → 95;
  - `ENS_rel` from 3.9–20.0% to 1.6–2.2%.
- **Per seed.** Tracking error is worse than the same seed's 60k
  checkpoint for all three seeds: +13,241 / +10,243 / +8,620, every CI
  excluding zero, n_clusters = 50. The convergence rule detected a plateau,
  not an improvement.
- **Seed spread (corrected 2026-10-05).** The spread shrank for user
  outcomes. Average satisfaction range went from 3.22 to 0.11 pp, and
  `ENS_rel` range from 16.13 to 0.59 pp. For tracking error the range is
  marginally tighter (8.3% → 7.3% relative) around a worse value, and for
  overload it widened (30.8% → 82.9%).
- **Interpretation, verified.** The extended policies deliver more energy
  (+18.6 kWh/day [+15.9, +21.2]) and score a **better** total training
  reward (+3,997 [+2,340, +5,790]). Extended training optimised its own
  reward, which values satisfaction over tracking. The wording "rather than
  reaching a better reward" is not supported by the data and is not used.
- **Budget.** RL was not budget-limited at 60,000 steps. Round Robin has
  lower tracking error and overload than every implementable arm (all CIs
  exclude zero). For the one arm extended to about 14× its budget, the gap
  is not a budget artefact. **The Round Robin recommendation stands.**
- **Final model (author's decision, 2026-10-05).** `TD3_vanilla` extended,
  **training seed 102, primary checkpoint at 850,000 steps** (validation
  tracking error 40,378, against 42,531 for seed 100 and 46,554 for seed
  101). Model:
  `experiments/phase2_algorithms/models/TD3_vanilla_extended_ts102/checkpoints/td3_vanilla_extended_ts102_850000_steps.zip`,
  with `..._vecnormalize.pkl` beside it. It is kept for four reasons:
  - the advisor asked for one stabilised model;
  - it has the lowest overload of all 15 TD3 checkpoints (3.58 kWh/day);
  - its `ENS_rel` is 2.20% and its average satisfaction 99.59%;
  - it is the longest-trained seed.

  Accepted trade-off: test tracking error of 41,195, against 32,575 at its
  own 60k checkpoint (+8,620 [+6,877, +10,419]).

## Part 1 — Parameters and Methods

| Parameter / decision | Value | Label | Justification |
|---|---|---|---|
| Model extended | `TD3_vanilla` (`SqTrError_TrPenalty_UserIncentives`), training seeds 100/101/102 | Empirically set | S5.8 names no trained winner, and no RL arm beat Round Robin in Week 5. `TD3_vanilla` is the best RL arm on S5.6's tracking-error ranking (arm mean 33,447 against 34,596) and on overload (4.72 against 8.26 kWh). Confirmed by the author at Gate 1. It is the best RL arm, not an overall winner. |
| Hyperparameters, reward, state, config | Unchanged from `config_rl.py` / `train_td3.py` ([64, 64] network, lr 1e-3, batch 256, buffer 50,000, learning_starts 500, tau 0.005, gamma 0.99, policy delay 2, target noise 0.2/0.5, action noise σ 0.1, VecNormalize) | Validated | The brief fixes everything except budget and monitoring. `train_td3.py::build_model` is called unchanged. |
| Training from scratch | Not warm-started from the 60k checkpoints | Validated | The original replay buffers were never saved (`save_replay_buffer=False`). A from-scratch run also gives one continuous curve whose first 60k steps can be compared with the original run. |
| Three training seeds, in parallel | 100, 101, 102 as separate processes | Validated | A single stabilising seed would be anecdotal, and the thesis claim is about the method. Gate 1 timing showed 3-parallel gives the most steps per seed (86 steps/s against 37 sequential and 58 two-at-a-time, in per-seed equivalents). |
| Primary comparator | The new run's own 60k checkpoints (`TD3_vanilla_new60k_ts*`) | Validated | The original 60k models were trained before the Week 5 `generate_power_setpoints` fix and evaluated after it. The new 60k checkpoints are environment-matched. The original rows are a secondary, labelled reference (author decision at Gate 1). |
| Validation set | Seeds 1,000,000–1,000,009 × {2022-01-31 Mon, 2022-03-12 Sat} = 20 cells | Validated | Disjoint by construction. EV2Gym's unseeded training draw is `np.random.randint(0, 1000000)`, so every training scenario is below 10⁶ (pinned by a test against the library source). The set is disjoint from the evaluation seeds (0–49) and training seeds (100–102), and both dates are outside `EVAL_DAYS` and `TRAIN_DAYS`. The date affects nothing but the weekday/weekend branch. |
| Validation procedure | Every 10,000 steps: save the checkpoint, reload it with frozen VecNormalize (`training=False`, `norm_reward=False`), run deterministic `predict` on the 20 cells | Validated | Scores the exact artifact on disk, using the Week 5 evaluation settings. A test pins that the training normaliser's count equals 1 + training steps, so no validation step reached it. |
| Selection criterion | Validation-mean `tracking_error` (lower is better); overload and energy user satisfaction logged as secondary metrics | Empirically set | Author decision at Gate 1. Strictly positive (~3×10⁴), so relative convergence thresholds are meaningful without normalisation. Overload can be exactly zero, which would make relative thresholds undefined. |
| Convergence rule | W = 5 evaluations (50k steps); abs(mean(last W) − mean(prev W)) / abs(mean(prev W)) < 2% and std(last W) / abs(mean(last W)) < 5%, on 3 consecutive evaluations | Empirically set | Fixed before launch and written into S5.11 as a labelled assumption. Implemented and unit-tested as `convergence_index` (flat, drifting, oscillating, step-change and interrupted synthetic curves). Earliest possible declaration: 120k steps. |
| Confirmation margin | 100,000 steps after convergence | Empirically set | Shows the plateau holds before stopping (brief). |
| Deadline | Stop at 10:15 (UTC−5), hard deadline 10:30 Mon 2026-09-28 | Simplification | The machine was available until 11:00. The 15-minute margin covers the final validation and saves. Not reached: all seeds stopped on convergence, the last at about 04:46. |
| Checkpoint selection | Primary: best criterion at or after convergence. Sensitivity: last checkpoint. Final model: the primary of the seed with the best validation criterion | Empirically set | Fixed in advance (brief). For a non-converging seed, both best and last would have been reported and the author would choose (Gate 1 decision 8). Not needed: all seeds converged. |
| Evaluation-seed leakage guard | A training draw that lands on a seed in `SEEDS` is redrawn for the same day, and every draw is logged | Validated | Expected about 4 hits over a multi-million-step run. Implemented in `ev2gym_thesis`, not in the library. Result: 0 draws rejected and 0 contaminated episodes in 21,354 training episodes. |
| Price-table cache | `ev2gym_thesis/rl/price_data_cache.py` | Validated | About 90% of a training episode's time was EV2Gym re-parsing the ENTSO-E CSV. The cache is output-identical: a test compares prices, setpoints, power trajectory, stats and post-episode RNG state, and the calibration gave identical validation values with and without it. Training throughput went from 13.8 to 86 steps/s per seed. |
| One torch thread per process | `--torch-threads 1` | Empirically set | Fastest configuration with 3 concurrent processes. The thread count changes floating-point results, so it is fixed and recorded. |
| Replay-buffer retention | Saved every 50,000 steps, last 2 kept per seed | Simplification | Author decision. Limits OneDrive sync volume, and 2 saves are enough for resume. |
| Monitor RNG isolation | Global numpy, Python and torch generators snapshotted and restored around every validation (including `TD3.load`, which reseeds them) | Validated | EV2Gym reseeds the global generators on construction. Without this step the monitor would change the training trajectory. A test confirms identical training draws with and without the monitor. |
| Keep-awake | `SetThreadExecutionState` with `ES_CONTINUOUS` + `ES_SYSTEM_REQUIRED`, per training process | Validated | The active power plan sleeps after 300 s idle on AC, and Windows counts user input, not CPU load. The request lapses when the process exits. |
| Test evaluation | 9 arms × 50 seeds × 2 day types = 900 rows through `evaluate_rl.eval_td3` and `run_week5_grid._with_week5_fields` | Validated | The Week 5 evaluation path, not a reimplementation. The existing 2,253 registry rows were verified byte-identical afterwards. |
| Statistics | `paired_cluster_bootstrap_ci`, cluster = scenario seed, 10,000 resamples, n_clusters = 50 reported in every table | Validated | The Week 5 standard. Method-level comparisons use the per-cell mean across the 3 training seeds. |
| `ENS_rel` definition | S5.7 definition: net energy vs. AFAP, summed per seed, pass iff the CI upper bound is < 15% | Validated | The brief called it "proposed, not yet adopted", but S5.7 records its formal adoption in Week 5. The repo is the source of truth. |
| First-60k reproduction rule | The new run's 30k–60k rolling training reward lies within the range of the three original seeds' means, ± the largest original within-segment std | Simplification | A labelled comparison, not a reproduction: the environment (setpoint fix) and thread count differ, so no bitwise match is possible. Result: all 3 seeds fall within the band. |

## Part 2 — Implementation

### `ev2gym_thesis/rl/extended_training.py` (new)

**Purpose:** everything the extended run adds beyond the Week 3 training
stack:
- the validation set and `disjointness_proof()`, printed at every launch;
- `convergence_conditions_at` / `convergence_index` (the rule) and
  `select_primary_index` (checkpoint selection);
- `SeedLoggingTrainingEnv`, a `TrainingDayCyclingEnv` subclass with
  identical reset/step, plus per-episode (day, scenario seed) logging and
  the leakage guard;
- `load_frozen_checkpoint` and `run_validation`;
- `ExtendedTrainingCallback`, which handles validation, checkpointing,
  buffer rotation, the per-episode log, convergence tracking and stopping.

**Design decision: score the saved artifact, not the live model.** The
checkpoint is written first and then reloaded frozen. The number in the
validation log therefore belongs to a file that exists, with the exact
normalisation statistics saved beside it.

**Design decision: pure functions for the rule.** The convergence rule
and the selection rule take a list of numbers and return an index. That
makes them testable on synthetic curves and re-runnable on the committed
logs: `analyze_week6_part0.py` asserts that its recomputation matches the
live run's `state.json`.

### `ev2gym_thesis/rl/price_data_cache.py` (new)

**Purpose:** wraps the `load_electricity_prices` name that
`ev2gym_env.py` imported, from outside the library, so the parsed price
table is reused across EV2Gym instances. The per-date lookup is still the
library's own code, and no random number is drawn. It is opt-in
(`--price-cache`), and its output identity is pinned by a permanent test.

### `scripts/train_td3_extended.py` (new) and `scripts/run_extended_seed.cmd` (new)

**Purpose:** one training seed per process. `build_model` reuses
`train_td3.build_model` unchanged by temporarily swapping in the logging
environment. `--resume` restores the latest complete resume point: model,
VecNormalize, replay buffer, generator states, the round-robin day index
and the CSV logs, rolled back to that step. Two real bugs were caught by
the resume smoke test and fixed:
- `TD3.load` re-queues the training seed on the VecEnv (fixed with
  `_reset_seeds()`);
- concurrent processes corrupted shared per-day YAML files (fixed with
  per-process directories).

The `.cmd` launcher sets `PYTHONPATH`, unbuffered UTF-8 output and the log
paths, so a detached WMI launch has a clean, reproducible command line.

### `scripts/calibrate_extended_timing.py` (new)

**Purpose:** the Gate 1 timing matrix: 8 configurations of concurrency,
cache and thread count, 5,000 steps plus one validation each. Output:
`experiments/phase2_algorithms/results/week6_part0/timing_calibration.csv`
(+ `.xlsx`). The single-process, no-cache row (18.43 steps/s) reproduces
Week 3's 18.09 steps/s.

### `scripts/evaluate_week6_part0.py` (new)

**Purpose:** the 900-row test-grid evaluation. Checkpoint steps are read
from each run's `state.json`, never typed by hand. The budget, selected
step, selection rule and `env=post_setpoint_fix` tag are appended to the
existing `notes` field, so no new registry columns were added.

### `scripts/analyze_week6_part0.py` (new) and `scripts/analyze_week5_results.py` (parametrized)

**Purpose:** convergence table, combined validation log, master
comparison, optimality gap, cluster-bootstrap comparisons, train-seed
dispersion, target compliance and the rule's final-model selection
(`results/week6_part0_*.csv`, `results/week6_part0_final_model_selection.json`).

**Design decision: parametrize, do not copy.** Week 5's
`master_comparison_table`, `optimality_gap` and `ens_and_compliance`
hard-coded their algorithm list and output path, so reusing them as they
stood would have overwritten Week 5's CSVs. They gained optional `algos` /
`out_path` arguments whose defaults reproduce Week 5 exactly, which keeps
one implementation of each statistic.

### `scripts/make_figures.py` and `ev2gym_thesis/figures.py` (extended)

**Purpose:** `f12_extended_training_reward` (raw training-episode reward
faint, 100-episode rolling mean on top) and `f13_extended_validation`
(validation criterion plus two secondary metrics: mean across seeds with a
min–max band, seeds continuing past the shortest run drawn individually).
Both mark the 60k budget and each seed's convergence point, and f13 also
marks the selected checkpoints. `--only f12,f13` regenerates them without
touching f01–f11. Nine `ALGORITHM_STYLE` entries were appended, none
reassigned.

**Visual QA found and fixed three issues:**
- The raw reward drawn in seed 101's light teal at 12% opacity was
  invisible, and it did not match the legend, which says grey.
- The "1e3" axis offset was easy to misread; the axis now uses "k" labels.
- f13's legend had no entry for the convergence markers.

### `scripts/export_week6_part0_results_xlsx.py` (new) and `ev2gym_thesis/xlsx_export.py` (one constant added)

**Purpose:** one formatted workbook per results CSV, following Week 5's
convention: convergence, validation log, test-grid results, cluster
bootstrap, target compliance, optimality gap, seed dispersion and timing
calibration. `MIXED_UNIT_4DP_FORMAT` was added for long-format tables
whose rows carry different metrics (CLAUDE.md rule 7: add a constant
rather than a one-off format string).

### `ev2gym_thesis/tests/test_final_rl_model.py` (new)

**Purpose:** 22 tests calling production code, covering:
- the convergence rule on synthetic curves with known answers;
- seed and day disjointness, plus the EV2Gym source pin on the draw range;
- price-cache output identity;
- the monitor not changing the training trajectory;
- the resume path;
- VecNormalize saved with every checkpoint and frozen in validation, plus
  buffer rotation;
- the leakage guard;
- pins on the convergence and primary steps recomputed from the committed
  logs;
- a pin on the selected checkpoint (`TD3_vanilla_extended_ts102`, 850,000
  steps);
- a row-count pin (900 new rows, 100 per arm, 2,200 analysis rows in total).
