"""
Week 6, Part 0: opt-in, process-wide cache of EV2Gym's parsed ENTSO-E price
table.

Why: TrainingDayCyclingEnv builds a fresh EV2Gym instance every episode (see
its docstring), and each instance's reset() calls
ev2gym/utilities/loaders.py::load_electricity_prices, which re-reads
Netherlands_day-ahead-2015-2024.csv and parses its ~70,000 timestamps with
dateutil four times whenever `env.price_data is None` -- measured at ~4.6 s
of a ~5 s training episode on this machine (Gate 1 profiling). The loader
itself already caches the parsed table on the instance (`env.price_data`);
this module extends that same cache across instances within one process.

What it does NOT change: the parsed table is the same object the loader
would have built, and the per-date price lookup that follows is the
loader's own code, unchanged -- so charge_prices/discharge_prices are
identical, and no random generator is touched (the parse draws no random
numbers), so training scenario draws are unaffected. Verified by
ev2gym_thesis/tests/test_final_rl_model.py, not assumed.

Never edits ev2gym/: it wraps the `load_electricity_prices` name that
ev2gym/models/ev2gym_env.py imported, from the outside.
"""
import ev2gym.models.ev2gym_env as _env_module

_ORIGINAL = _env_module.load_electricity_prices
_CACHE = {"price_data": None}


def _cached_load_electricity_prices(env):
    if getattr(env, "price_data", None) is None and _CACHE["price_data"] is not None:
        env.price_data = _CACHE["price_data"]
    out = _ORIGINAL(env)
    if _CACHE["price_data"] is None and getattr(env, "price_data", None) is not None:
        _CACHE["price_data"] = env.price_data
    return out


def enable():
    _env_module.load_electricity_prices = _cached_load_electricity_prices


def disable():
    _env_module.load_electricity_prices = _ORIGINAL
    _CACHE["price_data"] = None


def is_enabled():
    return _env_module.load_electricity_prices is _cached_load_electricity_prices
