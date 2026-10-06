# Chapter 7 — Replicability in a Second Colombian City (Objective 5)

This chapter asks which parts of the station study transfer to a second
Colombian city, which must be replaced, and which cannot be transferred
with the data available. No new simulation is run. The tariff transfer
recomputes Colombian-peso economics from the energy already recorded in
the registry, using the same pure function Week 5 used
(`ev2gym_thesis/prices/colombia.compute_row_economics`). This is valid
because no arm's control decision depends on the price (Week 5, Gate 0).
All statistics use `paired_cluster_bootstrap_ci` resampling the scenario
seed, and `n_clusters` is reported in every table.

## S7.1 City and data

**City (labelled assumption): Medellín.** Medellín is a district of
categoría especial. Its network operator and regulated retailer is
Empresas Públicas de Medellín (EPM), which publishes a monthly
regulated-market tariff sheet in the same CREG unit-cost (CU) format as
Enel Colombia's Bogotá sheet (G, T, D, Cv, PR, R). This common format is
what allows the Week 5 validation invariants to be applied unchanged. The
data turned out to be available and valid, so the brief's fallback city
(Cali) was not needed.

**Operator cost.** EPM, "Tarifas y Costo de Energía Eléctrica - Mercado
Regulado - septiembre de 2026", was the most recent sheet listed on
2026-10-05. It is stored as
`thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf`, with
full access details in `thesis_docs/sources/SOURCES_week7.md`.

For non-residential Nivel II, EPM publishes **hourly** rates rather than
the with-contribution monomial line that Enel publishes:

| Nivel II (COP/kWh) | Punta | Fuera de Punta |
|---|---:|---:|
| Industrial y Comercial (with contribution) | 923.92 | 917.58 |
| CU without contribution | 769.94 | 764.65 |

The monomial CU without contribution is 767.30; its components are not
published.

Both Week 5 invariants hold, with the same tolerances
(`ev2gym_thesis/prices/medellin.py::check_invariants`, pinned in
`test_replicability.py`):
1. **Component sum.** The six components sum to the stated CU: exactly for
   Punta, and within 0.01 COP/kWh for Fuera de Punta (764.66 against
   764.65). That 0.01 sits at the inclusive tolerance bound and is
   consistent with rounding six two-decimal components.
2. **Contribution factor.** The with-contribution line is 1.20× the
   without-contribution line: 1.19999 for Punta and 1.20000 for Fuera de
   Punta.

**Base cost (labelled, conservative):** 923.92 COP/kWh. This is the higher
of the two validated with-contribution rates, so Medellín margins are
lower bounds, the same direction as Bogotá's Week 5 framing. The
sensitivities are 917.58 (Fuera de Punta) and 920.76 (monomial × 1.20,
derived).

**Intraday spread:** 0.69% in Medellín, against 1.57% in Bogotá (Week 5).
The generation component is 52.1% of the CU in Medellín, against about
52% in Bogotá. As in Bogotá, there is no price signal worth exploiting
with time-of-use control, so no price-signal simulation was run.

**Retail price (negative result).** EPM publishes no per-kWh price for its
public EV charging stations. Charging at EPM's ~20 public "ecoestaciones"
is billed through the utility invoice or the EPM app; the sources searched
are listed in `SOURCES_week7.md`. Following Week 5's pairing rule (the
retail price must come from the same operator as the cost), no
competitor's price is substituted. **Bogotá's Enel 1,450 COP/kWh is used
only as a labelled sensitivity for Medellín**, with the Week 5 ±20% band.
Consequently, **no city-specific claim about Medellín's absolute margin is
made**. What transfers is the structure: the ranking and the relative cost
of the transformer limit.

## S7.2 What transfers, what is replaced, what cannot be transferred

`results/week7_transfer_classification.csv` (+ `.xlsx`):

| Model input | Classification | Bogotá | Medellín |
|---|---|---|---|
| Energy purchase cost (Nivel 2 commercial CU, with contribution) | city-specific, **replaced** | 865.7615 (Enel, Aug 2026) | 923.92 (EPM, Sep 2026, Punta) |
| Intraday spread | city-specific, **replaced** | 1.57% | 0.69% |
| Retail EV charging price | city-specific, **unavailable, kept and declared** | 1,450 (Enel, Aug 2025) | not published; 1,450 used as sensitivity |
| EV arrival/departure distributions | city-specific, **unavailable, kept and declared** | EV2Gym Dutch data | same Dutch data |
| Demand level (EVs per station per day) | city-specific, **unavailable, kept and declared** | `spawn_multiplier` 30 | not mapped (S7.4) |
| Feeder abstraction (34-node feeder, station at bus 27) | city-specific, **unavailable, kept and declared** | RL-ADN 34-node feeder | same |
| Climate / ambient temperature | city-specific, **unavailable, kept and declared** | not modelled in the main grid | not modelled |
| EV fleet specification (70 kWh, 50 kW) | **city-independent** | same | same |
| Station design (8 ports, 100 kW transformer) | **city-independent** | same | same |
| National regulation (CREG CU method, voltage band, Res. 40223/2021) | **city-independent** | national | national |

The decisive point is that **only the tariff inputs are both city-specific
and available**. Every other city-specific input (arrivals, demand level,
feeder and climate) is unavailable for Medellín and for Bogotá alike. The
Bogotá results already rest on the same declared stand-ins, so the
replication inherits them unchanged rather than losing realism relative to
Bogotá.

## S7.3 Tariff transfer: margins, cost of the transformer limit, ranking invariance

Non-grid statistical rows: Week 5's 13 arms plus the final RL model, 100
cells each, n_clusters = 50. Results are in COP per simulated day
(`results/week7_replicability_margin.csv`,
`results/week7_cost_of_transformer_limit_two_cities.csv`).

| Arm | Energy (kWh/day) | Bogotá margin | Medellín margin | Conceded vs. AFAP, Bogotá [95% CI] | Conceded vs. AFAP, Medellín [95% CI] |
|---|---:|---:|---:|---|---|
| AFAP | 202.1 | 118,084 | 106,329 | 0 | 0 |
| **Round Robin** | 201.2 | 117,532 | 105,832 | **551.9 [274.3, 874.2]** | **497.0 [247.0, 787.2]** |
| MPC_TrackingG2V | 201.1 | 117,512 | 105,814 | 571.8 [550.6, 593.1] | 514.9 [495.8, 534.0] |
| Optimal_Oracle_Tracking | 201.1 | 117,507 | 105,810 | 576.6 [555.6, 598.1] | 519.2 [500.3, 538.5] |
| TD3 extended, seed 102 (final RL) | 197.9 | 115,614 | 104,105 | 2,470.4 [1,353.5, 3,797.9] | 2,224.5 [1,218.8, 3,419.8] |

**The cost of respecting the 100 kW transformer limit with the recommended
deployable strategy** (Round Robin against AFAP) is 551.9 COP/day in
Bogotá and 497.0 COP/day in Medellín. That is 0.47% of AFAP's margin in
both cities. **In relative terms the cost transfers exactly.** Under a flat
price, the conceded margin is (energy foregone) × (retail − cost), so the
two cities differ only by the factor (1,450 − 923.92) / (1,450 − 865.76)
= 0.900.

**Ranking invariance, verified programmatically**
(`results/week7_ranking_invariance.csv`, asserted in
`analyze_week7_replicability.py::ranking_invariance` and pinned in
`test_replicability.py`). Across eight price scenarios, the ranking of the
arms by margin is identical to their ranking by energy delivered, and
identical across all scenarios. The eight scenarios are:
- Bogotá base and Bogotá retail ±20%;
- Medellín base and Medellín retail ±20%;
- the two Medellín cost sensitivities.

This holds for every dataset: the non-grid rows and each of the five grid
settings (S7.5). Under a flat tariff with retail above cost, **no tariff
level in either city can change which strategy is economically
preferable**. The economic argument for or against a strategy is entirely
its energy delivered.

## S7.4 Demand transfer

The question is whether the Medellín station should be mapped onto a
different point of the Objective 4 demand axis (Axis 1, 1.0–1.6×). The
evidence found:
- **EV registrations.** The Andi–Fenalco report (cited by El Colombiano,
  2025-09-10) gives January–August 2025 EV registrations of **2,148 in
  Medellín against 5,358 in Bogotá**, a ratio of 0.40. For August 2025
  alone the ratio is 0.51 (367 against 722).
- **Public charging points.** The same source counts about 30 in
  Medellín. Bogotá had at least 67 Enel X chargers in Week 1, which is a
  lower bound, not a census. The ratio is about 0.45.

**Decision (rule applied).** These are city-level flows and inventories,
in different units and from different dates. No source gives
EVs-per-station-per-day for either city. Taking the registration ratio
(0.40) as a per-station demand ratio would assume equal charger density;
correcting by the charger counts (0.40 / 0.45 ≈ 0.9) mixes a lower-bound
inventory with a flow. **Neither reading is defended by a source, so no
city-specific demand claim is made.** Both naive readings fall **below**
the 1.0–1.6× range that Objective 4 sweeps. The infrastructure guidelines
are therefore presented as **conditional on the station's demand level**.
They do not cover a station whose demand is below the Week 1 Bogotá
sizing.

**Proposal for future runs.** Run Axis 1 at 0.4×, 0.7× and 0.9×. Measured
cost: 16.3 s of computation per (setting, seed, day) for the 5 arms (1e).
At 50 seeds × 2 days per setting, that is about 27 minutes per setting on
one process, and about 10 minutes with 3 parallel workers as used in
Objective 4. Not run, per the brief.

## S7.5 Grid-enabled rows

The same tariff transfer was applied to the 2,500 Objective 4 grid rows,
5 settings × 500 cells (`results/week7_replicability_margin.csv`,
`results/week7_cost_of_transformer_limit_two_cities.csv`).

Round Robin's cost of respecting the 100 kW limit, as margin conceded
against AFAP in COP per day (n_clusters = 50):

| Setting | Bogotá | Medellín |
|---|---|---|
| base, load 1.3, load 1.6 | 551.9 [274.3, 874.2] | 497.0 [247.0, 787.2] |
| spawn 1.3× | 800.0 [472.3, 1,176.4] | 720.3 [425.3, 1,059.3] |
| spawn 1.6× | 556.1 [261.4, 921.2] | 500.8 [235.4, 829.5] |

The three Axis 2 settings are identical, because the feeder does not feed
back on the station's energy (06 S6.4). The ratio between the two cities is
the constant 0.900 in every row. **Ranking invariance holds in all 6
datasets × 8 price scenarios** (48 checks, all identical rankings,
`results/week7_ranking_invariance.csv`). The Objective 4 guidelines carry
their economic cost to Medellín unchanged in relative terms: under 1% of
daily margin at every growth level.

## S7.6 Answer to Objective 5

The Bogotá station study transfers to Medellín as follows:
- **Ranking and strategy recommendation: transfer fully.** The margin
  ranking is tariff-invariant under any flat price with retail above cost
  (verified across 8 scenarios). The recommendation does not depend on any
  price, so Round Robin remains the recommended strategy.
- **Relative cost of the transformer limit: transfers exactly** (0.47% of
  margin in both cities).
- **Absolute peso margins: transfer only through the tariff.** They scale
  with the unit margin, which is 9.95% lower in Medellín under the cost
  data that is available. The Medellín retail price is not published, so
  the absolute margin is a sensitivity, not a claim.
- **Physical results do not transfer, because their inputs are not
  city-specific in either city.** These are overload, satisfaction,
  energy-not-served and voltage. The arrival model, the demand level and
  the feeder are the same declared stand-ins in both cities.

Replicating the study in a second city is therefore immediate for the
economic layer and conditional, not established, for the physical layer.
The binding gaps are a Colombian charging-session dataset and a
per-station demand figure, not the tariff.
