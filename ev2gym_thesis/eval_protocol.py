"""
Week 2+ evaluation protocol: shared seeds and held-out calendar days.

Every script that runs a simulation for a reported result (registry backfill,
figure generation, algorithm comparisons in later weeks) must import SEEDS
and EVAL_DAYS from here rather than hard-coding its own, so that "5 seeds x
10 days = 50 runs" means the same 50 (seed, day) cells everywhere in the
thesis.

TRAIN_DAYS is reserved for Week 3+ RL training and is asserted disjoint from
EVAL_DAYS at import time: an RL agent must never be trained on a day it is
later evaluated on.

Week 3 adds a second, conceptually distinct kind of seed, TRAIN_SEEDS. This
distinction is subtle enough to be worth spelling out, since it is easy to
conflate the two and a thesis committee will ask about it:

- SEEDS controls the *scenario*: which stochastic EV arrivals/departures are
  drawn for a given (config, day) combination. It is the same source of
  randomness AFAP and Round Robin were evaluated under in Weeks 1-2, and RL
  agents are evaluated under it too (Entregable 6) -- SEEDS never touches
  anything about how an RL agent is built or trained.
- TRAIN_SEEDS controls the *agent*: Stable-Baselines3's network weight
  initialization and the exploration noise process during training. It has
  no scenario-generation meaning at all and is never passed to EV2Gym's
  `seed=` argument for an evaluation run.

Both are sources of randomness that must be reported, but they answer
different questions: "how much does this algorithm's measured performance
vary across scenarios" (SEEDS) vs. "how much does this algorithm's *training
outcome* vary across training runs" (TRAIN_SEEDS) -- see Entregable 7's
"dispersion across training seeds" analysis, which is kept separate from the
paired bootstrap across scenario cells for exactly this reason.
"""
import datetime

# doc:begin seeds
# CORRECTED 2026-09-08 (Week 5, Gate 3/Gate 4 -- see
# thesis_docs/chapters/00_lab_log.md's 2026-09-08 entries).
#
# ORIGINAL Weeks 1-4 values, kept for the historical record, not deleted:
#   SEEDS = [0, 1, 2, 3, 4]
#   EVAL_DAYS = 10 fixed 2022 dates (6 weekday, 4 weekend) -- see git history
#   of this file for the exact list.
#
# Found (Gate 3): for a fixed scenario_seed, EV2Gym's arrival-distribution
# selection depends only on weekday-vs-weekend (ev2gym_env.py's
# sim_date.weekday() branch, not the specific calendar date), and
# np.random.seed(self.seed) is reset identically regardless of which date
# in that category is simulated -- so the EV population was byte-identical
# across all 6 weekday EVAL_DAYS, and across all 4 weekend EVAL_DAYS, for
# every algorithm. The 10-day axis therefore added calendar bookkeeping,
# not statistical power, on the EV-population side.
#
# A second, independent bug (Gate 4) initially complicated this: EV2Gym's
# ev2gym/utilities/utils.py::generate_power_setpoints() weighted the power
# setpoint's shape by that day's real ENTSO-E price curve, so
# tracking_error (and, for setpoint-responsive algorithms, energy
# delivered/degradation/satisfaction) genuinely DID vary across
# same-category dates -- not noise, a live Dutch-price dependency inside
# the control layer itself. Fixed at the source (see that function's own
# 2026-09-08 correction comment) by making the setpoint's random
# spread price-neutral, governed only by np.random.seed(self.seed). After
# that fix, the day axis is genuinely fully redundant within a
# (seed, weekday/weekend) pair, for every deterministic algorithm.
#
# New configuration: expand SEEDS (more independent scenario draws, cheap
# -- evaluation only, no retraining) and collapse EVAL_DAYS to exactly one
# weekday + one weekend representative (now provably lossless, not a lossy
# compression). SEEDS = range(0, 50) supersedes [0..4]; the original 5 are
# a strict subset, not discarded.
SEEDS = list(range(0, 50))
# doc:end seeds

# doc:begin train_seeds
# Empirically set inside this project (not a literature value): 3 training
# seeds, sized against the ~4h total CPU training budget confirmed for Week
# 3 (see thesis_docs/chapters/00_lab_log.md's Entregable 4 entry) -- 3 full
# TD3 training runs is what that budget allows while still letting every
# seed be reported (never just the best, see Entregable 5). Disjoint from
# SEEDS by construction (100s vs. single digits) and asserted below so an
# accidental overlap fails at import time rather than silently reusing a
# scenario seed as a training seed.
TRAIN_SEEDS = [100, 101, 102]
# doc:end train_seeds

# doc:begin train_seeds_disjoint_assert
assert set(SEEDS).isdisjoint(set(TRAIN_SEEDS)), (
    "SEEDS and TRAIN_SEEDS overlap -- these are two different sources of "
    "randomness (scenario generation vs. agent training/exploration) and "
    "must stay disjoint so a seed value's meaning is unambiguous."
)
# doc:end train_seeds_disjoint_assert

# doc:begin eval_days
# CORRECTED 2026-09-08 (Week 5, Gate 3/Gate 4) -- see the SEEDS comment
# block above for the full reasoning. Collapsed from the original 10 dates
# (6 weekday, 4 weekend -- kept in git history, not reproduced here) to
# exactly one representative per day-type category, now that both the
# EV-population axis (Gate 3) and the power-setpoint axis (Gate 4) are
# confirmed fully redundant within a category for a fixed scenario_seed.
# 2022-01-17 (Monday) is the original Week 1 fixed reference day, kept for
# continuity; 2022-03-05 (Saturday) is carried over unchanged from the
# original weekend pool.
EVAL_DAYS = [
    (2022, 1, 17),   # Monday (weekday representative) -- Week 1 reference day
    (2022, 3, 5),    # Saturday (weekend representative)
]
# doc:end eval_days

# doc:begin day_type
WEEKDAY_LABEL = "weekday"
WEEKEND_LABEL = "weekend"


def day_type(day: tuple) -> str:
    """Classify an (year, month, day) tuple as 'weekday' or 'weekend',
    matching the exact branch EV2Gym's own arrival-distribution selection
    uses (ev2gym_env.py: sim_date.weekday() < 5) -- not a separate
    hardcoded date list that could silently drift from the real branch."""
    return WEEKDAY_LABEL if day_to_date(day).weekday() < 5 else WEEKEND_LABEL
# doc:end day_type

# doc:begin reference_day
# Single designated EVAL_DAYS element used for single-day figures (e.g. the
# power-profile plot) where overlaying 50 runs would be unreadable. Chosen
# to match the Week 1 fixed reference day for continuity with the already
# published Week 1 numbers.
REFERENCE_DAY = (2022, 1, 17)
assert REFERENCE_DAY in EVAL_DAYS, "REFERENCE_DAY must be one of EVAL_DAYS"
# doc:end reference_day

# doc:begin train_days
# Disjoint pool of dates reserved for Week 3+ RL training. 20 dates, spread
# across the year with a similar weekday/weekend mix to EVAL_DAYS. This is
# an initial pool sized for a first vanilla-TD3/SAC pass under the reduced
# training budget noted in CLAUDE.md; it can be extended later if a larger
# training set turns out to be needed.
TRAIN_DAYS = [
    (2022, 1, 24), (2022, 2, 7), (2022, 2, 21), (2022, 3, 19),
    (2022, 4, 13), (2022, 4, 27), (2022, 5, 9), (2022, 6, 4),
    (2022, 6, 22), (2022, 7, 26), (2022, 8, 3), (2022, 8, 17),
    (2022, 9, 7), (2022, 9, 29), (2022, 10, 12), (2022, 10, 26),
    (2022, 11, 23), (2022, 12, 7), (2022, 12, 17), (2022, 12, 28),
]
# doc:end train_days

# doc:begin disjoint_assert
assert set(EVAL_DAYS).isdisjoint(set(TRAIN_DAYS)), (
    "EVAL_DAYS and TRAIN_DAYS overlap -- an RL agent must never be "
    "evaluated on a day it could have been trained on."
)
# doc:end disjoint_assert


def day_to_date(day):
    """Convert an (year, month, day) tuple from EVAL_DAYS/TRAIN_DAYS to a datetime.date."""
    return datetime.date(*day)
