# Week 8 — Advisor review of 2026-11-01: code and run corrections

## Context

The advisor (Alejandra Tabares Pozos) reviewed the article draft of
2026-10-23 (`Documento_Final_PG_IIND.docx`). Her full review is at
`thesis_docs/sources/advisor_review_2026-11-01/Comentarios_Santiago_2026-11-01.tex`
(and the compiled `.pdf` beside it). **Read the whole `.tex` before
anything else.** It is in Spanish and numbered by section (3.1 to 3.15).
This brief covers every comment that needs code or runs. The writing-only
comments (3.1, 3.2, 3.13, most of 3.12 and 3.14) are handled outside Claude
Code, but this brief asks you to produce the numbers and code facts they
depend on.

Branch: stay on `semana-8` (the working tree is clean at `8b2fc50`). Never
commit, merge, push or tag. Leave everything uncommitted. At the end of
each block, propose a commit grouping so I can commit before the next block
starts.

The `TD3_safe` code from 2026-10-24 (`ev2gym_thesis/rl/config_safe.py`,
`safety.py`, `reward_service.py`, `state_service.py`, `safe_training.py`,
`scripts/train_td3_safe.py`, `scripts/evaluate_safe_rl.py`,
`ev2gym_thesis/tests/test_safe_rl.py`) was written but **never trained**.
This brief trains it, after the arrival generator is replaced (Block B),
because the agent must be trained in the environment it will be evaluated
in.

Decisions already taken by me (do not reopen them):

- **RL in the DC regime: full path.** Train `TD3_safe` in the DC regime
  with the hard transformer constraint and the served-energy reward. The
  Week 6 model (`TD3_vanilla` extended, seed 102, 850k steps) stays as the
  RL model of the long-dwell regime and is not retrained.
- **DC arrivals: a station-level Poisson generator outside EV2Gym**, with no
  dead time between sessions on a port, and demand levels defined by
  offered energy.
- **Sensitivities 3.11:** all three (load-dependent departure, 5-minute
  step, 22 kWh per session), run in that order, if the compute budget allows.

## Standing rules (from `CLAUDE.md`; repeated because they matter here)

- Do not modify `ev2gym/models/*.py` or `ev2gym/rl_agent/*.py`. Everything
  new goes in `ev2gym_thesis/` or `scripts/`. If a change inside the library
  is truly unavoidable, stop and tell me why first.
- Statistics: `paired_cluster_bootstrap_ci`, resampling the scenario seed,
  with `n_clusters` printed in every table. Grid: 50 seeds × 2 day types =
  100 cases. Report the number of resamples, the interval method and the
  resampling unit in every handback table (advisor 3.10).
- Never mix rows with and without `simulate_grid` in one statistic. Add two
  new registry columns and never mix their values in one statistic either:
  `arrival_model` (`ev2gym_spawner` | `station_poisson`) and `safety_layer`
  (`none` | `proportional`). Do not overwrite or delete existing registry
  rows. New DC rows go in a new registry `results/review_registry.csv` with
  the same schema plus the new columns. Allowlist it in `.gitignore` the way
  `dwell_*` and `safe_rl_*` were.
- Report only numbers you actually ran. If something was not run, say so.
- Gurobi: if the license fails, stop and tell me. Do not swap the solver.
- Ambiguity: propose a concrete, labelled assumption, proceed, and record it
  in the handback.
- **Long runs:** keep replay buffers, intermediate checkpoints and worker
  shards **outside the OneDrive-synced repo** (for example `C:\ev2gym_runs\`
  via `--output-root`). Copy only the selected final checkpoint and its
  `_vecnormalize.pkl` into `experiments/phase2_algorithms/models/`. Use the
  existing keep-awake and `--resume` support. Every long process must be
  resumable after a crash or a reboot.

---

## Gate 0 — audit and plan (stop and report)

1. Confirm the branch, the clean tree, that `Ran 155 tests` still passes,
   and that the Gurobi license works.
2. Confirm in **this repo's copy** of EV2Gym each code fact the advisor
   cites, with file and line. Say "matches" or "differs" for each:
   `EV_spawner` (free port at t, t−1 and t−2), `get_user_satisfaction`
   (`current_capacity / desired_capacity`), `spawn_single_EV` (arrival
   capacity = battery − requested), `generate_power_setpoints` (iterates
   `env.EVs_profiles`, uses `time_of_departure`), `median_smoothing`
   (centred window t−2..t+2), the MPC infeasibility path (`INFEASIBLE
   (applying default actions)` returning zeros), and `get_statistics`
   (fixed 0.95–1.05 p.u. band). `desired_capacity: 1` is already confirmed
   in both station configs.
3. Inventory what is stored per case: is there per-EV data (requested
   energy, delivered energy, departure step) and per-step time series (power
   per port, setpoint, transformer load, reward terms) for each arm and
   regime? For each Block A item, say whether it can be done by
   post-processing or needs re-simulation, and estimate the wall-clock time
   from measured timings (time one case per arm; do not guess).
4. Give a time plan for Blocks A–D on this laptop (cores available, what
   runs in parallel), with the hard deadline below in mind, and propose
   cuts if it does not fit.

**Hard deadline: all of Blocks A–C finished and reported by Thursday
2026-11-05 at 20:00 (America/Bogota).** Block D fills whatever remains
until Friday 2026-11-06 at 14:00. If something cannot fit, say what you
would cut in Gate 0. Do not cut silently later.

After I approve Gate 0, run Block A without stopping.

---

## Block A — post-processing and audit (no new arrival model)

Applies to the existing results of **both** regimes (long-dwell, EV2Gym
native; DC 42-min at 1.0×, 1.3×, 1.6× with the current spawner).
Re-simulate only where Gate 0 found the data missing. Re-simulated rows use
the same seeds and configs and must reproduce the registry values of the
existing metrics (assert it).

**A1. Energy satisfaction (advisor 3.3).** Implement in
`ev2gym_thesis/metrics/service.py`:
f_i = min(1, e_i / R_i), with e_i the energy delivered and R_i the energy
requested. Rejected drivers count with f_i = 0. Report the mean of f and the
service level (share of drivers with f_i ≥ 0.9), both with and without
rejected drivers, for every arm in both regimes. Keep EV2Gym's metric under
the name `ev2gym_battery_level_satisfaction`, documented with its real
definition s = 1 − (R/C)(1 − f). Add a test that recovers the advisor's
check: for served EVs, s ≈ 1 − (R/C)·ENS_rel on the stored grid.
Re-evaluate every anteproyecto target (satisfaction > 90%, DNS ≤ 15%,
overload, voltage) with the new metric. Labelled assumption: the 90% target
applies to the mean of f including rejected drivers. Report the service
level next to it.

**A2. One aggregation rule (advisor 3.10, doubt on means of ratios).**
Find every percentage in tables, chapters and figure captions and say how
each one is computed today (mean of per-case ratios, or ratio of totals).
Adopt **ratio of totals** (pooled kWh) as the single rule for energy
percentages (ENS_rel, DNS, overload share), computed inside each bootstrap
resample. Recompute and list every number that changes: the RR
tracking-error reduction (75.5% vs 75.8%), RR-TA ENS_rel (2.7% vs 2.84%),
AFAP long-dwell DNS (34.3% vs 38.2%) and any other.

**A3. Table IV and automatic tables (advisor 3.9).** Find the root cause of
the EV2Gym Round Robin row at 1.6× with 14 ports and 400 kVA (margin 512.6
k COP/day implies 3.7% DNS; the table says 13.1%). Say whether the error is
in the margin, the DNS or the offered demand. Write
`scripts/build_paper_tables.py`, which generates every article table
(I–V and the new ones in this brief) directly from the registries as `.xlsx`
and as Markdown. Add a test that, on every registry row, checks
margin = E·(p − c) within 0.5% and DNS = 1 − E / E_offered within 0.5
points, using each row's own p and c.

**A4. RL diagnosis (advisor 3.4).** On the long-dwell test grid (where the
Week 6 agent was trained):
- Decompose `SqTrError_TrPenalty_UserIncentives` into its three terms
  (squared deviation from min(setpoint, potential, rating), −100 per kW of
  overload, −1000·(1 − s) per departing EV). Report each term separately,
  per day, for the 60k and 850k checkpoints of all three seeds, with
  cluster CIs for the 850k − 60k difference.
- Compute the same reward, post hoc, from the time series of AFAP, EV2Gym
  RR, RR-TA, Random and MPC-T. State plainly whether any of them beats the
  850k TD3 on TD3's own reward.
- Test the advisor's hypothesis: did the deviation from the min(...) target
  improve while the raw `tracking_error` worsened? Report both per
  checkpoint.
- Paired comparison TD3 850k vs Random on all six Table II metrics, with
  CIs, and which differences are significant.
- Extract for the text: the checkpoint-selection rule exactly as coded
  (file and line), the training seeds vs the 50 test seeds vs the 10
  validation seeds (state that they are disjoint and prove it with the
  existing leakage test), what the training scenarios actually vary (seed
  vs date), and the budget in episodes (60,000 steps = 625 days; 850,000 =
  8,854).
- List all 27 state elements of the `PublicPST` state with their meaning
  and normalization, the action definition, γ, episode length, network
  architecture, exploration noise and budget, for the MDP formulation in
  the article (advisor 3.7).
- Enumerate the "fifteen TD3 checkpoints" quoted in IV-C: which ones they
  are, or correct the count (advisor 3.15).

**A5. MPC facts (advisor 3.7 doubts).** With file and line:
- Where `MPC_TrackingG2V` comes from (library class, our code or the
  companion repo) and its exact objective function and constraints, with
  units.
- `MPC_EnergyMaxG2V`: the sign of the objective, and which prices it
  receives (Dutch ENTSO-E, Colombian flat, or none). If any control
  decision in any arm depends on a price signal, say which, because the
  article claims none does.
- The source of the "+3.1 COP/day" of MPC-E over AFAP (solver tolerance,
  rounding or a real difference), as a kWh figure.
- The oracles' formulation (the same model with a one-day horizon?).

**A6. Information table (advisor 3.6).** For every arm, verify from the
code what it uses at step t: connected EVs, transformer rating, requested
energy, departure time, future arrivals (and how far ahead), the setpoint.
Confirm whether the EV2Gym RR and the TD3 state receive the setpoint, and
therefore indirect departure, energy and next-step arrival information.
Deliver the table as `.xlsx` and Markdown.

**A7. Long-dwell DNS bounds (advisor 3.8, task 3).** Report both bounds of
DNS in the long-dwell regime: the current lower bound, and an upper bound
that also counts as rejected every successful arrival draw that fell on a
blocked port while another port was free. Show both per arm, with CIs.

**A8. Facts for the text (advisor 3.12, 3.15):**
- The Week 1 transformer sweep (250, 150, 100, 75 and 50 kW): the AFAP
  overload at each rating, from the stored rows.
- The station's peak load per day: report the P95 and the maximum
  side by side for every DC arm, plus the number of days above the rating.
- What Week 2 produced (Bogotá-temperature battery degradation, city
  weather profiles, the 2/8/16-port sensitivity): the files, the numbers
  and one paragraph summarizing them.
- Every remaining "60 kWh" in the repo (code, configs, chapters, docs).

Block A deliverables: one workbook `results/review_A_post_processing.xlsx`
(one sheet per item), the figures that change, a dated lab-log entry, and
tests. Then write the Block A report and continue to Block B.

---

## Block B — station-level arrival generator (stop at Gate 1)

Implement `ev2gym_thesis/demand/station_arrivals.py`. It replaces
EV2Gym's `EV_spawner` for the DC regime, from outside the library. Use a
wrapper or subclass in `ev2gym_thesis/`, the way `dc_sessions.py` injects
durations.

Design requirements:

1. **Arrival stream, fixed per scenario.** For each (scenario seed, day
   type), draw the whole day's stream before the simulation with a seeded
   RNG: Poisson count per 15-min step with λ_t = τ(t)/Στ × arrivals_per_day,
   where τ is EV2Gym's arrival profile (`distribution-of-arrival.csv`,
   weekday or weekend, reordered to start at 05:00). Each arrival carries
   its requested energy (from EV2Gym's current per-arrival-hour table) and
   its sampled dwell (the existing lognormal, mean 42 min, CV 0.5, from
   `dc_sessions.py`). Every arm sees exactly the same stream (paired
   comparisons).
2. **Port assignment online, at simulation time.** At each step, before the
   control action, every arriving driver takes any free port, the first by
   index. A port is free as soon as the previous EV has left: **no dead
   time** (drop EV2Gym's t−1/t−2 rule). If no port is free, the driver is
   rejected and recorded with their requested energy. Assignment must be
   online, not precomputed, because Block D1 makes departures depend on the
   control. Under fixed departures, the assignments come out identical
   across arms. Assert it.
3. **Exact DNS.** With this generator, rejections are observed, not
   reconstructed: DNS = (E_rejected + R_served − E_delivered) /
   (E_rejected + R_served). It is exact, no longer a lower bound. Label it
   so.
4. **Demand levels by offered energy (advisor 3.8, task 1).** Calibrate
   `arrivals_per_day` so that the mean offered energy over the 100 cases is
   627 kWh/day at 1.0× (labelled assumption: 1.0× keeps the current DC
   offered energy, so results stay comparable to the current article), then
   1.3× (≈ 815 kWh) and 1.6× (≈ 1,003 kWh, the anteproyecto's +60%).
   Report each level in arrivals/day, kWh/day and kWh per port per day.
   Weekday and weekend use their own τ with the same daily total
   multiplier. Say how you handled it.
5. Tests: the stream is identical across arms for the same seed;
   λ calibration reproduces the target energy within 1%; a port is
   reusable in the step after a departure; rejections happen only when all
   ports are occupied; a no-control run conserves energy (delivered ≤
   requested per EV).

### Gate 1 (stop and report)

At 1.0×, AFAP and RR-TA, old spawner vs new generator, side by side:
offered arrivals/day, offered kWh/day, served EVs, rejected drivers, port
occupancy (with and without the old 45-minute dead time), DNS, ENS_rel,
energy satisfaction (A1), overload, margin. Explain every difference.
Measure how much the 1.3× threshold and the 10-port recommendation move
without the dead time (advisor's doubt in 3.8). This gate defines every DC
result from here on. Wait for my approval.

---

## Block C — fair comparison in the DC regime (new generator)

All rows: `arrival_model = station_poisson`, `simulate_grid = False`
(except C5), levels 1.0×, 1.3× and 1.6×, 100 cases each.

**C1. One safety layer for every causal arm (advisor 3.5).** Reuse
`ev2gym_thesis/rl/safety.py` (common scaling factor, 0.999 × rating) as
**the** layer for every arm that receives it. Do not write a second one.
Arms:

| Arm | Description | Causal |
|---|---|---|
| AFAP | unmanaged, reference for overload | yes |
| PS | AFAP + safety layer = proportional sharing (new baseline) | yes |
| FIX12.5 | every port capped at 100/8 = 12.5 kW, what an installer would do (advisor 3.2) | yes |
| RR | EV2Gym Round Robin, unchanged | no (setpoint) |
| RR+S | EV2Gym Round Robin + safety layer | no (setpoint) |
| RR-TA | transformer-aware Round Robin | yes |
| Random+S | random actions + safety layer, negative control | yes |
| TD3_safe | trained in C3 | yes |
| MPC-soft | operator objective, soft departure constraint (C2) | no |
| MPC-soft-est | same MPC, departure estimated as arrival + 42 min, no future arrivals (C2) | yes |
| Oracle-E | full-day perfect information, max energy within 100 kW (C2) | no |

MPC-T and Oracle-T (setpoint tracking) are not rerun in the DC regime. They
stay in the long-dwell regime only. Say so in the handback. Check the
causality column against A6 and fix it if the code says otherwise.

**C2. MPC and oracle with the operator objective (advisor 3.5 tasks 3–4,
3.6 task 2, 3.7).** Implement in `ev2gym_thesis/mpc/` (do not edit the
library classes):
max Σ_k Σ_i P_{i,k}·Δt − ρ·Σ_i σ_i
s.t. 0 ≤ P_{i,k} ≤ P_max·a_{i,k}; Σ_i P_{i,k} ≤ P_tr (kW);
E_{i,k+1} = E_{i,k} + η·P_{i,k}·Δt; E_{i,k} ≤ C;
E_{i,d_i} ≥ E_req_i − σ_i, σ_i ≥ 0,
with H = 10 steps, Δt = 0.25 h, units declared, and ρ labelled and
justified. It must never be infeasible. Count and report infeasible
solves, which should be 0. Oracle-E is the same model with a one-day
horizon and full knowledge. It is the upper bound on energy for the RR-TA
in this regime (it replaces "no upper bound exists"). MPC-soft minus
MPC-soft-est is the value of knowing departure times with everything else
fixed. Report it as such, not as a bound. Write each formulation as LaTeX in
the handback.

**C3. Train `TD3_safe` in the DC regime (advisor 3.4 tasks 3–6, 3.5
task 5).**
- Adapt `scripts/train_td3_safe.py` so the dc42 regime uses the
  station-level generator at 1.0×. Keep everything else in `config_safe.py`
  (reward, state, hyperparameters, safety layer, selection by validation
  energy delivered). Training seeds 100, 101, 102; validation seeds
  1,000,000–1,000,009; test seeds 0–49. Keep the leakage assertion.
- **Before training, write the checkpoint-selection rule into
  `config_safe.py` and the handback** (the existing 2%/5% rule on 50,000-step
  windows, applied to validation energy delivered; the final checkpoint is
  the one with the best validation value after convergence). Add a
  carried-model rule fixed now: the seed with the best validation value is
  the `TD3_safe` model used in every later table, and the test results of
  all three seeds are reported next to it.
- Also log, per validation evaluation, the three terms of the old reward
  (A4), so the advisor's comparison can be made on the new agent too.

### Gate 2 (stop before the real training run)

Run a calibration (`--max-steps` small, output outside OneDrive) and report
the measured steps/hour per seed with 1, 2 and 3 seeds in parallel, while
Block C1/C2 evaluations share the CPU. Propose the launch: number of
parallel seeds, `--deadline` (no later than **Wednesday 2026-11-04 at
14:00**), and expected steps per seed. If fewer than about 250,000 steps per
seed fit, propose two seeds instead of three. Wait for my approval. While
waiting and while training, run C1 and C2.

After training: if no seed converges by the deadline, use the
best-validation checkpoint and report non-convergence as a result, not a
failure. If `TD3_safe` does not beat Random+S on the test grid, report it as
it is.

**C4. Capacity and infrastructure (advisor 3.8).** Under the new generator,
redo the infrastructure table:
- RR-TA and PS: the largest arrivals/day (and kWh/day) with DNS ≤ 15% **and**
  the A1 satisfaction target met, at 8 and 10 ports with the 112.5 kVA unit
  (bisection on `arrivals_per_day`).
- At 1.6× (+60%): the minimum ports with the same transformer for RR-TA and
  PS, the minimum transformer (ET-013 sizes) for AFAP at 8 ports, and the
  ports/transformer EV2Gym RR needs.
- RR-TA vs FIX12.5 and vs AFAP with 300 kVA: differences in energy, DNS,
  satisfaction and gross energy margin, with CIs. This is the comparison
  against a feasible alternative that the general objective needs (advisor
  3.2).
- Cost of respecting the transformer in COP/day and as a share of margin,
  against AFAP and against FIX12.5.
In Gate 0, propose the smallest grid that answers these questions.

**C5. Voltage (advisor 3.2 task 3, 3.10, 3.12).** node_123, weekday, 50
cases, `simulate_grid = True` with the station at bus 115 through
`placement.py`. Run AFAP, PS and RR-TA at 1.0× and 1.6× with the new
generator. Report the feeder minimum and **the station-bus voltage**, the
absolute differences in p.u. with CIs, and the count of cases outside
0.95–1.05 p.u. (EV2Gym criterion) and outside 0.90–1.10 p.u. (CREG 024 of
2005). State the statistical vs physical significance in p.u.

**C6. Comparison table (advisor 3.10).** One master table per level: every
C1 arm × {energy kWh/d, ENS_rel, DNS (exact), mean f, service level f ≥ 0.9,
EV2Gym battery-level satisfaction, overload kWh/d, days with overload,
peak P95 and max, gross energy margin}, with CI half-widths and the
paired difference vs RR-TA with CI. Denominators in days. State whether the
CIs are per comparison or adjusted (Holm), and use the same choice
everywhere. Re-evaluate the targets for every arm and level.

Block C deliverables: `results/review_C_dc_comparison.xlsx`, figures
(load profiles of AFAP / PS / RR-TA / TD3_safe on a typical day, DNS and
satisfaction by level, the capacity threshold, the `TD3_safe` validation
curves), a dated lab-log entry, and tests (safety layer never exceeded for
any arm, Oracle-E ≥ every causal arm's energy per case, MPC-soft never
infeasible).

### Gate 3 (report, no stop)

A short results report for Blocks A–C. Then continue straight to Block D.

---

## Block D — DC sensitivities (if time allows, in this order)

Each one only for AFAP and RR-TA (plus PS where cheap) at 1.0× and 1.6×, new
generator, 100 cases, paired against the base Block C run. Report how the
capacity threshold (arrivals/day and kWh/day) and the port recommendation
move.

- **D1. Load-dependent departure (advisor 3.11 task 1):** departure =
  max(sampled dwell, time the EV needs to receive its requested energy at
  the power actually assigned), capped at 90 minutes. Labelled assumption:
  the cap is 90 min. The departure is updated online from the wrapper,
  never by editing `ev2gym/models/ev.py`. Port occupancy and rejections now
  differ across arms. That is the point of this sensitivity.
- **D2. 5-minute step (task 2):** `timescale = 5` (288 steps/day),
  checking that the setpoint median filter and every per-step constant
  (Δt, budget per step, 3-step rules) scale correctly.
- **D3. 22 kWh per session (task 3):** rescale requested energy so its mean
  is 22.0 kWh (capped by battery capacity), at the same arrivals/day as the
  base 1.0×. Report the threshold in both units.

If D does not finish by Friday 14:00, stop cleanly and report which parts
ran.

---

## Final deliverables

1. `results/review_*.xlsx` workbooks (formatted, never loose CSVs), figures
   as PNG + PDF + `.caption.md` through the figure pipeline with visual QA,
   using the article's names (RR, RR-TA, PS, FIX12.5, TD3_safe, 1.0×). No
   internal jargon in titles or captions ("closure run", "Week 1 spawn
   multiplier", "Checkpoint A rule", "Extended TD3_vanilla").
2. **`thesis_docs/review_2026-11-01_numbers.md`:** every number in the
   article draft that changes, as old value → new value → source (registry
   rows or workbook sheet), grouped by article section and table. This is
   the file the writing is done from. Be exhaustive.
3. **`thesis_docs/review_2026-11-01_response.md`:** for each advisor item
   (3.3 to 3.12, plus the code parts of 3.2 and 3.15), what was done, where
   the evidence is, or why it was not done.
4. The handback `thesis_docs/Week8_Advisor_Review_Parameter_Method_and_Implementation_Justification.docx`
   (+ `.md`), in the two-part format: a parameter table with Label and
   Justification (every labelled assumption in this brief included), then
   the implementation walkthrough, including the LaTeX formulations (C2,
   MDP of TD3_safe and of the Week 6 agent, ServedEnergyReward).
5. Extend `Progress_Log_Thesis_Project_corrected_2026-09-09.docx` with a new
   section via `scripts/extend_progress_log.py` (never rewrite it).
6. Update the chapters in `thesis_docs/chapters/` that the new numbers
   touch, and add the corrections to `08_limitations.md` (item 48 is now
   addressed: say how).
7. Tests calling real production functions. Report the final `Ran N tests`
   line.
8. `CLAUDE.md` updated: Week 8 status, the two RL models and the regime each
   belongs to, the new generator, the energy-satisfaction metric, the
   ratio-of-totals rule, and that the ±5% band is EV2Gym's criterion, while
   the regulatory range is 90–110% (CREG 024 of 2005), not RETIE.

## Confirm with me before proceeding

Gate 0 (plan and timings), Gate 1 (new generator vs old), Gate 2 (training
launch budget). Everything else runs unattended under the rules above.
Propose commit groups at the end of each block. Do not commit, merge, push
or tag.
