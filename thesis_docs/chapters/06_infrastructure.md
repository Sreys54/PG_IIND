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
the voltage results (S6.5). This is a property of the simulator, not a
finding about real feeders. It is declared as a limitation: a real feeder
operator could curtail, and a real transformer shared with other customers
would see their load.

### Guideline 1 — Transformer sizing

Per-seed overload and peak station power over 50 seeds
(`results/week7_transformer_sizing.csv`):

| Setting | Arm | Seeds with overload | Overload P50 / P95 / max (kWh/day) | Peak P50 / P95 / max (kW) | Next standard size for the P95 peak |
|---|---|---:|---|---|---:|
| base | AFAP | 28/50 | 10.32 / 44.88 / 78.63 | 116.2 / 172.7 / 220.8 | 225 kVA |
| spawn 1.3× | AFAP | 42/50 | 21.20 / 69.78 / 91.23 | 132.0 / 191.9 / 220.8 | 225 kVA |
| spawn 1.6× | AFAP | 39/50 | 25.09 / 61.45 / 83.13 | 134.6 / 189.1 / 204.7 | 225 kVA |
| base / 1.3× / 1.6× | Round Robin | 0/50 | 0 | P95 66.8 / 73.3 / 67.6 | within 100 kW |
| base / 1.3× / 1.6× | TD3 extended s102 | 16 / 16 / 26 of 50 | P95 22.14 / 23.01 / 28.82 | P95 144.3 / 144.5 / 145.9 | 150 kVA |

MPC and the oracle never overload (P95 peaks 51–61 kW). AFAP's peak does
not respond to the transformer rating, so its 95th-percentile peak is a
valid sizing number. **Unmanaged (AFAP) charging would need a transformer
of about 173–192 kW for the 95th-percentile scenario to stop
overloading.** That is the next standard size of **225 kVA** at unity power
factor, against the installed 100 kW, and it holds across 1.0–1.6× demand.

**With Round Robin, the installed 100 kW transformer is sufficient up to
1.6× the reference demand.** There is zero overload in every seed, and the
95th-percentile peak is 67–73 kW.

**Tail support:** the 95th percentile of 50 seeds rests on 3 seeds above
it in every row. This is a **directional** sizing result, not an estimate
of the tail of the demand distribution.

### Guideline 2 — Capacity and ports

The brief asked for the Axis 1 point at which Round Robin's satisfaction
falls below 90%. **That point is not reached within 1.0–1.6×.**

| Demand | Round Robin average satisfaction | Change vs. base |
|---|---|---|
| 1.0× | 99.91% [99.85, 99.96] | — |
| 1.3× | 99.89% [99.83, 99.94] | −0.02 pp [−0.08, +0.04] |
| 1.6× | 99.93% [99.88, 99.97] | +0.02 pp [−0.02, +0.07] |

Energy delivered, by contrast, grows by +22.1 kWh/day [+17.2, +27.1] at
1.3× and +37.3 [+30.9, +44.1] at 1.6×, and EVs served by +2.15 [+1.83,
+2.48] at 1.6×.

**The trade-off.** In this range, user satisfaction is not the binding
constraint. **Transformer overload is**, and only for unmanaged charging:
AFAP overloads in 28–42 of 50 seeds. Two options close the overload gap:
- **a larger transformer**, with the next standard size of 225 kVA for
  AFAP (Guideline 1);
- **smart-charging headroom**, with Round Robin on the existing 100 kW and
  zero overload. Its cost is 552–800 COP/day of margin against AFAP
  (Guideline 5).

**More DC ports** were not simulated (the port count is fixed at 8 in every
setting), so this chapter makes no claim about them. Within 1.6×, nothing
in the data indicates that the 8 ports are the bottleneck for the
satisfaction target.

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

`results/week7_target_compliance.csv`; CI-based tests with n_clusters = 50.

| Target | Result |
|---|---|
| Average satisfaction > 90% (CI lower bound) | **Met by all 5 arms at all 5 settings.** Lowest arm: final RL at 99.36%. |
| `ENS_rel` < 15% (CI upper bound) | **Met by all 5 arms at all 5 settings.** Highest CI upper bound: final RL at 3.32%; Round Robin ≤ 0.92%. |
| Voltage (±5% band) | **Not assessable as compliance on this feeder** (Guideline 3). The feeder is out of band with the station idle. As an increment, every arm adds out-of-band samples in 70–94 of 100 cells, and Round Robin adds the smallest voltage depth among the causal arms. |

## S6.5 Answer to Objective 4

For a public 8-port DC station with a 100 kW transformer, smart charging
(Round Robin) is the infrastructure guideline. It is the deployable option
that removes the transformer overload unmanaged charging causes, with no
loss of user satisfaction, up to 1.6× the reference demand. Its cost is
under 1% of daily margin against AFAP. It avoids the 225 kVA transformer
that unmanaged charging would need at the 95th-percentile scenario, and
it reduces the station's own contribution to voltage depression by 37%
compared with AFAP (−0.00053 against −0.00084 p.u. at base). Connector equipment must include CCS Combo 1 under
Res. 40223 de 2021, Art. 4.

These guidelines are **conditional**:
- on the simulator's feeder, which is itself out of the ±5% band at the
  chosen bus, so no RETIE compliance claim is made;
- on the Dutch arrival data;
- on demand between 1.0× and 1.6× the Week 1 sizing.
