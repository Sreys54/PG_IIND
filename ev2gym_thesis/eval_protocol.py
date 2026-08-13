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
SEEDS = [0, 1, 2, 3, 4]
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
# 10 fixed 2022 calendar dates, held out and never used for tuning or RL
# training. Chosen to spread across the year (roughly one every 5-6 weeks,
# avoiding December to sidestep end-of-year holiday effects on arrival
# patterns) and to mix weekdays and weekends: 6 weekdays (Mon/Wed) and 4
# weekend days (3x Saturday, 1x Sunday). Day-of-week for each date was
# verified with datetime.date(...).strftime('%A'), not assumed.
EVAL_DAYS = [
    (2022, 1, 17),   # Monday   -- also the Week 1 fixed reference day
    (2022, 2, 14),   # Monday
    (2022, 3, 5),    # Saturday
    (2022, 4, 6),    # Wednesday
    (2022, 5, 21),   # Saturday
    (2022, 6, 15),   # Wednesday
    (2022, 7, 10),   # Sunday
    (2022, 8, 24),   # Wednesday
    (2022, 9, 17),   # Saturday
    (2022, 11, 9),   # Wednesday
]
# doc:end eval_days

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
