# Lab Log

## 2026-08-13 — Week 3, Entregables 5-7: training, evaluation, statistics, and two real bugs caught by visual QA

**Entregable 5 (training) — done.** All 3 `TRAIN_SEEDS` trained sequentially
(`scripts/train_td3.py`) at the confirmed `TOTAL_TIMESTEPS=60_000` budget.
Wall-clock: ts100=57.62 min, ts101=54.91 min, ts102=55.06 min — **167.6 min
(2.79h) total**, matching the 165.9 min calibration estimate almost exactly.
Artifacts per seed in `experiments/phase2_algorithms/models/TD3_vanilla_ts{seed}/`:
`final_model.zip`, `final_model_vecnormalize.pkl`, `learning_curve.csv`,
`manifest.json` (git commit, hyperparameters, library versions, wall-clock).

**Convergence: weak but real, not clean.** Linear-fit slope of mean episode
reward vs. timesteps is positive for all 3 seeds (+21 to +30 per 1,000
steps) — same direction every time, not coincidence — but small relative to
within-seed noise (episode-reward std ~1,000-1,500 against means of
~-22,000 to -25,000). Reported as-is: a real but weak learning signal under
the declared 2.8h-total budget (vs. the source papers' 5-48h on HPC), not
dressed up as clean convergence. See `figures/f08_learning_curves.png`.

**Bug found during smoke-testing, before the real run:** `ep_info_buffer`
(the mean-episode-reward source `LearningCurveCallback` reads) stayed empty
because the training env wasn't wrapped in
`stable_baselines3.common.monitor.Monitor` — SB3 only populates it from an
`"episode"` info key that Monitor adds. Fixed at the source in
`env_factory.make_training_env` (now returns a Monitor-wrapped env), not
per call site. Caught before the real 2.8h run, not after.

**Entregable 6 (evaluation) — done.** All 3 TD3 checkpoints plus a
random-policy negative control evaluated on the same 50-cell grid (`SEEDS`
x `EVAL_DAYS`) used for AFAP/Round Robin, via `scripts/evaluate_rl.py`
(`--execute`, 200 runs, all appended, 0 skipped). `deterministic=True` for
TD3 `predict()`. Registry rows: `TD3_vanilla_ts100/101/102` and
`RandomPolicy`, all `algorithm_family="rl"`, `notes` recording
`reward=...,state=...,train_seed=...` per row.

**station_v0_bogota, n=50 per algorithm, mean [95% CI]:**

| Algorithm | EVs served | Profits | Avg. satisfaction | min energy satisfaction | Transformer overload (kWh) | Tracking error | Battery degradation |
|---|---|---|---|---|---|---|---|
| AFAP | 13.44 [13.22,13.67] | -45.73 [-53.80,-37.66] | 1.000 | 100.00 | 5.33 [1.93,8.73] | 51615 [48451,54779] | 0.000 |
| Round Robin | 13.44 [13.22,13.67] | -44.51 [-52.32,-36.71] | 1.000 | 99.95 | 0.00 | 12273 [11335,13211] | 0.000 |
| TD3 (seed 100) | 13.00 | -28.59 [-34.01,-23.16] | 0.996 | 93.06 [90.67,95.45] | 0.00 | 16668 [16325,17011] | 0.000 |
| TD3 (seed 101) | 10.40 [10.26,10.54] | -36.69 [-42.96,-30.42] | 0.995 | 92.31 [89.67,94.95] | 0.00 | 28152 [27540,28765] | 0.000 |
| TD3 (seed 102) | 12.80 [12.53,13.07] | -39.69 [-46.18,-33.19] | 0.984 | 86.71 [84.58,88.84] | 0.98 [0.16,1.81] | 25691 [24356,27025] | 0.000 |
| RandomPolicy (control) | 13.90 [13.56,14.24] | -48.19 [-57.38,-39.01] | 1.000 | 100.00 | **12.74 [3.45,22.03]** | 43878 [37148,50609] | 0.000 |

**Headline pattern -- a real tradeoff, not a uniform win:**
- **Overload:** all 3 TD3 seeds essentially match Round Robin (0.00, 0.00,
  0.98 kWh) and dramatically beat AFAP (5.33 kWh). The random-policy
  control shows **12.74 kWh -- worse than even unmanaged AFAP** -- proving
  this isn't "any policy beats AFAP here"; TD3 learned a real
  overload-avoidance behavior the control does not exhibit.
- **Cost of that:** `min_energy_user_satisfaction` drops to 93.1/92.3/86.7
  for TD3 (vs. ~100 for AFAP/RR/Random), and `total_ev_served` is lower and
  seed-inconsistent (13.0/10.4/12.8 vs. AFAP/RR's 13.44).
- **`tracking_error` is WORSE for TD3 than Round Robin** (+49% to +152%,
  paired bootstrap, see below) despite AFAP being worse still -- consistent
  with the declared reward-vs-metric misalignment
  (`03_rl_baseline.md` S3.4): the reward's tracking term and the reported
  `tracking_error` metric are related but not identical.
- **`total_profits` looks better for TD3** (less negative than both
  baselines, all 3 seeds) -- but profit is NOT in the reward at all (S3.2);
  this is very likely a side effect of serving fewer EVs / less energy
  exchanged (lower operating cost), not an intentional profit optimization.
  Stated as a caveat, not claimed as an achievement.
- **Battery degradation drops ~12-28% vs. both baselines** across all 3
  seeds (paired bootstrap) -- also very likely confounded with serving
  fewer EVs (less cycling), not necessarily "better battery management."

**Entregable 7 (statistics) — done**
(`scripts/analyze_rl_results.py` -> `results/rl_vs_baseline_bootstrap.csv`,
`results/rl_train_seed_dispersion.csv`, both using
`stats_utils.paired_bootstrap_ci`, no new bootstrap code written). Full
paired-bootstrap table (45 rows: 3 seeds x 2 baselines x 9 metrics
(each land n=50 paired cells)) in the CSV; headline percentages above.

**Cross-training-seed dispersion (separate from the scenario-level 95%
CIs above -- a genuinely different uncertainty source, see
`eval_protocol.py`'s SEEDS-vs-TRAIN_SEEDS docstring):**

| Metric | ts100 mean | ts101 mean | ts102 mean | spread (max-min) | relative spread |
|---|---|---|---|---|---|
| total_ev_served | 13.0 | 10.4 | 12.8 | 2.6 | 21.5% |
| total_profits | -28.59 | -36.69 | -39.69 | 11.10 | 31.7% |
| min_energy_user_satisfaction | 93.06 | 92.31 | 86.71 | 6.35 | 7.0% |
| tracking_error | 16668 | 28152 | 25691 | 11484 | 48.9% |
| total_transformer_overload | 0.0 | 0.0 | 0.98 | 0.98 | 300%* |

\* *300% relative spread is a division-by-near-zero artifact (two of three
seeds are exactly 0.0) -- flagged as such, not reported as a literal "300%
worse" claim.*

This dispersion is substantial (e.g. `total_ev_served` varies 21.5% and
`tracking_error` varies 48.9% purely from training-seed choice, holding the
evaluation grid fixed) -- reporting only one seed, or averaging across
seeds without disclosing this spread, would understate real uncertainty.
This is exactly why the Week 3 brief prohibits reporting only the best
seed.

**Registry contract change (Week 2 -> Week 3), documented as required
before use:** `ev2gym_thesis/registry_analysis.py`'s `main_grid_rows()`
used to filter by `notes == ""`, which silently excluded ALL 200 new RL
rows (they legitimately use non-empty `notes` for reward/state/train_seed
metadata per S3.5's registry-comparability requirement). Fixed by
introducing `NON_GRID_NOTES_MARKERS = {"week1_reference_day",
"pipeline_smoke_test_grid"}` and filtering by exact-marker exclusion
instead of "notes is non-empty" -- verified the two Week 1 reference rows
and the grid smoke test are still correctly excluded (`week1_reference_day`
rows found: 2, matching Week 1/2 expectations) and that `station_v0_bogota`
now correctly returns 300 main-grid rows (50 x 6 algorithms). This does NOT
affect `scripts/measure_degradation_by_ambient.py`, which has its own
independent inline `notes == ""` filter, not a call into `main_grid_rows`.

**Two real bugs found by the mandatory visual QA pass (Entregable 7),
neither of which raised an exception -- "ran without error" was not "was
correct," exactly as the Week 3 brief warned, and exactly as Week 2 found
two similar silent bugs:**

1. **TD3 timeseries were entirely zeroed out.** `figures/f01_power_profile.png`
   showed all 3 TD3 seeds as a flat line at 0 kW for the entire reference
   day, even though the same cell's own registry row correctly reported 13
   EVs served. Root cause: `scripts/evaluate_rl.py`'s original TD3 stepper
   ran the episode through `VecNormalize(DummyVecEnv([env]))`, and SB3's
   `DummyVecEnv` auto-resets its underlying env INSIDE the same `step()`
   call that returns the terminal transition -- so by the time external
   code read `env.current_power_usage` after the episode loop, the env had
   already been silently reset to a fresh (all-zero) state. Confirmed
   empirically: `current_power_usage.sum()` was `0.0` and `current_step`
   was `0` immediately after the loop, while the auto-preserved `info`
   dict's `total_ev_served` was still correctly `13`. **Scalar registry
   metrics were unaffected** (SB3 preserves the pre-reset info dict, which
   is where `stats_to_row` reads from) -- only the saved per-step
   timeseries were corrupted. Fixed by stepping the raw env directly
   (bypassing the VecEnv wrapper entirely) and manually applying the
   loaded `VecNormalize`'s observation normalization before each
   `model.predict()` call -- confirmed to produce IDENTICAL scalar stats to
   the original (VecEnv) stepper, only the timeseries capture changes. All
   150 TD3 timeseries `.npz` files were regenerated with the fixed stepper
   (registry rows were NOT re-appended -- already correct, would have
   collided with the dedup key anyway).
2. **Illegible/misleading figures once RL added 4 more algorithms.**
   `f02_metrics_bars` and `f04_distributions`: x-axis labels overlapped
   into an unreadable run-on string (6 algorithm names at a font/width
   sized for 2). Fixed with rotated labels (`f02`) and rotated labels + a
   width that scales with algorithm count (`f04`). `f05_vs_baseline`: title
   text was clipped at the figure's right edge (same failure mode as Week
   2's title-cutoff bug, different trigger -- now caused by the title
   enumerating 5 algorithm names instead of 1) and had large,
   growing-with-height wasted top/bottom margins (fixed-fraction
   `subplots_adjust` on a figure whose height now scales with algorithm
   count). Fixed by dropping the redundant algorithm-name enumeration from
   the title (already shown per-row on the y-axis) and switching to
   fixed-inch (not fixed-fraction) margins. `f06_size_sensitivity`: TD3/
   RandomPolicy appeared as disconnected single dots at the 8-port
   reference point only (they were never run across the size sweep -- a
   declared Week 3 scope limitation), implying a size trend that doesn't
   exist; fixed by restricting this figure to algorithms actually present
   on a non-reference sweep config.

**`f08_learning_curves` activated** (was an inert stub since Week 2,
correctly skipping until `algorithm_family=="rl"` rows existed). Reads each
training run's own `learning_curve.csv` directly (like `f09` reads its own
separate source file) -- NOT registry data, since the registry has no
reward-vs-timesteps time series column.

## 2026-08-12 — Week 3, Entregable 4: TD3 time calibration and confirmed training budget

**Calibration run** (`scripts/calibrate_td3_timing.py`, real `config_rl.py`
hyperparameters, `station_v0_bogota`, `train_seed=100`, round-robin cycling
over the 20-date `TRAIN_DAYS` pool): 5,000 timesteps completed in **276.4s
(4.61 min) = 18.09 steps/s**, 53 episodes started. This throughput is likely
dominated by per-episode environment reconstruction
(`env_factory.TrainingDayCyclingEnv` rebuilds `EV2Gym` — including
rereading the day-config YAML and the Netherlands day-ahead price CSV —
every episode, a documented design-decision tradeoff, not a bug) rather
than TD3's own gradient-step cost; flagged as a caveat on the number, not a
correction to it.

Linear extrapolation, presented as 4 candidates (15k/30k/60k/90k
timesteps/seed) against the user's stated constraints (~4h total budget,
~75 min/seed ceiling for 3 training seeds):

| timesteps/seed | est. time/seed | episodes | x per TRAIN_DAYS day | x3 seeds total |
|---:|---:|---:|---:|---:|
| 15,000 | 13.8 min | 156.2 | 7.81 | 41.5 min |
| 30,000 | 27.6 min | 312.5 | 15.62 | 82.9 min |
| 60,000 | 55.3 min | 625.0 | 31.25 | 165.9 min (2.8h) |
| 90,000 | 82.9 min | 937.5 | 46.88 | 248.8 min (4.2h) |

90,000 was already excluded from recommendation before asking: 82.9 min/seed
breaks the 75 min/seed ceiling, and 248.8 min breaks the 4h total budget.
**User confirmed 60,000 timesteps/seed** (asked explicitly via the tool, not
assumed) — the largest candidate respecting both ceilings, at 165.9 min
(2.8h) total, leaving headroom for Entregable 6's evaluation runs. Recorded
in `ev2gym_thesis/rl/config_rl.py`'s `TOTAL_TIMESTEPS = 60_000`.

**Declared scope reduction, stated plainly, not presented as equivalent:**
the PI-TD3/TD3 papers this thesis compares against trained for 5-48 hours
on HPC hardware. This project's entire Week 3 training budget (all 3
training seeds combined) is 2.8 hours on a single CPU laptop — roughly
**2-17x less wall-clock time than the papers' single training runs**, before
even accounting for HPC hardware being substantially faster per wall-clock
hour than a laptop CPU for this workload. At 60,000 timesteps, the agent
sees each `TRAIN_DAYS` date only ~31 times. Whatever convergence result
Entregable 5 produces must be read against this budget — a result showing
no clear convergence is an expected, legitimate possible outcome of this
reduced scope, not evidence of a bug, and will be reported as such rather
than adjusted or hidden (`CLAUDE.md` rule 3, brief S5 trap 7).

## 2026-08-12 — Week 3 kickoff: scope deviation (RL vanilla, not MPC), preflight (branch `semana-3`)

**Scope deviation, decided before any code was written.** `PROJECT_ROADMAP.md`
originally assigned Week 3 to the Gurobi/MPC baseline and Weeks 4–5 to RL.
This is deliberately reversed: **Week 3 = RL baseline vanilla (TD3), Week 4 =
perfect-information reference (free solver) + PI-TD3, Week 5 = full
comparison.** Full
reasoning (also in `PROJECT_ROADMAP.md`'s Phase → Objective Mapping note):

1. RL training is the highest-lead-time, highest-risk item in the compressed
   8-week plan; pushing it to Weeks 4–5 would concentrate that risk with no
   slack left to recover from a failed or slow run.
2. Week 2 confirmed only a *"Restricted — for non-production use only"*
   Gurobi license is available in this environment, not an academic one (see
   `02_model_validation.md`'s Gurobi section, 2026-08-12). Project policy
   already forbids any module from importing `gurobipy`. An MPC baseline in
   Week 3 would have made the week depend on a licensing question that was
   never actually resolved.
3. The perfect-information upper bound will very likely be computed with a
   free solver (HiGHS/CVXPY/OR-Tools), not Gurobi. Week 3 delivers only a
   short design note for this (no code, no numbers) so Week 4 doesn't have to
   make that call under time pressure.

`PROJECT_ROADMAP.md` was updated in the same commit: the old MPC-first plan
is marked `[SUPERSEDED]` and kept, not deleted, immediately above the revised
Week 3/4/5 sections. `CLAUDE.md`'s Current Phase section was also corrected
in this session — it had been left saying Week 2 was "in progress" (registry
backfill pending) after Week 2 had actually been finished and merged to
`main` on 2026-08-12; the two facts had drifted apart because the doc update
was deferred to be bundled with Week 3's first commit rather than committed
alone.

**Preflight (branch `semana-3`, created from `main` at commit `0b098f5`):**

- `semana-2` and `main` point to the same commit; working tree was clean —
  structurally fine to branch, no reconciliation needed.
- `results/master_results.csv`: 503 rows, generated by `0b098f5`.
  `config_name` in {`station_v0_bogota`, `station_n02_tx100`,
  `station_n02_tx025`, `station_n16_tx100`, `station_n16_tx200`,
  `v2ggrid_smoke_test`}; `algorithm` in {`ChargeAsFastAsPossible`,
  `RoundRobin`}; `algorithm_family` is `heuristic`-only — confirms no RL rows
  exist yet, so figure `f08` is correctly still an inert stub.
- Versions: Python 3.11.9, numpy 2.2.6, gymnasium 1.3.0 (no legacy `gym`
  installed), torch 2.9.0+cpu (already present). `stable-baselines3` was NOT
  installed; installed now (2.9.0) and added to `requirements.txt` along with
  `torch>=2.8` — unlike `gurobipy`, this is a real pipeline dependency.
- `ev2gym/rl_agent/reward.py`: 12 reward functions. Public/PST-relevant ones
  are `SquaredTrackingErrorReward` (env default; tracking-error only) and
  `SqTrError_TrPenalty_UserIncentives` (tracking error + transformer-overload
  penalty + user-satisfaction penalty). The rest (`ProfitMax_*`,
  `profit_maximization`, the `V2G_*` family) target Business/ProfitMax or
  V2G/grid scenarios (several require `simulate_grid=True`, which this
  project keeps `False` through Objectives 1–3) and don't fit this thesis's
  Public/PST variant.
- `ev2gym/rl_agent/state.py`: 5 state functions. `PublicPST` is the env
  default and the only one matching this project's scenario (no price
  forecasts, no grid/voltage terms) — vector of normalized timestep, next
  setpoint, current usage, and per-connected-EV `[full-flag, energy
  exchanged, dwell time]`. `BusinessPSTwithMoreKnowledge`, `V2G_profit_max`,
  `V2G_profit_max_loads`, `V2G_grid_state` all target other scenario
  families or need `simulate_grid=True`.
- `EV2Gym.__init__` (`ev2gym/models/ev2gym_env.py:38-56`): `reward_function`
  and `state_function` are plain constructor kwargs, defaulting to
  `SquaredTrackingErrorReward`/`PublicPST` if not passed — no
  string/registry lookup, the function object is passed directly and stored
  as `self.reward_function`/`self.state_function`.
- Gymnasium API compliance: full, no SB3 shim needed. `import gymnasium as
  gym` (not legacy `gym`), `reset(seed=None, options=None, **kwargs) ->
  (obs, {})`, `step(actions) -> (obs, reward, terminated, truncated, info)`
  — verified by reading the source, not assumed.
- Action space: `station_v0_bogota.yaml` has `v2g_enabled: False`, so
  `EV2Gym`'s action space is `Box(low=0, high=1)`, not `[-1,1]`. Checked
  Stable-Baselines3's installed source
  (`stable_baselines3/common/off_policy_algorithm.py:402,410`): TD3 samples
  in the policy's normalized `[-1,1]` space and calls
  `policy.scale_action`/`unscale_action` to rescale against
  `self.action_space.low/high` automatically. Trap #6 from the Week 3 brief
  (tanh output vs. env action range) is a non-issue here, confirmed by
  reading SB3's source rather than assumed — as long as nothing wraps the
  env in a way that misreports its action_space bounds.
- Trap #3 from the Week 3 brief (`ev.max_ac_charge_power` as a normalization
  denominator, even for DC charging) was already resolved at the config
  level before this session: `station_v0_bogota.yaml` sets
  `ev.max_ac_charge_power: 50` == `ev.max_dc_charge_power: 50`. The RL path
  reuses this same config through `ev2gym_thesis/config_utils.py`, so it
  inherits the fix; nothing RL-specific needed here.
- `TRAIN_DAYS` (disjoint-asserted against `EVAL_DAYS`) already existed in
  `ev2gym_thesis/eval_protocol.py` from Week 2 — added preemptively in
  anticipation of Week 3. Only `TRAIN_SEEDS` was missing (Entregable 1).

## 2026-08-12 (RESUMED, all Week 2 deliverables now complete) — supersedes the HANDOFF note below

Resumed from the HANDOFF note below and finished every remaining item, per
the user's choice to "finish everything before committing" rather than
defer Deliverables 4/5/7.

**Deliverable 4 (figures) — finished.** `scripts/make_figures.py` rewritten
to read the full `results/master_results.csv` (previously it only knew
`degradation_by_ambient.csv`, for f09). Implemented f01-f07 (f08 correctly
skips cleanly, no RL rows yet). **Every figure was visually inspected, not
just checked for "did it run" — this caught 2 real bugs:**
- `f05_vs_baseline`: figure canvas too narrow for its own labels — title
  and axis label were cut off outside the rendered image. Fixed sizing.
- `f07_metric_heatmap`: **color-direction bug.** `total_transformer_overload`
  is lower-is-better, but naive per-column min-max normalization colored
  the *worse* value (AFAP, 5.3 kWh) green and the *better* value (Round
  Robin, 0 kWh) red — backwards from every other column in the same
  figure. Added a `LOWER_IS_BETTER` set and inverted normalization for
  those columns so green consistently means "better," not just "higher
  raw number." This is exactly the kind of error that survives a "did it
  render" check but not an actual look at what the colors claim.

Also fixed, while building the figures: `scripts/backfill_registry.py` was
capturing `transformer_power`/`n_connected_evs` **once, after the
simulation loop ended** (a final-step snapshot), not per-step — so every
existing `results/timeseries/*.npz` has those two fields wrong-shaped
(single value instead of a 96-step array). `station_power` in the same
files is correct (reads `env.current_power_usage` directly, unaffected).
Fixed in code for future runs; the existing 500 npz files were **not**
regenerated, since nothing currently reads those two fields (only
`station_power`, used by f01, which is fine) — flagged rather than
silently left broken or silently re-run for ~45 minutes of no benefit.

**Deliverable 5 (`thesis_docs/chapters/03_algorithms.md`) — written.**
Full Rationale/Implementation/Hyperparameters/Results/Conclusions/
Limitations for AFAP and Round Robin, filled from
`results/master_results.csv` (`station_v0_bogota`, 50 runs/algorithm).
Headline paired result: Round Robin eliminates all measured transformer
overload (0.0 kWh vs. AFAP's 5.33 kWh [1.93, 8.73], 95% CI) at a real but
modest profit cost (-2.52% [-4.23%, -0.82%]), no measurable change in EVs
served, energy delivered, or satisfaction. Orfanoudakis et al.'s 313/57 kWh
figures cited only as an attributed external reference point in the
Conclusions prose, never placed in a results table, per the explicit
instruction.

**Sign-off obtained** (asked explicitly via the tool, not assumed): the
user confirmed keeping `results/degradation_by_ambient.csv` as a separate
file rather than retrofitting `master_results.csv` with an
`ambient_scenario` column.

**Deliverable 7 (hand-back document) — built as a generator, not
hand-written.** `scripts/build_week_doc.py` extracts every
`doc:begin <tag>`/`doc:end <tag>` region from `ev2gym_thesis/*.py` and
`scripts/*.py` fresh from disk (16 tagged regions found). Found and fixed
one real bug immediately: `ev2gym_thesis/figures.py` had an opened `doc:begin
write_caption` with no matching `doc:end` — the extractor's own strict
validation (raises rather than silently skipping) caught it on the first
run. Also trimmed 3 snippets that exceeded the ~40-line guideline
(`append_runs` 53->40, `paired_bootstrap` 47->34, `recompute_calendar`
67->40) by moving the `doc:begin` marker past each function's docstring —
the explanatory prose lives in the hand-back document text instead of
inside the quoted code.

`scripts/make_week2_handback.py` assembles
`thesis_docs/Week2_Parameter_Method_and_Implementation_Justification.md`
(Part 1: parameters introduced this week, labeled
validated/empirical/simplification; Part 2: every new file's location,
purpose, design decisions with the rejected alternative stated, library
choices, and the actual extracted code) plus a References section
(Primary/Secondary/Tertiary tiers, carrying forward the convention from
Week 1). Records the git commit and generation timestamp at the top, and
is regenerable with one command after any code change, per the
requirement.

`scripts/render_docx.py`: a small, project-specific (not general-purpose)
Markdown-to-docx renderer, following the stated Word conventions (plain
black text, no Word "Heading" styles — headers are bold plain paragraphs
with `style.name == "Normal"`, verified by reading the generated file back
with `python-docx`). Found and fixed one real bug: the first version wrote
table cells with raw `cells[i].text = val`, which left literal Markdown
syntax (backticks, asterisks) visible in the rendered table instead of
monospace/bold formatting — fixed by routing cell text through the same
inline-formatting parser used for body paragraphs, then verified by
reading the cells back and confirming the backticks were gone and the
run's font was `Consolas`. `python-docx` added to `requirements.txt`
(was not previously a project dependency).

**Claim-vocabulary check:** both new documents (`03_algorithms.md`, and
the hand-back doc, though the latter is technically outside
`check_claims.py`'s `thesis_docs/chapters/*.md` glob and was checked
manually instead) avoid the forbidden solver-optimality term outside of
meta-references to the reserved schema value or the policy itself (a
hyphenated-compound phrase in `03_algorithms.md`'s Pareto-frontier
discussion was reworded to "non-dominated," since the checker's
word-boundary regex matches the forbidden term inside compound words too).
`scripts/check_claims.py` passes clean.

**Status: all of Deliverables 1, 2, 3, 4, 5, 6, 7 and the Gurobi policy are
now complete**, per the original Week 2 prompt's own checklist. Nothing
committed yet — that's the next and last step.

## 2026-08-12 (HANDOFF, session cut short — laptop about to lose power) — READ THIS FIRST NEXT SESSION

User chose "finish everything before committing" for the remaining Deliverable
4/5/7 gap identified against the original Week 2 prompt. Made substantial
progress, then had to stop abruptly (battery). **Nothing is committed.**
`git status` on `semana-2` will show everything described below as
uncommitted/untracked. No background processes were left running (checked,
none found) -- safe to close the laptop.

**Done since the last "Status:" note further down this file:**
- Fixed a real bug in `scripts/backfill_registry.py`: `transformer_power`
  and `n_connected_evs` were captured ONCE after the simulation loop ended
  (a final-step snapshot) instead of per-step, so every existing
  `results/timeseries/*.npz`'s `transformer_power`/`n_connected_evs` fields
  are wrong-shaped (single value, not a 96-step array) -- `station_power`
  in those same files is correct (it reads `env.current_power_usage`
  directly, unaffected by the bug). Code is fixed for future runs; the
  existing 500 npz files were NOT regenerated (nothing currently uses those
  two fields, so not worth another ~45 min re-run -- flagged, not silently
  left broken).
- Built `ev2gym_thesis/registry_analysis.py` (`load_registry()`,
  `main_grid_rows()` -- shared filtering so every figure treats the
  registry the same way: excludes the grid smoke test, separates the
  balanced 500-row grid from the 2 Week 1 historical rows).
- Rewrote `scripts/make_figures.py` to actually read the full
  `results/master_results.csv` (previously it only knew about
  `degradation_by_ambient.csv` for f09). Implemented **f01 through f07 and
  f09** (f08 correctly detects zero `algorithm_family=="rl"` rows and skips
  cleanly with a log message, per spec -- not an error).
- **Visually inspected every figure, found and fixed 2 real bugs, not just
  "ran without crashing":**
  1. `f05_vs_baseline`: figure was too narrow for its own y-tick labels --
     title and axis label were literally cut off outside the canvas.
     Fixed sizing/margins.
  2. `f07_metric_heatmap`: **color direction bug** -- `total_transformer_overload`
     is a lower-is-better metric, but the naive column min-max normalization
     colored the WORSE value (AFAP, 5.3 kWh) green and the BETTER value
     (Round Robin, 0 kWh) red, backwards from every other column. Added a
     `LOWER_IS_BETTER` set and inverted normalization for those columns so
     green consistently means "better performance" everywhere, not just
     "higher raw number." This is exactly the kind of mistake that's easy
     to wave through if you only check "did it render," so flagging it
     explicitly here.
- All 8 implemented figures (f01,f02,f03,f04,f05,f06,f07,f09) regenerated
  cleanly in one final run, no errors, no warnings. `figures/` has 24 files
  (8 x {.png, .pdf, .caption.md}).
- Computed the exact Results-section numbers for Deliverable 5 from the
  registry (station_v0_bogota, 50 runs/algorithm, mean +/- 95% CI, paired
  bootstrap RR vs AFAP) -- **not yet written into a chapter file**:
  - AFAP: EVs served 13.44 [13.21,13.67], energy charged 196.7 kWh
    [190.9,202.5], transformer overload 5.33 kWh [1.93,8.73], satisfaction
    1.0, profits -45.73 [-53.8,-37.66].
  - Round Robin: EVs served 13.44 (identical), energy charged 196.5 kWh
    [190.7,202.4], transformer overload 0.0 kWh [0,0], satisfaction ~1.0,
    profits -44.51 [-52.32,-36.71].
  - Paired RR vs AFAP (bootstrap 95% CI, matched by seed+day cell):
    transformer overload -5.33 kWh [-8.96,-2.13] (absolute diff, AFAP
    baseline is exactly 0 so % is undefined), profits -2.52%
    [-4.23%,-0.82%], tracking_error -76.18% [-77.41%,-74.77%],
    power_tracker_violation -100% [-100%,-100%] (RR essentially eliminates
    it).

**NOT done yet, in priority order for next session:**
1. **`thesis_docs/chapters/03_algorithms.md` (Deliverable 5) -- not written
   at all.** The numbers above are ready to use directly; just needs the
   template filled (Rationale/Implementation/Hyperparameters/Results/
   Conclusions/Limitations, per algorithm) for AFAP and Round Robin. The
   313 kWh / 57 kWh Orfanoudakis et al. figures go in the text only as an
   attributed external reference point, never mixed into our own results
   table -- per the original prompt's explicit instruction.
2. Update `02_model_validation.md`'s header ("Status: partial" note) -- a
   lot has been resolved since that was written (grid-scope conflict,
   degradation now measured with CI, etc.); the note is stale.
3. Confirm with the user (asked once already, not yet re-confirmed after
   building the figures) that using a **separate** file
   (`results/degradation_by_ambient.csv`) instead of adding an
   `ambient_scenario` column to `master_results.csv` is acceptable --
   deviates from the literal Deliverable 6.4 text, justified by analogy to
   the `simulate_grid` separation principle, but was never explicitly
   signed off.
4. `scripts/build_week_doc.py` -- not started. Extracts `# doc:begin
   <tag>`/`# doc:end <tag>` regions (already placed in several files this
   session: `ev2gym_thesis/eval_protocol.py`, `registry.py`,
   `degradation_bogota.py`, `figures.py`) into the hand-back document at
   build time.
5. `thesis_docs/Week2_Parameter_Method_and_Implementation_Justification.md`
   + its `.docx` rendering (Deliverable 7) -- not started at all. Per the
   original order-of-work this was always meant to be built last, so its
   absence alone isn't a surprise -- but it's still fully outstanding.
6. `.gitignore`/`CLAUDE.md`/`PROJECT_ROADMAP.md` diff from the grid-scope
   resolution earlier this session was shown to the user but never
   committed.
7. Nothing from this entire `semana-2` session (going back to before the
   sleep interruption too) is committed. `git status` will show a large
   number of new/modified files across `ev2gym_thesis/`, `scripts/`,
   `data/`, `results/`, `figures/`, `thesis_docs/chapters/`, and the
   root-level `.gitignore`/`CLAUDE.md`/`PROJECT_ROADMAP.md`/
   `requirements.txt`/`setup.py`.

**To resume:** re-read this note, then pick up at item 1 (algorithm
chapter) using the numbers already computed above -- no need to re-run
anything to get those.

## 2026-08-12 — Week 2 kickoff: seed protocol, registry, degradation calibration (branch `semana-2`)

Week 1 was confirmed closed by the user (station_v0_bogota.yaml: AFAP 14 EVs /
0.132 kWh overload, Round Robin 14 EVs / 0.0 kWh overload — see
`01_baseline.md`). `number_of_charging_stations = 8` was retroactively
grounded in the Enel X Colombia public charge-point inventory (67 chargers /
21 sites in Bogota; CC Retiro = 8 ports) — see `01_baseline.md` for the full
citation and its two declared limitations (AC-only 8-port sites; Enel X is a
lower bound, not a census). Branch `semana-2` was created from `semana-1`'s
tip (not `main`, which still lacks the Week 1 fix — same reasoning as last
week, flagged again for the record).

**Gate 1 — seed-sensitivity verification (Deliverable 2).** Created
`ev2gym_thesis/eval_protocol.py`: `SEEDS = [0,1,2,3,4]`, 10 `EVAL_DAYS`
(6 weekdays / 4 weekend days, spread across 2022, day-of-week verified with
`datetime`, not assumed), `REFERENCE_DAY = 2022-01-17` (same as the Week 1
day, for continuity), and 20 `TRAIN_DAYS` reserved for future RL work with
an `assert` at import time that it is disjoint from `EVAL_DAYS`. Ran
`scripts/verify_seed_sensitivity.py`: AFAP on `station_v0_bogota.yaml`,
same day, seed=0 vs seed=1 -> `total_energy_charged` 214.40 kWh vs 204.64
kWh. **PASS** — the seed reaches the EV-spawn RNG.

**Gate 2 — degradation model inspection (Deliverable 6.1), read-only.**
Read `ev2gym/models/ev.py:442-521` (`get_battery_degradation`). Findings:
- Functional form matches a Xu et al. (2018)-type semi-empirical model
  (calendar aging ~ alpha(V,theta)*t^0.75, cycling aging ~
  beta(V,DoD)*Ah^0.5, Arrhenius term in alpha). **Citation not verified
  against the primary source** — no in-code citation exists, and WebFetch
  attempts against ResearchGate/MDPI/arXiv/Chalmers all failed (403s or
  unreadable scanned PDFs). Cite as "a semi-empirical model of Xu et al.
  (2018) type, as implemented by EV2Gym" until verified, per the user's
  explicit instruction.
- **`theta` is a hard-coded constant, `298.15 K` (25 C), not an input** —
  not derived from config or simulation state. Confirms calibration must be
  an added wrapper, not a parameter change.
- Temperature enters **only** the calendar term (`alpha`); `beta` (cycling)
  has no temperature dependence at all, and its first two terms
  (`z0*(v_half_soc-z1)^2 + z2`) never vary between EVs since `v_half_soc`
  is itself a constant — cycling aging is effectively linear in `delta_DoD`
  only. This is a model limitation to document, not a bug to fix.
- Other hard-coded constants found: `T_acc = 730 days`, `b_cap_kwh = 78`
  (does not match our config's `battery_capacity: 70` — used only as a
  normalization factor, not a bug), `d_dist = 15000 km/year`,
  `G = 0.186 kWh/km` — all describe a generic reference-vehicle usage
  pattern, unrelated to the specific simulated EV.
- **Battery-capacity discrepancy claimed by the user (70 vs "60 kWh")
  resolved: no discrepancy exists.** `station_v0_bogota.yaml` has
  `battery_capacity: 70` consistently; grep over all of `thesis_docs/` and
  `CLAUDE.md` found no document stating 60 kWh. The "60 kWh" figure existed
  only in the Week 2 prompt's own illustrative text for a not-yet-written
  deliverable, never in a committed file.

**Blocking check (user-mandated, before writing any calibration code):**
grepped `ev2gym/rl_agent/reward.py` (14 reward functions) and all of
`ev2gym/*.py` for `battery`/`degradation`/`calendar_loss`/`cyclic_loss` —
zero references outside `ev2gym/utilities/utils.py`'s `get_statistics()`.
**Confirmed: battery degradation does not feed into any reward function.**
Recomputing it post-hoc is therefore exact, not an approximation.

**Deliverable 3 — registry infrastructure.** Built
`ev2gym_thesis/registry.py` (`REGISTRY_COLUMNS` schema, `append_runs()`
with schema validation + dedup on `(config_name, algorithm, seed,
eval_day)`, `save_timeseries()`), `ev2gym_thesis/config_utils.py`
(per-eval-day temp config generation, since EV2Gym reads the date once from
the config file path at construction), and `scripts/backfill_registry.py`.
Dry-run reported **500 new simulation runs** (5 configs x 2 algorithms x 5
seeds x 10 days) + 2 backfilled Week 1 reference rows (read from the
existing committed CSVs, not re-run), estimated **~54 minutes**
single-threaded from one measured sample run (6.51s), not guessed.

Also had to fix `.gitignore` again: the blanket `/results/` rule (already
narrowed once, for Week 1) still fully blocked `results/master_results.csv`
at the repo root. Changed to `/results/*` + explicit
`!/results/master_results.csv` negation, so `results/timeseries/*.npz`
stays ignored (regenerable from config+seed+day, consistent with the
project's "no large binaries in git" convention) while the registry CSV is
tracked. Same fix applied for a `tests/` blanket-ignore conflict — rather
than patch that rule again, thesis unit tests live in
`ev2gym_thesis/tests/` instead of a top-level `tests/`.

User confirmed launching `--execute`. **Backfill started, then paused by
user request (couldn't wait ~54 min) at 26/502 rows** — safe to stop and
resume anytime given the append-only + dedup design; no work lost. Resume
tomorrow with `python scripts/backfill_registry.py --execute`.

**Deliverable 6.2-6.4 — Bogota degradation calibration wrapper.** Scope
approved by the user: a new module, not touching `ev2gym/models/ev.py`,
recomputing only calendar aging by substituting `theta` with a
session-integrated effective Arrhenius factor.

*IDEAM verification (mandatory before writing any ambient figure into the
thesis):* downloaded IDEAM's own `normales_climatologicas_periodo_1981-2010.xlsx`
directly (https://www.ideam.gov.co/sala-de-prensa/informes/Normales-clim%C3%A1ticas-est%C3%A1ndar)
and read station **21205791 "Aeropuerto El Dorado Catam - AUT"**, Bogota,
elevation 2547 m. **The originally assumed 13.3 C annual mean does NOT
match this primary source. The verified IDEAM value is 13.68 C**
(annual mean of daily max: 19.31 C; annual mean of daily min: 7.88 C;
monthly means range only 13.29-14.16 C, confirming negligible seasonal
variation). Per the user's explicit instruction, 13.68 C replaces 13.3 C
everywhere. The specific clock-hours of the diurnal min (~06:00) and max
(~14:30) are **not** verifiable against this file (IDEAM publishes monthly
normals, not an hourly curve) — kept as a labelled, unverified assumption.

Also verified (not assumed) from `README.md:113,116`: EV2Gym's own
documentation states arrival/time-of-stay/energy-required distributions are
based on *ElaadNL* data and EV/charger characteristics on the *RVO Survey*
— both Dutch, confirming the "not Colombian" transferability limitation
independently of the Week 2 prompt's claim.

Also verified (read `ev2gym/utilities/utils.py:477-556`, `EV_spawner`):
**EV2Gym does not model queueing.** Arrivals are only ever generated for a
(port, timestep) pair when that specific port is already free at that
moment (`if occupancy_list[counter, t] == 0 and ...`) — there is no queue
data structure and no explicit "EV arrived but was rejected" event; demand
generation is conditioned on capacity availability by construction. This
means Objective 1's "waiting time" metric is **not measurable** in the
current setup — it would require a custom spawn function that generates
arrivals independently of occupancy and explicitly tracks unserved demand.

Built:
- `ev2gym_thesis/ambient_bogota.py` — outdoor/underground diurnal profiles
  (piecewise-linear, trough 06:00 / peak 14:30), anchored to the verified
  IDEAM figures. Underground profile (+/-0.75 C around the 13.68 C mean) is
  a declared, uncited modeling assumption (no published normals exist for
  covered sites).
- `ev2gym_thesis/degradation_bogota.py` — `recompute_calendar_degradation()`:
  integrates `A_eff = mean(exp(-E2/theta(t)))` over each EV's actual
  session steps (reusing `historic_soc`/`active_steps`/`time_of_arrival`/
  `time_of_departure`, already exposed by the simulator), vs. a
  point-estimate at the session's mean temperature, to quantify the
  Jensen's-inequality gap the user flagged (`exp(-E2/theta)` is convex, so
  the point estimate underestimates). `T_acc`, `b_cap_kwh`, `d_dist_km_year`,
  `G_kwh_per_km` exposed as parameters (defaults = ev.py's hard-coded
  values). `delta_t_charging_c` implemented as a **declared, unvalidated
  sensitivity bump** (not a calibrated thermal model, per the user's
  explicit down-scope) applied only at actively-charging steps.
- `ev2gym_thesis/tests/test_degradation_bogota.py` — 6 tests, all pass,
  including the 4 mandated closed-form Arrhenius values (independently
  re-verified before writing the test, not just copied):
  `exp(-6976/theta)` relative to `theta=298.15K` at 280.15K/286.45K/
  293.15K/300.15K = 0.2224/0.3846/0.6709/1.1687 (tolerance 1e-3).

**Preliminary demo (`scripts/demo_degradation_bogota.py`) — ONE run only
(seed=0, 2022-01-17, 14 EVs), NOT the full multi-seed/multi-day measurement:**

| scenario | sum(calendar loss) | vs. 25 C default |
|---|---|---|
| Original (theta=298.15K fixed) | 2.2187e-04 | — |
| Bogota outdoor, delta_t=0 | 1.0700e-04 | -51.77% |
| Bogota outdoor, delta_t=+5C | 1.1582e-04 | -47.80% |
| Bogota underground, delta_t=0 | 9.0331e-05 | -59.29% |

Measured Jensen's gap on this run: the point-estimate (mean-temperature)
approximation underestimates the properly-integrated calendar degradation
by **1.016%**.

**This is a single-run preliminary result, not the CI-backed measurement
the user asked for ("MEDIR, NO SUPONER").** That requires the full 500-run
registry backfill (currently paused at 26/502 rows). Do not treat -51.77%/
-59.29% as final thesis numbers until re-measured across the full protocol.

**Status:** registry backfill paused (resumable), degradation wrapper built
and tested, IDEAM correction applied. Not yet done: finish backfill,
re-measure degradation-by-ambient-scenario across all 50 runs with
confidence intervals, write `f09_degradation_by_ambient`, extend
`ambient_bogota.py`/`data/ambient_profiles.yaml` to the other categoria
especial cities (Deliverable 6.5, explicitly out of scope for today),
`scripts/run_optimal_reference.py` + `scripts/check_claims.py` (Gurobi
hook), figure module, algorithm chapter, hand-back document. Nothing
committed yet — code + this log entry staged for tomorrow's commit.

---

## 2026-08-12 (continued) — Registry backfill completed, grid-scope resolved, CI-backed degradation measurement

**Registry backfill: COMPLETE.** Resumed the paused backfill (twice more —
once normally, once after a forced pause for the machine to sleep). Final
`results/master_results.csv`: **503 rows, 503 unique
`(config_name, algorithm, seed, eval_day)` keys, 0 duplicates** — the
dedup design held across three separate pause/resume cycles. Composition
verified: `station_v0_bogota` 102 rows (100 new + 2 Week 1 historical),
each of the 4 `station_sensitivity/` configs exactly 100 rows (2 algorithms
x 5 seeds x 10 days), `v2ggrid_smoke_test` 1 row.

**Efficiency bug found and fixed during resume:** `scripts/backfill_registry.py`
was re-simulating every already-completed row before checking the registry
to decide whether to skip it — the dedup check only happened at write time,
not before the (expensive) simulation. With ~357 rows already done, a naive
resume would have wasted ~35 minutes re-computing results only to discard
them. Fixed by exposing `ev2gym_thesis.registry.load_existing_keys()`
publicly and pre-filtering `all_run_specs()` against it before calling
`run_single()`. Confirmed fix: resumed run reached the prior 357-row mark
in 12 seconds instead of ~35 minutes.

**One unexplained timing anomaly, reported not hidden:** run
`station_n02_tx025__ChargeAsFastAsPossible__seed0__2022-07-10` (attempt
before the machine sleep) took 356.9s vs. the usual 5-7s, then immediately
returned to normal on the next run with the same config. No confirmed
cause (sibling runs on the identical config were unaffected, so it wasn't
the config itself); plausibly related to the machine approaching sleep
around that time, but not confirmed. The row itself completed correctly
(`total_ev_served` consistent with sibling runs) and was kept as-is.

**Grid-scope conflict, resolved by the user, documents corrected.** The
user resolved the apparent `PROJECT_ROADMAP.md` vs. Week 2 task-brief
conflict: `simulate_grid: False` (station + own local transformer) applies
through Objectives 1-3; `simulate_grid: True` + IEEE 34-bus is reserved for
Objectives 4-5, never mixed into the Phase 2 algorithm-comparison registry
(would break comparability across the 500-row evaluation grid). Week 2's
"grid model validation" was always about the station-and-local-transformer
model, not the feeder. `PROJECT_ROADMAP.md` and `CLAUDE.md` were both
corrected to remove language suggesting feeder/voltage work belongs in
Week 2 (diffs shown to and approved in principle by the user before
editing; not yet committed). `thesis_docs/chapters/02_model_validation.md`'s
grid-representation row updated accordingly, with the reasoning written out
in full (not just referenced).

**De-risking smoke test run and registered.** `scripts/smoke_test_grid.py`
ran `ev2gym/example_config_files/V2Ggrid.yaml` (unmodified upstream
example) once with AFAP: `simulate_grid: True` + IEEE 34-bus loaded,
resolved a power flow, and emitted both `voltage_violation` (a 1-tuple of
`np.float64`, interestingly — not a plain scalar) and
`voltage_violation_counter` without error. **PASS**, not interpreted.
Registered as `config_name="v2ggrid_smoke_test"`,
`notes="pipeline_smoke_test_grid"` — must be excluded from every figure
and results table. This run exposed a real gap in
`ev2gym_thesis/registry.py`'s `_coerce_scalar()`: it handled `list`/
`np.ndarray` but not plain `tuple`, so `voltage_violation` was stored as a
stringified tuple for this one row. Fixed for future `simulate_grid: True`
rows (Objectives 4-5); the smoke-test row's already-written value was left
as-is (append-only, and the row is excluded from analysis regardless).

**Gurobi policy implemented.** Removed `gurobipy` from `requirements.txt`
and `setup.py` (project-root packaging files, not `ev2gym/models`/
`rl_agent` internals). `scripts/run_optimal_reference.py`: self-contained,
never imported elsewhere, license-capability check on startup, exits 0
either way. Run once: `gurobipy` DID start an `Env()` in this environment,
but reported `"Restricted license - for non-production use only"` — this
is the free/size-limited default license that ships with the package, NOT
the university academic license `CLAUDE.md` describes. Flagging explicitly
so this isn't misread later as "the academic license arrived."
`scripts/check_claims.py`: trivial regex check over `thesis_docs/chapters/*.md`
for the forbidden solver-optimality vocabulary (see the Gurobi policy
section in `02_model_validation.md` for the exact terms) while no row using
the registry's reserved solver-comparison `algorithm_family` value exists.
First run failed against `02_model_validation.md`'s own meta-discussion of
the policy (false
positive on text *about* the forbidden words, not a real claim) — reworded
that section to avoid the trigger without making the
checker itself less trivial. Passes clean now.

**`data/ambient_profiles.yaml` (Deliverable 6.5, data only).** Reused the
same downloaded IDEAM `normales_climatologicas_periodo_1981-2010.xlsx` to
verify Medellin (22.53 C, Aeropuerto Olaya Herrera), Cali (24.48 C,
Universidad del Valle), Cartagena (27.78 C, Aeropuerto Rafael Nunez) — all
[Primary]. Two gaps found and flagged rather than papered over:
**Barranquilla has no station in this IDEAM workbook at all** — used
Infobae (which itself cites IDEAM) as [Secondary], marked "pending
verification against IDEAM." **Bucaramanga's only station in the workbook
(Universidad Industrial Santander) records 118 m elevation**, sharply
inconsistent with the ~959-1000 m commonly cited for the city — temperature
value (23.01 C) is plausible and kept, elevation flagged pending
verification rather than silently overridden with the "commonly known"
figure.

**`ev2gym_thesis/stats_utils.py` built and tested against synthetic
fixtures (not the registry), per the user's explicit requirement.**
`mean_ci()` verified against a hand-computed closed-form normal CI.
`paired_bootstrap_ci()` verified with two exact-zero-width discriminating
tests (`b = a + 3` with varying `a`; a constant 10% case) that would fail
if pairing were broken (i.e. if `a` and `b` were resampled independently
instead of by shared index) — both collapsed to exactly the true value,
confirming the pairing logic is correct. 9/9 tests pass.

**Degradation-by-ambient: final CI-backed measurement (replaces the
2026-08-12 preliminary single-run numbers above).**
`scripts/measure_degradation_by_ambient.py`, scope=`reference`
(`station_v0_bogota`'s 100 backfill rows: AFAP+RoundRobin x 5 seeds x
10 days — the user chose this scope over the full 502-row option to save
~52 minutes). Design: writes to a **separate** file,
`results/degradation_by_ambient.csv`, rather than adding a column to
`master_results.csv` — same "don't mix scenario dimensions into the
Phase 2 comparison registry" principle applied to the grid-scope
resolution above. Each row is re-simulated once (per-EV session data isn't
persisted in the registry) and measured under 4 ambient scenarios.
100/100 completed, 0 errors.

Paired bootstrap (10,000 resamples, matched by run_id/`(seed, day)` cell —
not independent-sample stats):

| | calendar-only change vs. 25C default | 95% CI | total (cal+cyc) change | 95% CI |
|---|---|---|---|---|
| Bogota outdoor | -51.75% | [-52.01%, -51.48%] | -26.13% | [-26.50%, -25.76%] |
| Bogota outdoor, +5C charging | -45.12% | [-45.48%, -44.74%] | -24.37% | [-24.87%, -23.87%] |
| Bogota underground | -59.17% | [-59.21%, -59.13%] | -32.49% | [-32.99%, -31.99%] |

Calendar aging is **48.08%** of total degradation under the default
scenario (95% CI [47.53%, 48.62%], n=100) — since cycling is
temperature-independent, this bounds how much of the *total* reported
`battery_degradation` metric can move with ambient scenario, which is why
the "total" column above is roughly half the "calendar-only" column.

Jensen's-gap, measured (not assumed) across all 100 runs: the
mean-temperature point-estimate underestimates the properly session-
integrated calendar degradation by **1.01%** (95% CI [0.97%, 1.06%]) —
tight and consistent with the earlier single-run estimate (1.016%).

**The single-run preliminary numbers from earlier today (-51.77%/-59.29%,
calendar-only) turn out nearly identical to the now-properly-measured
values (-51.75%/-59.17%)** — reassuring for stability, but the CI-backed
numbers above are now the citable ones; the single-run figures are
superseded, not deleted (kept above for the record of how this was built
incrementally).

**`f09_degradation_by_ambient` built.** `ev2gym_thesis/figures.py`
(`ALGORITHM_STYLE` dict -- AFAP red/circle, Round Robin blue/square, fixed
across all future figures; `write_caption()`, generated never hand-written)
and `scripts/make_figures.py`. Three-panel grouped bar chart (total /
calendar-only / cycling-only), x-axis = ambient scenario, bars = algorithm,
mean +/- 95% CI from `mean_ci()`. Output: `figures/f09_degradation_by_ambient.png`
(300 dpi), `.pdf` (vector), `.caption.md` (states runs behind it = 100,
configs, algorithms, git commit, generation timestamp). Visual check
confirms the measured numbers: calendar-only bars drop sharply across
Bogota scenarios, cycling-only bars stay flat (confirming no temperature
dependence, as expected from the code inspection), total sits at roughly
half the calendar-only drop. Only this one figure implemented so far.

**Status:** registry complete and verified (503 rows), degradation
calibration measured with confidence intervals (reference scope) and
plotted, grid-scope conflict resolved and both planning documents
corrected (diff shown, not yet committed), Gurobi policy implemented,
vocabulary checker passing, other-cities ambient data added with gaps
flagged. Not yet done: remaining Deliverable 4 figures (f01-f08), algorithm
chapter (Deliverable 5), hand-back document (Deliverable 7), the
`PROJECT_ROADMAP.md`/`CLAUDE.md` diff commit. Nothing
committed yet.

## 2026-08-05 — Week 1 baseline reproduction attempt (branch `semana-1`)

**Environment setup.** `pip install -e .` succeeded on a fresh Python 3.11.9
install, but did not pull in `pandapower`, `numba`, or `multicopula`
(consistent with prior notes in `CLAUDE.md`). Installed those three
explicitly; `gymnasium` and `gurobipy` were pulled automatically as
dependencies of `ev2gym`. No changes were made to `ev2gym/models/` or
`ev2gym/rl_agent/`.

**Ran:** `experiments/phase1_baseline/run_baseline.py`, which loads
`experiments/phase1_baseline/configs/station_v0_bogota.yaml` and runs a
96-step (15-min) day with `ChargeAsFastAsPossible` and `RoundRobin`.

**Assumption made (config's `random_day: True` contradicts a "fixed date"):**
`station_v0_bogota.yaml` has `random_day: True`. Reading
`ev2gym/models/ev2gym_env.py` (lines ~130-140) confirms that with
`random_day: True`, the simulated calendar date is drawn from
`random.randint()` seeded by whatever `seed` is passed to the `EV2Gym`
constructor — there is no fixed date sitting in this config file. Since no
seed was recorded anywhere in this repo (git history, `results/`, or
`thesis_docs/`) for whatever run originally produced the reference values
below, that prior result cannot be reproduced from this config alone.
**Assumption:** to give AFAP and Round Robin a fair, identical-day comparison
without editing the YAML, both runs were driven with the same explicit
seed (`SEED = 42` in `run_baseline.py`), landing on simulated date
2022-04-25. This should be revisited (e.g., set `random_day: False` with an
explicit `year/month/day`, or standardize on a documented seed) before this
becomes the reported Week-1 baseline in the thesis.

**Results obtained (seed=42, sim_date=2022-04-25):**

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 92 | 92 |
| total_profits | -280.52 | -274.35 |
| total_energy_charged (kWh) | 1260.38 | 1259.74 |
| average_user_satisfaction | 1.0 | 0.99995 |
| total_transformer_overload (kWh) | 0.0 | 0.0 |

**Comparison against previously reported reference values** (AFAP: 11 EVs,
profit -56.85, 206.48 kWh, 100% satisfaction, 42.17 kWh overload; Round
Robin: 13 EVs, profit -54.69, 191.18 kWh, 100% satisfaction, 0.00 kWh
overload): **does not match**, not even approximately — EVs served is ~7-8x
higher and energy charged ~6x higher than the reference.

**Root cause not yet confirmed, but the most likely explanation:**
`station_v0_bogota.yaml` is still an untouched copy of
`ev2gym/example_config_files/V2Ggrid.yaml` — `number_of_charging_stations:
150`, `spawn_multiplier: 5`, IEEE 34-bus grid, `v2g_enabled: True`. This is
a large synthetic multi-station grid scenario, not yet edited down to the
"representative single Bogotá public station" the roadmap's Week 1 task
calls for (`PROJECT_ROADMAP.md`, Week 1 checklist, still unchecked). A
scenario with 150 charging points and a 5x spawn multiplier plausibly
serving ~90 EVs/day is internally consistent; it is very unlikely to be the
same scenario that produced the reference 11-13 EVs/day. This is a
plausible explanation, not a confirmed one — the reference run's exact
config was not available to diff against.

**Status:** environment reproduced and smoke-tested; baseline run executed
successfully end-to-end; numeric results **do not match** the previously
reported reference values and should not be treated as validated until (a)
`station_v0_bogota.yaml` is actually edited per the Week 1 checklist item
("pick the representative station type... number_of_charging_stations...")
and (b) a fixed seed/date convention is agreed and recorded. Flagging for
user review before proceeding to Week 2.

---

## 2026-08-05 — Week 1 config fix: single-station sizing (branch `semana-1`)

Following the diagnosis above, `station_v0_bogota.yaml` was edited from the
unedited `V2Ggrid.yaml` copy to a small, single-station scenario. All values
below were specified by the user as settled decisions, not derived by
Claude Code this session:

| key | old (V2Ggrid.yaml copy) | new |
|---|---|---|
| `scenario` | public | public (unchanged) |
| `simulate_grid` | True | **False** |
| `number_of_charging_stations` | 150 | **8** |
| `number_of_transformers` | -1 | **1** |
| `transformer.max_power` | 200 kW | **100 kW** |
| `v2g_enabled` | True | **False** |
| `heterogeneous_ev_specs` | False | False (unchanged) |
| `ev.max_ac_charge_power` | 22 kW | **50 kW** |
| `ev.max_dc_charge_power` | 50 kW | 50 kW (unchanged, now equal to max_ac) |
| `charging_station.max_charge_current` | 32 A | **72 A** (~50 kW @ 400V/3-phase) |
| `spawn_multiplier` | 5 | **30** |
| `random_day` | True | **False** |
| `year/month/day` | 2022-01-17 | 2022-01-17 (unchanged, now actually used) |

**Verified against `ev2gym/utilities/loaders.py` before writing:** every key
above is read by the loader (`number_of_transformers`, `transformer.max_power`
in `load_transformers`; `v2g_enabled`, `charging_station.max_charge_current`
in `load_ev_charger_profiles`; `spawn_multiplier` in `EV_spawner`;
`random_day`/`year`/`month`/`day` in `EV2Gym.__init__`).

**`number_of_transformers: -1` bug, confirmed:** with `simulate_grid: False`,
`load_grid()` builds `cs_transformers` directly from
`env.number_of_transformers` via `np.arange(env.number_of_transformers)`.
`np.arange(-1)` returns an empty array, which would leave charging stations
unassigned to any transformer. This only went unnoticed previously because
`simulate_grid: True` overwrites `number_of_transformers` from the grid
topology before it's used. Setting it to `1` avoids this. (This matches a
comment already present in `ev2gym/example_config_files/PublicPST.yaml`:
"if simulate_grid is True then this value is overwritten by the topology
file".)

**`max_ac_charge_power` == `max_dc_charge_power` requirement:** requested by
the user as a settled value. Reading `ev2gym/models/ev.py` and
`ev2gym/utilities/utils.py`, no code path was found in the current codebase
that would raise a `ZeroDivisionError` from these two values differing, and
no such note exists in the current `CLAUDE.md`. Applying the requested equal
values anyway (50/50 kW) since it is harmless and doesn't contradict
anything observed; flagging this for the record since it could not be
independently verified.

**`simulation_days: weekdays` note:** with `random_day: False`,
`ev2gym_env.py` never reaches the `simulation_days` weekday/weekend check —
that branch only executes when `random_day: True`. The key is harmless to
leave in the config but currently has no effect; 2022-01-17 happens to be a
Monday anyway.

**Re-ran** `experiments/phase1_baseline/run_baseline.py` (SEED=42, unchanged)
against the corrected config, sim_date fixed at 2022-01-17 05:00 (from the
config itself now, not from the seed).

**Results obtained:**

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 14 | 14 |
| total_profits | -56.92 | -49.74 |
| total_energy_charged (kWh) | 240.93 | 240.81 |
| average_user_satisfaction | 1.0 | 1.0 |
| total_transformer_overload (kWh) | 0.132 | 0.0 |

**Sanity check:** 14 EVs/day for 8 stations at spawn_multiplier 30 is within
the expected ~10-15 ballpark — plausible order of magnitude, unlike the
previous 92 EVs/day run.

**Qualitative pattern now present:** AFAP produces a small but real
transformer overload (0.132 kWh) that Round Robin's power-setpoint tracking
reduces to exactly 0.0 kWh — the expected qualitative relationship between
an unmanaged and a managed charging strategy. Exact magnitudes are not
expected to match the original reference values (11/13 EVs, 42.17/0.00 kWh
overload) since this run uses a different random seed/EV-arrival draw than
whatever produced that reference; only the qualitative pattern (AFAP
overloads, RR doesn't) and the general order of magnitude are being used as
the validation criteria here.

**Status:** config now reflects a plausible single-station scenario; results
are in the right ballpark and show the expected qualitative
AFAP-vs-RoundRobin pattern. Treating this as the working Week 1 baseline
pending user confirmation. See `thesis_docs/chapters/01_baseline.md` for the
station description write-up.
