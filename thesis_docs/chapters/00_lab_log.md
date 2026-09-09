# Lab Log

## 2026-09-09 (continued) — Figures regenerated against the Gate 4 grid: 3 real bugs found by visual QA

**All 11 existing figures regenerated (`scripts/make_figures.py`) against
the corrected 13-algorithm, 1300-row grid — full FIGURE_SPECS/renaming
refactor (section 17.1) NOT done this pass, deferred, flagged explicitly
rather than rushed.** The existing figure code handled 13 algorithms
without crashing (it iterates `_algos_present(rows)` dynamically), but
visual QA — opening every regenerated PNG, per this project's own standing
rule — found 3 real bugs, consistent with every prior week's experience
that this step catches things automated tests don't:

1. **`f02_metrics_bars`'s last panel still plotted EV2Gym's `total_profits`,
   labeled "Profits".** Exactly the bug flagged in an earlier review and
   never actually implemented. Fixed: `METRICS_FOR_BARS`/`METRIC_LABELS`
   now use `gross_margin_cop` (merged in from `results/economics_cop.csv`
   via a new `_merge_economics()` step), with a footnote stating the
   non-discrimination caveat (05_algorithm_comparison.md S5.1) directly on
   the figure, not just in the caption sidecar.
2. **`f02`'s and `f04`'s titles were hardcoded to "5-seed x 10-day"**,
   stale since the Gate 4 grid rebuild — silently inconsistent with the
   correct `n=100`/`n=50` counts already computed dynamically next to
   them. Fixed to compute from `len(SEEDS)`/`len(EVAL_DAYS)` so this can't
   drift again.
3. **`f10_optimality_gap` was reading Week 4's own `results/optimality_gap.csv`/
   `oracle_tiebreak_noise_floor.csv`** — the pre-Gate-4 grid's analysis,
   11 algorithms, no MPC arms at all. This is the exact figure meant to
   show this week's headline finding (`MPC_TrackingG2V` closing the
   oracle gap) and was silently showing stale data. Fixed: repointed at
   `results/week5_optimality_gap.csv` (written by
   `scripts/analyze_week5_results.py`) and a newly-computed
   `results/week5_oracle_tiebreak_noise_floor.csv` (reused the real
   `analyze_oracle_noise_floor` function from `analyze_week4_results.py`
   against the new grid, not a reimplementation). Regenerated figure
   confirms the finding visually: `MPC_TrackingG2V`'s bar is barely
   visible above zero on the tracking-error panel, decisively below every
   other online algorithm including Round Robin.

**Side effect, flagged rather than silently left:** reusing
`analyze_oracle_noise_floor` overwrote Week 4's own
`results/oracle_tiebreak_noise_floor.csv` in place (the function writes
to a hardcoded path) with Week 5-grid values (tracking_error floor:
mean 68.37/max 146.44, vs. Week 4's original 60.93/89.35). **Week 4's own
chapter text (`04_oracle_and_pitd3.md` S4.9(4)) already quotes its
specific numbers inline** — that historical claim is unaffected — but the
underlying CSV file no longer matches what that prose cites. A copy of
the current (Week 5) values is preserved at
`results/week5_oracle_tiebreak_noise_floor.csv` for traceability going
forward.

**Remaining figure work, explicitly deferred, not silently dropped:** the
full section 17.1 renaming table (fNN_<what>_<breakdown>_<scope> convention,
approved in an earlier review round), the `FIGURE_SPECS` single-source-of-
truth refactor, `git mv` + `.caption.md` sidecar renames, and the 3 new
figures (f12 cross-family violin, f13 margin-vs-overload — data already
computed in `results/week5_margin_vs_overload.csv`, not yet plotted — f14
TD3 budget-control curve). Only the correctness fixes above were made this
pass, on the EXISTING 11 figures, so nothing downstream cites broken data.

## 2026-09-09 — Week 5 close: horizon sensitivity, TD3 budget curve, `test_week5.py` corrected for the Gate 4 grid shape

**MPC horizon sensitivity (section 14), `MPC_TrackingG2V` only, 10-seed
subset (seeds 0-9, both day types = 20 cells/horizon), horizons {5, 10,
20}:** a real, monotonic difference, not the "no meaningful difference"
case -- tracking error 10,643 (h=5) -> 8,427 (h=10) -> 6,673 (h=20), a
21% reduction from h=10 to h=20, at roughly 2x the per-cell compute cost
(2.84s -> 5.66s). Overload stays exactly 0.00 across all three (the
transformer constraint is hard regardless of planning horizon). h=10
remains the value actually used for every `MPC_TrackingG2V` row in the
main grid (the shipped classes' own default, set before this sensitivity
check ran) -- declared as an open, quantified opportunity (h=20 would
tighten the already-decisive 44.6% oracle gap further, ~9.4 min for a
full-grid rerun) rather than silently accepted or silently re-run this
week. Full data: `results/week5_horizon_sensitivity.csv`.

**TD3 training-budget control (section 15), `TD3_vanilla_ts100`,
checkpoints 10k/20k/30k/40k/50k/60k (confirmed present, no retraining --
the one hard gate in the Gate 4 brief, cleared), 10-seed subset:** no
monotonic improvement with more training. Tracking error is flat/noisy
across the whole range (27,512-31,164, no trend), and transformer overload
gets WORSE at later checkpoints (0.34 kWh at 10k -> 6.75-10.97 kWh at
50k-60k) rather than better. This is evidence AGAINST "the 60,000-timestep
budget is binding and a longer run would close the gap" -- a genuinely
undertrained model should show a noisy but improving trend across
checkpoints; this one doesn't, and overload actively regresses at some
later checkpoints. Consistent with, not contradicted by, the substantial
cross-training-seed dispersion already documented in Weeks 3-4 (up to
63.8% relative spread at this same budget). **Strengthens Week 4's
RL-vs-Round-Robin conclusion rather than qualifying it** -- the gap does
not look like an artifact of insufficient training compute. Full data:
`results/week5_td3_budget_curve.csv`.

Both results written into `05_algorithm_comparison.md` S5.9/S5.10.

**`ev2gym_thesis/tests/test_week5.py`'s `TestRegistryGridCount` corrected
for the Gate 4 grid shape** -- it asserted the pre-Gate-4 structure (550
rows = 11 algorithms x 50 cells) and would have failed (confirmed: ran it
before fixing, 2 failures, both exactly this class) against the
regenerated registry. Corrected to assert the current
`analysis_row=True` shape (1300 rows = 13 algorithms x 100 cells),
`superseded`/`analysis_row` consistency across the whole registry, and
that the 2 legacy Week 1 reference rows are preserved (not deleted) among
the superseded set. Added 3 new test classes per the standing "every test
calls the real production path" rule: `TestSetpointPriceIndependence`
(the Gate 4 fix itself, on the real `env_factory`/`MPCEnergyMaxG2V`
objects, not a reimplementation), `TestMPCInformationSet` (pins the
Gate 1 causality declaration -- both MPC arms are G2V-only and both know
the full EV population's departure times at construction, checked on the
real resolved agent objects), and `TestENSComplianceKnownAnswer`
(AFAP-vs-itself is a known-answer case for `ENS_rel`, exactly 0%, checked
against the real `results/week5_ens_compliance.csv` production output).
**20/20 tests passing.**

## 2026-09-08/09 — Gate 4: `generate_power_setpoints` fixed, grid regenerated at 50 seeds x 2 days, Week 5 Part B analysis complete

**Diagnostic (per the Gate 4 review) confirmed both halves before any fix
was written:** `env.charge_prices` for `station_v0_bogota` is still the
live Netherlands ENTSO-E series (verified: Jan-17 vs Feb-14 differ, e.g.
-0.2019 vs -0.1601 at step 0) -- Part A's Colombian recompute
(`ev2gym_thesis/economics_recompute.py`) only ever added a derived table,
it never touched `ev2gym/utilities/loaders.py` or re-simulated anything.
`generate_power_setpoints()` genuinely produced different setpoints for
the same seed on different same-category dates as a direct consequence.
All 953 pre-existing registry rows predate Part A by weeks (git commits
from Weeks 1-4) -- confirmed by construction, not inference.

**Fix 1 -- `ev2gym/utilities/utils.py::generate_power_setpoints`,** per
the user's pre-committed decision: the `prices` array (previously
`abs(env.charge_prices[0])` normalized) is now a constant array of 1s --
exactly what the normalization collapses to under a flat price series
(this project's actual Colombian economics). `loc = 1 - prices = 0`,
`scale = min(prices) = 1` for every EV, so the remaining
`np.random.normal` draw is governed purely by `np.random.seed(self.seed)`.
Verified end to end, not just at the array level: `RoundRobin`'s
`tracking_error` and `total_energy_charged` are now byte-identical across
two weekday dates for the same seed (11467.148... on both, exactly).
Isolated to this one array definition (CLAUDE.md rule 1's "real need"
case), nothing downstream of it altered.

**Fix 2 (found while building the grid runner, not anticipated at Gate 1/2)
-- `MPC_EnergyMaxG2V` had the identical problem one level up:** `eMPC_G2V`'s
objective reads `env.charge_prices` directly in the unmodified
`MPC.__init__` (`ev2gym/baselines/mpc/mpc.py:200-207`), so this arm's
schedule was still being shaped by genuine Dutch day-ahead prices, date to
date, even after Fix 1. Verified before assuming it (ch_prices differed
0.2019 vs a different value across two weekday dates). Fixed via a new
wrapper, `ev2gym_thesis/mpc/energy_max_mpc.py:MPCEnergyMaxG2V` --
subclasses the unmodified `eMPC_G2V`, overwrites `ch_prices`/`disch_prices`
with a flat constant (1.0) after construction, mirroring
`oracle/replay_utils.force_g2v`'s exact wrapper discipline. Verified end
to end: `MPCEnergyMaxG2V` now byte-identical across same-category dates
(tracking_error=44624.267..., energy=214.406... on both). Also refined
this arm's own description while fixing it: because `eMPC_G2V`'s battery-
capacity constraints already force every EV to reach desired capacity
(confirmed: `average_user_satisfaction=1.0` at Gate 2's calibration), a
flat price does not change WHETHER energy is delivered, only that the
solver has no preference for WHEN -- "meet AFAP's own charging
requirement without ever exceeding the transformer, tie-broken arbitrarily
by the solver" is more precise than the Gate 1 shorthand
("energy-maximizer"), corrected in `05_algorithm_comparison.md` S5.5.

**Registry schema migration (`scripts/migrate_registry_schema_week5.py`):**
added `day_type`/`scenario_id`/`analysis_row`/`superseded` to all 953
pre-existing rows. All 953 marked `superseded=True`, `analysis_row=False`
-- widened beyond the literal "552 station_v0_bogota rows" instruction to
every config (the other ~401 rows were generated by the identical buggy
function and are equally stale), flagged explicitly rather than applied
silently. Backup at `results/master_results_prefix_week5_setpoint_fix.csv`.
`ev2gym_thesis/eval_protocol.py` updated: `SEEDS=range(0,50)`,
`EVAL_DAYS=[(2022,1,17), (2022,3,5)]`, old values kept in comments, new
`day_type()` helper added (classifies by `datetime.weekday()`, matching
EV2Gym's own branch exactly, not a separate hardcoded list).
`ev2gym_thesis/registry_analysis.py::main_grid_rows` corrected to filter
on `analysis_row=="True"` instead of the old notes-marker exclusion.

**`stats_utils.paired_cluster_bootstrap_ci` added alongside the existing
`paired_bootstrap_ci`, not replacing it.** Resamples the scenario SEED
(not the row), carrying both of a seed's rows together -- per the user's
"conservative regardless of what check 2 finds" directive. 5 new tests,
including the discriminating one (duplicated-row-within-cluster data
must produce a WIDER interval under the cluster version than the naive
one on the identical data) -- all passing.

**Grid regenerated in one homogeneous pass, not a backfill**
(`scripts/run_week5_grid.py --execute`): all 13 arms (AFAP, RoundRobin,
RandomPolicy, 6 TD3 checkpoints, both Gurobi oracle variants, both new
MPC arms) x 50 seeds x 2 days = **1300/1300 rows, 0 errors, 0 skipped**.
133.6 min actual (vs. ~81 min single-cell-calibration estimate -- Gurobi
solve times ran heavier at full scale than the single reference cell
suggested; nothing failed). New scripts: `scripts/evaluate_mpc.py`
(standalone MPC evaluator, `--variant {tracking,energy_max}`),
`scripts/run_week5_grid.py` (consolidated runner, reuses the REAL
row-builders from `backfill_registry.py`/`evaluate_rl.py`/`evaluate_oracle.py`
directly, not reimplementations -- adds the 4 new Week 5 fields uniformly).
Dedup is `analysis_row`-aware (`scripts/evaluate_mpc.py::analysis_row_existing_keys`),
since a stale superseded row sharing the same
`(config, algorithm, seed, eval_day)` key would otherwise cause a false
skip against the raw key-based `load_existing_keys()`.

**Colombian economics recomputed to cover the new rows**
(`scripts/recompute_economics_cop.py`, rerun): 2253 total rows in
`results/economics_cop.csv`, implied-price check still 0 problems on
every row including the new 1300.

**Headline findings, full numbers in `05_algorithm_comparison.md` S5.6:**
1. AFAP's transformer overload, now on 50 real independent seeds (not 5):
   mean 14.22 kWh, median 10.32 kWh (no longer zero), **28/50 seeds (56%)
   show real overload** -- a materially larger, better-characterized risk
   than the 5-seed sample suggested (was: mean 5.33 kWh, only 1/5 seeds).
2. Old-vs-new CI on RoundRobin-vs-AFAP overload: naive 5-seed interval
   [-12.26, 0.00], cluster-corrected 50-seed interval [-19.25, -9.62] --
   narrower in absolute width (9.64 vs 12.26) because n went from 5 to 50
   clusters despite the correction, but the OLD interval's upper bound
   touched zero (not significant) while the NEW one excludes zero
   decisively -- the 5-seed sample was underpowered, not just uncorrected.
3. **`MPC_TrackingG2V` closes the gap Week 4 called unclosed:** 44.6% gap
   to `Optimal_Oracle_Tracking` on `tracking_error`, decisively beating
   Round Robin's 128.8% (itself still far ahead of every RL arm,
   420-514%, `RandomPolicy` 571%, `MPC_EnergyMaxG2V` 627%, AFAP worst at
   848%). Framed in the chapter as a value-of-information upper bound
   (the arm knows connected-EV departure times and near-term arrivals no
   causal arm has), not a deployable recommendation -- Round Robin remains
   the best CAUSAL arm on this evidence.
4. Every one of 13 arms clears both quantitative targets by a wide margin
   on the full 50-seed grid: `average_user_satisfaction` > 90% for all
   (worst: `TD3_vanilla_ts100` at 97.98%), and `ENS_rel`'s 95%
   cluster-bootstrap CI upper bound is under 15% for all (worst:
   `TD3_vanilla_ts100`/`ts101` at ~12.1%/12.0%). `ENS_abs` diagnostic
   (now computed properly from each cell's actual requested energy `R(s)`,
   not a proxy) confirms the station is not fleet-level inadequate: AFAP's
   own `ENS_abs` is 0.025%.

**Not yet in this entry -- horizon sensitivity and the TD3 budget curve
are running in the background as this entry is written; their numbers go
into a follow-up entry once complete, per the report's own structure.**

## 2026-09-08 (continued) — Part A acceptance review: AFAP margin headline formalized, Week 1 reference cell reconciled, CCS2 correction sharpened

**Item 1 — the AFAP-highest-margin result was in Part A's report but not
stated as the finding it is; corrected by writing it up properly, not by
recomputing anything.** `05_algorithm_comparison.md` S5.1 now states the
formal proposition (`margin_i = E_i x (p - c)`, flat `p`/`c` shared by
every algorithm => margin ranking = energy-delivered ranking for any
`p > c`, matching the already-measured +/-20% invariance from Part A) as a
named result, explains why both oracle variants sit below AFAP/Round Robin
on margin (they optimize tracking error, not energy delivered — expected,
not a bug), states gross margin is retired as a ranking metric (reported
for Objective 1, never used to rank strategies, with a standard caption
note), and replaces the Objective 4 trade-off figure originally specified
in section 17 of the brief (satisfaction vs. profit, which collapses to a
line under the proposition above) with **margin foregone vs. transformer
overload avoided, both relative to AFAP** — computed on the 550-row main
grid: Round Robin eliminates 100% of AFAP's overload for 88.6 COP/day
(16.6 COP/kWh avoided); both oracle variants also fully eliminate it at
26-111 COP/kWh; every RL arm is 60x-670x more expensive per kWh avoided
than Round Robin while NOT fully eliminating the overload and costing
real satisfaction (97.6-99.2% vs. 100% for every heuristic/oracle). This
table is now this chapter's actual Objective 4 evidence, not a robustness
note attached to a different figure.

**Item 2 — Week 1 reference cell reconciled: Part A's reported numbers
(14 EVs, 240.93/240.81 kWh, 0.132/0.0 kWh overload) are correct and are
the project's current standing facts; the "11 EVs/42.17 kWh, 13 EVs/0.00 kWh"
figures quoted in the review are the abandoned pre-project reference, not
a value any current project document asserts.** Checked directly, not
from memory: `CLAUDE.md` (line 174-180), `01_baseline.md` §1.3, and
`results/master_results.csv`'s own `seed=42, eval_day=2022-01-17` row all
agree exactly at 14 EVs / 240.93 / 240.81 kWh / 0.132 / 0.0 kWh overload.
The 11/13 figures trace to this file's own 2026-08-05 entry ("Week 1
baseline reproduction attempt"): "previously reported reference values"
of unknown, unrecorded origin, explicitly noted at the time as
unreproducible from the config alone (no seed on record). That same
session's first reproduction attempt (unedited 150-station config)
produced 92 EVs — matching neither reference — and was diagnosed as the
wrong config; once corrected to the 8-station scenario, the re-run
produced the 14-EV figures, explicitly flagged then as NOT matching the
11/13 reference, with only the qualitative pattern and rough order of
magnitude used as validation. `CLAUDE.md`'s 2026-08-11 "CONFIRMED" entry
is the user's own later ratification of the 14-EV figures — the 11/13
figures were superseded five weeks before this session, not overwritten
silently now. No project file currently states 11/42.17 or 13/0.00; full
account in `05_algorithm_comparison.md` S5.2 so this doesn't need
re-litigating in a future session.

**Item 3 — CCS2 correction sharpened and propagated beyond `01_baseline.md`
(the only file corrected in the first pass).** Res. 40223/2021 Art. 4 is a
*minimum*, not an exclusive standard: it requires Tipo 1 (AC) and CCS
Combo 1 (DC) to be present, and neither prohibits nor mentions CCS Combo
2. Restated precisely per the review: "a DC station equipped only with
CCS Combo 2 would not, by itself, satisfy Article 4's minimum" — not "the
regulatory floor is weaker than the config," which implied the wrong
comparison. Scope note added (Art. 4 Paragrafo 3: binds only stations
installed from 12 months after entry into force). Propagated to every
other location carrying the original wrong claim, found by a fresh
repo-wide grep for "Combo 2"/"CCS2": `CLAUDE.md` line 65 (Project Identity
boilerplate, corrected in place with a bracketed note, since this is
exactly the standing-facts file the correction exists to protect),
`02_model_validation.md`'s connector-and-rated-power table row (struck
through, corrected in place), and `PROJECT_ROADMAP.md`'s Week 6
infrastructure-guidelines checklist item (bracketed correction, so Week 6
doesn't inherit the wrong citation). **Also checked the anteproyecto**
(`Project_Proposal_EN_Santiago_Reyes.docx`, paragraphs 16 and 40): mentions
CCS Combo 2 twice as a general interoperability preference, without citing
Res. 40223/2021 by article in either instance — flagged in
`05_algorithm_comparison.md` S5.3 for the record, not edited (an
already-submitted document, out of scope for this project's
chapter-correction convention, and it doesn't make the specific wrong
citation the chapters made).

**Minor — February 2026's CU row labeled with its differing provenance in
the annex table**, not just in the fetch script's own comments:
`05_algorithm_comparison.md` S5.4's annex table bolds the February row and
states directly in the table that its values came from a 600dpi visual
crop read, not text extraction, alongside a pointer to the saved audit
image — passed both invariants, stays in the annex (not the base case)
exactly as before.

## 2026-09-08 — Week 5 Part A: Colombian price re-basing, `total_profits` corrected, Gate 0 done (branch `semana-5`)

**Branch `semana-5` created from an up-to-date `main`.** Registry state
confirmed before touching anything: 552 rows for `config_name ==
station_v0_bogota`, not the expected 550 — resolved, not a real
discrepancy: the extra 2 are AFAP's and Round Robin's original Week 1
single-day reference cells (`seed=42`, `eval_day=2022-01-17`,
`notes="week1_reference_day"`), predating the `SEEDS`(5)x`EVAL_DAYS`(10)
protocol adopted from Week 2 onward. The `SEEDS x EVAL_DAYS` grid itself is
exactly 550 rows = 11 algorithms x 50 cells. Pinned by
`ev2gym_thesis/tests/test_week5.py`'s `TestRegistryGridCount` (3 tests: the
550-row grid, exactly 2 legacy rows, both by the expected algorithms) so
this can't silently shift.

**Gate 0 audit — `total_profits` is a cost, not a profit or revenue, and
Weeks 1-4 read it as the latter.** Traced to source
(`ev2gym/models/ev_charger.py:178,194,207`,
`ev2gym/utilities/loaders.py:392-461`): `charge_price` is the ENTSO-E
Dutch day-ahead price, negated at load time; `total_profits` sums
`abs(actual_energy) * charge_price` (always <=0, charging) plus
`abs(actual_energy) * discharge_price` (>=0, discharging, never triggered
since `v2g_enabled: False` in `station_v0_bogota.yaml`). Verified
empirically, not just structurally: every one of the (then-)552
`station_v0_bogota` registry rows has `total_profits < 0`. **Consequence:
EV2Gym has no concept of a retail tariff charged to the driver at all** --
`total_profits` under this project's G2V-only config is literally the
negated cost of energy purchased, nothing else. Every "profit"/
"profitability" mention describing this column in `01_baseline.md`,
`02_model_validation.md`, `03_algorithms.md`, `03_rl_baseline.md`, and
`04_oracle_and_pitd3.md` corrected forward with a dated blockquote note
(not rewritten in place, per this project's standing correction
convention) -- see each file's own 2026-09-08 note.
`ev2gym_thesis/registry.py` gained a `total_profits_semantics` doc comment
at `STATS_COLUMNS` as the canonical explanation; the registry column
itself is left untouched (raw simulator output, EUR, ENTSO-E-priced) --
documented, not mutated, so the audit trail survives.

**Price-independence verified for every arm before trusting a post-hoc
recompute, not assumed.** Read every reward/state/objective function from
source: `ev2gym/baselines/heuristics.py` (AFAP, Round Robin) has zero
`price`/`cost` references; `ev2gym/rl_agent/reward.py`'s
`SquaredTrackingErrorReward` and `SqTrError_TrPenalty_UserIncentives`
(TD3_TrackingOnly and TD3_vanilla respectively) reference only
`power_setpoints`/`charge_power_potential`/`current_power_usage`/
transformer-overload/user-satisfaction, no price term; `PublicPST`
(`ev2gym/rl_agent/state.py`) carries no price observation either;
`ev2gym/baselines/gurobi_models/tracking_error.py` (both oracle variants'
base model) has zero `price`/`cost` references, consistent with S4.2's
already-documented objective. RandomPolicy samples uniformly, trivially
price-independent. **Every arm in the registry is price-independent** --
no control decision anywhere in the 552 rows would change under a
different price series, so all Colombian economics can be computed post
hoc from each row's already-recorded `total_energy_charged`, with no
re-simulation.

**Colombian price constants approved and implemented
(`ev2gym_thesis/prices/colombia.py`):**
- `RETAIL_TARIFF_COP_PER_KWH = 1450.0` -- Enel Colombia, August 2025
  article ("La recarga tendra un valor de 1.450 pesos por kilovatio, que
  puede variar segun el costo de la energia."). **Recency search performed
  2026-09-08, restricted to enelx.com and enel.com.co only, per the
  brief's explicit instruction not to substitute a competitor's (Terpel
  Voltex/Celsia/Primax) price: no more recent Enel X or Enel Colombia
  public EV charging retail price was found -- a negative result, logged
  here as instructed, not silently worked around.** One tangential,
  unadopted finding from the same search: an older (~April 2023) Enel X
  page describes public charging as free ("no cost, part of the promotion
  of electric mobility") -- predates the August 2025 article and is not
  used, flagged here only because it's a real, if outdated, conflicting
  data point a future session should not rediscover and be confused by.
  The August 2025 figure is carried forward paired with a 2026 cost, which
  understates operator margin by construction -- every profitability
  result this project reports from Week 5 onward is a **lower bound**, not
  a central estimate.
- `ENERGY_PURCHASE_COST_COP_PER_KWH = 865.7615` -- Enel Colombia's August
  2026 regulated tariff sheet, SECTOR NO RESIDENCIAL, Nivel de Tension 2
  (11.4 y 13.2 kV), INDUSTRIAL Y COMERCIAL CON CONTRIBUCION / SENCILLA
  Monomia. Confirmed September 2026 is not yet published (checked the live
  listing page directly, 2026-09-08 -- `scripts/fetch_enel_tariffs.py`'s
  `check_listing_for_new_month()`), so August stands as the base case per
  the brief.

**`scripts/fetch_enel_tariffs.py` built and run: 8/8 months of 2026
downloaded, extracted, and invariant-validated.** Stores PDFs in
`thesis_docs/sources/enel_tariffs/`, retrieval date recorded per file.
Both invariants (six CU components sum to the stated CU; with-contribution
= 1.20x without-contribution, extracted from a *different* table on the
same sheet, not merely computed) hold for all 8 months, matching both
hand-verified reference points exactly: January (605.4596 / 726.5515) and
August (721.4679 / 865.7615). **One month, February, has no extractable
text layer for its CU table** (confirmed: `pdfplumber` finds 0 characters
in that specific table region, though the rest of the page extracts fine
-- the table appears to be rendered as vector paths/outlined fonts, not
selectable text). Handled via a 600dpi crop of the rendered page, read
visually and hard-coded as `FEBRUARY_MANUAL_READING` in the script, saved
to `thesis_docs/sources/enel_tariffs/2026-febrero_cu_table_crop.png` for
audit -- and still validated against both invariants like every other
month (passed: 685.9857 sin contribucion, 823.1828 con contribucion,
685.9857 x 1.20 = 823.18284). Full monthly series in
`thesis_docs/sources/enel_tariffs/nivel2_cu_2026_monthly.csv`. **The
series confirms the brief's own finding:** CU rose from 605.4596
(January) to 721.4679 (August), +19.2%, driven by Generacion
(247.1961 -> 374.9931, +51.7%) while Restricciones fell
(17.7949 -> 6.0877) -- January is not representative and was correctly
excluded as the base case.

**Reconciliation replaced per the Gate 0 response -- the recompute-and-
compare-to-itself check does not reconcile anything, an implied-price
sanity check does.** For all 953 registry rows (all configs, not just
`station_v0_bogota`), computed `|total_profits| / total_energy_charged`
and checked it falls inside that row's simulated day's own ENTSO-E
[min, max] hourly band (`ev2gym_thesis/economics_recompute.py`'s
`implied_price_check`) -- catches a real problem if `total_profits` and
`total_energy_charged` ever stopped describing the same quantity, unlike a
tautological recompute-vs-recompute check. **Result: 953/953 rows pass, 0
problems** (no zero-energy-nonzero-profit rows, no missing price days, no
out-of-band implied price). Distribution, all rows:

| | value |
|---|---:|
| count | 953 |
| mean | 0.2252 EUR/kWh |
| std | 0.1434 |
| min | 0.0058 |
| 25% | 0.1475 |
| 50% (median) | 0.1955 |
| 75% | 0.2229 |
| max | 0.6761 |

Restricted to the 552 `station_v0_bogota` rows: mean 0.2292, min 0.0444,
max 0.6761 -- consistent, no surprises. Kept as an arithmetic-exactness
regression test (`TestEconomicsRecompute.test_week1_reference_cell_afap_hand_computed`
in `test_week5.py`) on the Week 1 AFAP reference cell, per the brief's
item (c) -- this is a unit test guarding against a constant-swap refactor
bug, explicitly not presented as the reconciliation.

**Why the old (EUR, ENTSO-E) and new (COP, flat CU) costs will never
numerically reconcile, documented so a future session doesn't "fix" a
non-bug:** the old figure is Sigma_t(energy_t x price_t) with an
hourly-varying price; the new figure is total_energy x flat_CU. These are
structurally different integrals of different price series in different
currencies -- not two estimates of the same number. Full statement in
`thesis_docs/Week5_Parameter_Method_and_Implementation_Justification.md`.

**Recompute run (`scripts/recompute_economics_cop.py`): 953 rows written
to `results/economics_cop.csv`** (derived table, joined 1:1 on
`(config_name, algorithm, seed, eval_day)`, no new registry columns, per
the approved plan). Gross margin (COP), `station_v0_bogota` main grid, by
algorithm (mean, n=50-51):

| algorithm | mean gross margin (COP) |
|---|---:|
| ChargeAsFastAsPossible | 115,419 |
| RoundRobin | 115,331 |
| RandomPolicy | 114,854 |
| Optimal_Oracle_Balanced | 114,774 |
| Optimal_Oracle_Tracking | 114,320 |
| TD3_TrackingOnly_ts100 | 110,127 |
| TD3_vanilla_ts102 | 108,027 |
| TD3_TrackingOnly_ts102 | 105,521 |
| TD3_TrackingOnly_ts101 | 101,917 |
| TD3_vanilla_ts101 | 101,740 |
| TD3_vanilla_ts100 | 100,079 |

**The two Week 1 reference cells specifically** (`seed=42`,
`eval_day=2022-01-17`, `notes="week1_reference_day"` -- the cell
`01_baseline.md`'s table quotes: 14 EVs served, 240.93/240.81 kWh charged,
0.132/0.0 kWh overload, matching that chapter exactly, confirming this is
the right row):

| algorithm | energy charged (kWh) | retail revenue (COP) | purchase cost (COP) | gross margin (COP) |
|---|---:|---:|---:|---:|
| ChargeAsFastAsPossible | 240.9269 | 349,344 | 208,585 | **140,759** |
| RoundRobin | 240.8065 | 349,169 | 208,481 | **140,688** |

**+/-20% retail tariff sensitivity: the algorithm ranking by gross margin
is invariant -- not only at +/-20%, but for any tariff above the purchase
cost, which is a structural property, not an empirical coincidence.**
Since `gross_margin_i = energy_i x (tariff - cost)` and `tariff` and
`cost` are the same flat constant for every algorithm, the margin ranking
is always identical to the ranking by `total_energy_charged` alone, for
any `tariff > cost`. Verified computationally at 1,160 / 1,450 / 1,740
COP/kWh (+/-20%): identical ordering all three times (AFAP >
RandomPolicy > RoundRobin > Optimal_Oracle_Balanced > Optimal_Oracle_Tracking
> TD3_TrackingOnly_ts100 > ... > TD3_vanilla_ts100). This is itself a
finding for `05_algorithm_comparison.md`, not just a robustness check: it
formally confirms section 7's "no intraday/no cross-tariff price signal"
result -- under Colombia's flat-tariff structure, an operator-economics
ranking is entirely a ranking of energy delivered, with no algorithm able
to win on unit economics alone.

**Station realism (user-directed, near-future single site): adopted as
instructed**, 8 DC ports read as a plausible near-future upgrade of a
single real site (CC Retiro, 8 ports AC-only today per the existing Enel X
inventory in `01_baseline.md` S1.1), not an aggregate of several
geographically separate zones. The two Enel inventories now in the project
(67 chargers/21 sites, Enel X page, consulted 2026-08-11; 15 points/6
zones, Enel Colombia article, August 2025) reconciled in one paragraph in
`01_baseline.md` per the user's instruction -- see that chapter's own
2026-09-08 update.

**CCS2 citation check found a real error in the existing chapter, not just
a missing citation -- corrected, not silently left.** Reading Articulo 4o
of Res. 40223/2021 directly
(`thesis_docs/references/regulatory/res_40223_2021.html`): the resolution
mandates **Tipo 1 (SAE J1772) for AC and CCS Combo 1 for DC** as the
minimum connector standard. **"CCS Combo 2" does not appear anywhere in
the resolution's text** -- the chapter's prior claim that Res. 40223/2021
sets "the DC charging floor" at CCS2 was wrong, not merely unsupported.
Corrected in `01_baseline.md` per the user's explicit instruction ("weaken
the claim rather than the citation"): the regulatory floor is CCS Combo 1
(weaker than this project's config), and `station_v0_bogota`'s CCS2
assumption is now justified on market-practice grounds instead (Enel
Colombia's August 2025 network report confirms CCS1/CCS2/GBT all in
active use) -- a declared simplification, not a regulatory-floor claim.
Scope also added: Art. 4 Paragrafo 3 binds only stations installed after
12 months from the resolution's entry into force, not all infrastructure
regardless of install date.

**Tests: `ev2gym_thesis/tests/test_week5.py`, 13/13 passing.** Covers the
price constants against the approved values, the tariff parser's two
invariants against the real stored PDFs (not fixtures) for all 8 months
including February's manual-reading fallback, the registry grid-count
assertions (550/552/2), the economics recompute against the hand-computed
Week 1 AFAP cell, and the implied-price check against the real registry
rows for both Week 1 reference cells.

**Not yet done, carried into the Part A close-out report:** the
`Week5_Parameter_Method_and_Implementation_Justification.md` write-up,
the `05_algorithm_comparison.md` chapter content proper (the corrections
above are dated blockquotes in the existing Weeks 1-4 chapters, not yet
the new chapter itself), and `CLAUDE.md`'s stale "Current Phase" section.
Per the brief: stopping to report Part A results now, before touching Part
B (the MPC arm / consolidated comparison) at all.

## 2026-08-20 — Week 4 acceptance review: git rule correction, verdict revision, gitignore bug

**Standing git rule corrected (`CLAUDE.md` rule 4, `PROJECT_ROADMAP.md`'s
Git Discipline Checklist): Claude Code never runs `git commit`/`merge`/
`tag`/`push` — the user does, from a proposed commit plan.** An earlier
brief's "commit early/often" instruction was wrong about this project's
workflow; both files corrected in place (old text struck through, not
deleted, per the project's own correction convention).

**Real bug found while auditing for anything mis-gitignored: all 5 of
Entregable 8's analysis CSVs were silently swallowed by a stale
`/results/*` allowlist.** `results/optimality_gap.csv`,
`oracle_tiebreak_noise_floor.csv`, `reward_ablation_bootstrap.csv`,
`reward_ablation_vs_baselines.csv`, and `trackingonly_train_seed_dispersion.csv`
all showed `!!` (ignored) under `git status --ignored` and matched
`.gitignore`'s blanket `/results/*` rule -- the per-file allowlist below it
was never extended for this week's new outputs, so these files would have
been silently absent from any commit despite being the actual evidence
behind this chapter's S4.9 numbers. Fixed: added all 5 to the allowlist;
also found and removed an exact duplicate of the entire `/results/*` +
allowlist block (harmless -- gitignore patterns are idempotent -- but
confusing to maintain in two places), consolidating to one copy. Confirmed
fixed via `git check-ignore -v` on each file (no longer matches) and
`git status --short results/` (all 5 now show `??`, ready to stage).

**Also renamed a CSV column for real stackability, not just described the
mismatch:** `reward_ablation_vs_baselines.csv`'s leading column was
`trackingonly_algorithm`; Week 3's `rl_vs_baseline_bootstrap.csv` uses
`td3_algorithm` for the same role. Renamed to match exactly
(`scripts/analyze_week4_results.py`), re-ran the script to confirm
identical values under the new column name -- the two CSVs now
concatenate directly (`pandas.concat`/CSV-append) into one comparison
table without a rename step.

**S4.9/S4.10's first draft was reviewed and found to overstate one result
and understate another -- both corrected in place, not quietly touched
up:**
1. **Ablation verdict softened from "retroactively validated" to a stated
   trade-off.** `TD3_vanilla` wins on tracking/overload/degradation;
   `TD3_TrackingOnly` wins on profit and both satisfaction metrics -- two
   of this thesis's three declared objective axes. Added a labeled
   **hypothesis** (not an established mechanism) for the counterintuitive
   direction: the composite reward's extra terms may act as
   shaping/regularization aiding credit assignment under the reduced
   60k-timestep budget, testable via a longer single-seed run -- out of
   scope this week, named as future work rather than run.
2. **The RL-vs-Round-Robin gap-to-oracle finding promoted to the week's
   stated headline**, with an explicit budget-boundedness caveat (*under a
   60,000-timestep CPU budget*, not a general RL-vs-heuristic claim) and
   its consequence for Objective 4 (on current evidence, the recommended
   strategy is Round Robin, not RL) surfaced now rather than left for
   Week 6.
3. **The oracle tie-break noise floor redone as a per-metric table**
   (previously one global "79x the floor" statement) -- `tracking_error`'s
   gap is genuinely far outside its floor (79x), but `average_/
   min_energy_user_satisfaction` have an EXACTLY zero floor, meaning
   "real" there doesn't mean "large": Round Robin's own gap on both is
   real but small (0.29 pp / 0.047 pp), distinct from the RL arms' larger,
   unambiguous gaps (0.8-21.75 pp). `energy_tracking_error` and
   `total_profits` have a measurable floor but were never included in
   S4.2's restricted gap-metric set -- flagged as an open scope question,
   not silently omitted from the table.

**Energy-not-served target: a mapping proposed, not adopted.** The
approved proposal defines the target as "error de energia no servida
<15% vs. baseline no gestionado" -- narrower than "undefined." Read
`ev2gym/models/ev.py:204-214` and `ev2gym/utilities/utils.py:58-62` from
source (not guessed): proposed `(1 - average_user_satisfaction) x 100`
(unserved energy relative to each EV's own requested `desired_capacity`,
EV2Gym's existing `get_user_satisfaction()`), with `energy_user_satisfaction`
(normalized against `max_energy_AFAP` instead of desired capacity) kept as
a rejected-but-computed cross-check, and a fleet-aggregate
`total_energy_charged`-based alternative rejected for needing new
uncomputed infrastructure and discarding per-EV worst-case information.
Computed for every arm: worst case 2.57% (`TD3_vanilla_ts100`, cross-check
definition), over 5x under the 15% threshold under either candidate --
every algorithm/arm tested through Week 4 clears the target comfortably.
Recorded as a labeled assumption in `04_oracle_and_pitd3.md` S4.9 for Week
5 to adopt or revise, per the brief's explicit instruction not to close
Week 4 on it.

**Also fixed while re-reading the chapter for staleness:** S4.2 still said
the balanced oracle variant was "not yet implemented" -- stale since S4.6/
S4.7 fully implemented and evaluated it days earlier; corrected in place.

Full corrected text in `thesis_docs/chapters/04_oracle_and_pitd3.md`
(S4.0's status block, S4.2, S4.9, S4.10) -- nothing below this entry in
the chapter's own body was removed, only corrected and marked as such,
per the project's standing correction convention (never silently rewrite
a prior claim).

## 2026-08-20 — Week 4, Entregables 7-14: closeout

**Entregable 7 (evaluation):** `scripts/evaluate_rl.py --execute` completed
in the background (training itself finished 2026-08-19, wall-clock
confirmed: ts100=3343.24s, ts101=3276.59s, ts102=3485.78s -- total
168.43 min vs. the 170.9 min calibration estimate, -1.4%). Appended exactly
150 `TD3_TrackingOnly` rows, correctly skipped 200 already-present rows, 0
errors. Final main-grid registry: **550 rows = 11 algorithms x 50 cells
exactly** (`TestRegistryCount`, new this deliverable, passes). Re-verified
`assert_total_reward_comparable` against the completed registry, not just
the pre-TrackingOnly data: AFAP+RoundRobin+TD3_TrackingOnly (all three
sharing `SquaredTrackingErrorReward`) passes; mixing in `TD3_vanilla` or
either oracle variant both raise, as expected -- the first case in this
project where `total_reward` is legitimately comparable across a heuristic
and a trained RL agent.

**Entregable 8 (analysis):** `scripts/analyze_week4_results.py` run
against the completed registry, no errors. Headline: `TD3_TrackingOnly`
achieves *better* profit/satisfaction than `TD3_vanilla` (+5.0%/+0.4%/+7.6%
on profit/avg-satisfaction/min-satisfaction, n=150 pooled) but *worse*
tracking error, energy tracking error, transformer overload, and battery
degradation (+13.0%/+5.3%/+1.75kWh/+2.6%) -- the composite reward Week 3
chose is retroactively validated by this ablation, not merely asserted.
Every TD3 variant (both reward arms, all 6 seeds) sits farther from the
tracking-error oracle than Round Robin (136% gap) does -- RoundRobin
421.9%-893.97% closer than every RL checkpoint, including the arm trained
solely on tracking error. Noise floor (oracle tie-break spread) is
negligible against every reported gap (max 89.35 vs. the smallest online
gap of 7,080.11 absolute). Full numbers now in
`thesis_docs/chapters/04_oracle_and_pitd3.md` S4.8-S4.10.

**Entregable 9 (figures):** all 11 figures regenerated, including new
`f10_optimality_gap` and `f11_physics_term_falsification`. **Visual QA
found and fixed 2 real bugs**, both introduced by Week 4's longer algorithm
names/extra arms, neither previously present:
1. `f02_metrics_bars`/`f04_distributions` titles printed "n=61 per
   algorithm" instead of the true 50 -- `len(grid)//len(algos)` divided
   ALL grid rows (including the 100 oracle rows, excluded from the plot but
   still counted in `grid`) by only the plotted algorithm count. Fixed by
   counting only rows for algorithms actually plotted.
2. `f05_vs_baseline`/`f07_metric_heatmap`: y-axis row labels clipped at the
   left edge ("...ckingOnly (seed 100)", missing "TD3-Tra") -- both used a
   FIXED fraction (`left=0.42`/`0.15`) sized for Week 3's longest label
   ("TD3 (seed 100)"); Week 4's "TD3-TrackingOnly (seed 10X)" labels no
   longer fit. Fixed the same way Week 3 fixed the analogous top/bottom
   margin bug: measure the actual rendered label width via
   `get_window_extent` and convert to a fraction of the real figure width,
   instead of assuming a constant.
`f06_size_sensitivity` confirmed (by looking at the actual PNG, not just
inferring from filter logic) to still correctly restrict to AFAP/Round
Robin only -- TD3/oracle rows don't exist on the non-reference sweep
config, so `_algos_present` naturally excludes them.

**Entregable 10 (tests):** `ev2gym_thesis/tests/test_week4.py`, 16 tests,
**16/16 passing** against the completed registry (`TestOracleDeterminism`
actually re-solved a Gurobi model -- confirmed a live academic license, not
skipped).

**Entregable 11 (chapter):** S4.8-S4.10 filled with real numbers (above).
Title updated to name all three real deliverables (oracle, falsification,
`TD3_TrackingOnly` ablation); filename kept unchanged (dozens of existing
cross-references point at the current path -- see the chapter's own
2026-08-20 title note for the full reasoning).

**Entregables 12-13 (hand-back docs):** `scripts/make_week4_handback.py`
written (modeled on Week 3's), `scripts/extend_progress_log.py` extended
with a `build_week4_section` function appending "2.3. Week 4" to the
externally-located `Progress_Log_Thesis_Project.docx`. Both run; see this
entry's own closing paragraph for the generated file paths.

**Entregable 14 (housekeeping):** per explicit user instruction earlier
this session, no commits/tags/merges were made by Claude for any of Week
4's work -- everything above remains in the uncommitted working tree for
the user to review and commit/push themselves.

## 2026-08-19 — Week 4, Entregable 6: `TD3_TrackingOnly` throughput measured, Gate 3 re-confirmed, training launched

**`scripts/train_td3.py`/`scripts/calibrate_td3_timing.py` gained
`--reward {vanilla,tracking_only}`** (same one-script, not-a-fork pattern
as `evaluate_oracle.py --variant`). `TestControlledComparisonInvariant`
(`ev2gym_thesis/tests/test_week4.py`) updated to exercise the actual Part
B arm; 10/10 passing.

**Throughput measured, not carried over:** `SquaredTrackingErrorReward`
-- 17.56 steps/s (5,000 timesteps, 284.8s, train_seed=100, 53 episodes),
vs. Week 3 vanilla's 18.09 steps/s -- a ~2.9% *slowdown*, not the speedup
one might guess for a simpler reward (the per-step cost is almost
entirely environment/day-reconstruction overhead, not reward-function
evaluation, so a shorter reward formula barely moves the number). At
60,000 timesteps/seed: 57.0 min/seed, **170.9 min (2.85h) for 3 seeds** --
+3% vs. Week 3's 165.9 min estimate / 167.6 min actual for vanilla, well
under the ~15% re-confirmation threshold. Gate 3 (60,000 x 3 seeds,
already confirmed 2026-08-19) stands; training launched without asking
again, per that threshold.

**Process correction applied:** launched via the harness's own background-
task tracking this time (`run_in_background: true`), not a bare `&` --
the earlier balanced-oracle run's mistake (2026-08-19 entry above) is not
repeated. Checkpointing (`CheckpointCallback`, `save_vecnormalize=True`)
and the incrementally-flushed `learning_curve.csv`
(`elapsed_wall_clock_s` column, written every `LEARNING_CURVE_LOG_FREQ_STEPS`)
were already in place from Week 3's infrastructure -- satisfy the
resumability/progress-visibility requirement without new code; monitored
via the CSV's growing row count during the run, same method already used
for the oracle grid runs.

## 2026-08-19 — Week 4: PI-TD3 falsified by two independent reward-only designs, pivoted to `TD3_TrackingOnly`

**Before training, not after: the "does reward_pi actually differ from
vanilla" check the user demanded caught a real problem the smoke test
(one AFAP episode, correlation ~1.0 but only 3 nonzero steps) had not
surfaced clearly enough to act on.** Full protocol, in order.

**Design 1 (instantaneous capacity margin) -- decisively falsified.**
`transformer_capacity_margin_term`: 0 while `current_power <
0.95*max_power`, ramping negative above that pre-violation threshold.
Weight sweep (`scripts/verify_pi_reward_differs.py`, one AFAP episode,
`station_v0_bogota`, seed 0, 2022-01-17):

| Weight | Pearson (full episode) | Spearman | mean |ratio| at relevant steps |
|---:|---:|---:|---:|
| 20 (original) | 0.999977 | 1.0000 | 2.7% |
| 100 | 0.999554 | 1.0000 | 13.5% |
| 300 | 0.997529 | 1.0000 | 40.6% |
| 1000 | 0.991130 | 1.0000 | 135% |
| 2000 | 0.986452 | 1.0000 | 271% |

**Spearman = 1.0 at every weight tested.** Mechanism: both this term and
the vanilla reward's existing `-100 * tr.get_how_overloaded()` are
monotonic functions of the same instantaneous scalar (current power vs.
current capacity) -- any two monotone functions of the same scalar induce
the same step ordering, so no weight could ever create a ranking
disagreement. This was proven with five minutes of CPU, not inferred from
three hours of a flat learning curve.

**Reward-component decomposition** (same episode, needed to calibrate any
future weight against a measured target rather than a qualitative guess):
tracking term sums to -37,778.42 (16/96 nonzero steps), the existing
overload term to -3,732.25 (2/96 steps), the original raw physics term to
only -52.09 (3/96 steps) -- confirming the original weight (20.0) was
qualitatively guessed, not measured, and badly undersized regardless of
the deeper Spearman problem.

**Design 2 (capacity-headroom / latent-exposure) -- also falsified, for a
different reason.** Used `env.charge_power_potential` (the CONNECTED
FLEET's max-rate demand, action-independent in principle) against the
transformer's near-future minimum capacity over a horizon `H`. Genuinely
broke the Spearman tie:

| day | seed | Spearman(vanilla, PI) | disagreement steps |
|---|---:|---:|---:|
| 2022-01-17 | 0 | 0.9565 | 4/96 |
| 2022-01-17 | 1 | 1.0000 | 0/96 |
| 2022-02-14 | 0 | 0.9565 | 4/96 |
| 2022-02-14 | 1 | 1.0000 | 0/96 |
| 2022-03-05 | 0 | 1.0000 | 2/96 |
| 2022-03-05 | 1 | 1.0000 | 0/96 |

Mean Spearman 0.9855 across 6 cells -- real movement, but the *reason* it
moved turned out to be the problem. Horizon sensitivity (`H` in {1,2,4,8}):
**completely flat** -- `station_v0_bogota`'s `transformer.max_power` is a
constant 100.0 kW all day (no demand-response events configured), so
`min(max_power[t:t+H])` never differs from `max_power[t]` regardless of
`H` -- the anticipatory-on-the-capacity-side half of the design is inert
for this station's config, confirmed directly (`(mp == mp[0]).all() ==
True`), not assumed.

Predictability from the observation the policy actually sees (`PublicPST`):
R^2 = 0.5535 (linear regression, 576 samples across 3 `EVAL_DAYS` x 2
seeds under Round Robin) -- moderate, not the "high" hypothesized, a real
caveat even before the decisive problem below.

**The decisive problem, control-responsiveness + SoC-gradient check
(`scripts/verify_headroom_term.py`), same (config, day, seed) cell:**

| | AFAP | Round Robin |
|---|---:|---:|
| Headroom term nonzero steps (/96) | 2 | 27 |
| Headroom term sum | -99.298 | -3236.085 |
| Correlation(headroom term, mean fleet SoC) | +0.6814 | +0.6617 |

Round Robin -- the heuristic that already nearly eliminates transformer
overload -- was penalized **~32x more often** than AFAP, the unmanaged
baseline that overloads this station routinely. Mechanism, confirmed by
the correlation: `charge_power_potential` excludes an EV once it reaches
100% SoC, so charging faster and more completely (AFAP's whole strategy)
removes EVs from the term's sum regardless of whether that fast charging
caused a real overload. **The gradient points toward AFAP, the exact
baseline this thesis is trying to beat.**

A repair was considered (weight the term by remaining need instead of
counting full/not-full) and rejected as relocating the same flaw, not
fixing it: any measure of pending demand falls when demand is satisfied
sooner, so "finish everyone as fast as possible" remains a way to minimize
it under any variant. The signal that would resist this -- infeasibility
against a **departure deadline** -- needs each EV's remaining time to
departure, and confirmed by reading `ev2gym/rl_agent/state.py:6-63`
directly: `PublicPST` exposes a full/not-full flag, cumulative
ALREADY-delivered energy, and ELAPSED (not remaining) dwell time -- no
departure time, no remaining-energy figure. This is deliberate: the
EV2Gym paper's own Public-PST problem formulation (Sec. III-A) assumes
"information about EV arrival and departure time... is unavailable" to
the operator, which is exactly why this thesis chose `PublicPST` for a
public-station scenario in Week 3.

**Extending the state to fix this was considered and rejected, on realism
grounds, not cost.** A real Bogota public-station operator does not know
when a walk-up user intends to leave; encoding it into the observation
would let the learned policy depend on information that operator
categorically lacks, undercutting this thesis's realism claim more than a
weaker physics term costs it. Extending the state for only the PI arm
(cheaper) was rejected on a second, independent ground: it would make the
arm differ from vanilla TD3 in two variables (state AND reward), so no
result could be attributed to either one.

**Verdict, stated as a finding with a mechanism, not a delay before a
"real" result:** a reward-only physics-informed adaptation of PI-TD3 is
not achievable under `simulate_grid=False` + `PublicPST`. Design 1 failed
because its input (instantaneous realized power) is already captured by
the baseline reward. Design 2 failed because its input
(connected-fleet potential) can be driven to zero by exactly the
behavior this thesis wants to discourage, and the fix needs information
`PublicPST` deliberately withholds. **PI-TD3's mechanism requires the
physics it was designed for** -- a voltage constraint, absent from the
baseline reward, reducible by load-shifting rather than charging speed,
and observable without assuming operator knowledge the real scenario
lacks. All three hold once `simulate_grid=True` + the IEEE 34-bus feeder
exist (Week 6). Recorded there as a conditional stretch goal, not a
commitment (`PROJECT_ROADMAP.md`'s Week 6 entry, amended same session).

**No arm named `PI_TD3`/`PI-TD3` exists anywhere in this project as a
result.** `ev2gym_thesis/rl/reward_pi.py` and both failed designs stay in
the repository and git history -- they are the evidence for this finding,
not dead code. Part B's actual second training arm, decided in the same
session: **`TD3_TrackingOnly`**, a reward ablation (Week 3's
`SqTrError_TrPenalty_UserIncentives` vs. EV2Gym's bare
`SquaredTrackingErrorReward`) using two pre-existing, unmodified
`ev2gym.rl_agent.reward` functions -- no new adaptation, no sign
ambiguity, no observability question, a genuinely single-variable
comparison the two design attempts above could not achieve. Answers a
real question Week 3 assumed rather than measured: does encoding
transformer/satisfaction penalties into the training reward actually buy
anything over optimizing tracking error alone? Full design in
`thesis_docs/chapters/04_oracle_and_pitd3.md` S4.4.

`PROJECT_ROADMAP.md` and `CLAUDE.md` corrected in the same session
(`[SUPERSEDED]` markers, dated notes, old text kept not deleted) to
reflect the pivot and the Week 6 conditional stretch goal.

## 2026-08-19 — Week 4, Entregable 5: PI-TD3 scope resolved after reading the paper in full, reward module built and tested

**Read `pi_td3_paper.pdf` (arXiv:2510.12335v2) in full before writing any
code** — CLAUDE.md rule 3 / the task brief's explicit requirement.
Surfaced a finding the brief's original §4.1 framing did not anticipate:
**PI-TD3's actual novel mechanism is not primarily its reward shape.**
Algorithm 1 line 11 uses a K-step, model-based, *differentiable* rollout
(Eq. 20) — a differentiable transition model (Eq. 18) and differentiable
reward (Eq. 14) simulate K steps forward and backpropagate gradients
directly into the actor, bypassing the environment. Fig. 3b's own
rollout-horizon ablation (K=5 vs. K≥20: roughly a 4x difference in final
reward) is the paper's own evidence this mechanism, not the reward term
alone, drives PI-TD3's sample-efficiency gain over vanilla TD3.

**Presented to the user as a genuine "is this too thin to call PI-TD3"
moment** (the brief's own escape hatch), with three options: (a) a thin,
reward-only adaptation, explicitly declared as such; (b) build the full
differentiable-rollout mechanism (a custom transition model + replacing
SB3's `TD3.train()`, materially larger scope); (c) drop PI-TD3 from
Weeks 4-5 and report the scoping finding instead. **User chose (a).**

**Built `ev2gym_thesis/rl/reward_pi.py`** — a drop-in for
`env_factory.DEFAULT_REWARD_FN`, requiring zero changes to
`env_factory.py`/`config_rl.py`/`callbacks.py`/`eval_utils.py` (the Week 3
separation held, confirmed rather than assumed). Ports only Eq. 14 Term 1
(the physics penalty: 0 within a ±5%-of-nominal voltage band, increasingly
negative beyond it), reinterpreted for a one-sided transformer-capacity
margin since `simulate_grid=False` has no voltage variable — the 5% margin
fraction is borrowed directly from the paper; the penalty weight
(`PI_TD3_PHYSICS_WEIGHT = 20.0`) is not, and is labeled "set for this
project," not tuned via a sweep. Base reward
(`SqTrError_TrPenalty_UserIncentives`) kept byte-identical to Week 3's
vanilla-TD3 arm — Eq. 14's profit term (Term 2) and its dense
near-departure satisfaction term (Term 3) were both deliberately NOT
ported (the first would reopen Week 3's S3.2 rejection of the
Business/ProfitMax family; the second would introduce a second new
variable into the comparison, since Week 3's base reward already has its
own satisfaction penalty).

**A genuine ambiguity found in Eq. 14 while adapting it, recorded rather
than silently resolved either way:** the paper's own stated `λ1 = -5×10⁴`
(Sec. IV-A), applied literally to Term 1, produces a positive contribution
that GROWS as voltage violations worsen — under a maximized reward
(Eq. 16), this rewards larger violations, opposite to the paper's own
prose ("the first term penalizes voltage deviations", Sec. II-B). Could be
a genuine sign inconsistency in the paper or a misreading from this PDF's
extraction of a multi-line, subscript-heavy equation (a known risk) — not
resolved with confidence either way. Not propagated: this thesis's own
term was built with an unambiguous, directly-tested sign instead, matching
the paper's prose description of intent rather than its literal numeric
coefficient.

**Verified before moving on, not just written:** smoke-tested
`transformer_capacity_margin_term` against a real `ChargeAsFastAsPossible`
episode on `station_v0_bogota` (known to overload this station) — 93/96
steps at 0 (within margin), 3/96 steps negative (worst -31.68), all terms
≤0, matching the designed shape exactly. `ev2gym_thesis/tests/test_week4.py`
added: 10 tests (7 for the reward term's exact shape — zero within margin,
zero at the boundary, negative and worsening beyond it, correct
multi-transformer summation — and 3 for the controlled-comparison
invariant, asserted on the real resolved `TrainingDayCyclingEnv` objects
built through `env_factory.make_training_env`, not by inspection). All
10/10 passing.

**Entregable 6 (PI-TD3 training throughput calibration) — done, Gate 3
presented, awaiting confirmation.** Extended `scripts/calibrate_td3_timing.py`
with a `--reward {vanilla,pi}` flag (one script, not a fork, per the
brief's stated preference — the exact same calibration path measures
either reward). Measured: **16.85 steps/s** (5,000 timesteps, 296.8s,
train_seed=100, 53 episodes) — a ~6.9% slowdown vs. Week 3's vanilla-TD3
measurement (18.09 steps/s), consistent with the small added per-step
Python loop over transformers in `transformer_capacity_margin_term`.
Extrapolated to 60,000 timesteps/seed (the same budget Week 3 used, not
assumed to carry over automatically): **59.4 min/seed, 178.1 min (2.97h)
total for 3 seeds** — vs. Week 3's 165.9 min (2.8h) estimate / 167.6 min
(2.79h) actual for vanilla TD3. Per `CLAUDE.md` rule 2, training does not
launch until the user explicitly confirms this budget — presented, not
assumed, even though the same numeric budget worked for Week 3.

## 2026-08-19 — Week 4: references acquired, Balanced oracle built and verified, 100-cell oracle grid complete (branch `semana-4`)

**Process correction, noted for the record:** the balanced-oracle grid run
was launched with a bare `nohup ... &` inside a single Bash call, which the
harness could not track as a background task -- no completion notification
arrived; progress had to be polled manually via the registry row count.
Not repeated: subsequent long runs use the tool's own `run_in_background`
mechanism, which does notify on completion.

**Reference acquisition (§2 of the user's consolidated instruction).**
`thesis_docs/references/` previously held only a `.docx` proposal file --
`CLAUDE.md` asserted PDFs that did not exist, discovered when Week 4 tried
to read `pi_td3_paper.pdf` and correctly stopped rather than reconstruct
Algorithm 1/Eq. 14 from memory (2026-08-18 entry above). Fetched and
verified (not just downloaded -- header/content-checked, since `curl`
saves an HTML error page as `.pdf` without complaining):

- `ev2gym_paper.pdf` (arXiv:2404.01849v1) and `pi_td3_paper.pdf`
  (arXiv:2510.12335v2) -- both confirmed genuine PDFs with plausible page
  counts (10 and 18 pages respectively; a `file`-reported "2 page(s)" for
  the EV2Gym PDF was a false alarm from that utility -- the actual content,
  read in full, has 10 pages including all sections through the
  bibliography).
- Colombian regulatory PDFs (Ley 1964/2019, RETIE Res. 40117/2024, RETIE
  Libro 3) -- confirmed genuine (`%PDF-1.x` headers). The RETIE Res. 40117
  URL needed proper UTF-8 percent-encoding of the accented "ó"
  (`Resoluci%C3%B3n_...`) -- the literal accented URL 404'd.
- The two CREG resolutions (40223/2021, 40123/2024) are HTML-only at their
  official source, no PDF alternative found. No HTML-to-PDF renderer was
  available in this environment (`wkhtmltopdf`, `pandoc`, `weasyprint`,
  `pdfkit` all checked, all absent) -- saved as raw HTML with retrieval
  date/URL rather than fabricating a PDF or silently substituting a
  different source. Declared as a limitation in
  `thesis_docs/references/REFERENCES.md`, not worked around silently.
- Zandrazavi et al. (2022) and Mahmoud (2017) Ch. 1 remain pending
  (advisor / institutional access respectively) -- Weeks 6-7, not a Week 4
  blocker. Full citations, DOIs, and status in `REFERENCES.md`.
- `CLAUDE.md`'s references section corrected with a dated note (2026-08-19,
  same discipline as `02_model_validation.md`'s correction) -- the original
  list is kept, not deleted, with a pointer to `REFERENCES.md` as the new
  source of truth.
- **Read in full: `ev2gym_paper.pdf`.** Beyond confirming it's genuine,
  this surfaced something directly relevant to the Balanced oracle work
  below: Eq. 24 states the profit-maximization problem's departure
  constraint as `E_{j,i,t} >= E*_{j,i,t}` -- a same-unit (kWh) comparison
  with no multiplication by any other energy term. `profit_max.py`'s
  installed `user_satisfaction` term (`ev_des_energy * ev_max_energy -
  energy`) does not match this formal definition either -- a second,
  independent confirmation (beyond the dimensional-analysis argument
  already in `04_oracle_and_pitd3.md`) that the installed class's
  satisfaction term is not a faithful implementation of the paper's own
  formulation, not just internally unit-inconsistent.

**Balanced oracle verification (§3) -- "satisfaction is free" was checked,
not just believed, before writing it anywhere.** The concern raised: an
identical `ObjVal` across three penalty weights (0.5x/1x/2x) on the
reference cell has two explanations -- the penalty is genuinely 0 at the
optimum, or the term never entered the model (a silently-inert Gurobi
objective term is a common, easy-to-produce bug, and this code was fresh
and freshly adapted across a units fix). Ran the full protocol
(`scripts/verify_balanced_oracle_objective.py`):

1. **Penalty value at optimum, measured directly** (not inferred from
   `ObjVal`): `user_satisfaction.sum() = 0.0` exactly, weight=1.0.
2. **Absurd-weight probe** (weight=1e6): `ObjVal` still identical to
   weight=1.0's. Necessary but not sufficient, as expected -- both
   hypotheses predict this.
3. **Positive control (decisive):** built a stressed replay (transformer
   `tra_max_amps`/`tra_min_amps` scaled down on a copy, diagnostic-only
   helper, not part of the production pipeline) and re-solved at
   0.5x/1x/2x. At 0.2x capacity, satisfaction was STILL free (0.0 penalty,
   identical `ObjVal`) -- inconclusive, correctly reported as such rather
   than claimed as proof either way. Escalated to 0.05x capacity: **the
   term became decisively live** -- `ObjVal` differs by weight (31595 /
   32452 / 34145 at weight 0.5/1.0/2.0) and, critically, the satisfaction
   penalty *decreases* monotonically as weight increases (1731 -> 1697 ->
   1694) while the implied tracking-error component *increases*
   correspondingly (30730 -> 30754 -> 30757) -- the exact tradeoff pattern
   a correctly-functioning weighted objective must produce. This rules out
   the dead-term hypothesis.
4. **Solution comparison, not just objective values:** on the real
   (unstressed) reference cell, Balanced's action array is NOT
   byte-identical to Tracking-only's despite the tied `ObjVal` (max abs
   diff 0.578 in the normalized `[0,1]` action space, at one specific
   port/timestep) -- confirming the term is actively selecting among
   multiple LP-tied optima, not inert.
5. **Code order**, read directly from `ev2gym_thesis/oracle/balanced_model.py`:
   `user_satisfaction` variable created, then constrained (at departure
   timesteps only, matching `profit_max.py`'s own pattern of leaving
   non-departure entries unconstrained so the minimization drives them to
   their default lower bound of 0), then referenced in `setObjective` --
   no shadowing, no reordering bug.

**Verdict: "satisfaction is free" on the real 50-cell grid is a real
result, not a bug artifact** -- confirmed by a protocol capable of
detecting the bug it was designed to catch, not just consistent with one
untested hypothesis.

**A second, unanticipated finding surfaced while confirming this against
the full grid (not just the reference cell): the two oracle variants are
NOT identical on every reported metric, even though they tie exactly on
Gurobi's own internal objective.** Checked across all 50 cells, not
assumed from the reference cell alone:

| Metric | Identical across all 50 cells? |
|---|---|
| `total_ev_served` | Yes (0.000000 max diff) |
| `total_transformer_overload` | Yes (0.000000 max diff) |
| `min_energy_user_satisfaction` | Yes (0.000000 max diff) |
| `average_user_satisfaction` | Yes (0.000000 max diff) |
| `tracking_error` | **No** -- Balanced consistently ~1-1.5% LOWER than Tracking-only, all 50 cells, same direction every time |
| `total_profits` | No -- small, consistent difference (max 0.53) |
| `battery_degradation` | No -- negligible but nonzero (max 0.000023) |

**Root cause, traced, not guessed:** Gurobi's internal `power_error.sum()`
objective is computed from the LP's own linear energy-update model
(`energy[t] = energy[t-1] + current * voltage * efficiency * dt`). EV2Gym's
*actual* simulated charging uses a two-stage (CC/CV) nonlinear SoC curve
once above a transition threshold (`ev2gym_paper.pdf` Eq. 1-2, Table III,
Fig. 3 -- confirmed by reading the paper the same session this was found,
not assumed). The LP has multiple solutions tied at the exact same
`power_error.sum()` (confirmed: both variants' `ObjVal` match exactly, to
the cell, on every one of the 50 cells checked); Balanced's extra
satisfaction term breaks that tie differently than Tracking-only's bare
objective does. When each variant's chosen (LP-tied, but different)
action sequence is replayed through EV2Gym's actual nonlinear simulator to
compute the registry's `tracking_error`/`total_profits`/
`battery_degradation` metrics, the two variants' realized values diverge
slightly -- small, consistent, and fully explained, not noise and not a
bug. This is the oracle-domain analogue of Week 3's reward-vs-metric
misalignment (`03_rl_baseline.md` S3.4): the optimized quantity and the
reported metric are related but not identical, here because of a
linear-vs-nonlinear MODEL mismatch between the LP and the real simulator,
rather than a differing objective formula.

**Both oracle variants remain a valid, dominant bound** -- the ~90-unit
Balanced-vs-Tracking gap is negligible next to the gap to every online
algorithm on the same reference cell: `tracking_error` = 6388-6482
(oracle, both variants) vs. 14477 (Round Robin), 33111 (TD3 seed 100),
43608 (RandomPolicy), 72374 (AFAP). The Entregable 10 tripwire condition
("the oracle is no worse than every online algorithm on the metric it
optimizes") holds comfortably for both variants on every cell checked.

**Consequence for the chapter, per the user's explicit instruction ("if
Balanced == Tracking on every cell, do not keep two identical columns"):**
they are demonstrably NOT identical on the registry's own reported
`tracking_error`/`total_profits`/`battery_degradation` -- only tied on
`total_ev_served`, `total_transformer_overload`, `min_/average_user_satisfaction`,
and the LP's internal (unreported) objective. Both variants are kept as
separate columns, with this nuance stated plainly rather than either
collapsing them or reporting the tie without explaining why the "identical"
values and the "different" values aren't the same set of metrics.

**Balanced oracle grid run: 50/50 cells, 0 infeasible.** Weight
`SATISFACTION_PENALTY_WEIGHT = 1.0` (declared origin: adapted from
`profit_max.py`'s penalty in structure, not scale -- see
`ev2gym_thesis/oracle/balanced_model.py`'s doc comment). `--variant`
flag added to `scripts/evaluate_oracle.py` rather than forking a second
script, per the project's "extend, don't fork" convention.

## 2026-08-18 — Week 4 kickoff: Gate 1 preflight, amendments, Entregables 2-3 (branch `semana-4`, from corrected `semana-3`)

**Scope deviation, reduction not addition (see `04_oracle_and_pitd3.md` S4.0
and `PROJECT_ROADMAP.md`'s 2026-08-18 amendment):** Week 3's handback
document declared Week 4 as a perfect-information reference using a free
solver, no Gurobi — that plan is now amended. A Gurobi **academic** license
is active on this machine, verified directly (`gurobipy` reports `LicenseID
2853634`, `"Academic license - for non-commercial use only - expires
2027-08-14"`), reversing Week 2's finding of a size-limited "Restricted"
license. The oracle now uses Gurobi via the unmodified
`ev2gym/baselines/gurobi_models/`. This is a reduction in deviation from
the *original* roadmap (which always planned Gurobi for this phase), not a
second new deviation — recorded as an amendment in `PROJECT_ROADMAP.md` and
`02_model_validation.md`, both dated 2026-08-18, with every superseded
"free solver" sentence marked `[SUPERSEDED]`, kept, not deleted.

**Gate 1 — preflight findings (full detail in the chat record; summarized
here for the permanent log):**
- Model size for `station_v0_bogota`: ~9,000 vars, ~1,536 binary — well
  inside the unlimited academic license.
- Inventoried all 3 `gurobi_models/` classes plus the adjacent
  `mpc/V2GProfitMax.py` (receding-horizon, rejected on that basis alone).
  Recommended `PowerTrackingErrorrMin` (tracking_error.py) over
  `V2GProfitMaxOracleGB` (profit_max.py, Business/ProfitMax family already
  rejected for this thesis in Week 3) and `V2GProfitMax_Grid_OracleGB`
  (v2g_grid.py, requires `simulate_grid=True`, reserved for Weeks 6-7).
- Found, by tracing `ev2gym_env.py:227` and `replay.py:89-90`, that
  `v2g_enabled=False` does NOT zero the replay's discharge-current bounds —
  only gates the RL/heuristic action-space sign. Left unfixed, the oracle
  would have V2G capability none of the compared algorithms have. This was
  praised explicitly as the kind of thing that had to be caught before any
  run, and is fixed by `ev2gym_thesis/oracle/replay_utils.force_g2v`.
- Confirmed the oracle bypasses `reward_function`/`state_function` entirely
  (reads a pickled replay directly) — `total_reward` is undefined for
  oracle rows, `notes` records `reward=none`.

**User amendments accepted at Gate 1:**
1. **Two oracle variants**, not a single composite one —
   `Optimal_Oracle_Tracking` (untouched objective, the defensible bound on
   tracking error) and `Optimal_Oracle_Balanced` (same model + a
   satisfaction penalty term, not yet implemented) — because a composite
   objective is not a decomposable bound, and the tripwire test asserting
   the oracle beats every online algorithm on its own optimized metric
   needs a single-objective target to be meaningful. Full reasoning in
   `04_oracle_and_pitd3.md` S4.2's Amendment 1.
2. **Replay-vs-`make_env` parity must be proven empirically before any
   full-grid run**, not assumed — directly motivated by the Week 3 bug
   this same session found (below). Three properties verified before
   trusting any oracle result: the replay's oracle-relevant fields are
   algorithm-independent (compared `ChargeAsFastAsPossible` vs.
   `RoundRobin` byte-for-byte); the replay matches `make_env`'s scenario
   element-by-element (14 EVs, `station_v0_bogota`, seed 0, 2022-01-17, all
   fields array-equal); replay generation is deterministic across two
   independent runs. Full detail in `04_oracle_and_pitd3.md` S4.5.

**Between Gate 1 and Entregable 2: Week 3 evaluation-bug detour.** Building
the parity check above surfaced a bug in Week 3's *evaluation* pipeline
(unrelated to Gurobi) serious enough that Week 4 was paused entirely to fix
it on `semana-3`, per the user's explicit sequencing decision, before any
further Week 4 work. Full account in this file's next entry below and
`03_rl_baseline.md` S3.11 — not repeated here. `semana-4` was re-branched
from the corrected `semana-3`/`main` tip (commit `88c767e`) after that fix
landed.

**Entregable 2 — `thesis_docs/chapters/04_oracle_and_pitd3.md` skeleton,
done.** S4.0 (scope deviation), S4.1 (what the oracle is/isn't), S4.2
(selection rationale + Amendment 1), S4.5 (registry comparability rules +
the parity verification) written in full, methodological content before
any results exist, per the project's standing discipline. S4.3/S4.4
(PI-TD3) deliberately left reserved — not started, per the brief's
instruction not to begin Part B before the oracle clears Gate 2.
`scripts/check_claims.py` initially flagged two false positives in this
chapter (a "distance from the bound" phrasing and the reserved
`algorithm_family` registry value, both meta-references to the vocabulary
restriction itself, not results claims — the same class of false positive
Week 2 hit) — reworded per that precedent (not the checker), passes clean.

**Entregable 3 — `scripts/calibrate_oracle_timing.py`, done. Full table:**

Built `ev2gym_thesis/oracle/replay_utils.py`
(`generate_replay`/`force_g2v`/`build_g2v_replay_for_cell`) and ran the
calibration on `station_v0_bogota`'s reference cell (`REFERENCE_DAY`
2022-01-17, `SEEDS[0]=0`), the real unmodified
`PowerTrackingErrorrMin`, not a shrunk toy model:

| Quantity | Value |
|---|---|
| Replay generation + G2V-forcing | 3.94s |
| Model build (Python-side, pre-optimize) | 0.41s |
| Gurobi solve (`Model.optimize` wall-clock) | **0.10s** |
| NumVars / NumBinVars | 9,024 / 1,536 |
| NumConstrs (linear) / NumQConstrs (quadratic) | 10,546 / 2,304 |
| Status | solved to a certified optimum (1 B&B node, gap 0.00%) |
| Presolve reduction | 10,476 of 10,546 rows removed; 8,200 of 9,024 columns removed |

Solve time measured via a scoped monkeypatch of `gurobipy.Model.optimize`
(records wall-clock around the real call, restored immediately after,
touches no file on disk) — the only way to isolate build-time from
solve-time without editing the unmodified library class, whose `__init__`
fuses model construction and `self.m.optimize()` into one method.

**Extrapolation:** 50 cells (tracking-only) × 4.45s/cell ≈ **3.7 minutes**
total. Both variants (2×50=100 cells), *assuming* the not-yet-implemented
balanced variant costs the same per cell — an explicitly flagged estimate,
not a measurement — ≈**7.4 minutes**. This is far under the brief's
~3-minutes-per-cell concern threshold; no MIP-gap/time-limit approximation
is needed at this station size. Also found and reported at Gate 2:
`PowerTrackingErrorrMin.__init__` does not currently wire a `MIPGap=`/
`timelimit=` kwarg to `self.m.setParam` before its internal
`self.m.optimize()` call (unlike `profit_max.py`/`v2g_grid.py`, which do)
— moot given the measured speed, but noted for the record since the
balanced variant, once built, may not be as fast.

**Gate 2 — presented to the user, awaiting confirmation before any
full-grid oracle run** (either variant). Recommended candidate: full
optimality for the tracking-only 50-cell grid (~3.7 min), given the
measured solve time makes gap/time-limit tricks unnecessary.

## 2026-08-18 — Week 3 correction: TD3/RandomPolicy evaluation ran uncontrolled scenarios, not the registered ones (branch `semana-3`)

**Context: this was found while doing Week 4 preflight work, not while
working on Week 3.** Building the perfect-information oracle's replay-vs-
`make_env` parity check (Week 4 Amendment 2) required proving, empirically,
that an evaluation episode's EV population matches the `(config, day,
scenario_seed)` cell it's registered under. The same check applied to
`scripts/evaluate_rl.py`'s existing TD3/RandomPolicy evaluation path failed.
Week 4 was paused at that point (branch `semana-4` was created and then set
aside) and this correction was done on `semana-3`, where the bug originated,
per the user's explicit instruction not to fix a Week 3 bug on a Week 4
branch.

**What was believed.** `scripts/evaluate_rl.py`'s `_TD3Stepper` and
`_RandomPolicyStepper` classes start each evaluation episode by calling
`env.reset()` on an env already constructed via
`ev2gym_thesis.rl.env_factory.make_env(config, day, scenario_seed)`. The
belief (`_RandomPolicyStepper`'s own comment, verbatim, before this fix:
`# scenario seed already applied via make_env's EV2Gym(seed=...)`) was that
the scenario seed passed at construction time persists across a subsequent
`env.reset()` call with no seed argument.

**What was found, and how it was reproduced.** `EV2Gym.reset(seed=None)` —
which is what a bare `env.reset()` and an explicit `env.reset(seed=None)`
both do — draws a **fresh** `np.random.randint(0, 1_000_000)` and
regenerates `self.EVs_profiles` from scratch; it does not fall back to the
seed the env was constructed with. Reproduced directly, not inferred from
reading the code:

```
construction (seed=0, 2022-01-17): 14 EVs, first arrival/departure (11, 37), (11, 32), (11, 36)
after stepper.reset() [no seed]:   16 EVs, first arrival/departure (14, 33), (15, 38), (15, 41)   <- different scenario
after env.reset(seed=0) explicit:  matches construction exactly
```

`scripts/backfill_registry.py` (AFAP/Round Robin) was checked with the exact
same population-diff method, not assumed correct because "the code looks
right" — that was precisely the mistake the original `_RandomPolicyStepper`
comment made. Confirmed: constructing with `seed=seed` and then calling
`env.reset(seed=seed)` explicitly (backfill_registry.py's actual pattern)
reproduces the construction-time population exactly, and does so
identically across two independent constructions with the same seed. AFAP
and Round Robin's Weeks 1–2 numbers are unaffected by this bug.

**Blast radius.** All 200 of Week 3's TD3/RandomPolicy evaluation rows (3
checkpoints x 50 cells + 1 control x 50 cells) were measured against an
uncontrolled, re-randomized scenario instead of the `(SEEDS x EVAL_DAYS)`
cell their registry row claims. This corrupted the scalar stats themselves
(`total_ev_served`, `average_user_satisfaction`, `total_transformer_overload`,
etc.) — not just post-episode timeseries capture, which is what the
already-documented DummyVecEnv auto-reset bug (2026-08-13 entry below)
affected. Consequently: `results/master_results.csv`'s 200 RL rows,
`results/rl_vs_baseline_bootstrap.csv`, `results/rl_train_seed_dispersion.csv`,
every figure built from them (`f01`, `f02`, `f03`, `f04`, `f05`, `f06`,
`f07`), the written conclusions in `03_rl_baseline.md` (S3.8/S3.9), and
`Week3_Parameter_Method_and_Implementation_Justification.docx`. **Trained
model weights are unaffected — no retraining was needed** (see the training-time
finding below for why: training-scenario randomization is a different
question from evaluation-scenario randomization, and even there only
episode 1 was ever seed-controlled).

**§2 diagnosis (why a passing test didn't catch this).** Week 3's
Entregable 9 test suite included `TestEvaluationReproducibility`, whose
docstring claimed exactly the property that was actually broken. That test
passed. Diagnosis: **the test never exercised `_TD3Stepper` or
`_RandomPolicyStepper` at all.** It built its own `run_once(env)` helper
that called `env.reset(seed=seed)` directly — a correct call, but a
parallel reimplementation of the evaluation loop, not the one
`scripts/evaluate_rl.py` actually runs in production. It certified that
"deterministic scenario generation + deterministic predict, when you pass
the seed correctly" works, which was never in question — it did not
certify that the production stepper classes pass the seed correctly, which
was the actual point of the test and the actual bug. Rewritten to
construct and call `scripts.evaluate_rl._TD3Stepper` /
`_run_and_capture` directly (see `ev2gym_thesis/tests/test_rl_infrastructure.py`).

**General rule extracted and applied:** every test in this project must
exercise the real call path used in production, not a lookalike of it.
Audited the other 7 (now 9) tests in `test_rl_infrastructure.py` against
this rule:
- `TestSeedAndDayDisjointness` (3 tests) and the pools-non-empty test:
  check module-level constants (`SEEDS`/`TRAIN_SEEDS`/`EVAL_DAYS`/`TRAIN_DAYS`)
  directly — no production code path to reimplement, not at risk of this
  failure mode.
- `TestTrainingEnvNeverLeaksEvalDays` (3 tests): construct and call the
  real `TrainingDayCyclingEnv` class directly, the same class
  `make_training_env` uses — real call path, not a lookalike. No issue.
- `TestVecNormalizeStatsRequired`: calls `load_trained_agent` directly, the
  real production function. No issue.
- `TestEvaluationReproducibility`: the one bug, fixed above.

Two new tests added instead of just fixing the one: `TestResetForEvaluation`
pins the fix at the smallest possible grain (`reset_for_evaluation`
reproduces construction, a bare `env.reset()` provably diverges from it —
the second test exists so that if EV2Gym's upstream `reset()` semantics
ever change, this test fails loudly and flags that the workaround should be
re-examined, not silently rot).

**§3 audit: every `.reset(` call site under `ev2gym_thesis/` and `scripts/`,
classified.** Only `evaluate_rl.py`'s two steppers were wrong. Specifically
checked, per the user's instruction not to assume:
- `scripts/backfill_registry.py`, `scripts/make_figures.py`,
  `scripts/demo_degradation_bogota.py`, `scripts/smoke_test_grid.py`,
  `scripts/run_size_sensitivity.py`, `scripts/measure_degradation_by_ambient.py`,
  `scripts/verify_seed_sensitivity.py`: all call `env.reset(seed=seed)`
  explicitly. AFAP/Round Robin confirmed correct empirically above; the
  others use the identical pattern.
- `ev2gym_thesis/rl/env_factory.py`'s `TrainingDayCyclingEnv.reset()`
  forwards whatever seed SB3 passes, which is the real construction-time
  `train_seed` on episode 1 only (traced through SB3's source:
  `base_class.py`'s `_setup_learn` calls `self.env.reset()` once, with no
  args, after `TD3(seed=train_seed)`'s `set_random_seed` has called
  `self.env.seed(train_seed)` — `DummyVecEnv.seed()` queues the seed for
  exactly the next `reset()` call and then clears it, per
  `dummy_vec_env.py`'s `reset()`/`_reset_seeds()`). Every training episode
  after the first therefore samples an unseeded, freshly-random EV scenario
  within whichever `TRAIN_DAYS` date the round-robin cycle lands on. This is
  **acceptable for training** (arguably beneficial — more scenario diversity
  per date than a fixed draw would give) and **does not invalidate the
  trained weights**, but it means `TRAIN_SEEDS` should be read exactly as
  `eval_protocol.py`'s own docstring already describes it — reproducible
  agent initialization/exploration-noise/replay-sampling — and NOT as a
  reproducible stream of training scenarios, which no document claimed
  outright but which the parallel structure with `SEEDS` could invite a
  reader to assume. Day coverage itself (round-robin over `TRAIN_DAYS`) is
  confirmed unaffected: `_next_day()` selects by an integer index
  (`self._rr_index % len(TRAIN_DAYS)`), never by the RNG, so the "every
  `TRAIN_DAYS` date seen an equal (+/-1) number of times" claim in
  `TrainingDayCyclingEnv`'s docstring remains true independent of this bug
  — confirmed by reading `_next_day()`, not assumed, and already covered by
  `TestTrainingEnvNeverLeaksEvalDays`'s existing (correct, real-call-path)
  test.
- `_RandomPolicyStepper`'s action-space seeding claim
  (`env.action_space.seed(scenario_seed)`) was never actually false: EV2Gym
  sets `self.action_space` once in `__init__` and `reset()` never
  reassigns it (confirmed by reading the full `reset()` method), so the
  seeded action-space RNG does survive `reset()` calls. The bug was
  entirely in which EV *scenario* the seeded actions got applied to, not in
  the action sampling itself.
- Also found and removed: `ev2gym_thesis/rl/eval_utils.py`'s `run_episode`
  function, whose docstring claimed it was "used for every Entregable 6
  evaluation run." It was dead code — grepped, zero call sites anywhere in
  the repo, superseded by `_TD3Stepper`/`_run_and_capture` in
  `evaluate_rl.py`. Deleted rather than left as a stale, false claim.

**The fix — at the source, not per call site** (the user's explicit
correction to the initially-proposed per-stepper patch, on the grounds that
two call sites are two chances to get it wrong again, and Week 4 was about
to add a third). `ev2gym_thesis/rl/env_factory.py` gained
`reset_for_evaluation(env, scenario_seed)`: the only sanctioned way to start
an evaluation episode on a `make_env()`-built env. It passes
`scenario_seed` explicitly to `env.reset()` and then **asserts** (not
comments) that the post-reset EV population matches the construction-time
population, element by element. `_TD3Stepper` and `_RandomPolicyStepper`
were both changed to call it instead of `env.reset()` directly, and both now
store `scenario_seed` as an attribute so they can. The Week 4 oracle's own
stepper (not yet written) is required to go through this same helper.

**Registry correction: re-run, old rows preserved, not overwritten.** The
200 pre-fix rows were extracted from `results/master_results.csv` into
`results/master_results_prefix_week3_evaluation_bug.csv` (all 200, `algorithm`
in `{TD3_vanilla_ts100, TD3_vanilla_ts101, TD3_vanilla_ts102, RandomPolicy}`)
and removed from the live registry (503 rows remaining, matching Week 2's
known count) before re-running `scripts/evaluate_rl.py --execute` — a
separate archived file rather than a `notes` marker, so the old-vs-new
comparison below could be built directly without reconstructing it from git
history. All 200 corrected rows appended cleanly (200/200, 0 skipped) under
the exact same registry keys.

**Old vs. corrected, mean across the 50-cell grid (`station_v0_bogota`):**

| Algorithm | Metric | Pre-fix (invalid) | Corrected | Δ |
|---|---|---:|---:|---:|
| TD3 (seed 100) | EVs served | 13.00 | 13.44 | +0.44 |
| TD3 (seed 100) | min energy satisfaction | 93.06 | 78.25 | **-14.81** |
| TD3 (seed 100) | Transformer overload (kWh) | 0.00 | 0.45 | +0.45 |
| TD3 (seed 100) | Tracking error | 16668 | 27101 | +10433 |
| TD3 (seed 101) | EVs served | 10.40 | 13.44 | **+3.04** |
| TD3 (seed 101) | min energy satisfaction | 92.31 | 83.80 | -8.51 |
| TD3 (seed 101) | Transformer overload (kWh) | 0.00 | 2.65 | +2.65 |
| TD3 (seed 101) | Tracking error | 28152 | 29538 | +1386 |
| TD3 (seed 102) | EVs served | 12.80 | 13.44 | +0.64 |
| TD3 (seed 102) | min energy satisfaction | 86.71 | 85.49 | -1.22 |
| TD3 (seed 102) | Transformer overload (kWh) | 0.98 | 0.96 | -0.02 |
| RandomPolicy | Transformer overload (kWh) | **12.74** | **0.22** | **-12.52** |
| RandomPolicy | Tracking error | 43878 | 36972 | -6906 |

**Does the correction change the conclusions? Yes, on the exact claim the
control was built to support — this is the headline finding of this
correction, not a footnote.** Paired bootstrap (5,000 resamples,
`stats_utils.paired_bootstrap_ci`, matched by `(seed, eval_day)` cell) on
the corrected data:

| Comparison | Metric | Point est. | 95% CI |
|---|---|---:|---|
| RandomPolicy vs. AFAP | Transformer overload (abs diff, kWh) | **-5.106** | [-8.763, -1.907] |
| RandomPolicy vs. Round Robin | Transformer overload (abs diff, kWh) | +0.224 | [0.075, 0.411] |
| TD3 (seed 100) vs. RandomPolicy | Transformer overload (abs diff, kWh) | +0.228 | [-0.233, 0.795] |
| TD3 (seed 100) vs. Round Robin | Transformer overload (abs diff, kWh) | +0.452 | [0.032, 0.980] |
| TD3 (seed 101) vs. Round Robin | Transformer overload (abs diff, kWh) | +2.654 | [0.898, 4.800] |
| TD3 (seed 102) vs. Round Robin | Transformer overload (abs diff, kWh) | +0.962 | [0.213, 1.837] |
| every TD3 seed vs. AFAP/RR | EVs served (pct diff) | 0.000 | [0.000, 0.000] |

Week 3's original conclusion was: *"the random-policy control shows worse
overload (12.74 kWh) than even unmanaged AFAP (5.33 kWh) — proving TD3's
near-zero overload is a demonstrated learned behavior, not an artifact of
'any coordination beats AFAP here.'"* **This is false under the corrected
data.** The corrected random-policy control has **significantly lower**
overload than AFAP (95% CI entirely below zero) and is **statistically
indistinguishable** from TD3 (seed 100) (CI spans zero). The physical
explanation is straightforward and was checked, not just accepted: AFAP
dispatches every connected port at (near-)maximum current every step, which
is what drives this station's 4:1 oversubscription into overload; a uniform
random action in `[0,1]` per port has an expected value of ~0.5x max power,
so simply *not always maxing out* — which a policy needs no learning at all
to do — already removes most of the overload at this specific
oversubscription ratio. The control still does its job on a different,
narrower claim (Round Robin vs. RandomPolicy IS a small but statistically
real difference, +0.224 kWh [0.075, 0.411]), but it no longer supports
"TD3/Round Robin learned/derived a real overload-avoidance behavior beyond
what naive throttling gives for free." Also newly significant: TD3 vs.
Round Robin on overload flips from "TD3 matches Round Robin" (both ~0 in
the buggy data) to **TD3 is significantly worse than Round Robin** for all
3 seeds (all three 95% CIs exclude zero). `total_ev_served` is now
**identical** across every algorithm tested (all diffs [0.000, 0.000]) —
the "TD3 serves fewer/inconsistent EVs" tradeoff reported in Week 3 does
not survive the correction either; it was an artifact of the same bug.

**What is and isn't invalidated, stated explicitly:**
- **Trained models: still valid, no retraining.** Confirmed above — the
  training-time finding changes what "TRAIN_SEEDS" should be understood to
  mean, not whether the weights are legitimate.
- **Evaluation rows: all 200 were invalid, now corrected and re-registered.**
- **AFAP / Round Robin: confirmed unaffected**, empirically, not assumed —
  see the reproduction method above.
- **The paired-bootstrap results were invalid in a specific way, not just
  "wrong numbers":** the 50 cells were never actually paired (each
  TD3/RandomPolicy episode ran an independent, re-randomized scenario, not
  the same scenario AFAP/Round Robin saw on that nominal cell), so
  `paired_bootstrap_ci` was applied under an assumption — shared scenario
  per cell — that did not hold. The point estimates happened to land in a
  broadly similar range for several metrics (same underlying scenario
  *distribution*, still 50 draws), but the confidence intervals were
  computed as if within-cell variance had been removed by pairing, when it
  hadn't been. The overload/control finding above is the case where this
  mattered enough to flip a conclusion, not just narrow a CI.

**Downstream re-derivation, all done this session:**
`results/rl_vs_baseline_bootstrap.csv` and `results/rl_train_seed_dispersion.csv`
regenerated (`scripts/analyze_rl_results.py`, no new bootstrap code, same
`stats_utils.paired_bootstrap_ci` as Week 3). All 9 figures regenerated
(`scripts/make_figures.py`) and visually QA'd individually — **no new bugs
found this pass** (unlike Week 2's 2 and Week 3's 5); `f01` and `f02`
visibly reflect the corrected overload pattern (Random control now sits
just above Round Robin, well below AFAP, instead of above everyone); `f05`'s
forest plot shows the corrected, CI-backed per-algorithm comparisons above;
`f07`'s heatmap shows Random (control) now green (good) rather than red
(worst) on the overload column; `f06`/`f08`/`f09` are structurally
unaffected (f06 correctly still excludes TD3/RandomPolicy from the size
sweep; f08 reads training-time `learning_curve.csv` files, untouched by an
evaluation-only bug; f09 reads a wholly separate registry file). Full test
suite re-run: 10/10 passing (8 original + 2 new).
`03_rl_baseline.md` and `Week3_Parameter_Method_and_Implementation_Justification.docx`
corrected in the same session — see that chapter's own correction section
for the narrative-level writeup; not duplicated here.

## 2026-08-13 — Week 3, Entregables 5-7: training, evaluation, statistics, and two real bugs caught by visual QA

**Entregable 5 (training) — done.** All 3 `TRAIN_SEEDS` trained sequentially
(`scripts/train_td3.py`) at the confirmed `TOTAL_TIMESTEPS=60_000` budget.
Wall-clock: ts100=57.62 min, ts101=54.91 min, ts102=55.06 min — **167.6 min
(2.79h) total**, matching the 165.9 min calibration estimate almost exactly.
Artifacts per seed in `experiments/phase2_algorithms/models/TD3_vanilla_ts{seed}/`:
`final_model.zip`, `final_model_vecnormalize.pkl`, `learning_curve.csv`,
`manifest.json` (git commit, hyperparameters, library versions, wall-clock).

**Convergence: weak but real, not clean.** Linear-fit slope of mean episode
reward vs. timesteps is positive for all 3 seeds (+21 to +30 per 1,000
steps) — same direction every time, not coincidence — but small relative to
within-seed noise (episode-reward std ~1,000-1,500 against means of
~-22,000 to -25,000). Reported as-is: a real but weak learning signal under
the declared 2.8h-total budget (vs. the source papers' 5-48h on HPC), not
dressed up as clean convergence. See `figures/f08_learning_curves.png`.

**Bug found during smoke-testing, before the real run:** `ep_info_buffer`
(the mean-episode-reward source `LearningCurveCallback` reads) stayed empty
because the training env wasn't wrapped in
`stable_baselines3.common.monitor.Monitor` — SB3 only populates it from an
`"episode"` info key that Monitor adds. Fixed at the source in
`env_factory.make_training_env` (now returns a Monitor-wrapped env), not
per call site. Caught before the real 2.8h run, not after.

**Entregable 6 (evaluation) — done.** All 3 TD3 checkpoints plus a
random-policy negative control evaluated on the same 50-cell grid (`SEEDS`
x `EVAL_DAYS`) used for AFAP/Round Robin, via `scripts/evaluate_rl.py`
(`--execute`, 200 runs, all appended, 0 skipped). `deterministic=True` for
TD3 `predict()`. Registry rows: `TD3_vanilla_ts100/101/102` and
`RandomPolicy`, all `algorithm_family="rl"`, `notes` recording
`reward=...,state=...,train_seed=...` per row.

**station_v0_bogota, n=50 per algorithm, mean [95% CI]:**

| Algorithm | EVs served | Profits | Avg. satisfaction | min energy satisfaction | Transformer overload (kWh) | Tracking error | Battery degradation |
|---|---|---|---|---|---|---|---|
| AFAP | 13.44 [13.22,13.67] | -45.73 [-53.80,-37.66] | 1.000 | 100.00 | 5.33 [1.93,8.73] | 51615 [48451,54779] | 0.000 |
| Round Robin | 13.44 [13.22,13.67] | -44.51 [-52.32,-36.71] | 1.000 | 99.95 | 0.00 | 12273 [11335,13211] | 0.000 |
| TD3 (seed 100) | 13.00 | -28.59 [-34.01,-23.16] | 0.996 | 93.06 [90.67,95.45] | 0.00 | 16668 [16325,17011] | 0.000 |
| TD3 (seed 101) | 10.40 [10.26,10.54] | -36.69 [-42.96,-30.42] | 0.995 | 92.31 [89.67,94.95] | 0.00 | 28152 [27540,28765] | 0.000 |
| TD3 (seed 102) | 12.80 [12.53,13.07] | -39.69 [-46.18,-33.19] | 0.984 | 86.71 [84.58,88.84] | 0.98 [0.16,1.81] | 25691 [24356,27025] | 0.000 |
| RandomPolicy (control) | 13.90 [13.56,14.24] | -48.19 [-57.38,-39.01] | 1.000 | 100.00 | **12.74 [3.45,22.03]** | 43878 [37148,50609] | 0.000 |

**Headline pattern -- a real tradeoff, not a uniform win:**
- **Overload:** all 3 TD3 seeds essentially match Round Robin (0.00, 0.00,
  0.98 kWh) and dramatically beat AFAP (5.33 kWh). The random-policy
  control shows **12.74 kWh -- worse than even unmanaged AFAP** -- proving
  this isn't "any policy beats AFAP here"; TD3 learned a real
  overload-avoidance behavior the control does not exhibit.
- **Cost of that:** `min_energy_user_satisfaction` drops to 93.1/92.3/86.7
  for TD3 (vs. ~100 for AFAP/RR/Random), and `total_ev_served` is lower and
  seed-inconsistent (13.0/10.4/12.8 vs. AFAP/RR's 13.44).
- **`tracking_error` is WORSE for TD3 than Round Robin** (+49% to +152%,
  paired bootstrap, see below) despite AFAP being worse still -- consistent
  with the declared reward-vs-metric misalignment
  (`03_rl_baseline.md` S3.4): the reward's tracking term and the reported
  `tracking_error` metric are related but not identical.
- **`total_profits` looks better for TD3** (less negative than both
  baselines, all 3 seeds) -- but profit is NOT in the reward at all (S3.2);
  this is very likely a side effect of serving fewer EVs / less energy
  exchanged (lower operating cost), not an intentional profit optimization.
  Stated as a caveat, not claimed as an achievement.
- **Battery degradation drops ~12-28% vs. both baselines** across all 3
  seeds (paired bootstrap) -- also very likely confounded with serving
  fewer EVs (less cycling), not necessarily "better battery management."

**Entregable 7 (statistics) — done**
(`scripts/analyze_rl_results.py` -> `results/rl_vs_baseline_bootstrap.csv`,
`results/rl_train_seed_dispersion.csv`, both using
`stats_utils.paired_bootstrap_ci`, no new bootstrap code written). Full
paired-bootstrap table (45 rows: 3 seeds x 2 baselines x 9 metrics
(each land n=50 paired cells)) in the CSV; headline percentages above.

**Cross-training-seed dispersion (separate from the scenario-level 95%
CIs above -- a genuinely different uncertainty source, see
`eval_protocol.py`'s SEEDS-vs-TRAIN_SEEDS docstring):**

| Metric | ts100 mean | ts101 mean | ts102 mean | spread (max-min) | relative spread |
|---|---|---|---|---|---|
| total_ev_served | 13.0 | 10.4 | 12.8 | 2.6 | 21.5% |
| total_profits | -28.59 | -36.69 | -39.69 | 11.10 | 31.7% |
| min_energy_user_satisfaction | 93.06 | 92.31 | 86.71 | 6.35 | 7.0% |
| tracking_error | 16668 | 28152 | 25691 | 11484 | 48.9% |
| total_transformer_overload | 0.0 | 0.0 | 0.98 | 0.98 | 300%* |

\* *300% relative spread is a division-by-near-zero artifact (two of three
seeds are exactly 0.0) -- flagged as such, not reported as a literal "300%
worse" claim.*

This dispersion is substantial (e.g. `total_ev_served` varies 21.5% and
`tracking_error` varies 48.9% purely from training-seed choice, holding the
evaluation grid fixed) -- reporting only one seed, or averaging across
seeds without disclosing this spread, would understate real uncertainty.
This is exactly why the Week 3 brief prohibits reporting only the best
seed.

**Registry contract change (Week 2 -> Week 3), documented as required
before use:** `ev2gym_thesis/registry_analysis.py`'s `main_grid_rows()`
used to filter by `notes == ""`, which silently excluded ALL 200 new RL
rows (they legitimately use non-empty `notes` for reward/state/train_seed
metadata per S3.5's registry-comparability requirement). Fixed by
introducing `NON_GRID_NOTES_MARKERS = {"week1_reference_day",
"pipeline_smoke_test_grid"}` and filtering by exact-marker exclusion
instead of "notes is non-empty" -- verified the two Week 1 reference rows
and the grid smoke test are still correctly excluded (`week1_reference_day`
rows found: 2, matching Week 1/2 expectations) and that `station_v0_bogota`
now correctly returns 300 main-grid rows (50 x 6 algorithms). This does NOT
affect `scripts/measure_degradation_by_ambient.py`, which has its own
independent inline `notes == ""` filter, not a call into `main_grid_rows`.

**Two real bugs found by the mandatory visual QA pass (Entregable 7),
neither of which raised an exception -- "ran without error" was not "was
correct," exactly as the Week 3 brief warned, and exactly as Week 2 found
two similar silent bugs:**

1. **TD3 timeseries were entirely zeroed out.** `figures/f01_power_profile.png`
   showed all 3 TD3 seeds as a flat line at 0 kW for the entire reference
   day, even though the same cell's own registry row correctly reported 13
   EVs served. Root cause: `scripts/evaluate_rl.py`'s original TD3 stepper
   ran the episode through `VecNormalize(DummyVecEnv([env]))`, and SB3's
   `DummyVecEnv` auto-resets its underlying env INSIDE the same `step()`
   call that returns the terminal transition -- so by the time external
   code read `env.current_power_usage` after the episode loop, the env had
   already been silently reset to a fresh (all-zero) state. Confirmed
   empirically: `current_power_usage.sum()` was `0.0` and `current_step`
   was `0` immediately after the loop, while the auto-preserved `info`
   dict's `total_ev_served` was still correctly `13`. **Scalar registry
   metrics were unaffected** (SB3 preserves the pre-reset info dict, which
   is where `stats_to_row` reads from) -- only the saved per-step
   timeseries were corrupted. Fixed by stepping the raw env directly
   (bypassing the VecEnv wrapper entirely) and manually applying the
   loaded `VecNormalize`'s observation normalization before each
   `model.predict()` call -- confirmed to produce IDENTICAL scalar stats to
   the original (VecEnv) stepper, only the timeseries capture changes. All
   150 TD3 timeseries `.npz` files were regenerated with the fixed stepper
   (registry rows were NOT re-appended -- already correct, would have
   collided with the dedup key anyway).
2. **Illegible/misleading figures once RL added 4 more algorithms.**
   `f02_metrics_bars` and `f04_distributions`: x-axis labels overlapped
   into an unreadable run-on string (6 algorithm names at a font/width
   sized for 2). Fixed with rotated labels (`f02`) and rotated labels + a
   width that scales with algorithm count (`f04`). `f05_vs_baseline`: title
   text was clipped at the figure's right edge (same failure mode as Week
   2's title-cutoff bug, different trigger -- now caused by the title
   enumerating 5 algorithm names instead of 1) and had large,
   growing-with-height wasted top/bottom margins (fixed-fraction
   `subplots_adjust` on a figure whose height now scales with algorithm
   count). Fixed by dropping the redundant algorithm-name enumeration from
   the title (already shown per-row on the y-axis) and switching to
   fixed-inch (not fixed-fraction) margins. `f06_size_sensitivity`: TD3/
   RandomPolicy appeared as disconnected single dots at the 8-port
   reference point only (they were never run across the size sweep -- a
   declared Week 3 scope limitation), implying a size trend that doesn't
   exist; fixed by restricting this figure to algorithms actually present
   on a non-reference sweep config.

**`f08_learning_curves` activated** (was an inert stub since Week 2,
correctly skipping until `algorithm_family=="rl"` rows existed). Reads each
training run's own `learning_curve.csv` directly (like `f09` reads its own
separate source file) -- NOT registry data, since the registry has no
reward-vs-timesteps time series column.

## 2026-08-12 — Week 3, Entregable 4: TD3 time calibration and confirmed training budget

**Calibration run** (`scripts/calibrate_td3_timing.py`, real `config_rl.py`
hyperparameters, `station_v0_bogota`, `train_seed=100`, round-robin cycling
over the 20-date `TRAIN_DAYS` pool): 5,000 timesteps completed in **276.4s
(4.61 min) = 18.09 steps/s**, 53 episodes started. This throughput is likely
dominated by per-episode environment reconstruction
(`env_factory.TrainingDayCyclingEnv` rebuilds `EV2Gym` — including
rereading the day-config YAML and the Netherlands day-ahead price CSV —
every episode, a documented design-decision tradeoff, not a bug) rather
than TD3's own gradient-step cost; flagged as a caveat on the number, not a
correction to it.

Linear extrapolation, presented as 4 candidates (15k/30k/60k/90k
timesteps/seed) against the user's stated constraints (~4h total budget,
~75 min/seed ceiling for 3 training seeds):

| timesteps/seed | est. time/seed | episodes | x per TRAIN_DAYS day | x3 seeds total |
|---:|---:|---:|---:|---:|
| 15,000 | 13.8 min | 156.2 | 7.81 | 41.5 min |
| 30,000 | 27.6 min | 312.5 | 15.62 | 82.9 min |
| 60,000 | 55.3 min | 625.0 | 31.25 | 165.9 min (2.8h) |
| 90,000 | 82.9 min | 937.5 | 46.88 | 248.8 min (4.2h) |

90,000 was already excluded from recommendation before asking: 82.9 min/seed
breaks the 75 min/seed ceiling, and 248.8 min breaks the 4h total budget.
**User confirmed 60,000 timesteps/seed** (asked explicitly via the tool, not
assumed) — the largest candidate respecting both ceilings, at 165.9 min
(2.8h) total, leaving headroom for Entregable 6's evaluation runs. Recorded
in `ev2gym_thesis/rl/config_rl.py`'s `TOTAL_TIMESTEPS = 60_000`.

**Declared scope reduction, stated plainly, not presented as equivalent:**
the PI-TD3/TD3 papers this thesis compares against trained for 5-48 hours
on HPC hardware. This project's entire Week 3 training budget (all 3
training seeds combined) is 2.8 hours on a single CPU laptop — roughly
**2-17x less wall-clock time than the papers' single training runs**, before
even accounting for HPC hardware being substantially faster per wall-clock
hour than a laptop CPU for this workload. At 60,000 timesteps, the agent
sees each `TRAIN_DAYS` date only ~31 times. Whatever convergence result
Entregable 5 produces must be read against this budget — a result showing
no clear convergence is an expected, legitimate possible outcome of this
reduced scope, not evidence of a bug, and will be reported as such rather
than adjusted or hidden (`CLAUDE.md` rule 3, brief S5 trap 7).

## 2026-08-12 — Week 3 kickoff: scope deviation (RL vanilla, not MPC), preflight (branch `semana-3`)

**Scope deviation, decided before any code was written.** `PROJECT_ROADMAP.md`
originally assigned Week 3 to the Gurobi/MPC baseline and Weeks 4–5 to RL.
This is deliberately reversed: **Week 3 = RL baseline vanilla (TD3), Week 4 =
perfect-information reference (free solver) + PI-TD3, Week 5 = full
comparison.** Full
reasoning (also in `PROJECT_ROADMAP.md`'s Phase → Objective Mapping note):

1. RL training is the highest-lead-time, highest-risk item in the compressed
   8-week plan; pushing it to Weeks 4–5 would concentrate that risk with no
   slack left to recover from a failed or slow run.
2. Week 2 confirmed only a *"Restricted — for non-production use only"*
   Gurobi license is available in this environment, not an academic one (see
   `02_model_validation.md`'s Gurobi section, 2026-08-12). Project policy
   already forbids any module from importing `gurobipy`. An MPC baseline in
   Week 3 would have made the week depend on a licensing question that was
   never actually resolved.
3. The perfect-information upper bound will very likely be computed with a
   free solver (HiGHS/CVXPY/OR-Tools), not Gurobi. Week 3 delivers only a
   short design note for this (no code, no numbers) so Week 4 doesn't have to
   make that call under time pressure.

`PROJECT_ROADMAP.md` was updated in the same commit: the old MPC-first plan
is marked `[SUPERSEDED]` and kept, not deleted, immediately above the revised
Week 3/4/5 sections. `CLAUDE.md`'s Current Phase section was also corrected
in this session — it had been left saying Week 2 was "in progress" (registry
backfill pending) after Week 2 had actually been finished and merged to
`main` on 2026-08-12; the two facts had drifted apart because the doc update
was deferred to be bundled with Week 3's first commit rather than committed
alone.

**Preflight (branch `semana-3`, created from `main` at commit `0b098f5`):**

- `semana-2` and `main` point to the same commit; working tree was clean —
  structurally fine to branch, no reconciliation needed.
- `results/master_results.csv`: 503 rows, generated by `0b098f5`.
  `config_name` in {`station_v0_bogota`, `station_n02_tx100`,
  `station_n02_tx025`, `station_n16_tx100`, `station_n16_tx200`,
  `v2ggrid_smoke_test`}; `algorithm` in {`ChargeAsFastAsPossible`,
  `RoundRobin`}; `algorithm_family` is `heuristic`-only — confirms no RL rows
  exist yet, so figure `f08` is correctly still an inert stub.
- Versions: Python 3.11.9, numpy 2.2.6, gymnasium 1.3.0 (no legacy `gym`
  installed), torch 2.9.0+cpu (already present). `stable-baselines3` was NOT
  installed; installed now (2.9.0) and added to `requirements.txt` along with
  `torch>=2.8` — unlike `gurobipy`, this is a real pipeline dependency.
- `ev2gym/rl_agent/reward.py`: 12 reward functions. Public/PST-relevant ones
  are `SquaredTrackingErrorReward` (env default; tracking-error only) and
  `SqTrError_TrPenalty_UserIncentives` (tracking error + transformer-overload
  penalty + user-satisfaction penalty). The rest (`ProfitMax_*`,
  `profit_maximization`, the `V2G_*` family) target Business/ProfitMax or
  V2G/grid scenarios (several require `simulate_grid=True`, which this
  project keeps `False` through Objectives 1–3) and don't fit this thesis's
  Public/PST variant.
- `ev2gym/rl_agent/state.py`: 5 state functions. `PublicPST` is the env
  default and the only one matching this project's scenario (no price
  forecasts, no grid/voltage terms) — vector of normalized timestep, next
  setpoint, current usage, and per-connected-EV `[full-flag, energy
  exchanged, dwell time]`. `BusinessPSTwithMoreKnowledge`, `V2G_profit_max`,
  `V2G_profit_max_loads`, `V2G_grid_state` all target other scenario
  families or need `simulate_grid=True`.
- `EV2Gym.__init__` (`ev2gym/models/ev2gym_env.py:38-56`): `reward_function`
  and `state_function` are plain constructor kwargs, defaulting to
  `SquaredTrackingErrorReward`/`PublicPST` if not passed — no
  string/registry lookup, the function object is passed directly and stored
  as `self.reward_function`/`self.state_function`.
- Gymnasium API compliance: full, no SB3 shim needed. `import gymnasium as
  gym` (not legacy `gym`), `reset(seed=None, options=None, **kwargs) ->
  (obs, {})`, `step(actions) -> (obs, reward, terminated, truncated, info)`
  — verified by reading the source, not assumed.
- Action space: `station_v0_bogota.yaml` has `v2g_enabled: False`, so
  `EV2Gym`'s action space is `Box(low=0, high=1)`, not `[-1,1]`. Checked
  Stable-Baselines3's installed source
  (`stable_baselines3/common/off_policy_algorithm.py:402,410`): TD3 samples
  in the policy's normalized `[-1,1]` space and calls
  `policy.scale_action`/`unscale_action` to rescale against
  `self.action_space.low/high` automatically. Trap #6 from the Week 3 brief
  (tanh output vs. env action range) is a non-issue here, confirmed by
  reading SB3's source rather than assumed — as long as nothing wraps the
  env in a way that misreports its action_space bounds.
- Trap #3 from the Week 3 brief (`ev.max_ac_charge_power` as a normalization
  denominator, even for DC charging) was already resolved at the config
  level before this session: `station_v0_bogota.yaml` sets
  `ev.max_ac_charge_power: 50` == `ev.max_dc_charge_power: 50`. The RL path
  reuses this same config through `ev2gym_thesis/config_utils.py`, so it
  inherits the fix; nothing RL-specific needed here.
- `TRAIN_DAYS` (disjoint-asserted against `EVAL_DAYS`) already existed in
  `ev2gym_thesis/eval_protocol.py` from Week 2 — added preemptively in
  anticipation of Week 3. Only `TRAIN_SEEDS` was missing (Entregable 1).

## 2026-08-12 (RESUMED, all Week 2 deliverables now complete) — supersedes the HANDOFF note below

Resumed from the HANDOFF note below and finished every remaining item, per
the user's choice to "finish everything before committing" rather than
defer Deliverables 4/5/7.

**Deliverable 4 (figures) — finished.** `scripts/make_figures.py` rewritten
to read the full `results/master_results.csv` (previously it only knew
`degradation_by_ambient.csv`, for f09). Implemented f01-f07 (f08 correctly
skips cleanly, no RL rows yet). **Every figure was visually inspected, not
just checked for "did it run" — this caught 2 real bugs:**
- `f05_vs_baseline`: figure canvas too narrow for its own labels — title
  and axis label were cut off outside the rendered image. Fixed sizing.
- `f07_metric_heatmap`: **color-direction bug.** `total_transformer_overload`
  is lower-is-better, but naive per-column min-max normalization colored
  the *worse* value (AFAP, 5.3 kWh) green and the *better* value (Round
  Robin, 0 kWh) red — backwards from every other column in the same
  figure. Added a `LOWER_IS_BETTER` set and inverted normalization for
  those columns so green consistently means "better," not just "higher
  raw number." This is exactly the kind of error that survives a "did it
  render" check but not an actual look at what the colors claim.

Also fixed, while building the figures: `scripts/backfill_registry.py` was
capturing `transformer_power`/`n_connected_evs` **once, after the
simulation loop ended** (a final-step snapshot), not per-step — so every
existing `results/timeseries/*.npz` has those two fields wrong-shaped
(single value instead of a 96-step array). `station_power` in the same
files is correct (reads `env.current_power_usage` directly, unaffected).
Fixed in code for future runs; the existing 500 npz files were **not**
regenerated, since nothing currently reads those two fields (only
`station_power`, used by f01, which is fine) — flagged rather than
silently left broken or silently re-run for ~45 minutes of no benefit.

**Deliverable 5 (`thesis_docs/chapters/03_algorithms.md`) — written.**
Full Rationale/Implementation/Hyperparameters/Results/Conclusions/
Limitations for AFAP and Round Robin, filled from
`results/master_results.csv` (`station_v0_bogota`, 50 runs/algorithm).
Headline paired result: Round Robin eliminates all measured transformer
overload (0.0 kWh vs. AFAP's 5.33 kWh [1.93, 8.73], 95% CI) at a real but
modest profit cost (-2.52% [-4.23%, -0.82%]), no measurable change in EVs
served, energy delivered, or satisfaction. Orfanoudakis et al.'s 313/57 kWh
figures cited only as an attributed external reference point in the
Conclusions prose, never placed in a results table, per the explicit
instruction.

**Sign-off obtained** (asked explicitly via the tool, not assumed): the
user confirmed keeping `results/degradation_by_ambient.csv` as a separate
file rather than retrofitting `master_results.csv` with an
`ambient_scenario` column.

**Deliverable 7 (hand-back document) — built as a generator, not
hand-written.** `scripts/build_week_doc.py` extracts every
`doc:begin <tag>`/`doc:end <tag>` region from `ev2gym_thesis/*.py` and
`scripts/*.py` fresh from disk (16 tagged regions found). Found and fixed
one real bug immediately: `ev2gym_thesis/figures.py` had an opened `doc:begin
write_caption` with no matching `doc:end` — the extractor's own strict
validation (raises rather than silently skipping) caught it on the first
run. Also trimmed 3 snippets that exceeded the ~40-line guideline
(`append_runs` 53->40, `paired_bootstrap` 47->34, `recompute_calendar`
67->40) by moving the `doc:begin` marker past each function's docstring —
the explanatory prose lives in the hand-back document text instead of
inside the quoted code.

`scripts/make_week2_handback.py` assembles
`thesis_docs/Week2_Parameter_Method_and_Implementation_Justification.md`
(Part 1: parameters introduced this week, labeled
validated/empirical/simplification; Part 2: every new file's location,
purpose, design decisions with the rejected alternative stated, library
choices, and the actual extracted code) plus a References section
(Primary/Secondary/Tertiary tiers, carrying forward the convention from
Week 1). Records the git commit and generation timestamp at the top, and
is regenerable with one command after any code change, per the
requirement.

`scripts/render_docx.py`: a small, project-specific (not general-purpose)
Markdown-to-docx renderer, following the stated Word conventions (plain
black text, no Word "Heading" styles — headers are bold plain paragraphs
with `style.name == "Normal"`, verified by reading the generated file back
with `python-docx`). Found and fixed one real bug: the first version wrote
table cells with raw `cells[i].text = val`, which left literal Markdown
syntax (backticks, asterisks) visible in the rendered table instead of
monospace/bold formatting — fixed by routing cell text through the same
inline-formatting parser used for body paragraphs, then verified by
reading the cells back and confirming the backticks were gone and the
run's font was `Consolas`. `python-docx` added to `requirements.txt`
(was not previously a project dependency).

**Claim-vocabulary check:** both new documents (`03_algorithms.md`, and
the hand-back doc, though the latter is technically outside
`check_claims.py`'s `thesis_docs/chapters/*.md` glob and was checked
manually instead) avoid the forbidden solver-optimality term outside of
meta-references to the reserved schema value or the policy itself (a
hyphenated-compound phrase in `03_algorithms.md`'s Pareto-frontier
discussion was reworded to "non-dominated," since the checker's
word-boundary regex matches the forbidden term inside compound words too).
`scripts/check_claims.py` passes clean.

**Status: all of Deliverables 1, 2, 3, 4, 5, 6, 7 and the Gurobi policy are
now complete**, per the original Week 2 prompt's own checklist. Nothing
committed yet — that's the next and last step.

## 2026-08-12 (HANDOFF, session cut short — laptop about to lose power) — READ THIS FIRST NEXT SESSION

User chose "finish everything before committing" for the remaining Deliverable
4/5/7 gap identified against the original Week 2 prompt. Made substantial
progress, then had to stop abruptly (battery). **Nothing is committed.**
`git status` on `semana-2` will show everything described below as
uncommitted/untracked. No background processes were left running (checked,
none found) -- safe to close the laptop.

**Done since the last "Status:" note further down this file:**
- Fixed a real bug in `scripts/backfill_registry.py`: `transformer_power`
  and `n_connected_evs` were captured ONCE after the simulation loop ended
  (a final-step snapshot) instead of per-step, so every existing
  `results/timeseries/*.npz`'s `transformer_power`/`n_connected_evs` fields
  are wrong-shaped (single value, not a 96-step array) -- `station_power`
  in those same files is correct (it reads `env.current_power_usage`
  directly, unaffected by the bug). Code is fixed for future runs; the
  existing 500 npz files were NOT regenerated (nothing currently uses those
  two fields, so not worth another ~45 min re-run -- flagged, not silently
  left broken).
- Built `ev2gym_thesis/registry_analysis.py` (`load_registry()`,
  `main_grid_rows()` -- shared filtering so every figure treats the
  registry the same way: excludes the grid smoke test, separates the
  balanced 500-row grid from the 2 Week 1 historical rows).
- Rewrote `scripts/make_figures.py` to actually read the full
  `results/master_results.csv` (previously it only knew about
  `degradation_by_ambient.csv` for f09). Implemented **f01 through f07 and
  f09** (f08 correctly detects zero `algorithm_family=="rl"` rows and skips
  cleanly with a log message, per spec -- not an error).
- **Visually inspected every figure, found and fixed 2 real bugs, not just
  "ran without crashing":**
  1. `f05_vs_baseline`: figure was too narrow for its own y-tick labels --
     title and axis label were literally cut off outside the canvas.
     Fixed sizing/margins.
  2. `f07_metric_heatmap`: **color direction bug** -- `total_transformer_overload`
     is a lower-is-better metric, but the naive column min-max normalization
     colored the WORSE value (AFAP, 5.3 kWh) green and the BETTER value
     (Round Robin, 0 kWh) red, backwards from every other column. Added a
     `LOWER_IS_BETTER` set and inverted normalization for those columns so
     green consistently means "better performance" everywhere, not just
     "higher raw number." This is exactly the kind of mistake that's easy
     to wave through if you only check "did it render," so flagging it
     explicitly here.
- All 8 implemented figures (f01,f02,f03,f04,f05,f06,f07,f09) regenerated
  cleanly in one final run, no errors, no warnings. `figures/` has 24 files
  (8 x {.png, .pdf, .caption.md}).
- Computed the exact Results-section numbers for Deliverable 5 from the
  registry (station_v0_bogota, 50 runs/algorithm, mean +/- 95% CI, paired
  bootstrap RR vs AFAP) -- **not yet written into a chapter file**:
  - AFAP: EVs served 13.44 [13.21,13.67], energy charged 196.7 kWh
    [190.9,202.5], transformer overload 5.33 kWh [1.93,8.73], satisfaction
    1.0, profits -45.73 [-53.8,-37.66].
  - Round Robin: EVs served 13.44 (identical), energy charged 196.5 kWh
    [190.7,202.4], transformer overload 0.0 kWh [0,0], satisfaction ~1.0,
    profits -44.51 [-52.32,-36.71].
  - Paired RR vs AFAP (bootstrap 95% CI, matched by seed+day cell):
    transformer overload -5.33 kWh [-8.96,-2.13] (absolute diff, AFAP
    baseline is exactly 0 so % is undefined), profits -2.52%
    [-4.23%,-0.82%], tracking_error -76.18% [-77.41%,-74.77%],
    power_tracker_violation -100% [-100%,-100%] (RR essentially eliminates
    it).

**NOT done yet, in priority order for next session:**
1. **`thesis_docs/chapters/03_algorithms.md` (Deliverable 5) -- not written
   at all.** The numbers above are ready to use directly; just needs the
   template filled (Rationale/Implementation/Hyperparameters/Results/
   Conclusions/Limitations, per algorithm) for AFAP and Round Robin. The
   313 kWh / 57 kWh Orfanoudakis et al. figures go in the text only as an
   attributed external reference point, never mixed into our own results
   table -- per the original prompt's explicit instruction.
2. Update `02_model_validation.md`'s header ("Status: partial" note) -- a
   lot has been resolved since that was written (grid-scope conflict,
   degradation now measured with CI, etc.); the note is stale.
3. Confirm with the user (asked once already, not yet re-confirmed after
   building the figures) that using a **separate** file
   (`results/degradation_by_ambient.csv`) instead of adding an
   `ambient_scenario` column to `master_results.csv` is acceptable --
   deviates from the literal Deliverable 6.4 text, justified by analogy to
   the `simulate_grid` separation principle, but was never explicitly
   signed off.
4. `scripts/build_week_doc.py` -- not started. Extracts `# doc:begin
   <tag>`/`# doc:end <tag>` regions (already placed in several files this
   session: `ev2gym_thesis/eval_protocol.py`, `registry.py`,
   `degradation_bogota.py`, `figures.py`) into the hand-back document at
   build time.
5. `thesis_docs/Week2_Parameter_Method_and_Implementation_Justification.md`
   + its `.docx` rendering (Deliverable 7) -- not started at all. Per the
   original order-of-work this was always meant to be built last, so its
   absence alone isn't a surprise -- but it's still fully outstanding.
6. `.gitignore`/`CLAUDE.md`/`PROJECT_ROADMAP.md` diff from the grid-scope
   resolution earlier this session was shown to the user but never
   committed.
7. Nothing from this entire `semana-2` session (going back to before the
   sleep interruption too) is committed. `git status` will show a large
   number of new/modified files across `ev2gym_thesis/`, `scripts/`,
   `data/`, `results/`, `figures/`, `thesis_docs/chapters/`, and the
   root-level `.gitignore`/`CLAUDE.md`/`PROJECT_ROADMAP.md`/
   `requirements.txt`/`setup.py`.

**To resume:** re-read this note, then pick up at item 1 (algorithm
chapter) using the numbers already computed above -- no need to re-run
anything to get those.

## 2026-08-12 — Week 2 kickoff: seed protocol, registry, degradation calibration (branch `semana-2`)

Week 1 was confirmed closed by the user (station_v0_bogota.yaml: AFAP 14 EVs /
0.132 kWh overload, Round Robin 14 EVs / 0.0 kWh overload — see
`01_baseline.md`). `number_of_charging_stations = 8` was retroactively
grounded in the Enel X Colombia public charge-point inventory (67 chargers /
21 sites in Bogota; CC Retiro = 8 ports) — see `01_baseline.md` for the full
citation and its two declared limitations (AC-only 8-port sites; Enel X is a
lower bound, not a census). Branch `semana-2` was created from `semana-1`'s
tip (not `main`, which still lacks the Week 1 fix — same reasoning as last
week, flagged again for the record).

**Gate 1 — seed-sensitivity verification (Deliverable 2).** Created
`ev2gym_thesis/eval_protocol.py`: `SEEDS = [0,1,2,3,4]`, 10 `EVAL_DAYS`
(6 weekdays / 4 weekend days, spread across 2022, day-of-week verified with
`datetime`, not assumed), `REFERENCE_DAY = 2022-01-17` (same as the Week 1
day, for continuity), and 20 `TRAIN_DAYS` reserved for future RL work with
an `assert` at import time that it is disjoint from `EVAL_DAYS`. Ran
`scripts/verify_seed_sensitivity.py`: AFAP on `station_v0_bogota.yaml`,
same day, seed=0 vs seed=1 -> `total_energy_charged` 214.40 kWh vs 204.64
kWh. **PASS** — the seed reaches the EV-spawn RNG.

**Gate 2 — degradation model inspection (Deliverable 6.1), read-only.**
Read `ev2gym/models/ev.py:442-521` (`get_battery_degradation`). Findings:
- Functional form matches a Xu et al. (2018)-type semi-empirical model
  (calendar aging ~ alpha(V,theta)*t^0.75, cycling aging ~
  beta(V,DoD)*Ah^0.5, Arrhenius term in alpha). **Citation not verified
  against the primary source** — no in-code citation exists, and WebFetch
  attempts against ResearchGate/MDPI/arXiv/Chalmers all failed (403s or
  unreadable scanned PDFs). Cite as "a semi-empirical model of Xu et al.
  (2018) type, as implemented by EV2Gym" until verified, per the user's
  explicit instruction.
- **`theta` is a hard-coded constant, `298.15 K` (25 C), not an input** —
  not derived from config or simulation state. Confirms calibration must be
  an added wrapper, not a parameter change.
- Temperature enters **only** the calendar term (`alpha`); `beta` (cycling)
  has no temperature dependence at all, and its first two terms
  (`z0*(v_half_soc-z1)^2 + z2`) never vary between EVs since `v_half_soc`
  is itself a constant — cycling aging is effectively linear in `delta_DoD`
  only. This is a model limitation to document, not a bug to fix.
- Other hard-coded constants found: `T_acc = 730 days`, `b_cap_kwh = 78`
  (does not match our config's `battery_capacity: 70` — used only as a
  normalization factor, not a bug), `d_dist = 15000 km/year`,
  `G = 0.186 kWh/km` — all describe a generic reference-vehicle usage
  pattern, unrelated to the specific simulated EV.
- **Battery-capacity discrepancy claimed by the user (70 vs "60 kWh")
  resolved: no discrepancy exists.** `station_v0_bogota.yaml` has
  `battery_capacity: 70` consistently; grep over all of `thesis_docs/` and
  `CLAUDE.md` found no document stating 60 kWh. The "60 kWh" figure existed
  only in the Week 2 prompt's own illustrative text for a not-yet-written
  deliverable, never in a committed file.

**Blocking check (user-mandated, before writing any calibration code):**
grepped `ev2gym/rl_agent/reward.py` (14 reward functions) and all of
`ev2gym/*.py` for `battery`/`degradation`/`calendar_loss`/`cyclic_loss` —
zero references outside `ev2gym/utilities/utils.py`'s `get_statistics()`.
**Confirmed: battery degradation does not feed into any reward function.**
Recomputing it post-hoc is therefore exact, not an approximation.

**Deliverable 3 — registry infrastructure.** Built
`ev2gym_thesis/registry.py` (`REGISTRY_COLUMNS` schema, `append_runs()`
with schema validation + dedup on `(config_name, algorithm, seed,
eval_day)`, `save_timeseries()`), `ev2gym_thesis/config_utils.py`
(per-eval-day temp config generation, since EV2Gym reads the date once from
the config file path at construction), and `scripts/backfill_registry.py`.
Dry-run reported **500 new simulation runs** (5 configs x 2 algorithms x 5
seeds x 10 days) + 2 backfilled Week 1 reference rows (read from the
existing committed CSVs, not re-run), estimated **~54 minutes**
single-threaded from one measured sample run (6.51s), not guessed.

Also had to fix `.gitignore` again: the blanket `/results/` rule (already
narrowed once, for Week 1) still fully blocked `results/master_results.csv`
at the repo root. Changed to `/results/*` + explicit
`!/results/master_results.csv` negation, so `results/timeseries/*.npz`
stays ignored (regenerable from config+seed+day, consistent with the
project's "no large binaries in git" convention) while the registry CSV is
tracked. Same fix applied for a `tests/` blanket-ignore conflict — rather
than patch that rule again, thesis unit tests live in
`ev2gym_thesis/tests/` instead of a top-level `tests/`.

User confirmed launching `--execute`. **Backfill started, then paused by
user request (couldn't wait ~54 min) at 26/502 rows** — safe to stop and
resume anytime given the append-only + dedup design; no work lost. Resume
tomorrow with `python scripts/backfill_registry.py --execute`.

**Deliverable 6.2-6.4 — Bogota degradation calibration wrapper.** Scope
approved by the user: a new module, not touching `ev2gym/models/ev.py`,
recomputing only calendar aging by substituting `theta` with a
session-integrated effective Arrhenius factor.

*IDEAM verification (mandatory before writing any ambient figure into the
thesis):* downloaded IDEAM's own `normales_climatologicas_periodo_1981-2010.xlsx`
directly (https://www.ideam.gov.co/sala-de-prensa/informes/Normales-clim%C3%A1ticas-est%C3%A1ndar)
and read station **21205791 "Aeropuerto El Dorado Catam - AUT"**, Bogota,
elevation 2547 m. **The originally assumed 13.3 C annual mean does NOT
match this primary source. The verified IDEAM value is 13.68 C**
(annual mean of daily max: 19.31 C; annual mean of daily min: 7.88 C;
monthly means range only 13.29-14.16 C, confirming negligible seasonal
variation). Per the user's explicit instruction, 13.68 C replaces 13.3 C
everywhere. The specific clock-hours of the diurnal min (~06:00) and max
(~14:30) are **not** verifiable against this file (IDEAM publishes monthly
normals, not an hourly curve) — kept as a labelled, unverified assumption.

Also verified (not assumed) from `README.md:113,116`: EV2Gym's own
documentation states arrival/time-of-stay/energy-required distributions are
based on *ElaadNL* data and EV/charger characteristics on the *RVO Survey*
— both Dutch, confirming the "not Colombian" transferability limitation
independently of the Week 2 prompt's claim.

Also verified (read `ev2gym/utilities/utils.py:477-556`, `EV_spawner`):
**EV2Gym does not model queueing.** Arrivals are only ever generated for a
(port, timestep) pair when that specific port is already free at that
moment (`if occupancy_list[counter, t] == 0 and ...`) — there is no queue
data structure and no explicit "EV arrived but was rejected" event; demand
generation is conditioned on capacity availability by construction. This
means Objective 1's "waiting time" metric is **not measurable** in the
current setup — it would require a custom spawn function that generates
arrivals independently of occupancy and explicitly tracks unserved demand.

Built:
- `ev2gym_thesis/ambient_bogota.py` — outdoor/underground diurnal profiles
  (piecewise-linear, trough 06:00 / peak 14:30), anchored to the verified
  IDEAM figures. Underground profile (+/-0.75 C around the 13.68 C mean) is
  a declared, uncited modeling assumption (no published normals exist for
  covered sites).
- `ev2gym_thesis/degradation_bogota.py` — `recompute_calendar_degradation()`:
  integrates `A_eff = mean(exp(-E2/theta(t)))` over each EV's actual
  session steps (reusing `historic_soc`/`active_steps`/`time_of_arrival`/
  `time_of_departure`, already exposed by the simulator), vs. a
  point-estimate at the session's mean temperature, to quantify the
  Jensen's-inequality gap the user flagged (`exp(-E2/theta)` is convex, so
  the point estimate underestimates). `T_acc`, `b_cap_kwh`, `d_dist_km_year`,
  `G_kwh_per_km` exposed as parameters (defaults = ev.py's hard-coded
  values). `delta_t_charging_c` implemented as a **declared, unvalidated
  sensitivity bump** (not a calibrated thermal model, per the user's
  explicit down-scope) applied only at actively-charging steps.
- `ev2gym_thesis/tests/test_degradation_bogota.py` — 6 tests, all pass,
  including the 4 mandated closed-form Arrhenius values (independently
  re-verified before writing the test, not just copied):
  `exp(-6976/theta)` relative to `theta=298.15K` at 280.15K/286.45K/
  293.15K/300.15K = 0.2224/0.3846/0.6709/1.1687 (tolerance 1e-3).

**Preliminary demo (`scripts/demo_degradation_bogota.py`) — ONE run only
(seed=0, 2022-01-17, 14 EVs), NOT the full multi-seed/multi-day measurement:**

| scenario | sum(calendar loss) | vs. 25 C default |
|---|---|---|
| Original (theta=298.15K fixed) | 2.2187e-04 | — |
| Bogota outdoor, delta_t=0 | 1.0700e-04 | -51.77% |
| Bogota outdoor, delta_t=+5C | 1.1582e-04 | -47.80% |
| Bogota underground, delta_t=0 | 9.0331e-05 | -59.29% |

Measured Jensen's gap on this run: the point-estimate (mean-temperature)
approximation underestimates the properly-integrated calendar degradation
by **1.016%**.

**This is a single-run preliminary result, not the CI-backed measurement
the user asked for ("MEDIR, NO SUPONER").** That requires the full 500-run
registry backfill (currently paused at 26/502 rows). Do not treat -51.77%/
-59.29% as final thesis numbers until re-measured across the full protocol.

**Status:** registry backfill paused (resumable), degradation wrapper built
and tested, IDEAM correction applied. Not yet done: finish backfill,
re-measure degradation-by-ambient-scenario across all 50 runs with
confidence intervals, write `f09_degradation_by_ambient`, extend
`ambient_bogota.py`/`data/ambient_profiles.yaml` to the other categoria
especial cities (Deliverable 6.5, explicitly out of scope for today),
`scripts/run_optimal_reference.py` + `scripts/check_claims.py` (Gurobi
hook), figure module, algorithm chapter, hand-back document. Nothing
committed yet — code + this log entry staged for tomorrow's commit.

---

## 2026-08-12 (continued) — Registry backfill completed, grid-scope resolved, CI-backed degradation measurement

**Registry backfill: COMPLETE.** Resumed the paused backfill (twice more —
once normally, once after a forced pause for the machine to sleep). Final
`results/master_results.csv`: **503 rows, 503 unique
`(config_name, algorithm, seed, eval_day)` keys, 0 duplicates** — the
dedup design held across three separate pause/resume cycles. Composition
verified: `station_v0_bogota` 102 rows (100 new + 2 Week 1 historical),
each of the 4 `station_sensitivity/` configs exactly 100 rows (2 algorithms
x 5 seeds x 10 days), `v2ggrid_smoke_test` 1 row.

**Efficiency bug found and fixed during resume:** `scripts/backfill_registry.py`
was re-simulating every already-completed row before checking the registry
to decide whether to skip it — the dedup check only happened at write time,
not before the (expensive) simulation. With ~357 rows already done, a naive
resume would have wasted ~35 minutes re-computing results only to discard
them. Fixed by exposing `ev2gym_thesis.registry.load_existing_keys()`
publicly and pre-filtering `all_run_specs()` against it before calling
`run_single()`. Confirmed fix: resumed run reached the prior 357-row mark
in 12 seconds instead of ~35 minutes.

**One unexplained timing anomaly, reported not hidden:** run
`station_n02_tx025__ChargeAsFastAsPossible__seed0__2022-07-10` (attempt
before the machine sleep) took 356.9s vs. the usual 5-7s, then immediately
returned to normal on the next run with the same config. No confirmed
cause (sibling runs on the identical config were unaffected, so it wasn't
the config itself); plausibly related to the machine approaching sleep
around that time, but not confirmed. The row itself completed correctly
(`total_ev_served` consistent with sibling runs) and was kept as-is.

**Grid-scope conflict, resolved by the user, documents corrected.** The
user resolved the apparent `PROJECT_ROADMAP.md` vs. Week 2 task-brief
conflict: `simulate_grid: False` (station + own local transformer) applies
through Objectives 1-3; `simulate_grid: True` + IEEE 34-bus is reserved for
Objectives 4-5, never mixed into the Phase 2 algorithm-comparison registry
(would break comparability across the 500-row evaluation grid). Week 2's
"grid model validation" was always about the station-and-local-transformer
model, not the feeder. `PROJECT_ROADMAP.md` and `CLAUDE.md` were both
corrected to remove language suggesting feeder/voltage work belongs in
Week 2 (diffs shown to and approved in principle by the user before
editing; not yet committed). `thesis_docs/chapters/02_model_validation.md`'s
grid-representation row updated accordingly, with the reasoning written out
in full (not just referenced).

**De-risking smoke test run and registered.** `scripts/smoke_test_grid.py`
ran `ev2gym/example_config_files/V2Ggrid.yaml` (unmodified upstream
example) once with AFAP: `simulate_grid: True` + IEEE 34-bus loaded,
resolved a power flow, and emitted both `voltage_violation` (a 1-tuple of
`np.float64`, interestingly — not a plain scalar) and
`voltage_violation_counter` without error. **PASS**, not interpreted.
Registered as `config_name="v2ggrid_smoke_test"`,
`notes="pipeline_smoke_test_grid"` — must be excluded from every figure
and results table. This run exposed a real gap in
`ev2gym_thesis/registry.py`'s `_coerce_scalar()`: it handled `list`/
`np.ndarray` but not plain `tuple`, so `voltage_violation` was stored as a
stringified tuple for this one row. Fixed for future `simulate_grid: True`
rows (Objectives 4-5); the smoke-test row's already-written value was left
as-is (append-only, and the row is excluded from analysis regardless).

**Gurobi policy implemented.** Removed `gurobipy` from `requirements.txt`
and `setup.py` (project-root packaging files, not `ev2gym/models`/
`rl_agent` internals). `scripts/run_optimal_reference.py`: self-contained,
never imported elsewhere, license-capability check on startup, exits 0
either way. Run once: `gurobipy` DID start an `Env()` in this environment,
but reported `"Restricted license - for non-production use only"` — this
is the free/size-limited default license that ships with the package, NOT
the university academic license `CLAUDE.md` describes. Flagging explicitly
so this isn't misread later as "the academic license arrived."
`scripts/check_claims.py`: trivial regex check over `thesis_docs/chapters/*.md`
for the forbidden solver-optimality vocabulary (see the Gurobi policy
section in `02_model_validation.md` for the exact terms) while no row using
the registry's reserved solver-comparison `algorithm_family` value exists.
First run failed against `02_model_validation.md`'s own meta-discussion of
the policy (false
positive on text *about* the forbidden words, not a real claim) — reworded
that section to avoid the trigger without making the
checker itself less trivial. Passes clean now.

**`data/ambient_profiles.yaml` (Deliverable 6.5, data only).** Reused the
same downloaded IDEAM `normales_climatologicas_periodo_1981-2010.xlsx` to
verify Medellin (22.53 C, Aeropuerto Olaya Herrera), Cali (24.48 C,
Universidad del Valle), Cartagena (27.78 C, Aeropuerto Rafael Nunez) — all
[Primary]. Two gaps found and flagged rather than papered over:
**Barranquilla has no station in this IDEAM workbook at all** — used
Infobae (which itself cites IDEAM) as [Secondary], marked "pending
verification against IDEAM." **Bucaramanga's only station in the workbook
(Universidad Industrial Santander) records 118 m elevation**, sharply
inconsistent with the ~959-1000 m commonly cited for the city — temperature
value (23.01 C) is plausible and kept, elevation flagged pending
verification rather than silently overridden with the "commonly known"
figure.

**`ev2gym_thesis/stats_utils.py` built and tested against synthetic
fixtures (not the registry), per the user's explicit requirement.**
`mean_ci()` verified against a hand-computed closed-form normal CI.
`paired_bootstrap_ci()` verified with two exact-zero-width discriminating
tests (`b = a + 3` with varying `a`; a constant 10% case) that would fail
if pairing were broken (i.e. if `a` and `b` were resampled independently
instead of by shared index) — both collapsed to exactly the true value,
confirming the pairing logic is correct. 9/9 tests pass.

**Degradation-by-ambient: final CI-backed measurement (replaces the
2026-08-12 preliminary single-run numbers above).**
`scripts/measure_degradation_by_ambient.py`, scope=`reference`
(`station_v0_bogota`'s 100 backfill rows: AFAP+RoundRobin x 5 seeds x
10 days — the user chose this scope over the full 502-row option to save
~52 minutes). Design: writes to a **separate** file,
`results/degradation_by_ambient.csv`, rather than adding a column to
`master_results.csv` — same "don't mix scenario dimensions into the
Phase 2 comparison registry" principle applied to the grid-scope
resolution above. Each row is re-simulated once (per-EV session data isn't
persisted in the registry) and measured under 4 ambient scenarios.
100/100 completed, 0 errors.

Paired bootstrap (10,000 resamples, matched by run_id/`(seed, day)` cell —
not independent-sample stats):

| | calendar-only change vs. 25C default | 95% CI | total (cal+cyc) change | 95% CI |
|---|---|---|---|---|
| Bogota outdoor | -51.75% | [-52.01%, -51.48%] | -26.13% | [-26.50%, -25.76%] |
| Bogota outdoor, +5C charging | -45.12% | [-45.48%, -44.74%] | -24.37% | [-24.87%, -23.87%] |
| Bogota underground | -59.17% | [-59.21%, -59.13%] | -32.49% | [-32.99%, -31.99%] |

Calendar aging is **48.08%** of total degradation under the default
scenario (95% CI [47.53%, 48.62%], n=100) — since cycling is
temperature-independent, this bounds how much of the *total* reported
`battery_degradation` metric can move with ambient scenario, which is why
the "total" column above is roughly half the "calendar-only" column.

Jensen's-gap, measured (not assumed) across all 100 runs: the
mean-temperature point-estimate underestimates the properly session-
integrated calendar degradation by **1.01%** (95% CI [0.97%, 1.06%]) —
tight and consistent with the earlier single-run estimate (1.016%).

**The single-run preliminary numbers from earlier today (-51.77%/-59.29%,
calendar-only) turn out nearly identical to the now-properly-measured
values (-51.75%/-59.17%)** — reassuring for stability, but the CI-backed
numbers above are now the citable ones; the single-run figures are
superseded, not deleted (kept above for the record of how this was built
incrementally).

**`f09_degradation_by_ambient` built.** `ev2gym_thesis/figures.py`
(`ALGORITHM_STYLE` dict -- AFAP red/circle, Round Robin blue/square, fixed
across all future figures; `write_caption()`, generated never hand-written)
and `scripts/make_figures.py`. Three-panel grouped bar chart (total /
calendar-only / cycling-only), x-axis = ambient scenario, bars = algorithm,
mean +/- 95% CI from `mean_ci()`. Output: `figures/f09_degradation_by_ambient.png`
(300 dpi), `.pdf` (vector), `.caption.md` (states runs behind it = 100,
configs, algorithms, git commit, generation timestamp). Visual check
confirms the measured numbers: calendar-only bars drop sharply across
Bogota scenarios, cycling-only bars stay flat (confirming no temperature
dependence, as expected from the code inspection), total sits at roughly
half the calendar-only drop. Only this one figure implemented so far.

**Status:** registry complete and verified (503 rows), degradation
calibration measured with confidence intervals (reference scope) and
plotted, grid-scope conflict resolved and both planning documents
corrected (diff shown, not yet committed), Gurobi policy implemented,
vocabulary checker passing, other-cities ambient data added with gaps
flagged. Not yet done: remaining Deliverable 4 figures (f01-f08), algorithm
chapter (Deliverable 5), hand-back document (Deliverable 7), the
`PROJECT_ROADMAP.md`/`CLAUDE.md` diff commit. Nothing
committed yet.

## 2026-08-05 — Week 1 baseline reproduction attempt (branch `semana-1`)

**Environment setup.** `pip install -e .` succeeded on a fresh Python 3.11.9
install, but did not pull in `pandapower`, `numba`, or `multicopula`
(consistent with prior notes in `CLAUDE.md`). Installed those three
explicitly; `gymnasium` and `gurobipy` were pulled automatically as
dependencies of `ev2gym`. No changes were made to `ev2gym/models/` or
`ev2gym/rl_agent/`.

**Ran:** `experiments/phase1_baseline/run_baseline.py`, which loads
`experiments/phase1_baseline/configs/station_v0_bogota.yaml` and runs a
96-step (15-min) day with `ChargeAsFastAsPossible` and `RoundRobin`.

**Assumption made (config's `random_day: True` contradicts a "fixed date"):**
`station_v0_bogota.yaml` has `random_day: True`. Reading
`ev2gym/models/ev2gym_env.py` (lines ~130-140) confirms that with
`random_day: True`, the simulated calendar date is drawn from
`random.randint()` seeded by whatever `seed` is passed to the `EV2Gym`
constructor — there is no fixed date sitting in this config file. Since no
seed was recorded anywhere in this repo (git history, `results/`, or
`thesis_docs/`) for whatever run originally produced the reference values
below, that prior result cannot be reproduced from this config alone.
**Assumption:** to give AFAP and Round Robin a fair, identical-day comparison
without editing the YAML, both runs were driven with the same explicit
seed (`SEED = 42` in `run_baseline.py`), landing on simulated date
2022-04-25. This should be revisited (e.g., set `random_day: False` with an
explicit `year/month/day`, or standardize on a documented seed) before this
becomes the reported Week-1 baseline in the thesis.

**Results obtained (seed=42, sim_date=2022-04-25):**

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 92 | 92 |
| total_profits | -280.52 | -274.35 |
| total_energy_charged (kWh) | 1260.38 | 1259.74 |
| average_user_satisfaction | 1.0 | 0.99995 |
| total_transformer_overload (kWh) | 0.0 | 0.0 |

**Comparison against previously reported reference values** (AFAP: 11 EVs,
profit -56.85, 206.48 kWh, 100% satisfaction, 42.17 kWh overload; Round
Robin: 13 EVs, profit -54.69, 191.18 kWh, 100% satisfaction, 0.00 kWh
overload): **does not match**, not even approximately — EVs served is ~7-8x
higher and energy charged ~6x higher than the reference.

**Root cause not yet confirmed, but the most likely explanation:**
`station_v0_bogota.yaml` is still an untouched copy of
`ev2gym/example_config_files/V2Ggrid.yaml` — `number_of_charging_stations:
150`, `spawn_multiplier: 5`, IEEE 34-bus grid, `v2g_enabled: True`. This is
a large synthetic multi-station grid scenario, not yet edited down to the
"representative single Bogotá public station" the roadmap's Week 1 task
calls for (`PROJECT_ROADMAP.md`, Week 1 checklist, still unchecked). A
scenario with 150 charging points and a 5x spawn multiplier plausibly
serving ~90 EVs/day is internally consistent; it is very unlikely to be the
same scenario that produced the reference 11-13 EVs/day. This is a
plausible explanation, not a confirmed one — the reference run's exact
config was not available to diff against.

**Status:** environment reproduced and smoke-tested; baseline run executed
successfully end-to-end; numeric results **do not match** the previously
reported reference values and should not be treated as validated until (a)
`station_v0_bogota.yaml` is actually edited per the Week 1 checklist item
("pick the representative station type... number_of_charging_stations...")
and (b) a fixed seed/date convention is agreed and recorded. Flagging for
user review before proceeding to Week 2.

---

## 2026-08-05 — Week 1 config fix: single-station sizing (branch `semana-1`)

Following the diagnosis above, `station_v0_bogota.yaml` was edited from the
unedited `V2Ggrid.yaml` copy to a small, single-station scenario. All values
below were specified by the user as settled decisions, not derived by
Claude Code this session:

| key | old (V2Ggrid.yaml copy) | new |
|---|---|---|
| `scenario` | public | public (unchanged) |
| `simulate_grid` | True | **False** |
| `number_of_charging_stations` | 150 | **8** |
| `number_of_transformers` | -1 | **1** |
| `transformer.max_power` | 200 kW | **100 kW** |
| `v2g_enabled` | True | **False** |
| `heterogeneous_ev_specs` | False | False (unchanged) |
| `ev.max_ac_charge_power` | 22 kW | **50 kW** |
| `ev.max_dc_charge_power` | 50 kW | 50 kW (unchanged, now equal to max_ac) |
| `charging_station.max_charge_current` | 32 A | **72 A** (~50 kW @ 400V/3-phase) |
| `spawn_multiplier` | 5 | **30** |
| `random_day` | True | **False** |
| `year/month/day` | 2022-01-17 | 2022-01-17 (unchanged, now actually used) |

**Verified against `ev2gym/utilities/loaders.py` before writing:** every key
above is read by the loader (`number_of_transformers`, `transformer.max_power`
in `load_transformers`; `v2g_enabled`, `charging_station.max_charge_current`
in `load_ev_charger_profiles`; `spawn_multiplier` in `EV_spawner`;
`random_day`/`year`/`month`/`day` in `EV2Gym.__init__`).

**`number_of_transformers: -1` bug, confirmed:** with `simulate_grid: False`,
`load_grid()` builds `cs_transformers` directly from
`env.number_of_transformers` via `np.arange(env.number_of_transformers)`.
`np.arange(-1)` returns an empty array, which would leave charging stations
unassigned to any transformer. This only went unnoticed previously because
`simulate_grid: True` overwrites `number_of_transformers` from the grid
topology before it's used. Setting it to `1` avoids this. (This matches a
comment already present in `ev2gym/example_config_files/PublicPST.yaml`:
"if simulate_grid is True then this value is overwritten by the topology
file".)

**`max_ac_charge_power` == `max_dc_charge_power` requirement:** requested by
the user as a settled value. Reading `ev2gym/models/ev.py` and
`ev2gym/utilities/utils.py`, no code path was found in the current codebase
that would raise a `ZeroDivisionError` from these two values differing, and
no such note exists in the current `CLAUDE.md`. Applying the requested equal
values anyway (50/50 kW) since it is harmless and doesn't contradict
anything observed; flagging this for the record since it could not be
independently verified.

**`simulation_days: weekdays` note:** with `random_day: False`,
`ev2gym_env.py` never reaches the `simulation_days` weekday/weekend check —
that branch only executes when `random_day: True`. The key is harmless to
leave in the config but currently has no effect; 2022-01-17 happens to be a
Monday anyway.

**Re-ran** `experiments/phase1_baseline/run_baseline.py` (SEED=42, unchanged)
against the corrected config, sim_date fixed at 2022-01-17 05:00 (from the
config itself now, not from the seed).

**Results obtained:**

| metric | AFAP | Round Robin |
|---|---|---|
| total_ev_served | 14 | 14 |
| total_profits | -56.92 | -49.74 |
| total_energy_charged (kWh) | 240.93 | 240.81 |
| average_user_satisfaction | 1.0 | 1.0 |
| total_transformer_overload (kWh) | 0.132 | 0.0 |

**Sanity check:** 14 EVs/day for 8 stations at spawn_multiplier 30 is within
the expected ~10-15 ballpark — plausible order of magnitude, unlike the
previous 92 EVs/day run.

**Qualitative pattern now present:** AFAP produces a small but real
transformer overload (0.132 kWh) that Round Robin's power-setpoint tracking
reduces to exactly 0.0 kWh — the expected qualitative relationship between
an unmanaged and a managed charging strategy. Exact magnitudes are not
expected to match the original reference values (11/13 EVs, 42.17/0.00 kWh
overload) since this run uses a different random seed/EV-arrival draw than
whatever produced that reference; only the qualitative pattern (AFAP
overloads, RR doesn't) and the general order of magnitude are being used as
the validation criteria here.

**Status:** config now reflects a plausible single-station scenario; results
are in the right ballpark and show the expected qualitative
AFAP-vs-RoundRobin pattern. Treating this as the working Week 1 baseline
pending user confirmation. See `thesis_docs/chapters/01_baseline.md` for the
station description write-up.
