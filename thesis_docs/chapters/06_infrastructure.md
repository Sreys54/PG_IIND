# Chapter 6 — Infrastructure Guidelines on the Grid-Enabled Model (Objective 4)

This chapter moves the reference station (`station_v0_bogota`: 8 ports,
50 kW each, one 100 kW local transformer) onto a distribution feeder and
asks two questions:
- what the station needs as demand at the station and load on the feeder
  grow;
- what the station does to the feeder's voltage.

The guidelines are argued only from the numbers below, each with its 95%
cluster-bootstrap CI (`paired_cluster_bootstrap_ci`, resampling the
scenario seed) and `n_clusters`.

## S6.1 Grid-enabled model and its validation

**Feeder.** The feeder is EV2Gym's 34-node network
(`ev2gym/data/network_data/node_34`, taken from the RL-ADN environment of
Hou et al., 2025): Laurent power flow, 7.80 MW total nominal load and PV at
80% of each bus's load (`pv_scale`). The library calls it the IEEE 34-bus
feeder. **This thesis does not validate it against the IEEE published
test-feeder data**, and it is a stand-in for an Enel or EPM feeder, none of
which is public. The background load profile is drawn by EV2Gym's own data
generator, and the PV profile is Dutch.

**Station placement (labelled assumption).** All 8 charging stations sit
on **bus 27**, the electrically farthest bus from the substation (largest
series path resistance, 16 hops). It is the most voltage-sensitive bus,
and therefore the conservative choice for a voltage study.

EV2Gym has no configuration key for this. In grid mode it creates one
transformer per bus and spreads the stations round-robin across them. Here
that would have put 8 stations on 8 buses with 8 separate 100 kW
transformers, silently replacing the study's single 100 kW constraint with
800 kW. `ev2gym_thesis/grid/placement.py` reassigns the stations from
outside the library (no file in `ev2gym/` is edited) and refuses to build a
grid environment without an explicit station bus.

**Config.** `experiments/phase3_infra_replicability/configs/station_v0_bogota_grid.yaml`
differs from the Week 1–5 config only in the following:
- `simulate_grid: True`;
- `number_of_transformers: -1`;
- `load_multiplier: 1.0`;
- the station bus (`network_info.thesis_station_bus: 27`).

The station transformer stays at **100 kW**.

**Equivalence (Step 1b).** A tolerance of ≤ 1e-6 absolute was stated
before the run. AFAP and Round Robin were run on seeds 0–9 × both
evaluation days under both configs, 40 paired cells. The maximum absolute
difference was **0.0** in all five metrics checked:
- EVs served;
- energy charged;
- transformer overload;
- average satisfaction;
- tracking error.

All five Objective 4 arms also reproduce their non-grid registry values
exactly on a further cell (seed 0, weekday). **The grid-enabled model is
therefore the same station model plus a feeder.** Station metrics carry
over unchanged, and voltage is the only new output. The 1b divergence rule
did not fire, so grid and non-grid station results may be compared.

**RL compatibility (Step 1c).** The final RL model, `TD3_vanilla` extended
seed 102 at 850,000 steps (author's decision, S5.11), was trained without
the grid. Under the grid config its observation space is identical (27-dim).
Its observations, actions and resulting metrics are bit-identical step by
step to the non-grid run of the same scenario, with the frozen
VecNormalize statistics never updated (`test_week6_infra.TestRLCompatibility`).
No adapter and no retraining were needed.

## S6.2 What the voltage metric measures (Step 1d)

EV2Gym computes three voltage statistics on the per-bus, per-step voltage
array (34 buses × 96 steps, in p.u.):

| Statistic | Definition |
|---|---|
| `voltage_violation` | Σ over buses and steps of min(0, 0.05 − abs(1 − v)), aggregate and ≤ 0 |
| `voltage_violation_counter` | Number of (bus, step) samples outside [0.95, 1.05] |
| `voltage_violation_counter_per_step` | Number of steps in which any bus is outside the band |

The band is therefore **±5% around 1.0 p.u.**, the band this thesis adopts
as its voltage target. The source of that band in Colombian regulation is
not re-verified in this chapter. An independent check on the raw voltage
array (`ev2gym_thesis/grid/voltage.py::band_check`) was implemented and
tested anyway. It matches the library exactly on every probe row, and it
also reports the station's own bus separately.

**Can it trip?** A probe used AFAP and Round Robin on seeds 0–9 × 2 days,
with `load_multiplier` from 0.5 to 1.0 (200 rows, `analysis_row = False`):
- it first trips at **`load_multiplier` = 0.8**;
- at the library's nominal load (1.0) it trips in 16 of 20 AFAP cells;
- **with the station idle** (zero-charging diagnostic) it trips in 15 of 20
  of the same cells.

The feeder at bus 27 is already outside the band without any EV load. The
metric is live, which makes this a usable result rather than a negative
one, but it measures the feeder rather than the station. **Voltage
compliance is therefore assessed as the station's increment over the
idle-station run of the same cell** (S6.5). No absolute RETIE compliance
claim is made for the feeder.

## S6.3 Experiment design

| Item | Value |
|---|---|
| Arms (fixed) | AFAP; Round Robin; MPC_TrackingG2V (non-causal); final RL model (TD3 extended, seed 102, 850k); Optimal_Oracle_Tracking (upper bound, non-causal) |
| Axis 1, station demand | `spawn_multiplier` 30 / 39 / 48 (1.0× / 1.3× / 1.6× the Week 5 value), feeder load 1.0 |
| Axis 2, feeder background | `load_multiplier` 1.0 / 1.3 / 1.6, `spawn_multiplier` 30 |
| Settings | 5 distinct, swept one axis at a time; the base setting is shared by both axes |
| Cells per arm and setting | 50 scenario seeds (`SEEDS` 0–49) × 2 day types (2022-01-17, 2022-03-05) = 100 |
| Total | 2,500 grid rows, with `analysis_row = True` and `simulate_grid = True`, plus a zero-charging voltage baseline for all 500 (setting, seed, day) cells |

The 50-seed count was chosen by the Checkpoint 1 timing rule: the
projection plus 25% finished before 07:00. Rows were produced with the real
row builders (`scripts/run_week7_grid.py`), and the analysis is in
`scripts/analyze_week7_infra.py`.

## S6.4 Results and guidelines

All 2,500 grid cells completed: 5 arms × 5 settings × 50 seeds × 2 days,
`analysis_row = True`, `simulate_grid = True`. At the base setting, all 500
cells × 5 arms equal the non-grid registry rows on every station metric,
with a maximum difference of 0.0
(`results/week7_grid_base_equivalence_all_arms.csv`). All CIs below are 95%
cluster-bootstrap CIs with **n_clusters = 50**. Figures: `figures/f15_grid_growth.png`,
`f16_transformer_sizing.png` and `f17_voltage_attribution.png`.

**A structural finding governs Axis 2.** Raising the feeder's background
load (`load_multiplier` 1.3 and 1.6) leaves **every station metric
identical to the base setting**. EV2Gym's feeder does not feed back on the
station: the station's power is not curtailed by the feeder's voltage, and
its transformer does not see the bus load. Axis 2 therefore affects only
the voltage results (S6.5). **This is a property of the simulator, not a
finding about real feeders.** It is declared as a limitation (08, L4):
a real feeder operator could curtail, and a real transformer shared with
other customers would see their load.

*Source confirmation (2026-10-06, closure brief E1).* The order of
operations in `ev2gym/models/ev2gym_env.py::step` is:
- every charging station executes its action and updates its own
  transformer first (`cs.step(...)` and `self.transformers[...].step(...)`,
  lines 362–385);
- only then does `self.grid.step(self.node_ev_power[1:, ...])` run the
  power flow (lines 387–397);
- the resulting voltages are written to `self.node_voltage` (line 397)
  and nowhere else.

`node_voltage` is read only by the following:
- the voltage-aware reward functions in `ev2gym/rl_agent/reward.py`
  (lines 108, 117, 270), none of which this project's arms use;
- the statistics (`ev2gym/utilities/utils.py`, lines 69–75);
- the plots.

It appears in none of `ev_charger.py`, `transformer.py`, `ev.py`,
`baselines/heuristics.py` or `rl_agent/state.py`. That absence is pinned
in `test_closure.TestNoFeederFeedback`. The background feeder load enters
only `grid.step` and never the station transformer.

### Guideline 1 — Transformer sizing

Per-seed overload and peak station power over 50 seeds
(`results/week7_transformer_sizing.csv`):

| Setting | Arm | Seeds with overload | Overload P50 / P95 / max (kWh/day) | Peak P50 / P95 / max (kW) | Next standard size for the P95 peak |
|---|---|---:|---|---|---:|
| base | AFAP | 28/50 | 10.32 / 44.88 / 78.63 | 116.2 / 172.7 / 220.8 | 225 kVA |
| spawn 1.3× | AFAP | 42/50 | 21.20 / 69.78 / 91.23 | 132.0 / 191.9 / 220.8 | 225 kVA |
| spawn 1.6× | AFAP | 39/50 | 25.09 / 61.45 / 83.13 | 134.6 / 189.1 / 204.7 | 225 kVA |
| base / 1.3× / 1.6× | Round Robin | 0/50 | 0 | P95 66.8 / 73.3 / 67.6 | within 100 kW |
| base / 1.3× / 1.6× | TD3 extended s102 | 16 / 16 / 26 of 50 | P95 22.14 / 23.01 / 28.82 | P95 144.3 / 144.5 / 145.9 | 225 kVA at pf 0.894 (150 kVA at unity pf; corrected 2026-10-06) |

MPC and the oracle never overload (P95 peaks 51–61 kW). AFAP's peak does
not respond to the transformer rating, so its 95th-percentile peak is a
valid sizing number. **Unmanaged (AFAP) charging would need a transformer
of about 173–192 kW for the 95th-percentile scenario to stop
overloading.** That is the next standard size of **225 kVA**, against the
installed 100 kW, and it holds across 1.0–1.6× demand.

*Units (correction 2026-10-06, closure brief A.4).* EV2Gym models the
transformer limit in kW only. The underlying figures are P95 peaks of
172.7 / 191.9 / 189.1 kW at 1.0 / 1.3 / 1.6×.

**Power factor.** CREG Res. 015 de 2018, Chapter 12, charges an end user
for reactive energy above 50% of active energy per hour. The lowest
uncharged power factor is therefore cos(arctan 0.5) = **0.894**. This is a
derived value, with a verification caveat on the compiled text in
`thesis_docs/sources/SOURCES_closure.md`. At that power factor the peaks
are 193.2 / 214.6 / 211.5 kVA.

**Standard ratings.** The operator's standard three-phase list (Enel
ET-013, Table 1) is 15, 30, 45, 75, 112.5, 150, 225, 300, 400, 500, 630,
800 and 1,000 kVA.

**Mapping, rounding up.** Every peak maps to **225 kVA**, whether the
power factor is 0.894 or 1.0. The installed 100 kW limit corresponds to
112.5 kVA at pf 0.894 (111.9 kVA needed). The RL model's 144–146 kW P95
peaks are 161–163 kVA at pf 0.894, which maps to 225 kVA. At unity power
factor they map to 150 kVA, so the earlier "150 kVA" assumed unity power
factor.

**With Round Robin, the installed 100 kW transformer is sufficient up to
1.6× the reference demand.** There is zero overload in every seed, and the
95th-percentile peak is 67–73 kW.

**Tail support:** the 95th percentile of 50 seeds rests on 3 seeds above
it in every row. This is a **directional** sizing result, not an estimate
of the tail of the demand distribution.

### Guideline 2 — Capacity and ports, on demand not served (rewritten 2026-10-06, closure brief Parts B–C)

*Correction (2026-10-06, closure brief Checkpoint B).* This guideline
originally said that Round Robin's satisfaction "is not reached [below
90%] within 1.0–1.6×" and that "nothing in the data indicates that the 8
ports are the bottleneck". **Both statements are withdrawn.** The
satisfaction figures (99.89–99.93%) were correctly computed. They describe
only the EVs that obtained a port: EV2Gym never creates an arrival at an
occupied port, so turned-away drivers appear in no registry metric
(mechanism below). Measured on demand not served, the 8 ports are the
binding constraint already at the reference demand.

**Mechanism (EV2Gym source, read-only).** Arrivals are drawn per port in
`ev2gym/utilities/utils.py::EV_spawner`:
- one uniform draw per port and step (line 490);
- an EV is created only if that port has been free for three steps
  (lines 531–535) and the draw passes the arrival threshold (line 537);
- a draw on an occupied port creates nothing: no queue, no counter, no
  statistic;
- `ev_charger.spawn_ev` asserts that the port is free (line 271).

**Metric.** `ev2gym_thesis/demand/censoring.py` replays the spawner's
random draws from outside the library. It asserts that the replay re-finds
every spawned EV, then counts the draws that fell on blocked ports. Two
bounds:
- *lower:* only arrivals that no free port in the same step could have
  absorbed;
- *upper:* every blocked draw.

Each rejected arrival is assigned the day's mean requested energy, capped
at the 70 kWh battery. Demand not served is then:

DNS = (E_rejected + R_served − E_delivered) / (E_rejected + R_served),

where R_served is the energy requested by the EVs that were served. The
counts are stored in `results/closure_censoring_by_cell.csv`; they are a
post-processing workbook, never a registry column. DNS below is the lower
bound unless stated, and every CI is a cluster bootstrap with
n_clusters = 50.

**C1 — where each arm breaks.** The sweep uses the non-grid reference
config. This is justified because the grid rows reproduce every non-grid
station metric with a 0.0 difference (S6.1). It covers 7 demand levels,
50 seeds × 2 days per level, for AFAP, Round Robin and the final RL
model:
- 0.5×, 0.733×, 2.0× and 2.5× are new rows;
- 1.0×, 1.3× and 1.6× are the Step 2 rows.

The 0.733× level comes from spawn multiplier 22, because round(22.5) = 22;
it is labelled 0.75× in the files.

A level is "broken" when the 95% CI fails a target. The rule takes the
side that makes compliance hardest to claim (conservative, labelled):
- satisfaction: CI lower bound below 90%;
- DNS: CI upper bound above 15%;
- 95th-percentile per-seed peak power: CI upper bound above 100 kW.

(`results/closure_c1_capacity_by_level.csv`, `closure_c1_breaking_levels.csv`.)

| Arm | Breaking level | First criterion broken | Value at the breaking level [95% CI] | n_clusters |
|---|---|---|---|---:|
| Round Robin | **0.733×** (holds at 0.5×) | demand not served | 15.80% [12.56, 19.13] | 50 |
| AFAP | **0.5×** (lowest tested) | P95 peak > 100 kW | 133.1 kW [122.2, 156.3] | 50 |
| Final RL model (TD3 extended, s102, 850k) | **0.5×** (lowest tested) | P95 peak > 100 kW | 137.6 kW [121.6, 156.5] | 50 |

Round Robin across the sweep:

| Demand | DNS, lower bound | DNS, upper bound | Overload | P95 peak | Satisfaction (served EVs) |
|---|---|---|---|---|---|
| 0.5× | 4.08% [2.59, 5.77] | 57.4% | 0 in all seeds | 65.2 kW | 99.96% |
| 0.733× | 15.80% [12.56, 19.13] | 65.2% | 0 | 62.7 kW | 99.92% |
| 1.0× | 34.58% [30.75, 38.38] | 71.9% | 0 | 66.8 kW | 99.91% |
| 1.3× | 53.08% [49.90, 56.06] | 76.7% | 0 | 73.3 kW | 99.89% |
| 1.6× | 64.98% [62.99, 66.91] | 80.2% | 0 | 67.6 kW | 99.93% |
| 2.0× | 73.67% [72.07, 75.14] | 83.3% | 0 | 72.2 kW | 99.92% |
| 2.5× | 80.24% [79.24, 81.17] | 86.0% | 0 | 80.3 kW | 99.94% |

At every level, DNS differs between AFAP, Round Robin and the RL model by
at most 2.6 points. Nearly all of it is rejected energy (7–1,094 kWh/day),
not shortfall on the EVs that were served (0.05–4.3 kWh/day). **Ports, not
the control policy or the transformer, set demand not served.**

The policy shapes peak power, where AFAP and the RL model break first:
- *AFAP*'s P95 peak is 133–208 kW over the sweep, with overload in 11–44
  of 50 seeds.
- *The RL model*'s P95 peak is 138–155 kW, with overload in 11–26 seeds
  (3.0–7.8 kWh/day).
- *Round Robin* never overloads; its P95 peak is at most 80.3 kW
  (CI ≤ 82.6) up to 2.5×.

The RL model therefore breaks earlier than Round Robin, on the
transformer criterion. Satisfaction of the served EVs never falls below
99.5% for any arm. As the Checkpoint B finding explains, it is not the
binding metric.

**C2 — what closes the gap.** The options were tested at the breaking
level (0.733×) and, as a labelled addition, at 1.0×, for AFAP and Round
Robin. The RL policy's observation and action spaces are fixed at 8 ports,
so it is excluded, as declared.

Transformer ratings come from the operator's standard list (Enel ET-013:
112.5 and 150 kVA). They were converted to kW at the CREG-derived power
factor 0.894 (`thesis_docs/sources/SOURCES_closure.md`), giving 100.6 and
134.2 kW.

**Modelling caveat.** EV2Gym draws arrivals per port, so a 10- or 12-port
station at the same spawn multiplier also faces 25% or 50% more potential
arrivals. Each port option was therefore run twice:
- *as run*, with the spawn multiplier unchanged;
- at *constant station demand*, with the spawn multiplier scaled by 8/P,
  so that only the port count changes. This is the primary reading.

(`results/closure_c2_options.csv`; censoring recomputed for each port
count.)

| Level | Option (Round Robin) | DNS [95% CI] | Δ DNS vs. 8 ports / 100 kW | Δ margin, COP/day [95% CI] | Overload | P95 peak |
|---|---|---|---|---|---|---|
| 0.733× | 8 ports, 112.5 or 150 kVA | 15.80% [12.56, 19.13] | 0 | 0 | 0 | 62.7 kW |
| 0.733× | **10 ports, 100 kW, constant demand** | **4.72% [3.04, 6.74]** | −11.1 pp [−14.2, −8.2] | +12,159 [+5,638, +18,600] | 0 | 63.2 kW |
| 0.733× | 12 ports, 100 kW, constant demand | 2.18% [1.19, 3.41] | −13.6 pp [−16.9, −10.5] | +22,413 [+14,667, +30,097] | 0 | 74.2 kW |
| 1.0× | 8 ports, 112.5 or 150 kVA | 34.58% [30.75, 38.38] | 0 | 0 | 0 | 66.8 kW |
| 1.0× | 10 ports, 100 kW, constant demand | 14.93% [12.06, 18.05] | −19.7 pp [−23.5, −15.6] | +14,625 [+7,758, +21,402] | 0 | 75.7 kW |
| 1.0× | **12 ports, 100 kW, constant demand** | **7.94% [5.64, 10.54]** | −26.6 pp [−30.7, −22.6] | +28,225 [+20,593, +35,721] | 0 | 75.8 kW |

Margins are at the Bogotá prices of 05 S5.1: 1,450 retail minus the
865.76 Enel cost. The as-run variants reduce DNS less, by 4.8–7.3 points,
because they also add demand. Their margin gains are larger (+24,225 to
+56,417 COP/day) because they serve that extra demand. Both are in the
table file.

- **A larger transformer does nothing for Round Robin.** Its peak never
  reaches 100 kW at 8 ports, so 112.5 and 150 kVA leave its energy, DNS
  and margin identical (to the cent).
- **A larger transformer only reduces AFAP's overload.** At 150 kVA
  (134.2 kW) AFAP's overload falls from 5.74 to 1.20 kWh/day at 0.733×,
  and from 14.22 to 3.78 at 1.0×. It is not eliminated.
- **AFAP's overload grows with more ports.** At 1.0× and constant demand,
  12 ports reach 22.27 kWh/day, overloading in 37 of 50 seeds.
- **Round Robin on 12 ports stays within the 100 kW unit.** Its P95 peak
  is 75.8 kW at 1.0×.

**The trade-off, restated.** In this range the binding constraint is the
port count:
- Round Robin removes the transformer constraint at no change in demand
  served.
- Unmanaged charging adds a second constraint, the transformer, which
  ports alone make worse.

### C3 — Guideline per growth level (8-port, 100 kW reference station; Round Robin)

- **Up to 0.5× the Week 1 demand:** the reference design meets every
  target:
  - zero overload;
  - DNS 4.1% [2.6, 5.8];
  - served-EV satisfaction 99.96%.

  Unmanaged charging would already need about 150 kVA (P95 133 kW at
  pf 0.894).
- **At 0.733×:** keep the 100 kW transformer and Round Robin, and **add 2
  ports (10 in total)**. At the same demand this brings DNS from 15.8% to
  4.7% [3.0, 6.7] and earns +12,159 COP/day [+5,638, +18,600]. A larger
  transformer does not help.
- **At 1.0× (the Week 1 sizing):** keep the 100 kW transformer and Round
  Robin, and **go to 12 ports**. DNS falls to 7.9% [5.6, 10.5], with
  +28,225 COP/day [+20,593, +35,721] and the P95 peak still 75.8 kW.
  10 ports are not enough (CI up to 18.1%).
- **At 1.3×, 1.6×, 2.0× and 2.5×:** the transformer guideline is
  unchanged. Round Robin keeps the 100 kW unit, with zero overload and a
  P95 peak of at most 80 kW. The port count needed for DNS < 15% was **not
  simulated** above 12 ports, and is not stated. With 8 ports, DNS is
  53–80% at these levels. The C2 trend says that more than 12 ports are
  needed, but how many is not established.
- **At every level:** unmanaged charging needs a larger transformer. The
  next standard size is 225 kVA for the 1.0–1.6× P95 peak (Guideline 1),
  and even 150 kVA does not remove its overload. Round Robin needs none.

### Guideline 3 — Voltage compliance (framed strictly by S6.2)

Station-attributable effect, measured as each arm minus the idle-station
run of the same cell (`results/week7_voltage_attribution.csv`):

| Setting | Idle feeder out of band | Round Robin: added out-of-band samples per day | Round Robin: Δ min voltage (p.u.) | AFAP: added samples | AFAP: Δ min voltage (p.u.) |
|---|---:|---|---|---|---|
| base | 78/100 cells | 2.71 [2.23, 3.24] | −0.00053 [−0.00061, −0.00046] | 3.51 [2.92, 4.11] | −0.00084 [−0.00102, −0.00067] |
| spawn 1.3× | 84/100 | 4.01 [3.43, 4.59] | −0.00073 [−0.00082, −0.00064] | 4.23 [3.47, 5.00] | −0.00097 [−0.00116, −0.00079] |
| spawn 1.6× | 86/100 | 4.08 [3.46, 4.71] | −0.00079 [−0.00089, −0.00070] | 4.26 [3.56, 5.02] | −0.00103 [−0.00120, −0.00085] |
| load 1.3 | 100/100 | 4.19 [3.65, 4.74] | −0.00054 [−0.00062, −0.00047] | 4.33 [3.78, 4.92] | −0.00089 [−0.00107, −0.00072] |
| load 1.6 | 100/100 | 4.09 [3.55, 4.66] | −0.00057 [−0.00065, −0.00050] | 4.20 [3.64, 4.81] | −0.00093 [−0.00111, −0.00075] |

**Read strictly.**
1. **The feeder fails the ±5% band at bus 27 by itself.** With the station
   idle, this happens in 78–86% of cells at nominal load and in 100% at
   1.3–1.6× load. The worst feeder voltage is 0.9275 p.u. at base and
   0.8783 p.u. at load 1.6. **No compliance claim of any kind is made for
   this feeder.**
2. **The station's own contribution is small but real.** Every arm adds
   about 2.7–4.5 out-of-band (bus, step) samples per day, all CIs exclude
   zero, and every arm lowers the minimum voltage by 0.0004–0.0010 p.u.
3. **Smart charging reduces the station's voltage impact relative to
   unmanaged charging.** Round Robin's drop in minimum voltage is 37% smaller
   than AFAP's at base (−0.00053 against −0.00084 p.u.), and the CIs do not
   overlap at any setting. The final RL model lies near AFAP (−0.00077 at
   base). MPC and the oracle lie lower still.
4. **No arm meets the strict target** that the station adds no out-of-band
   sample in any cell. This target cannot be met on a feeder that already
   sits at the band edge (`results/week7_target_compliance.csv`).

**Closure (2026-10-06, brief E2–E3): a feeder that is in band, and what "37%" means.**

*E2 — feeder screen.* Every feeder shipped with EV2Gym was probed with the
station idle at nominal load (load multiplier 1.0, PV 80%, no parameter
tuned), with the station on the electrically farthest bus
(`results/closure_feeder_probe_summary.csv`):
- *node_34* is out of band, as S6.2 found.
- *node_25 and node_69* cannot run as shipped. Their bus files have no
  PD/QD nominal loads, so EV2Gym's power flow cannot be built, and none
  was invented.
- **node_123** (EV2Gym's 123-bus network, station on bus
  115) is **inside the ±5% band in all
  20 idle cells** (lowest 0.9738 p.u.).

Following the brief, AFAP and Round Robin were rerun on node_123 at 1.0,
1.3 and 1.6× demand, with 50 seeds (`scripts/closure_ieee123_voltage.py`,
`results/closure_ieee123_voltage.csv`).

**Weekday only (labelled scope reduction).** EV2Gym's background-load
generator (`data_augment.py::sample_data`) redraws a full 123-bus profile
inside `while True` until no value is NaN. On the weekend evaluation day,
a single environment build ran for more than 240 s without finishing.
Making it terminate would mean changing EV2Gym's load model, which this
project does not do. n_clusters = 50.

| Demand | AFAP: cells out of band | AFAP: lowest bus V (p.u.) | AFAP: drop in feeder min. V vs. idle (p.u.) | Round Robin: cells out of band | Round Robin: lowest bus V | Round Robin: drop vs. idle | Round Robin's reduction of the drop |
|---|---|---|---|---|---|---|---|
| 1× | 0/50 | 0.9736 | -0.00009 [-0.00011, -0.00007] | 0/50 | 0.9737 | -0.00006 [-0.00006, -0.00005] | 39.2% [18.6, 53.7] |
| 1.3× | 0/50 | 0.9720 | -0.00011 [-0.00014, -0.00008] | 0/50 | 0.9722 | -0.00007 [-0.00008, -0.00006] | 36.6% [14.6, 51.7] |
| 1.6× | 0/50 | 0.9728 | -0.00011 [-0.00014, -0.00009] | 0/50 | 0.9728 | -0.00008 [-0.00010, -0.00007] | 24.5% [4.3, 39.2] |

The idle feeder is out of band in 0 of 50 weekday cells. Across
the station-on runs, 0 cells leave the band, and the lowest bus
voltage of any run is 0.9720 p.u.
**Neither AFAP nor Round Robin pushes this in-band feeder out of the ±5% band at any demand level.** On this feeder, therefore, RETIE ±5% compliance is evaluable, and it is met for both strategies up to 1.6×.
This is a statement about EV2Gym's 123-bus test network, not about any
Colombian operator's feeder.

The idle baseline is matched per level as well as per seed and day.
EV2Gym draws the EV population from the same random stream before it
samples the feeder's background load (`ev2gym_env.py`, lines 252, 294 and
316). A different demand level therefore changes the background-load draw
of the same cell. A first analysis shared one idle run across levels and
was corrected; Week 7's per-setting baseline already did this.

On this stronger feeder, the station's own effect is about a tenth of
that on the 34-node feeder: about 0.0001 against 0.0008 p.u. Round
Robin's relative reduction of it is nevertheless of the same size:
39.2% [18.6, 53.7] at 1.0×, falling to 24.5% at 1.6×. This independently
corroborates the 34-node result below.

*E3 — the "37%".* The quantity is the per-run drop in the **feeder-wide
daily minimum voltage** (the minimum over all buses and steps) relative to
the idle-station run of the same cell. The 37% is Round Robin's reduction
of that drop against AFAP, as a ratio of means over the 100 paired base
runs (`scripts/closure_voltage_contribution.py`):
- on the 34-node feeder it is
  **36.4% [22.3, 47.0]**;
- the paired difference is +0.00030 p.u.
  [+0.00015, +0.00046], with
  n_clusters = 50;
- the lowest-voltage bus is the station's own bus 27 in all 100 AFAP
  runs.

The figure holds at the base setting only. At 1.3× and 1.6× demand the
reduction is 24.7% and
22.7%. The "37%" is
kept, and is stated with this definition wherever it appears.

**Guideline.** Before siting a public DC station on a weak, already
low-voltage bus, the operator's study must start from the feeder's own
voltage profile. On this feeder the station is not the cause of the
violation, but it deepens it slightly. A charging schedule that flattens
the station's peak (Round Robin) reduces that contribution by about a
third compared with unmanaged charging. That rests on the simulator's
feeder, not a Colombian one (S6.1).

### Guideline 4 — Connectors (Res. 40223 de 2021, Art. 4)

The resolution requires the following:
- **at least one Tipo 1 (SAE J1772) connector** on every Level 2 and Level 3
  AC station;
- **at least one CCS Combo 1 connector** on every Level 3 DC station.

This is a minimum, not an exclusive standard, and the resolution does not
mention CCS Combo 2. The reference station's CCS2-only DC configuration,
chosen on market-practice grounds (01 §1.1), **would not by itself satisfy
Art. 4**. A compliant design adds at least one CCS Combo 1 connector to the
DC equipment. CCS2 may remain alongside it, because the mandate is a
minimum. EV2Gym has no connector state, so this guideline has no effect
on, and draws no support from, any simulated quantity.

### Guideline 5 — Economic frame

Under the flat tariff, margin is proportional to energy delivered (05
S5.1; 07 S7.3). Each guideline's cost is the margin conceded against AFAP
at the same growth level, in Bogotá prices (`results/week7_grid_margin_bogota.csv`).
Round Robin concedes:

| Demand | Margin conceded (COP/day) | 95% CI | Share of AFAP margin |
|---|---:|---|---:|
| 1.0× | 551.9 | [274.3, 874.2] | 0.47% |
| 1.3× | 800.0 | [472.3, 1,176.4] | 0.61% |
| 1.6× | 556.1 | [261.4, 921.2] | 0.40% |

MPC_TrackingG2V concedes 571.8–683.4 and the final RL model 1,248–2,470.
The Axis 2 settings are identical to base.

**The cost of keeping the 100 kW transformer, rather than buying a
225 kVA unit for unmanaged charging, is under 1% of daily margin at every
demand level studied.** The capital cost of the larger transformer is not
in this project's data and is not estimated.

### Guideline 6 — RL under growth

The final RL model against Round Robin, at the same setting
(`results/week7_grid_vs_roundrobin.csv`):

| Demand | Tracking error (RL − RR) | Overload, kWh/day (RL − RR) | Average satisfaction (RL − RR) |
|---|---|---|---|
| 1.0× | +27,614 [+25,309, +29,960] | +3.58 [+1.71, +5.71] | −0.32 pp [−0.51, −0.16] |
| 1.3× | +32,353 [+29,939, +34,918] | +4.17 [+2.14, +6.45] | −0.18 pp [−0.33, −0.04] |
| 1.6× | +33,440 [+30,922, +36,077] | +7.37 [+4.44, +10.59] | −0.09 pp [−0.21, 0.00] |

The RL policy was trained at the base demand. **As demand grows, its
overload grows** (+3.79 kWh/day from 1.0× to 1.6×, CI [+0.10, +7.59]), and
its satisfaction gap to Round Robin narrows. Round Robin remains better on
tracking and overload at every level. Nothing in the data suggests that
the RL model would close the gap at higher demand.

### Guideline 7 — Target compliance under growth

*Closure update (2026-10-06): the final compliance table at the reference
demand.* It uses 1.0×, 100 runs and n_clusters = 50
(`results/closure_target_compliance.csv`), and supersedes the two
satisfaction/ENS rows below as statements about the station's users.

How the targets are read:
- *Served EVs* is the old reading. *Counting rejected arrivals* scores
  each rejected arrival as satisfaction 0.
- Demand not served is the lower bound.
- Voltage is evaluated on node_123 (in band when idle), weekday only, for
  the two arms rerun there. On the 34-node feeder it stays not
  evaluable.

| Arm | Satisfaction > 90%, served EVs | Satisfaction > 90%, counting rejected arrivals | ENS_rel < 15%, served EVs | Demand not served < 15% | Transformer within 100 kW | Voltage ±5% |
|---|---|---|---|---|---|---|
| ChargeAsFastAsPossible | met (100.00% CI low) | **not met** (64.6%) | met (0.00% CI high) | **not met** (34.3%, CI high 38.1%) | **not met** (35/100 cells overload) | met on node_123 |
| RoundRobin | met (99.85% CI low) | **not met** (64.6%) | met (0.75% CI high) | **not met** (34.6%, CI high 38.4%) | met (0/100 cells overload) | met on node_123 |
| MPC_TrackingG2V | met (100.00% CI low) | **not met** (64.6%) | met (0.52% CI high) | **not met** (34.6%, CI high 38.4%) | met (0/100 cells overload) | not evaluable |
| TD3_vanilla_extended_ts102 | met (99.36% CI low) | **not met** (64.3%) | met (3.32% CI high) | **not met** (35.8%, CI high 39.5%) | **not met** (18/100 cells overload) | not evaluable |
| Optimal_Oracle_Tracking | met (100.00% CI low) | **not met** (64.6%) | met (0.52% CI high) | **not met** (34.6%, CI high 38.4%) | met (0/100 cells overload) | not evaluable |

The table below is the original Week 7 table, kept for the record. Its
first two rows are superseded by the table above.


`results/week7_target_compliance.csv`; CI-based tests with n_clusters = 50.

| Target | Result |
|---|---|
| Average satisfaction > 90% (CI lower bound) | **Met by all 5 arms at all 5 settings.** Lowest arm: final RL at 99.36%. *(Served EVs only; superseded on demand not served, see the closure table above.)* |
| `ENS_rel` < 15% (CI upper bound) | **Met by all 5 arms at all 5 settings.** Highest CI upper bound: final RL at 3.32%; Round Robin ≤ 0.92%. *(Served EVs only; superseded on demand not served, see the closure table above.)* |
| Voltage (±5% band) | **Not assessable as compliance on this feeder** (Guideline 3). The feeder is out of band with the station idle. As an increment, every arm adds out-of-band samples in 70–94 of 100 cells, and Round Robin adds the smallest voltage depth among the causal arms. |

## S6.5 Answer to Objective 4

*Rewritten 2026-10-06 (closure brief, Checkpoint B rule).* The earlier
answer said that Round Robin removes the overload "with no loss of user
satisfaction, up to 1.6×". That claim is withdrawn as a statement about
the station's users. The satisfaction figure covers only the EVs that
obtained a port.

For a public 8-port DC station with a 100 kW transformer:

1. **Control: Round Robin is the guideline.** It is the deployable
   strategy that keeps the 100 kW transformer within its rating with zero
   overload, up to 2.5× the reference demand (P95 peak ≤ 80 kW). Its cost
   is under 1% of daily margin against unmanaged charging. Unmanaged
   charging, and the final RL model, exceed 100 kW already at 0.5×.
   Unmanaged charging would need a 225 kVA unit (ET-013 standard size, at
   pf 0.894 or 1.0).
2. **Capacity: the binding constraint is ports, not the transformer.**
   EV2Gym turns away arrivals at a full station. At the Week 1 demand,
   34.6% [30.8, 38.4] of the requested energy goes unserved with 8 ports,
   whatever the control. The rule per growth level is in Guideline 2 / C3:
   - up to 0.5×: the reference design;
   - 0.733×: 10 ports;
   - 1.0×: 12 ports;
   - above 1.0×: more ports, in a number not simulated.

   The 100 kW transformer with Round Robin remains sufficient in every
   case tested.
3. **Voltage.**
   - On EV2Gym's 34-node feeder, which is out of band at the station bus
     even with the station idle, Round Robin lowers the feeder's daily
     minimum voltage 36.4% [22.3, 47.0] less than AFAP at the base demand
     (22.7–24.7% at 1.3–1.6×). No compliance claim is made there.
   - On the 123-bus feeder shipped with EV2Gym, which is in band when
     idle, the lowest bus voltage across AFAP and Round Robin at 1.0–1.6×
     is 0.9720 p.u.; 0 cells leave the band.
     This was run on the weekday only. On that test network, the ±5%
     band is therefore met.
4. **Connectors.** The DC equipment must include CCS Combo 1 under
   Res. 40223 de 2021, Art. 4.

These guidelines are **conditional**:
- on the simulator's feeders, which are test networks, not a Colombian
  operator's feeder;
- on EV2Gym having no feedback from the feeder to the station;
- on the Dutch arrival data and EV2Gym's per-port arrival model;
- on demand stated relative to the Week 1 sizing, with no city mapped
  onto that axis (07 S7.8).
