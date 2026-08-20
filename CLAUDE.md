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
  (±5% voltage band, OCPP + CCS Combo 2 interoperability, min. 5 public
  stations per category-especial city).

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
4. **Git discipline:** work on the `semana-N` branch matching the current
   week (e.g. `semana-1`, `semana-2`, ... `semana-8` — no `dev` branch, no
   `feature/*` naming, working solo). Commit incrementally on that branch.
   Merge to `main` only when I confirm the week's checklist is done, then
   create the next `semana-N` branch from the updated `main`. Do not merge
   to `main` without my explicit confirmation — I tag milestones manually.
5. **When a task is ambiguous** (e.g. "which real station do we model"),
   propose a concrete, clearly-labeled assumption and proceed — don't block
   on it — but always write the assumption down in the relevant
   `docs/thesis/*.md` file so it can be challenged/revised later.
6. **Gurobi**: assume an academic license is available via university email;
   if a Gurobi call fails due to licensing, tell me immediately rather than
   silently switching to a different solver, since MPC/optimal baselines
   are a required comparison point.

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
