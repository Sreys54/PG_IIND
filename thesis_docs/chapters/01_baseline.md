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
  represents an 8-port hub upgraded to DC fast charging, i.e. a plausible
  **near-term upgrade** of a site like CC Retiro (near-future single site,
  not an aggregate of several sites — see the 2026-09-08 note below), not
  a snapshot of what exists today.

  **Correction, 2026-09-08 (Week 5 Part A, connector-standard citation
  check): the claim that Res. 40223/2021 sets a "CCS Combo 2 DC floor" is
  wrong and is weakened here, not kept.** Reading Articulo 4o directly
  (`thesis_docs/references/regulatory/res_40223_2021.html`): the
  resolution's minimum mandated connector standard is **Tipo 1 (SAE
  J1772) for AC (Nivel de carga 2 and 3 CA) and CCS Combo 1 (SAE J1772-
  based) for DC (Nivel de carga 3 CD)** — "CCS Combo 2" does not appear
  anywhere in the resolution's text (checked directly, not inferred). The
  regulation is explicit that this is a *minimum* only (Art. 4, Paragrafo
  1: the Ministry may revise it; the recitals note operators remain free
  to also offer additional connector types beyond the minimum), and its
  own recitals explain the Tipo 1 choice by observing the Colombian market
  was, at the time, oriented mostly toward Tipo 1 due to grid-topology
  compatibility at the residential level — the opposite of a CCS2 mandate.
  Scope: binds every charging-service provider's *new* stations (Art. 4,
  Paragrafo 3: enforceable from 12 months after entry into force, and only
  for stations installed after that date) — not a blanket requirement on
  all infrastructure regardless of install date.
  **This project's config uses CCS Combo 2 anyway — the justification is
  market practice, not the regulatory floor.** Enel Colombia's own August
  2025 network (see §1.1's station-realism reconciliation below) reports
  CCS1, CCS2, and GBT connectors in active use, i.e. CCS2 is a real,
  currently-deployed standard in Bogota despite not being the regulatory
  minimum. `station_v0_bogota`'s CCS2-only assumption is therefore a
  **declared simplification** (one connector standard, matching the
  higher-capability end of what's actually deployed) rather than a
  regulatory-floor claim — the regulatory floor is CCS Combo 1, weaker
  than what this config assumes, not stronger.
- **(b) Lower bound, not a census.** The Enel X inventory covers only Enel
  X's own public charging network. It excludes other charge point operators
  (CPOs) active in Bogota, and excludes private/workplace charging entirely.
  67 public chargers across 21 Enel X sites is therefore a lower bound on
  Bogota's actual public charging infrastructure, not a complete census.

**Reconciling two different Enel inventories (added 2026-09-08, Week 5
Part A) — both are real, they count different things at different dates:**
this chapter's §1.1 grounding above uses Enel X's public charge-point
listing page (enelx.com/co/es/personas/puntos-de-recarga), consulted
2026-08-11: 67 chargers across 21 sites, port counts per site as tabulated
above. A second, independent Enel Colombia source — a corporate news
article, "Estas son las estaciones de carga para vehiculos electricos en
Bogota" (enel.com.co, published August 2025) — describes a narrower,
more recent network: 15 fast-charging terminals across 6 zones (La
Alhambra 3 terminals/6 vehicles, Calle 97 2/4, Modelia 2/4, Nicolas de
Federman 3/6, Terminal de Transporte del Salitre 1 station, San Andresito
de la 38 1 station), using CCS1/CCS2/GBT connectors. The two do not
contradict each other — they are different scopes (a general public
listing vs. a specific fast-charging sub-network) counted at different
times — but citing both without saying so would look like an unnoticed
inconsistency to a reader who checks. `station_v0_bogota`'s 8-port,
CCS2-capable configuration is anchored to the **first** source (the
broader listing, specifically CC Retiro's 8-port count) for its port
count, and reads its DC-upgrade framing against real market practice
using the **second**, more detailed source (CCS2 confirmed in active use
network-wide, August 2025).

**Station-realism reading, decided 2026-09-08 (Week 5 Part A, user-
directed): near-future single site, not an aggregate of several sites.**
Three reasons: (1) an aggregate reading is physically incoherent — the
six zones in the August 2025 article are geographically separate,
each behind its own connection, so modelling 8 ports behind one shared
100 kW transformer would describe no real electrical topology, while a
single upgraded site does; (2) it matches the research question — this
thesis asks how much is gained from managing *existing* infrastructure
well before expanding it (Objective 1) and asks for infrastructure
guidance under demand growth (Objective 4), so the 100 kW-transformer
capacity constraint needs to be the object of study, not an artifact of
treating several separately-constrained sites as if they shared one
transformer; (3) the port count already has a real referent — CC Retiro,
8 ports, in the first Enel X source above — so only the DC-power upgrade
is speculative, not the port count itself. No site in either Enel source
currently combines 8 ports with 50 kW DC capability at a single location;
`station_v0_bogota` is best read as CC Retiro upgraded to DC fast
charging at the CCS2 standard Enel's own network already uses elsewhere,
not as a snapshot of any single site today.

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

> **Correction, 2026-09-08 (Week 5 Part A, see `00_lab_log.md`'s 2026-09-08
> entry and `05_algorithm_comparison.md`): `total_profits` above is not a
> profit or revenue figure.** Traced to source
> (`ev2gym/models/ev_charger.py:178,194,207`): it is the negated cost of
> energy purchased, in EUR, priced against EV2Gym's default Netherlands
> ENTSO-E day-ahead series — not Colombian prices, and not money collected
> from any EV driver. The two values in the table are kept as originally
> reported (not deleted, per this project's correction convention); the
> Colombian-peso figures that actually answer Objective 1's revenue
> question for this exact cell (retail revenue, purchase cost, gross
> margin, all in COP) are in `results/economics_cop.csv` and quoted in
> `05_algorithm_comparison.md`.

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
