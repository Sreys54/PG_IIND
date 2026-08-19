# Chapter 3 — RL Baseline Vanilla: TD3 (Week 3)

> Status: Entregables 1–9 (partial) complete as of 2026-08-13 — reward/state
> choice, `ev2gym_thesis/rl/` package, the perfect-information-reference
> design note, calibration + confirmed training budget, training (3 seeds),
> evaluation (50-cell grid + random-policy control), statistics (paired
> bootstrap + cross-training-seed dispersion), and figures (`f08` activated,
> all figures visually QA'd — 2 real bugs found and fixed, see
> `00_lab_log.md`). Only Entregable 10 (Word hand-back document) remains.
> Full session history in `thesis_docs/chapters/00_lab_log.md`'s 2026-08-12
> and 2026-08-13 Week 3 entries.
>
> **Correction, 2026-08-18 (see S3.11 and `00_lab_log.md`'s 2026-08-18
> entry): the Entregable 6/7 evaluation numbers below were wrong.** All 200
> TD3/RandomPolicy evaluation episodes ran against an uncontrolled,
> re-randomized scenario instead of the registered `(SEEDS x EVAL_DAYS)`
> cell, due to a missing seed argument in `scripts/evaluate_rl.py`'s
> steppers. Fixed, re-run, and the tables/figures throughout this chapter
> now reflect the corrected data. **The correction reverses one headline
> conclusion** (the random-policy control no longer supports "TD3 learned a
> real overload-avoidance behavior" — see S3.11). Trained model weights are
> unaffected; no retraining was needed.

## 3.1 Algorithm choice: TD3, not SAC

This project trains vanilla **TD3** (Twin Delayed DDPG, Fujimoto et al.
2018) via Stable-Baselines3, not SAC, even though SAC is also a common
modern choice for continuous control. The reason is specific to this
thesis's later plan, not a general preference: `pi_td3_paper.pdf`'s
physics-informed contribution is defined as an ablation **on top of TD3**
(Algorithm 1 extends TD3's actor-critic update with a physics-informed
penalty term, reward Eq. 14). Week 4 needs to isolate the effect of adding
that physics-informed component as a single-factor change. If Week 3's
vanilla baseline were SAC, Week 4's "vanilla vs. physics-informed"
comparison would actually be measuring two simultaneous changes (SAC→TD3
*and* physics-uninformed→physics-informed), confounding the one comparison
this thesis is built around. Choosing TD3 now is what keeps that comparison
a clean ablation.

**Rejected alternative:** SAC. Plausibly a stronger baseline in isolation
(entropy-regularized exploration, generally more sample-efficient in some
benchmarks), but rejected because it would break the Week 4 ablation
structure described above — the choice here is driven by what Week 4 needs
to measure, not by which algorithm alone performs better on this
environment.

## 3.2 Reward function: `SqTrError_TrPenalty_UserIncentives`

Chosen from the 12 reward functions that actually exist in
`ev2gym/rl_agent/reward.py` (full list and preflight findings in
`00_lab_log.md`'s Week 3 entry) — not from an idealized reward this project
would prefer if the library offered it.

Two candidates fit this thesis's **Public/PST (Public Power Setpoint
Tracking)** problem variant at all (the rest require `simulate_grid=True`
or target the Business/V2G-ProfitMax scenario families this project does
not use):

| Candidate | What it optimizes | Fit to this thesis |
|---|---|---|
| `SquaredTrackingErrorReward` (env default) | Negative squared error between `min(power_setpoint, charge_power_potential)` and actual power usage. Nothing else. | Tracks the PST objective directly, but is blind to two of this thesis's three declared success criteria (satisfaction >90%, zero violations, profitability) — a policy could track the setpoint perfectly while leaving EVs undercharged or repeatedly overloading the transformer, and the reward would never signal it. |
| `SqTrError_TrPenalty_UserIncentives` **(chosen)** | Same squared tracking-error term, **plus** `-100 * tr.get_how_overloaded()` per transformer per step, **plus** `-1000 * (1 - score)` per departing EV's satisfaction score. | Directly penalizes two of the thesis's three declared success axes (transformer overload, user satisfaction) in addition to tracking, not just tracking alone. |

**Design decision:** use `SqTrError_TrPenalty_UserIncentives`, not the
environment's bare default. **Rejected alternative:** the plain
`SquaredTrackingErrorReward` default. Rejected because a reward that never
penalizes overload or dissatisfaction gives TD3 no training signal at all
toward two of this project's three declared success metrics — the agent
could legitimately learn a policy that maximizes tracking accuracy alone,
which this thesis would still have to judge unacceptable on the metrics
that matter for the grade. `SqTrError_TrPenalty_UserIncentives` is the closest existing function
to "optimize tracking while being penalized for the failure modes this
thesis actually cares about," without writing a new reward file (which
would be a legitimate option too, but the task brief's instruction is to
choose from what exists first).

**What this reward does NOT cover:** `total_profits` (the third declared
success axis). No reward function in `ev2gym/rl_agent/reward.py` that fits
the Public/PST variant includes a profitability term — the Public/PST family
is tracking-oriented by design, profit terms belong to the
Business/ProfitMax family which is a different scenario branch entirely (see
`00_lab_log.md`). This is a real, declared gap: TD3's training signal in
this project has no direct profitability incentive. `total_profits` is still
**measured and reported** in Entregable 6/7's evaluation (it's already a
registry column), just not optimized during training. See §3.3.

## 3.3 State function: `PublicPST`

`PublicPST` is the environment's own default state function and the only
one of the 5 functions in `ev2gym/rl_agent/state.py` that fits this
project's configuration (no price forecasts, no grid/voltage terms, no
`simulate_grid=True` requirement). The other 4
(`BusinessPSTwithMoreKnowledge`, `V2G_profit_max`, `V2G_profit_max_loads`,
`V2G_grid_state`) target other scenario families or need data this
project's config doesn't produce. There is no live alternative to reject
here — `PublicPST` is the only candidate that actually applies, which is
itself worth stating rather than presenting as if a choice among equals was
made.

`PublicPST`'s feature vector: normalized simulation timestep, the next-step
power setpoint, current aggregate power usage, and per-connected-port
`[is-full flag (1 or 0.5), cumulative energy exchanged, dwell time in
steps]` (zeros for empty ports). For `station_v0_bogota` (8 ports) this is a
27-dimensional vector — confirmed empirically
(`ev2gym_thesis/rl/env_factory.py`'s smoke test), not assumed from reading
the source alone.

## 3.4 Reward-vs-evaluation-metric misalignment (declared, not hidden)

TD3 optimizes a single scalar per step
(`SqTrError_TrPenalty_UserIncentives`'s weighted combination of tracking
error, overload penalty, and satisfaction penalty). This thesis is evaluated
on a **different, wider set of metrics**: `total_ev_served`,
`total_profits`, `average_user_satisfaction`, `energy_user_satisfaction`,
`min_energy_user_satisfaction`, `total_transformer_overload`,
`tracking_error`, `energy_tracking_error`, `battery_degradation` (the full
Entregable 6 table). These are related but **not the same object**:

- The reward's tracking term and `tracking_error`/`energy_tracking_error`
  are close but not identical (the reward uses a *squared*, per-step,
  potentially-clipped-by-transformer-limit term; the reported metric is
  computed independently by `get_statistics`).
- The reward's overload penalty (`-100 * get_how_overloaded()`) is a
  training-time deterrent; `total_transformer_overload` is the actual
  measured kWh of overload, on a completely different scale and sign
  convention.
- The reward's satisfaction penalty uses `-1000 * (1 - score)` per
  *departing* EV during the episode; `average_user_satisfaction` and the
  `min_`/`std_` satisfaction variants are computed over the full evaluation
  run's statistics, not accumulated the same way.
- `total_profits`, as established in §3.2, has **no representation in the
  reward at all**.

**Consequence, stated plainly:** a TD3 agent that achieves a high
(less-negative) cumulative reward during training is not guaranteed to be
the best-performing agent on this thesis's actual success criteria, and the
converse also holds — a policy that scores worse on the training reward
could still score competitively on `average_user_satisfaction` or
`total_transformer_overload` if its errors happen to fall outside what the
reward weights heavily. Entregable 6/7's evaluation therefore reports the
full metric table, not the training reward, as the basis for any comparison
claim — the reward is a training mechanism, not a stand-in for the thesis's
actual evaluation.

## 3.5 Registry consequence: `total_reward` is not comparable across algorithm families

AFAP and Round Robin (Weeks 1–2) were run under `SquaredTrackingErrorReward`
implicitly (`ev2gym_thesis/registry.py`'s `stats_to_row` records whatever
`env.step()`'s stats dict returns, which reflects the reward function passed
to `EV2Gym` — the default for those Week 1–2 runs). Week 3's TD3 rows use
`SqTrError_TrPenalty_UserIncentives` instead (§3.2). This means the
`total_reward` column in `results/master_results.csv` is **not a comparable
quantity between `algorithm_family="heuristic"` rows and
`algorithm_family="rl"` rows** — same column name, different underlying
formula, different scale, different sign conventions from the extra penalty
terms.

Three obligatory actions, all completed in this same session:

1. **Every new registry row's `notes` column records the reward and state
   function names** (e.g.
   `"reward=SqTrError_TrPenalty_UserIncentives,state=PublicPST,train_seed=100"`)
   — no new registry columns were added; `notes` (already part of
   `META_COLUMNS`) is the mechanism, per the task brief's explicit
   instruction not to change `REGISTRY_COLUMNS` without asking first.
2. **A guardrail was added to `ev2gym_thesis/figures.py`**
   (`assert_total_reward_comparable`) that raises if any figure attempts to
   plot/compare `total_reward` across rows whose `notes` field encodes
   different reward functions. `scripts/make_figures.py` does not currently
   plot `total_reward` at all (`METRICS_FOR_BARS` never included it), so
   this guardrail is a defense against a future mistake, not a fix to an
   existing figure.
3. **This limitation is stated here**, not left implicit: any thesis-level
   claim comparing "how well did algorithm X do" across the heuristic and RL
   families must use the shared, reward-independent metrics
   (`total_ev_served`, `average_user_satisfaction`,
   `total_transformer_overload`, `total_profits`, etc.), never
   `total_reward`.

## 3.6 Entregable 8 — Design note: the perfect-information reference (Week 4, not implemented here)

This is a design note only — no code, no numbers, respecting
`scripts/check_claims.py`'s restriction on optimality language until a row
using the registry's reserved-but-currently-unused `algorithm_family` value
for this kind of comparison exists (none does yet; this section itself was
checked against that script before committing).

**What the reference would be.** An offline upper bound computed with
perfect information: given the full day's EV arrival/departure/energy-need
schedule known in advance (not revealed incrementally, as every algorithm
tested so far experiences it), find the charging schedule that maximizes
the same combination of objectives this thesis cares about (subject to the
transformer power limit and each EV's charge-rate limit), and use its
achieved value as a ceiling that no causal (online) policy — heuristic, RL,
or otherwise — can exceed. This is the Week 3 brief's Entregable 8, deferred
here to a note precisely so Week 4 doesn't have to make this design call
under time pressure.

**Likely formulation.** For a fixed day and station (8 ports, 96 fifteen-
minute steps), assigning a charging power `p[i, t]` to each connected EV `i`
at each step `t`, subject to: `0 <= p[i,t] <= max_charge_power`,
`sum_i p[i,t] <= transformer_limit` for every `t`, and each EV's total
delivered energy across its dwell window bounded by its battery
capacity/desired SoC — is a **linear program (LP)** if charge power is
allowed to vary continuously step-to-step (the natural formulation, and the
one that matches how every algorithm tested so far actually controls
charging). No binary/integer variables are obviously required unless a
discrete on/off or fixed-tariff-tier constraint is added later, in which
case it would become a small MILP. Problem size for 8 ports x 96 steps: at
most 8 x 96 = 768 continuous decision variables (fewer in practice, since a
port only has a decision variable while an EV is actually connected), plus
96 transformer-capacity constraints and one energy-budget constraint per
EV — small by LP standards, solvable in well under a second per (seed,
day) cell with any of the solvers below.

**Viable free solvers.** HiGHS (via `scipy.optimize.linprog(method="highs")`
or via CVXPY/PuLP as a backend) is the most likely choice: it is a modern,
actively maintained, genuinely free (MIT-licensed) LP/MILP solver with no
academic-license dependency at all — unlike Gurobi, there is no capability
check to run and no email approval to wait for. CVXPY and PuLP are viable
modeling-layer alternatives that can both call HiGHS or other free
backends (CBC, GLPK); OR-Tools' linear solver wrapper is another option.
The concrete choice between "raw `scipy.optimize.linprog`" vs. "a modeling
layer like CVXPY/PuLP" is a Week 4 implementation decision, not made here.

**What is lost vs. Gurobi, and what is not.** Lost: Gurobi's presolve and
branch-and-cut performance advantage matters mainly at MILP scale or very
large LPs — irrelevant at this problem's size (a few hundred variables).
Not lost: solution correctness (HiGHS solves LPs to the same optimality
guarantees Gurobi does — an LP optimum is an LP optimum regardless of
solver, modulo numerical tolerance), reproducibility (no license file, no
network activation step, works identically on any machine), and cost (zero,
vs. depending on a "restricted, non-production" license this project
already confirmed is not usable per `CLAUDE.md` rule 6 and
`02_model_validation.md`'s Gurobi section). For a problem this small, the
choice of free LP solver over Gurobi is not expected to change any reported
number — it changes only which software computed it.

## 3.7 Hyperparameters

Every value below has a declared origin (`ev2gym_thesis/rl/config_rl.py`,
verbatim comments per constant) — none is an unlabeled guess.

| Parameter | Value | Origin |
|---|---|---|
| Policy | MlpPolicy | SB3 default (flat-vector observation, not an image) |
| Network architecture | [64, 64] | Reduced from SB3 default / TD3 paper [400, 300], for this project's CPU budget (27-dim obs, 8-dim action — far smaller than the paper's benchmarks) |
| Learning rate | 1e-3 | SB3 default |
| Discount factor (gamma) | 0.99 | SB3 default |
| Soft update rate (tau) | 0.005 | SB3 default |
| Train frequency | 1 step | SB3 default |
| Gradient steps | 1 | SB3 default |
| Policy delay | 2 | SB3 default / TD3 paper |
| Target policy noise | 0.2 | SB3 default / TD3 paper |
| Target noise clip | 0.5 | SB3 default / TD3 paper |
| Batch size | 256 | SB3 default |
| Replay buffer size | 50,000 | Reduced from SB3 default 1,000,000, for this project's CPU budget (a 1e6 buffer would stay mostly empty at this run's scale) |
| Learning starts | 500 steps (~5 episodes) | Increased from SB3 default 100, for this project's CPU budget (more pure-exploration data before the first gradient update, proportionally larger given the short total run) |
| Exploration noise (sigma) | 0.1 | TD3 paper (relative to this project's [0,1] action range, not the paper's symmetric [-1,1]) |
| VecNormalize (obs + reward) | on, clip_obs=10.0 | Empirically set inside this project — design decision documented in S3.2/config_rl.py: this environment's observation mixes wildly different feature scales |
| Training seeds | [100, 101, 102] | Empirically set inside this project, sized against the confirmed CPU budget |
| Total timesteps/seed | 60,000 | **User-confirmed 2026-08-12** after the Entregable 4 calibration (measured 18.09 steps/s); see `00_lab_log.md` |
| Checkpoint frequency | 10,000 steps | Empirically set inside this project (resumability granularity) |
| Learning-curve log frequency | 500 steps | Empirically set inside this project |

## 3.8 Results

**Training** (Entregable 5): 3/3 seeds trained, 167.6 min (2.79h) total wall
clock (vs. 165.9 min estimated). Learning curves show a small but
consistent positive trend across all 3 seeds (+21 to +30 reward/1,000
steps), not clean convergence — see `figures/f08_learning_curves.png` and
`00_lab_log.md`'s 2026-08-13 entry for the full numeric breakdown.

**Evaluation** (Entregable 6), `station_v0_bogota`, n=50 per algorithm
(5 `SEEDS` × 10 `EVAL_DAYS`), mean [95% CI] — **corrected 2026-08-18, see
S3.11; do not cite the pre-correction numbers this table used to hold**:

| Algorithm | EVs served | Profits | Avg. satisfaction | min energy satisfaction | Transformer overload (kWh) |
|---|---|---|---|---|---|
| AFAP | 13.44 | -45.73 | 1.000 | 100.00 | 5.33 [1.93,8.73] |
| Round Robin | 13.44 | -44.51 | 1.000 | 99.95 | 0.00 |
| TD3 (seed 100) | 13.44 | -39.23 | 0.976 | 78.25 | 0.45 [0.00,0.93] |
| TD3 (seed 101) | 13.44 | -38.69 | 0.979 | 83.80 | 2.65 [0.65,4.68] |
| TD3 (seed 102) | 13.44 | -42.64 | 0.991 | 85.49 | 0.96 [0.13,1.81] |
| RandomPolicy (control) | 13.44 | -46.14 | 1.000 | 100.00 | 0.22 [0.00,0.52] |

Full 9-metric table and the paired-bootstrap comparisons against AFAP and
Round Robin are in `00_lab_log.md`'s 2026-08-18 correction entry and
`results/rl_vs_baseline_bootstrap.csv`.

**The random-policy control does NOT support the "TD3 learned a real
overload-avoidance behavior" claim under the corrected data — see S3.11
for the full reversal.** In short: the corrected control's overload (0.22
kWh) is *significantly lower* than AFAP's (5.33 kWh, paired bootstrap 95%
CI [-8.76,-1.91]) and statistically indistinguishable from TD3 (seed 100)'s
(CI [-0.23,0.80] spans zero) — the opposite of what the pre-correction data
showed and the opposite of what this section used to conclude from it.

**Cross-training-seed dispersion** (Entregable 7, separate from the
scenario-level CIs above, recomputed on corrected data): `total_ev_served`
now has **zero** spread (all three seeds converge to AFAP/RR's exact 13.44 —
the "seed-inconsistent EVs served" finding was itself an artifact of the
pre-correction bug); `total_transformer_overload` spread is now the
standout at 162.4% relative (largely a division-by-near-zero artifact, as
in Week 3's original table, since the underlying values are themselves
small); `tracking_error` spread is 13.3%, smaller than the pre-correction
48.9%. Full table in `00_lab_log.md`.

## 3.9 Conclusions

**Corrected 2026-08-18 — see S3.11; this section previously drew a
conclusion the corrected data does not support.** Under this week's
declared, reduced training budget, TD3 vanilla **reduces transformer
overload relative to unmanaged AFAP** (statistically significant for 2 of
3 seeds; the third's CI spans zero) but **does not match Round Robin's
near-elimination of it** — TD3 is significantly *worse* than Round Robin
on overload for all 3 seeds (paired bootstrap 95% CIs all exclude zero:
+0.45, +2.65, +0.96 kWh). Critically, TD3's overload reduction is **not
distinguishable from the random-policy control's** for seed 100 (CI spans
zero) — the control that was meant to demonstrate "TD3 learned something a
naive policy doesn't" instead shows that *not always dispatching at
maximum power*, which uniform random sampling does for free, already
removes most of this station's overload at its 4:1 oversubscription ratio.
This is a materially weaker claim than Week 3 originally reported, and it
is reported as such rather than reframed after the fact.

The `total_ev_served` tradeoff reported in the original version of this
section (lower and seed-inconsistent for TD3) **does not survive
correction either** — all three TD3 seeds now serve exactly the same
number of EVs as AFAP and Round Robin (paired bootstrap point estimate
0.000, CI [0.000, 0.000] against both baselines, for all 3 seeds). The
cost that *does* survive correction, and is now larger than originally
reported, is `min_energy_user_satisfaction`: materially and consistently
lower than every non-RL policy (78.3%/83.8%/85.5% vs. ~100% for
AFAP/Round Robin/RandomPolicy, all three paired-bootstrap CIs excluding
zero against both baselines). TD3 also tracks the power setpoint *worse*
than Round Robin, now by a larger margin than originally reported (+137%
to +164%, vs. the pre-correction +49% to +152%) — consistent with, and now
more strongly evidencing, the declared reward-vs-metric misalignment
(S3.4). None of the three training seeds can be called uniformly better or
worse than the others; the dispersion across seeds is itself a reportable
result.

At this station's 4:1 oversubscription ratio, the corrected data supports
a narrower claim than originally drawn: TD3 reduces overload versus
unmanaged charging, at a real and now larger cost in worst-case user
experience and tracking precision, but the evidence that this reduction
reflects *learned coordination* beyond what naive throttling already gives
is weak — the random-policy control, correctly evaluated, does not clearly
distinguish TD3 from a policy that learned nothing at all. Whether the
tradeoff that does hold up is "worth it" is not something this thesis can
answer with the vocabulary available yet (the registry's
reserved-but-currently-unused `algorithm_family` value for a
perfect-information comparison point does not have any rows yet) — it can
only report that the (narrower) tradeoff is real and quantified.

## 3.10 Limitations

- **Training budget is a drastic reduction against the source papers**
  (2.79h total across all 3 seeds vs. 5-48h per single run on HPC in the
  PI-TD3/TD3 papers). Convergence claims must be read against this — the
  observed weak learning signal is a legitimate result of this reduced
  scope, not evidence that TD3 cannot learn this task with a larger budget.
- **`total_reward` is not comparable across algorithm families** (S3.5) —
  AFAP/Round Robin used the environment's default reward,
  `SqTrError_TrPenalty_UserIncentives` was used for TD3. Enforced by a
  guardrail in `ev2gym_thesis/figures.py`.
- **No profitability signal in the reward** (S3.2) — TD3's apparently
  better `total_profits` is not an intentional achievement. **Corrected
  2026-08-18 (S3.11):** the pre-correction explanation ("confounded with
  serving fewer EVs") no longer holds — `total_ev_served` is now identical
  across every algorithm (S3.9). The likelier confound, per `f02`'s energy-
  charged panel, is that TD3 delivers less energy per served EV (lower
  `total_energy_charged` at the same EV count), which lowers both charging
  cost and delivered satisfaction together — not an intentional profit
  optimization either way.
- **Trained and evaluated on `station_v0_bogota` only** — the CPU budget
  did not cover training across the station-size sweep (`f06`'s station
  sensitivity figure correctly excludes TD3/RandomPolicy for this reason,
  fixed during this week's visual QA).
- **Reward-vs-evaluation-metric misalignment is real and demonstrated**,
  not just declared in the abstract: `tracking_error` is measurably worse
  for TD3 than for Round Robin despite TD3 optimizing a tracking-based
  reward (S3.4, S3.8).
- **A perfect-information reference does not exist yet** — no claim in
  this chapter or elsewhere in the thesis may describe any tested strategy
  using language that implies a proven best-possible solution was
  identified, until Week 4 adds that reference point (enforced mechanically
  by `scripts/check_claims.py`). The permitted phrasing is
  "best-performing among the strategies tested."

## 3.11 Correction, 2026-08-18: TD3/RandomPolicy evaluation ran uncontrolled scenarios

**Found while doing Week 4 preflight work**, not while working on Week 3:
building the perfect-information oracle's replay-vs-`make_env` parity check
required proving, empirically, that an evaluation episode's EV population
matches the `(config, day, scenario_seed)` cell it's registered under. The
same check applied to this chapter's existing TD3/RandomPolicy evaluation
path failed. Full technical diagnosis, the reproduction method, the
call-site audit, and the fix are in `00_lab_log.md`'s 2026-08-18 entry —
not repeated in full here to avoid the two documents drifting apart; this
section states the narrative consequence for this chapter specifically.

**Root cause, in one sentence:** `scripts/evaluate_rl.py`'s `_TD3Stepper`
and `_RandomPolicyStepper` started each evaluation episode with
`env.reset()` (no seed), which silently draws a fresh random EV scenario
instead of reusing the `scenario_seed` the env was constructed with — so
all 200 TD3/RandomPolicy evaluation episodes (Entregable 6) were measured
against scenarios nobody chose, not the registered 50-cell grid. AFAP and
Round Robin (Weeks 1–2, `scripts/backfill_registry.py`) were unaffected —
confirmed empirically with the identical method, not assumed.

**What changed in this chapter as a result** (S3.8/S3.9/S3.10 above are now
the corrected versions; the numbers and conclusions they held before this
date are superseded, not deleted — see `00_lab_log.md` for the full
old-vs-corrected table):

1. **`total_ev_served` "lower and seed-inconsistent for TD3" — did not
   survive correction.** All three TD3 seeds now serve exactly 13.44 EVs on
   average, identical to AFAP and Round Robin (paired bootstrap point
   estimate 0.000 against both, for all 3 seeds). This was an artifact of
   the bug, not a real property of the trained policies.
2. **`min_energy_user_satisfaction` cost — real, and larger than reported.**
   78.3%/83.8%/85.5% for the three seeds (was 93.1%/92.3%/86.7%), still
   materially below every non-RL policy's ~100%.
3. **Transformer overload vs. Round Robin — reverses from "matches" to
   "significantly worse."** All 3 TD3 seeds now show statistically
   significant overload relative to Round Robin (95% CIs excluding zero:
   [0.03,0.98], [0.90,4.80], [0.21,1.84] kWh), not the near-zero parity
   originally reported.
4. **The random-policy control's argument — the most consequential
   reversal.** Originally: control shows worse overload (12.74 kWh) than
   AFAP (5.33 kWh), proving TD3's near-zero overload is learned, not
   incidental. Corrected: control shows **significantly lower** overload
   than AFAP (0.22 kWh, 95% CI [-8.76,-1.91] vs. AFAP) and is
   **statistically indistinguishable** from TD3 (seed 100) (CI
   [-0.23,0.80]). A uniform-random policy's expected ~0.5x-max-power
   dispatch already avoids most of this station's overload at its 4:1
   oversubscription ratio, with no learning involved — the control no
   longer separates "TD3 learned something" from "any policy that doesn't
   dispatch at maximum power like AFAP does."

**What did not change:** the training run itself (weights, learning
curves, wall-clock, the weak-but-consistent convergence signal) — this bug
is entirely in the evaluation path, not training. The reward-vs-metric
misalignment finding (S3.4) is unchanged in direction and now better
evidenced (the tracking-error gap vs. Round Robin widened under
correction, from +49%–+152% to +137%–+164%).

**Verification performed before trusting the corrected numbers:** all 200
episodes re-run through the fixed pipeline (200/200 appended, 0 skipped);
old rows preserved in
`results/master_results_prefix_week3_evaluation_bug.csv` rather than
overwritten; `results/rl_vs_baseline_bootstrap.csv` and
`results/rl_train_seed_dispersion.csv` regenerated with the same,
unmodified `stats_utils.paired_bootstrap_ci`; all 9 figures regenerated
and individually visually QA'd (no new bugs found this pass); the full
`test_rl_infrastructure.py` suite re-run (10/10 passing, including 2 new
regression tests for this exact bug — see `00_lab_log.md`).
