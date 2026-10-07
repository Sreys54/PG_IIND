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
both cities. The equal 0.47% and the factor (1,450 − 923.92) / (1,450 −
865.76) = 0.900 between the two cities are **consequences of
Proposition 7.1 (S7.3a), not empirical findings**. Under a flat price,
the relative cost is ΔE / E_AFAP whatever the tariff, so it could not
have differed between the cities.

*Correction (2026-10-06, closure brief D1).* This paragraph originally presented "the cost transfers
exactly" as a finding of the replication. It is an algebraic identity of
the flat-tariff economics, proved in S7.3a.

**Implementation check of Proposition 7.1**
(`results/week7_ranking_invariance.csv`, asserted in
`analyze_week7_replicability.py::ranking_invariance` and pinned in
`test_replicability.py`). Across eight price scenarios, the ranking of the
arms by margin is identical to their ranking by energy delivered, and
identical across all scenarios. Proposition 7.1 guarantees this for any
flat price with retail above cost. The check therefore verifies that the
code implements the economics correctly. It is not evidence about
Medellín. The eight scenarios are:
- Bogotá base and Bogotá retail ±20%;
- Medellín base and Medellín retail ±20%;
- the two Medellín cost sensitivities.

This holds for every dataset: the non-grid rows and each of the five grid
settings (S7.5). Under a flat tariff with retail above cost, **no tariff
level in either city can change which strategy is economically
preferable** (Proposition 7.1). The economic argument for or against a
strategy is entirely its energy delivered. This is true **only under a
flat (monomial) tariff**. Under a two-band time-of-use option the ranking
can change, and S7.7 measures by how much.

### S7.3a Proposition 7.1 (flat-tariff economics)

**Setting.** Let arm a deliver energy E_a(s) ≥ 0 in cell s (a scenario seed
and day). The station buys energy at a constant unit cost c and sells it
at a constant unit price p > c, both fixed over the day. Two facts hold in
this project:
- no arm discharges (V2G is disabled, `total_energy_discharged` = 0);
- no arm's control decision depends on p or c (Week 5, Gate 0).

The daily gross margin is therefore M_a(s) = (p − c) · E_a(s).

**Proposition 7.1.** Under these conditions, for any arms a, b and any
p > c:
1. sign(M_a(s) − M_b(s)) = sign(E_a(s) − E_b(s)) in every cell. The same
   holds for the means over any set of cells: the ranking of arms by mean
   margin equals their ranking by mean energy delivered.
2. The relative margin that arm b concedes against AFAP is
   (M̄_AFAP − M̄_b) / M̄_AFAP = (Ē_AFAP − Ē_b) / Ē_AFAP, independent of p
   and c.
3. The absolute margin conceded, M̄_AFAP − M̄_b = (p − c)(Ē_AFAP − Ē_b),
   scales linearly with the unit margin (p − c). Between two cities with
   the same energy outcomes it differs only by the ratio of their unit
   margins.

**Proof.**
1. M_a − M_b = (p − c)(E_a − E_b), and p − c > 0, so the two differences
   have the same sign. Means are linear, so M̄_a − M̄_b =
   (p − c)(Ē_a − Ē_b) and the argument repeats.
2. Divide M̄_AFAP − M̄_b = (p − c)(Ē_AFAP − Ē_b) by
   M̄_AFAP = (p − c)Ē_AFAP. The factor (p − c) cancels.
3. Read directly from the expression in step 2, before dividing. ∎

**What the proposition does not cover.**
- *A cost that varies over the day.* With a two-band option, the margin is
  M = p·E − c_peak·E_peak − c_off·E_off. This depends on when the energy is
  delivered, not only on how much, so ranking invariance is no longer
  guaranteed (S7.7).
- *Price-responsive control.* Any arm whose actions depended on p or c
  would also break step 1. No arm in this project does.

**Status of earlier statements.** Three earlier statements are
**implications of Proposition 7.1, not findings**:
- the 48/48 identical rankings of S7.5;
- the identical 0.47% in both cities;
- the constant 0.900 ratio.

They remain valid as checks that the code implements the economics.


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

*Update (2026-10-06, closure brief D3).* Lower-demand runs at 0.5× and
0.733× were made in the closure (S7.8). The 0.4/0.7/0.9× proposal is
superseded by them.

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
the constant 0.900 in every row. Ranking invariance holds in all 6
datasets × 8 price scenarios (48 checks, all identical rankings,
`results/week7_ranking_invariance.csv`). These 48 checks are the
implementation check of Proposition 7.1. They are not 48 independent
pieces of evidence, because the proposition makes each of them certain.
The Objective 4 guidelines carry their economic cost to Medellín unchanged
in relative terms (proposition, part 2): under 1% of daily margin at every
growth level, under a flat tariff.

## S7.7 Every categoría especial municipality (closure brief D2)

**City list (official source).** Ley 617 de 2000, Art. 6, defines
categoría especial as a population of at least 500,001 and annual
unrestricted current revenue (ICLD) above 400,000 SMMLV. The Contaduría
General de la Nación's categorisation workbook gives the category of every
municipality. Its "Vigencia 2026" column records the 2025
self-categorisation decrees. It lists six municipalities as ESP:
- Bogotá D.C. (Decreto 523, 2025-10-28);
- Medellín (Decreto 837, 2025-10-08);
- Cali (Decreto 725, 2025-09-30);
- Barranquilla (Decreto 646, 2025-10-02);
- Cartagena (Decreto 2000, 2025-08-26);
- Bucaramanga (Decreto 710, 2025-09-02).

The workbook is saved as
`thesis_docs/sources/municipal_categories/cgn_categorizacion_historicos_hasta_2025.xlsx`
(accessed 2026-10-06), and the law as `ley_617_2000.pdf`. The CGN's own
Res. 338/2025, which categorises only the entities that did not
categorise themselves, is saved too. It is a scanned PDF with no text
layer, so it was not used to extract the list.

**Operators and sheets.** Each city's network operator is the one whose
regulated tariff sheet covers it: Enel Colombia, EPM, EMCALI, Air-e
(intervened by Superservicios), Afinia (Grupo EPM) and ESSA (Grupo EPM).
Values are transcribed in `ev2gym_thesis/prices/cities.py`, each with its
saved sheet. The Air-e and Afinia sheets have no usable text layer and
were read from rendered images. Tables:
`results/closure_multicity_tariffs.csv` and
`results/closure_multicity_rr_cost.csv`, with `.xlsx` versions.

| City | Operator, sheet month | Nivel 2 CU without contribution | Flat cost with 20% contribution | Two-band option (with contribution), peak / off-peak | Spread | Generation share of CU | Invariants |
|---|---|---:|---:|---|---:|---:|---|
| Bogotá | Enel, Aug 2026 | 721.47 | 865.76 (published) | Opciones horarias 9–12, 18–21 h: 877.57 / 864.02 | 1.57% | 52.0% | both pass |
| Medellín | EPM, Sep 2026 | 767.30 (monomial) | 920.76 (derived ×1.20) | Tarifa horaria 9–12, 18–21 h: 923.92 / 917.58 | 0.69% | 52.1% | both pass (Week 7) |
| Cali | EMCALI, **Jan 2026** | 625.75 | 750.89 (derived ×1.20) | Doble horaria 9–12, 18–21 h: 755.84 / 748.91 (derived) | 0.92% | 49.4% | sum passes; factor 1.20 checked on the Nivel 1 commercial line |
| Barranquilla | Air-e, Sep 2026 | 746.55 | 895.85 (published) | Doble tipo 1, 17–22 h: **956.74 / 869.52** | **10.03%** | 60.2% | both pass |
| Cartagena | Afinia, Sep 2026 | 859.76 (CU with COT) | 1,031.71 (derived ×1.20) | Doble tipo 1, 17–22 h: 1,031.46 / 1,031.22 | 0.02% | 50.6% | both pass (sum against the with-COT CU) |
| Bucaramanga | ESSA, Sep 2026 | 855.67 | 1,026.80 (published) | none published | — | 56.1% | both pass |

**Unavailable, listed rather than filled in.**
- *EMCALI after January 2026.* The latest sheet retrievable on 2026-10-06
  is January 2026, and Cali's row uses it, labelled.
- *Time-of-use option in Bucaramanga.* ESSA publishes none.
- *A per-kWh public charging price* from EPM, Air-e, Afinia and ESSA:
  - EPM, Air-e and Afinia: no price located.
  - ESSA prices per "Unidad de Recarga Vehicular", about 1,500 COP fast
    and 1,200 COP normal (Vanguardia, 2026-06-01). The unit is not defined
    in kWh.
- *EMCALI's price.* The 2,500 COP/kWh comes from a press report (El País
  Cali, 2025-04-30), not an EMCALI page, and is labelled secondary.
- *Afinia's Nivel 2 row.* The Afinia sheet does not label its Nivel 2
  two-band row directly. It was identified through the residential
  >173 kWh row, which pays the full CU (labelled assumption).

**Unit margin and the cost of the transformer limit** (non-grid statistical
rows, 100 paired runs, n_clusters = 50). "Flat" uses the flat cost column
above. "Two-band" applies the city's option to each run's 15-minute station
power profile. Each profile is checked to reproduce the registry energy
exactly (maximum difference 0.000000 kWh over 2,200 runs).

| City | Unit margin at 1,450 | Unit margin at the operator's price | Round Robin's cost vs. AFAP, flat (COP/day) | Same, two-band option (COP/day) |
|---|---:|---:|---|---|
| Bogotá | 584.2 | 584.2 (1,450 is Enel's price) | 551.9 [274.3, 874.2] | 775.1 [487.5, 1,108.4] |
| Medellín | 529.2 | not published | 500.0 [248.5, 791.9] | 606.6 [353.8, 901.0] |
| Cali | 699.1 | 1,749.1 (2,500, press) | 660.4 [328.2, 1,046.1]; at 2,500: 1,652.3 [821.2, 2,617.2] | 775.5 [444.7, 1,161.1] |
| Barranquilla | 554.1 | not published | 523.5 [260.2, 829.2] | **1,878.4 [1,425.7, 2,358.5]** |
| Cartagena | 418.3 | not published | 395.1 [196.4, 625.9] | 399.3 [200.4, 630.2] |
| Bucaramanga | 423.2 | not published | 399.8 [198.7, 633.2] | — |

Under the flat cost, the relative cost is 0.47% of AFAP's margin in every
city, as Proposition 7.1 requires. Medellín's flat figure here (500.0)
uses the monomial ×1.20 so that the definition is the same in every city.
Week 7's 497.0 used the higher Punta rate, the conservative choice, and
both are reported.

**Headline: is the spread small everywhere? No.**
- **Four cities are small.** In Bogotá, Medellín, Cali and Cartagena the
  published two-band spread is at most 1.57%.
- **Bucaramanga publishes no option.**
- **Barranquilla is the exception.** Air-e's Nivel 2 "doble tipo 1"
  option charges 10.03% more from 17:00 to 22:00.

Round Robin places more of its energy in the 17–22 h band than AFAP:
27.6% against 20.2%. In the 9–12, 18–21 h bands it places 43.8% against
36.1%. Round Robin spreads charging over each EV's stay, so more of it
falls in the evening. Under the Air-e option, its cost of the 100 kW limit
therefore rises from 523 to 1,878 COP/day. That is still under 2% of
margin, but 3.6 times the flat figure.

The margin ranking under the two-band options differs from the energy
ranking:
- *Bogotá, Medellín and Cali:* in 3 of 22 positions, all among arms whose
  energy differs by tenths of a kWh (Round Robin, MPC_TrackingG2V,
  Optimal_Oracle_Tracking).
- *Cartagena:* in 2 positions (AFAP and MPC_EnergyMaxG2V).
- *Barranquilla:* in 12 positions. The RL arms move up, because they
  deliver less energy in the evening band
  (`results/closure_multicity_tou_ranking.csv`).

Two consequences follow:
1. An operator choosing a two-band option should check where the
   charging falls in the day. In Barranquilla, the flat (monomial) option
   keeps Proposition 7.1 exact.
2. The recommendation of Round Robin rests on overload and demand not
   served, not on margin, so the ranking shifts do not change it.

## S7.8 Lower demand (closure brief D3)

The closure runs at 0.5× and 0.733× the Week 1 demand (06 S6.4; the
spawn multiplier 22 gives 0.733×, not 0.75×) answer S7.4's open question
directly. They replace the proposed 0.4/0.7/0.9× runs, which were not run.

Under Round Robin, paired by seed and day, with n_clusters = 50
(`results/closure_lower_demand_monotonicity.csv`):
- **Overload.** It is 0.0 kWh at 0.5×, 0.733× and 1.0×, so lower demand
  never worsens it.
- **Demand not served (lower bound)**, going down from each level to the
  next lower one:
  - from 1.0× to 0.733×: falls by 18.8 points [15.8, 21.8];
  - from 0.733× to 0.5×: falls by 11.7 points [9.2, 14.4].

  So lower demand never worsens it on average. Cell by cell, the
  relationship is not strictly monotone: 18 of 100 cells have higher DNS
  at 0.5× than at 0.733×, because the arrival draws differ between levels.
- **Satisfaction.** Differences are within ±0.1 point, and the CIs include
  zero or nearly so.

**Statement.** Below 0.733× the Bogotá demand, the guideline holds. The
transformer limit is never exceeded, and demand not served is under 15%
with its CI: at 0.5× it is 4.1% [2.6, 5.8]. At 0.733× it is already
15.8% [12.6, 19.1]. **The tested level at which the guideline holds is
0.5×, and the threshold lies between 0.5× and 0.733×.**

**City mapping: not made.** No source gives EVs per station per day for
any of the six cities (S7.4), so no city is placed on this axis. The
statement is conditional on a station's demand relative to the Week 1
sizing.

## S7.9 What does not transfer (closure brief D4)

Three physical inputs are the same declared stand-ins in every city. The
physical results therefore do not transfer as city-specific findings.
1. **Climate.** Battery thermal behaviour and ambient temperature are not
   modelled. The cities range from Bogotá's highland climate (about
   2,600 m) to the Caribbean coast (Barranquilla, Cartagena), and that
   difference is not represented. It is declared, not estimated.
2. **Arrivals.** Arrival times, stay durations and requested energy come
   from EV2Gym's Dutch data in every city. Two further points:
   - The per-port arrival model also ties demand to the port count (06
     S6.4, C2).
   - No Colombian charging-session dataset was available.
3. **Feeder.** Every result on the grid uses EV2Gym's 34-node network,
   with the station on bus 27. None of the six operators' feeders is
   public. Three further points:
   - The 34-node feeder is out of band at bus 27 with the station idle
     (06 S6.2).
   - EV2Gym has no feedback from the feeder to the station (06 S6.4).
   - EV2Gym's 123-bus network is in band when idle, and it was used for
     the voltage check (06, Guideline 3). It is a test network too, not a
     Colombian feeder.

The economic layer transfers by Proposition 7.1 under a flat tariff. Under
a two-band tariff it transfers with the corrections measured in S7.7.

## S7.6 Answer to Objective 5

The Bogotá station study transfers to Medellín as follows:
- **Ranking and strategy recommendation: transfer fully under a flat
  tariff.** The margin ranking is tariff-invariant under any flat price
  with retail above cost (Proposition 7.1; the 8-scenario check verifies
  the implementation). The recommendation does not depend on any price, so
  Round Robin remains the recommended strategy. Under a two-band option
  the ranking can shift among arms with near-equal energy (S7.7).
- **Relative cost of the transformer limit: identical in every city under
  a flat tariff** (0.47% of margin), by Proposition 7.1, part 2.
- **Absolute peso margins: transfer only through the tariff.** They scale
  with the unit margin, which is 9.95% lower in Medellín under the cost
  data that is available. The Medellín retail price is not published, so
  the absolute margin is a sensitivity, not a claim.
- **Physical results do not transfer, because their inputs are not
  city-specific in any city.** These are overload, satisfaction, demand
  not served and voltage. The arrival model, the demand level, the feeder
  and the climate are the same declared stand-ins in every city (S7.9).
- **Six cities, not one** (closure, S7.7). The spread is small in four
  cities. Bucaramanga publishes no option. Barranquilla's 10% two-band
  option is the exception: under it, Round Robin's cost of the limit
  rises from 523 to 1,878 COP/day and the margin ranking shifts. The flat
  option keeps Proposition 7.1 exact there.
- **Lower demand** (S7.8). Below 0.733× the Bogotá demand, the guideline
  holds; 0.5× is the tested level. No city is mapped onto the demand axis,
  because no per-station source exists.

Replicating the study in a second city is therefore immediate for the
economic layer and conditional, not established, for the physical layer.
The binding gaps are a Colombian charging-session dataset and a
per-station demand figure, not the tariff.
