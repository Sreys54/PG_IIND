# Chapter 2 — Model and Network Validation (Week 2)

> Status: the 10-row table below and its labels are complete as of
> 2026-08-12 (branch `semana-2`) — every row has been independently verified
> (code inspection, IDEAM primary source, or measured with confidence
> intervals), not assumed. The grid-scope conflict referenced in earlier
> drafts of this note has been resolved (see the dedicated section below).
> What's still open in Week 2 as a whole (not this chapter specifically):
> the full 502-row registry's degradation-by-ambient hasn't been measured
> (only the `station_v0_bogota` 100-row scope has — see the residual
> limitations section), and the Week 2 hand-back document
> (`thesis_docs/Week2_Parameter_Method_and_Implementation_Justification.md`)
> is still being written. See `thesis_docs/chapters/00_lab_log.md`'s
> 2026-08-12 entries for the full session history.

This chapter is an explicit, itemised statement of what in the current
simulation model is realistic and what is a simplification, following the
project's convention: every row is labelled **validated against an external
source**, **empirically set inside this project**, or **simplification /
declared limitation**. No row is left unlabelled.

## Summary table

| Modelling element | Value in config | Realistic? | Evidence / source | Effect on Week 1 results | How it will be addressed |
|---|---|---|---|---|---|
| Station size (port count) | `number_of_charging_stations: 8` | Partially — the count matches an observed real hub | Enel X Colombia public inventory, 67 chargers / 21 sites, consulted 2026-08-11 (see `01_baseline.md` §1.1) | Grounds the scale of Week 1's ~14 EVs/day result against a real comparable hub (CC Retiro) | Label: **validated against external source**. Revisit if a directly-surveyed station becomes available. |
| Connector and rated power | `ev.max_ac_charge_power/max_dc_charge_power: 50 kW`, CCS Combo 2 implied | No — no observed 8-port Enel X site has 50 kW DC | Same Enel X inventory: the two ~8-port sites are AC-only (Salitre: 8x Type2 AC 43kW; CC Retiro: 8x AC 7.2kW); Res. 40223/2021 sets the DC floor this config targets | Overload dynamics in Week 1 (AFAP 0.132 kWh, RR 0.0 kWh) are driven by a charging capability that does not exist yet at any single observed 8-port site | Label: **simplification / declared limitation**. Documented in `01_baseline.md` §1.1(a) as a near-term Res. 40223/2021-driven upgrade scenario, not current hardware. |
| Transformer capacity (100 kW) and 4:1 oversubscription ratio | `transformer.max_power: 100`, ratio = 400kW installed / 100kW = 4:1 | Not benchmarked against a published standard | Searched for a Colombian utility/regulatory transformer-sizing figure for EV hubs; found none. RETIE (per Res. 40117/2024 guidance) requires a dedicated transformer "sized to what the station(s) require" — a case-by-case principle, not a published kW table; CREG's own public documents describe metering/connection conditions as still under review, not a sizing standard. | 100 kW and the 4:1 ratio are internal choices, now explored as a sensitivity dimension (`station_sensitivity/` configs, `size_sensitivity` in the registry) rather than presented as a single fixed "correct" value | Label: **empirically set inside this project**. The size-sensitivity sweep (Week 2, Deliverable 3) is the mechanism for exploring this, not a literature lookup. |
| `spawn_multiplier: 30` | 30 | No — tuned to produce a plausible EV/day count, not from Colombian arrival data | No Colombian public EV arrival-rate dataset was found or used; this value was reverse-engineered from the desired ~10-15 EVs/day order of magnitude (see `00_lab_log.md`, 2026-08-05 entry) | Directly controls how many EVs appear per day; the single biggest lever behind the reported EV counts | Label: **simplification / declared limitation**. This is the single weakest quantitative assumption in the model — stated plainly, not hidden. |
| Homogeneous 70 kWh fleet | `heterogeneous_ev_specs: False`, `battery_capacity: 70 kWh` | No — Bogota's actual EV fleet is mixed-brand and mixed-capacity | Enel X's site listings reportedly publish a compatible-brand column per site (BYD, Renault, Volvo, BMW, Porsche, Jaguar, Mitsubishi, Nissan, Mercedes-Benz, JAC, Changan) — **this specific claim is inherited from the Week 2 task description and has not been independently re-verified against the live Enel X page in this session**; flagged pending verification rather than asserted as checked | All EVs charge/depart identically in Week 1; no capacity or charge-rate heterogeneity in the results | Label: **simplification / declared limitation**. `heterogeneous_ev_specs: True` plus a brand-mix-derived spec file is a stretch goal, not yet implemented. |
| Arrival and departure time distributions | `ev2gym/data/distribution-of-arrival.csv`, `distribution-of-connection-time.csv` | No — sourced from the Netherlands, not Colombia | Verified directly in `README.md:113,116`: "EV spawn rate, time of stay, and energy required are based on realistic probability distributions *ElaadNL*..." and "EV and Charger characteristics are based on real EVs and chargers existing in NL (*RVO Survey*)" | Every EV's arrival hour, connection duration, and requested energy in Week 1 follows Dutch behavioral patterns | Label: **simplification / declared limitation**. Transferability limitation; no Colombian equivalent dataset is known to exist. |
| Electricity prices | `ev2gym/data/Netherlands_day-ahead-2015-2024.csv` | No — ENTSO-E Dutch day-ahead prices, not CREG-regulated Colombian tariffs | Verified directly: CSV header is `Country,Datetime (UTC),Datetime (Local),Price (EUR/MWhe)` with `Country=Netherlands` on every row; read by `ev2gym/utilities/loaders.py:load_electricity_prices` | `total_profits` in every Week 1/Week 2 result table is computed against Dutch EUR/MWh prices | Label: **simplification / declared limitation**. `total_profits` is usable ONLY as a relative comparison between algorithms under identical prices — it must NOT be reported as a COP revenue figure until Colombian tariffs replace this data source. |
| Grid representation | `simulate_grid: False`, single local transformer, `number_of_transformers: 1` | No — no voltage or feeder constraints modeled | Config inspection; `ev2gym/models/ev2gym_env.py`'s `load_grid()` only builds a `PowerGrid` (pandapower/IEEE 34-bus) when `simulate_grid: True` | Week 1/Week 2 results cannot speak to RETIE's +/-5% voltage band at all | Label: **simplification / declared limitation**, by design (see resolution below), not an oversight. |
| Queueing (EVs waiting for a free port) | N/A — no config key | No — not modeled at all | Verified by reading `ev2gym/utilities/utils.py:477-556` (`EV_spawner`): an arrival is only ever generated for a `(port, timestep)` pair when that exact port is already free at that step (`if occupancy_list[counter, t] == 0 and ...`). There is no queue data structure and no "EV arrived but was rejected" event — demand generation is conditioned on capacity availability by construction. | Objective 1's "waiting time" metric is **not measurable** in the current setup — no EV instance in this model ever represents a vehicle that had to wait | Label: **simplification / declared limitation**. Obtaining a waiting-time metric would require a custom spawn function (new file, not modifying `ev2gym/models/`) that generates arrivals independently of occupancy and explicitly tracks unserved/waiting demand — not yet built. |
| Battery degradation model — ambient temperature | See `ev2gym_thesis/degradation_bogota.py` | Previously no (fixed 25 C assumption); now calibrated to a verified Bogota climate normal and measured with confidence intervals across 100 runs (5 seeds x 10 days) | `theta=298.15K` hard-coded in `ev2gym/models/ev.py:480`, confirmed by inspection (not fed by config or reward — see `00_lab_log.md` 2026-08-12 blocking check). Ambient profiles anchored to IDEAM's own `normales_climatologicas_periodo_1981-2010.xlsx`, station 21205791 (Aeropuerto El Dorado): verified annual mean 13.68 C (not 13.3 C as originally assumed — corrected), mean daily max 19.31 C, mean daily min 7.88 C. | Original Week 1/Week 2 degradation figures (computed at the fixed 25 C default) overstate calendar aging relative to Bogota's actual climate. Paired bootstrap (100 runs, 95% CI): calendar-only change vs. the 25 C default is **-51.75% [-52.01%, -51.48%]** (outdoor), **-45.12% [-45.48%, -44.74%]** (outdoor +5C charging), **-59.17% [-59.21%, -59.13%]** (underground). Since cycling aging is temperature-independent and is 51.92% of total degradation (calendar is 48.08%, 95% CI [47.53%, 48.62%]), the change in the actual reported `battery_degradation` (calendar+cycling) is roughly half as large: **-26.13% [-26.50%, -25.76%]** (outdoor), **-24.37%** (outdoor+5C), **-32.49% [-32.99%, -31.99%]** (underground). See `results/degradation_by_ambient.csv` and `00_lab_log.md`'s 2026-08-12 (continued) entry for the full measurement. | Label: **empirically set inside this project** (climate data is externally validated; the calibration mechanism, delta_T charging-heating sensitivity, and the Xu et al. citation itself are all internal/unverified — see residual limitations below). |

## Resolution: grid-representation scope (Week 2 vs. Objectives 4-5)

This chapter previously flagged an apparent conflict between
`PROJECT_ROADMAP.md` (which lists "Grid model validation" as Week 2 /
Objective 2) and the Week 2 task brief (which framed voltage/feeder work as
belonging to "Phase 3, Objectives 4-5"). Resolved, per the project's own
governing convention, which is the source of truth over both documents:

- **`simulate_grid: False` (single station, own local transformer) is the
  correct setup for Objectives 1-3.** `station_v0_bogota.yaml` and every
  `station_sensitivity/` config stay this way through the algorithm
  comparison in Phase 2.
- **`simulate_grid: True` + the IEEE 34-bus feeder is reserved for
  Objectives 4-5.** It is not "Week 2 work" in the sense of running the
  feeder now — it is a distinct, later phase of the project.
- **There was no real contradiction, only an overly broad reading of
  `PROJECT_ROADMAP.md`.** Week 2's "Grid Model Sanity Check" refers to
  validating the *station-and-local-transformer* model (Objective 2:
  "model station + local transformer + prices and validate against real
  operation") — the feeder is not part of that objective's scope. This
  chapter itself — a documented statement of what is realistic vs.
  simplified in the model — **is** that Week 2 deliverable; it is a
  validation note, not a network study.
- **Why the two scenario types must not mix in the registry:** Phase 2's
  algorithm comparison depends on every row being evaluated under the same
  station model. Introducing `simulate_grid: True` rows into the same
  registry used for that comparison would break comparability across the
  500-run backfill and fragment what is meant to be a single, uniform
  evaluation grid. This is a validity safeguard, not a bureaucratic rule.
- `PROJECT_ROADMAP.md` and `CLAUDE.md` are being corrected in this same
  session so neither continues to suggest feeder work belongs in Week 2
  (diff shown separately, not yet committed).

**De-risking exception, not a scope change:** a single smoke-test run
(`config_name="v2ggrid_smoke_test"`, `notes="pipeline_smoke_test_grid"`)
exercises `simulate_grid: True` + IEEE 34-bus once, purely to confirm the
grid-enabled path still loads, solves, and emits
`voltage_violation`/`voltage_violation_counter` without error — de-risking
Objectives 4-5 now rather than discovering a broken pipeline in Week 6. Its
results are **not interpreted** here and **must be excluded** from every
figure and results table by filtering out `notes == "pipeline_smoke_test_grid"`
(or `config_name == "v2ggrid_smoke_test"`) — see
`scripts/smoke_test_grid.py`.

## Residual limitations of the battery degradation calibration (Deliverable 6)

- **Citation not fully verified.** The implemented model's functional form
  matches a Xu et al. (2018)-type semi-empirical model, but the exact
  7 coefficients (e0, e1, e2, z0-z3) have not been checked line-by-line
  against the primary IEEE Transactions on Smart Grid paper — access to the
  full text was blocked (ResearchGate/MDPI 403, arXiv/Chalmers PDFs
  unreadable by the available tooling). Cite as "a semi-empirical model of
  Xu et al. (2018) type, as implemented by EV2Gym" until verified against
  the primary source.
- **Diurnal timing not IDEAM-verified.** The 06:00 trough / 14:30 peak
  hours used in `ambient_bogota.py` are a general assumption about
  tropical-highland diurnal timing, not sourced from IDEAM's normals file
  (which reports monthly/annual values only, no hourly curve).
- **Underground profile is uncited.** No published normals exist for
  covered/basement charging sites; the +/-0.75 C swing around the verified
  13.68 C mean is a declared modeling choice, not a measured figure.
- **`delta_t_charging_c` (DC-charging self-heating sensitivity) is not a
  validated thermal model.** Implemented only as a flat, declared +5 C
  sensitivity bump during active-charging steps, per the approved
  down-scoped plan — no validated thermal model exists for 50kW DC charging
  at 2600m altitude, and none was built.
- **Absolute degradation figures are not physical predictions for
  Colombia.** `T_acc` (730 days), `b_cap_kwh` (78), `d_dist` (15,000
  km/year) and `G` (0.186 kWh/km) are hard-coded assumptions about a
  generic European reference vehicle's usage pattern, exposed as parameters
  but not recalibrated for Colombia. Only RELATIVE differences — between
  algorithms, or between ambient scenarios, under these same fixed
  assumptions — are reportable claims.
- **Measurement scope: `station_v0_bogota` only, not the full registry.**
  The CI-backed figures above come from `scope=reference` (100 runs: AFAP +
  RoundRobin x 5 seeds x 10 days on `station_v0_bogota.yaml`), not all 502
  registry rows — the full-registry measurement (~65 min estimated) was
  deliberately not run, to save time; the size-sensitivity configs'
  degradation-by-ambient behavior remains unmeasured.
- **Jensen's-gap, measured:** the mean-temperature point-estimate
  underestimates the properly session-integrated calendar degradation by
  **1.01% [0.97%, 1.06%]** (95% CI, n=100) — small but consistent and
  non-zero, confirming the convexity argument rather than assuming it.

## Gurobi / deferred solver-based reference limitation

No module in this codebase depends on Gurobi (no module-level import, no
requirements-file entry -- removed from `requirements.txt`/`setup.py` this
session). `scripts/run_optimal_reference.py` performs a license capability
check on startup and exits cleanly either way; it is self-contained and
never imported elsewhere. The corresponding registry column
(`algorithm_family`) reserves a value for a future solver-based comparison
that stays unused until that comparison actually runs.

**Vocabulary discipline, enforced by `scripts/check_claims.py`:** until a
row using that reserved value exists in the registry, this project's
results chapters may not describe any tested strategy using language that
implies a proven best-possible solution was identified. The permitted
phrasing is "best-performing among the strategies tested". We can rank the
tested strategies against one another and against the unmanaged AFAP
baseline, but we cannot yet quantify how far the best of them sits from
that theoretical ceiling -- this is a scoping decision taken deliberately
and documented, not a hidden gap.

**Free bounds usable without a solver, pending addition to the figure
module:** the total energy requested by all arriving EVs (upper-bounds
served energy under an unconstrained transformer) and the unmanaged AFAP
baseline (lower reference) should appear as horizontal reference lines on
relevant figures, labelled as bounds -- they bracket the achievable region
without identifying the best point within it. Not yet implemented (Deliverable 4).
