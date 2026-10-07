# Closure — Parameter, Method, and Implementation Justification: Corrections, Capacity Threshold and Colombian Replicability

**Status: complete (2026-10-06), run unattended on branch `semana-7`;
nothing committed.**

This document follows the Week 5–7 mechanism. It is a Markdown record
rendered to `.docx` by `scripts/render_docx.py`. The decision log, with
the Bogotá time of each checkpoint, is the closure section at the top of
`thesis_docs/overnight_report.md`.

The baseline for this run was HEAD `6f42b02` with a clean working tree
(`thesis_docs/closure_baseline_status.txt`). Every file that differs from
`6f42b02` was therefore changed by this run.

## Headline Results Summary

**1. EV2Gym silently drops arrivals at a full station, and the station is
port-limited at its reference demand.**
- An arrival drawn for an occupied port is never created. Every registry
  metric therefore covers served EVs only.
- Reconstructed from the simulator's own random draws, demand not served
  is **34.6% [30.8, 38.4]** for Round Robin at the reference demand
  (rejected plus shortfall, lower bound; n_clusters = 50). AFAP and the
  RL model are within 1.6 points.
- The Week 7 claim that satisfaction "is unchanged" up to 1.6× is
  withdrawn as a statement about the station's users.

**2. Capacity threshold.**

| Arm | Breaking level | First criterion broken | Value [95% CI] | n_clusters |
|---|---|---|---|---:|
| Round Robin | 0.733× (holds at 0.5×) | demand not served > 15% | 15.80% [12.56, 19.13] | 50 |
| AFAP | 0.5× | P95 peak > 100 kW | 133.1 kW [122.2, 156.3] | 50 |
| Final RL model | 0.5× | P95 peak > 100 kW | 137.6 kW [121.6, 156.5] | 50 |

**3. What closes the gap: ports, not the transformer.** Read at constant
station demand:
- *At 0.733×:* 10 ports bring Round Robin's demand not served to 4.7%
  [3.0, 6.7], with +12,159 COP/day.
- *At 1.0×:* 12 ports bring it to 7.9% [5.6, 10.5], with +28,225 COP/day.
- *Transformer:* 112.5 or 150 kVA changes nothing for Round Robin, whose
  P95 peak is ≤ 83 kW. It only reduces AFAP's overload.

Guideline per growth level (06, C3):
- **≤ 0.5×:** the reference design meets every target.
- **0.733×:** go to 10 ports.
- **1.0×:** go to 12 ports.
- **> 1.0×:** keep the 100 kW unit with Round Robin. The number of ports
  needed is not simulated.

**4. Six categoría especial cities.** The list comes from the CGN workbook
for vigencia 2026, under Ley 617 de 2000.
- **The spread is small in four cities (≤ 1.57%).** ESSA publishes no
  option.
- **Barranquilla is the exception.** Air-e publishes a 10.03% two-band
  option. Under it, Round Robin's cost of the 100 kW limit rises from 523
  to **1,878 COP/day [1,426, 2,359]**, and the margin ranking shifts.
- **Proposition 7.1, with proof.** Under a flat tariff, the margin
  ranking equals the energy ranking and the relative cost is
  price-independent. The Week 7 "48/48" check and the equal 0.47% are its
  consequences, not findings.

**5. Voltage.**
- **No feedback.** EV2Gym has no feedback from the feeder to the station.
  This is confirmed in source (`ev2gym_env.py`, lines 365–397) and pinned
  by a test.
- **Shipped feeders.** Of EV2Gym's four networks, only **node_123 is in
  band with the station idle** (20/20 cells, lowest 0.9738 p.u.). node_34
  is not, and node_25 and node_69 cannot run as shipped.
- **AFAP and Round Robin on node_123** (50 seeds, 1.0/1.3/1.6×, weekday
  only, because EV2Gym's load generator stalls on the weekend day): **0 of
  50 cells leave the ±5% band** for either arm at any level, with the
  lowest bus at 0.9720 p.u. On that test network the band is met. On the
  34-node feeder, RETIE compliance remains not evaluable.
- **The 37% result.** It is the ratio of the mean drops in the feeder-wide
  daily minimum voltage relative to the idle station: **36.4% [22.3,
  47.0]** at the base setting only. At 1.3× and 1.6× demand it is 24.7%
  and 22.7%. On node_123 the same reduction is 39.2% [18.6, 53.7] at 1.0×,
  which corroborates it.

**6. Final compliance at the reference demand.**
- Satisfaction of served EVs is met by every arm.
- **Satisfaction counting rejected arrivals and demand not served are not
  met by any arm.**
- The transformer target is met by Round Robin, MPC_TrackingG2V and the
  oracle, and not by AFAP or the RL model.
- Voltage is met on node_123 for AFAP and Round Robin. It is not
  evaluable for the other arms, which were not rerun there.

The full table is in the overnight report's FINAL REPORT and in
`results/closure_target_compliance.csv`.

**7. Corrections (Part A).** Each one carries a dated note:
- the battery is 70 kWh, not 60 kWh;
- AFAP overload is 14.22 kWh/day, not the old 5-seed 5.33 kWh;
- Round Robin's cost of the limit is 551.9 COP/day, not 503.9 or
  88.6 COP;
- the energy change is −0.47%, not −0.08%.

The `test_week4` arm list was rewritten to 22 arms × 100 cells. It is
stricter than before, because it now checks the exact SEEDS × EVAL_DAYS
cover.

## Part 1 — Parameters and Methods

| Parameter / decision | Value | Label | Justification |
|---|---|---|---|
| Final RL model | `TD3_vanilla` extended, seed 102, 850k steps | Validated | Fixed by the author (2026-10-05); never substituted. |
| Demand-not-served definition | (E_rejected + R_served − E_delivered) / (E_rejected + R_served) | Labelled method | Brief B: rejected plus shortfall over total requested. |
| Rejection bounds | lower: blocked draws no free port could absorb; upper: every blocked draw | Labelled assumption | EV2Gym gives each port its own arrival stream, while a real driver takes any free port. Both bounds are reported, and the lower one is primary (favourable to the station). |
| Energy of a rejected arrival | EV2Gym's mean requested energy for that arrival time, min(max(mean, 5), 70) kWh | Labelled assumption | It is the expectation of the draw that `spawn_single_EV` would have made (utils.py, line 207). |
| Breaking criteria | satisfaction CI lower < 90%; DNS CI upper > 15%; P95 peak CI upper > 100 kW | Labelled assumption, conservative | The CI side that makes compliance hardest to claim. |
| P95 peak CI | per-seed peak (max of two days), quantile CI by resampling seeds | Declared method | A quantile is not a mean, so `paired_cluster_bootstrap_ci` does not apply. The cluster unit is the same. |
| Demand levels | spawn 15 / 22 / 30 / 39 / 48 / 60 / 75 = 0.5 / **0.733** / 1.0 / 1.3 / 1.6 / 2.0 / 2.5× | Declared | round(22.5) = 22. 3.0–5.0× were not run, because RR breaks well below them. |
| Non-grid configs for Part C | `station_v0_bogota` with only spawn, ports and transformer changed | Validated | Week 7: grid and non-grid station metrics are identical (0.0 difference). |
| Constant-demand port variants | spawn × 8/P (e.g. 17.6, 14.67) | Labelled method | EV2Gym's per-port arrivals would otherwise add demand with the ports. The multiplier enters only as a factor (utils.py, line 538). |
| Transformer variants | 100.6 and 134.2 kW = 112.5 and 150 kVA × 0.894 | Sourced | ET-013 standard ratings; pf from CREG 015/2018. |
| Power factor | 0.894 = cos(arctan 0.5) | Derived, with a caveat | CREG 015/2018 Ch. 12, 50% reactive threshold. Ratings are also given at unity power factor, with the same 225 kVA result. |
| City list | Bogotá, Medellín, Cali, Barranquilla, Cartagena, Bucaramanga | Sourced | CGN categorisation workbook, vigencia 2026 (2025 decrees); Ley 617/2000 Art. 6. |
| City cost | Nivel 2 commercial flat cost with 20% contribution, published where printed, else 1.20 × CU | Sourced / derived, labelled | Uniform definition across cities. Invariants checked (07 S7.7). |
| Two-band options | the operator's own option and hours | Sourced | Applied to each run's 15-minute station power, with the simulation starting at 05:00. |
| Feeder probe criterion | no bus out of band in any of 20 idle cells at nominal load | Stated before the run | No parameter tuned. node_123 passed; the screen stops a feeder at its first out-of-band cell. |
| node_123 voltage runs | AFAP and RR, 1.0/1.3/1.6×, 50 seeds, weekday only, station on bus 115, idle baseline per level | Labelled scope reduction | The weekend build does not finish (EV2Gym load-generator loop). The idle run must match the level, because EVs are drawn before the background load from the same random stream. |

## Part 2 — Implementation

### `ev2gym_thesis/demand/censoring.py` (new)

This wraps the `EV_spawner` name that `ev2gym/utilities/loaders.py`
imports, without editing the library:
1. It snapshots the global NumPy state.
2. It lets the original spawner run.
3. It replays the snapshot to recover the `(ports × steps)` arrival-draw
   matrix.
4. It restores the post-spawner state, so the simulation is unchanged.
5. It re-walks the spawner's loop with the same free-port and threshold
   tests.

It asserts that the replay re-finds every spawned EV. `scenario_demand()`
returns the counts for one cell, and `demand_not_served()` computes DNS.

### `scripts/closure_demand_censoring.py`, `scripts/closure_dns_summary.py` (new)

The first script builds the censoring table: 11 levels × 100 cells for 8
ports, plus the 10- and 12-port variants, as run and at constant demand,
in a separate file. The second joins the table to each arm's delivered
energy, giving per-run and per-(level, arm) DNS with cluster CIs. Neither
writes the registry.

### `scripts/run_closure_capacity.py`, `scripts/run_closure_worker.cmd` (new); `scripts/run_week7_grid.py` (extended)

These are detached, resumable workers with shard CSVs:
- `--prepare` writes every variant config once. This fixed a worker crash
  caused by parallel config rewrites, the same failure class as Week 7's
  day-config race.
- `--merge` appends once through `append_runs`, deduplicating on
  (config, algorithm, seed, day).
- `run_week7_grid.run_cell` gained `require_voltage=False` for non-grid RL
  rows.

The merge added 6,000 rows (`analysis_row=True`, `simulate_grid=False`).
Prior registry bytes were verified unchanged at both merges.

### `scripts/analyze_closure_capacity.py` (new)

This produces the C1 thresholds and the C2 options (per arm, level, port
count, rating and demand treatment). It joins the censoring table by
(level, ports, demand treatment, seed, day) and asserts that the censoring
spawn count equals the registry's `total_ev_served` for every run. Peaks
come from the saved timeseries.

### `ev2gym_thesis/prices/cities.py` (new), `scripts/analyze_closure_multicity.py` (new)

These hold the transcribed Nivel 2 values for the six cities, each with
its saved sheet, plus the invariant checks, spreads, generation shares and
two-band timing. The analysis applies flat and two-band costs to every
run's 15-minute power profile. It asserts that the profile energy equals
the registry energy (maximum difference 0.000000 kWh over 2,200 runs).

### `scripts/analyze_closure_lower_demand.py`, `scripts/closure_voltage_contribution.py`, `scripts/closure_feeder_probe.py`, `scripts/closure_target_compliance.py` (new)

- `analyze_closure_lower_demand.py`: D3, paired comparisons between demand
  levels.
- `closure_voltage_contribution.py`: E3, the exact definition and CI of
  the "37%".
- `closure_feeder_probe.py`: E2, idle-station probes of every shipped
  feeder.
- `closure_ieee123_voltage.py` with `run_closure_ieee123_worker.cmd`, and
  `analyze_closure_ieee123.py`: E2, the node_123 reruns (450 runs,
  resumable shards) and their analysis.
- `closure_target_compliance.py`: the final compliance table.

### `scripts/regenerate_margin_vs_overload.py` (new), `scripts/closure_audit.py` (new)

- `regenerate_margin_vs_overload.py`: A.2. It is the missing generator
  for `week5_margin_vs_overload.csv`, now regenerated from the analysis
  rows, plus the cluster-bootstrap companion.
- `closure_audit.py`: Part F. It is the audit table of stated against
  source values (`results/closure_audit_table.csv`), and it ends with 0
  unresolved occurrences.

### `scripts/export_closure_results_xlsx.py` (new), `scripts/extend_progress_log.py` (extended)

- `export_closure_results_xlsx.py`: every closure table as a formatted
  `.xlsx` through `export_formatted_xlsx`.
- `extend_progress_log.py`: Progress Log section 15, appended only. 15.1
  lists dated corrections to earlier paragraphs by section number.

### Tests: `ev2gym_thesis/tests/test_closure.py` (new); `test_week4.py`, `test_week6_infra.py` (corrected)

`test_closure.py` covers:
- the censoring wrapper and its replay against the registry;
- the DNS formula, the tables, the thresholds and the C2 options;
- the city invariants, spreads and band timing;
- the D3 monotonicity;
- the no-feedback source check and the feeder classification.

Two tests were corrected:
- `test_week4.TestRegistryCount` now pins 22 arms × 100 cells and the
  exact cell cover.
- `test_week6_infra.TestRegistryGridFlag` keeps the pre-closure 2,200 pin
  and adds a separate 6,000 closure pin.

### Sources added (`thesis_docs/sources/`, record in `SOURCES_closure.md`)

- **Regulation:** CREG 015/2018 (`regulatory/creg_015_2018.htm`).
- **Standards:** Enel ET-013, ET-009 and ET-012 (`standards/`).
- **Municipal categories:** the CGN categorisation workbook and Res.
  338/2025, plus Ley 617/2000 (`municipal_categories/`).
- **Tariff sheets:** ESSA Sep 2026, Afinia Sep 2026, Air-e Sep 2026 and
  EMCALI Jan 2026 (`tariffs_d2/`).
- **Charging-price press reports:** El País (EMCALI) and Vanguardia (ESSA).
