# Week 5 — Parameter, Method, and Implementation Justification

**Status: Part A and Part B both complete (2026-09-09).** Written
incrementally, per the brief's instruction ("updated as you go, not at the
end"), hand-maintained rather than script-generated — `scripts/make_week5_handback.py`
(the DOCX handback proper) was not built this pass; this markdown document
is the complete parameter/method/implementation record for both parts.
Part A content is unchanged below; Part B is appended as its own section.

**Scope, stated up front:** Week 5 has two parts. Part A re-bases the
whole project's economics on Colombian prices and applies retroactively to
Weeks 1-4. Part B is the originally-planned Week 5 work (online MPC arm,
consolidated comparison — see `PROJECT_ROADMAP.md`'s Week 5 entry). Part A
is reported and approved before Part B starts, per the brief's explicit
gate.

## Headline finding: the price re-basing changes what this thesis is arguing, not just its units

**This is the result to lead with, not a currency-conversion footnote.**
Weeks 1-4 priced every result in Dutch ENTSO-E day-ahead terms — a market
this project's operator does not participate in. Re-basing to Colombia's
actual flat retail tariff and regulated purchase cost does more than
change the numbers on an axis: it changes which question Objective 4 is
actually answering.

Under a flat retail/purchase spread, gross margin is mathematically
proportional to energy delivered (`margin = energy x (retail - cost)`,
the same positive constant for every algorithm). Two consequences follow,
and both reframe the project:

1. **There is no price-arbitrage signal for this operator to exploit.**
   Every argument this project (and the papers it draws on) might have
   built around time-of-use pricing, price-responsive charging, or
   demand-response revenue does not apply to a Colombian public station
   under the current tariff structure — confirmed quantitatively, not
   assumed (Part A, sections below: the Punta/Fuera-de-Punta spread is
   1.57%, the generation component bounding any arbitrage value is ~52%
   of the CU, and the margin ranking is provably invariant to the retail
   tariff's level).
2. **The economic case for smart charging has to come from somewhere
   else, and Part B identifies exactly where: capacity headroom and
   avoided transformer stress, not money moved by timing.** This is why
   the AFAP-has-the-highest-nominal-margin result (05_algorithm_comparison.md
   S5.1) is not a curiosity — it is the clean demonstration that "who
   earns more" and "who manages the grid constraint well" are different
   questions under this tariff, and Objective 4 has to be argued on the
   second one. The margin-vs-overload-avoided framing (S5.1, S5.8) is
   the direct product of this reframing, and it is what the final
   recommendation (Round Robin) is actually argued on.

**This did not derail the originally planned Week 5 work — it sits
alongside it, and Part B still delivers everything `PROJECT_ROADMAP.md`
assigned to this week.** The online MPC arm the roadmap put in Week 3
(deferred by the Week 3/4 RL-first decision, see that file's own
deviation notes) is built and evaluated this week: `MPC_TrackingG2V` and
`MPC_EnergyMaxG2V`, both audited for causality before being trusted
(section 10's Gate 1). The full cross-algorithm comparison the roadmap
asked for is complete: all 13 arms — 2 heuristics, 1 random control, 6 TD3
checkpoints across 2 reward arms, 2 Gurobi oracle variants, and the 2 new
MPC arms — on one corrected, properly-powered evaluation grid, with a
recommended strategy for Objective 4 argued from that evidence (S5.8).
The price re-basing is what makes the recommendation's *reasoning*
correct; the comparison itself is the deliverable the roadmap always
asked for.

## Part 1 — Parameters and Methods

| Parameter | Value | Label | Justification |
|---|---|---|---|
| `RETAIL_TARIFF_COP_PER_KWH` | `1450.0` | Validated external, single point, no time series | Enel Colombia, "Estas son las estaciones de carga para vehiculos electricos en Bogota" (August 2025). A 2026-09-08 recency search restricted to enelx.com/enel.com.co found no more recent published figure from either source — negative result, logged in `00_lab_log.md`, not substituted with a competitor's price. |
| `RETAIL_TARIFF_SENSITIVITY_FRACTION` | `0.20` | Declared assumption | Sizes the +/-20% band the brief asked for, testing ranking robustness against the 2025 figure being wrong by a reasonable margin — not a literature value. |
| `ENERGY_PURCHASE_COST_COP_PER_KWH` | `865.7615` | Validated external, regulated tariff sheet | Enel Colombia's August 2026 pliego tarifario, SECTOR NO RESIDENCIAL, Nivel de Tension 2, INDUSTRIAL Y COMERCIAL CON CONTRIBUCION / SENCILLA Monomia — extracted and invariant-validated from the stored PDF by `scripts/fetch_enel_tariffs.py`, not the live URL. August is the base case: most recently published sheet as of 2026-09-08 (September not yet published, confirmed against the live listing page), and NOT an average across months since the CU is on a clear upward trend (+19.2% Jan-Aug 2026), not fluctuating around a mean. |
| Contribution factor | `1.20` (with-contribution / sin-contribucion) | Validated external, regulated tariff sheet | Regulatory contribucion de solidaridad for non-residential, non-exempt users. No CREG/Ley 1964 de 2019 exemption for commercial EV charging was found when checked — the with-contribution figure is used without assuming an unverified exemption. |
| Tariff-sheet extraction invariants | (1) six CU components sum to the stated CU; (2) with-contribution = 1.20x without-contribution, extracted from a different table on the same sheet | User-specified, per the brief | These are the checks that identify the correct row was parsed, not decorative — a failure means the parser grabbed the wrong row and the number must not be used. Validated for all 8 months of 2026 (`thesis_docs/sources/enel_tariffs/nivel2_cu_2026_monthly.csv`); both hand-verified reference points (Jan: 605.4596/726.5515; Aug: 721.4679/865.7615) matched exactly. |
| February 2026 CU extraction | Manual visual read of a 600dpi page crop | Declared simplification | The only one of 8 months whose CU table has no extractable text layer in the PDF (confirmed: 0 characters in that page region; rest of the page extracts fine). Values still validated against both invariants above (passed) — not exempted from validation for being manually transcribed. Audit crop saved to `thesis_docs/sources/enel_tariffs/2026-febrero_cu_table_crop.png`. |
| Economics recompute scope | All registry rows (953, all configs), statistics restricted to the 550-row `station_v0_bogota` SEEDS x EVAL_DAYS grid | User-directed (Gate 0 response, item 1), extended by this project to every config | The recompute is a pure function of `total_energy_charged` — nothing about it depends on a row being part of the evaluation grid, the same reasoning the user applied to `station_v0_bogota`'s own 2 legacy rows, extended here to the other 4 sensitivity-sweep configs and the smoke-test row so nothing is left silently inconsistent. |
| Reconciliation method | Implied-price sanity check: `abs(total_profits) / total_energy_charged` must fall inside that row's simulated day's own ENTSO-E [min, max] hourly band | User-directed (Gate 0 response, item 3) | A recompute-and-compare-to-itself check cannot fail in a way that indicates a real problem (pure arithmetic tautology). This check can: it fails if `total_profits` and `total_energy_charged` ever stop describing the same quantity. Result: 953/953 rows pass, 0 problems. |
| Arithmetic-exactness regression test | Week 1 AFAP reference cell (`seed=42`, `2022-01-17`) | User-directed (Gate 0 response, item 3c) | Explicitly a unit test guarding against a constant-swap refactor bug — not presented as the reconciliation. |
| Station realism | Near-future single site (CC Retiro upgraded to DC), not an aggregate of several Enel zones | User-directed (Gate 0 response, item 4) | An aggregate reading is physically incoherent (separate zones, separate connections, cannot share one 100 kW transformer); the capacity constraint under study needs to stay a real constraint, not an artifact of aggregation; the 8-port count already has a real single-site referent (CC Retiro). |
| Connector standard (CCS2) | Declared simplification, justified by market practice, NOT by Res. 40223/2021's regulatory floor | Corrected 2026-09-08 | Reading Res. 40223/2021 Art. 4 directly found the regulation mandates Tipo 1 (AC) / **CCS Combo 1** (DC) as the *minimum* — "CCS Combo 2" does not appear in the resolution's text at all. The project's prior claim ("Res. 40223/2021 sets the CCS2 DC floor") was wrong, not merely uncited, and is corrected in `01_baseline.md`, not kept. CCS2 is still used in the config, justified instead by Enel Colombia's own August 2025 network report confirming CCS1/CCS2/GBT are all in active use. |

## Part 2 — Implementation

### `ev2gym_thesis/prices/` (new subpackage)

**Location:** new top-level subpackage. Never touches `ev2gym/` — EV2Gym
has no G2V revenue concept at all, so Colombian economics can only be a
post-hoc wrapper/analysis layer, never an edit inside the library (per
`CLAUDE.md` rule 1).

#### `ev2gym_thesis/prices/colombia.py`

**Purpose:** the two approved price constants, with declared origins, and
a pure function turning `total_energy_charged` into Colombian-peso
economics for one row.

**Design decision — explicit column names, never `profit`:** the entire
reason this correction was needed is that EV2Gym's own `total_profits`
column's name let a cost be misread as a revenue for four weeks straight.
`compute_row_economics` returns `retail_revenue_cop`,
`energy_purchase_cost_cop`, `gross_margin_cop` — no name in this module
uses the word "profit" alone, on purpose.

**Design decision — flat constants, not a price array:** EV2Gym's own
price pipeline (`load_electricity_prices`) produces an hourly-varying
array. This module deliberately does not, because neither Colombian input
is a time series (the retail tariff is a single published point; the
CU is a monthly-updated flat rate, not an hourly one under the tariff
option this project uses — see the rejected Punta/Fuera-de-Punta
alternative in `05_algorithm_comparison.md`, Part B/section 6 of the
original brief). There is no EV2Gym-native price array being "replaced" —
Gate 0's price-independence finding (below) is what makes a flat constant
sufficient instead of a forecast/array.

```python
def compute_row_economics(total_energy_charged_kwh: float,
                           retail_tariff_cop_per_kwh: float = RETAIL_TARIFF_COP_PER_KWH,
                           purchase_cost_cop_per_kwh: float = ENERGY_PURCHASE_COST_COP_PER_KWH) -> dict:
    revenue = total_energy_charged_kwh * retail_tariff_cop_per_kwh
    cost = total_energy_charged_kwh * purchase_cost_cop_per_kwh
    return {
        "retail_revenue_cop": revenue,
        "energy_purchase_cost_cop": cost,
        "gross_margin_cop": revenue - cost,
    }
```

**Walkthrough:** for any registry row, multiply the already-recorded
`total_energy_charged` by each flat COP/kWh constant to get revenue and
cost; margin is the difference. Valid as a post-hoc recompute (no
re-simulation) only because every algorithm family in the registry was
independently verified to be price-independent (Gate 0 report, section
5.2) — no control decision anywhere in the 552-row `station_v0_bogota`
registry depends on the price series.

### `scripts/fetch_enel_tariffs.py`

**Purpose:** downloads all 8 published 2026 Enel Colombia monthly tariff
sheets, extracts each month's Nivel 2 CU breakdown, validates both
invariants, and writes one CSV row per month.

**Design decision — filenames read from the live listing page's actual
`<a href>` attributes, not constructed from a pattern:** the naming
convention changed mid-year (`tarifario-enel-<mes>-2026.pdf` for
Jan/Feb, `pliego-tarifario-digital-<mes>-2026.pdf` for Mar-Jun, two
one-off names for Jul/Aug) — a guessed pattern would have 404'd on at
least 2 of 8 months.

**Design decision — regex extraction with a documented manual-fallback
path, not OCR:** 7 of 8 months extract cleanly via `pdfplumber` text
extraction (`NIVEL\s*2\s+...` regex on the CU breakdown table, a second
regex on the SECTOR NO RESIDENCIAL table's with-contribution row).
February has no extractable text layer for its CU table specifically —
installing and wiring an OCR pipeline (`pytesseract` + a system Tesseract
binary, unavailable in this environment) for one month's one table was
rejected as disproportionate; a 600dpi crop, read visually and hard-coded
as `FEBRUARY_MANUAL_READING` with a saved audit image, was chosen instead
— cheaper, and the resulting values are still subject to both invariants
programmatically, so a wrong manual read would still be caught.

`scripts/fetch_enel_tariffs.py:167-183` (breakdown-table regex):

```python
breakdown_pattern = (
    r"NIVEL\s*2\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM +
    r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM
)
m = re.search(breakdown_pattern, full_text)
...
gen, trans, dist, com, perd, restr, cu_sin = (_to_float(g) for g in m.groups())
```

**Design decision — the with-contribution figure is extracted
independently from a different table, not computed as `1.20x`:** if the
with-contribution constant were only ever computed as `cu_sin *
1.20`, the "invariant" check would be a tautology (it could never fail).
Extracting it separately from the SECTOR NO RESIDENCIAL table's
"INDUSTRIAL Y ... SENCILLA Monomia" row and then checking it against
`1.20 * cu_sin` is a genuine cross-check between two independent
extractions from the same document — exactly the check the brief asked
for ("these are the checks that caught the correct row in the first
place").

**Design decision — check the live listing for a new month before
downloading, don't guess a September filename:** `check_listing_for_new_month()`
fetches the listing page and diffs its actual 2026 PDF hrefs against the
8 known filenames, rather than constructing and probing a guessed
`.../septiembre-2026.pdf` URL (which the naming-convention churn above
makes unreliable). Confirmed 2026-09-08: no month beyond August is
published yet.

**Walkthrough:** `main()` checks the listing for a new month (informational
only, does not fail the run), downloads each of the 8 known PDFs
(skipping ones already present), extracts each with `extract_month`
(regex, or the February fallback), validates both invariants per month
via `validate_invariants` (raises and exits non-zero on any failure — a
month is never written to the CSV if either invariant fails), and writes
`thesis_docs/sources/enel_tariffs/nivel2_cu_2026_monthly.csv`.

### `ev2gym_thesis/economics_recompute.py`

**Purpose:** the retroactive recompute over the registry, plus the
implied-price sanity check that replaced the originally-proposed (and
correctly rejected by the user) recompute-and-compare-to-itself
reconciliation.

**Design decision — per-day price band from the raw ENTSO-E CSV, not a
global band:** `load_price_day_ranges()` groups
`Netherlands_day-ahead-2015-2024.csv` by calendar date and computes each
day's own `[min, max]` EUR/kWh, rather than one range across the whole
5-year dataset. A global range would be so wide (spanning years of price
volatility, including negative-price hours elsewhere in the dataset) that
almost nothing could ever fail the check — a per-day band is the
tightest check that is still guaranteed to hold whenever
`total_profits` and `total_energy_charged` genuinely describe the same
simulated day.

`ev2gym_thesis/economics_recompute.py:52-83` (`implied_price_check`):

```python
implied_eur_per_kwh = abs(profit) / energy
...
lo, hi = ranges.loc[day, "min"], ranges.loc[day, "max"]
in_range = (lo - tolerance) <= implied_eur_per_kwh <= (hi + tolerance)
```

**Walkthrough:** for every registry row with nonzero
`total_energy_charged`, compute the implied EUR/kWh the simulator
effectively paid and check it against that row's own simulated day's
ENTSO-E band. A zero-energy row with nonzero `total_profits` also fails
(dimensionally impossible under this project's G2V-only config). Result
on the full registry (953 rows, all configs): 0 problems, implied-price
distribution mean 0.2252 EUR/kWh (full detail in `00_lab_log.md`'s
2026-09-08 entry).

### `scripts/recompute_economics_cop.py`

**Purpose:** the runnable entry point — runs the implied-price check
first and stops (non-zero exit, no CSV written) if it finds any problem,
per the user's explicit instruction; only then recomputes and writes
`results/economics_cop.csv`.

### `ev2gym_thesis/tests/test_week5.py`

13 tests, all calling real production functions (per the project's
standing rule extracted from the Week 3 evaluation-bug correction —
never a lookalike reimplementation):

- `TestPriceConstants` (3): the two approved constants and the
  contribution factor match the values above exactly.
- `TestEnelTariffParserInvariants` (5): calls `extract_month`/
  `validate_invariants` from `scripts/fetch_enel_tariffs.py` directly
  against the real stored PDFs for all 8 months (including February's
  manual-reading fallback), plus the two hand-verified reference points.
- `TestRegistryGridCount` (3): the 550-row SEEDS x EVAL_DAYS grid, exactly
  2 legacy `week1_reference_day` rows, 552-row `station_v0_bogota` total —
  pins the numbers the Gate 0 response settled so a future change fails
  loudly instead of silently shifting a table.
- `TestEconomicsRecompute` (2): `compute_row_economics` against the
  hand-computed Week 1 AFAP cell, and a zero-energy edge case.
- `TestImpliedPriceCheck` (1): the real implied-price check against the
  two real Week 1 reference registry rows.

All 13 passing (2026-09-08). (Extended to 20 in Part B, below.)

---

# Part B — MPC arm, evaluation-grid correction, and full comparison

## Part 1 — Parameters and Methods

| Parameter | Value | Label | Justification |
|---|---|---|---|
| MPC classes audited | 8 (`ev2gym/baselines/mpc/`: `V2GProfitMaxOracle`/`V2GProfitMaxLoadsOracle`, `eMPC_V2G`/`eMPC_G2V`, `eMPC_V2G_v2`/`eMPC_G2V_v2`, `OCMF_V2G`/`OCMF_G2V`) | Read from source, not filenames | All rejected as shipped: the two Oracle classes solve the full day in one shot (`control_horizon=env.simulation_length`, self-declared `algo_name="Optimal (Offline)"`) — structurally offline oracles, not MPC; the V2G variants would give this arm discharge capability no other arm in the project has; the shipped price objective is provably inert under Colombia's flat tariff (Part A) and, independently, still read live ENTSO-E prices at decision time. |
| `MPCTrackingG2V` (new class) | `ev2gym_thesis/mpc/tracking_mpc.py` | Empirically set inside this project | No shipped class matches this thesis's Public/PST tracking objective — built by subclassing the unmodified `MPC` base, matching `PowerTrackingErrorrMin`'s exact objective (`Σ(power−setpoint)²`, no `charge_power_potential` clamp) so its oracle gap is measured on the identical optimized quantity. |
| `MPCEnergyMaxG2V` (new wrapper) | `ev2gym_thesis/mpc/energy_max_mpc.py`, `FLAT_PRICE_CONSTANT = 1.0` | Declared assumption | `eMPC_G2V`, unmodified, wrapped to overwrite `ch_prices`/`disch_prices` with a flat constant post-construction — mirrors `oracle/replay_utils.force_g2v`'s exact wrapper discipline. The constant's absolute value is immaterial: `eMPC_G2V`'s battery-capacity constraints already force every EV to reach desired capacity (a hard constraint), so a flat price only removes the solver's preference for WHEN to charge, never WHETHER. |
| MPC control horizon | `10` steps (main grid); sensitivity-checked at `{5, 10, 20}` | Set for this project | Matches the shipped classes' own default; horizon sensitivity (10-seed subset) found a real, monotonic 21% tracking-error improvement from h=10 to h=20 — declared as an open opportunity for a future pass, not silently absorbed into this week's already-large scope. |
| `SEEDS` | `range(0, 50)` (was `[0,1,2,3,4]`) | Empirically set inside this project | Expanding scenario seeds is cheap (evaluation only, no retraining) and was needed once the day axis was found non-independent — see the evaluation-grid correction below. |
| `EVAL_DAYS` | `[(2022,1,17), (2022,3,5)]` (was 10 dates) | Empirically set inside this project | Collapsed from 10 to 2 (one weekday, one weekend) once both the EV-population axis and the power-setpoint axis were confirmed fully redundant within a category for a fixed seed — a genuinely lossless compression after the Gate 4 fix, not before it. |
| `paired_cluster_bootstrap_ci` | `ev2gym_thesis/stats_utils.py` | Empirically set inside this project | Resamples the scenario seed (not the row), added alongside the existing `paired_bootstrap_ci`, never replacing it — this project's evaluation design clusters rows by seed (weekday/weekend rows for one seed are not independent draws), so row-level resampling understates uncertainty. |
| `ENS_rel` definition | `(E_AFAP(s) − E_a(s)) / E_AFAP(s)`, `E` = net delivered energy, paired within seed, gated on the 95% CI upper bound < 0.15 | Declared assumption, adopted this week | Matches the proposal's literal "vs. baseline no gestionado" wording; a point estimate alone does not establish compliance, per the brief's explicit instruction. |
| `ENS_abs` definition | `(R(s) − E_a(s)) / R(s)`, `R(s)` = actual requested energy of EVs departing within the simulation horizon, computed directly from `EVs_profiles` | Declared assumption, diagnostic only | Never the compliance gate — separates "station lacks capacity" (not the case: AFAP's own `ENS_abs` is 0.025%) from "capacity used badly" (the actual finding). |
| Registry schema additions | `day_type`, `scenario_id`, `analysis_row`, `superseded` | Empirically set inside this project | `analysis_row` is the single source of truth for "belongs to a current statistic" — replaces the old notes-marker exclusion in `registry_analysis.main_grid_rows`. All 953 pre-existing rows marked `superseded=True`, kept as provenance, never deleted. |

## Part 2 — Implementation

### `ev2gym/utilities/utils.py::generate_power_setpoints` (library file, changed — the CLAUDE.md rule 1 "real need" case)

**Purpose:** originally wove that simulated day's real ENTSO-E price curve
into the operational power-setpoint target via a price-weighted random
draw. **Design decision — isolate to one array definition:** `prices`
(previously `abs(env.charge_prices[0])`, normalized) is now
`np.ones(env.simulation_length)` — exactly what the normalization
collapses to under a flat price series (this project's actual Colombian
economics), so `loc = 1 − prices = 0` and `scale = min(prices) = 1` for
every EV, and the remaining `np.random.normal` draw is governed purely by
`np.random.seed(self.seed)`. Nothing downstream of this one array altered.
Verified end to end (`RoundRobin`'s `tracking_error`/`total_energy_charged`
byte-identical across two weekday dates, same seed) before trusting any
grid result built on it.

### `ev2gym_thesis/mpc/` (new subpackage)

**`tracking_mpc.py::MPCTrackingG2V`** — subclasses the unmodified `MPC`
base, reuses its causal machinery (`reconstruct_state`, `update_tr_power`,
`calculate_XF_G2V`/`g2v_station_models`/`calculate_InequalityConstraints`
— no discharge variable, so no `force_g2v`-style fix is needed), replaces
the price-linear objective with a fresh Gurobi `QuadExpr`:
`Σ_i (station_power_i − power_setpoint_i)²` over the receding horizon —
a convex QP (sum of squares of a linear combination), no `NonConvex=2`
needed, confirmed by the model solving cleanly without it.

**`energy_max_mpc.py::MPCEnergyMaxG2V`** — see Part 1's table; the
`ch_prices`/`disch_prices` overwrite happens once per `get_action` call's
underlying agent (constructed once per episode), verified identical
across same-category dates after the fix (`ch_prices` byte-identical,
where it previously differed 0.2019 vs. a different value).

### `scripts/evaluate_mpc.py`, `scripts/run_week5_grid.py`

**Design decision — reuse the REAL row-builders from every existing
evaluation script, not reimplementations:** `run_week5_grid.py` imports
`heuristic_run_single` from `backfill_registry.py`, `eval_td3`/
`eval_random_policy` from `evaluate_rl.py`, `oracle_run_single` from
`evaluate_oracle.py`, and `mpc_run_single` from the new `evaluate_mpc.py`
— then adds the four Week 5 schema fields uniformly via one shared
`_with_week5_fields` function, rather than editing four separate row
constructors. **Design decision — `analysis_row`-aware dedup:** a stale
pre-Gate-4 row shares the same `(config, algorithm, seed, eval_day)` key
for seeds 0-4 on the two retained `EVAL_DAYS` — the registry's raw
`load_existing_keys()` would false-skip those cells. `evaluate_mpc.analysis_row_existing_keys`
filters on `analysis_row=="True"` specifically, and every append uses
`force=True` to bypass the raw key check (safe here because the
pre-filter already excludes genuinely-done cells).

**Result:** all 13 arms × 50 seeds × 2 days = 1,300/1,300 rows, 0 errors,
0 skipped, 133.6 min wall-clock (single continuous pass, not a backfill —
the Week 2 duplicate-row lesson applied).

### `scripts/migrate_registry_schema_week5.py`

**Design decision — widen beyond the literal instruction:** the brief
asked to mark "the 552 `station_v0_bogota` rows" superseded; this script
marks all 953 pre-existing rows across every config, since the other
~401 rows (sensitivity-sweep configs, the smoke test) were generated by
the identical buggy `generate_power_setpoints`. Flagged explicitly in the
script's own docstring and the lab log, not applied silently.

### `scripts/analyze_week5_results.py`

Produces the master comparison table, the old-vs-new CI comparison
(same headline pairing — Round Robin vs. AFAP, `total_transformer_overload`
— computed two ways on two datasets, not two different pairings), the
seed-level overload distribution, the optimality gap (cluster-bootstrap
version of the Week 4 pattern), and `ENS_rel`/`ENS_abs` compliance.
**Design decision — compute `R(s)` from real `EVs_profiles`, not a
proxy:** `requested_energy_by_cell()` constructs each of the 100 cells'
env once (no stepping needed — EV population is deterministic and
algorithm-independent) and sums `desired_capacity − battery_capacity_at_arrival`
for EVs departing within the horizon; still-connected-at-horizon-end EVs
are excluded and tracked as a separate diagnostic, per the brief's
declared assumption.

### `scripts/run_horizon_sensitivity.py`, `scripts/run_td3_budget_curve.py`

Both run on 10-seed subsets (seeds 0-9, both day types = 20 cells per
horizon/checkpoint), per the brief's explicit "small subset" instruction
for both deliverables. `run_td3_budget_curve.py` reuses `_TD3Stepper`/
`_run_and_capture` from `evaluate_rl.py` directly — the real production
stepping logic, not a reimplementation — pointed at each of
`TD3_vanilla_ts100`'s intermediate checkpoints (confirmed present at
10k-step intervals before any code was written, clearing the Gate 4
hard-gate check).

### `ev2gym_thesis/tests/test_week5.py` — corrected and extended

`TestRegistryGridCount` was rewritten (it asserted the pre-Gate-4 grid
shape and would fail against the regenerated registry — confirmed by
running it before fixing it, not assumed). Three new test classes added:
`TestSetpointPriceIndependence` (the Gate 4 fix itself, on real
`env_factory`/`MPCEnergyMaxG2V` objects), `TestMPCInformationSet` (pins
the Gate 1 causality declaration — G2V-only, non-causal departure-time
knowledge — on the real resolved agent objects, not by inspection), and
`TestENSComplianceKnownAnswer` (AFAP-vs-itself is a known-answer case for
`ENS_rel`, exactly 0%, checked against the real production CSV output).
**20/20 tests passing.**
