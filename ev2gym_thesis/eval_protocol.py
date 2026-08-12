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
"""
import datetime

# doc:begin seeds
SEEDS = [0, 1, 2, 3, 4]
# doc:end seeds

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
