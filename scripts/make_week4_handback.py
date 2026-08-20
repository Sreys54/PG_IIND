"""
Builds thesis_docs/Week4_Parameter_Method_and_Implementation_Justification.md
by extracting code excerpts fresh from source (via scripts/build_week_doc.py)
every time it runs -- same convention as scripts/make_week3_handback.py: the
document can never quote code that no longer exists, because it re-reads the
actual file every time.

Format mirrors Week 3's: Part 1 (parameters and methods, validated/empirical/
simplification labeling), Part 2 (implementation: Location, Purpose, Design
decision(s) with rejected alternatives, the actual code, and a Walkthrough
where the code isn't self-explanatory), Library Choices, References, and a
Headline Results Summary that points at thesis_docs/chapters/04_oracle_and_pitd3.md
rather than duplicating its numbers.

Usage: PYTHONPATH=. python scripts/make_week4_handback.py
Then:  PYTHONPATH=. python scripts/render_docx.py thesis_docs/Week4_Parameter_Method_and_Implementation_Justification.md thesis_docs/Week4_Parameter_Method_and_Implementation_Justification.docx
"""
import datetime

from scripts.build_week_doc import get_snippet
from ev2gym_thesis.registry import get_git_commit

OUT_PATH = "thesis_docs/Week4_Parameter_Method_and_Implementation_Justification.md"


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
    parts.append(f"""# Week 4 — Parameter, Method, and Implementation Justification

**Git commit:** `{commit}`
**Generated:** {generated} (regenerate with `PYTHONPATH=. python scripts/make_week4_handback.py` after any code change -- this document is built, not hand-maintained)

**Scope, stated up front, and amended twice during the week (both amendments kept, not deleted):**
Week 3's handback declared Week 4 as *"a perfect-information reference (free
solver, no Gurobi) + PI-TD3."* **Amendment 1 (2026-08-19):** an academic
Gurobi license is active on this machine (`LicenseID 2853634`, expires
2027-08-14, unlimited size), so the perfect-information reference uses
Gurobi via EV2Gym's own `ev2gym/baselines/gurobi_models/`, not a free
solver -- a reduction in deviation from the original `PROJECT_ROADMAP.md`,
not a new one. **Amendment 2 (2026-08-19):** Part B's scope changed from
delivering a trained arm named `PI_TD3` to a falsified physics-adaptation
attempt (two independent designs, both built, verified, and rejected before
any training compute was spent) plus a reward ablation
(`TD3_TrackingOnly`) that actually trained. No arm in this thesis is named
`PI_TD3`/`PI-TD3` anywhere in the registry, code, or results. Full account
in `thesis_docs/chapters/04_oracle_and_pitd3.md` S4.0 and S4.3.

**A third, unplanned correction happened first and delayed this chapter,**
carried over from Week 3: building this chapter's replay-vs-scenario parity
check surfaced Week 3's evaluation-pipeline bug (uncontrolled `env.reset()`
calls corrupting all 200 TD3/RandomPolicy evaluation episodes). Already
fully documented in `thesis_docs/Week3_Parameter_Method_and_Implementation_Justification.md`'s
correction note and `00_lab_log.md`'s 2026-08-18 entry -- not repeated here.

This document has two halves, in the same format as Weeks 2-3: **Part 1**
(parameters and methods, validated/empirical/simplification labeling
convention) and **Part 2** (implementation, file by file: Location,
Purpose, Design decision(s) with rejected alternatives, the actual code,
and a Walkthrough).
""")

    # -----------------------------------------------------------------
    # Part 1
    # -----------------------------------------------------------------
    parts.append("""## Part 1 -- Parameters and Methods

| Parameter | Value | Label | Justification |
|---|---|---|---|
| Oracle model | `PowerTrackingErrorrMin` (`ev2gym/baselines/gurobi_models/tracking_error.py`), unmodified | Validated against external source (the class exists as-is in the library) | The only one of 3 candidate Gurobi models whose objective matches this thesis's chosen Public/PST problem family -- see `04_oracle_and_pitd3.md` S4.2 for the full 3-way comparison and why the other two (`V2GProfitMaxOracleGB`, `V2GProfitMax_Grid_OracleGB`) were rejected. |
| G2V forcing | zero `port_max_discharge_current`/`port_min_discharge_current` on a replay copy | Empirically set inside this project | `v2g_enabled: False` only gates the RL/heuristic action-space sign (`ev2gym_env.py:227`), not the replay's discharge current bounds (`replay.py:89-90`) -- left unfixed, the oracle would have V2G capability none of the compared algorithms have, and its "upper bound" would not bound the same problem. |
| Oracle variants | `Optimal_Oracle_Tracking` (tracking-only) + `Optimal_Oracle_Balanced` (tracking + satisfaction penalty) | User-directed (2026-08-18 Amendment 1) | A single "bound" that added a satisfaction penalty to the objective would no longer be the true optimum on tracking error alone -- composite objectives are not decomposable bounds, so two separate variants answer two separate questions instead of one hedged answer. |
| `SATISFACTION_PENALTY_WEIGHT` | `1.0` | Set for this project | Adapted from `profit_max.py`'s departure-satisfaction penalty in STRUCTURE (squared kWh gap at departure), not scale -- that file's weight=100 was calibrated against a profit objective with different units and would carry no transferable meaning here. Also dimensionally corrected: `profit_max.py`'s own term multiplies `ev_des_energy * ev_max_energy` (kWh x kWh) against `energy` (kWh), which is dimensionally inconsistent; this project's term uses `(ev_des_energy - energy)**2`, both in kWh. |
| PI-TD3 physics term | **not used by any training run** -- falsified, kept for the record | Negative result, declared as such | Two structurally different reward-only adaptations of PI-TD3's Eq. 14 Term 1 (voltage band -> transformer capacity) were built and verified before either was trusted with training compute; both failed for different, now well-understood reasons. Full mechanism and evidence in `04_oracle_and_pitd3.md` S4.3. |
| `PI_TD3_HORIZON_H` | `4` steps (1h ahead, 15 min/step) | Set for this project | Chosen after a sensitivity sweep over H in {{1, 2, 4, 8}} steps, measuring the effect on the disagreement rate against the vanilla reward's existing overload term -- see `00_lab_log.md`'s 2026-08-19 entry. Never reached training (Design 2 was independently falsified on a different axis -- the SoC-gradient problem, not a horizon-tuning problem). |
| `PI_TD3_PHYSICS_WEIGHT` | `50.0` | Set for this project | Calibrated against the measured reward-term decomposition (tracking term ~-37,778, existing overload term ~-3,732 over one reference AFAP episode) -- target: comparable magnitude to the existing overload term, not dominant or negligible. Superseded the original qualitatively-estimated weight of 20.0. |
| `TD3_TrackingOnly` reward | `SquaredTrackingErrorReward` (EV2Gym's own bare default) | Validated against external source | Everything else (timesteps, `TRAIN_SEEDS`, state function, network architecture, replay buffer, `VecNormalize`) held identical to Week 3's vanilla-TD3 arm -- a genuinely single-variable ablation, answering "does the overload/satisfaction reward shaping Week 3 chose actually buy anything over tracking error alone?" |
| Oracle solve settings | full optimality, no MIP-gap/time-limit approximation | User-confirmed (Gate 2, 2026-08-18) | Entregable 3's timing calibration measured 0.10s Gurobi solve time for the reference cell (1 branch-and-bound node after presolve), implying the full 50-cell grid costs ~3.7 minutes -- far under the "potentially exceeds 3 min/cell" scenario the task brief flagged as a possibility, so no gap/time-limit relaxation was needed at this station size. |
""")

    # -----------------------------------------------------------------
    # Part 2
    # -----------------------------------------------------------------
    parts.append("""## Part 2 -- Implementation

### `ev2gym_thesis/oracle/` (new subpackage)

**Location:** new top-level subpackage, mirroring Week 3's `ev2gym_thesis/rl/` --
`ev2gym/baselines/gurobi_models/*.py` is never modified in place; this
subpackage only reads pickled `EvCityReplay` files those unmodified classes
already consume via a plain file path (per `CLAUDE.md` rule 1).

#### `ev2gym_thesis/oracle/replay_utils.py`

**Purpose:** generates the pickled `EvCityReplay` the oracle reads, and
forces G2V-only bounds on it.

**Design decision -- generate the replay with `RoundRobin`, not any
algorithm-agnostic placeholder, and never call `env.reset()` a second time
after construction:** verified, not assumed, that any algorithm produces an
identical replay for the fields the oracle actually reads (`u`,
`ev_arrival`, `t_dep`, `ev_des_energy`, `ev_max_energy`, `ev_max_ch_power`,
`ev_max_dis_power`, `energy_at_arrival`) -- compared `ChargeAsFastAsPossible`
vs. `RoundRobin` on the same `(config, day, seed)` cell, byte-identical. The
one algorithm-dependent field, `max_energy_at_departure`, is loaded by
`tracking_error.py` but never referenced in its constraints/objective (dead
code in the upstream library, confirmed by reading the source). A second
`env.reset()` call is deliberately avoided because it is exactly Week 3's
evaluation bug (`00_lab_log.md`'s 2026-08-18 entry): `EV2Gym.__init__`
already performs the one seeded reset that matters, and any unseeded reset
after that would silently re-randomize the scenario the replay encodes.

""" + code_block("generate_replay") + """

**Design decision -- zero the discharge-current bounds on a copy of the
replay, not on the live `EV2Gym` config:** `v2g_enabled: False` in
`station_v0_bogota.yaml` only gates the RL/heuristic action-space sign
(`ev2gym_env.py:227`) -- it does not alter the replay's own
`port_max_discharge_current`/`port_min_discharge_current` fields, which are
copied from `charging_station.max_discharge_current`/`min_discharge_current`
regardless (`replay.py:89-90`). Left unfixed, the oracle would legitimately
have V2G capability none of AFAP/Round Robin/TD3 have, invalidating its
status as a bound on the same problem -- a Week 4 Gate 1 preflight finding.

""" + code_block("force_g2v") + """

**Design decision -- an automated parity assertion for every cell, not a
one-time manual check:** rejected relying on the Entregable 3 reference-cell
calibration (a single manual comparison) to stand in for every one of the
100 cells (50 per oracle variant) actually evaluated. Chosen:
`verify_parity` is called by `scripts/evaluate_oracle.py` before any cell's
result is trusted, checking occupancy-step count and the sorted multiset of
desired energies against the live `env`'s own `EVs_profiles` -- the same
discipline `env_factory.reset_for_evaluation` (Week 3) enforces for
RL/heuristic evaluation, applied here because Week 4's oracle work exists in
large part because that discipline was once missing.

""" + code_block("verify_parity") + """

**Walkthrough:** `build_g2v_replay_for_cell` chains `generate_replay` and
`force_g2v` into a single call for `scripts/evaluate_oracle.py`'s per-cell
loop -- the raw (non-G2V) replay is also kept on disk, so a discharge-bound
bug can always be diagnosed by comparing the two files directly.

#### `ev2gym_thesis/oracle/balanced_model.py`

**Purpose:** `PowerTrackingErrorMinBalanced` -- the `Optimal_Oracle_Balanced`
variant's Gurobi model, `PowerTrackingErrorrMin`'s tracking objective plus a
departure-satisfaction penalty.

**Design decision -- a near-full copy of `PowerTrackingErrorrMin.__init__`,
not a subclass overriding one method:** the upstream class fuses model
construction and solving into a single `__init__` with no separate
`build_model()`/`objective()` hook to override -- there is no clean seam to
inject one additional objective term without either (a) editing the library
file in place (forbidden, `CLAUDE.md` rule 1) or (b) reimplementing the
whole method. Rejected (a). Chosen (b), documented here rather than hidden.
Every constraint block is copied verbatim from `tracking_error.py` (same
variable names, same structure, so a future diff against the upstream file
stays legible) except the new `user_satisfaction` variable/constraint and
the objective.

""" + code_block("balanced_oracle_penalty_weight") + """

**Bug found and fixed while adapting, not copied blindly from
`profit_max.py`:** that file's own `user_satisfaction` term is
`(ev_des_energy[p,i,t] * ev_max_energy[p,i,t-1] - energy[p,i,t])**2` --
multiplying two kWh quantities together (`ev_des_energy` is documented in
kWh: `ev2gym/models/ev.py:23,51`) produces a `kWh^2 - kWh` expression,
dimensionally inconsistent. This class uses the dimensionally consistent
form instead:

""" + code_block("balanced_oracle_satisfaction_term") + """

**Walkthrough:** verified before being trusted, not just calibrated -- a
five-step protocol (penalty value measured directly, an absurd-weight
probe, an escalating positive control that only became decisive at 0.05x
transformer capacity, solution comparison, and a source-order code review,
`00_lab_log.md`'s 2026-08-19 entry, `scripts/verify_balanced_oracle_objective.py`)
confirmed the term is live and correctly implemented -- "satisfaction is
free" on the real 50-cell grid (both variants tie exactly on
`average_/min_energy_user_satisfaction`, S4.7) is a genuine result, not a
silently-dead objective term producing a false tie.

### `scripts/evaluate_oracle.py` (Entregable 5)

**Location:** `scripts/` -- entry point, mirrors `scripts/evaluate_rl.py`'s
dry-run-by-default / `--execute` structure.

**Purpose:** builds a G2V-forced replay for each of the 50 grid cells, runs
the requested oracle variant, verifies parity, and appends
`algorithm_family="optimal"` rows to `results/master_results.csv`.

**Design decision -- a `--variant tracking/balanced` flag selecting between
two otherwise-identical evaluation loops, not two separate scripts:** the
replay generation, G2V forcing, and parity verification are identical
between variants -- only the Gurobi model class differs. A single script
with a variant flag keeps that shared logic in one place.

""" + code_block("oracle_variants") + """

**Walkthrough:** `notes` records `reward=none` for every oracle row (S4.5,
`04_oracle_and_pitd3.md`) -- the oracle bypasses `reward_function`/
`state_function` entirely (reads the replay directly, never calls
`env.step()` with a reward), confirmed by reading `PowerTrackingErrorrMin.__init__`,
which has no such parameter and never imports from `ev2gym.rl_agent`.
`total_reward` is therefore left blank rather than populated with a number
nothing else is comparable to.

### `ev2gym_thesis/rl/reward_pi.py` -- retained as negative-result evidence

**Location:** `ev2gym_thesis/rl/`, alongside Week 3's `env_factory.py`/`config_rl.py`.

**Purpose:** documents, and keeps importable, both falsified reward-only
physics adaptations -- used by no training run in this project. The module's
own docstring states this explicitly (added 2026-08-19) so a future reader
opening this file does not mistake it for the actual `TD3_TrackingOnly` arm.

**Design decision -- kept in the repository and git history rather than
deleted:** this module IS the evidence for `04_oracle_and_pitd3.md` S4.3's
finding. Its tests (`ev2gym_thesis/tests/test_week4.py`'s
`TestPIRewardFunction`) stay green because the functions themselves are
correctly implemented and well-tested -- what failed was the underlying
design idea in each case, not the code.

**Design 1 (instantaneous margin), rejected -- Spearman rank correlation
with the vanilla reward's existing overload term was exactly 1.0 at every
weight tested (20-2000):** both terms are monotonic functions of the same
single scalar (instantaneous power vs. instantaneous capacity) -- any two
monotone functions of the same scalar induce the same step ordering, so no
weight could ever make them rank steps differently. Proven before training,
not inferred from a disappointing learning curve afterward.

""" + code_block("pi_physics_margin_fraction") + """

**Design 2 (capacity-headroom / latent-exposure), rejected on a different,
independent axis -- the SoC-gradient problem:** uses
`env.charge_power_potential` (the connected fleet's max-rate demand, a
function of which EVs are present and their state, not directly of the
action taken) against the transformer's near-future minimum capacity. This
genuinely broke the Spearman=1.0 tie (mean 0.9855 across 6 cells), but a
second, independent verification found why it moved:
`charge_power_potential` excludes any EV once it reaches 100% SoC, so
charging EVs to full faster removes them from the term's sum regardless of
whether that fast charging caused a real overload -- Round Robin (which
already nearly eliminates transformer overload) was penalized ~32x more
often than AFAP (which overloads routinely), with a +0.66/+0.68 correlation
against mean fleet SoC confirming the mechanism directly.

""" + code_block("headroom_constants") + """

""" + code_block("pi_physics_term") + """

""" + code_block("pi_reward_fn") + """

**Walkthrough -- why no third design was attempted:** the repair that would
fix Design 2's flaw (weighting by each EV's remaining need against a fixed
departure deadline, so early completion cannot lower the penalty) needs each
EV's time of departure. `ev2gym.rl_agent.state.PublicPST` withholds this
information deliberately -- confirmed by reading `state.py:6-63`: the
exposed per-EV features are a full/not-full flag, cumulative
already-delivered energy, and elapsed (not remaining) dwell time, per the
EV2Gym paper's own Public-PST problem definition (Sec. III-A: *"we assume
that information about EV arrival and departure time... is unavailable"*).
Extending the state was considered and rejected on realism grounds, not
cost: a real Bogota public-station operator does not know a walk-up user's
departure time either, and extending the state for only this arm would also
make the comparison two-variable (state AND reward differing), with no way
to attribute a result to either one. Full account, including the Eq. 14
sign ambiguity found while reading the paper and the Week 6 conditional
stretch-goal path, in `04_oracle_and_pitd3.md` S4.3.

### `scripts/train_td3.py` / `scripts/calibrate_td3_timing.py` -- `TD3_TrackingOnly` reward arm (Entregable 6)

**Location:** `scripts/` -- Week 3's existing entry points, extended in
place, not forked.

**Purpose:** adds a second, selectable reward function
(`SquaredTrackingErrorReward`) alongside Week 3's vanilla reward
(`SqTrError_TrPenalty_UserIncentives`), so the same training/evaluation
pipeline produces a genuinely single-variable ablation.

**Design decision -- a `--reward` flag selecting a named arm, not a new
script:** rejected copying `train_td3.py` into a `train_td3_tracking_only.py`
fork -- every other hyperparameter (timesteps, `TRAIN_SEEDS`, state
function, network architecture, replay buffer, `VecNormalize`) must stay
byte-identical between the two arms for the comparison to be
single-variable, and a fork risks silent drift between the two copies over
time. Chosen: one script, one new flag, both reward functions pre-existing
and unmodified in `ev2gym.rl_agent.reward`.

""" + code_block("reward_arms") + """

**Walkthrough:** `run_name(seed, reward_key)` and
`ARM_NAMES = {"vanilla": "TD3_vanilla", "tracking_only": "TD3_TrackingOnly"}`
keep the two arms' checkpoint directories and registry algorithm names
distinct without touching `env_factory.py`/`config_rl.py`/`callbacks.py`/
`eval_utils.py` -- the Week 3 reward/state separation held, exactly as
`04_oracle_and_pitd3.md` S4.4 states.

""" + code_block("manifest_reproducibility_artifact") + """

**Design decision -- the manifest now records `reward_arm` and the real
`reward_fn.__name__`, not just a hardcoded string:** Week 3's manifest
schema already captured reward/state function names, but as a
constructor-time constant. Recording the actually-resolved function name
(not the flag string passed on the command line) means a manifest is
self-describing even if `ARM_NAMES`' mapping is ever edited later.

### `scripts/evaluate_rl.py` -- extended for `TD3_TrackingOnly` (Entregable 7)

**Location:** `scripts/` -- Week 3's existing entry point, extended in
place.

**Purpose:** evaluates all 6 TD3 checkpoints (3 `TD3_vanilla` seeds + 3
`TD3_TrackingOnly` seeds) plus the existing `RandomPolicy` control on the
same 50-cell grid.

**Design decision -- `TD3_ALGORITHMS` becomes a list of
`(algo_name, train_seed, model_path, reward_fn)` tuples, not two separate
lists:** a single list keeps the evaluation loop identical for both arms --
`reward_fn` is threaded into `make_env(..., reward_fn=reward_fn)` per
checkpoint, since evaluation must reconstruct the same reward function each
checkpoint was trained under (a mismatch here would make evaluation-time
reward diagnostics meaningless, even though the reported registry METRICS
are reward-independent).

""" + code_block("td3_stepper_fix") + """

**Walkthrough:** `_notes_for(reward_fn, train_seed=None)` records
`reward=<function name>` in the registry `notes` field per row -- the same
mechanism Week 3 already used, extended so `TD3_TrackingOnly` rows correctly
carry `reward=SquaredTrackingErrorReward` (matching AFAP/Round Robin's
fallback-default name) while `TD3_vanilla` rows carry
`reward=SqTrError_TrPenalty_UserIncentives`. This is what makes
`ev2gym_thesis/figures.py`'s `assert_total_reward_comparable` guardrail
correctly permit AFAP/RoundRobin/TD3_TrackingOnly comparisons on
`total_reward` while still raising if `TD3_vanilla` is mixed in -- the first
case in this project where `total_reward` is legitimately comparable across
a heuristic and a trained RL agent (S4.4/S4.5 in `04_oracle_and_pitd3.md`).

### `scripts/analyze_week4_results.py` (Entregable 8)

**Location:** `scripts/` -- entry point, writes 5 CSVs to `results/`.

**Purpose:** the reward-ablation bootstrap comparison (`TD3_TrackingOnly` vs.
`TD3_vanilla` vs. baselines), the optimality-gap analysis (each online
algorithm's distance to the appropriate oracle variant), and the oracle
tie-break noise floor.

**Design decision -- the optimality-gap metrics are restricted to a
declared, small set, not computed for every registry column:** rejected
computing a gap for every shared metric -- several (e.g. transformer
overload) are hard constraints in both oracle variants, trivially 0, and a
"gap" against a trivial bound is not informative (S4.2/S4.7's own
restriction, repeated here at the code level).

""" + code_block("optimality_gap_restriction") + """

**Design decision -- reuse `stats_utils.paired_bootstrap_ci` (Week 2),
write no new bootstrap code:** the pairing logic (resample matched `(seed,
eval_day)` cells together) is identical to what Weeks 2-3's figures already
needed.

**Walkthrough:** `cross_check_against_noise_floor()` is the explicit link
between `results/optimality_gap.csv` and
`results/oracle_tiebreak_noise_floor.csv` -- an online algorithm's measured
gap to the oracle is only interpreted as a real, closeable gap if it exceeds
the noise floor `Optimal_Oracle_Tracking` and `Optimal_Oracle_Balanced`
already show against EACH OTHER purely from the LP-tie-break/nonlinear-
simulator mismatch (S4.7). A gap smaller than that floor cannot be
distinguished from oracle-internal noise.

### `ev2gym_thesis/figures.py` / `scripts/make_figures.py` -- extended for 11 arms (Entregable 9)

**Location:** same Week 2-3 modules, extended in place.

**Purpose:** `ALGORITHM_STYLE` grows to cover `TD3_TrackingOnly_ts100/101/102`
and both oracle variants; two new figures (`f10_optimality_gap`,
`f11_physics_term_falsification`) are added; `f08` is rewritten to one panel
per reward arm.

""" + code_block("algorithm_style") + """

**Design decision -- oracle rows excluded from every figure that compares
online algorithms on a shared axis (f02-f05, f07), included only in the new
`f10`:** the oracle is not a competing strategy (S4.1) -- plotting it
alongside AFAP/Round Robin/TD3 on a bar chart would visually imply it is
one more algorithm choice rather than a bound. `_algos_present(rows,
exclude_oracle=True)` centralizes this exclusion so it cannot be
accidentally reintroduced figure-by-figure.

**Design decision -- `f08_learning_curves` becomes one subplot panel per
reward arm, not one shared axis:** `TD3_vanilla` and `TD3_TrackingOnly`
optimize different reward functions with different natural scales
(`SqTrError_TrPenalty_UserIncentives` includes overload/satisfaction
penalty terms `SquaredTrackingErrorReward` does not) -- plotting both
arms' raw episode reward on one shared y-axis would visually suggest they
are comparable numbers, repeating the exact mistake
`total_reward_guardrail` exists to prevent elsewhere in this codebase.

""" + code_block("total_reward_guardrail") + """

**Design decision -- `f11_physics_term_falsification` regenerates its data
live from `reward_pi.py`'s real functions, not from hand-transcribed
numbers:** rejected copying the Spearman/Pearson table from
`04_oracle_and_pitd3.md` S4.3 into the figure script as a literal constant
-- a hand-transcribed number can silently drift from the function that
produced it if either is edited later. Chosen: the figure calls
`transformer_capacity_margin_term`/`headroom_penalty_term` directly against
a real evaluation episode at figure-generation time, so the figure and the
chapter text are guaranteed to describe the same underlying computation.

**Visual QA findings:** see the Week 4 lab-log entry and
`04_oracle_and_pitd3.md` S4.9 for the executed run's findings -- reported
there rather than duplicated here, since this document is regenerated by
source inspection and cannot itself confirm what a rendered PNG looks like.

### `ev2gym_thesis/tests/test_week4.py` (Entregable 10)

**Location:** `ev2gym_thesis/tests/`, alongside Week 2-3's test modules.

**Purpose:** 16 tests across 6 classes: `TestPIRewardFunction` (7, pins the
shape of both falsified reward terms so future edits to `reward_pi.py`
cannot silently change already-reported numbers), `TestControlledComparisonInvariant`
(3, extended for `TD3_TrackingOnly` -- builds both training envs through the
shared `env_factory.make_training_env` path and checks resolved
`action_space`/`observation_space`/`state_fn`/`config_path`/`sample_mode`
are identical while `reward_fn` differs, on the actual resolved objects),
`TestOracleDeterminism` (1, skipped if Gurobi unavailable),
`TestOracleBoundTripwire` (1), `TestRegistryCount` (1, new this deliverable
-- expects `11 x 50 = 550` main-grid rows), `TestTotalRewardComparabilityGuardrail`
(3, empirically verifies AFAP+RoundRobin+TD3_TrackingOnly is permitted on
`total_reward` while AFAP+TD3_vanilla and AFAP+Oracle both raise).

**Bug found and fixed while writing `TestOracleBoundTripwire`:**
`ev2gym_thesis/registry_analysis.load_registry` coerces every
`NUMERIC_META_COLUMNS` field, including `seed`, to `float`. An early version
of this test compared `r["seed"] == "0"` (string) against the coerced
`float` value, which never matches -- the assertion silently iterated over
zero rows and reported false-positive success. Fixed to `r["seed"] == 0.0`;
documented in the test's own comment so the same mistake is not repeated in
a future test against this module.

**Results:** see the Week 4 lab-log entry for the executed run's pass/fail
outcome -- this document describes what the tests check, not whether they
passed on a specific run, since re-running this generator does not itself
re-execute the test suite.

## Library Choices (additions this week)

| Library | Used for | Why this one | Rejected alternative |
|---|---|---|---|
| `gurobipy` (academic license, `LicenseID 2853634`) | The perfect-information oracle, both variants | Already the project's declared MPC/optimal solver per `CLAUDE.md` rule 6; an academic license became available this week, superseding the Week 2/3 "restricted, non-production license" finding that had pointed toward a free-solver fallback. | A free solver (HiGHS/CVXPY/OR-Tools) -- was the Week 2/3 fallback plan, no longer needed once the academic license was confirmed active and unlimited. |

## References (additions this week)

**[Primary]**

- Read in full this week: `pi_td3_paper.pdf` (arXiv:2510.12335v2) -- Algorithm 1
  (the K-step differentiable-rollout actor update, the paper's actual novel
  mechanism) and Eq. 14 (the reward decomposition the brief originally asked
  to adapt) are cited by number in `04_oracle_and_pitd3.md` S4.3, per
  `CLAUDE.md` rule 3 (never reconstruct a paper's equations from memory).
- `ev2gym_paper.pdf` (arXiv:2404.01849v1) -- Sec. III-A's Public-PST problem
  definition (*"we assume that information about EV arrival and departure
  time... is unavailable"*) is the source confirming why `PublicPST` cannot
  be extended to support Design 2's repair without breaking this thesis's
  realism claim.

Full acquisition status and citation details for every reference (including
the 2-of-N regulatory documents available only as HTML, a declared
limitation) in `thesis_docs/references/REFERENCES.md`, new this week.

## Headline Results Summary

**Stated plainly here, not softened or left only in the full chapter
(corrected 2026-08-20 after an acceptance review found the first draft
buried this in passing):**

**Under this project's training budget, reinforcement learning does not
beat a trivial round-robin heuristic on tracking error -- by a wide
margin, consistently across two reward functions and six independent
training seeds.** Round Robin sits 136.3% above the tracking-error oracle
bound; every TD3 checkpoint tested (both reward arms) sits 422-612% above
it -- the closest RL checkpoint is still 3.1x farther from the bound than
a heuristic with no training cost and no seed variance. This is bounded
explicitly to *a 60,000-timestep budget on CPU* (this project's declared,
drastic reduction against the source papers' 5-48 hour HPC runs), not
claimed as a general property of RL vs. heuristics. On this evidence,
Objective 4's recommended-strategy question currently points toward Round
Robin, not RL -- a legitimate, defensible conclusion this thesis is fully
able to reach, surfaced now rather than left for Week 6.

**The `TD3_TrackingOnly` vs. `TD3_vanilla` reward ablation is a mixed
result, not a validation of Week 3's reward choice.** `TD3_vanilla`
(composite reward) wins on tracking error, energy tracking error,
transformer overload, and battery degradation; `TD3_TrackingOnly`
(tracking-only reward) wins on profit and both satisfaction metrics --
two of this thesis's three declared objective axes (satisfaction,
profitability, technical compliance). Neither dominates. The
counterintuitive direction -- optimizing tracking error alone producing a
*worse* realized tracking error -- is recorded as a **hypothesis**
(reduced-budget reward shaping aiding credit assignment), not an
established mechanism, with an explicit longer-run test proposed and
declared out of scope this week.

Full tables, the oracle-vs-online comparison, the reward-ablation bootstrap,
the per-metric noise-floor table, and the proposed energy-not-served target
mapping are in `thesis_docs/chapters/04_oracle_and_pitd3.md` (S4.6-S4.10) and
`thesis_docs/chapters/00_lab_log.md`'s Week 4 entries -- not repeated in
full here to avoid drift between two copies of the same numbers, per the
same convention Week 3's handback document used; the two findings above are
stated in full because they are this week's headline conclusions, not
supporting detail.
""")

    return "\n".join(parts)


if __name__ == "__main__":
    content = build_document()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {OUT_PATH} ({len(content)} characters)")
