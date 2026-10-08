# Final — Parameter, Method, and Implementation Justification: Recommended Strategy, Bounds, Voltage and Tariffs Under DC Sessions

**Status: complete (2026-10-07). Run unattended on branch `semana-7`;
nothing committed. This is the last experimental run; the practical part of
the thesis is closed.**

This document follows the usual mechanism. It is a Markdown record rendered
to `.docx` by `scripts/render_docx.py`. The decision log is the last-run
section at the top of `thesis_docs/overnight_report.md`. The baseline was
HEAD `dad3f3e` with a clean tree (`thesis_docs/final_baseline_status.txt`).
Unless stated otherwise, everything uses 42-minute DC sessions (an external,
non-Colombian reference), 8 ports and one 100 kW (112.5 kVA) transformer,
50 seeds × 2 days, and n_clusters = 50.

## Headline Results Summary

**Objective 4 — infrastructure guidelines (final answer).**
1. **Operate the station with a transformer-aware Round Robin**: round-robin
   load management whose power budget is the transformer rating.
   - It keeps every run within 100 kW.
   - It serves 95.0% of requested energy at the reference demand (AFAP:
     97.6%, but it overloads in 97/100 runs).
   - It costs 10,141 COP/day [7,816, 12,623] of margin in Bogotá (2.8%).
   - EV2Gym's own `RoundRobin` is not this strategy: it follows a
     median-smoothed setpoint and never reads the transformer limit.
2. **Size it in physical units.** The 8-port, 100 kW station meets every
   criterion up to **47 offered arrivals/day (763 kWh/day)**. At **57
   arrivals/day (911 kWh/day) it needs 10 ports** on the same unit.
3. **Voltage.** On EV2Gym's node_123 test feeder, AFAP and the
   transformer-aware Round Robin stay within ±5% at 1.0–1.6× (0/50 cells
   out of band; lowest bus 0.9733 p.u.; weekday only).
4. **The non-causal MPC and oracle are not upper bounds on service under
   DC sessions.** They track the same median-smoothed setpoint and leave
   48.5% / 39.9% of demand unserved at 1.0×. MPC is infeasible in 37.7% of
   its steps.

**Objective 5 — replicability (final answer).**
- The guideline transfers through two inputs:
  - the station's own arrivals per day;
  - the operator's Nivel 2 tariff.
- Under a flat tariff the ranking is tariff-invariant (Proposition 7.1).
- Under DC load profiles, Air-e's 10.03% two-band option no longer changes
  the cost of the limit materially (9,230 COP/day two-band against 9,619
  flat), and the cost is about 2.8% of margin in all six categoría especial
  cities.
- No city's demand is mapped onto the axis, because no per-station demand
  source exists.

## Part 1 — Parameters and Methods

| Parameter / method | Value | Label | Justification | Source |
|---|---|---|---|---|
| Recommended arm | Round Robin, transformer-aware (`RoundRobinTransformerCapped`) | promoted from diagnostic | The thesis's recommendation (round-robin sharing of the rating) implemented with the rating as the budget. It is causal and needs no forecast | 06 S6.7.1 |
| Budget fraction | 0.999 × rating | labelled | 0.1% margin so float rounding cannot register as overload | `ev2gym_thesis/heuristics.py` |
| Session model | lognormal, mean 42 min, CV 0.5 (bracket 32 / 78) | external reference, not Colombian | Final capacity brief | U.S. DOE (2023); Hardman (2026) |
| Bounds | MPC_TrackingG2V, Optimal_Oracle_Tracking at 1.0/1.3/1.6× | upper bounds on setpoint tracking, non-causal | Both know departure times. The 4-hour timing rule did not fire, so all 50 seeds were used | `tracking_mpc.py`; `tracking_error.py` |
| Voltage protocol | node_123, bus 115, weekday, 50 seeds, idle matched per level | closure E2, unchanged | The only shipped feeder in band when idle | `scripts/dwell_ieee123_voltage.py` |
| Two-band tariffs | closure D2 tariffs, 15-min DC profiles, 1.0× | post-processing | `city_tables` reused unchanged | `scripts/dwell_multicity_dc.py` |
| Criteria | satisfaction counting rejected (CI low ≥ 90%); DNS (CI high ≤ 15%); zero overload in every run; ±5% band in every cell | hardest CI side | As in the closure and dwell runs | `analyze_last_run.py` |

**Final target compliance (DC 42 min, 8 ports, 100 kW; n_clusters = 50).**

| Level | Arm | Satisfaction > 90%, served | Satisfaction > 90%, counting rejected | ENS_rel < 15% | DNS < 15% | Transformer within rating | Voltage ±5% |
|---|---|---|---|---|---|---|---|
| 1× | AFAP | met (CI low 99.8%) | met (97.9%, CI low 97.2%) | met (0.0%) | met (2.4%, CI high 3.2%) | **not met** (97/100 runs overload) | met on node_123 (0/50 cells out of band) |
| 1× | Round Robin (EV2Gym, setpoint) | met (CI low 94.4%) | met (93.0%, CI low 92.2%) | **not met** (22.9%) | **not met** (24.8%, CI high 26.8%) | **not met** (65/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1× | **Round Robin, transformer-aware (recommended)** | met (CI low 99.1%) | met (97.3%, CI low 96.5%) | met (2.7%) | met (5.0%, CI high 6.1%) | met (0/100 runs overload) | met on node_123 (0/50 cells out of band) |
| 1× | MPC_TrackingG2V (upper bound, non-causal) | **not met** (CI low 87.7%) | **not met** (87.2%, CI low 85.8%) | **not met** (47.3%) | **not met** (48.5%, CI high 53.1%) | **not met** (7/100 runs overload, solver tolerance ≤ 0.0001 kWh/day) | not evaluated (not rerun on node_123 under DC) |
| 1× | Optimal_Oracle_Tracking (upper bound, non-causal) | met (CI low 90.8%) | **not met** (89.5%, CI low 88.7%) | **not met** (38.4%) | **not met** (39.9%, CI high 41.9%) | met (0/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1× | Final RL model (out of distribution) | met (CI low 93.7%) | met (92.2%, CI low 91.5%) | **not met** (26.3%) | **not met** (28.1%, CI high 29.6%) | **not met** (81/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1.3× | AFAP | met (CI low 99.8%) | met (94.7%, CI low 93.7%) | met (0.0%) | met (5.5%, CI high 6.5%) | **not met** (100/100 runs overload) | met on node_123 (0/50 cells out of band) |
| 1.3× | Round Robin (EV2Gym, setpoint) | met (CI low 95.1%) | **not met** (90.6%, CI low 89.6%) | **not met** (19.0%) | **not met** (23.5%, CI high 25.2%) | **not met** (83/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1.3× | **Round Robin, transformer-aware (recommended)** | met (CI low 98.9%) | met (93.9%, CI low 92.8%) | met (3.7%) | met (9.0%, CI high 10.2%) | met (0/100 runs overload) | met on node_123 (0/50 cells out of band) |
| 1.3× | MPC_TrackingG2V (upper bound, non-causal) | **not met** (CI low 86.7%) | **not met** (83.3%, CI low 81.9%) | **not met** (51.7%) | **not met** (54.4%, CI high 58.7%) | **not met** (7/100 runs overload, solver tolerance ≤ 0.0001 kWh/day) | not evaluated (not rerun on node_123 under DC) |
| 1.3× | Optimal_Oracle_Tracking (upper bound, non-causal) | met (CI low 91.3%) | **not met** (87.0%, CI low 86.1%) | **not met** (35.6%) | **not met** (39.2%, CI high 40.8%) | met (0/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1.3× | Final RL model (out of distribution) | met (CI low 94.0%) | **not met** (89.4%, CI low 88.4%) | **not met** (24.8%) | **not met** (29.0%, CI high 30.4%) | **not met** (95/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1.6× | AFAP | met (CI low 99.8%) | **not met** (89.5%, CI low 88.0%) | met (0.0%) | met (10.5%, CI high 11.8%) | **not met** (100/100 runs overload) | met on node_123 (0/50 cells out of band) |
| 1.6× | Round Robin (EV2Gym, setpoint) | met (CI low 95.8%) | **not met** (86.1%, CI low 84.8%) | **not met** (16.6%) | **not met** (25.3%, CI high 26.9%) | **not met** (96/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1.6× | **Round Robin, transformer-aware (recommended)** | met (CI low 98.8%) | **not met** (88.6%, CI low 87.2%) | met (4.2%) | **not met** (14.2%, CI high 15.7%) | met (0/100 runs overload) | met on node_123 (0/50 cells out of band) |
| 1.6× | MPC_TrackingG2V (upper bound, non-causal) | **not met** (CI low 85.8%) | **not met** (77.8%, CI low 76.2%) | **not met** (56.0%) | **not met** (60.6%, CI high 64.6%) | **not met** (11/100 runs overload, solver tolerance ≤ 0.0001 kWh/day) | not evaluated (not rerun on node_123 under DC) |
| 1.6× | Optimal_Oracle_Tracking (upper bound, non-causal) | met (CI low 91.7%) | **not met** (82.5%, CI low 81.2%) | **not met** (34.4%) | **not met** (41.3%, CI high 42.8%) | met (0/100 runs overload) | not evaluated (not rerun on node_123 under DC) |
| 1.6× | Final RL model (out of distribution) | met (CI low 94.5%) | **not met** (84.9%, CI low 83.5%) | **not met** (22.5%) | **not met** (30.6%, CI high 32.1%) | **not met** (98/100 runs overload) | not evaluated (not rerun on node_123 under DC) |

The paired comparisons, the voltage table and the tariff table are in
chapters 06 (S6.7.2–S6.7.3) and 07 (S7.11).

## Part 2 — Implementation

### `ev2gym_thesis/heuristics.py`, `ev2gym_thesis/figures.py` (relabelled)

The display name is now "Round Robin, transformer-aware", and the docstring
states its promotion. The class name is unchanged, so every registry row
stays valid.

### `scripts/run_dwell_capacity.py` (extended), `scripts/run_last_worker.cmd` (new)

The bound arms go through `run_week7_grid.run_cell` with the DC transform
enabled (MPC through `evaluate_mpc`, the oracle through
`evaluate_oracle`, with a per-process replay directory). Their notes carry
`upper_bound_noncausal=knows_departure_times,tracks_ev2gym_power_setpoint=True`.
- Plan: `configs/dwell/plans/dwell_bounds.json`.
- Output: 600 rows appended to `results/dwell_registry.csv`, which now has
  23,800 rows.

### `scripts/dwell_ieee123_voltage.py` (new)

This is the closure E2 protocol, reused through the closure script's own
functions and constants. The configs are the closure's `grid123_sp*` YAMLs
plus a DC sidecar. The transformer-aware arm runs through the heuristic row
builder, with the Week 7 voltage capture. There are 450 runs.

### `scripts/dwell_multicity_dc.py` (new)

The closure's `attach_bands` and `city_tables` are reused unchanged on the
DC rows at 1.0×. The transformer-aware arm is passed in the "RoundRobin"
pairing slot, which is documented.

### `scripts/analyze_last_run.py` (new)

It produces:
- the bounds against the transformer-aware Round Robin, with paired
  cluster-bootstrap differences and MPC's infeasible-step count;
- the node_123 voltage table, with a no-feedback check (station energy
  equals the non-grid DC rows);
- the 6-arm × 3-level final compliance table.

### `scripts/make_figures.py` (extended)

- New figures: f19_capacity_threshold_dc, f20_port_options_dc and
  f25_voltage_dc.
- The Dutch-duration f19 and f20 are kept and relabelled "SENSITIVITY".
- Visual QA found and fixed three issues:
  - f19dc picked its legend handle by position, so it duplicated RL and
    dropped the 100 kW line;
  - the f25 axis label was clipped;
  - the f20dc legend overlapped a marker.

### `scripts/export_dwell_results_xlsx.py` (run), `scripts/extend_progress_log.py` (`--section last`)

- Every new table has an `.xlsx` twin produced through
  `export_formatted_xlsx`.
- Progress Log section 17 was appended; nothing earlier was modified.

### Tests: `ev2gym_thesis/tests/test_dwell.py` (extended)

`TestTransformerAwareBudget` steps the recommended arm for 10 seeds × 2 days
at 1.6× and asserts, at every step, that the aggregate transformer power
and the station power are ≤ 0.999 × rating. It also asserts that the budget
actually binds (maximum ratio > 0.9), so the pass is not vacuous.

## References (APA 7)

- Blu Radio. (2026, May 13). *Conductores en Bogotá podrán cargar hasta el 50 % de batería de su carro eléctrico en menos tiempo* (C. Durán, Author). https://www.bluradio.com/motor/conductores-en-boogta-podran-cargar-hasta-el-50-de-bateria-de-su-carro-electrico-en-menos-tiempo-so35
- Enel Colombia. (2024, May). *Avances en infraestructura de recarga de vehículos eléctricos.* https://www.enel.com.co/es/historias/archive/2024/05/infraestructura-de-recarga-de-vehiculos-electricos.html
- Hardman, S. (2026). Exploring electric vehicle driver activities and expenditure while using DC fast chargers. *Findings.* https://doi.org/10.32866/001c.162484
- U.S. Department of Energy, Vehicle Technologies Office. (2023, December 4). *FOTW #1319: EV charging at paid DC fast charging stations average 42 minutes per session* [Fact of the Week]. https://www.energy.gov/cmei/vehicles/articles/fotw-1319-december-4-2023-ev-charging-paid-dc-fast-charging-stations-average
