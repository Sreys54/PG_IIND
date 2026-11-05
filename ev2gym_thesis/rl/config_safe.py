"""
Week 8 (redesigned RL): hyperparameters and design for the projected TD3 agent
("TD3_safe"), every value with a declared origin.

Why a new config instead of editing config_rl.py. config_rl.py is the exact
configuration behind every Weeks 3-7 RL result (registry rows, figures,
chapters 03-06). It is left untouched so those results stay reproducible;
this module holds the corrected design, used only by
scripts/train_td3_safe.py and scripts/evaluate_safe_rl.py.

What changed, and why (review of 2026-10-14, chapter 08 item 48):
  1. Transformer limit: a hard constraint (ev2gym_thesis/rl/safety.py), not a
     reward penalty.
  2. Reward: ServedEnergyReward (ev2gym_thesis/rl/reward_service.py), whose
     episode return is exactly the energy delivered, i.e. it minimises demand
     not served with no weight to tune. The old composite reward is retired.
  3. State: ServiceState (ev2gym_thesis/rl/state_service.py), which adds each
     EV's state of charge (its remaining need), still without departure times.
  4. Hyperparameters: the TD3 authors' reference implementation, instead of
     values reduced for the Week 3 CPU budget. The reference is
     github.com/sfujim/TD3 (TD3.py, main.py, utils.py), read on 2026-10-24;
     every constant below quotes it. Where this project departs from it, the
     comment says from what and why.
  5. Selection: the validation criterion is the energy delivered (aligned
     with the reward), not tracking error.

Origins used:
  "TD3 reference implementation" -- sfujim/TD3, the value quoted in the comment.
  "SB3 default"                  -- stable_baselines3 2.9.0, td3.py.
  "set for this project"         -- departs from the reference; the comment
                                    states from what and why.
"""
import numpy as np
from stable_baselines3.common.noise import NormalActionNoise

from ev2gym_thesis.rl.reward_service import ServedEnergyReward, CappedTrackingReward
from ev2gym_thesis.rl.state_service import ServiceState, ServiceStateCausal

# doc:begin safe_td3_hyperparams
POLICY = "MlpPolicy"            # SB3 default for a flat vector observation
NET_ARCH = [256, 256]           # TD3 reference implementation: actor and critics are Linear(.,256)-Linear(256,256) (TD3.py, Actor/Critic)
LEARNING_RATE = 3e-4            # TD3 reference implementation: Adam(lr=3e-4) for actor and critic (TD3.py)
GAMMA = 0.99                    # TD3 reference implementation: discount=0.99. A 96-step day sits inside the ~100-step effective horizon
TAU = 0.005                     # TD3 reference implementation: tau=0.005
TRAIN_FREQ = 1                  # TD3 reference implementation: one gradient update per environment step (main.py loop)
GRADIENT_STEPS = 1              # TD3 reference implementation, as above
POLICY_DELAY = 2                # TD3 reference implementation: policy_freq=2
TARGET_POLICY_NOISE = 0.2       # TD3 reference implementation: policy_noise=0.2 x max_action; SB3 applies it in the [-1, 1] policy space, the same scale
TARGET_NOISE_CLIP = 0.5         # TD3 reference implementation: noise_clip=0.5 x max_action, same note
BATCH_SIZE = 256                # TD3 reference implementation: batch_size=256
ACTION_NOISE_SIGMA = 0.1        # TD3 reference implementation: expl_noise=0.1 x max_action, i.e. 0.1 of the half-range. SB3 adds the noise
                                # in the policy's [-1, 1] space (off_policy_algorithm._sample_action), so sigma=0.1 there is the same
                                # magnitude. (config_rl.py's comment read sigma as relative to [0, 1]; it is the half-range, 0.05 of [0, 1].)
LEARNING_STARTS = 10_000        # set for this project: the reference uses start_timesteps=25e3 of a 1e6-step budget (2.5%); 10,000 steps
                                # (~104 episodes of uniformly random actions) is 2-5% of the 220k-500k steps this run is expected to take
BUFFER_SIZE = 300_000           # set for this project: the reference uses max_size=1e6 (utils.py). The observation is float64, so 1e6
                                # transitions are ~0.6 GB in RAM and on disk per saved buffer, per seed, inside a OneDrive-synced folder.
                                # 300,000 keeps the most recent ~3,100 episodes, at least half of the expected run.


def make_action_noise(n_actions: int) -> NormalActionNoise:
    return NormalActionNoise(mean=np.zeros(n_actions), sigma=ACTION_NOISE_SIGMA * np.ones(n_actions))
# doc:end safe_td3_hyperparams

# doc:begin safe_vecnormalize
# Observations are standardised (their scales still differ: SoC in [0, 1],
# steps connected / T, power / rating). Rewards are NOT normalised: the
# served-energy reward is already in [0, 1] by construction, and keeping it
# raw keeps the critic's targets interpretable (return = energy / 25 kWh)
# and removes a non-stationary scaling the old design had.
VECNORMALIZE_NORM_OBS = True
VECNORMALIZE_NORM_REWARD = False
VECNORMALIZE_CLIP_OBS = 10.0    # SB3 VecNormalize default
VECNORMALIZE_GAMMA = GAMMA
# doc:end safe_vecnormalize

# doc:begin safe_design
STATE_FN = ServiceStateCausal
# Week 8 review (A6/C1): ServiceState passes EV2Gym's power setpoint, which
# is built from every EV's departure time and energy and the next arrivals
# (non-causal). ServiceStateCausal drops it. Author's decision, 2026-11-03
# (Gate 1+2): TD3_safe uses ServiceStateCausal, so the trained agent is a
# causal arm. ServiceState stays selectable with train_td3_safe.py --state;
# the choice is recorded in the run manifest.
STATE_FNS = {"service": ServiceState, "service_causal": ServiceStateCausal}
REWARD_FNS = {"served_energy": ServedEnergyReward, "tracking": CappedTrackingReward}
DEFAULT_REWARD = "served_energy"

# Regimes (06 S6.8). The DC regime config is the dwell brief's own 1.0x
# variant: the reference YAML plus a <config>.dwell.json sidecar with the
# 42-minute lognormal session model (ev2gym_thesis/demand/dc_sessions.py).
#
# Week 8 advisor review (2026-11-01), C3: the dc42 regime now uses the
# station-level arrival generator (ev2gym_thesis/demand/station_arrivals.py)
# at 1.0x (627 kWh/day offered), with the config's <config>.arrivals.json
# sidecar. The dwell brief's per-port-spawner config is kept under
# "dc42_spawner" for provenance only; no TD3_safe model was ever trained on it.
REGIME_CONFIGS = {
    "dc42": "experiments/phase4_review/configs/station_v0_bogota_dc42_poisson_1.00x_p8_tr100.yaml",
    "dc42_spawner": "experiments/phase3_infra_replicability/configs/dwell/station_v0_bogota_dc42_sp30.yaml",
    "long": "experiments/phase1_baseline/configs/station_v0_bogota.yaml",
}
DEFAULT_REGIME = "dc42"

# Validation criterion, aligned with the reward: mean energy delivered over
# the 20 validation cells (higher is better). It is strictly positive and of
# order 10^2 kWh, so extended_training's relative convergence thresholds are
# meaningful. For the tracking reward the criterion is tracking error.
SELECTION = {"served_energy": ("total_energy_charged", False), "tracking": ("tracking_error", True)}
VALIDATION_LOG_METRICS = ["total_energy_charged", "average_user_satisfaction", "energy_user_satisfaction",
                          "total_transformer_overload", "tracking_error", "total_ev_served"]
# Week 8 review C3 (advisor 3.4): also logged at every validation, so the
# advisor's comparison can be made on the new agent too -- the three terms of
# the retired reward SqTrError_TrPenalty_UserIncentives (computed post hoc
# per step by ev2gym_thesis/metrics/service.py, summed per episode), and the
# A1 service metrics (exact DNS, mean energy satisfaction f including
# rejected drivers, service level f >= 0.9 including rejected drivers).
VALIDATION_EXTRA_METRICS = ["old_r_tracking", "old_r_overload", "old_r_user", "dns_exact", "mean_f_all",
                            "service_level_all", "arrivals_rejected"]
# doc:end safe_design

# doc:begin safe_selection_rule
# Checkpoint-selection rule and carried-model rule (Week 8 review C3), fixed
# here BEFORE the training run and copied verbatim into the handback:
#  1. Every 10,000 steps the checkpoint is validated (deterministic policy,
#     frozen VecNormalize, safety layer on) on the 20 validation cells
#     (seeds 1,000,000-1,000,009 x {2022-01-31 weekday, 2022-03-12 weekend});
#     the criterion is the mean energy delivered (total_energy_charged,
#     higher is better).
#  2. Convergence (ev2gym_thesis/rl/extended_training.py,
#     convergence_index): over windows of W = 5 evaluations (50,000 steps),
#     |mean(last W) - mean(previous W)| / |mean(previous W)| < 2% and
#     std(last W) / |mean(last W)| < 5%, on 3 consecutive evaluations.
#  3. The seed's final checkpoint is the one with the best validation value at
#     or after the convergence declaration (select_primary_index). If the seed
#     never converges before the deadline, it is the best-validation
#     checkpoint over the whole run, and non-convergence is reported as a
#     result (brief C3, after training).
#  4. Carried model: of the training seeds 100, 101, 102, the seed whose final
#     checkpoint has the best validation value is THE TD3_safe model used in
#     every later table; the test results (seeds 0-49 x 2 days) of every
#     seed's final checkpoint are reported next to it.
SELECTION_RULE_VERSION = "week8_review_2026-11-03"
CARRIED_MODEL_RULE = "best validation total_energy_charged among the seeds' final checkpoints"


# doc:begin long_budget_sensitivity
# Long-budget sensitivity (Week 8 review, C3 follow-up), approved by the
# author on 2026-11-03 ("opcion A") and fixed HERE BEFORE the runs started,
# after the C3 results were known:
#  1. Seeds 100, 101, 102, the same design, state (service_causal), reward,
#     hyperparameters, validation cells and cadence as C3, trained from
#     scratch to a fixed budget of 2,000,000 steps with NO convergence stop
#     (train_td3_safe.py --fixed-budget --max-steps 2000000), run root
#     C:/ev2gym_runs/w8_td3_safe_long. Amended by the author at 23:15, before
#     any long-run result: the first launch (1,000,000 steps, 23:05) was
#     stopped after its first validation (10,000 steps, identical to C3) and
#     moved to C:/ev2gym_runs/w8_td3_safe_long_aborted_1M; it is not used.
#     Seeds 100 and 101 run in parallel, then 102; hard stop 2026-11-05
#     23:59 UTC-5 (a seed stopped by it is reported with stop_reason
#     "deadline" and its last checkpoint).
#  2. Two checkpoints per seed are tested on the C3 test grid (300 cases,
#     1.0/1.3/1.6x): the last one (2,000,000 steps) and the best validation
#     value over the whole run. Registry arms TD3_safe_long_last_ts<seed> and
#     TD3_safe_long_bestval_ts<seed>.
#  3. The carried TD3_safe model does NOT change, whatever these runs give:
#     it is the C3 rule's output (seed 100, 150,000 steps). The results are
#     reported as a sensitivity, in full, whether better or worse.
LONG_BUDGET_STEPS = 2_000_000
LONG_BUDGET_RULE = ("fixed 2,000,000 steps, no convergence stop; test the last and the best-validation checkpoint "
                    "per seed; carried model unchanged; reported in full as a sensitivity (2026-11-03)")
# doc:end long_budget_sensitivity


def final_index(m, conv_idx, lower_is_better=False):
    """Rule 3 above: best at/after convergence, else best over the run."""
    m = np.asarray(m, dtype=float)
    lo = 0 if conv_idx is None else conv_idx
    w = m[lo:]
    return lo + int(np.argmin(w) if lower_is_better else np.argmax(w))
# doc:end safe_selection_rule


def arm_name(regime: str, reward: str) -> str:
    return "TD3_safe_" + regime + ("" if reward == DEFAULT_REWARD else f"_{reward}")


def hyperparameters_dict() -> dict:
    return {k: globals()[k] for k in (
        "POLICY", "NET_ARCH", "LEARNING_RATE", "BUFFER_SIZE", "LEARNING_STARTS", "BATCH_SIZE", "TAU", "GAMMA",
        "TRAIN_FREQ", "GRADIENT_STEPS", "POLICY_DELAY", "TARGET_POLICY_NOISE", "TARGET_NOISE_CLIP",
        "ACTION_NOISE_SIGMA", "VECNORMALIZE_NORM_OBS", "VECNORMALIZE_NORM_REWARD", "VECNORMALIZE_CLIP_OBS")}


# doc:begin enable_regime
def enable_regime(regime: str) -> str:
    """Install the regime's demand model process-wide, before any EV2Gym is
    built; return the config path. dc42: the station-level arrival generator
    (sidecar <config>.arrivals.json); dc42_spawner: EV2Gym's spawner with the
    42-minute duration transform (sidecar <config>.dwell.json); long: none."""
    from ev2gym_thesis.demand import dc_sessions, station_arrivals
    config_path = REGIME_CONFIGS[regime]
    if regime == "dc42":
        spec = station_arrivals.spec_for_config(config_path)
        assert spec is not None and spec.dwell.mean_min == 42.0 and abs(spec.level - 1.0) < 1e-9, \
            f"{config_path} must carry the 1.0x station-arrivals sidecar"
        station_arrivals.enable(spec)
    elif regime == "dc42_spawner":
        model = dc_sessions.model_for_config(config_path)
        assert model is not None and model.mean_min == 42.0
        dc_sessions.enable(model)
    else:
        assert dc_sessions.model_for_config(config_path) is None
    return config_path


def disable_regime():
    from ev2gym_thesis.demand import dc_sessions, station_arrivals
    station_arrivals.disable()
    dc_sessions.disable()
# doc:end enable_regime
