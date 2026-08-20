"""
Week 4, Entregable 5: PI-TD3's reward, adapted to a transformer-limited,
simulate_grid=False configuration. Drop-in for env_factory.DEFAULT_REWARD_FN
-- no env_factory.py/config_rl.py/callbacks.py/eval_utils.py change was
needed to wire this in, which is itself worth recording (the Week 3
separation held).

**Scope, decided with the user 2026-08-19 after reading the PI-TD3 paper in
full (thesis_docs/references/pi_td3_paper.pdf) -- a THIN adaptation, and
this is stated here, not hidden:** PI-TD3's actual novel mechanism is not
its reward shape. Algorithm 1 line 11 ("Update actor using del_theta J(theta)
from (20)") replaces TD3's standard single-transition actor update with a
K-step, model-based, DIFFERENTIABLE rollout: a differentiable transition
model (Eq. 18, the piecewise SoC update) and a differentiable reward model
(Eq. 14, including a power-flow-derived voltage term) are used to simulate
K steps forward and backpropagate gradients directly into the actor,
bypassing the environment. Fig. 3b's rollout-horizon ablation (K=5/10/20/40)
is the paper's own evidence that THIS mechanism, not the reward term alone,
drives PI-TD3's sample-efficiency gain over vanilla TD3.

Porting that mechanism would mean writing a custom differentiable transition
model and replacing Stable-Baselines3's TD3.train() actor-update step
entirely (not a swappable reward/state module -- a different training
loop), a materially larger undertaking than this week's budget, and not
something `simulate_grid=False` has the underlying power-flow model to
support even if built. **This module ports only the reward term** (Eq. 14's
Term 1, the physics-based penalty), run through SB3's standard TD3 actor
update, identically to Week 3's vanilla TD3. This is an adaptation of
PI-TD3's physics-informed PRINCIPLE (a physical-limit-aware reward shape)
to this configuration -- not a reproduction of Algorithm 1's model-based
training mechanism. The rejected alternative (the full differentiable
rollout) and why it was rejected is recorded here and in
thesis_docs/chapters/04_oracle_and_pitd3.md S4.3, not silently dropped.

**A genuine ambiguity found while reading Eq. 14, recorded rather than
silently resolved either way:** the paper states weights
lambda_1 = -5e4, lambda_2 = 1, lambda_3 = -10 (Sec. IV-A) for Eq. (1)/(14).
Applied literally to Term 1 (lambda_1 * min{0, 0.05 - |1 - V|}, a
quantity that is 0 when compliant and increasingly NEGATIVE the worse the
violation), a NEGATIVE lambda_1 makes the product increasingly POSITIVE
as violations worsen -- rewarding larger violations under a MAXIMIZED
reward (Eq. 16/Algorithm 1), the opposite of the paper's own stated intent
("the first term penalizes voltage deviations", Sec. II-B). This could be
a genuine sign inconsistency in the paper, or a misreading introduced by
this PDF's text extraction of a multi-line, subscript-heavy equation (a
known extraction risk) -- not resolved with confidence either way, and NOT
propagated into this module. Instead, this module's own term is built with
an unambiguous, directly-testable sign (0 within margin, negative and
worsening outside it -- see ev2gym_thesis/tests/test_week4.py), matching
the paper's PROSE description of what Term 1 is supposed to do, independent
of how its literal numeric coefficient should be read.

Base reward, kept identical to Week 3's vanilla-TD3 arm:
ev2gym.rl_agent.reward.SqTrError_TrPenalty_UserIncentives (tracking error +
transformer overload penalty + user satisfaction penalty) -- unchanged, so
that the controlled comparison (thesis_docs/chapters/04_oracle_and_pitd3.md
S4.4) isolates the added physics term as the only new variable. Eq. 14's
Term 2 (profit) is not ported: this thesis's reward family already
excluded the Business/ProfitMax objective in Week 3 (03_rl_baseline.md
S3.2), and porting it here would silently reopen that decision. Eq. 14's
Term 3 (a proactive, near-departure satisfaction indicator) is not ported
either -- Week 3's reward already has its own satisfaction penalty
(`-1000 * (1 - score)` per departing EV); duplicating a second, structurally
different satisfaction term would confound the comparison with two new
variables instead of one, contrary to S4.4's design.
"""
from ev2gym.rl_agent.reward import SqTrError_TrPenalty_UserIncentives

# doc:begin pi_physics_margin
# "PI-TD3 paper Eq. 14 Term 1": the paper's voltage term is a dead-zone
# penalty of half-width 0.05 p.u. (5% of nominal voltage) -- zero while
# |1-V| stays within that margin, increasingly negative beyond it. This
# thesis's configuration has no voltage variable (simulate_grid=False), so
# the natural substitute -- per the Week 4 brief's own framing -- is the
# transformer's power capacity. Reinterpreted here as a ONE-SIDED margin
# (a transformer has no equivalent of undervoltage; only exceeding
# capacity is a physical concern), unlike the paper's two-sided voltage
# band: the term stays 0 while power draw is below
# (1 - PI_TD3_CAPACITY_MARGIN_FRACTION) * transformer_max_power, and
# ramps linearly negative above that pre-violation threshold -- giving
# the agent gradient signal BEFORE an actual overload, which is the
# paper's own stated motivation for Term 1 ("richer gradient information",
# Sec. III-A) applied to this configuration's one physical constraint.
PI_TD3_CAPACITY_MARGIN_FRACTION = 0.05

# "Set for this project": the paper's own lambda_1 = -5e4 could not be
# reused with confidence (see the sign-ambiguity note in this module's
# docstring), and even if it could, it was calibrated against a
# differently-scaled voltage-deviation quantity (p.u., bounded in [0,1])
# vs. this term's kW-scale quantity. Chosen empirically so the physics
# term's magnitude is comparable to, not dominated by or dominating,
# SqTrError_TrPenalty_UserIncentives's existing -100*get_how_overloaded()
# term at a typical single-step overload of a few kW (this station's
# observed AFAP overload, Week 1-3, is O(1-10) kW per violating step) --
# not tuned via a training sweep, a declared limitation, not a hidden one.
PI_TD3_PHYSICS_WEIGHT = 20.0
# doc:end pi_physics_margin


# doc:begin pi_physics_term
def transformer_capacity_margin_term(env) -> float:
    """The Eq. 14 Term 1 analogue: 0 while every transformer's power draw
    is within its pre-violation margin, increasingly negative beyond it.
    Direction is unambiguous and directly unit-tested (see
    ev2gym_thesis/tests/test_week4.py) -- unlike the paper's own Term 1,
    whose literal numeric sign could not be confirmed from the source PDF
    (see this module's docstring)."""
    total = 0.0
    for tr in env.transformers:
        max_power = tr.max_power[tr.current_step]
        margin_threshold = (1 - PI_TD3_CAPACITY_MARGIN_FRACTION) * max_power
        proximity = margin_threshold - tr.current_power  # >0 = safely below margin, <0 = inside margin or overloaded
        total += min(0.0, proximity)
    return total
# doc:end pi_physics_term


# doc:begin pi_reward_fn
def SqTrError_TrPenalty_UserIncentives_PI(env, total_costs, user_satisfaction_list, *args):
    """Drop-in PI-TD3 reward: Week 3's vanilla-TD3 reward, unchanged, plus
    the physics-informed transformer-capacity-margin term. This is the
    ONLY difference from the vanilla-TD3 arm (thesis_docs/chapters/
    04_oracle_and_pitd3.md S4.4's controlled-comparison design)."""
    reward = SqTrError_TrPenalty_UserIncentives(env, total_costs, user_satisfaction_list, *args)
    reward += PI_TD3_PHYSICS_WEIGHT * transformer_capacity_margin_term(env)
    return reward
# doc:end pi_reward_fn
