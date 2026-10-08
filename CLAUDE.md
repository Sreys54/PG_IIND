# CLAUDE.md — Project Instructions for Claude Code

> Place this file at the **root of your forked repository**
> (`EV2Gym-colombia-cpo/CLAUDE.md`). Claude Code automatically reads it at the
> start of every session in this repo, so you don't need to re-explain the
> project each time — this is what keeps your credit usage low.

## Project Identity

This is a **university thesis (Industrial Engineering, Universidad de los
Andes)** repository, forked from `StavrosOrf/EV2Gym`
(https://github.com/StavrosOrf/EV2Gym), a Gym-compatible EV smart-charging
simulator. The goal is **not** to modify the core EV2Gym library, but to:

1. Configure and run realistic Colombian EV-charging-station scenarios on
   top of EV2Gym's existing models (`ev2gym/models/`).
2. Implement/compare charging control algorithms (heuristic, MPC/optimal,
   RL, physics-informed RL) using EV2Gym's existing `baselines/` and
   `rl_agent/` interfaces wherever possible — prefer extension over
   rewriting.
3. Produce reproducible experiment artifacts (config files, metrics CSVs,
   plots) and Markdown documentation chapters that will be assembled into a
   Word thesis document later.

Full plan lives in `PROJECT_ROADMAP.md` at repo root (8-week compressed
version) — **read it** before starting work in a new phase if you (Claude)
are unsure what's next.

**Correction, 2026-08-19 (Week 4): the list below asserted files that did
not exist in this repo** — discovered when Week 4's PI-TD3 work tried to
read `pi_td3_paper.pdf` and found `thesis_docs/references/` held only a
`.docx` proposal file. Costed a round trip (stopped rather than guess at
Algorithm 1/Eq. 14 from memory, correctly, but the gap itself shouldn't
have existed). Real, current state — see
`thesis_docs/references/REFERENCES.md` for full citations, DOIs,
acquisition status, and (for regulatory documents) retrieval dates/URLs;
this list is not the source of truth any more, that file is:
- `ev2gym_paper.pdf`, `pi_td3_paper.pdf` — **in repo**, fetched 2026-08-19
  from arXiv (2404.01849 / 2510.12335v2).
- Colombian regulatory PDFs — **in repo**, fetched 2026-08-19 (Ley
  1964/2019, RETIE Res. 40117/2024, RETIE Libro 3; the two CREG
  resolutions, 40223/2021 and 40123/2024, are HTML, not PDF — no
  HTML-to-PDF renderer was available, declared as a limitation in
  `REFERENCES.md` rather than worked around silently). Weeks 6-7 material,
  not read into Week 4.
- `microgrid_chapter.pdf` (Mahmoud 2017, Ch. 1) — **pending institutional
  access** (paywalled, Uniandes library/document delivery). Weeks 6-7.
- Zandrazavi et al. (2022), Energy 241 — **pending from advisor** (she is
  the paper's third author). Weeks 6-7, required reading before the Week 6
  IEEE 34-bus phase specifically (unbalanced-network treatment), plus a
  required literature-review positioning paragraph once acquired.

Original list, kept for the historical record of what was assumed present
(the reasoning below for *why* each source matters is still accurate,
only the "already in repo" assumption was wrong):
- `ev2gym_paper.pdf` — simulator paper (models, baseline algorithms, metrics
  in Table V).
- `pi_td3_paper.pdf` — physics-informed RL for voltage-constrained charging
  (Algorithm 1, reward Eq. 14, evaluation metrics Table II).
- `microgrid_chapter.pdf` — background on microgrid control hierarchy
  (primary/secondary/tertiary control, MGCC) — used for the infrastructure
  guidelines chapter (Objective 4), not for direct code implementation.
- Colombian regulatory PDFs (Ley 1964/2019, RETIE Res. 40117/2024,
  Res. 40223/2021, Res. 40123/2024) — used to justify constraints
  (±5% voltage band, OCPP + CCS Combo 1 [CORRECTED 2026-09-08, Week 5 Part
  A — Res. 40223/2021 Art. 4 mandates at least one Tipo 1 (AC) and at
  least one CCS Combo 1 (DC) connector as the *minimum*; it does not
  establish, mention, or exclude CCS Combo 2. The original text here said
  "CCS Combo 2" and was wrong, not merely uncited — verified directly
  against the resolution's stored text
  (`thesis_docs/references/regulatory/res_40223_2021.html`), not
  paraphrased from memory. This project's `station_v0_bogota` config still
  assumes CCS2-only, on market-practice grounds (Enel Colombia's own
  network uses CCS1/CCS2/GBT) — see `01_baseline.md` §1.1(a) — not on
  regulatory-floor grounds; a DC station equipped with CCS2 only would NOT
  by itself satisfy Art. 4's minimum, which requires Combo 1. The
  requirement binds only stations installed from 12 months after the
  resolution's entry into force, per Art. 4 Paragrafo 3.] interoperability,
  min. 5 public stations per category-especial city).

## Language & Output Conventions

- **All code, comments, docstrings, config files, commit messages, and
  generated documentation must be in English.** This is a formal academic
  deliverable.
- Config files go in `experiments/<phase>/configs/*.yaml`, following
  EV2Gym's existing YAML schema (see any file under
  `ev2gym/example_config_files/` as the canonical reference — do not invent
  new top-level keys unless the library actually supports them; check
  `ev2gym/utilities/loaders.py` if unsure whether a key is consumed).
- Results (metrics) go in `experiments/<phase>/results/*.csv`. Plots go in
  `experiments/<phase>/results/figures/*.png`.
- Thesis-facing documentation goes in `thesis_docs/chapters/*.md`, numbered
  (`00_lab_log.md`, `01_baseline.md`, ...). Write these as clear academic
  prose, not chat-style explanations.
- Every experiment run must be reproducible from its config file alone —
  never hardcode paths, seeds, or scenario parameters inline in a way that
  isn't also saved to the YAML/JSON used for that run.

## Working Rules

1. **Never modify files inside the original `ev2gym/` package internals**
   (`ev2gym/models/*.py`, `ev2gym/rl_agent/*.py`) unless a specific bug or
   missing feature genuinely requires it — and if so, isolate the change,
   explain why in the commit message, and note it in
   `docs/thesis/00_lab_log.md` since it affects reproducibility claims
   against the upstream library. Prefer writing new files (custom reward
   functions, custom state functions, custom heuristics) that import and
   extend the library, following the pattern shown in the EV2Gym README's
   "Reinforcement Learning" section.
2. **Before running anything that trains an RL agent**, confirm the
   expected wall-clock time with me (the user) — PI-TD3/TD3 training took
   5–48 hours in the original paper on a HPC cluster; on a laptop this
   needs to be scoped down (shorter horizons, fewer scenarios, smaller
   networks) and I need to explicitly agree to the reduced scope before
   you proceed, since it changes what claims we can make in the thesis.
3. **Always report the actual metrics obtained**, never estimate or
   extrapolate what a metric "should" look like based on the papers'
   numbers — those are a different network/scenario/dataset. If a run
   fails or produces an unexpected result, report the raw output and flag
   it, don't silently adjust or omit it.
   Confirmed stats keys available from `env.step()`: `total_ev_served,
   total_profits, total_energy_charged, total_energy_discharged,
   average_user_satisfaction, power_tracker_violation, tracking_error,
   energy_tracking_error, energy_user_satisfaction,
   std_energy_user_satisfaction, min_energy_user_satisfaction,
   total_steps_min_emergency_battery_capacity_violation,
   total_transformer_overload, battery_degradation,
   battery_degradation_calendar, battery_degradation_cycling,
   total_reward, saved_grid_energy, voltage_violation,
   voltage_violation_counter, voltage_violation_counter_per_step,
   action_mask`.
4. **Git discipline, corrected 2026-08-20 (standing rule, supersedes
   anything below or in any earlier week's brief that says otherwise):
   Claude Code never runs `git commit`, `git merge`, `git tag`, or
   `git push`.** The user does all of those manually. Work on the
   `semana-N` branch matching the current week (e.g. `semana-1`,
   `semana-2`, ... `semana-8` — no `dev` branch, no `feature/*` naming,
   working solo) and leave the working tree in a state the user can review
   and commit themselves. When a chunk of work is done, provide `git status
   --short` plus a **proposed commit plan** (how to split the work into
   logical commits, with the message for each, English,
   `feat:`/`fix:`/`exp:`/`docs:` prefixes) — the user runs the actual
   commands. Also flag anything that should be `.gitignore`d and isn't
   (model checkpoints, replay files, Gurobi `.log`/`.lp`/`.mps` dumps), and
   anything that IS gitignored but shouldn't be (a stale or overly broad
   pattern silently swallowing real deliverables — check with
   `git check-ignore -v` before assuming a missing file is simply "not
   generated yet"). The user tags milestones and merges to `main`
   themselves once they confirm a week's checklist is done.
5. **When a task is ambiguous** (e.g. "which real station do we model"),
   propose a concrete, clearly-labeled assumption and proceed — don't block
   on it — but always write the assumption down in the relevant
   `docs/thesis/*.md` file so it can be challenged/revised later.
6. **Gurobi**: assume an academic license is available via university email;
   if a Gurobi call fails due to licensing, tell me immediately rather than
   silently switching to a different solver, since MPC/optimal baselines
   are a required comparison point.
7. **Excel exports (added 2026-09-09):** any `.xlsx` generated in this
   project — a human-readable export of a results CSV, or any other
   spreadsheet meant for me to read by eye — must go through
   `ev2gym_thesis/xlsx_export.py::export_formatted_xlsx`, never a plain
   `df.to_excel()`. That function enforces:
   - Every column header renamed to a detailed, unit-bearing label (e.g.
     `"Gross Margin, Revenue minus Cost (COP per simulated day)"`, never
     a bare `gross_margin_cop`). If a column's scale is ambiguous or
     inconsistent with a same-sounding column elsewhere in the project
     (this project's own `average_user_satisfaction` is a 0-1 fraction
     while `min_energy_user_satisfaction` is already on a 0-100 scale),
     the label states which scale applies.
   - Thousand-separator number formats matched to the value's type, using
     the constants already defined in `xlsx_export.py`
     (`COP_FORMAT`/`KWH_FORMAT` = `#,##0.00`; `COP_PER_KWH_FORMAT` =
     `#,##0.0000` for exact reference-tariff constants; `COUNT_FORMAT` =
     `#,##0`; `PCT_ALREADY_SCALED_FORMAT` = a literal `"%"` appended
     without re-multiplying, for a value already on a 0-100 scale;
     `PCT_FRACTION_FORMAT` = Excel's native `0.00%`, for a true 0-1
     fraction) — add a new constant there rather than inventing a
     one-off format string in a calling script.
   - Bold, frozen header row; column widths sized so headers aren't
     truncated.
   - A hard check that every column has an explicit label (raises if one
     is missing) — do not work around this check.

## Current Phase

<!-- Update this section yourself at the start of each work session so
     Claude Code always knows where you are without you re-explaining. -->

- **Timeline:** compressed to 8 weeks (see `PROJECT_ROADMAP.md`).
- **Branch naming:** `semana-1` through `semana-8`, one per week, merged
  into `main` at the end of each week (no `dev`, no `feature/*`).
- **Active phase:** Week 3 — RL baseline vanilla (TD3) on the reference station.
- **Active branch:** `semana-3`, branched from `main` at commit `0b098f5`
  (2026-08-12). `semana-2` and `main` point to this same commit — Week 2 is
  merged, not a divergent branch to reconcile.
- **Week 2: CLOSED (2026-08-12).** All 7 deliverables complete and committed
  (`0b098f5`, "complete Deliverables 1-7 and the deferred-Gurobi policy");
  merged to `main`. This includes the registry backfill and the multi-seed
  Bogota degradation re-measurement that were previously the open item —
  both done, not pending. Full account in `thesis_docs/chapters/00_lab_log.md`
  (2026-08-12 entry) and `thesis_docs/chapters/02_model_validation.md`.
- **Last milestone tag:** `v0.0-env-ready`
- **Environment status:** installed and smoke-tested. `pip install -e .`
  alone is NOT enough — also needed `pandapower`, `numba`, `multicopula`
  (missing from a strict `requirements.txt` install; `gurobipy` is listed
  but still needs an actual license activated).
- **Environment reproduced locally (2026-08-05):** `pip install -e .` +
  `pandapower`, `numba`, `multicopula` installed on this machine (Python
  3.11.9, Windows). `ev2gym` + `ev2gym.baselines.heuristics` import cleanly;
  no changes made to `ev2gym/models/` or `ev2gym/rl_agent/`.
- **Week 1 baseline: CONFIRMED (2026-08-11).** `station_v0_bogota.yaml`
  (8 charging stations, 100 kW transformer, `simulate_grid: False`,
  `v2g_enabled: False`, `spawn_multiplier: 30`, `random_day: False` fixed
  at 2022-01-17) is the validated Week 1 reference config. Reference
  results (seed=42, from `experiments/phase1_baseline/results/baseline_afap.csv`
  / `baseline_roundrobin.csv`): AFAP = 14 EVs served / 240.93 kWh charged /
  0.132 kWh transformer overload; Round Robin = 14 EVs served / 240.81 kWh
  charged / 0.0 kWh overload. Oversubscription ratio (installed 400 kW / 100
  kW transformer) = 4:1. Do not re-run or overwrite these files. Full
  write-up in `thesis_docs/chapters/01_baseline.md`.
- **`number_of_charging_stations = 8` now grounded in data (2026-08-11):**
  Enel X Colombia's public charge-point inventory for Bogota (67 chargers /
  21 sites, consulted 2026-08-11) shows an 8-port hub (CC Retiro) exists in
  practice, though at lower AC power than our 50 kW DC-capable config
  assumes — see `thesis_docs/chapters/01_baseline.md` §1.1 for the citation
  and declared limitations (hardware mismatch; Enel X is a lower bound, not
  a census of all Bogota public charging).
- **Open item, unconfirmed:** the requirement that `ev.max_ac_charge_power`
  equal `ev.max_dc_charge_power` (to avoid a claimed `ZeroDivisionError`)
  could not be verified against the current codebase (`ev2gym/models/ev.py`,
  `ev2gym/utilities/utils.py`) — applied anyway since it's harmless, but
  flagging that this specific failure mode is not confirmed to exist.
- **Grid-scope note (resolved 2026-08-12):** `simulate_grid: False` (single
  station, own local transformer) is used through Objectives 1-3, weeks
  1-3. `simulate_grid: True` + the IEEE 34-bus feeder is reserved for
  Objectives 4-5 — NOT Week 2. Week 2's "model validation" means
  documenting what's realistic vs. simplified in the station-and-local-
  transformer model (`thesis_docs/chapters/02_model_validation.md`), not
  running the feeder. One de-risking smoke test only
  (`notes="pipeline_smoke_test_grid"`, excluded from all figures/tables) is
  the sole exception. See `PROJECT_ROADMAP.md`'s matching grid-scope note.
- **Week 3 preflight: DONE (2026-08-12).** Confirmed `semana-2`/`main` merge
  state; `results/master_results.csv` has 503 rows, `algorithm_family` is
  `heuristic`-only so far (no RL rows yet, `f08` correctly inert);
  `stable-baselines3` (2.9.0) installed and added to `requirements.txt`
  alongside `torch>=2.8`; confirmed `EV2Gym` is fully Gymnasium-API-compliant
  (`reset()->(obs,{})`, `step()->(obs,r,terminated,truncated,info)`, no SB3
  shim needed) and that `reward_function`/`state_function` are plain
  constructor kwargs defaulting to `SquaredTrackingErrorReward`/`PublicPST`.
- **Week 3, Entregables 1-4, 8, 9 (partial): DONE (2026-08-12).**
  `TRAIN_SEEDS` added to `eval_protocol.py`; `ev2gym_thesis/rl/` package
  built (`env_factory.py`, `config_rl.py`, `callbacks.py`, `eval_utils.py`);
  reward (`SqTrError_TrPenalty_UserIncentives`) and state (`PublicPST`)
  choice justified in `thesis_docs/chapters/03_rl_baseline.md`, including
  the reward-vs-evaluation-metric misalignment and the `total_reward`
  cross-family comparability guardrail in `ev2gym_thesis/figures.py`; the
  Week 4 perfect-information-reference design note (Entregable 8) written;
  8 pre-training tests added and passing
  (`ev2gym_thesis/tests/test_rl_infrastructure.py`). Time calibration run
  (Entregable 4) measured 18.09 steps/s; **user confirmed a training budget
  of `TOTAL_TIMESTEPS = 60_000` per training seed** (~55.3 min/seed, ~2.8h
  for all 3 `TRAIN_SEEDS`) — see `ev2gym_thesis/rl/config_rl.py` and
  `00_lab_log.md`'s Entregable 4 entry for the full table and the declared
  scope-reduction comparison against the papers' HPC budgets.
- **Week 3, Entregables 5-7: DONE (2026-08-13).** All 3 `TRAIN_SEEDS`
  trained at the confirmed 60,000-timestep budget (2.79h total wall-clock,
  matching the calibration estimate; weak-but-consistent learning signal
  across all 3 seeds, not clean convergence — declared, not hidden). All 3
  checkpoints + a random-policy negative control evaluated on the same
  50-cell grid (`scripts/evaluate_rl.py --execute`, 200 runs appended to
  `results/master_results.csv`). Headline: TD3 matches Round Robin's
  near-elimination of transformer overload (vs. AFAP's 5.33 kWh and the
  random control's **12.74 kWh — worse than AFAP**, confirming this is a
  real learned behavior), at a real cost in `min_energy_user_satisfaction`
  and `total_ev_served`, with substantial cross-training-seed dispersion.
  Paired bootstrap + cross-seed dispersion in
  `results/rl_vs_baseline_bootstrap.csv` /
  `results/rl_train_seed_dispersion.csv`. Visual QA found and fixed 5 real
  bugs: TD3 timeseries were silently zeroed by SB3's `DummyVecEnv`
  auto-reset (scalar registry metrics were unaffected), plus 4
  figure-legibility bugs from `make_figures.py` not scaling past 2
  algorithms. Full account in `00_lab_log.md`'s 2026-08-13 entry and
  `thesis_docs/chapters/03_rl_baseline.md`.
- **Next concrete task (Week 3):** Entregable 10 — Week 3 hand-back
  document (`scripts/make_week3_handback.py`) and
  `Progress_Log_Thesis_Project.docx` extension. This is the last remaining
  Week 3 deliverable; no merge to `main` or tag until the user confirms.

**Correction, 2026-08-19: the "Current Phase" section above is stale —
kept for the historical record, not rewritten in place.** Real current
state:
- **Week 3 is fully closed**, including a correction found during Week 4
  preflight: `scripts/evaluate_rl.py`'s evaluation steppers had an unseeded
  `env.reset()` bug corrupting all 200 TD3/RandomPolicy evaluation rows.
  Fixed on `semana-3` (commit `88c767e`, "Fix Week 3 evaluation-scenario
  bug..."), re-evaluated, `Week3_...docx` regenerated with a correction
  section. `main`/`semana-3`/`semana-4` all point to that commit.
- **Correction, 2026-08-20: Week 4 is CLOSED, not "in progress."** All 14
  Entregables from the closeout brief are done: oracle (both variants),
  falsified PI-TD3 adaptation (reported as a finding), `TD3_TrackingOnly`
  reward ablation trained (3 seeds, 168.43 min total) and evaluated (150
  rows), analysis (`scripts/analyze_week4_results.py`, 5 CSVs), figures
  (all 11 incl. new f10/f11, 2 real bugs found by visual QA and fixed —
  see `00_lab_log.md`'s 2026-08-20 entry), tests (16/16 passing, incl.
  `TestRegistryCount` confirming the main-grid registry is exactly 550
  rows = 11 algorithms x 50 cells), chapter S4.8-S4.10 filled with real
  numbers, both hand-back documents generated
  (`Week4_Parameter_Method_and_Implementation_Justification.docx` and the
  external `Progress_Log_Thesis_Project.docx`'s new "2.3. Week 4" section).
  **Per explicit user instruction, no commits/merges/tags were made by
  Claude for this work** — everything above is uncommitted on `semana-4`,
  left for the user to review and commit/push themselves. Active branch:
  `semana-4`, branched from the corrected `semana-3`/`main` tip.
- The oracle (`Optimal_Oracle_Tracking` + `Optimal_Oracle_Balanced`,
  50 cells each, `ev2gym_thesis/oracle/`) is complete and verified.
- **No arm named `PI_TD3`/`PI-TD3` exists in this project.** Two
  reward-only physics-adaptations were built and falsified before training
  (see `thesis_docs/chapters/04_oracle_and_pitd3.md` S4.3 for the full
  mechanism). Part B's actual second training arm is `TD3_TrackingOnly` (a
  reward ablation vs. Week 3's `SqTrError_TrPenalty_UserIncentives`
  choice) — retroactively validates that choice: the composite reward
  beats tracking-only on tracking error itself, not just overload/
  satisfaction. A faithful PI-TD3 port is a conditional stretch goal for
  Week 6 (`PROJECT_ROADMAP.md`'s Week 6 entry), not a commitment.
- **Open item carried into Week 5, not resolved this week:** the
  proposal's "<15% energy error" success target has no operationalized
  definition against a specific registry metric yet — flag before the
  final comparison is written up.
- Full session account in `thesis_docs/chapters/00_lab_log.md`'s
  2026-08-18/19/20 entries.

**Correction, 2026-09-09: everything above this line is stale (still says
"Active phase: Week 3") — kept for the historical record, not rewritten
in place.** Real current state:
- **Active phase: Week 5 — Colombian price re-basing (Part A) and full
  algorithm comparison including the MPC arm (Part B). Both complete.**
  Active branch: `semana-5`, branched from the corrected `semana-4`/`main`
  tip. **Not merged to `main`, not tagged** — per standing git discipline,
  the user tags `v0.3-algorithms-compared` and merges themselves once they
  confirm the week's checklist is done.
- **Colombian price constants (standing facts, so a future session cannot
  silently reintroduce ENTSO-E prices):** retail tariff
  `RETAIL_TARIFF_COP_PER_KWH = 1450.0` (Enel Colombia, August 2025, a
  single published point — not a time series); energy purchase cost
  `ENERGY_PURCHASE_COST_COP_PER_KWH = 865.7615` (Enel Colombia's regulated
  tariff sheet, Nivel de Tension 2, with contribution, August 2026 — the
  most recently published month at the time, not an average). Both in
  `ev2gym_thesis/prices/colombia.py`. `results/economics_cop.csv` is the
  source of truth for revenue/cost/margin from Week 5 onward —
  EV2Gym's own `total_profits` registry column is NOT a profit/revenue
  figure (it is a negated ENTSO-E-priced purchase cost; see
  `ev2gym_thesis/registry.py`'s `total_profits_semantics` doc comment) and
  must not be read as one.
- **The evaluation grid was rebuilt.** The original 5-seed x 10-`EVAL_DAYS`
  grid was found to be non-independent (EV2Gym's arrival distribution
  depends on weekday-vs-weekend only, not the specific date) and, separately,
  `ev2gym/utilities/utils.py::generate_power_setpoints` had a live ENTSO-E
  price dependency inside the control layer (fixed at the source, isolated
  change, see that function's own dated comment). Current grid:
  `ev2gym_thesis/eval_protocol.py`'s `SEEDS = range(0, 50)`,
  `EVAL_DAYS = [(2022,1,17), (2022,3,5)]` (one weekday, one weekend). The
  registry (`results/master_results.csv`) now has an `analysis_row`
  column — **only `analysis_row=True` rows are statistically valid**
  (1,300 rows = 13 algorithms x 100 cells); every pre-existing row is
  `superseded=True`, kept as provenance, never used in a current figure or
  table. `ev2gym_thesis/stats_utils.py::paired_cluster_bootstrap_ci`
  (resamples the scenario seed, not the row) is the current bootstrap for
  any cross-cell comparison — the older `paired_bootstrap_ci` still exists
  but understates uncertainty on this project's clustered evaluation
  design.
- **Two new algorithm arms:** `MPC_TrackingG2V` and `MPC_EnergyMaxG2V`
  (`ev2gym_thesis/mpc/`), both wrapping unmodified `ev2gym/baselines/mpc/`
  classes. Both are non-causal (know connected-EV departure times and
  near-horizon arrivals no real operator has) — never described as
  deployable without that caveat.
- **Recommended strategy for Objective 4, on evidence through Week 5:
  Round Robin** — the best fully causal, deployable arm on every declared
  axis at this station's scale. `MPC_TrackingG2V`/`MPC_EnergyMaxG2V` and
  both oracle variants outperform it but are not causal; their gap to
  Round Robin is framed as a value-of-information bound (e.g. what a
  declared-departure app feature could be worth), not a competing
  recommendation.
- Full session account in `thesis_docs/chapters/00_lab_log.md`'s
  2026-09-08/09 entries and `thesis_docs/chapters/05_algorithm_comparison.md`.

**Update, 2026-09-28: Week 6 Part 0 (extended RL training) — branch
`semana-6`, from `main` at `23468f3`. Not merged, not tagged.**
- **FINAL RL MODEL (ADOPTED by the user, 2026-10-05; fixed for the rest of
  the thesis, never substitute another seed or checkpoint):
  `TD3_vanilla` extended, training seed 102, primary checkpoint at 850,000
  steps.**
  - Model:
    `experiments/phase2_algorithms/models/TD3_vanilla_extended_ts102/checkpoints/td3_vanilla_extended_ts102_850000_steps.zip`
  - VecNormalize:
    `experiments/phase2_algorithms/models/TD3_vanilla_extended_ts102/checkpoints/td3_vanilla_extended_ts102_850000_steps_vecnormalize.pkl`
    (load frozen: `training=False`, `norm_reward=False`)
  - Registry name on the non-grid grid: `TD3_vanilla_extended_ts102`.
  - Accepted trade-off: test tracking error 41,195, against 32,575 at its
    own 60k checkpoint.
  - Original Part 0 record, kept for history. The pre-registered rule output
    was the same checkpoint, **`TD3_vanilla_extended_ts102`**, checkpoint
    at 850,000 steps,
    `experiments/phase2_algorithms/models/TD3_vanilla_extended_ts102/checkpoints/td3_vanilla_extended_ts102_850000_steps.zip`
    (+ `_vecnormalize.pkl` next to it). Pinned in
    `results/week6_part0_final_model_selection.json` and
    `ev2gym_thesis/tests/test_final_rl_model.py`.
  - Verdict (S5.11): extended training **degraded** the pre-registered
    criterion. Test-grid tracking error is +10,701 (+33%) against the
    environment-matched new-run 60k checkpoints (`TD3_vanilla_new60k_ts*`;
    cluster bootstrap, n_clusters = 50, CI excludes zero). Overload is
    unchanged within the CI, and satisfaction and `ENS_rel` improved. RL was
    not budget-limited, and **Round Robin remains the recommended strategy**.
    Because the rule's checkpoint is worse on its own criterion than the 60k
    checkpoints, the user chooses which RL model is carried forward.
  - Whichever model the user adopts, **the Week 6 grid-enabled brief uses it
    instead of the Week 5 `TD3_vanilla_ts*` checkpoints**, which were trained
    before the `generate_power_setpoints` fix and evaluated after it (declared
    limitation, S5.11).
- New registry arms (900 rows, `analysis_row=True`; budget, step and rule in
  `notes`): `TD3_vanilla_extended_ts*` (primary), `TD3_vanilla_extended_last_ts*`,
  `TD3_vanilla_new60k_ts*`. Analysis-row total: 2,200.
- Standing implementation facts:
  - `ev2gym_thesis/rl/price_data_cache.py` is output-identical (pinned test)
    and ~6× faster for training.
  - Use one torch thread per process: the thread count changes the numerics.
  - Parallel processes need per-process day-config dirs
    (`extended_training.day_config_dirs_for`).
  - This laptop idles to sleep after 300 s on AC, and
    `scripts/train_td3_extended.py` requests keep-awake.
  - `FIGURE_SPECS` and `scripts/make_week5_handback.py` do not exist: figures
    are `make_figures.py` functions (`--only f12,f13`), and handbacks are
    `.md` rendered by `scripts/render_docx.py`.

**Update, 2026-10-06: Week 7, Objectives 4 and 5 (final practical phase).
Branch `semana-7`, from `main` at `ebf3634`. Uncommitted, untagged: the
user commits and tags `v0.4-infra-guidelines` and `v0.5-replicability`.**
Everything above about the "current phase" is history. The current state
is the following.
- **Phase:** the practical work is complete. Only the final thesis document
  remains. The night's decision log is `thesis_docs/overnight_report.md`,
  and the deliverables index is `thesis_docs/DELIVERABLES_INDEX.md`.
- **Final RL model (unchanged, author's decision):** `TD3_vanilla` extended,
  seed 102, 850,000 steps (see the Week 6 Part 0 block above).
- **Grid vs. non-grid registry rows.** `results/master_results.csv` has a
  last column, `simulate_grid` (added by
  `scripts/migrate_registry_schema_week7.py`; every pre-Week-7 row is
  `False` except the Week 2 smoke test).
  - Grid rows: `config_name` `station_v0_bogota_grid[_spawn1.3|_spawn1.6|_load1.3|_load1.6]`,
    `analysis_row=True`, `simulate_grid=True`, 5 arms × 50 seeds × 2 days
    per setting.
  - Voltage probe rows: `station_v0_bogota_grid_probe_*`,
    `analysis_row=False`.
  - Non-grid statistics: `analysis_row=True` and
    `config_name == 'station_v0_bogota'` (2,200 rows).
  - At the base setting, the grid rows are identical to the non-grid rows
    on every station metric (0.0 difference, asserted).
- **Grid model facts.**
  - `ev2gym_thesis/grid/placement.py` must be enabled in any process that
    builds a grid env. EV2Gym has no station-placement key, and it would
    otherwise spread the 8 stations over 8 buses with 8 × 100 kW
    transformers.
  - The station is on bus 27 (`network_info.thesis_station_bus`).
  - The feeder is EV2Gym's RL-ADN 34-node network, not a validated IEEE
    feeder.
  - The voltage band is 0.95–1.05 p.u. (`ev2gym_thesis/grid/voltage.py::band_check`).
    The feeder is out of band at bus 27 even with the station idle, so
    voltage is reported only as the station's increment over the
    idle-station baseline of the same cell. **Never claim absolute RETIE
    compliance.**
  - Parallel EV2Gym processes need per-process day-config and replay
    directories (`run_week7_grid._per_process_day_configs`).
- **Replicability city: Medellín (EPM).** Constants are in
  `ev2gym_thesis/prices/medellin.py`; the source PDF is
  `thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf`
  (accessed 2026-10-05).
  - Nivel II commercial, with contribution: Punta **923.92** (the base
    cost) and Fuera de Punta 917.58 COP/kWh.
  - CU without contribution: 769.94 / 764.65. Both Week 5 invariants pass.
  - EPM publishes **no** EV charging price, so 1,450 is used only as a
    labelled sensitivity. The intraday spread is 0.69%.
  - The margin ranking is tariff-invariant under a flat price (asserted).
- **Res. 40223 de 2021, Art. 4 (corrected statement, standing):** every
  Level 2 and Level 3 AC station must have at least one Tipo 1 (SAE J1772)
  connector, and every Level 3 DC station at least one CCS Combo 1
  connector. It is a minimum, not an exclusive standard, and it does not
  mention CCS Combo 2. **The project's CCS2-only DC configuration would not
  by itself satisfy it.**
- **Corrections made this phase:**
  - S5.8's 503.9 COP/day (a stale pre-Gate-4 CSV) is now 551.9 COP/day;
  - the fleet battery is **70 kWh**, and documents saying 60 kWh need
    correcting (overnight report, Checkpoint 1a);
  - the S5.11 seed-spread sentence;
  - the S5.11 point-3 interpretation (the training reward *improved*).
- **Consolidated limitations:** `thesis_docs/chapters/08_limitations.md`.

**Update, 2026-10-06: Closure brief (fixes, capacity threshold, Colombian
replicability). Branch `semana-7`. Uncommitted: the user commits.** The
decision log is the closure section at the top of
`thesis_docs/overnight_report.md`. The handback is
`thesis_docs/Closure_Parameter_Method_and_Implementation_Justification.{md,docx}`.

Standing facts (do not lose them):
- **EV2Gym silently drops arrivals at occupied ports**
  (`utils.py::EV_spawner`, lines 490 and 531–537).
  - Satisfaction, `ENS_rel` and EVs served therefore cover **served EVs
    only**.
  - Use **demand not served (DNS)**, from
    `ev2gym_thesis/demand/censoring.py` (post-processing, never a registry
    column). The lower bound is primary.
  - Round Robin DNS at 1.0× is **34.6% [30.8, 38.4]**. The 8 ports bind,
    not the transformer.
  - Never again write that satisfaction "is unchanged" or "met" as a claim
    about the station's users.
- **Capacity thresholds** (`results/closure_c1_breaking_levels.csv`):
  - Round Robin breaks at 0.733× (DNS);
  - AFAP and the final RL model break at 0.5× (P95 peak > 100 kW).
- **What closes the gap is ports** (constant station demand):
  - 10 ports at 0.733× and 12 ports at 1.0× (`results/closure_c2_options.csv`);
  - a larger transformer changes nothing for Round Robin.
- **EV2Gym draws arrivals per port.** More ports at the same
  `spawn_multiplier` also means more demand. Compare port counts with spawn
  × 8/P. `spawn_multiplier` 22 is 0.733×, not 0.75×.
- **Power factor and ratings.** pf 0.894 is derived from CREG 015/2018,
  with a caveat in `thesis_docs/sources/SOURCES_closure.md`. Standard
  ratings come from Enel ET-013. AFAP needs **225 kVA** at either power
  factor.
- **Six categoría especial cities** (CGN workbook, vigencia 2026):
  Bogotá, Medellín, Cali, Barranquilla, Cartagena, Bucaramanga. Their
  tariffs are in `ev2gym_thesis/prices/cities.py`.
  - Air-e (Barranquilla) has a **10.03%** two-band Nivel 2 option.
  - EMCALI's latest retrievable sheet is January 2026.
- **Proposition 7.1** (07 S7.3a). Under a flat tariff, the margin ranking
  equals the energy ranking and the relative cost is ΔE/E_AFAP. The 48/48
  check and the equal 0.47% are its consequences, not findings. It does
  not hold exactly under a two-band tariff.
- **Voltage.**
  - EV2Gym has no feedback from the feeder to the station
    (source-confirmed, `test_closure.TestNoFeederFeedback`).
  - The 34-node feeder is out of band when idle.
  - **node_123 is in band when idle** (`results/closure_feeder_probe_summary.csv`).
    The AFAP and RR voltage runs on it are weekday only, because EV2Gym's
    load generator stalls for 123 buses on the weekend day
    (`scripts/closure_ieee123_voltage.py` docstring).
  - The "37%" is 36.4% [22.3, 47.0] at base only.
- **Registry.** It gained 6,000 closure rows (`notes` contain
  `closure_part=`; `analysis_row=True`, `simulate_grid=False`). The
  non-grid statistics set is still `config_name == 'station_v0_bogota'`
  (2,200 rows).
- **Laptop limits.** At most 2 parallel EV2Gym workers. Three workers plus
  the test suite overloaded the machine.

**Update, 2026-10-07: Final capacity brief (DC session duration and growth
scenario). Branch `semana-7`, uncommitted: the user commits.** The decision
log is the dwell section at the top of `thesis_docs/overnight_report.md`.
The handback is
`thesis_docs/Dwell_Capacity_Parameter_Method_and_Implementation_Justification.{md,docx}`.

Standing facts (do not lose them):
- **EV2Gym's sessions are Dutch AC sessions, not DC.**
  - Durations come from the ElaadNL `public` column of
    `mean-session-length-per.csv`, floored at `min_time_of_stay` = 200 min,
    plus 2 steps.
  - The simulated mean is 300.6 min; no session is under 225 min.
  - Every Weeks 1–7 and closure result uses these durations. The closure
    capacity results are now a declared sensitivity.
- **The DC session model is primary for capacity.**
  - `ev2gym_thesis/demand/dc_sessions.py` is a lognormal, mean 42 min, CV
    0.5, with a 32/78 min bracket. These are external references, not
    Colombian (U.S. DOE 2023; Hardman 2026).
  - The transform rewrites departures inside EV2Gym's spawner, from outside
    the library. Its parameters live in a `<config>.dwell.json` sidecar,
    never a YAML key.
  - Enable it BEFORE `censoring.enable()`.
- **EV2Gym's RoundRobin follows the median-smoothed power setpoint, never
  the transformer** (`heuristics.py`, lines 58–77).
  - Its zero overload in Weeks 1–7 is a long-stay artefact.
  - Under DC sessions it fails at every demand level.
  - `ev2gym_thesis/heuristics.py::RoundRobinTransformerCapped` is a
    added as a diagnostic and **promoted to the recommended operating strategy on 2026-10-07**, with the display name "Round Robin, transformer-aware": the same allocation, with a budget of 0.999 × rating.
- **Results:**
  - Runs are in `results/dwell_registry.csv` (23,200 rows, master schema).
    `master_results.csv` was NOT touched; its pins are unchanged.
  - The binding constraint under DC is power, not ports.
  - The transformer-aware Round Robin holds through 1.3×, which is 47 offered
    arrivals/day (763 kWh/day), on 8 ports and the 100 kW unit. At 1.6×
    (57/day, 911 kWh/day) it needs 10 ports.
  - The closure's 34.6% DNS was largely a duration artefact.
- **The demand multiplier is not comparable across session models.** Use
  physical units (`results/dwell_d_physical_units.csv`). At 1.0×: Dutch
  22.3 arrivals and 327 kWh/day; DC 42 min, 38.9 arrivals and 627 kWh/day.
- **The final RL model is out of its training distribution under DC
  sessions.** Never present its DC results as RL evidence.
- **Enel Unicentro Bogotá serves up to 10 vehicles simultaneously** (Blu
  Radio 2026). The "8 ports exceed any Enel site" limitation is withdrawn.

**Update, 2026-10-07: Last run (the practical part is CLOSED). Branch
`semana-7`, uncommitted.** The decision log is the last-run section at the
top of `thesis_docs/overnight_report.md`. The handback is
`thesis_docs/Final_Parameter_Method_and_Implementation_Justification.{md,docx}`.
- **Recommended operating strategy: "Round Robin, transformer-aware"**
  (`ev2gym_thesis/heuristics.py::RoundRobinTransformerCapped`; budget 0.999
  × rating; pinned by `test_dwell.TestTransformerAwareBudget`). EV2Gym's
  `RoundRobin` is NOT the recommendation: it follows the median-smoothed
  setpoint (`heuristics.py` lines 54–93, line 58; `utils.py` lines 664–772).
- **Under DC sessions the non-causal bounds are not upper bounds on
  service.**
  - MPC_TrackingG2V and Optimal_Oracle_Tracking track the same setpoint.
  - At 1.0× their DNS is 48.5% / 39.9%, against 5.0% for the
    transformer-aware Round Robin.
  - MPC is infeasible in 37.7% of its steps (it applies zero power there).
  - Never call them bounds on demand served.
- **Voltage under DC on node_123** (weekday, 50 seeds): AFAP and the
  transformer-aware Round Robin have 0/50 cells out of band at 1.0/1.3/1.6×
  (lowest bus 0.9733 p.u.). The other arms are not evaluated.
- **Barranquilla under DC profiles:** the two-band cost is within 4% of the
  flat cost; no longer material. The cost of the limit is about
  10,000 COP/day in Bogotá (2.8% of margin).
- **Runs:** `results/dwell_registry.csv` has 23,800 rows (+600 bounds
  rows). The voltage runs are in `results/dwell_ieee123_voltage_by_run.csv`.
  `master_results.csv` is untouched.

## Useful Commands (reference, don't re-derive these each time)

```bash
# One-time environment setup (in addition to requirements.txt)
pip install -e .
pip install pandapower numba multicopula gurobipy stable-baselines3 sb3-contrib jupyter

# Run a single scenario with a given config + algorithm
python -c "
from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible
env = EV2Gym(config_file='experiments/phase1_baseline/configs/station_v0_bogota.yaml',
             save_replay=True, save_plots=True)
state, _ = env.reset()
agent = ChargeAsFastAsPossible()
for t in range(env.simulation_length):
    actions = agent.get_action(env)
    state, reward, done, truncated, stats = env.step(actions)
print(stats)
"
```
