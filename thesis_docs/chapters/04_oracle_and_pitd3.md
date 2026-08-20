# Chapter 4 — Perfect-Information Oracle, Physics-Informed Reward Falsification, and the Tracking-Only Ablation (Week 4)

**Title updated 2026-08-20; filename kept unchanged.** The original title
("Perfect-Information Oracle and PI-TD3") described the planned
investigation; it undersold the finished chapter, which delivers three real
components (the oracle, S4.1-S4.2/S4.6-S4.7; the falsification, S4.3; and
the `TD3_TrackingOnly` ablation that replaced the originally-planned trained
`PI_TD3` arm, S4.4/S4.8-S4.10). The title is updated to name all three; the
filename (`04_oracle_and_pitd3.md`) is deliberately left unchanged, since
dozens of existing cross-references across `00_lab_log.md`,
`PROJECT_ROADMAP.md`, `CLAUDE.md`, and this week's hand-back document point
at that exact path — renaming it would require updating every one of those
links for a purely cosmetic gain, and risks a stale/broken reference
somewhere they were missed. The filename documents which week produced this
chapter and its original planned scope; the title documents what it
actually contains.

> Status: complete as of 2026-08-20. All Entregables (1–14 per the Week 4
> closeout brief) done: preflight, oracle (both variants, 100/100 cells),
> two falsified reward-only physics-adaptation attempts (S4.3), the
> `TD3_TrackingOnly` reward ablation trained (3 seeds, 168.43 min total)
> and evaluated (150 rows, 550-row main-grid registry = 11 algorithms x 50
> cells exactly), analyzed (S4.9), and verdicted (S4.10). **A same-day
> acceptance review found the first draft of S4.9/S4.10 overstated the
> reward-ablation result and understated the RL-vs-Round-Robin gap-to-oracle
> finding — both corrected in place, marked, not silently rewritten** (see
> S4.9(1)/(3) and S4.10 items 3–4); also added a per-metric noise-floor
> table (S4.9(4), replacing a single global statement) and a proposed
> energy-not-served target mapping (S4.9). Full session history, including
> the Week 3 evaluation-bug detour, the reference-acquisition detour, and
> the two PI-TD3 design iterations and why each failed, in
> `thesis_docs/chapters/00_lab_log.md`'s 2026-08-18/19/20 entries.

## S4.0 Scope deviation, stated up front

Week 3's handback document declared Week 4 as *"a perfect-information
reference (free solver, no Gurobi) + PI-TD3."* **That is now amended: a
Gurobi academic license is active and verified on this machine, so the
perfect-information reference uses Gurobi via EV2Gym's own
`ev2gym/baselines/gurobi_models/`, not a free solver.** Verified directly,
not assumed: `gurobipy` reports `LicenseID 2853634`, `"Academic license -
for non-commercial use only - expires 2027-08-14"` — unlimited (no
2,000-variable/2,000-constraint cap), confirmed by building and solving a
real ~9,000-variable model for `station_v0_bogota` (S4.7).

This is a **reduction** in deviation from the original `PROJECT_ROADMAP.md`
(which always assigned the Gurobi/MPC baseline to this phase), not a new
one — Week 2/3 moved to a "free solver" plan only because the license
available at the time was a size-limited `"Restricted — for non-production
use only"` license, not an academic one. That superseded reasoning is kept,
not deleted, in `PROJECT_ROADMAP.md`'s Phase → Objective Mapping amendment
and `02_model_validation.md`'s Gurobi section, both dated 2026-08-18.

**A second, unplanned correction happened first and delayed this chapter.**
Building this chapter's own replay-vs-scenario parity check (S4.5's
methodology) surfaced a bug in Week 3's *evaluation* pipeline — unrelated
to Gurobi, but serious enough that Week 4 was paused to fix it before
proceeding. Full account in `00_lab_log.md`'s 2026-08-18 correction entry
and `03_rl_baseline.md` S3.11. Not repeated here; this chapter's own content
below was not affected (the oracle's replay-generation path was built with
that bug's exact failure mode in mind from the start, see S4.5).

**`[SUPERSEDED]` 2026-08-19, kept for the record, not deleted: Part B's
scope changed from delivering a trained "PI-TD3" arm to a falsified
physics-adaptation attempt plus a reward ablation.** Two independent
reward-only adaptations of PI-TD3's physics-informed principle
(voltage-band → transformer-capacity analogue) were designed, built, and
verified before either was trusted with training compute — both failed,
for structurally different and now well-understood reasons (S4.3). No arm
in this thesis is named `PI_TD3`/`PI-TD3` anywhere in the registry, code,
or results. Part B's actual second training arm is `TD3_TrackingOnly`, a
reward ablation Week 3 never ran (S4.4) — a real, if smaller, contribution
this week still delivers, in place of the originally planned one. A
faithful PI-TD3 port is recorded as a conditional stretch goal for the
Week 6 grid-enabled phase (S4.3), not a commitment.

## S4.1 What a perfect-information oracle is, and is not

An offline, perfect-information oracle solves the charging-schedule problem
with the entire day's EV arrival/departure/energy-need schedule known in
advance — not revealed incrementally, the way AFAP, Round Robin, TD3, and
PI-TD3 all experience it. **It is not a deployable controller.** It sees
the future. Reporting it as if it were a competing strategy — "the oracle
achieves X" alongside "TD3 achieves Y" as parallel rows in a leaderboard —
would misrepresent what it is.

Its purpose in this thesis is narrower and specific: to bound how much
headroom remains between what the best-performing *tested* (causal, online)
strategy achieves and what is achievable at all on the same problem, given
perfect foresight. It answers "how much of the remaining gap is a real
online-algorithm limitation, and how much was never closeable without
seeing the future" — not "which algorithm should be deployed."

## S4.2 Oracle selection rationale

Three candidate Gurobi models exist in `ev2gym/baselines/gurobi_models/`,
read from source (not inferred from filenames or the EV2Gym paper alone):

| Class | File | Objective | V2G? | Grid? | Verdict |
|---|---|---|---|---|---|
| `PowerTrackingErrorrMin` | `tracking_error.py` | minimize Σ(power − `power_setpoints`)² | allows discharge unless bounded to 0 | none (transformer current limits, hard constraint) | **Selected, as the tracking-only base** |
| `V2GProfitMaxOracleGB` | `profit_max.py` | maximize revenue − 100·(departure satisfaction penalty) | allows discharge unless bounded to 0 | none | Rejected |
| `V2GProfitMax_Grid_OracleGB` | `v2g_grid.py` | minimize voltage-limit slack (linearized power flow) | yes | requires `simulate_grid=True` | Rejected — out of scope |

A fourth, adjacent option was checked and rejected on different grounds:
`ev2gym/baselines/mpc/V2GProfitMax.py` also depends on `gurobipy` but is
**receding-horizon MPC**, not offline perfect-information — the wrong kind
of reference point for this section regardless of its objective. Kept as a
candidate for Weeks 6–7 if a deployable (not offline) optimizer becomes
relevant to the infrastructure-guidelines phase; not implemented here.

**Why `V2GProfitMax_Grid_OracleGB` is rejected:** requires `simulate_grid=True`
grid data (`replay.active_power`, `.K`, `.L`, populated only under grid
simulation) — this thesis keeps `simulate_grid=False` through Objectives
1–3 (Weeks 1–4), per the standing grid-scope note in `PROJECT_ROADMAP.md`
and `02_model_validation.md`. Reserved for Weeks 6–7, not usable now.

**Why `V2GProfitMaxOracleGB` is rejected:** its objective family
(Business/V2G-ProfitMax) was already explicitly rejected for this thesis's
RL work in Week 3 (`03_rl_baseline.md` §3.2: *"profit terms belong to the
Business/ProfitMax family which is a different scenario branch entirely"*)
— using it for the oracle would bound a different problem than the one
every other algorithm in this thesis is being evaluated on. Its
charge/discharge prices are also the same Dutch-sourced electricity price
data already flagged as a declared limitation elsewhere in this project
(`02_model_validation.md`).

**Why `PowerTrackingErrorrMin` is selected:** it is the only one of the
three whose objective matches this thesis's chosen problem family —
Public/PST (Public Power Setpoint Tracking) — the same family Week 3's
reward/state choice was justified against (`03_rl_baseline.md` §3.2–§3.3).
`station_v0_bogota.yaml`'s own `power_setpoint_enabled: true` and
`load_power_setpoints()` being called unconditionally regardless of grid
mode (`ev2gym_env.py:296`) confirm this is a native, always-meaningful
quantity for this scenario, not a grid-only concept.

**Two changes were required, both made as an `ev2gym_thesis/`-side
wrapper — the unmodified `gurobi_models/tracking_error.py` is never
edited in place:**

1. **Forced G2V bounds.** `v2g_enabled: False` in `station_v0_bogota.yaml`
   only gates the RL/heuristic action-space sign (`ev2gym_env.py:227`) — it
   does **not** zero the replay's `port_max_discharge_current`/
   `port_min_discharge_current`, which come straight from
   `charging_station.max_discharge_current`/`min_discharge_current`
   regardless (`replay.py:89-90`). Fed unmodified, the oracle would have
   V2G capability none of AFAP/Round Robin/TD3 have, and its "upper bound"
   would not be a bound on the same problem. Fixed by
   `ev2gym_thesis/oracle/replay_utils.force_g2v`, which zeroes these two
   fields on a **copy** of the replay before it reaches the unmodified
   Gurobi class.
2. **A satisfaction term — see Amendment 1 below, not applied to this
   variant.**

### Amendment 1 (user-directed, 2026-08-18): two oracle variants, not one

`PowerTrackingErrorrMin`'s objective minimizes tracking error alone;
transformer compliance is a hard constraint (trivially 0 in every feasible
solution — informative as a sanity check, but not a differentiator, since
Round Robin already achieves 0 too); user satisfaction is not represented
at all. A single "bound" that added a satisfaction penalty term to the
objective would no longer be the true optimum on tracking error alone —
composite objectives are not decomposable bounds. So this thesis reports
**two** oracle variants, answering two different questions, neither one a
hedge:

- **`Optimal_Oracle_Tracking`** — `PowerTrackingErrorrMin`'s objective
  untouched, G2V-forced only. The defensible upper bound on tracking error,
  and the one Entregable 10's oracle-bound-sanity tripwire test is checked
  against.
- **`Optimal_Oracle_Balanced`** — same model, plus a quadratic
  departure-satisfaction penalty mirroring `profit_max.py`'s existing
  `user_satisfaction` term (no price/profit component). Answers "what does
  perfect foresight buy on tracking *and* satisfaction at once."
  **Implemented and evaluated over the full 50-cell grid — see S4.6-S4.7**;
  the "not yet implemented" language earlier in this section described the
  design-phase skeleton and is now stale, corrected 2026-08-20.

The penalty weight got a named constant with a declared origin
(`SATISFACTION_PENALTY_WEIGHT = 1.0` in
`ev2gym_thesis/oracle/balanced_model.py`, `"adapted from profit_max.py's
departure-satisfaction penalty in STRUCTURE, not scale"`) — see that
constant's own comment for the full reasoning. **The planned 0.5x/1x/2x
single-cell sensitivity sweep on this weight was not run.** It is not
required for this chapter's claims (verified live/dead via the five-step
protocol in S4.6 instead, a stronger check for the question that actually
mattered — whether the term does anything at all — than a weight sweep
would have been), but is flagged here as a real, unclosed gap rather than
silently dropped: if a reviewer specifically asks "how sensitive is the
balanced oracle's bound to this weight choice," that question remains
open.

**Transformer compliance is not a meaningful "distance from the bound"
metric** for either variant: it is a hard constraint in both, so that
distance would measure a constraint that was imposed, not a quantity that
was optimized — not a meaningful comparison, and Round Robin already
reaches 0 on this axis without any oracle.

## S4.3 PI-TD3: what "physics-informed" means here, and what it does not

**Read in full: `pi_td3_paper.pdf` (arXiv:2510.12335v2).** Algorithm 1 and
Eq. 14 are cited by number below, per the task brief's requirement and
`CLAUDE.md` rule 3 (never reconstruct a paper's equations from memory).

### The central finding that reframed this section's design question

The brief's original framing (§4.1) asked which components of PI-TD3's
*reward* have a transformer-capacity analogue. Reading the paper in full
surfaced something the brief did not anticipate: **PI-TD3's actual novel
mechanism is not primarily its reward shape.** Algorithm 1 line 11
("Update actor using ∇θJ(θ) from (20)") replaces TD3's standard
single-transition actor update with a **K-step, model-based, differentiable
rollout**: a differentiable transition model (Eq. 18, the piecewise SoC
update) and a differentiable reward model (Eq. 14, including a
power-flow-derived voltage term) simulate K steps forward, sampling only
exogenous variables (prices, arrivals, loads) from the replay buffer, and
backpropagate gradients directly into the actor network — bypassing the
environment entirely for the actor's gradient signal. Fig. 3b's own
rollout-horizon ablation (K=5/10/20/40, four-fold difference in final
reward between K=5 and K≥20) is the paper's own evidence that **this
mechanism, not the reward term alone, drives PI-TD3's sample-efficiency
gain** over vanilla TD3 (Fig. 3a: PI-TD3 reaches vanilla TD3's asymptotic
performance in ~1/4 the epochs).

Porting Algorithm 1's actual mechanism would require building a
differentiable transition model for this thesis's own charging dynamics
and replacing Stable-Baselines3's `TD3.train()` actor-update step entirely
— not a swappable reward/state module the way Week 3's infrastructure was
designed for, but a different training loop. `simulate_grid=False` also
has no power-flow model to differentiate through even if this were built.

**Presented to the user as a genuine "is this adaptation too thin to be
worth calling PI-TD3" moment, per the brief's own escape hatch.** Decided
2026-08-19: proceed with the **thin, reward-only adaptation**, explicitly
declared as such rather than presented as a faithful port. The rejected
alternative (the full differentiable-rollout mechanism) is recorded here,
not silently dropped, as the more faithful port a future Week 6-7 grid-
enabled phase could revisit once a power-flow model exists to differentiate
through.

### A genuine ambiguity found in Eq. 14, recorded rather than resolved either way

Applying the paper's own stated `λ1 = −5×10⁴` (Sec. IV-A) literally to
Term 1: the bracketed quantity is ≤0 (zero when compliant, more negative
when violated). A **negative** `λ1` therefore makes `λ1 · [bracket]`
increasingly **positive** as violations worsen — under a **maximized**
reward (Eq. 16, Algorithm 1), this rewards *larger* violations, the
opposite of the paper's own prose description ("the first term penalizes
voltage deviations", Sec. II-B). This may be a genuine sign inconsistency
in the paper, or a misreading introduced by this PDF's extraction of a
multi-line, subscript-heavy equation (a known risk of that extraction
method) — not resolved with confidence either way. Not that it mattered in
the end: neither design attempt below reused the paper's literal
coefficient, for the reasons given in each.

### What was ported, tried, and falsified: a reward-only physics term does not survive contact with this configuration

Two structurally different designs for the Eq. 14 Term 1 analogue
(voltage band → transformer capacity) were built and verified — both
failed, for different reasons, before either was trusted with three hours
of training. This is reported as the result it is, not as a delay before
a "real" result: **a reward-only physics-informed adaptation is not
achievable in this configuration**, and the mechanism is now understood
precisely enough to say why, and what would need to be true elsewhere in
this thesis for it to work.

**Design 1 — instantaneous capacity margin.** `transformer_capacity_margin_term`
(kept in `ev2gym_thesis/rl/reward_pi.py`, unused, for the record): 0 while
`current_power < 0.95 × transformer_max_power`, ramping linearly negative
above that pre-violation threshold — an action-dependent quantity, since
`current_power` is a direct function of the agent's chosen action.
Verified via `scripts/verify_pi_reward_differs.py`: Spearman rank
correlation against the vanilla reward's existing `-100 *
get_how_overloaded()` term was **exactly 1.0 at every weight tested (20
through 2000)**.

| Weight | Pearson (full episode) | Spearman | mean \|ratio\| at relevant steps |
|---:|---:|---:|---:|
| 20 | 0.999977 | 1.0000 | 2.7% |
| 100 | 0.999554 | 1.0000 | 13.5% |
| 300 | 0.997529 | 1.0000 | 40.6% |
| 1000 | 0.991130 | 1.0000 | 135% |
| 2000 | 0.986452 | 1.0000 | 271% |

**Mechanism:** both terms are monotonic functions of the same single
scalar — instantaneous power versus instantaneous capacity. Any two
monotone functions of the same scalar induce the same step ordering; the
weight can rescale the numeric gap (Pearson falls) but can never create a
ranking disagreement (Spearman cannot move). No amount of recalibration
could have fixed this — it is a structural property of using the *action's
realized outcome* as the term's only input, proven by the sweep itself
before a single training step ran.

**Design 2 — capacity-headroom / latent-exposure.** `headroom_penalty_term`:
uses `env.charge_power_potential` — the power the *connected fleet* could
draw at maximum rate, a function of which EVs are present and their state,
not directly of the action taken — against the transformer's near-future
minimum capacity. Genuinely broke the Spearman=1.0 tie (mean 0.9855 across
6 (day, seed) cells, `scripts/verify_headroom_term.py`), but a second,
independent verification (the same script, required before trusting any
result that "worked") found why it moved: `charge_power_potential`
excludes any EV once it reaches 100% SoC, so charging EVs to full **faster**
removes them from the term's sum, regardless of whether that fast charging
caused a real overload.

| Check | AFAP | Round Robin |
|---|---:|---:|
| Headroom term nonzero steps (of 96) | 2 | 27 |
| Headroom term sum | −99.3 | −3236.1 |
| Correlation(headroom term, mean fleet SoC) | +0.68 | +0.66 |

Round Robin — the heuristic that already nearly eliminates transformer
overload (Week 1-3 results) — was penalized **~32× more often** than
AFAP, the unmanaged baseline that overloads this station routinely. The
strongly positive SoC correlation confirms the mechanism directly: raising
fleet SoC *lowers* the penalty. **The term's gradient points toward
charging faster and more completely — toward AFAP — not toward
capacity-aware pacing.** This is not a calibration problem either; it is
a structural property of any measure of *pending demand* under an
uncontrolled completion time.

A repair considered and rejected: weighting the term by each EV's
*remaining* need rather than counting it fully or not at all. This
relocates the same flaw rather than fixing it — any function of "how much
is still owed" falls when the owing is paid off sooner, so "finish
everyone as fast as possible" remains a way to minimize the penalty. The
signal that would actually resist this — infeasibility relative to a
**departure deadline**, since total remaining energy against a fixed
deadline does not shrink just because charging was eager — needs each EV's
time of departure, and `ev2gym.rl_agent.state.PublicPST` withholds that
information *deliberately*, because a real public-station operator does
not have it either (confirmed by reading `state.py:6-63`: the exposed
per-EV features are a full/not-full flag, cumulative already-delivered
energy, and elapsed — not remaining — dwell time; see the state-extension
question resolved below). Both design failures trace back to the same
wall from two different directions.

**Also considered and rejected:** extending `PublicPST` to expose
departure time, which would have fixed Design 2's flaw directly. Rejected
on realism grounds, not cost: a public charging station's operator does
not know when a walk-up user intends to leave, and `PublicPST`'s omission
of this is the EV2Gym paper's own deliberate modeling choice for the
Public-PST problem family (Sec. III-A: *"we assume that information about
EV arrival and departure time... is unavailable"*) — the same family this
thesis chose in Week 3 specifically because it fits a public station.
Extending the state would let the learned policy depend on information a
real Bogotá operator would not have, undercutting this thesis's realism
claim more than a weaker physics term costs it. Extending the state for
only the PI arm was also rejected: it would make the arm differ from
vanilla TD3 in two variables (state *and* reward), so no result could be
attributed to either one.

**Consequence, stated as a finding, not a limitation buried in a
paragraph:** PI-TD3's physics-informed mechanism requires the physics it
was designed for. A voltage constraint is (a) genuinely absent from any
reward this thesis's baseline already uses, (b) reducible by *temporal
load shifting* rather than simply by charging faster or more completely,
and (c) observable in a way that doesn't require assuming information a
real operator lacks. None of the three hold for a transformer-capacity
substitute under `simulate_grid=False` and `PublicPST` — (a) fails for
Design 1, (b)/(c) fail for Design 2. All three hold once
`simulate_grid=True` and the IEEE 34-bus feeder exist (Week 6-7): voltage
is a per-bus quantity the baseline reward has no term for, reducible by
shifting *which bus* or *when* charging happens rather than by charging
speed alone, and observable from the grid model without assuming
knowledge of user intent. **This is recorded as a conditional stretch
goal for the Week 6 infrastructure phase, not a commitment** — if that
phase's own scope leaves room, a faithful PI-TD3 port (voltage band, and
possibly the Algorithm 1 rollout mechanism deferred in this chapter's
opening) is the natural next attempt; if it doesn't, this chapter has
already explained why Week 4 did not attempt a thinner substitute.

`reward_pi.py` and both failed designs stay in the repository and in git
history — they are the evidence for this section, not dead code to prune.

## S4.4 Controlled comparison: `TD3_TrackingOnly` reward ablation

With the physics-adaptation line closed, Week 4's second training arm
answers a question Week 3 assumed rather than measured: **does encoding
transformer overload and user-satisfaction penalties into the training
reward (`SqTrError_TrPenalty_UserIncentives`, Week 3's choice, justified
by reasoning in `03_rl_baseline.md` S3.2) actually buy anything over
optimizing tracking error alone (`SquaredTrackingErrorReward`, EV2Gym's
own bare default)?**

**Held identical to Week 3's vanilla-TD3 arm:** total timesteps
(60,000/seed), `TRAIN_SEEDS` ([100, 101, 102]), `TRAIN_DAYS` round-robin
sampling, state function (`PublicPST`), network architecture ([64, 64]),
replay buffer, `VecNormalize` setup — every hyperparameter in
`ev2gym_thesis/rl/config_rl.py`. **Deliberately differs:** the reward
function only — `SquaredTrackingErrorReward` in place of
`SqTrError_TrPenalty_UserIncentives`, both pre-existing, unmodified
`ev2gym.rl_agent.reward` functions, so this arm needs no new adaptation,
no sign-convention question, and no observability question — a genuinely
single-variable comparison, in contrast to the two design attempts above.
Selected via `scripts/calibrate_td3_timing.py`/`scripts/train_td3.py`'s
existing `--reward` flag (`vanilla`/`pi` extended to include
`tracking_only`), not a fork.

**`total_reward` is not comparable between this arm and Week 3's vanilla
TD3** (different reward functions — same rule as `03_rl_baseline.md`
S3.5): the comparison runs on the shared environment metrics
(`total_transformer_overload`, `average_/min_energy_user_satisfaction`,
`total_ev_served`, `tracking_error`). `ev2gym_thesis/figures.py`'s
`assert_total_reward_comparable` guardrail is expected to raise if
anything tries to plot `total_reward` across the two — verified, not
assumed (see S4.9).

Asserted, not just declared: `ev2gym_thesis/tests/test_week4.py`'s
`TestControlledComparisonInvariant` (extended for this arm) builds both
training envs through the shared `env_factory.make_training_env` code
path and checks the resolved `action_space`/`observation_space`/
`state_fn`/`config_path`/`sample_mode` are identical while `reward_fn`
differs — on the actual resolved objects, not by inspection.

## S4.5 Registry comparability rules for this week's rows

Extends Week 3's §3.5 (`total_reward` is not comparable across reward
functions) with the oracle-specific consequences:

1. **The oracle bypasses `reward_function`/`state_function` entirely.** It
   reads a pickled `EvCityReplay` directly (`pickle.load(replay_path)`) and
   never calls `env.step()` with a reward at all — confirmed by reading
   `PowerTrackingErrorrMin.__init__`, which has no `reward_function`/
   `state_function` parameter and never imports from `ev2gym.rl_agent`.
   `total_reward` is therefore **not defined** for oracle rows; `notes`
   records `reward=none`, and the registry field is left blank rather than
   populated with a number nothing else is comparable to (a blank is
   honest; a number invites someone to plot it).
2. **Registered under the registry's reserved solver-comparison
   `algorithm_family` value** (`ev2gym_thesis/registry.py`'s
   `ALGORITHM_FAMILIES`) for both variants — this is what lifts
   `scripts/check_claims.py`'s vocabulary restriction once a row using it
   exists.
3. **Algorithm naming:** `Optimal_Oracle_Tracking` / `Optimal_Oracle_Balanced`,
   no training seed (the oracle is deterministic given a fixed MIP gap —
   see S4.7 and the Entregable 10 determinism test), so no seed-suffix
   collision problem like TD3's `_ts100/_ts101/_ts102`.
4. **Replay-vs-scenario parity is a load-bearing claim for this whole
   chapter, so it was verified, not assumed** — the exact category of
   mistake that caused Week 3's evaluation bug (S4.0). Three things
   confirmed empirically before any oracle result is trusted:
   - The replay's per-EV arrays (`u`, `ev_arrival`, `t_dep`, `ev_des_energy`,
     `ev_max_energy`, `ev_max_ch_power`, `ev_max_dis_power`,
     `energy_at_arrival`) — the fields `PowerTrackingErrorrMin` actually
     reads — are **identical regardless of which algorithm stepped through
     the episode to generate the replay** (compared `ChargeAsFastAsPossible`
     vs. `RoundRobin` byte-for-byte on the same `(config, day, seed)` cell).
     The one field that IS algorithm-dependent, `max_energy_at_departure`
     (derived from the EV's actual charged level at its last step), is
     loaded but never referenced in `tracking_error.py`'s active
     constraints/objective (dead code in the upstream library, confirmed by
     reading the source) — so it doesn't matter which algorithm generates
     the replay. `ev2gym_thesis/oracle/replay_utils.generate_replay` uses
     `RoundRobin` for no reason beyond "a real, already-implemented,
     G2V-safe heuristic."
   - The replay's population matches `env_factory.make_env`'s scenario for
     the identical `(config, day, seed)` cell **element by element** — not
     counts, not means. Verified directly by reconstructing `u`/`ev_arrival`/
     `t_dep`/`ev_des_energy`/`energy_at_arrival` from `make_env`'s
     `env.EVs_profiles` and comparing array-equal against the replay's own
     fields: all matched exactly (14 EVs, `station_v0_bogota`, seed 0,
     2022-01-17).
   - Replay generation is deterministic: the same `(config, day, seed)`
     produces byte-identical replay arrays across two independent runs.
   - **Replay generation deliberately never calls `env.reset()` a second
     time after construction** — `EV2Gym.__init__` already performs the one
     seeded reset that matters; a second, unseeded `reset()` is exactly
     Week 3's bug (S4.0) and would silently re-randomize the scenario the
     replay encodes.

## S4.6 Oracle timing calibration — reserved for the full write-up, headline below

Full table, methodology, and Gate 2 candidates in `00_lab_log.md`'s
2026-08-18 Entregable 3 entry. Headline: the tracking-only oracle solved
`station_v0_bogota`'s reference cell (2022-01-17, seed 0) to **full
optimality in 0.10s** of Gurobi solve time (1 branch-and-bound node after
presolve removed 10,476 of 10,546 rows and 8,200 of 9,024 columns), with
replay generation (3.94s, dominated by re-reading day-config YAML and price
data, not the solve) as the actual bottleneck. Per-cell cost ≈4.45s implies
the full 50-cell tracking-only grid costs **≈3.7 minutes**, not the
"potentially exceeds 3 minutes per cell" scenario the task brief flagged as
a possibility — MIP-gap/time-limit approximations are not needed at this
station size. **Gate 2 confirmed by the user 2026-08-18** before the
tracking-only grid was run; the balanced grid (below) followed the same
confirmed default (full optimality, no gap/time-limit needed).

### Balanced oracle: verified before trusting, not just calibrated

Before any result below was written down, the "identical objective across
penalty weights" observation on the reference cell was treated as a claim
requiring proof, not a finding to report — an inert (silently-dead) Gurobi
objective term produces exactly this symptom, and the term had just been
adapted across a units fix, so the code was fresh and untested. Full
five-step verification protocol (penalty value measured directly,
absurd-weight probe, an escalating positive control that only became
decisive at 0.05x transformer capacity, solution comparison, and a source-
order code review) in `00_lab_log.md`'s 2026-08-19 entry
(`scripts/verify_balanced_oracle_objective.py`). **Verdict: the term is
live and correctly implemented; "satisfaction is free" on the real grid is
a genuine result.** `SATISFACTION_PENALTY_WEIGHT = 1.0`
(`ev2gym_thesis/oracle/balanced_model.py`) was used for the grid below.

## S4.7 Oracle evaluation over the 50-cell grid — done, both variants

**station_v0_bogota, n=50 per variant (5 `SEEDS` × 10 `EVAL_DAYS`), mean
[all cells OPTIMAL status, 0 infeasible, either variant]:**

| Metric | `Optimal_Oracle_Tracking` | `Optimal_Oracle_Balanced` |
|---|---|---|
| EVs served | 13.44 (identical every cell) | 13.44 (identical every cell) |
| Transformer overload (kWh) | 0.00 (hard constraint) | 0.00 (hard constraint) |
| Avg. / min energy satisfaction | 1.000 / 100.00 (identical every cell) | 1.000 / 100.00 (identical every cell) |
| Tracking error (reference cell) | 6481.77 | 6408.81 |

Full 50-cell numbers in `results/master_results.csv`
(`algorithm_family="optimal"`); per-cell comparison and the mechanism
behind the `tracking_error`/`total_profits`/`battery_degradation`
divergence between variants (small, consistent, fully explained — a
linear-LP-vs-nonlinear-simulator model mismatch, not noise or a bug) is in
`00_lab_log.md`'s 2026-08-19 entry, not duplicated here.

**Both variants dominate every online algorithm by a wide margin on
tracking error**, the metric the tracking-only variant directly optimizes
and the metric a jury would ask the tripwire question about first
(Entregable 10): reference-cell `tracking_error` is 6388-6482 (either
oracle variant) vs. **14477 (Round Robin), 33111 (TD3 seed 100), 43608
(RandomPolicy), 72374 (AFAP)** — a 2x-to-11x gap. The oracle's status as a
real, dominant upper bound on this axis is not in question; the small
Tracking-vs-Balanced gap is a second-order methodological subtlety, not a
threat to that conclusion.

**Both variants kept as separate reported columns, not collapsed.** They
tie exactly on `total_ev_served`, `total_transformer_overload`, and
`average_/min_energy_user_satisfaction` (all 50 cells, 0.000000 max
difference) — but do NOT tie on `tracking_error`, `total_profits`, or
`battery_degradation` (small, consistent, nonzero differences on all 50
cells). Reporting only one column, or reporting them as identical, would
each be inaccurate in a different direction; both are kept with this exact
distinction stated, per `00_lab_log.md`'s 2026-08-19 entry.

**Transformer overload is not a meaningful "gap-to-bound" metric for
either variant** (S4.2) — it is a hard constraint in both, trivially 0,
same restriction already stated there.

## S4.8 `TD3_TrackingOnly` training and evaluation — completed

All 3 `TRAIN_SEEDS` trained at the identical 60,000-timestep/seed budget
confirmed for `TD3_vanilla` (S4.4). Per-seed wall-clock (`manifest.json`):
ts100 = 3343.24s (55.72 min), ts101 = 3276.59s (54.61 min), ts102 = 3485.78s
(58.10 min). **Total: 10,105.61s = 168.43 min (2.807h) — 1.4% under the
pre-training calibration estimate of 170.9 min** (`00_lab_log.md`'s
2026-08-19 Entregable 6 entry), within the declared re-confirmation
threshold, so no second Gate 3 confirmation was requested before launching.

Evaluated on the identical 50-cell grid (5 `SEEDS` x 10 `EVAL_DAYS`) used for
every other arm: `scripts/evaluate_rl.py --execute` appended exactly 150
rows (3 seeds x 50 cells), correctly skipped the 200 already-present
`TD3_vanilla`/`RandomPolicy` rows, and reported 0 errors. Final main-grid
registry: **550 rows = 11 algorithms x 50 cells exactly**, confirmed by
`TestRegistryCount` (S4.10) and directly:

| algorithm | n |
|---|---:|
| ChargeAsFastAsPossible, RoundRobin, RandomPolicy, both oracle variants, all 6 TD3 checkpoints | 50 each |

## S4.9 Analysis

**(1) Reward ablation headline — pooled, n=150 matched cells, `TD3_TrackingOnly`
vs. `TD3_vanilla`, paired bootstrap (`results/reward_ablation_bootstrap.csv`):**

| Metric | Point estimate | 95% CI | Direction |
|---|---:|---|---|
| `total_ev_served` | 0.000% | [0.000, 0.000] | identical |
| `total_profits` | +5.02% | [1.68, 8.39] | TrackingOnly higher |
| `average_user_satisfaction` | +0.41% | [0.05, 0.78] | TrackingOnly higher |
| `min_energy_user_satisfaction` | +7.59% | [3.44, 11.58] | TrackingOnly higher |
| `total_transformer_overload` | +1.75 kWh (abs.) | [0.61, 2.97] | TrackingOnly **worse** |
| `tracking_error` | +12.95% | [8.88, 17.09] | TrackingOnly **worse** |
| `energy_tracking_error` | +5.30% | [3.61, 7.06] | TrackingOnly **worse** |
| `battery_degradation` | +2.65% | [0.84, 4.57] | TrackingOnly **worse** |

Every CI excludes 0 except `total_ev_served` (both arms serve identically
13.44 EVs/day, tied by construction of this station's demand). **The
result is mixed, not a win for either reward — stated plainly rather than
flattened into a single direction (correction, 2026-08-20; an earlier draft
of this section called it "retroactively validated," which overstated
what the numbers show):**

- `TD3_vanilla` (composite reward) is better on `tracking_error`,
  `energy_tracking_error`, `total_transformer_overload`, and
  `battery_degradation`.
- `TD3_TrackingOnly` is better on `total_profits` and BOTH satisfaction
  metrics (`average_user_satisfaction` +0.41%, `min_energy_user_satisfaction`
  +7.59%).

Neither arm dominates. Against this thesis's three declared objective axes
— user satisfaction, operator profitability, and technical compliance
(tracking/overload) — `TD3_TrackingOnly` wins two of three
(satisfaction, profitability) and `TD3_vanilla` wins one (technical
compliance, which itself bundles two of the eight metrics above). Week 3's
choice of the composite reward was justified by *reasoning* at the time
(`03_rl_baseline.md` S3.2 — overload and satisfaction have no
representation at all in the bare tracking-only default, so leaving them
out seemed strictly worse). This week's evidence *partially* supports that
reasoning — real, if modest, gains on the axes the composite reward was
designed to target — but it is not proof the earlier decision was correct
overall, since it comes at a real, non-trivial cost on two of the three
axes this thesis weights. Evidence obtained later that partially supports
an earlier reasoned choice is a different thing from that choice being
validated, and the distinction is kept rather than collapsed.

**The counterintuitive part needs a mechanism, not just a report:**
optimizing tracking error *alone* produces a *worse* realized tracking
error than a reward that also spends capacity on overload and satisfaction
penalties. **Hypothesis, not established fact:** the composite reward's
extra terms may act as implicit shaping/regularization that helps credit
assignment under this project's severely reduced training budget (60,000
timesteps vs. the source papers' HPC-scale runs) — a denser, more
frequently-informative reward signal could make gradient estimates less
noisy early in training even though the *ultimate* optimization target
(tracking error) is diluted by two unrelated terms. Under this hypothesis,
the effect would be an **artifact of the reduced budget**, not an inherent
property of composite vs. tracking-only rewards — a longer run might show
`TD3_TrackingOnly` eventually catching up or overtaking `TD3_vanilla` on
tracking error once its own signal is no longer starved of an early,
denser gradient. **What would test this:** a matched-budget comparison at
a substantially longer horizon (e.g. 300,000–500,000 timesteps) on a single
seed for each arm, watching whether the tracking-error gap narrows or
inverts as training progresses. **This is explicitly out of scope for Week
4** — flagged as a testable hypothesis for a future week's budget, not
run here.

**Per-seed consistency (`results/reward_ablation_bootstrap.csv`'s per-seed
breakdown):** the *direction* of every headline metric is identical across
all 3 training seeds (TrackingOnly always worse on overload/tracking/
degradation, always better-or-tied on profit/satisfaction), but
significance and magnitude vary substantially: ts100 shows the strongest,
most consistent effect (every metric's CI excludes 0 except EVs served);
ts101/ts102 show weaker effects, with `total_transformer_overload`'s CI
including 0 for both individually (only significant pooled). This is the
same cross-training-seed dispersion phenomenon Week 3 documented for
`TD3_vanilla`, reconfirmed here for a second, independent reward arm.

**(2) `TD3_TrackingOnly` vs. AFAP/Round Robin
(`results/reward_ablation_vs_baselines.csv`) — a sharper version of Week 3's
reward-vs-evaluation-metric misalignment finding:** vs. Round Robin,
`TD3_TrackingOnly`'s `tracking_error` is **158.6%–191.1% worse across all 3
seeds**, despite Round Robin being a zero-learning heuristic and
`TD3_TrackingOnly` training *solely* to minimize tracking error. This rules
out "the other reward terms (overload/satisfaction penalties) distract the
agent from tracking" as an explanation for TD3's underperformance vs. Round
Robin on this axis — the same underperformance persists even with every
other term removed.

**(3) Optimality gap vs. the appropriate oracle variant
(`results/optimality_gap.csv`, restricted to metrics the oracle actually
optimizes — S4.2):**

| Algorithm | `tracking_error` gap (% of oracle) | `min_energy_user_satisfaction` gap |
|---|---:|---:|
| Round Robin | **136.3%** (closest online algorithm) | 0.05% |
| TD3_vanilla (best seed, ts100) | 421.9% | 21.75% |
| TD3_TrackingOnly (best seed, ts101) | 482.0% | 16.61% |
| RandomPolicy | 612.0% | 0.00% |
| AFAP | 893.97% (worst) | 0.00% |

**This is the week's headline result, and it is stated plainly, not in
passing: under this training budget, reinforcement learning does not beat
a trivial round-robin heuristic on tracking error — by a wide margin,
consistently across two reward functions and six independent training
seeds.** Every TD3 variant, both reward arms, all 6 checkpoints, is farther
from the tracking-error oracle than Round Robin (136.3%) — the closest RL
checkpoint (`TD3_vanilla_ts100`) is still 3.1x farther from the bound than
a heuristic with no learning, no training cost, and no seed-to-seed
variance. `average_/min_energy_user_satisfaction` gaps show the inverse
pattern: heuristics and the random control tie the oracle almost exactly
(0.00–0.05%), while every RL variant shows a real, nonzero gap (0.8–21.75%)
— a real, if fairly small in absolute terms, cost RL pays for whatever
tracking-side behavior it learned instead.

**This claim is bounded to the training regime actually used, not stated
as a general property of RL vs. heuristics:** *under a 60,000-timestep
budget on CPU* (the declared, drastic reduction this project made against
the source papers' 5–48 hour HPC training runs per single run —
`03_rl_baseline.md` S3.10), RL underperforms Round Robin on tracking error.
Whether this gap would close, persist, or reverse under the papers'
original budget is genuinely unknown from this project's evidence and is
not claimed either way.

**Consequence for Objective 4 (recommended strategy), surfaced now rather
than left for Week 6 to discover cold:** on the evidence gathered through
Week 4, the strategy that best approaches the perfect-information bound on
tracking error is Round Robin, not either trained RL variant. This thesis
is fully able to reach that conclusion — a simple heuristic beating RL
under a realistic, declared, laptop-scale training budget is a legitimate
and defensible finding, not a failure of the RL work — but it cannot
recommend an RL-based strategy on tracking-error grounds without evidence
that a larger budget changes this picture, which does not currently exist
in this project.

**(4) Oracle tie-break noise floor, redone per metric (2026-08-20
correction) — a single global "gaps are 79x the floor" statement does not
transfer across metrics, since each has its own tie-break spread and its
own gap magnitudes:**

| Metric | Floor (mean / max) | Smallest reported gap | Ratio | Verdict |
|---|---:|---:|---:|---|
| `tracking_error` | 60.93 / 89.35 | 7,080.11 (Round Robin) | 79x (vs. max) | **Real, far outside the floor.** No metric in this chapter is close to this margin. |
| `average_user_satisfaction` | 0.0000 / 0.0000 (exact tie) | 0.0029 (Round Robin, i.e. ~0.29 percentage points) | undefined (floor is exactly zero) | **Real but small in absolute terms.** AFAP and RandomPolicy tie the oracle EXACTLY (gap = 0.0000, a genuine tie, not "inside a floor region"); Round Robin's tiny nonzero gap and every RL arm's larger gap (0.80–2.40%) are both distinguishable from a literal-zero floor, but Round Robin's own gap is small enough that "real" should not be read as "large." |
| `min_energy_user_satisfaction` | 0.0000 / 0.0000 (exact tie) | 0.047 pp (Round Robin) | undefined (floor is exactly zero) | Same pattern: AFAP/RandomPolicy tie exactly; Round Robin's gap is real but tiny (0.047 pp); every RL arm's gap (6.95–21.75 pp) is unambiguously real and non-negligible. |
| `energy_tracking_error` | 0.7766 / 1.0474 | **not computed** | N/A | This metric has a measurable, nonzero floor but was never included in S4.2's restricted `GAP_METRICS` set — flagged as an open scope question (should it be?), not silently omitted. |
| `total_profits` | 0.1833 / 0.5325 | **not computed** | N/A | Same as above — a real floor exists, no gap was ever computed against it in this chapter. |
| `total_ev_served`, `total_transformer_overload`, `battery_degradation`, `energy_user_satisfaction` | 0.0000 / 0.0000 | **not computed** | N/A | Floor is trivially zero (both oracle variants tie exactly) and none of these were selected as gap metrics — `total_transformer_overload` deliberately so (S4.2: a hard constraint in both variants, not a meaningful "distance from bound"), the other three simply never included. |

**No metric in this chapter has a ratio anywhere near 1** — the resolution-limit
concern the per-metric redo was checking for does not materialize on the 3
metrics this chapter actually reports a gap for. The two satisfaction
metrics' zero floor means a ratio literally cannot be computed (division by
zero); the honest statement there is "any nonzero gap is real by
construction," not a numeric ratio, and Round Robin's own gaps on both
those metrics are real-but-small rather than a strong finding. Cross-checked
programmatically (`analyze_week4_results.py`'s `cross_check_against_noise_floor()`),
not just asserted from the two numbers.

**(5) `TD3_TrackingOnly` cross-training-seed dispersion
(`results/trackingonly_train_seed_dispersion.csv`):**
`total_transformer_overload` rel_spread = **63.8%** (the largest, echoing
Week 3's `TD3_vanilla` dispersion finding), `min_energy_user_satisfaction`
rel_spread = 11.8%, `tracking_error` rel_spread = 13.7% — real, substantial
training-seed variability persists for this second arm too, at the same
declared, reduced training budget. Not a property of the vanilla reward
specifically.

**Against the proposal's declared success targets
(`PROJECT_ROADMAP.md`: *">90% satisfaction, <15% energy error, ±5% RETIE
voltage band"*):**

- **`average_user_satisfaction` > 90%: met by every algorithm and arm
  tested this week**, with no exception — worst observed value is
  `TD3_vanilla_ts100` at 97.6% (mean over the 50-cell grid); every other RL
  arm ≥ 97.6%; every heuristic and oracle variant = 100.0%.
- **"<15% error de energía no servida vs. baseline no gestionado":
  mapping PROPOSED 2026-08-20, not yet adopted as this project's final
  operationalization — labeled assumption, per `CLAUDE.md` rule 5.** The
  approved proposal's own wording is narrower than "undefined": it names
  *energy not served*, benchmarked against the unmanaged baseline (AFAP in
  this project's own terminology). Two EV2Gym-native, already-computed
  registry columns are read from source (`ev2gym/models/ev.py:204-214`,
  `ev2gym/utilities/utils.py:58-62`) as candidates, not guessed:

  | Candidate | Formula (source-read) | What it measures |
  |---|---|---|
  | **Proposed: `average_user_satisfaction`** | `1 − mean_i[min(1, current_capacity_i / desired_capacity_i)]`, per departed EV | Energy not delivered, **relative to what the EV itself requested** (`desired_capacity`) — the standard "energy not served" definition (unserved demand as a fraction of demand), matching *"energía no servida"* literally. |
  | Rejected alt. 1: `energy_user_satisfaction` | `1 − mean_i[current_capacity_i / max_energy_AFAP_i]`, where `max_energy_AFAP` is EV2Gym's own simulated "what this EV would reach charged at max rate every step" (`ev.py:420-439`) | Energy not delivered relative to what an **idealized max-rate charge** would have achieved — literally embeds "vs. the unmanaged baseline" into the denominator, but changes the reference from *demand* to *idealized outcome*. Kept as a secondary/robustness cross-check (both computed below; they agree closely at this station) but not the primary definition, since the proposal's own phrase centers on unserved *demand*. At a more oversubscribed station this metric would systematically understate true unserved demand whenever AFAP itself cannot fully charge every EV — a divergence this station is too lightly loaded to expose. |
  | Rejected alt. 2: derived from `total_energy_charged` vs. a new fleet-total "energy requested" quantity | `1 − total_energy_charged / Σ_i(desired_capacity_i − battery_capacity_at_arrival_i)` | Rejected on two grounds: (1) the denominator is not a registry column today — it would need new computation and testing infrastructure, unlike the other two candidates which EV2Gym already computes; (2) fleet-level aggregation discards exactly the per-EV worst-case information this project's own `min_energy_user_satisfaction` column exists to capture — an algorithm that fully serves most EVs while starving one could show a deceptively good aggregate ratio. |

  **Computed for every arm this week, against the proposed definition**
  (`energy_not_served_pct = (1 − average_user_satisfaction) × 100`, mean
  over the 50-cell grid):

  | Algorithm | Energy not served (%) | Rejected-alt. 1 cross-check (%) |
  |---|---:|---:|
  | AFAP (unmanaged baseline) | 0.00 | 0.00 |
  | Round Robin | 0.29 | 0.39 |
  | RandomPolicy | 0.00 | 0.00 |
  | TD3_vanilla (worst seed, ts100) | 2.40 | 2.57 |
  | TD3_TrackingOnly (worst seed, ts101) | 2.00 | 2.37 |
  | Both oracle variants | 0.00 | 0.00 |

  **Every algorithm and arm tested through Week 4 clears the <15% target
  by a wide margin under either candidate definition** — worst observed
  value is 2.57% (`TD3_vanilla_ts100`, rejected-alt. 1), over 5x under the
  threshold. The two candidate definitions agree closely (within ~0.3
  percentage points) at this station's oversubscription level, which is
  reassuring but not a substitute for choosing one as the thesis's
  official definition. **Not closing Week 4 on this** per the brief's own
  instruction — this is a proposal for Week 5 to adopt or revise, not a
  final decision, and is recorded here as a labeled assumption so it can
  be challenged before the final comparison is written up.
- **Voltage band: not applicable this week** — `simulate_grid=False`
  through Week 4 per the standing grid-scope note; no `voltage_violation`
  data exists until Weeks 6–7's grid-enabled phase.

## S4.10 Verdict

1. **Oracle:** a real, dominant, verified upper bound on `tracking_error`
   (2x–11x gap over every online algorithm, S4.7) with a well-understood,
   quantified tie-break noise floor separating real gaps from measurement
   resolution (S4.9(4)).
2. **Physics-informed reward adaptation: genuinely falsified, not
   abandoned** — two structurally different designs, both built, verified,
   and rejected before training compute was spent, for two independent,
   now well-diagnosed mechanisms (S4.3). No `PI_TD3` arm exists anywhere in
   this thesis's registry, code, or results.
3. **Reward ablation answers Week 3's open question with a mixed result,
   not a validation (corrected 2026-08-20 — see S4.9(1) for the full
   reversal of an earlier, overstated draft of this point):**
   `TD3_vanilla`'s composite reward wins on tracking error, energy
   tracking error, overload, and degradation; `TD3_TrackingOnly` wins on
   profit and both satisfaction metrics — two of this thesis's three
   declared objective axes. Week 3's reasoning is partially, not fully,
   supported by this week's evidence. The counterintuitive direction
   (tracking-only training producing worse tracking error) is recorded as
   a **hypothesis** — reduced-budget shaping/regularization, not an
   established mechanism — with an explicit, out-of-scope test proposed
   (S4.9(1)).
4. **The week's real headline, stated without softening: under this
   training budget, RL does not beat Round Robin on tracking error, by a
   wide margin, across two reward functions and six training seeds**
   (S4.9(3)) — Round Robin's 136.3% gap to the tracking-error oracle vs.
   422–612% for every RL checkpoint. Bounded explicitly to the
   60,000-timestep CPU budget actually used, not claimed as a general
   property of RL vs. heuristics — see S4.9(3) for the full statement and
   its consequence for Objective 4's recommended-strategy question, which
   this evidence currently points toward Round Robin, not RL.
5. **Both TD3 reward arms show substantial cross-training-seed dispersion**
   (up to 63.8% relative spread on individual metrics) at the declared,
   reduced training budget — a real limitation of the 60,000-timestep/seed
   scope, not resolved this week, and worth flagging explicitly for Week
   5's synthesis rather than averaging away.
6. **Energy-not-served target: proposed operationalization, not yet
   adopted** (S4.9) — `(1 − average_user_satisfaction) × 100`, source-read
   from `ev.get_user_satisfaction()`. Every algorithm/arm tested this week
   clears the <15% threshold with a wide margin (worst case 2.57%,
   cross-checked against a second candidate definition) — a proposal for
   Week 5 to adopt or revise, not a closed decision.
