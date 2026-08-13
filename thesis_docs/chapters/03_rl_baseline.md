# Chapter 3 — RL Baseline Vanilla: TD3 (Week 3)

> Status: this chapter is being written incrementally as Week 3 progresses
> (branch `semana-3`). As of this section, Entregables 1–3 and 8 are
> complete (reward/state choice, `ev2gym_thesis/rl/` package, this
> justification, and the perfect-information-reference design note below); Entregables
> 4–7 and 10 (training, evaluation, statistics, figures, the hand-back
> document) follow after the Entregable 4 CPU-budget confirmation, per
> `CLAUDE.md` rule 2. See `thesis_docs/chapters/00_lab_log.md`'s 2026-08-12
> Week 3 entry for the full preflight this chapter's choices are based on.

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
