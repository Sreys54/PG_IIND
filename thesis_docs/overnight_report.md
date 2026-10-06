# Overnight Report — Final Practical Brief (Objectives 4 and 5), branch `semana-7`

## FINAL REPORT (2026-10-06, 00:50 Bogotá)

**No hard stop was triggered.** The Gurobi licence worked (every oracle and
MPC cell solved; the timing cell reached OPTIMAL), nothing in
`ev2gym/models` or `ev2gym/rl_agent` was edited, and no existing registry
value changed (verified at byte level at every write). Two authorized,
verified metadata changes were made to the registry: the new
`simulate_grid` column, and that flag's correction on the Week 2
smoke-test row.

### 1. Decision rules that fired, and what they decided

| # | Rule | Decision |
|---|---|---|
| 1 | Step 0: anything from `semana-6` missing from `main`? | **No.** `main` = `semana-6` = `ebf3634`, so `semana-7` was created from `main`. |
| 2 | Point 3: verify the trade-off claim with `total_energy_charged`; drop it if unsupported | **Partly dropped.** Energy rose (+18.6 kWh/day), but the training reward *improved* (+3,997 [+2,340, +5,790]), so "rather than reaching a better reward" was **removed** and replaced by the supported reading. |
| 3 | 1b: grid vs. non-grid divergence? | **No divergence.** 0.0 difference on every station metric (40 cells; 500 cells × 5 arms). Grid and non-grid station results are comparable. |
| 4 | 1c: RL observation space changes? | **No.** Observations are bit-identical step by step, so no adapter was needed and the RL arm stayed (5 arms). |
| 5 | 1d: voltage never trips (negative result)? | **Did not fire.** It trips from load 0.8, but the idle feeder already trips. Conservative choice (labelled): voltage reported only as the station's increment, **no RETIE compliance claim**. |
| 6 | Checkpoint 1 seed count | **50 seeds** (projection 2.3 h, 2.8 h with margin, ending before 07:00). Finished 00:17. |
| 7 | 3a: data unavailable / invariant fails → Cali | **Did not fire.** EPM September 2026 passes both invariants. |
| 8 | 3a: no published retail price → Bogotá's 1,450 as sensitivity | **Fired.** EPM publishes none, so 1,450 is a labelled sensitivity and no absolute Medellín margin claim is made. |
| 9 | Checkpoint 2: spread materially above Bogotá's 1.57%? | **No** (0.69%). No new price simulations. |
| 10 | 3d: no source supports a demand ratio → conditional guidelines | **Fired.** Guidelines are conditional on demand; 0.4–0.9× runs proposed with timing, not run. |

**Judgement calls taken conservatively (labelled assumptions):**
- station on bus 27, the most voltage-sensitive bus;
- oracle variant `Optimal_Oracle_Tracking`;
- Medellín base cost = the higher validated rate (Punta 923.92);
- new consolidated limitations chapter `08_limitations.md`;
- S5.8 corrected with a dated note rather than rewritten;
- the stale CSV `results/week5_margin_vs_overload.csv` left in place and
  flagged.

### 2. Headline answers

**Objective 4.** For the 8-port, 100 kW public DC station, **smart charging
(Round Robin) is the infrastructure guideline**:
- It keeps zero transformer overload in all 50 seeds up to 1.6× demand
  (95th-percentile peak ≤ 73 kW).
- User satisfaction is unchanged (≥ 99.89%).
- The cost is 552–800 COP/day of margin against AFAP, under 1%.
- Unmanaged charging overloads the transformer in 28–42 of 50 seeds and
  would need about 225 kVA for the 95th-percentile scenario.
- Raising the feeder's background load changes nothing at the station
  (EV2Gym has no feedback).
- The feeder at the station's bus is outside ±5% even with the station
  idle. The station's own contribution is small but significant, and Round
  Robin reduces it by 37% compared with AFAP.
- Connectors must include CCS Combo 1 (Res. 40223/2021 Art. 4).
- The final RL model remains worse than Round Robin at every growth level.

**Objective 5.** **The economic layer and the strategy recommendation
transfer to Medellín.**
- EPM's validated Nivel II CU is 923.92 COP/kWh.
- The ranking is tariff-invariant in 48/48 checks.
- The relative cost of the transformer limit is identical (0.47% of margin
  in both cities, constant ratio 0.900).
- **The physical layer is conditional, not established.** Arrivals,
  per-station demand, the feeder and the climate are the same declared
  stand-ins in both cities.
- EPM publishes no EV retail price.

### 3. Compliance with the three anteproyecto targets

Grid-enabled model, 50 seeds × 2 days per cell, cluster-bootstrap CIs,
n_clusters = 50:

| Arm | Satisfaction > 90% (CI lower bound) | ENS_rel < 15% (CI upper bound) | Voltage ±5% |
|---|---|---|---|
| AFAP | Met at all 5 settings (100%) | Met (0%, reference) | Not assessable: idle feeder out of band in 78–100% of cells; station adds samples in 74–94 of 100 cells |
| Round Robin | Met at all 5 (≥ 99.83%) | Met (CI upper ≤ 0.92%) | Same framing; adds samples in 70–91 of 100 cells; smallest Δ min V among causal arms |
| MPC_TrackingG2V | Met (100%) | Met (≤ 0.52%) | Same framing; 73–92 of 100 cells |
| TD3 extended s102 | Met (≥ 99.36%) | Met (≤ 3.32%) | Same framing; 73–92 of 100 cells |
| Optimal_Oracle_Tracking | Met (100%) | Met (≤ 0.52%) | Same framing; 70–94 of 100 cells |

Full table: `results/week7_target_compliance.csv` (+ `.xlsx`).

### 4. git status of `semana-7`, grouped, with suggested commit messages

**Nothing committed.** 102 changed or new files.

**Group A — Week 6 Part 0 closure:**
- `thesis_docs/chapters/05_algorithm_comparison.md` (S5.11 points 1–6, the
  final model and the S5.8 correction note);
- `thesis_docs/Week6_Part0_Parameter_Method_and_Implementation_Justification.{md,docx}`.

Suggested message:
```
docs: close Week 6 Part 0 - final RL model (TD3 extended seed 102 @ 850k), S5.11 per-seed CIs, Progress Log section 12

Per-seed paired cluster CIs vs. each seed's 60k checkpoint; the
"rather than a better reward" interpretation dropped (training reward
improved); seed-spread sentence corrected; S5.8 503.9 -> 551.9 COP/day
correction note (stale pre-Gate-4 CSV).
```

**Group B — Objective 4** (the files listed in the STEP 2 section below).
Suggested message:
```
exp: Objective 4 - grid-enabled infrastructure guidelines (34-node feeder, 5 arms x 5 growth settings x 50 seeds)

Station placed on bus 27 via ev2gym_thesis/grid/placement.py (no
ev2gym/ edits); grid == non-grid on every station metric (0.0 diff,
500 cells x 5 arms); voltage band check + idle-station attribution;
simulate_grid registry column (migration verified, smoke-test flag
corrected); 2,500 analysis rows + 200 probe rows; f15-f17; workbooks;
test_week6_infra.py.
```

**Group C — Objective 5 and closing documentation:**
- `ev2gym_thesis/prices/medellin.py`;
- `scripts/analyze_week7_replicability.py`;
- `ev2gym_thesis/tests/test_replicability.py`;
- `thesis_docs/sources/SOURCES_week7.md`,
  `thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf`;
- `results/week7_replicability_margin.*`,
  `results/week7_cost_of_transformer_limit_two_cities.*`,
  `results/week7_ranking_invariance.*`,
  `results/week7_transfer_classification.*`,
  `results/week7_demand_mapping.*`;
- `figures/f18_two_city_margin.*`;
- `thesis_docs/chapters/07_replicability.md`,
  `thesis_docs/chapters/08_limitations.md`;
- `thesis_docs/Week7_Objectives4_5_Parameter_Method_and_Implementation_Justification.{md,docx}`;
- `thesis_docs/DELIVERABLES_INDEX.md`, `scripts/build_deliverables_index.py`;
- `thesis_docs/overnight_report.md`.

Suggested message:
```
exp: Objective 5 - replicability in Medellin (EPM Sep 2026 CU, ranking invariance, transfer classification)

EPM Nivel II CU 923.92 COP/kWh passes both Week 5 invariants; no
published EPM EV price (1,450 as labelled sensitivity); ranking
tariff-invariant in 48/48 checks; demand mapping not defended by any
source (guidelines conditional). Closing docs: Week 7 handback,
Progress Log sections 13-14, consolidated limitations (ch. 08),
deliverables index, overnight report, CLAUDE.md.
```

**Files spanning several groups** (commit them with Group C, or split the
hunks with `git add -p`):
- `CLAUDE.md`: final model (A), the Week 7 block (B and C).
- `thesis_docs/chapters/00_lab_log.md`: entries for all three groups.
- `thesis_docs/Progress_Log_Thesis_Project_corrected_2026-09-09.docx`:
  section 12 (A), 13 (B), 14 (C). It is a binary file and cannot be split.
- `scripts/extend_progress_log.py`: `--section` week6_part0 / week7.
- `scripts/make_figures.py`: f15–f17 (B) and f18 (C).
- `scripts/export_week7_results_xlsx.py`: both.
- `ev2gym_thesis/xlsx_export.py`.

### 5. Files that should not be committed

All are **already covered by `.gitignore`**, verified with
`git check-ignore -v`:
- `results/timeseries/` (including `week7_voltage/*.npz`, 2,500 per-run
  voltage arrays);
- `experiments/phase3_infra_replicability/results/shards/` (worker shards
  and logs; their contents are merged into the registry);
- `experiments/phase3_infra_replicability/configs/_tmp*/`, and every
  per-process `**/_tmp_*_pid*/`;
- `experiments/phase4_oracle/replays_raw_pid*/`, `replays_g2v_pid*/`
  (oracle replay pickles);
- `experiments/phase2_algorithms/models/` (checkpoints).

`results/master_results.csv` (~6 MB) and the EPM PDF (341 KB) **should** be
committed: they are the registry and a cited source.

**Items for the author:**
1. Correct "60 kWh" → "70 kWh" in the Week 1 handback, the external
   Progress Log and §8.1.4 of the corrected Progress Log (Checkpoint 1a).
2. `results/week5_margin_vs_overload.csv` is stale (pre-Gate-4) and has no
   generator script. Delete it or regenerate it; it was left untouched.
3. `test_week4.TestRegistryCount` fails as before this work. Its arm list
   predates Week 5's MPC arms.
4. The new sections of the corrected Progress Log use bold Normal
   paragraphs, per your rule; the older sections use Word Heading styles.

---

# Checkpoint log (chronological)

## CHECKPOINT 0 — Week 6 Part 0 closure (2026-10-05, ~23:00 Bogotá)

**`main` verification.** `git pull origin main`: already up to date.
`main`, `semana-6`, `origin/main` and `origin/semana-6` all point to
`ebf3634` ("extended TD3_vanilla training to convergence"), and `semana-6`
is an ancestor of `main`. Last commits on `main`:

```
ebf3634 extended TD3_vanilla training to convergence
23468f3 Correcciones y validaciones del proyecto hasta ahora corte semana 8
d59a593 nueva regla para claude
26b6a91 Mejor orden en los excels
b06c4af Colombian price re-basing, MPC arm, and corrected evaluation grid
```

Decision rule: nothing from `semana-6` is missing, so **`semana-7` was
created from the updated `main` (`ebf3634`)**.

**Part 0 items already in `main`:**
- S5.11;
- the Part 0 handback (`.md` and `.docx`);
- the 900 registry rows;
- `results/week6_part0_*`;
- f08 and f12–f14;
- the tests;
- the `CLAUDE.md` Part 0 block.

**Missing, done now on `semana-7`:**
- the Progress Log extension. It was never run. Done:
  `extend_progress_log.py --section week6_part0`, which appended section
  "12.", 480 → 512 paragraphs, with all prior paragraphs and tables
  verified unchanged;
- recording the final model (seed 102) in S5.11, the handback, the Progress
  Log and `CLAUDE.md`;
- points 1–6 with per-seed paired CIs.

**Final RL model (author's decision).** `TD3_vanilla` extended, training
seed 102, primary checkpoint at **850,000** steps.
- Model:
  `experiments/phase2_algorithms/models/TD3_vanilla_extended_ts102/checkpoints/td3_vanilla_extended_ts102_850000_steps.zip`
- VecNormalize: same path with the suffix `_vecnormalize.pkl`. Both files
  exist.
- Validation tracking error of the primary checkpoints:
  - seed 100: 42,531 (at 400k steps);
  - seed 101: 46,554 (630k);
  - **seed 102: 40,378 (850k)**.

**S5.11 headline paragraph (as now written).** Extended training did not
improve the selection criterion. For all three seeds, test-grid tracking
error is worse than the same seed's new-run 60k checkpoint (every CI
excludes zero, n_clusters = 50). The convergence rule detected a plateau,
not an improvement. User outcomes improved and their across-seed spread
shrank. Overload did not change significantly. Round Robin still has lower
tracking error and overload than every implementable arm, so for the one
arm extended to about 14× its budget the gap is not a budget artefact.

**Numbers behind points 1–4.** Extended primary minus the same seed's
new-run 60k checkpoint, paired cluster bootstrap, n_clusters = 50:

| Seed | Tracking error | Overload (kWh) | Avg. satisfaction | Energy charged (kWh) | total_reward |
|---|---|---|---|---|---|
| 100 | +13,241 [+10,689, +15,920] | +3.19 [−1.23, +7.74] | +0.0152 [+0.0106, +0.0200] | +15.83 [+11.38, +20.30] | +3,333 [+1,430, +5,202] |
| 101 | +10,243 [+8,140, +12,441] | +0.62 [−4.22, +5.20] | +0.0360 [+0.0306, +0.0413] | +36.17 [+30.93, +41.34] | +5,961 [+3,286, +8,792] |
| 102 | +8,620 [+6,877, +10,419] | −1.58 [−4.38, +1.27] | +0.0034 [+0.0005, +0.0065] | +3.74 [+0.53, +7.09] | +2,698 [+432, +5,028] |
| 3-seed mean | +10,701 [+9,042, +12,472] | +0.74 [−1.98, +3.40] | +0.0182 [+0.0155, +0.0209] | +18.58 [+15.86, +21.24] | +3,997 [+2,340, +5,790] |

- **Point 2 (spread).** Across-seed range, new60k → extended:
  - average satisfaction 3.22 → 0.11 pp;
  - `ENS_rel` 16.13 → 0.59 pp;
  - minimum energy satisfaction 17.14 → 1.71.

  Overload is not significant for any seed, and its spread widened
  (30.8% → 82.9% relative range).
- **Point 3: decision rule fired.** The brief asked to write that the
  policy moved along the trade-off "rather than reaching a better reward",
  and to drop the claim if the data does not support it.
  `total_energy_charged` supports the trade-off part: more energy in every
  seed. The **"rather than a better reward" part is contradicted**: the
  test-grid `total_reward` under the same training reward improved for all
  three seeds. That part was dropped. S5.11 instead states, as a labelled
  interpretation, that extended training optimised its own reward better,
  and that this reward values satisfaction over tracking. This is the
  Week 3 reward-versus-metric misalignment, now measured.
- **Point 4.** Round Robin minus each implementable arm, every CI excluding
  zero, across AFAP, the random control and all 15 TD3 checkpoints:
  - tracking error: lower for Round Robin in every case;
  - overload: lower for Round Robin in every case;
  - satisfaction: Round Robin is 0.09 pp below AFAP and the random control
    (CI [0.04, 0.16] pp), and statistically indistinguishable from the last
    checkpoints of seeds 101 and 102.

**A further correction made in S5.11.** The 2026-09-28 text said the seed
spread "did not shrink in any meaningful sense". That holds only for
tracking error and overload, so it is now corrected and marked as a
correction.

**git status (semana-7, uncommitted):**
```
 M CLAUDE.md
 M scripts/extend_progress_log.py
 M thesis_docs/Progress_Log_Thesis_Project_corrected_2026-09-09.docx
 M thesis_docs/Week6_Part0_Parameter_Method_and_Implementation_Justification.docx
 M thesis_docs/Week6_Part0_Parameter_Method_and_Implementation_Justification.md
 M thesis_docs/chapters/05_algorithm_comparison.md
```
(plus `thesis_docs/overnight_report.md` and `00_lab_log.md`, added after
this list was taken)

## CHECKPOINT 1 — Objective 4 checks, 1a–1e (2026-10-05, 23:20 Bogotá)

### 1a. Pre-flight

**Registry before Week 7:** 3,153 rows.

| `analysis_row` | `superseded` | Rows |
|---|---|---:|
| True | False | 2,200 (all `station_v0_bogota`) |
| False | True | 953 |

After the registry changes below there are 3,353 rows.

**Registry changes made at this checkpoint:**
1. **`simulate_grid` column added**, the one new column the brief allows.
   It was appended as the last column with `False` for every existing row
   (`scripts/migrate_registry_schema_week7.py`). The migration was verified
   two ways: the 38 prior columns are identical value by value, and every
   raw line changed only by an appended `,False`. The registry backup is in
   the session scratchpad.
2. **Correction.** A test then found one pre-existing grid row, the Week 2
   smoke test `v2ggrid_smoke_test` (`notes = pipeline_smoke_test_grid`).
   Its new flag was set to `True` (`--fix-smoke-test-flag`). Exactly one
   raw line changed.
3. **200 probe rows** from 1d, with `analysis_row = False` and
   `superseded = False`.

**Oracle variant.** Week 5 evaluated `Optimal_Oracle_Tracking` and
`Optimal_Oracle_Balanced`. S5.6's tracking-error optimality gap used
`Optimal_Oracle_Tracking`. **Labelled assumption:** Week 7 uses
`Optimal_Oracle_Tracking` as the upper bound, because its objective is the
same tracking target that RR, MPC and RL are judged on.

**Statistics-set filter:**
- non-grid: `analysis_row == True` and `config_name == 'station_v0_bogota'`
  (`registry_analysis.main_grid_rows`);
- grid: `analysis_row == True` and `simulate_grid == True` and
  `config_name` in the 5 Week 7 setting names.

**ENS_rel (S5.7).** `(E_AFAP(s) − E_a(s)) / E_AFAP(s)`, with net energy
summed over both day types per seed. The arm passes when the 95%
cluster-bootstrap CI upper bound is below 15%. It was **formally adopted in
Week 5**, not merely proposed.

**Fleet battery.** `station_v0_bogota.yaml` uses **70 kWh**
(`battery_capacity: 70`, line 132, `heterogeneous_ev_specs: False`). These
documents state **60 kWh** instead:

| Document | Exact text |
|---|---|
| `thesis_docs/Progress_Log_Thesis_Project_corrected_2026-09-09.docx` | "All simulated vehicles share one 60 kWh battery profile for Week 1." |
| `../Progress_Log_Thesis_Project.docx` | "Uniform, 60 kWh battery" |
| `../Progress_Log_Thesis_Project.backup-before-week3-20260813000202.docx` | "Uniform, 60 kWh battery" |
| `../Week1_Parameter_and_Method_Justification.docx` | "All simulated vehicles share one 60 kWh battery profile for Week 1." |

No `.md`, `.py` or `.yaml` file states 60 kWh. An older lab-log entry said
that "no document stating 60 kWh" was found; that search covered Markdown
only and was incomplete. **These documents are not edited here (extend,
never rewrite). The author should correct 60 → 70 kWh in them.**

### 1b. Grid bring-up and equivalence

**Config.** `experiments/phase3_infra_replicability/configs/station_v0_bogota_grid.yaml`.
The diff against `station_v0_bogota.yaml` contains only these changes:
- `number_of_transformers: 1 → -1`;
- `simulate_grid: False → True`;
- `load_multiplier: 1 → 1.0`;
- `network_info.thesis_station_bus: 27`, added with a labelled comment.

**Station placement (finding).** No EV2Gym config key places the station on
a bus. In grid mode `load_grid` creates 33 transformers (one per bus) and
spreads the 8 stations round-robin: 8 buses, each with its own 100 kW
transformer, which is 800 kW of capacity. **That would not preserve the
100 kW local limit.** `ev2gym_thesis/grid/placement.py` wraps `load_grid`
from outside the library (nothing in `ev2gym/` is edited) and puts all 8
stations on bus 27, transformer id 25. Bus 27 is labelled as the
electrically farthest bus (series path R = 2.90, 16 hops), the conservative
choice for voltage.

**Station transformer limit:**
- non-grid: 1 transformer, 100 kW;
- grid: 33 transformers, with only #25 carrying EV load, at **100 kW**.

The limit is **preserved**.

**Network.** EV2Gym's "node_34" network is the RL-ADN 34-node feeder (Hou
et al., 2025), 7.80 MW total nominal load, PV at 80% (`pv_scale`). It is
called "IEEE 34-bus" in this thesis only as the library names it; it is not
validated against the IEEE published data (declared).

**Tolerance (stated before running):** absolute difference ≤ 1e-6 on every
metric. AFAP and RR × seeds 0–9 × both EVAL_DAYS (40 paired cells,
`results/week7_grid_equivalence*.csv`):

| Metric | Mean, non-grid | Mean, grid | Max abs diff |
|---|---:|---:|---:|
| total_ev_served | 13.500 | 13.500 | 0.0 |
| total_energy_charged | 199.4145 | 199.4145 | 0.0 |
| total_transformer_overload | 5.5772 | 5.5772 | 0.0 |
| average_user_satisfaction | 0.999398 | 0.999398 | 0.0 |
| tracking_error | 35,365.88 | 35,365.88 | 0.0 |

In the 1e timing cell (seed 0, weekday), all 5 arms (AFAP, RR,
MPC_TrackingG2V, the final RL model and the oracle) also reproduce their
non-grid registry values exactly. **No divergence; the 1b divergence rule
did not fire.** Station metrics are identical with and without the grid;
voltage is the only new information.

### 1c. RL compatibility

The observation space is `(27,)` under both configs. Over a full episode
with the final RL model (seed 4, weekday), observations, actions and the
final tracking error are bit-identical at every step. The frozen
VecNormalize statistics are never updated. This is pinned by
`test_week6_infra.TestRLCompatibility`. No adapter is needed, and **the RL
arm stays in the grid runs (5 arms)**.

### 1d. Can `voltage_violation` trip?

**Definitions** (`ev2gym/utilities/utils.py::get_statistics`, grid mode
only, on `env.node_voltage`: 34 buses × 96 steps, in p.u., row 0 = slack
bus):

| Metric | What it measures |
|---|---|
| `voltage_violation` | Σ over all buses and steps of min(0, 0.05 − abs(1 − v)). Aggregate, cumulative, ≤ 0, in p.u.·step; a 1-tuple, summed by `registry._coerce_scalar`. |
| `voltage_violation_counter` | Number of (bus, step) samples outside [0.95, 1.05]. |
| `voltage_violation_counter_per_step` | Number of steps with at least one bus outside. Not a registry column; recomputed into `results/week7_voltage_*.csv`. |

**Band.** Hard-coded at 0.95–1.05 p.u., which equals the ±5% band the
thesis adopts. An independent check was implemented and tested anyway:
`ev2gym_thesis/grid/voltage.py::band_check`, which also reports the station
bus separately. It matches the library exactly on all 200 probe rows (same
counter; magnitude difference 7.5e-15).

**Probe** (`results/week7_voltage_probe*.csv`). AFAP and RR, seeds 0–9 × 2
days, spawn 30, `load_multiplier` from 0.5 to 1.0, plus a zero-charge
diagnostic with the station idle:

| load_multiplier | Cells tripping, AFAP | Cells tripping, RR | Cells tripping, idle station | Min V (AFAP) |
|---:|---:|---:|---:|---:|
| 0.5 | 0/20 | 0/20 | 0/20 | 0.9658 |
| 0.7 | 0/20 | 0/20 | 0/20 | 0.9520 |
| **0.8** | **4/20** | 4/20 | 3/20 | 0.9450 |
| 0.9 | 10/20 | 9/20 | 9/20 | 0.9378 |
| 1.0 | 16/20 | 15/20 | 15/20 | 0.9305 |

The smallest setting at which the metric becomes non-zero is
**load_multiplier 0.8**; no probed setting at or below 0.7 trips. The worst
bus is always bus 27, the station's bus.

**Finding: not a negative result. The metric trips at the library's
nominal feeder, but the feeder's background load drives it.** With the
station idle, 15/20 cells already violate at load 1.0. The station adds only
a small increment: at most about 0.0006 p.u. of extra depth, plus a few
extra (bus, step) samples. **The 1d negative-result rule did not fire.**

**Consequence (labelled, for chapter 06).** Voltage compliance is reported
as **the station's increment over the zero-charging baseline of the same
cell**. `scripts/week7_zero_charging_baseline.py` records that baseline for
every Step 2 cell. **No absolute RETIE compliance claim is made for the
feeder**: the base feeder is itself outside the band at bus 27.

### 1e. Timing

One grid cell end to end (base setting, seed 0, weekday):

| Arm | Seconds |
|---|---:|
| AFAP | 4.77 (includes the first-cell warm-up) |
| RR | 0.85 |
| MPC_TrackingG2V | 3.61 |
| TD3 extended seed 102 | 4.59 |
| Oracle | 2.49 (Gurobi OPTIMAL; licence OK) |

That is 16.3 s per (setting, seed, day). The Step 2 grid has 5 settings × 2
days per seed, so the single-process projection is:
- 20 seeds: 0.9 h;
- 30 seeds: 1.4 h;
- 50 seeds: 2.3 h, or 2.8 h with the 25% margin.

**Seed-count rule fired: 50 seeds.** Fifty seeds with the margin end at
about 02:15 even run serially, before 07:00. Launched at 23:16 as 3
detached workers (`scripts/run_week7_worker.cmd`, WMI, keep-awake). The
measured 0.23–0.24 cells/s per worker gives an ETA of about 00:15. That is
2,500 cells = 5 arms × 5 settings × 50 seeds × 2 days.

## CHECKPOINT 2 — Objective 5, Step 3a: city and data (2026-10-05, 23:24 Bogotá)

**City (labelled assumption):** **Medellín**. It is a district of categoría
especial, its network operator and regulated retailer is EPM, and EPM
publishes a monthly regulated tariff sheet in the same CREG CU format as
Enel's Bogotá sheet. That makes the Week 5 invariants applicable unchanged.
All sources and access dates are in `thesis_docs/sources/SOURCES_week7.md`,
and the local copy is
`thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf`.

**Operator cost.** EPM, regulated market, **September 2026**, the most
recent sheet listed, accessed 2026-10-05 23:21. Non-residential **Nivel II**
in COP/kWh:

| Line | Punta | Fuera de Punta |
|---|---:|---:|
| Industrial y Comercial, **with** contribution | 923.92 | 917.58 |
| CU, **without** contribution (Oficial y Exentos) | 769.94 | 764.65 |
| Components G / T / D / CV / PR / R | 401.37 / 46.84 / 197.10 / 96.41 / 22.54 / 5.68 | 399.72 / 42.74 / 197.10 / 96.41 / 23.10 / 5.59 |

The monomial Nivel II CU (without contribution) is 767.30; its components
are not published.

**Invariant check** (Week 5 tolerances):

| Period | Components vs. stated CU | With / without contribution |
|---|---|---|
| Punta | 769.94 = 769.94 → pass | 1.19999 → pass |
| Fuera de Punta | 764.66 vs. 764.65, diff 0.01, at the inclusive tolerance bound → pass | 1.20000 → pass |

The Fuera de Punta 0.01 difference is consistent with rounding six
two-decimal components, and it is declared.

**Base cost value (labelled assumption, conservative):** 923.92 COP/kWh, the
higher validated with-contribution rate (Punta). Every Medellín margin is
therefore a lower bound, as in Bogotá. Sensitivities:
- Fuera de Punta: 917.58;
- monomial CU × 1.20 = 920.76 (derived; the with-contribution monomial is
  not published).

**Retail price:** no EPM EV-charging price is published (negative result,
sources tried listed in `SOURCES_week7.md`). **Decision rule fired:**
Bogotá's 1,450 COP/kWh is used as a **labelled sensitivity**, not as a
Medellín price. No competitor's price is substituted.

**Intraday spread:** Medellín (923.92 − 917.58) / 917.58 = **0.69%**,
against Bogotá's 1.57% recorded in Week 5. The generation component is
401.37 / 769.94 = 52.1% of the CU, matching Bogotá's ~52%.

**Decision rules:**
- **Data unavailable / invariant fails:** did not fire. Medellín's data is
  available and both invariants pass, so the alternative city (Cali) was
  not needed.
- **Spread materially larger than Bogotá's:** did not fire. 0.69% is
  smaller, and no price-signal simulation is warranted.

## STEP 2 — Objective 4 grid run and analysis (2026-10-05 23:16 → 2026-10-06 00:45 Bogotá)

**Run.**
- 3 detached workers, launched at 23:16.
- Worker 1 crashed at about 23:28 (shared day-config race). All workers
  were stopped, fixed with per-process directories, shards verified, and
  resumed at 23:35.
- Finished at 00:17. 2,500/2,500 cells, 0 errors after the resume.
- Merged once: 2,500 rows appended, and the 3,353 prior rows were verified
  byte-identical.
- Each arm × setting has exactly 100 rows.
- The analysis ran at about 00:30.

**Integrity.**
- Base setting, all 500 cells × 5 arms: grid = non-grid on all 9 station
  metrics (maximum difference 0.0).
- Axis 2 (feeder load) settings are cell-by-cell identical to base on
  every station metric, and differ only in voltage. EV2Gym has no feedback
  from the feeder to the station (declared as limitation L20).

**Headline numbers** (95% cluster-bootstrap CI, n_clusters = 50):

| | Value |
|---|---|
| Round Robin overload | 0 in all seeds at every setting; 95th-percentile peak 66.8 / 73.3 / 67.6 kW at 1.0× / 1.3× / 1.6× |
| AFAP overload | 14.2 / 24.0 / 26.4 kWh/day; 28 / 42 / 39 of 50 seeds; 95th-percentile peak 172.7 / 191.9 / 189.1 kW → next standard size 225 kVA |
| Round Robin satisfaction | 99.91 / 99.89 / 99.93%. The 90% threshold is not reached within 1.6×, and satisfaction is unchanged vs. base (CI includes zero) |
| Round Robin energy at 1.6× | +37.3 kWh/day [+30.9, +44.1] vs. base |
| Voltage | The idle feeder is out of band in 78 / 84 / 86 / 100 / 100 of 100 cells. The station adds 2.7–4.5 out-of-band samples per day. Round Robin's Δ min V is −0.00053 against AFAP's −0.00084 p.u. at base (37% smaller, CIs disjoint) |
| Round Robin cost vs. AFAP | 551.9 / 800.0 / 556.1 COP/day (under 1% of margin) |
| Final RL vs. Round Robin | Tracking error +27.6k to +33.4k; overload +3.58 to +7.37 kWh/day; all CIs exclude zero |
| Targets | Satisfaction and ENS_rel met by all arms at all settings. Voltage not assessable as compliance on this feeder |

**Files belonging to Objective 4** (for a separate commit and the
`v0.4-infra-guidelines` tag):
- **Code:**
  - `ev2gym_thesis/grid/__init__.py`, `ev2gym_thesis/grid/placement.py`,
    `ev2gym_thesis/grid/voltage.py`;
  - `ev2gym_thesis/registry.py`;
  - `ev2gym_thesis/xlsx_export.py` (`PER_UNIT_VOLTAGE_FORMAT`; the file
    also holds the `MIXED_UNIT` constant from Part 0);
  - `scripts/migrate_registry_schema_week7.py`,
    `scripts/week7_grid_equivalence.py`, `scripts/week7_voltage_probe.py`,
    `scripts/week7_zero_charging_baseline.py`, `scripts/run_week7_grid.py`,
    `scripts/run_week7_worker.cmd`, `scripts/analyze_week7_infra.py`;
  - `scripts/analyze_week5_results.py` (`config_path` parameter);
  - `scripts/make_figures.py` (f15–f18; shared with Objective 5);
  - `scripts/export_week7_results_xlsx.py` (shared with Objective 5).
- **Configs:** `experiments/phase3_infra_replicability/configs/*.yaml`
  (5 settings and 5 probes).
- **Data:**
  - `results/master_results.csv`;
  - `results/week7_grid_*`, `results/week7_transformer_*`,
    `results/week7_voltage_*`, `results/week7_target_compliance.*`
    (`.csv` and `.xlsx`);
  - `experiments/phase3_infra_replicability/results/week7_timing_one_cell.*`.
- **Figures:** `figures/f15_grid_growth.*`, `figures/f16_transformer_sizing.*`,
  `figures/f17_voltage_attribution.*`.
- **Tests:** `ev2gym_thesis/tests/test_week6_infra.py`;
  `ev2gym_thesis/tests/test_final_rl_model.py` (pin scoped to the non-grid
  config).
- **Docs:** `thesis_docs/chapters/06_infrastructure.md`; `.gitignore`.

## STEP 3 — Objective 5 (Medellín) (2026-10-05 23:20 → 2026-10-06 00:35 Bogotá)

- **3a:** see Checkpoint 2.
- **3b:** `results/week7_transfer_classification.*`. Only the tariff inputs
  are both city-specific and available.
- **3c:** recomputed from the registry's energy on the non-grid rows plus
  all 2,500 grid rows. Round Robin's cost of the 100 kW limit is 551.9
  COP/day in Bogotá against 497.0 in Medellín at base (ratio 0.900; 0.47%
  of margin in both). It is 800.0 against 720.3 at 1.3× and 556.1 against
  500.8 at 1.6×. **Ranking invariance holds in all 48 dataset × price-scenario
  checks** (asserted in code and pinned by a test).
- **3d, decision rule fired:** no source defends a per-station demand
  ratio. EV registrations give Medellín/Bogotá = 0.40 (January–August 2025,
  Andi–Fenalco via El Colombiano); charger counts give about 0.45 (lower
  bound). Both naive readings fall below 1.0×, so the guidelines are
  presented as conditional on demand. A proposal for 0.4×, 0.7× and 0.9×
  Axis 1 runs costs about 27 min per setting on one process, or about 10
  min on 3 workers. Not run.
- **Found while working:** S5.8's 503.9 COP/day came from a stale
  pre-Gate-4 CSV, `results/week5_margin_vs_overload.csv`, which no script
  in the repo regenerates. The current value is 551.9 [274, 874]. A dated
  correction note was added to S5.8; the stale CSV is left untouched as
  history and flagged.
