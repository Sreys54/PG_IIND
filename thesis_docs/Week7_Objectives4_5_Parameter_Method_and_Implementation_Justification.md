# Week 7 (Objectives 4 and 5) — Parameter, Method, and Implementation Justification: Grid-Enabled Infrastructure Guidelines and Replicability in Medellín

**Status: complete (2026-10-06), run unattended overnight on branch
`semana-7`; nothing committed.** This document follows the Week 5 and
Week 6 Part 0 mechanism: a Markdown record rendered to `.docx` by
`scripts/render_docx.py`, with plain black text, bold section titles and no
Word Heading styles. The night's decision log is
`thesis_docs/overnight_report.md`.

## Headline Results Summary

**Objective 4 — answer.** For the reference public station (8 DC ports,
100 kW transformer) on EV2Gym's 34-node feeder, **smart charging (Round
Robin) is the infrastructure guideline**.

**Growth in station demand up to 1.6×:**
- Round Robin keeps **zero transformer overload in all 50 seeds** at every
  level, with a 95th-percentile peak of 67–73 kW.
- User satisfaction is unchanged: 99.89–99.93%, and the change against
  base has a CI that includes zero.
  **Withdrawn 2026-10-06 (closure brief, Checkpoint B):** this is satisfaction
  of the EVs that obtained a port only. EV2Gym silently drops arrivals at
  occupied ports, so demand not served (rejected + shortfall, lower bound)
  is 34.6% [30.8, 38.4] for Round Robin at 1.0× and 65.0% [63.0, 66.9] at
  1.6×, n_clusters = 50. The station is port-limited at the reference
  demand. See `Closure_Parameter_Method_and_Implementation_Justification`.
- It delivers +37.3 kWh/day [+30.9, +44.1] more energy at 1.6×.
- Unmanaged charging (AFAP) overloads the transformer in 28–42 of 50 seeds
  (14.2–26.4 kWh/day). It would need a transformer of about 173–192 kW for
  the 95th-percentile scenario, which is the next standard size of
  **225 kVA**.
- The cost of keeping the 100 kW unit with Round Robin is **552–800
  COP/day of margin against AFAP, under 1%**.

**Voltage:**
- The simulated feeder **is already outside the ±5% band at the station's
  bus with the station idle**: 78–100% of cells. No RETIE compliance claim
  is made.
- The station's own contribution is small but significant: 2.7–4.5 extra
  out-of-band samples per day.
- Round Robin reduces the station's depression of the minimum voltage by
  37% against AFAP: −0.00053 against −0.00084 p.u., with CIs that do not
  overlap.

**Other results:**
- Raising the feeder's background load changes nothing at the station,
  because EV2Gym has no feeder-to-station feedback.
- The satisfaction > 90% and `ENS_rel` < 15% targets are **met by every arm
  at every setting**.
  **Withdrawn in part 2026-10-06:** both targets cover spawned EVs only.
  On demand not served, every arm fails the 15% target at every setting.
- The final RL model stays worse than Round Robin on tracking error and
  overload at every growth level. Its overload grows with demand: +3.79
  kWh/day from 1.0× to 1.6×.
- **Connectors:** a CCS2-only DC station does not satisfy Res. 40223 de
  2021 Art. 4. At least one CCS Combo 1 connector is required.

**Objective 5 — answer (Medellín).**
- **The economic layer transfers immediately.** EPM's September 2026
  Nivel II commercial CU (923.92 COP/kWh with contribution, Punta) passes
  both Week 5 invariants, and its intraday spread is 0.69%.
- **The strategy ranking is tariff-invariant.** It is identical across 6
  datasets × 8 price scenarios under a flat price.
- **The relative cost of the transformer limit transfers exactly.** Round
  Robin concedes 497.0 COP/day in Medellín against 551.9 in Bogotá, a
  constant ratio of 0.900, or 0.47% of margin in both.
- **The physical layer is conditional, not established.** Arrivals,
  per-station demand, the feeder and the climate are unavailable for
  Medellín, as they are for Bogotá; the Dutch stand-ins are kept in both.
- **EPM publishes no EV charging price**, so Medellín's absolute margin is
  a sensitivity, not a claim.
- **No source defends a per-station demand mapping.** City registrations
  give Medellín/Bogotá = 0.40, and both naive mappings fall below the 1.0×
  lower end of the studied range, so lower-demand runs are proposed, not
  run.

**Integrity:**
- The grid-enabled model reproduces every non-grid station metric exactly
  (500 cells × 5 arms, maximum difference 0.0).
- The registry gained one authorized column (`simulate_grid`), with every
  prior value verified unchanged.
- 2,500 analysis rows and 200 probe rows were appended.

## Part 1 — Parameters and Methods

| Parameter / decision | Value | Label | Justification |
|---|---|---|---|
| Final RL model | `TD3_vanilla` extended, training seed 102, primary checkpoint at 850,000 steps | Validated | The author's fixed decision (2026-10-05), recorded in S5.11, the Part 0 handback, the Progress Log and `CLAUDE.md`. Its frozen VecNormalize statistics are loaded with `training=False`. |
| Branch | `semana-7`, from `main` at `ebf3634` | Validated | `main` = `semana-6` = `origin/*` were verified identical before branching (Checkpoint 0). |
| Grid config | `station_v0_bogota_grid.yaml`, which differs from the Week 1–5 config only in `simulate_grid`, `number_of_transformers`, `load_multiplier` and the station bus | Validated | The printed diff contains only those keys, pinned by a test. Equivalence is 0.0 difference on all station metrics: 40 cells (1b) and 500 cells × 5 arms (base setting, full grid). |
| Station placement | All 8 stations on bus 27 (transformer id 25), through `ev2gym_thesis/grid/placement.py` | Simplification | EV2Gym has no placement key, and would otherwise spread the stations over 8 buses with 800 kW of transformers. Bus 27 is the electrically farthest bus, the conservative choice for voltage. |
| Feeder | EV2Gym 34-node (RL-ADN) feeder, Laurent power flow, `pv_scale` 80 | Simplification | The library's only feeder of this size. Not validated against the IEEE data, and no Enel or EPM feeder is public. |
| 1b tolerance | ≤ 1e-6 absolute, stated before running | Empirically set | The station model is identical by construction, so floating-point noise is the only legitimate difference. Result: 0.0. |
| Voltage band | 0.95–1.05 p.u. (±5%), EV2Gym's hard-coded band, independently recomputed by `band_check` | Validated | Read from source and matched exactly on 200 probe rows. Equal to the thesis's adopted band. |
| Voltage compliance definition | Station increment over the idle-station (zero-charging) run of the same cell | Empirically set | The feeder alone is outside the band at bus 27 in 15 of 20 probe cells at nominal load, so absolute compliance would measure the feeder, not the station. |
| Voltage probe | AFAP and RR, seeds 0–9 × 2 days, `load_multiplier` 0.5 / 0.7 / 0.8 / 0.9 / 1.0, `analysis_row = False` | Validated | The smallest tripping setting is 0.8. Probe rows are kept out of every statistic. |
| Oracle variant | `Optimal_Oracle_Tracking` | Empirically set | The variant S5.6's tracking optimality gap used; its objective matches the tracking target. |
| Arms | AFAP, Round Robin, MPC_TrackingG2V, final RL, Optimal_Oracle_Tracking | Validated | Fixed by the brief. The two non-causal arms are bounds, not candidates. |
| Growth axes | Axis 1: `spawn_multiplier` 30 / 39 / 48. Axis 2: `load_multiplier` 1.0 / 1.3 / 1.6 | Empirically set | One axis at a time, not a cross product, as the brief specifies: 5 distinct settings. |
| Seed count | 50 seeds × 2 day types per setting | Validated | Checkpoint 1 rule: 16.3 s per (setting, seed, day) gives 2.3 h serial, or 2.8 h with a 25% margin, ending before 07:00. Run on 3 workers. |
| Registry grid flag | New last column `simulate_grid`; `False` for all 3,153 prior rows, then `True` for the one Week 2 grid smoke-test row | Validated | The one new column the brief authorized. Every prior raw line was verified to change only by a trailing field, and exactly one line for the smoke-test correction. |
| Parallel safety | Per-process day-config and oracle-replay directories | Validated | A shared-directory race crashed one worker. The fix leaves file contents byte-identical, and the full-grid base equivalence (0.0) rules out corrupted reads. |
| Transformer sizing statistic | 95th percentile over 50 seeds of the per-seed peak station power, plus the next standard kVA size at unity power factor | Simplification | Valid for AFAP, whose peak ignores the rating. With n = 50 the tail rests on 2–3 seeds, so the result is directional. |
| Economics (Bogotá) | Retail 1,450 COP/kWh; CU 865.7615 COP/kWh | Validated | Week 5 constants, unchanged. |
| City for Objective 5 | Medellín (EPM) | Empirically set | Categoría especial, with a monthly CREG-format tariff sheet available, so the Week 5 invariants apply unchanged. Cali was not needed. |
| Medellín cost | 923.92 COP/kWh (EPM, Sep 2026, Nivel II commercial, with contribution, Punta); sensitivities 917.58 and 920.76 | Validated | Both Week 5 invariants pass on Punta and on Fuera de Punta (the latter at the inclusive 0.01 bound). The higher validated rate was taken, so margins are lower bounds. |
| Medellín retail | 1,450 COP/kWh (Bogotá value) as a labelled sensitivity | Simplification | EPM publishes no EV charging price (negative result). No competitor price is substituted, per the pairing rule. |
| Intraday spread | Medellín 0.69%, Bogotá 1.57% | Validated | Below Bogotá's, so no price-signal simulation (Checkpoint 2 rule). |
| Ranking invariance | Margin ranking = energy ranking under 8 price scenarios, per dataset | Validated | Asserted in code and pinned by a test. Under a flat price, margin = energy × (retail − cost). |
| Demand mapping | Not mapped; guidelines conditional on demand | Simplification | City EV registrations (0.40) do not give per-station demand. Both naive mappings fall below 1.0×, so 0.4×–0.9× runs are proposed and not run. |
| Limitations list | `08_limitations.md`, new consolidated chapter | Simplification | No consolidated list existed. Chapters keep their own sections, with pointers. |
| Week 5 margin figure | 503.9 corrected to 551.9 COP/day (S5.8 correction note) | Validated | The 503.9 came from a stale pre-Gate-4 CSV; 551.9 was recomputed with Week 5's own loader on the current analysis rows. |

## Part 2 — Implementation

### `ev2gym_thesis/grid/placement.py` (new)

**Purpose:** wraps the `load_grid` name that `ev2gym_env.py` imported,
from outside the library. After EV2Gym's own `load_grid` runs, it
reassigns every station to the transformer of
`network_info.thesis_station_bus`. A grid environment without that key
raises an error instead of silently spreading the stations.
`electrical_distance()` ranks buses by series path impedance and is used to
justify bus 27.

### `ev2gym_thesis/grid/voltage.py` (new)

**Purpose:** documents, from the source, what EV2Gym's three voltage
statistics measure. `band_check()` independently recomputes the ±5% check
on the raw per-bus array (out-of-band samples, out-of-band steps, minimum
voltage, worst bus, excursion, and station-bus values). It matches the
library exactly.

### `scripts/migrate_registry_schema_week7.py` (new) and `ev2gym_thesis/registry.py` (extended)

**Purpose:** adds the authorized `simulate_grid` column as the last column
and verifies every prior value against a backup. `--fix-smoke-test-flag`
corrects the one Week 2 grid row. `append_runs` defaults the flag to
`False` for pre-Week-7 writers and refuses a grid-config row that does not
declare it.

### `scripts/week7_grid_equivalence.py`, `scripts/week7_voltage_probe.py`, `scripts/week7_zero_charging_baseline.py` (new)

**Purpose:** Steps 1b and 1d, plus the idle-station voltage baseline for
all 500 Step 2 cells. They use the real heuristic row builder and
`band_check`. The tolerance is written in the docstring before the first
run.

### `scripts/run_week7_grid.py` and `scripts/run_week7_worker.cmd` (new)

**Purpose:** the Step 2 grid. It reuses the real row builders of
`backfill_registry`, `evaluate_mpc`, `evaluate_oracle` and `evaluate_rl`;
the last three read a module-level config constant, which is redirected
only for the duration of one call. Each cell's voltage is captured through
a wrapper on the `get_statistics` name. Workers write shards and resume
from them, and `--merge` appends to the registry once. Per-process
day-config and replay directories prevent the shared-file race.
`--timing` produced Step 1e.

### `scripts/analyze_week7_infra.py` (new) and `scripts/analyze_week5_results.py` (extended)

**Purpose:** Objective 4 statistics, each with its cluster bootstrap and
`n_clusters`:
- base equivalence over all arms;
- master comparison per setting;
- arms against Round Robin;
- growth effects against base;
- ENS compliance;
- transformer sizing from the saved timeseries;
- station-attributable voltage;
- margin;
- target compliance.

Week 5's `ens_and_compliance` / `requested_energy_by_cell` gained a
`config_path` argument; the default reproduces Week 5.

### `ev2gym_thesis/prices/medellin.py` (new) and `scripts/analyze_week7_replicability.py` (new)

**Purpose:** EPM sheet parser, invariant checks, Medellín constants with
their declared origins, tariff transfer on registry energy under 8 price
scenarios, ranking-invariance assertion, transferability classification
and demand mapping.

### `scripts/make_figures.py` and `ev2gym_thesis/figures.py` (extended)

**Purpose:** f15 (growth, 2 axes × 4 metrics), f16 (transformer sizing),
f17 (station-attributable voltage) and f18 (two-city margin), following the
f13/f14 conventions. All were visually checked and their fixes are logged.
`--only` regenerates only the named figures.

### `scripts/export_week7_results_xlsx.py` (new) and `ev2gym_thesis/xlsx_export.py` (one constant)

**Purpose:** one formatted workbook per Week 7 table, with every header
unit-labelled. `PER_UNIT_VOLTAGE_FORMAT` was added for p.u. values.

### `scripts/extend_progress_log.py` (extended) and `scripts/build_deliverables_index.py` (new)

**Purpose:** Progress Log sections 13 (Objective 4) and 14 (Objective 5),
extend only. The deliverables index for Weeks 1–7 is generated from the
file system.

### Tests: `ev2gym_thesis/tests/test_week6_infra.py`, `test_replicability.py` (new); `test_week5.py` (unchanged)

**Purpose:** pins on the following:
- the config diff, the placement and the 100 kW limit;
- refusal without a station bus;
- the equivalence table;
- step-by-step RL observation identity and frozen statistics;
- the library band and `band_check`;
- the probe threshold;
- the registry flag and probe rows;
- the grid row count;
- the cluster-bootstrap `n_clusters`;
- the EPM invariants on the stored PDF;
- invariant failure detection, ranking invariance, the two-city ratio and
  the source files.
