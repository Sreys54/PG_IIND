# Chapter 1 — Baseline Characterization (Objective 1)

## 1.1 Representative Station Definition

The Week 1 baseline models a small public charging station representative
of a neighborhood-scale installation in Bogota, rather than the large
synthetic multi-station grid scenario shipped as EV2Gym's `V2Ggrid.yaml`
example. The station is configured as 8 charging points (one port each),
served by a single 100 kW local transformer, with AC charging up to 50 kW
per port (72 A at 400 V, 3-phase) and no vehicle-to-grid (V2G) discharge.
This is an explicit modeling assumption, not a measured or surveyed value
from a real Bogota installation: it represents a plausible small/medium
public charging hub (e.g., a shopping center or municipal parking lot)
rather than any specific site. It should be revisited if a real reference
station (capacity, connector count, transformer sizing) becomes available
later in the project. The EV arrival intensity (`spawn_multiplier: 30`) was
tuned so that this 8-station scenario produces a plausible daily EV count
(order of 10-15 vehicles/day) rather than the 90+ vehicles/day produced by
the unedited, 150-station configuration — see
`thesis_docs/chapters/00_lab_log.md` for the diagnosis that led to this fix.

Grid-level constraints (voltage band, distribution feeder topology) are
deliberately **not** modeled in this baseline (`simulate_grid: False`): the
station is treated as sitting behind its own transformer, independent of
any upstream feeder. Grid-level validation against a synthetic distribution
network is the subject of Week 2 (Objective 2), not this baseline.

## 1.2 Simulation Setup

- Config: `experiments/phase1_baseline/configs/station_v0_bogota.yaml`
- Script: `experiments/phase1_baseline/run_baseline.py`
- Horizon: 96 steps at 15-minute resolution (one full day)
- Date: fixed at 2022-01-17 (`random_day: False`) — an explicit assumption
  for deterministic, reproducible Week 1 results; see the lab log for the
  discussion of why `random_day: True` (the value inherited from
  `V2Ggrid.yaml`) is incompatible with reproducibility.
- EV-arrival sampling seed: 42 (fixed in `run_baseline.py`, applied
  identically to both algorithms below so they are compared on the same set
  of arriving EVs)
- Algorithms compared: `ChargeAsFastAsPossible` (AFAP, "unmanaged charging")
  and `RoundRobin` (a simple managed heuristic that tracks a power
  setpoint)

## 1.3 Results

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 14 | 14 |
| total_profits | -56.92 | -49.74 |
| total_energy_charged (kWh) | 240.93 | 240.81 |
| average_user_satisfaction | 1.0 | 1.0 |
| total_transformer_overload (kWh) | 0.132 | 0.0 |

Both algorithms serve the same 14 EVs at 100% user satisfaction, since the
station has enough capacity relative to the (deliberately modest) arrival
rate to fully charge every vehicle that connects. The distinguishing result
is transformer loading: AFAP, which charges every connected EV at maximum
power regardless of the transformer's rated capacity, produces a small
transformer overload (0.132 kWh over the day). Round Robin, which
distributes available power across connected EVs to track a power setpoint,
eliminates this overload entirely (0.0 kWh). This is the expected
qualitative relationship between an unmanaged and a managed charging
strategy, and is the headline finding of the Week 1 baseline: **unmanaged
charging at this station size creates a (small) grid violation that a
simple heuristic already resolves.**

## 1.4 Known Limitations of This Baseline

- The 8-station, 100 kW, spawn_multiplier-30 sizing is an assumption (see
  §1.1), not a measured real-world station.
- The transformer overload magnitude (0.132 kWh) is small in absolute terms
  given the station's modest size; a larger or more aggressively-loaded
  station would likely show a more pronounced AFAP-vs-RR gap. This should be
  explored via the load-multiplier sweep planned for Week 6.
- Grid voltage constraints are not modeled here (`simulate_grid: False`);
  RETIE's ±5% voltage band cannot be checked against this baseline and will
  require the Week 2 grid-enabled scenario instead.
- Results are for a single fixed day and a single random seed; they should
  not be read as an average-case estimate. A multi-seed/multi-scenario sweep
  is planned for later phases (see `PROJECT_ROADMAP.md`, Week 4-5 comparison
  methodology).
