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

Reference papers live in `thesis_docs/references/` (NOT `docs/` — that
folder already holds this repo's own Sphinx documentation, don't touch it):
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
- **Active phase:** Week 2 — Station-Size Sensitivity + Grid Model Sanity Check
- **Active branch:** `semana-2` (branched from `semana-1`'s tip, NOT from
  `main` — as of 2026-08-11, `main` still has the pre-fix `station_v0_bogota.yaml`
  since `semana-1` has not been merged yet. Deviates from the stated
  "branch from main" convention; flagged here since it affects reproducing
  this branch's config history.)
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
- **Next concrete task (Week 2, in progress):** station-size sensitivity
  sweep — `configs/station_sensitivity/` (n=2 and n=16 ports, at both fixed
  100 kW transformer and ratio-scaled transformer) run via
  `scripts/run_size_sensitivity.py`, emitting
  `experiments/phase1_baseline/results/size_sensitivity.csv`. Then the
  Week 2 grid model sanity check (Round Robin on a grid-enabled scenario,
  per `PROJECT_ROADMAP.md`).

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
