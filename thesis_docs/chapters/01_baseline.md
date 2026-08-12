# Chapter 1 — Baseline Characterization (Objective 1)

## 1.1 Representative Station Definition

The Week 1 baseline models a small public charging station representative
of a neighborhood-scale installation in Bogota, rather than the large
synthetic multi-station grid scenario shipped as EV2Gym's `V2Ggrid.yaml`
example. The station is configured as 8 charging points (one port each),
served by a single 100 kW local transformer, with AC charging up to 50 kW
per port (72 A at 400 V, 3-phase) and no vehicle-to-grid (V2G) discharge.

**`number_of_charging_stations = 8` is grounded in observed data, not a
blind guess.** Enel X Colombia's published public charge-point inventory for
Bogota (consulted 2026-08-11 at
https://www.enelx.com/co/es/personas/puntos-de-recarga) lists 67 public
chargers across 21 sites. Port counts per site are bimodal: a median of 2
ports (small AC destination-charging points), plus a handful of larger
hubs — Unicentro 2 (16 ports), Salitre (10 ports: 8x Type 2 AC 43 kW + 2x DC
150 kW), CC Retiro (8 ports), and Unicentro 1 (3 ports). Our
`number_of_charging_stations = 8` therefore corresponds to an observed
mid-size hub in this inventory (matching CC Retiro's port count), rather
than an arbitrary value picked without reference to any real network. The
EV arrival intensity (`spawn_multiplier: 30`) was tuned so that this
8-station scenario produces a plausible daily EV count (order of 10-15
vehicles/day) rather than the 90+ vehicles/day produced by the unedited,
150-station configuration — see `thesis_docs/chapters/00_lab_log.md` for
the diagnosis that led to this fix.

Grid-level constraints (voltage band, distribution feeder topology) are
deliberately **not** modeled in this baseline (`simulate_grid: False`): the
station is treated as sitting behind its own transformer, independent of
any upstream feeder. Grid-level validation against a synthetic distribution
network is the subject of Week 2 (Objective 2), not this baseline.

**Declared limitations of the Enel X grounding:**
- **(a) Hardware mismatch.** No site in the Enel X inventory currently
  combines 8 ports with 50 kW DC (CCS2) charging as our config assumes: the
  two 8-ish-port sites we can compare against are AC-only in practice
  (Salitre: 8x Type 2 AC at 43 kW; CC Retiro: 8 ports at 7.2 kW AC). Our
  configured 50 kW-per-port capability is therefore not a description of
  currently installed hardware at any single observed 8-port site — it
  represents an 8-port hub built to the DC charging floor implied by Res.
  40223/2021, i.e. a plausible **near-term upgrade** of a site like CC
  Retiro, not a snapshot of what exists today.
- **(b) Lower bound, not a census.** The Enel X inventory covers only Enel
  X's own public charging network. It excludes other charge point operators
  (CPOs) active in Bogota, and excludes private/workplace charging entirely.
  67 public chargers across 21 Enel X sites is therefore a lower bound on
  Bogota's actual public charging infrastructure, not a complete census.

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

Installed charging power for this station: 8 ports x 50 kW = 400 kW, against
a 100 kW transformer, i.e. an **oversubscription ratio of 4:1**. This ratio
is reported alongside every results table from here on, since it is the
single number that most directly explains why AFAP can overload the
transformer while Round Robin cannot.

| metric | AFAP | Round Robin |
|---|---|---|
| n_ports | 8 | 8 |
| transformer_kw | 100 | 100 |
| oversubscription_ratio | 4:1 | 4:1 |
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

- The 8-port count is grounded in the Enel X inventory (§1.1) as an observed
  mid-size hub, but the 100 kW transformer, 50 kW-per-port DC capability,
  and `spawn_multiplier: 30` arrival intensity remain our own sizing
  choices, not measured values from a real Bogota station. See §1.1's
  declared limitations (a) and (b) for the specific gaps between this config
  and the Enel X data.
- The transformer overload magnitude (0.132 kWh) is small in absolute terms
  given the station's modest size; a larger or more aggressively-loaded
  station would likely show a more pronounced AFAP-vs-RR gap. Station size
  is now treated as a first-class sensitivity dimension rather than a fixed
  assumption — see `experiments/phase1_baseline/results/size_sensitivity.csv`
  and `scripts/run_size_sensitivity.py` for the n=2/8/16-port sweep at both
  fixed and ratio-scaled transformer capacity.
- Grid voltage constraints are not modeled here (`simulate_grid: False`);
  RETIE's ±5% voltage band cannot be checked against this baseline and will
  require the Week 2 grid-enabled scenario instead.
- Results are for a single fixed day and a single random seed; they should
  not be read as an average-case estimate. A multi-seed/multi-scenario sweep
  is planned for later phases (see `PROJECT_ROADMAP.md`, Week 4-5 comparison
  methodology).

## 1.5 Bibliography

- Enel X Colombia. *Puntos de recarga* (public EV charging point locator for
  Colombia). https://www.enelx.com/co/es/personas/puntos-de-recarga.
  Consulted 2026-08-11. Used to ground `number_of_charging_stations = 8`
  against observed Bogota public charging infrastructure (§1.1).
- Colombia, Ministerio de Minas y Energia. Resolucion 40223 de 2021 (RETIE
  DC fast-charging provisions). Referenced in §1.1 as the basis for treating
  our 50 kW DC-capable 8-port config as a near-term upgrade path rather than
  a description of currently installed hardware.
