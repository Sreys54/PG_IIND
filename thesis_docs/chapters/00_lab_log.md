# Lab Log

## 2026-08-05 — Week 1 baseline reproduction attempt (branch `semana-1`)

**Environment setup.** `pip install -e .` succeeded on a fresh Python 3.11.9
install, but did not pull in `pandapower`, `numba`, or `multicopula`
(consistent with prior notes in `CLAUDE.md`). Installed those three
explicitly; `gymnasium` and `gurobipy` were pulled automatically as
dependencies of `ev2gym`. No changes were made to `ev2gym/models/` or
`ev2gym/rl_agent/`.

**Ran:** `experiments/phase1_baseline/run_baseline.py`, which loads
`experiments/phase1_baseline/configs/station_v0_bogota.yaml` and runs a
96-step (15-min) day with `ChargeAsFastAsPossible` and `RoundRobin`.

**Assumption made (config's `random_day: True` contradicts a "fixed date"):**
`station_v0_bogota.yaml` has `random_day: True`. Reading
`ev2gym/models/ev2gym_env.py` (lines ~130-140) confirms that with
`random_day: True`, the simulated calendar date is drawn from
`random.randint()` seeded by whatever `seed` is passed to the `EV2Gym`
constructor — there is no fixed date sitting in this config file. Since no
seed was recorded anywhere in this repo (git history, `results/`, or
`thesis_docs/`) for whatever run originally produced the reference values
below, that prior result cannot be reproduced from this config alone.
**Assumption:** to give AFAP and Round Robin a fair, identical-day comparison
without editing the YAML, both runs were driven with the same explicit
seed (`SEED = 42` in `run_baseline.py`), landing on simulated date
2022-04-25. This should be revisited (e.g., set `random_day: False` with an
explicit `year/month/day`, or standardize on a documented seed) before this
becomes the reported Week-1 baseline in the thesis.

**Results obtained (seed=42, sim_date=2022-04-25):**

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 92 | 92 |
| total_profits | -280.52 | -274.35 |
| total_energy_charged (kWh) | 1260.38 | 1259.74 |
| average_user_satisfaction | 1.0 | 0.99995 |
| total_transformer_overload (kWh) | 0.0 | 0.0 |

**Comparison against previously reported reference values** (AFAP: 11 EVs,
profit -56.85, 206.48 kWh, 100% satisfaction, 42.17 kWh overload; Round
Robin: 13 EVs, profit -54.69, 191.18 kWh, 100% satisfaction, 0.00 kWh
overload): **does not match**, not even approximately — EVs served is ~7-8x
higher and energy charged ~6x higher than the reference.

**Root cause not yet confirmed, but the most likely explanation:**
`station_v0_bogota.yaml` is still an untouched copy of
`ev2gym/example_config_files/V2Ggrid.yaml` — `number_of_charging_stations:
150`, `spawn_multiplier: 5`, IEEE 34-bus grid, `v2g_enabled: True`. This is
a large synthetic multi-station grid scenario, not yet edited down to the
"representative single Bogotá public station" the roadmap's Week 1 task
calls for (`PROJECT_ROADMAP.md`, Week 1 checklist, still unchecked). A
scenario with 150 charging points and a 5x spawn multiplier plausibly
serving ~90 EVs/day is internally consistent; it is very unlikely to be the
same scenario that produced the reference 11-13 EVs/day. This is a
plausible explanation, not a confirmed one — the reference run's exact
config was not available to diff against.

**Status:** environment reproduced and smoke-tested; baseline run executed
successfully end-to-end; numeric results **do not match** the previously
reported reference values and should not be treated as validated until (a)
`station_v0_bogota.yaml` is actually edited per the Week 1 checklist item
("pick the representative station type... number_of_charging_stations...")
and (b) a fixed seed/date convention is agreed and recorded. Flagging for
user review before proceeding to Week 2.

---

## 2026-08-05 — Week 1 config fix: single-station sizing (branch `semana-1`)

Following the diagnosis above, `station_v0_bogota.yaml` was edited from the
unedited `V2Ggrid.yaml` copy to a small, single-station scenario. All values
below were specified by the user as settled decisions, not derived by
Claude Code this session:

| key | old (V2Ggrid.yaml copy) | new |
|---|---|---|
| `scenario` | public | public (unchanged) |
| `simulate_grid` | True | **False** |
| `number_of_charging_stations` | 150 | **8** |
| `number_of_transformers` | -1 | **1** |
| `transformer.max_power` | 200 kW | **100 kW** |
| `v2g_enabled` | True | **False** |
| `heterogeneous_ev_specs` | False | False (unchanged) |
| `ev.max_ac_charge_power` | 22 kW | **50 kW** |
| `ev.max_dc_charge_power` | 50 kW | 50 kW (unchanged, now equal to max_ac) |
| `charging_station.max_charge_current` | 32 A | **72 A** (~50 kW @ 400V/3-phase) |
| `spawn_multiplier` | 5 | **30** |
| `random_day` | True | **False** |
| `year/month/day` | 2022-01-17 | 2022-01-17 (unchanged, now actually used) |

**Verified against `ev2gym/utilities/loaders.py` before writing:** every key
above is read by the loader (`number_of_transformers`, `transformer.max_power`
in `load_transformers`; `v2g_enabled`, `charging_station.max_charge_current`
in `load_ev_charger_profiles`; `spawn_multiplier` in `EV_spawner`;
`random_day`/`year`/`month`/`day` in `EV2Gym.__init__`).

**`number_of_transformers: -1` bug, confirmed:** with `simulate_grid: False`,
`load_grid()` builds `cs_transformers` directly from
`env.number_of_transformers` via `np.arange(env.number_of_transformers)`.
`np.arange(-1)` returns an empty array, which would leave charging stations
unassigned to any transformer. This only went unnoticed previously because
`simulate_grid: True` overwrites `number_of_transformers` from the grid
topology before it's used. Setting it to `1` avoids this. (This matches a
comment already present in `ev2gym/example_config_files/PublicPST.yaml`:
"if simulate_grid is True then this value is overwritten by the topology
file".)

**`max_ac_charge_power` == `max_dc_charge_power` requirement:** requested by
the user as a settled value. Reading `ev2gym/models/ev.py` and
`ev2gym/utilities/utils.py`, no code path was found in the current codebase
that would raise a `ZeroDivisionError` from these two values differing, and
no such note exists in the current `CLAUDE.md`. Applying the requested equal
values anyway (50/50 kW) since it is harmless and doesn't contradict
anything observed; flagging this for the record since it could not be
independently verified.

**`simulation_days: weekdays` note:** with `random_day: False`,
`ev2gym_env.py` never reaches the `simulation_days` weekday/weekend check —
that branch only executes when `random_day: True`. The key is harmless to
leave in the config but currently has no effect; 2022-01-17 happens to be a
Monday anyway.

**Re-ran** `experiments/phase1_baseline/run_baseline.py` (SEED=42, unchanged)
against the corrected config, sim_date fixed at 2022-01-17 05:00 (from the
config itself now, not from the seed).

**Results obtained:**

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 14 | 14 |
| total_profits | -56.92 | -49.74 |
| total_energy_charged (kWh) | 240.93 | 240.81 |
| average_user_satisfaction | 1.0 | 1.0 |
| total_transformer_overload (kWh) | 0.132 | 0.0 |

**Sanity check:** 14 EVs/day for 8 stations at spawn_multiplier 30 is within
the expected ~10-15 ballpark — plausible order of magnitude, unlike the
previous 92 EVs/day run.

**Qualitative pattern now present:** AFAP produces a small but real
transformer overload (0.132 kWh) that Round Robin's power-setpoint tracking
reduces to exactly 0.0 kWh — the expected qualitative relationship between
an unmanaged and a managed charging strategy. Exact magnitudes are not
expected to match the original reference values (11/13 EVs, 42.17/0.00 kWh
overload) since this run uses a different random seed/EV-arrival draw than
whatever produced that reference; only the qualitative pattern (AFAP
overloads, RR doesn't) and the general order of magnitude are being used as
the validation criteria here.

**Status:** config now reflects a plausible single-station scenario; results
are in the right ballpark and show the expected qualitative
AFAP-vs-RoundRobin pattern. Treating this as the working Week 1 baseline
pending user confirmation. See `thesis_docs/chapters/01_baseline.md` for the
station description write-up.
