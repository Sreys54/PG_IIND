"""
Week 4, Entregable 5: a reward-only adaptation of PI-TD3's physics-informed
PRINCIPLE, not a reproduction of its formulation or algorithm. Named
`TD3_HeadroomPenalty` (not `PI-TD3`) once the naming decision below is
settled -- drop-in for env_factory.DEFAULT_REWARD_FN, no
env_factory.py/config_rl.py/callbacks.py/eval_utils.py change needed to
wire it in (the Week 3 separation held).

**Why this is not called PI-TD3, decided 2026-08-19 after reading
thesis_docs/references/pi_td3_paper.pdf in full:** PI-TD3's actual novel
mechanism (Algorithm 1 line 11, Eq. 20 -- a K-step, model-based,
differentiable rollout replacing TD3's standard actor update) is out of
scope (would mean replacing Stable-Baselines3's TD3.train() entirely, not
swapping a reward function; simulate_grid=False also has no power-flow
model to differentiate through). What remains, after two design
iterations (both documented below, neither silently dropped), is a
reward-only term inspired by Eq. 14 Term 1's principle -- embedding a
physical feasibility signal into the learning signal, voltage band ->
transformer headroom -- not a port of the paper's formulation or
algorithm. Calling this "PI-TD3" would overclaim; `TD3_HeadroomPenalty`
with the lineage declared as inspiration is the honest name.

**Design iteration 1 (instantaneous margin), rejected:** penalized
env.transformers[i].current_power directly (a function of the ACTION
taken this step) against a pre-violation margin below max_power. Empirical
check (scripts/verify_pi_reward_differs.py): Spearman rank correlation
with the vanilla reward's existing `-100 * tr.get_how_overloaded()` term
was EXACTLY 1.0 at every weight tested (20 through 2000) -- both terms are
monotonic functions of the same instantaneous scalar (current power vs.
current capacity), so no weight could ever make them rank steps
differently. Proven before training, not inferred from a disappointing
learning curve afterward. Full diagnosis in
thesis_docs/chapters/00_lab_log.md's 2026-08-19 entries.

**Design iteration 2 (this one): capacity-headroom / latent-exposure.**
Uses env.charge_power_potential -- the total power the CONNECTED FLEET
could draw at maximum rate (EV2Gym's own calculate_charge_power_potential,
ev2gym/utilities/utils.py), a function of which EVs are connected and
their own state, not directly of the action taken -- against the MINIMUM
transformer capacity over the next PI_TD3_HORIZON_H steps, not just the
current step. This is deliberately NOT the "committed-load feasibility"
design considered and rejected first: that design needs each EV's
remaining required energy and remaining time to departure, and
`ev2gym.rl_agent.state.PublicPST` exposes neither, by the Public-PST
problem's own deliberate design (the EV2Gym paper's Sec. III-A states the
Public variant assumes departure time and arrival SoC are NOT known to the
operator -- confirmed by reading state.py:6-63 directly: PublicPST's
per-EV features are a full/not-full flag, cumulative ALREADY-exchanged
energy, and ELAPSED (not remaining) dwell time). Extending the state to
expose departure time would import an assumption a real public charging
station cannot make (a walk-up user does not declare a departure time),
undercutting this thesis's realism claim more than a weaker physics term
would -- rejected on that basis, not on cost, and even the cheaper
single-arm-only version of that extension was rejected because it would
make the comparison two-variable (state AND reward differing), with no
way to attribute a result to either.

Verified before being trusted (thesis_docs/chapters/00_lab_log.md,
2026-08-19 entry, scripts/verify_pi_reward_differs.py /
scripts/verify_headroom_term.py):
1. Predictability from the observation the policy actually sees (a reward
   term the policy cannot predict from PublicPST is shaping noise, not
   signal).
2. Control-responsiveness (AFAP vs. Round Robin on the same cell) --
   charge_power_potential is not purely demand-determined: an EV that
   reaches 100% SoC stops contributing to it, so aggressive charging can
   reduce the term, which needed checking for a perverse gradient before
   trusting it.
3. Correlation against mean fleet SoC, to catch exactly that perverse
   gradient (a term whose penalty drops simply because EVs were charged
   up fast would reward AFAP-like behavior, not discourage it).
4. Spearman rank correlation against get_how_overloaded() across multiple
   EVAL_DAYS and seeds, not a single episode.

**A genuine ambiguity found while reading Eq. 14, recorded rather than
silently resolved either way:** the paper states weights
lambda_1 = -5e4, lambda_2 = 1, lambda_3 = -10 (Sec. IV-A). Applied
literally to Term 1 (lambda_1 * min{0, 0.05 - |1-V|}, a quantity that is 0
when compliant and increasingly NEGATIVE the worse the violation), a
NEGATIVE lambda_1 makes the product increasingly POSITIVE as violations
worsen -- rewarding larger violations under a MAXIMIZED reward (Eq. 16,
Algorithm 1), the opposite of the paper's own stated intent ("the first
term penalizes voltage deviations", Sec. II-B). Could be a genuine sign
inconsistency in the paper or a misreading from this PDF's extraction of a
multi-line, subscript-heavy equation -- not resolved with confidence
either way, and NOT propagated here: this module's term has an
unambiguous, directly-tested sign instead (ev2gym_thesis/tests/test_week4.py).

Base reward, kept identical to Week 3's vanilla-TD3 arm:
ev2gym.rl_agent.reward.SqTrError_TrPenalty_UserIncentives -- unchanged, so
the controlled comparison (thesis_docs/chapters/04_oracle_and_pitd3.md
S4.4) isolates the added term as the only new variable. Eq. 14's Term 2
(profit) and Term 3 (a proactive near-departure satisfaction indicator)
are not ported, for the same reasons as before: Term 2 would reopen Week
3's S3.2 rejection of the Business/ProfitMax family; Term 3 would
introduce a second new variable, since the base reward already has its
own satisfaction penalty.

**Potential-based vs. non-potential-based shaping (Ng, Harada & Russell
1999), stated explicitly, not left implicit:** this term is
NON-potential-based -- it is not constructed as `gamma*Phi(s') - Phi(s)`
for any state potential Phi, so it is not guaranteed to leave the optimal
policy unchanged; it is meant to change learned behavior (discourage
scheduling that leaves the fleet exposed to latent capacity risk), not
merely accelerate convergence to the same policy. This is a deliberate
choice, not an oversight.
"""
from ev2gym.rl_agent.reward import SqTrError_TrPenalty_UserIncentives

# doc:begin pi_physics_margin
# doc:begin headroom_constants
# "Set for this project": the horizon over which the transformer's
# capacity profile is scanned for its minimum, so the term reacts to
# capacity dips the current step alone wouldn't reveal (this station's
# max_power profile can vary intra-day, e.g. under a demand-response
# event -- see ev2gym.models.transformer). Chosen after a sensitivity
# sweep over H in {1, 2, 4, 8} steps (15 min/step, so up to 2h ahead) --
# see thesis_docs/chapters/00_lab_log.md's 2026-08-19 entry for the
# measured effect on the disagreement rate against get_how_overloaded().
PI_TD3_HORIZON_H = 4

# "Set for this project", calibrated against the measured decomposition
# (thesis_docs/chapters/00_lab_log.md, 2026-08-19: tracking term sums to
# ~-37,778, the existing overload term to ~-3,732, over one reference
# AFAP episode) -- target: comparable magnitude to the existing overload
# term at the steps where this term is active, not dominant or negligible.
# The original design's weight, 20.0, is named here as the rejected,
# qualitatively-estimated value that motivated this recalibration.
PI_TD3_PHYSICS_WEIGHT = 50.0
# doc:end headroom_constants

# Kept for the record, not used: the original instantaneous-margin design
# (design iteration 1), rejected after the Spearman=1.0 finding -- see
# this module's docstring and thesis_docs/chapters/00_lab_log.md for the
# full rejected-alternative writeup.
PI_TD3_CAPACITY_MARGIN_FRACTION = 0.05
# doc:end pi_physics_margin


def transformer_capacity_margin_term(env) -> float:
    """REJECTED DESIGN (iteration 1), kept for the record -- not called by
    SqTrError_TrPenalty_UserIncentives_PI. Rank-correlated 1.0 with the
    vanilla reward's existing overload penalty at every weight tested."""
    total = 0.0
    for tr in env.transformers:
        max_power = tr.max_power[tr.current_step]
        margin_threshold = (1 - PI_TD3_CAPACITY_MARGIN_FRACTION) * max_power
        proximity = margin_threshold - tr.current_power
        total += min(0.0, proximity)
    return total


# doc:begin pi_physics_term
def headroom_penalty_term(env, horizon: int = PI_TD3_HORIZON_H) -> float:
    """Design iteration 2, actually used. Penalizes in proportion to how
    much the connected fleet's max-rate demand (env.charge_power_potential)
    exceeds the MINIMUM transformer capacity over the next `horizon` steps
    -- anticipatory on both sides: the fleet's latent demand (not the
    realized draw) and the capacity's near-future minimum (not just its
    current value). 0 when latent demand is within that minimum capacity;
    increasingly negative otherwise, regardless of whether the agent's
    action this step caused a realized overload. Direction is unambiguous
    and directly unit-tested (ev2gym_thesis/tests/test_week4.py).
    """
    step = env.current_step
    potential = env.charge_power_potential[step] if step < len(env.charge_power_potential) else 0.0
    total = 0.0
    for tr in env.transformers:
        end = min(step + horizon, len(tr.max_power))
        min_capacity = min(tr.max_power[step:end]) if end > step else tr.max_power[min(step, len(tr.max_power) - 1)]
        total -= max(0.0, potential - min_capacity)
    return total
# doc:end pi_physics_term


# doc:begin pi_reward_fn
def SqTrError_TrPenalty_UserIncentives_PI(env, total_costs, user_satisfaction_list, *args):
    """Drop-in reward for the TD3_HeadroomPenalty arm: Week 3's
    vanilla-TD3 reward, unchanged, plus the capacity-headroom penalty
    term. This is the ONLY difference from the vanilla-TD3 arm
    (thesis_docs/chapters/04_oracle_and_pitd3.md S4.4's controlled-
    comparison design). Function name kept for import stability across
    the naming decision (04_oracle_and_pitd3.md S4.3) -- the ALGORITHM
    name used in the registry/training scripts is TD3_HeadroomPenalty."""
    reward = SqTrError_TrPenalty_UserIncentives(env, total_costs, user_satisfaction_list, *args)
    reward += PI_TD3_PHYSICS_WEIGHT * headroom_penalty_term(env)
    return reward
# doc:end pi_reward_fn
