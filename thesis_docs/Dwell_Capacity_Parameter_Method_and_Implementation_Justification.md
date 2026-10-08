# Final Capacity Brief — Parameter, Method, and Implementation Justification: DC Session Duration and Growth Scenario

**Status: complete (2026-10-07). Run unattended on branch `semana-7`;
nothing committed.**

This document follows the Week 5–7 and closure mechanism. It is a Markdown
record rendered to `.docx` by `scripts/render_docx.py`. The decision log,
with the Bogotá time of each checkpoint, is the dwell section at the top of
`thesis_docs/overnight_report.md`. The baseline was HEAD `942122a` with a
clean working tree (`thesis_docs/dwell_baseline_status.txt`).

## Headline Results Summary

**1. EV2Gym's session durations are not DC sessions (the Checkpoint A rule
fired).**
- The simulated mean connection is **300.6 min [296.5, 304.7]**. No session
  is shorter than 225 min.
- The reference is 42 min for paid DC charging (U.S. DOE, 2023), and the
  rule's ceiling is 90 min.
- The 42-minute DC model therefore became primary. The closure results are
  a declared sensitivity.

**2. The closure's 34.6% demand not served was largely a session-duration
artefact.** At the same spawn multiplier, DC sessions give:
- rejected arrivals of 0.9/day instead of 8.9;
- port occupancy of 14% instead of 35%;
- demand not served of 2.4% (AFAP) and 5.0% (transformer-aware Round Robin).

**3. EV2Gym's Round Robin follows a median-smoothed power setpoint, not the
transformer.**
- Its zero overload in Weeks 1–7 came from long stays.
- Under 42-minute sessions it fails every criterion at every demand tested:
  at 1.0×, DNS is 24.8% and 65/100 runs overload.
- AFAP and the final RL model (out of its training distribution) also
  exceed 100 kW from the lowest level.
- **The binding constraint is power, not ports.**

**4. Threshold with a transformer-aware round-robin load manager**
(added as a diagnostic in this brief; promoted to the recommended strategy, 2026-10-07):
- **8 ports and the 100 kW (112.5 kVA) unit serve up to 47 arrivals/day
  (763 kWh/day) with DNS ≤ 15%** (9.0%, CI high 10.2%; n_clusters = 50).
- The threshold is the same at 32 min and falls to 35 arrivals/day at
  78 min.

**5. Growth scenario (42 min).**

| Level | Round Robin (EV2Gym) | Transformer-aware Round Robin | AFAP |
|---|---|---|---|
| 1.3× (47 arrivals/day) | none | 8 ports, 100 kW | 8 ports, 300 kVA |
| 1.6× (57 arrivals/day) | 14 ports, 400 kVA | **10 ports, 100 kW** | 10 ports, 300 kVA |

**6. Final compliance (DC 42 min, 8 ports, 100 kW).**
- Only the transformer-aware Round Robin meets every evaluable target at 1.0× and
  1.3×.
- At 1.6× no arm meets the satisfaction target counting rejected arrivals.
- Voltage is not evaluable under DC sessions.

## Part 1 — Parameters and Methods

| Parameter | Value | Label | Justification | Citation |
|---|---|---|---|---|
| Central DC session duration | **42 min** (lognormal mean) | external reference, not Colombian | Enel's service is paid (pay per kWh), so paid sessions are the analogue. It is a measured mean over 1,412,050 sessions. It lies between Enel's 50% (25–30 min) and full-charge (just over 1 h) times. | U.S. DOE (2023); Blu Radio (2026) |
| Low bracket | **32 min** | external reference, not Colombian | Self-reported recall of the last session (survey, 3,350 households), so it is the low bound, not the centre | Hardman (2026) |
| High bracket | **78 min** | external reference, not Colombian | Mean of free US DC sessions (957,265). Without a price there is no incentive to leave, so it bounds the result from above | U.S. DOE (2023) |
| Coefficient of variation | **0.5** | labelled assumption | Survey per-activity SDs: 15.56 / 15.06 / 19.00 min on means of 29.65 / 30.70 / 38.39, a CV of 0.49–0.52 | Hardman (2026), Suppl. Table 3 |
| Checkpoint A rule | **90 min** | brief's rule; plausibility ceiling | The slowest Enel figure (about 1 h 30 min to 100%, earlier equipment). It describes a full charge, not a typical session. The page could not be saved | Enel Colombia (2024) |
| Rounding | nearest 15-min step, floor 1 step | simulator constraint | ±7.5 min resolution; 13% of 42-min sessions are one step | `dc_sessions.py` |
| Energy per session | not rescaled (16.1 kWh simulated) | declared limitation | 27% below the 22.0 kWh paid-DC reference. It comes from the Dutch per-arrival demand table, not from the battery | U.S. DOE (2023) |
| Breaking criteria | satisfaction counting rejected arrivals CI low ≥ 90%; DNS CI high ≤ 15%; P95 peak CI high ≤ rating (kW) | brief; hardest CI side (conservative) | The same as the closure run; the peak is judged against the candidate's own rating in C2 | `analyze_dwell_capacity.py` |
| Transformer ratings | 100 kW reference; 150 / 225 / 300 / 400 kVA at pf 0.894 | standard classes | Enel ET-013 Table 1; pf from CREG 015/2018 (closure run) | `SOURCES_closure.md` |
| Port variants | 8–16 at constant station demand (spawn × 8/P) | closure convention | EV2Gym draws arrivals per port | closure run |
| Round Robin, transformer-aware (added as a diagnostic; recommended from 2026-10-07) | Round Robin, budget 0.999 × rating | labelled judgement call | Separates round-robin load management from EV2Gym's setpoint coupling | `ev2gym_thesis/heuristics.py` |

**The 42-minute justification (as written in chapter 06, S6.6.2).**
1. **Payment model.** Enel's public charging in Bogotá is paid: users
   activate the charge and pay only for the energy consumed (Blu Radio,
   2026). Paid DC sessions are therefore the behavioural analogue. Free
   sessions last almost twice as long, 78 against 42 minutes (U.S. DOE,
   2023), because without a price users have no incentive to leave.
2. **Strength of the evidence.** The 42-minute figure is the mean of
   1,412,050 measured paid DC sessions (U.S. DOE, 2023). The 32-minute
   California figure is self-reported recall (Hardman, 2026), so it is the
   low bound.
3. **Consistency with Enel's own figures.** Unicentro reaches about 50% in
   25–30 minutes and a full charge in a little over an hour (Blu Radio,
   2026). A 42-minute mean lies between the two, consistent with users
   stopping before 100%. The older 1 h 30 min figure (Enel Colombia, 2024)
   is a full charge on earlier equipment, so it is used only as the rule's
   ceiling.
4. **Sensitivity bracket.** The transformer-aware Round Robin's threshold is the same
   at 32 and 42 min (holds at 1.3×) and moves down one level at 78 min
   (holds at 1.0×): about 49 / 47 / 35 arrivals per day. EV2Gym's Round
   Robin meets the criteria at no level under any duration.
5. **Declared limitation.** No Colombian per-session statistics are
   published. The value comes from the US fleet and charger mix. It
   replaces Dutch AC times that are inconsistent with DC charging, but it
   is not Colombian data (chapter 08).

**Final target compliance** (DC 42 min, 8 ports, 100 kW;
`results/dwell_e_target_compliance.csv`; n_clusters = 50). Satisfaction and
DNS are judged on the hardest CI side.

| Level | Arm | Satisfaction, served | Satisfaction, counting rejected | ENS_rel, served | DNS < 15% | Transformer | Voltage ±5% |
|---|---|---|---|---|---|---|---|
| 1.0× | AFAP | met | met (97.9%) | met (0.0%) | met (2.4%) | **not met** (97/100) | not evaluable |
| 1.0× | Round Robin (EV2Gym) | met | met (93.0%) | **not met** (22.9%) | **not met** (24.8%) | **not met** (65/100) | not evaluable |
| 1.0× | Final RL (out of distribution) | met | met (92.2%) | **not met** (26.3%) | **not met** (28.1%) | **not met** (81/100) | not evaluable |
| 1.0× | Round Robin, transformer-aware | met | met (97.3%) | met (2.7%) | met (5.0%) | met (0/100) | not evaluable |
| 1.3× | AFAP | met | met (94.7%) | met | met (5.5%) | **not met** (100/100) | not evaluable |
| 1.3× | Round Robin (EV2Gym) | met | **not met** (90.6%, CI low 89.6%) | **not met** (19.0%) | **not met** (23.6%) | **not met** (83/100) | not evaluable |
| 1.3× | Final RL | met | **not met** (89.4%) | **not met** (24.8%) | **not met** (29.0%) | **not met** (95/100) | not evaluable |
| 1.3× | Round Robin, transformer-aware | met | met (93.9%) | met (3.7%) | met (9.0%) | met (0/100) | not evaluable |
| 1.6× | AFAP | met | **not met** (89.5%) | met | met (10.5%) | **not met** (100/100) | not evaluable |
| 1.6× | Round Robin (EV2Gym) | met | **not met** (86.1%) | **not met** (16.6%) | **not met** (25.3%) | **not met** (96/100) | not evaluable |
| 1.6× | Final RL | met | **not met** (84.9%) | **not met** (22.5%) | **not met** (30.6%) | **not met** (98/100) | not evaluable |
| 1.6× | Round Robin, transformer-aware | met | **not met** (88.6%) | met (4.2%) | **not met** (14.2%, CI high 15.7%) | met (0/100) | not evaluable |

The voltage reason applies to every row: the arms were not rerun on a
feeder under DC sessions. The 34-node feeder is out of band when idle, and
the node_123 result (closure) used Dutch durations.

## Part 2 — Implementation

### `ev2gym_thesis/demand/dc_sessions.py` (new)

The DC session-duration transform, applied from outside the library. No file
in `ev2gym/` was edited.

**The hook.** EV2Gym has no session-duration key, and no hook between "the
population is generated" and "the episode runs" other than the spawner
itself. Rewriting departures after `EV_spawner` returns would keep the port
occupancy that decided which arrivals exist: an arrival blocked behind a
6-hour Dutch session would stay blocked behind a 42-minute one. The
transform therefore works inside the spawner's own loop:
1. It wraps `loaders.EV_spawner`, the name that `load_ev_profiles` calls.
2. **Pass 1** runs the library spawner unchanged. This is the
   Dutch-duration population every registry row used.
3. It restores the RNG state, then runs **pass 2**: the library spawner
   again, with `utils.spawn_single_EV` temporarily replaced by a function
   that:
   - for an arrival pass 1 also produced (same station, port and step),
     returns pass 1's EV object itself, with only `time_of_departure`
     rewritten. Arrival time, battery at arrival and desired capacity are
     bitwise unchanged;
   - for an arrival that exists only because a port is now free, calls the
     library's own `spawn_single_EV` under an RNG keyed on (scenario,
     station, port, step). The energy requested is then the same in every
     duration variant;
   - draws the connection duration from a lognormal with the target mean
     and CV 0.5, using z ~ N(0,1) keyed the same way. The same z is used in
     every variant, so the 32/42/78-minute populations are comonotone;
   - rounds the duration to the 15-minute step, half up, with a floor of 1
     step, and applies the library's own horizon rule.
4. It sets the global RNG to its state after pass 1. Everything EV2Gym draws
   after the spawner is therefore unchanged.

**Setpoint guard.** `utils.generate_power_setpoints` spreads each EV's
energy over [arrival + 1, departure), which is empty for a 1-step session,
so `min()` raises. For that computation only, a 1-step session is treated
as 2 steps and then restored. This affects the tracking target and EV2Gym's
Round Robin (which follows the setpoint) for 1-step sessions: 13% at 42 min,
29% at 32 min, 1% at 78 min. It is declared in chapter 08.

**Parameters.** They live in a sidecar `<config>.dwell.json`, never in a new
YAML key: EV2Gym does not consume one (CLAUDE.md config rule).

### `ev2gym_thesis/demand/censoring.py` (extended)

The rejected-arrival replay now wraps whatever spawner is installed before
`enable()`. When the DC transform is on, the replay re-walks the transformed
population. Without it, behaviour is unchanged (the existing closure tests
still pin this).

### `ev2gym_thesis/heuristics.py` (new)

`RoundRobinTransformerCapped` is a diagnostic arm. It keeps EV2Gym's Round
Robin allocation unchanged (same buffer, rotation and per-port action) and
replaces only the power budget: 0.999 × the transformer's rated power,
instead of the power setpoint. The setpoint itself is restored after each
call, so the tracking target is unchanged. It was added after the first C1
results showed that EV2Gym's Round Robin follows a median-smoothed setpoint
and never reads the transformer limit.

### `scripts/dwell_session_stats.py` (new)

Part A and the realised-mean check of Part B. It builds the population
exactly as evaluation runs do (`make_env` + `reset_for_evaluation`, with the
censoring replay on), for 50 seeds × 2 days per session model. Outputs:
- `results/dwell_sessions_ev_level.csv`;
- `results/dwell_sessions_by_cell.csv`;
- `results/dwell_a_session_summary.csv`;
- `results/dwell_a_reference_comparison.csv`.

### `scripts/run_dwell_capacity.py`, `scripts/run_dwell_worker.cmd` (new)

**Configs.** Each is the non-grid reference YAML with only three lines
changed: `spawn_multiplier`, `number_of_charging_stations` and
`transformer.max_power`. Each has its `.dwell.json` sidecar. They are
written once by `--prepare`:
- `experiments/phase3_infra_replicability/configs/dwell/`, 81 configs;
- run plans in `.../dwell/plans/dwell_main.json` and `dwell_diag.json`.

**Row builders.** The same real ones as before:
- `backfill_registry.run_single` for the heuristics;
- `run_week7_grid.run_cell` for the final RL model, with its notes
  carrying `out_of_training_distribution=dc_session_durations`.

**Workers and outputs.**
- Workers are detached and resumable, with 2 processes at most (the laptop
  limit). Each writes a row shard and a censoring shard.
- `--merge` writes `results/dwell_registry.csv` (the master registry
  schema, 23,200 rows) and `results/dwell_censoring_by_cell.csv`.
- **`results/master_results.csv` is never opened for writing** (a labelled
  choice: the DC model is a different population model, and a separate file
  removes any risk to existing rows and existing pins).

### `scripts/analyze_dwell_capacity.py` (new)

Post-processing only. It computes:
- per-run DNS (lower and upper bounds), satisfaction counting rejected
  arrivals, peak power from the saved time series, and margin at Bogotá
  prices;
- the breaking criteria on the hardest CI side;
- the C1 thresholds per arm and session model;
- the C2 feasibility grid and its Pareto-minimal configurations;
- the Part D physical units;
- the E3 compliance table.

### `scripts/export_dwell_results_xlsx.py` (new), `scripts/make_figures.py` (extended), `ev2gym_thesis/figures.py` (style appended)

- Every dwell table has an `.xlsx` twin produced through
  `export_formatted_xlsx`.
- Figures f22–f24 were added (`--only f22,f23,f24`).
- The transformer-aware Round Robin's style was appended without reassigning any existing
  colour.

### `scripts/extend_progress_log.py` (extended)

A new `--section dwell` appends section 16. Nothing already in the file is
modified.

### Tests: `ev2gym_thesis/tests/test_dwell.py` (new)

Each test calls the production functions:
- **Arrivals and energy (B.2 test 1).** The arrival draw matrix is
  identical. Every shared arrival keeps its arrival time, battery at
  arrival and desired capacity bitwise. Pass 1 equals the library
  population. Energy is identical across the 32/42/78 variants.
- **Realised mean (B.2 test 2).** It is within 5% of the target over the
  100 cells, built by the production statistics script.
- **Transform disabled (B.2 test 3).** AFAP, Round Robin and the final RL
  model reproduce existing registry rows exactly.
- **Further checks.** The setpoint guard, the config/sidecar contract, the
  Part A pin, the dwell-registry schema and grid completeness, and that the
  master registry carries no dwell rows.

## References (APA 7)
- Blu Radio. (2026, May 13). *Conductores en Bogotá podrán cargar hasta el 50 % de batería de su carro eléctrico en menos tiempo* (C. Durán, Author). https://www.bluradio.com/motor/conductores-en-boogta-podran-cargar-hasta-el-50-de-bateria-de-su-carro-electrico-en-menos-tiempo-so35
- Enel Colombia. (2024, May). *Avances en infraestructura de recarga de vehículos eléctricos.* https://www.enel.com.co/es/historias/archive/2024/05/infraestructura-de-recarga-de-vehiculos-electricos.html
- Hardman, S. (2026). Exploring electric vehicle driver activities and expenditure while using DC fast chargers. *Findings.* https://doi.org/10.32866/001c.162484
- U.S. Department of Energy, Vehicle Technologies Office. (2023, December 4). *FOTW #1319: EV charging at paid DC fast charging stations average 42 minutes per session* [Fact of the Week]. https://www.energy.gov/cmei/vehicles/articles/fotw-1319-december-4-2023-ev-charging-paid-dc-fast-charging-stations-average
