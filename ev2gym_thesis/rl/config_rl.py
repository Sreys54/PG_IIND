"""
Week 3, Entregable 2: TD3 hyperparameters, every one with a declared origin.

Origins used, exactly one per constant below:
  "SB3 default"                       -- stable_baselines3.td3.TD3's own
                                          __init__ default, read directly
                                          from the installed
                                          stable_baselines3==2.9.0 source
                                          (site-packages/stable_baselines3/
                                          td3/td3.py and td3/policies.py),
                                          not assumed from memory.
  "TD3 paper"                         -- Fujimoto et al. (2018), "Addressing
                                          Function Approximation Error in
                                          Actor-Critic Methods" -- also the
                                          origin SB3 itself cites for its own
                                          defaults in most cases, called out
                                          separately only where this project
                                          deviates from the SB3 default.
  "set for this project's CPU budget" -- reduced below the SB3
                                          default/paper value specifically
                                          because Week 3's confirmed budget
                                          is CPU-only, ~4h total across 3
                                          training seeds (see Entregable 4 in
                                          thesis_docs/chapters/00_lab_log.md)
                                          -- each such constant states what
                                          it's reduced FROM.
"""
import numpy as np
from stable_baselines3.common.noise import NormalActionNoise

from ev2gym_thesis.eval_protocol import TRAIN_SEEDS

# Network architecture: reduced from the SB3 default / TD3 paper's [400, 300]
# (tuned for higher-dimensional continuous-control benchmarks such as
# MuJoCo's ~17-111 dim observation/action spaces) to [64, 64], set for this
# project's CPU budget. This environment's observation is 27-dim and its
# action is 8-dim for station_v0_bogota -- a 400x300 network is
# disproportionately large for that input size and would slow every
# gradient step for no expected benefit at this problem scale.
#
# Replay buffer: reduced from SB3 default 1,000,000 to 50,000, set for this
# project's CPU budget -- at Week 3's scale (at most a few hundred thousand
# timesteps total across all 3 training seeds, see Entregable 4) a 1e6
# buffer would spend the entire run mostly empty, wasting the RAM
# allocation for no replay-diversity benefit.
#
# Learning starts: reduced... no, INCREASED from SB3 default 100 to 500
# (~5 episodes at 96 steps/episode), set for this project's CPU budget:
# with a short total training budget, giving the replay buffer a handful of
# full episodes' worth of uniform-random transitions before the first
# gradient update is a larger fraction of the run than it would be in a
# paper's million-step training, so it's worth a few more steps of pure
# exploration up front.
#
# Exploration noise: TD3 paper. SB3's TD3 does not add exploration noise by
# default (action_noise=None) -- confirmed by reading td3.py's __init__
# signature; the paper's own recipe adds N(0, 0.1) Gaussian noise to
# actions during data collection, which SB3 exposes via the action_noise
# argument. This project's action space is [0, 1]^n (v2g_enabled=False,
# see station_v0_bogota.yaml), so sigma=0.1 is relative to that full [0, 1]
# range, not to a symmetric [-1, 1] range as in the original paper's MuJoCo
# tasks -- same relative exploration magnitude, different absolute scale.
# doc:begin td3_hyperparams
POLICY = "MlpPolicy"          # SB3 default policy class for a flat vector observation
NET_ARCH = [64, 64]           # set for this project's CPU budget (reduced from SB3 default/TD3 paper [400, 300])
LEARNING_RATE = 1e-3          # SB3 default
GAMMA = 0.99                  # SB3 default
TAU = 0.005                   # SB3 default ("Polyak" target-network update rate)
TRAIN_FREQ = 1                # SB3 default (one env step per gradient-update opportunity)
GRADIENT_STEPS = 1            # SB3 default
POLICY_DELAY = 2              # SB3 default / TD3 paper (delayed policy updates, TD3's namesake mechanism)
TARGET_POLICY_NOISE = 0.2     # SB3 default / TD3 paper (target policy smoothing noise std)
TARGET_NOISE_CLIP = 0.5       # SB3 default / TD3 paper (target policy smoothing noise clip)
BATCH_SIZE = 256              # SB3 default
BUFFER_SIZE = 50_000          # set for this project's CPU budget (reduced from SB3 default 1,000,000)
LEARNING_STARTS = 500         # set for this project's CPU budget (increased from SB3 default 100)
ACTION_NOISE_SIGMA = 0.1      # TD3 paper (exploration noise, relative to this project's [0,1] action range)


def make_action_noise(n_actions: int) -> NormalActionNoise:
    return NormalActionNoise(mean=np.zeros(n_actions), sigma=ACTION_NOISE_SIGMA * np.ones(n_actions))
# doc:end td3_hyperparams


# doc:begin vecnormalize_config
# Design decision: wrap the training env in VecNormalize (normalize
# observations AND reward). Rejected alternative: no normalization. This
# environment's observation vector mixes wildly different scales in the
# same vector (a 0/0.5/1 "is full" flag, energy_exchanged in kWh up to
# ~70, dwell time in simulation steps up to ~96, current power usage in kW
# up to ~400) -- TD3's actor/critic networks are not scale-invariant, and
# leaving this unnormalized risks the largest-magnitude features (dwell
# time, power) dominating gradients over the binary/near-zero ones. This is
# exactly the failure mode VecNormalize exists to prevent, and it's the
# standard recipe for off-policy continuous control in this size regime.
# NORM_OBS/NORM_REWARD both True during training; evaluation reloads the
# saved statistics with training=False, norm_reward=False (see Entregable 6
# and the corresponding test in ev2gym_thesis/tests/) -- reward
# normalization is a training-time-only convenience and must never leak
# into reported evaluation metrics.
VECNORMALIZE_NORM_OBS = True     # design decision, see above
VECNORMALIZE_NORM_REWARD = True  # design decision, see above (training only)
VECNORMALIZE_CLIP_OBS = 10.0     # SB3 VecNormalize default
VECNORMALIZE_GAMMA = GAMMA       # must match the TD3 discount factor (SB3 VecNormalize's reward normalizer uses gamma internally)
# doc:end vecnormalize_config


# doc:begin timesteps_confirmed
# TOTAL_TIMESTEPS: confirmed by the user 2026-08-12 (per CLAUDE.md rule 2 --
# training wall-clock must be confirmed before any long run) after the
# Entregable 4 calibration below. Measured: 5,000 timesteps = 276.4s (18.09
# steps/s) on station_v0_bogota with these exact hyperparameters. 60,000
# timesteps/seed = ~55.3 min/seed, ~165.9 min (2.8h) for all 3 TRAIN_SEEDS --
# the largest of 4 presented candidates (15k/30k/60k/90k) that respects
# BOTH the user's stated ~75 min/seed ceiling and ~4h total budget (90k
# would have been 82.9 min/seed, breaking the per-seed ceiling). At this
# budget the agent sees each of the 20 TRAIN_DAYS dates ~31 times
# (round-robin cycling, see env_factory.TrainingDayCyclingEnv). This is a
# declared, drastic reduction against the PI-TD3/TD3 papers' HPC training
# budgets of 5-48 hours -- NOT presented as an equivalent training regime;
# see thesis_docs/chapters/00_lab_log.md's Entregable 4 entry for the full
# comparison and thesis_docs/chapters/03_rl_baseline.md for how this bounds
# what can be claimed about convergence.
TOTAL_TIMESTEPS = 60_000
# doc:end timesteps_confirmed

CALIBRATION_TIMESTEPS = 5_000  # Entregable 4's fixed calibration run size, not a hyperparameter choice

# doc:begin callback_freqs
# Checkpoint every 10,000 steps (6 checkpoints across a 60,000-step run) --
# set for this project's CPU budget: frequent enough that an interrupted
# ~55-minute run loses at most ~9 minutes of progress, not frequent enough
# to make checkpoint I/O (full model + VecNormalize stats) a meaningful
# fraction of wall-clock time.
CHECKPOINT_FREQ_STEPS = 10_000  # set for this project's CPU budget

# Learning-curve CSV logged every 500 steps (120 rows across a 60,000-step
# run) -- set for this project's CPU budget: dense enough to see the shape
# of a short training curve, sparse enough that ep_info_buffer-based
# averaging (over up to the last 100 episodes) has enough new episodes
# between log points to move meaningfully.
LEARNING_CURVE_LOG_FREQ_STEPS = 500  # set for this project's CPU budget
# doc:end callback_freqs

# doc:begin train_seeds_note
# TRAIN_SEEDS (imported, not redefined here) is the set of 3 training seeds
# every TD3 run in Week 3 must use -- see ev2gym_thesis/eval_protocol.py for
# the full SEEDS-vs-TRAIN_SEEDS distinction and origin.
_ = TRAIN_SEEDS  # re-exported for callers that only import config_rl
# doc:end train_seeds_note
