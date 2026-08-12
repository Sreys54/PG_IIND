# Week 2 — Parameter, Method, and Implementation Justification

**Git commit:** `05317b75b2c199f567445246f7dae09fb7632907`
**Generated:** 2026-08-12T23:31:30.912613Z (regenerate with `PYTHONPATH=. python scripts/make_week2_handback.py` after any code change — this document is built, not hand-maintained)

Note on continuity with Week 1: no standalone Week 1 justification document
of this same name/format exists in this repository (the Week 1 equivalent
content lives inside `thesis_docs/chapters/01_baseline.md`). From Week 2
onward this dedicated hand-back document format is used, per this week's
instructions, and will continue in this format for future weeks.

This document has two halves: **Part 1** (parameters and methods, in the
same validated/empirical/simplification labeling convention as
`thesis_docs/chapters/02_model_validation.md`) and **Part 2** (implementation
— every new file created this week, why it exists, what it decides, and the
actual code that encodes each decision).

## Part 1 — Parameters and Methods

Model-level parameters (station size, connector power, transformer
capacity, spawn rate, fleet homogeneity, arrival distributions, prices,
grid representation, queueing) were already itemised in
`thesis_docs/chapters/02_model_validation.md` and are not repeated here.
This section covers parameters **introduced this week** by the evaluation
protocol, the station-size sensitivity sweep, and the degradation
calibration.

| Parameter | Value | Label | Justification |
|---|---|---|---|
| `SEEDS` | `[0, 1, 2, 3, 4]` | Empirically set inside this project | Five arbitrary small integers, chosen only for determinism and to give the paired bootstrap enough independent draws per (config, algorithm, day) cell; not tuned. |
| `EVAL_DAYS` | 10 fixed 2022 dates (6 weekday, 4 weekend) | Empirically set inside this project | Spread roughly monthly across the year to avoid seasonal clustering, with day-of-week verified via `datetime.date(...).strftime('%A')` rather than assumed. Not sourced from any external sampling standard. |
| `TRAIN_DAYS` | 20 fixed 2022 dates, disjoint from `EVAL_DAYS` | Empirically set inside this project | Reserved for Week 3+ RL training; disjointness is asserted at import time (see Part 2, `eval_protocol.py`) so a training/evaluation leak is a hard import-time failure, not a silent bug. |
| Station-size sweep: port counts | 2, 8, 16 | Empirically set inside this project | 8 is the already-validated reference (`station_v0_bogota`, Enel X-grounded); 2 and 16 bracket it by roughly 4x in each direction, chosen for sensitivity-sweep coverage, not from a specific real-site distribution beyond the Enel X range already cited (median 2, max 16). |
| Station-size sweep: transformer policies | Policy A fixed 100 kW; Policy B scaled to hold 4:1 | Empirically set inside this project | Isolates two different questions: does port count alone matter at fixed capacity (Policy A), or does the ratio matter more than the absolute scale (Policy B)? Neither is a literature value — see `02_model_validation.md`'s transformer-capacity row. |
| Bogota ambient temperature: annual mean | 13.68 C | Validated against external source | IDEAM `normales_climatologicas_periodo_1981-2010.xlsx`, station 21205791 (Aeropuerto El Dorado). Corrects an earlier, unverified assumption of 13.3 C. |
| Bogota ambient temperature: daily max / min | 19.31 C / 7.88 C | Validated against external source | Same IDEAM source, annual mean of monthly daily-max / daily-min normals. |
| Diurnal trough/peak hours (06:00 / 14:30) | assumed | Simplification / declared limitation | NOT in the IDEAM normals file (monthly/annual only, no hourly curve) — a general assumption about tropical-highland diurnal timing. |
| Underground ambient swing | +/-0.75 C around the verified mean | Simplification / declared limitation | No published normals exist for covered/basement sites; this is a declared modeling choice, not a measured figure. |
| `delta_t_charging_c` (DC-charging self-heating sensitivity) | 0 C and +5 C (sensitivity bracket) | Simplification / declared limitation | Per the approved scope: altitude affects degradation only via reduced convective cooling raising cell temperature during charging, but no validated thermal model for 50kW DC charging at 2600m was available or built. Implemented as a declared, flat sensitivity bracket, not a calibrated prediction. |
| `T_acc` (730 days), `b_cap_kwh` (78), `d_dist_km_year` (15000), `G_kwh_per_km` (0.186) | inherited from `ev2gym/models/ev.py`'s hard-coded values | Simplification / declared limitation | Describe a generic European reference vehicle's usage pattern (used only to normalize the cycling-aging denominator), unrelated to the specific simulated EV or to Colombia. Exposed as parameters (not buried literals) but not recalibrated. |
| Other categoria especial cities' ambient means | Medellin 22.53 C, Cali 24.48 C, Cartagena 27.78 C, Bucaramanga 23.01 C (elevation flagged pending verification), Barranquilla 27.0 C (Secondary source) | Mixed — see `data/ambient_profiles.yaml` per-city `source_tier` | Medellin/Cali/Cartagena/Bucaramanga's temperatures verified against the same IDEAM workbook; Bucaramanga's elevation field and Barranquilla's entire entry are flagged pending further verification rather than silently trusted. |
| Paired bootstrap: `n_bootstrap=10000`, `ci=0.95` | — | Empirically set inside this project | Standard convention for bootstrap resampling counts and confidence level; not derived from a power analysis. |

## Part 2 — Implementation

### `ev2gym_thesis/eval_protocol.py`

**Location:** new top-level package `ev2gym_thesis/`, not inside `ev2gym/` —
keeps every thesis-specific extension physically separate from the forked
upstream library, per the project's working rule of never modifying
`ev2gym/models`/`ev2gym/rl_agent` and preferring new files that import and
extend it.

**Purpose:** defines the shared evaluation protocol (which seeds, which
calendar days are for evaluation vs. RL training) as module-level constants,
so every later script — the registry backfill, the degradation
measurement, the figures — imports the exact same 50-cell grid instead of
each script inventing its own.

**Design decision:** a plain Python module of constants, not a config file
(YAML/JSON). Rejected alternative: putting `SEEDS`/`EVAL_DAYS` in a YAML
config alongside the station configs. Chosen because these are
protocol-level constants shared across every config, not per-scenario
settings — duplicating them into 5+ station YAMLs would risk drift; a
single importable module makes the "same grid everywhere" guarantee
mechanical rather than a matter of remembering to copy values.

**The disjointness assertion (module-level, not a function call somewhere
that might not run):**

`ev2gym_thesis/eval_protocol.py:66-69`

```python
assert set(EVAL_DAYS).isdisjoint(set(TRAIN_DAYS)), (
    "EVAL_DAYS and TRAIN_DAYS overlap -- an RL agent must never be "
    "evaluated on a day it could have been trained on."
)
```


This runs at *import* time, not inside a function that a caller might
forget to invoke — any script that imports `ev2gym_thesis.eval_protocol`
gets the safety check for free, which matters because the consequence of
skipping it (training an RL agent on a day it's later evaluated on) is a
silent, hard-to-detect leak, not a crash.

### `ev2gym_thesis/registry.py`

**Location:** `ev2gym_thesis/`, alongside `eval_protocol.py` — same
reasoning (thesis-specific, not upstream library code).

**Purpose:** the append-only master results registry
(`results/master_results.csv`) that every figure and table in the thesis
is meant to trace back to. Provides schema validation, deduplication, and
per-run time-series storage so no experiment result exists only as
console output.

**Design decision — append-only registry vs. per-experiment files:**
rejected alternative was one CSV per experiment run (as Week 1's
`baseline_afap.csv`/`baseline_roundrobin.csv` already were). Chosen instead:
a single growing file with a `(config_name, algorithm, seed, eval_day)`
dedup key, because Deliverable 4's figure module needs to read "the entire
history of every run so far" in one pass — scattering that across
per-experiment files would require the figure module to know the full list
of files to read, which grows every week and is exactly the kind of
bookkeeping an append-only design eliminates.

**Design decision — regenerating all figures from the registry vs.
incremental plotting:** rejected alternative was to plot each new
experiment's results as it's produced. Chosen instead: `make_figures.py`
reads the whole registry and rebuilds every figure from scratch on every
invocation, so a figure can never silently reflect a stale subset of the
data, at the cost of a few seconds of recomputation each time (cheap,
since it's plotting from already-computed CSV rows, not re-running
simulations).

**Design decision — `.npz` for time series vs. CSV:** rejected CSV because
per-step time series (station power, transformer load, connected-EV count)
are numeric arrays, and `numpy.savez` stores them as native arrays with no
parsing cost on read, vs. CSV requiring a parse-and-cast step per load;
`.npz` also bundles the three related arrays for one run into a single
file rather than three, and is not committed to git (see
`.gitignore` — regenerable from `config_name` + `seed` + `eval_day` alone,
consistent with the project's "no large binaries in git" convention).

**The schema and the validate-before-write logic that makes a renamed
column fail loudly instead of silently corrupting the registry:**

`ev2gym_thesis/registry.py:27-53`

```python
ALGORITHM_FAMILIES = {"heuristic", "mpc", "rl", "optimal"}

META_COLUMNS = [
    "run_id", "timestamp_utc", "git_commit", "config_name", "n_ports",
    "transformer_kw", "oversubscription_ratio", "algorithm",
    "algorithm_family", "seed", "eval_day", "sim_steps", "runtime_s",
    "notes",
]

# Every scalar in env.step() stats (see CLAUDE.md's confirmed stats key
# list). action_mask and voltage_violation_counter_per_step are excluded:
# both are per-port/per-step arrays, not per-run scalars.
STATS_COLUMNS = [
    "total_ev_served", "total_profits", "total_energy_charged",
    "total_energy_discharged", "average_user_satisfaction",
    "power_tracker_violation", "tracking_error", "energy_tracking_error",
    "energy_user_satisfaction", "std_energy_user_satisfaction",
    "min_energy_user_satisfaction",
    "total_steps_min_emergency_battery_capacity_violation",
    "total_transformer_overload", "battery_degradation",
    "battery_degradation_calendar", "battery_degradation_cycling",
    "total_reward", "saved_grid_energy", "voltage_violation",
    "voltage_violation_counter",
]

REGISTRY_COLUMNS = META_COLUMNS + STATS_COLUMNS
DEDUP_KEY_COLUMNS = ("config_name", "algorithm", "seed", "eval_day")
```


`ev2gym_thesis/registry.py:105-144`

```python
def append_runs(rows: list, force: bool = False) -> dict:
    """Validate and append rows to the master registry. Never overwrites.

    Returns {"appended": n, "skipped": n} so callers can report what
    actually happened rather than assuming every row was written.
    """
    for row in rows:
        missing = set(REGISTRY_COLUMNS) - set(row.keys())
        extra = set(row.keys()) - set(REGISTRY_COLUMNS)
        if missing or extra:
            raise ValueError(
                f"Row schema mismatch for run_id={row.get('run_id')!r}: "
                f"missing={missing}, unexpected={extra}. "
                f"Registry schema is REGISTRY_COLUMNS in ev2gym_thesis/registry.py "
                f"-- update both the writer and this schema together."
            )
        if row["algorithm_family"] not in ALGORITHM_FAMILIES:
            raise ValueError(
                f"algorithm_family={row['algorithm_family']!r} not in {ALGORITHM_FAMILIES}"
            )

    existing_keys = load_existing_keys() if not force else set()
    file_exists = os.path.exists(REGISTRY_PATH)

    appended, skipped = 0, 0
    os.makedirs(os.path.dirname(REGISTRY_PATH) or ".", exist_ok=True)
    with open(REGISTRY_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            key = tuple(str(row[k]) for k in DEDUP_KEY_COLUMNS)
            if key in existing_keys and not force:
                skipped += 1
                continue
            writer.writerow(row)
            existing_keys.add(key)
            appended += 1

    return {"appended": appended, "skipped": skipped}
```


**Walkthrough:** every row is checked against `REGISTRY_COLUMNS` twice —
once for missing keys, once for unexpected extras — before anything is
written, and `algorithm_family` is checked against a fixed set that
includes `"optimal"` (see the Gurobi section below) even though no row
uses it yet. Deduplication reads existing keys from disk once per call
(or is skipped entirely with `force=True`), so re-running the same backfill
command twice is safe by construction rather than by convention.

### `ev2gym_thesis/config_utils.py`

**Location:** `ev2gym_thesis/`.

**Purpose:** lets every script in the evaluation grid run a station config
on any `EVAL_DAYS`/`TRAIN_DAYS` date without editing the base YAML, by
writing a day-specific copy (`config['year'/'month'/'day']` overridden)
that `EV2Gym` reads normally.

**Design decision:** EV2Gym's `config_file` argument only accepts a file
path and reads the date once at construction — there is no API to override
the date after loading a config from disk. Rejected alternative: monkey-
patching `env.config` after construction (rejected — much of `__init__`
that depends on the date, like loading EV spawn scenarios, has already run
by the time a caller could reach in and change it). Chosen: write a real,
loadable temp YAML file per (base config, day) combination — slower (one
extra file write per run) but correct and simple, and the resulting file
is itself a valid, inspectable config (gitignored, regenerable).

### `scripts/backfill_registry.py`

**Location:** `scripts/` (an entry point, not a library module — imports
from `ev2gym_thesis/` but is not itself imported elsewhere).

**Purpose:** runs every (config, algorithm, seed, eval_day) combination in
the evaluation grid and appends each result to the registry. Backfilled
500 new rows (5 configs x 2 algorithms x 5 seeds x 10 days) plus the 2
pre-existing Week 1 single-day rows (read from their already-committed
CSVs, not re-run).

**Design decision (fixed mid-session after a real inefficiency was found):**
the dedup check must happen **before** running a simulation, not just
before writing the result. The first version of this script checked
`append_runs()`'s dedup only at write time, so resuming a paused backfill
re-simulated every already-completed row (wasted ~35 minutes reaching a
point it had already reached) before discovering the row was a duplicate
and discarding the recomputed result. Fixed by exposing
`ev2gym_thesis.registry.load_existing_keys()` and filtering the run list
against it before calling the simulation. Recorded here because it's a
concrete example of a design decision that looked fine until it met a
real resume scenario.

### `scripts/measure_degradation_by_ambient.py` and `results/degradation_by_ambient.csv`

**Location:** `scripts/` (entry point) writing to `results/` (alongside
the main registry, but as a **separate file**, not a new column on
`master_results.csv`).

**Purpose:** measures how much the Bogota-calibrated degradation model
(see `ev2gym_thesis/degradation_bogota.py` below) shifts predicted battery
degradation relative to the model's fixed 25 C default, across the
evaluation grid, with confidence intervals rather than a single run.

**Design decision — separate file vs. an `ambient_scenario` column on the
main registry (confirmed explicitly with the user, not assumed):** the
original plan called for adding a column to `master_results.csv`. Rejected
in favor of a separate, `run_id`-joinable file, by direct analogy to a
principle the user applied elsewhere this same week: the Phase 2
algorithm-comparison registry must stay a single, uniform evaluation grid
(`simulate_grid: True` rows were kept out of it for the same reason — see
`02_model_validation.md`'s grid-scope resolution). Adding an ambient-scenario
dimension to the same file used for algorithm comparison would mean every
future reader has to remember to filter by `ambient_scenario=='default'`
to get a clean algorithm comparison, or risk silently averaging across
scenario types. A separate file makes that filtering structural rather
than a convention to remember.

### `ev2gym_thesis/ambient_bogota.py` and `ev2gym_thesis/degradation_bogota.py`

**Location:** `ev2gym_thesis/` — does not modify `ev2gym/models/ev.py`.
Confirmed by inspection (see `thesis_docs/chapters/00_lab_log.md`,
2026-08-12) that `battery_degradation` does not feed into any reward
function (`ev2gym/rl_agent/reward.py`) and is not configurable via YAML,
so recomputing it post-hoc, outside the simulator, is exact — not an
approximation of what the simulator would have produced.

**Purpose:** substitutes EV2Gym's hard-coded `theta=298.15K` (confirmed by
inspection to be a literal constant, not an input) with a time-varying
ambient temperature integrated over each EV's actual charging session,
using Bogota's IDEAM-verified diurnal profile.

**Design decision — session-integrated effective Arrhenius factor vs. a
single mean-temperature evaluation:** rejected substituting the session's
mean experienced temperature into one evaluation of `exp(-E2/theta)`.
Chosen instead: average the exponential term itself over the session's
actual per-step temperatures. Reason: `exp(-E2/theta)` is convex in theta
over the relevant range, so by Jensen's inequality the mean-temperature
shortcut systematically *underestimates* the properly integrated value —
confirmed, not assumed: measured at 1.01% (95% CI [0.97%, 1.06%], n=100)
across the evaluation grid. The point-estimate version is still computed
alongside the integrated one specifically to quantify this gap, not
discarded.

**The Arrhenius factor and its 4 closed-form regression values (verified
independently before writing the corresponding unit test, not just
computed and trusted):**

`ev2gym_thesis/degradation_bogota.py:64-69`

```python
def arrhenius_factor(theta_kelvin: float) -> float:
    """exp(-E2/theta), the temperature term inside ev.py's alpha(V,theta).
    Verified against 4 closed-form reference values -- see
    tests/test_degradation_bogota.py.
    """
    return math.exp(-E2 / theta_kelvin)
```


**The session-integration logic — the actual decision this module
encodes:**

`ev2gym_thesis/degradation_bogota.py:122-161`

```python
    hours, charging_flags = _session_hours_and_charging_flags(ev, sim_starting_date, timescale_min)
    if not hours:
        return None

    avg_soc = float(np.mean(ev.historic_soc))
    v_avg = V_MIN + K * avg_soc

    T_sim_days = (ev.time_of_departure - ev.time_of_arrival + 1) * timescale_min / (60 * 24)

    exp_terms = []
    ambient_temps_c = []
    for hour, is_charging in zip(hours, charging_flags):
        ambient_c = ambient_profile_fn(hour)
        bump = delta_t_charging_c if is_charging else 0.0
        theta_t = 273.15 + ambient_c + bump
        exp_terms.append(arrhenius_factor(theta_t))
        ambient_temps_c.append(ambient_c + bump)

    A_eff = float(np.mean(exp_terms))
    alpha_eff = (E0 * v_avg - E1) * A_eff
    d_cal = alpha_eff * 0.75 * T_sim_days / (T_acc_days ** 0.25)

    # Point-estimate comparison: single evaluation at the session's mean
    # experienced temperature, to quantify the Jensen's-inequality gap.
    theta_mean = 273.15 + float(np.mean(ambient_temps_c))
    A_point = arrhenius_factor(theta_mean)
    alpha_point = (E0 * v_avg - E1) * A_point
    d_cal_point_estimate = alpha_point * 0.75 * T_sim_days / (T_acc_days ** 0.25)

    return {
        "d_cal": d_cal,
        "d_cal_point_estimate": d_cal_point_estimate,
        "jensen_gap_pct": (d_cal - d_cal_point_estimate) / d_cal * 100 if d_cal else float("nan"),
        "A_eff": A_eff,
        "A_point": A_point,
        "T_sim_days": T_sim_days,
        "v_avg": v_avg,
        "mean_ambient_c": float(np.mean(ambient_temps_c)),
        "n_session_steps": len(hours),
    }
```


**Walkthrough:** `_session_hours_and_charging_flags` (not shown, ~15 lines)
reconstructs which hour of day each of the EV's already-recorded
`historic_soc`/`active_steps` entries corresponds to, using
`sim_starting_date` and the EV's `time_of_arrival`. The loop above then
evaluates the ambient profile function once per session step, applies the
declared `delta_t_charging_c` bump only where `active_steps[i]==1`, and
takes the mean of `exp(-E2/theta(t))` across the session — a discrete
Riemann-sum approximation of the continuous integral at simulation-step
resolution. Cycling aging (`d_cyc`) is deliberately not recomputed here:
`beta()`'s formula has no temperature term (confirmed by reading
`ev2gym/models/ev.py`), so recomputing it would be redundant.

**Exposed, not recalibrated, reference-vehicle constants:**

`ev2gym_thesis/degradation_bogota.py:35-59`

```python
# These four are ev.py's hard-coded assumptions about a REFERENCE vehicle's
# annual usage pattern (15,000 km/year at 0.186 kWh/km, a 78 kWh battery,
# 2-year-old at simulation time), used only to build the normalizing
# denominator Q_acc for cycling aging -- they describe a generic European
# EV usage pattern, not the specific EV being simulated (whose own
# battery_capacity may differ, e.g. our station configs use 70 kWh).
# Exposed here as parameters (current values = ev.py's defaults) so a
# future run can vary them explicitly instead of editing buried literals.
EXPOSED_DEFAULTS = dict(
    T_acc_days=2 * 365,   # battery age assumed at simulation time (days)
    b_cap_kwh=78,         # reference vehicle battery capacity (kWh)
    d_dist_km_year=15000, # reference vehicle annual distance (km/year)
    G_kwh_per_km=0.186,   # reference vehicle energy consumption (kWh/km)
)

# Battery-chemistry coefficients from ev.py's implemented model (Xu et al.
# 2018 -type semi-empirical form -- citation pending verification, see
# thesis_docs/chapters/00_lab_log.md). These are NOT usage-pattern
# assumptions, so they are not exposed as calibration parameters here.
E0 = 7.543e6
E1 = 23.75e6
E2 = 6976
K = 0.8263
V_MIN = 3.3324
B_CAP_AH = 2.05
```


### `ev2gym_thesis/figures.py` and `scripts/make_figures.py`

**Location:** shared infrastructure (`ALGORITHM_STYLE`, caption generation)
in `ev2gym_thesis/figures.py`; the actual figure-building logic in
`scripts/make_figures.py` as an entry point.

**Purpose:** regenerates all 8 implemented figures (f01-f07, f09; f08 is
an inert stub until RL rows exist) from `results/master_results.csv` on
every invocation, with generated captions so no figure can silently
misrepresent what data actually produced it.

**Design decision — fixed color dictionary vs. automatic color cycling:**
rejected matplotlib's default color cycler (assigns colors by plot order,
which changes as algorithms are added/removed/reordered across weeks).
Chosen: a single `ALGORITHM_STYLE` dict keyed by algorithm name, appended
to (never reassigned) as new algorithms arrive in later weeks, so AFAP is
red in every figure of every week, not just the figures generated in the
same session.

`ev2gym_thesis/figures.py:17-22`

```python
ALGORITHM_STYLE = {
    "ChargeAsFastAsPossible": {"color": "#d62728", "marker": "o", "label": "AFAP"},
    "RoundRobin": {"color": "#1f77b4", "marker": "s", "label": "Round Robin"},
    # Append new algorithms here as they're added (MPC, RL, ...) -- never
    # reassign an existing entry's color/marker once a figure has used it.
}
```


**Design decision — generated captions, never hand-written:**

`ev2gym_thesis/figures.py:37-62`

```python
def write_caption(name: str, what_it_shows: str, n_runs: int, configs: list,
                   algorithms: list, extra: str = "") -> str:
    """Every figure gets a generated (never hand-written) sidecar caption
    stating what it shows, how many runs are behind it, which
    configs/algorithms are included, the git commit, and the generation
    timestamp -- so a figure can never silently go stale relative to the
    data that produced it.
    """
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = f"{FIGURES_DIR}/{name}.caption.md"
    lines = [
        f"# {name}",
        "",
        what_it_shows,
        "",
        f"- Runs behind this figure: {n_runs}",
        f"- Configs: {', '.join(configs)}",
        f"- Algorithms: {', '.join(algorithms)}",
        f"- Git commit: {get_git_commit()}",
        f"- Generated: {datetime.datetime.utcnow().isoformat()}Z",
    ]
    if extra:
        lines += ["", extra]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path
```


**Two real bugs found during visual QA of these figures (recorded because
"it ran without crashing" is not the same as "it's correct"):** the
`f05_vs_baseline` figure was initially sized too narrow for its own
y-axis tick labels — the title and axis label were literally cut off
outside the rendered canvas; and `f07_metric_heatmap`'s naive per-column
min-max color normalization colored `total_transformer_overload`
backwards, since that metric is lower-is-better but the normalization
treated "higher raw number" as "greener" for every column uniformly. Both
were caught by actually looking at the rendered PNGs, not by the script
running without an exception, and both are fixed in the current code.

### `ev2gym_thesis/stats_utils.py`

**Location:** `ev2gym_thesis/` — used by `make_figures.py` and by the
degradation measurement.

**Purpose:** the paired bootstrap and mean-with-CI functions every figure
and results table uses, verified against synthetic fixtures with
analytically known answers rather than against real experiment data.

**Design decision — paired bootstrap vs. independent-sample confidence
intervals:** rejected computing separate means and CIs for each algorithm
independently and comparing them. Chosen: resample matched `(seed,
eval_day)` pairs together, since every algorithm in this project is
evaluated on the identical scenario grid — an independent-sample CI would
throw away the fact that algorithm A and algorithm B were compared on the
literal same day-and-arrival-sequence, inflating the apparent uncertainty
in their difference.

`ev2gym_thesis/stats_utils.py:55-88`

```python
    values_a = np.asarray(values_a, dtype=float)
    values_b = np.asarray(values_b, dtype=float)
    if len(values_a) != len(values_b):
        raise ValueError("values_a and values_b must be the same length (paired)")
    n = len(values_a)
    if n == 0:
        raise ValueError("No pairs to bootstrap")

    rng = np.random.default_rng(seed)

    def _stat(a, b):
        if statistic == "diff":
            return np.mean(b - a)
        elif statistic == "pct":
            return np.mean((b - a) / a) * 100
        else:
            raise ValueError(f"Unknown statistic {statistic!r}")

    point_estimate = float(_stat(values_a, values_b))

    boot_stats = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot_stats[i] = _stat(values_a[idx], values_b[idx])

    alpha = 1 - ci
    lo, hi = np.percentile(boot_stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])

    return {
        "point_estimate": point_estimate,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_pairs": n,
    }
```


**Verification (not just "it runs"):** two tests construct a case where
`b = a + constant` for a *varying* `a` — if the pairing were broken (i.e.
if `a` and `b` were resampled independently by the code instead of by a
shared index), the resulting bootstrap distribution would show nonzero
spread, since `a` itself varies. Both tests collapse to an exact
zero-width interval at the true constant, which is only possible if the
pairing logic is correct — see `ev2gym_thesis/tests/test_stats_utils.py`.

### `data/ambient_profiles.yaml`

**Location:** new top-level `data/` directory — deliberately not
`ev2gym/data/` (that's the upstream library's own bundled datasets) and
not `ev2gym_thesis/` (this is data, not code).

**Purpose:** per-city ambient temperature figures (annual mean, daily
max/min, elevation, source citation) for Bogota plus the other categoria
especial cities, so Objective 5's replicability analysis can become a
config change later instead of a code change.

**Design decision:** data only, as instructed — no code was written this
week to actually run the multi-city comparison. Every entry carries an
explicit `source_tier` (Primary/Secondary) and, where applicable, a `note`
field flagging what's still unverified (Barranquilla has no station in the
IDEAM workbook at all; Bucaramanga's only station records an elevation
inconsistent with commonly-cited figures) — chosen over silently using a
"best guess" number, per the project's convention of never hiding an
unresolved gap.

### `scripts/run_optimal_reference.py` and `scripts/check_claims.py`

**Location:** `scripts/`, both self-contained entry points; neither is
imported by any other module in this project (verified: `run_optimal_reference.py`
performs a Gurobi license check and exits, never contributing to any
result; `check_claims.py` only reads chapter files, contributing nothing
to any script's runtime behavior).

**Purpose:** operationalize the deferred-solver policy — nothing in the
pipeline depends on Gurobi being available, but the hook to use it later
costs one command instead of a redesign under deadline pressure, and a
vocabulary check prevents describing untested strategies as "optimal"
before an actual solver-based comparison exists.

**Design decision:** `gurobipy` was removed from `requirements.txt` and
`setup.py` this week (previously listed as a hard dependency) — a
deliberate, recorded deviation from the state those files were in before
this session, since the revised Gurobi policy explicitly forbids any
module-level dependency on it.

**What was actually found when the capability check was run once:**
`gurobipy` successfully started an `Env()` in this development environment,
but reported a **"Restricted license - for non-production use only"** —
the free, size-limited default license the package ships with, not the
university's academic license `CLAUDE.md` describes. Recorded explicitly
so this isn't later misread as confirmation that the academic license has
been approved.

### `scripts/build_week_doc.py`

**Location:** `scripts/` — imported by `scripts/make_week2_handback.py`
(this document's own generator), not imported by any simulation code.

**Purpose:** the mechanism this very document is built with. Scans
`ev2gym_thesis/*.py` and `scripts/*.py` for paired begin/end comment tags
and returns the exact current file/line-range/code for each — so every
code excerpt above was re-read from the live source file at the moment
this document was generated, not pasted by hand and left to rot.

**Design decision:** raises loudly (unclosed tag, duplicate tag, mismatched
nesting) rather than silently skipping a malformed region — an example of
this catching a real mistake: an earlier draft of `ev2gym_thesis/figures.py`
had an opened-but-never-closed tag, and the very first run of this
extractor against the whole codebase failed with a clear error naming the
file and line, instead of silently omitting that snippet from a build.

## Gurobi Policy — Explicit Statement

Per the project's revised Gurobi policy (binding since this week): **no
script in this pipeline imports `gurobipy` at module level, and
`gurobipy` is absent from `requirements.txt`/`setup.py`.** The only touch
point is `scripts/run_optimal_reference.py`, a self-contained,
never-imported entry point. The registry's `algorithm_family` column
reserves the value `"optimal"` but no row uses it yet, and
`scripts/check_claims.py` enforces (mechanically, not just by convention)
that no chapter describes a tested strategy as "optimal" or "near-optimal"
until a row with that value actually exists.

## Library Choices

| Library | Used for | Why this one | Rejected alternative |
|---|---|---|---|
| `pandas`-free `csv` module (stdlib) | Registry read/write | The registry schema is simple (flat rows, no joins needed at write time); `csv.DictWriter`/`DictReader` avoid adding a pandas dependency purely for append-and-read. Analysis code (`registry_analysis.py`, figure scripts) does load rows as plain dicts rather than a DataFrame. | `pandas.DataFrame.to_csv(mode='a')` — rejected because pandas was not otherwise required for the registry's own read/write path, only for later analysis, and the stdlib csv module already handles that adequately at this data size (~500 rows). |
| `matplotlib` | All figures | Already a project dependency (ships with EV2Gym itself); no seaborn per the explicit instruction. | `seaborn` — explicitly excluded; would add a dependency and a styling layer not otherwise needed. |
| `numpy` `.npz` | Per-run time series | Native array storage, no parse cost on read, bundles related arrays in one file. See the registry.py design-decision entry above. | CSV per time series — rejected for the reasons given there. |
| `PyYAML` | All config files, `data/ambient_profiles.yaml` | Already the project's config format throughout (Week 1 configs, `station_sensitivity/`); no reason to introduce a second format for one new data file. | JSON — would have worked equally well; YAML chosen only for consistency with every other config file in the project. |
| `numpy.random.default_rng` (bootstrap) | `paired_bootstrap_ci` resampling | Modern numpy RNG API, explicit seedability for reproducible tests. | `scipy.stats.bootstrap` — rejected to avoid adding scipy as a dependency for one function, and because the paired-resampling requirement (resample shared indices, not independent samples) needed custom logic regardless of which RNG API was used underneath. |
| Gurobi | — | Deliberately absent. See the Gurobi Policy section above. | — |
| `python-docx` | `.docx` rendering of this document | Only viable pure-Python library for writing `.docx` files without a Word/LibreOffice dependency; already implied by the project's stated Word conventions (plain text, no Heading styles). | Manually authoring a `.docx` — infeasible; `pandoc` — would require a system-level binary dependency outside the Python environment. |

## References

**[Primary]**

- Enel X Colombia, public charge-point inventory: https://www.enelx.com/co/es/personas/puntos-de-recarga (consulted 2026-08-11).
- IDEAM, *Normales climatologicas estandar 1981-2010*: https://www.ideam.gov.co/sala-de-prensa/informes/Normales-clim%C3%A1ticas-est%C3%A1ndar — downloaded and read directly (`normales_climatologicas_periodo_1981-2010.xlsx`) for Bogota, Medellin, Cali, Cartagena, and Bucaramanga station data. Barranquilla: **no station found in this file** — see the Secondary entry below.
- EV2Gym source repository and its `README.md`: https://github.com/StavrosOrf/EV2Gym — read directly (`README.md:113,116`) to confirm the arrival/time-of-stay/energy-required distributions are ElaadNL-sourced and EV/charger characteristics are RVO-Survey-sourced (both Dutch).
- Colombian regulation already cited in the Week 1 bibliography: Ley 1964 de 2019, Resolucion 40223 de 2021, Resolucion 40117 de 2024 (RETIE), Resolucion 40123 de 2024.

**[Secondary]**

- Infobae (2026-04-25), "Cual es la temperatura promedio en Barranquilla," citing IDEAM: https://www.infobae.com/colombia/2026/04/25/cual-es-la-temperatura-promedio-en-barranquilla/ — used because no Barranquilla station exists in the Primary IDEAM workbook consulted this week; **pending verification against a Primary IDEAM source** if one becomes available.

**[Tertiary]** — none newly relied upon this week; the annex's tertiary list (Time and Date, Climates to Travel, Weather Spark, Climate-Data.org) was not used, since the Primary IDEAM workbook covered every city needed except Barranquilla.

**Not verified this week, flagged rather than silently cited:** Xu, B. et
al. (2018), "Modeling of Lithium-Ion Battery Degradation for Cell Life
Assessment," IEEE Transactions on Smart Grid — the implemented degradation
model's functional form (calendar aging ~ alpha(V,theta)*t^0.75, cycling
aging ~ beta(V,DoD)*Ah^0.5, an Arrhenius term in alpha) matches this
paper's known structure, but the paper's full text was not successfully
retrieved (ResearchGate and MDPI returned 403; arXiv/Chalmers PDFs
downloaded but were not machine-readable by the tooling available). Cite
as "a semi-empirical model of Xu et al. (2018) type, as implemented by
EV2Gym" — not as a verified citation — until the 7 model coefficients are
checked line-by-line against the primary source.
