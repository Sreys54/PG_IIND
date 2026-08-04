# Project Roadmap — EV Charging Station Operation Optimization (Colombia)
**Student:** Santiago Reyes Cortes (202221394) — Industrial Engineering, Universidad de los Andes
**Advisor:** Alejandra Tabares Pozos
**Term:** 2026-20 | **Compressed to 8 weeks**

> ⚠️ Compressing 16→8 weeks means each phase now runs in parallel with
> documentation instead of sequentially after it, and RL training scope is
> deliberately reduced (short horizons, fewer scenarios) — this is a
> conscious trade-off documented in the thesis limitations section, not
> something to hide.

**Verified feasibility (already done, see below):** the repo was installed
and smoke-tested locally. A grid-enabled scenario (150 chargers, IEEE
34-bus, AFAP heuristic, 96 steps) runs in **~7 seconds**. This means running
50 stochastic scenarios per algorithm (matching the papers' methodology)
costs minutes, not hours — the 8-week compression is realistic for
heuristics/MPC. RL training is the only piece that needs deliberate scope
reduction (see Week 4–5).

Confirmed available output metrics from `env.step()` stats dict:
`total_ev_served, total_profits, total_energy_charged/discharged,
average_user_satisfaction, power_tracker_violation, tracking_error,
energy_user_satisfaction, total_transformer_overload, battery_degradation
(+calendar/cycling), total_reward, voltage_violation,
voltage_violation_counter(_per_step)`. These map directly onto your
proposal's success metrics (>90% satisfaction, <15% energy error, ±5% RETIE
voltage band).

---

## 0. Repo Setup — Already Scaffolded ✅

Done in this session (mirror this on your own machine / your fork):
1. Cloned `StavrosOrf/EV2Gym`, installed in editable mode
   (`pip install -e .`) plus dependencies not pinned tightly enough in
   `requirements.txt` on a fresh environment: `pandapower`, `numba`,
   `multicopula`. **Action item for you:** on your Windows machine run
   `pip install -e . && pip install pandapower numba multicopula gurobipy
   stable-baselines3 sb3-contrib jupyter`. If any of these fail, tell
   Claude Code immediately (don't skip silently).
2. Verified `ev2gym/example_config_files/V2Ggrid.yaml` (the grid-simulation
   template, IEEE 34-bus, `simulate_grid: True`) runs end-to-end with the
   `ChargeAsFastAsPossible` heuristic — this is now your starting config.
3. Folder structure created:
   ```
   experiments/phase1_baseline/{configs,results/figures}/
   experiments/phase2_algorithms/{configs,results/figures}/
   experiments/phase3_infra_replicability/{configs,results/figures}/
   thesis_docs/{references,chapters}/   # NOT docs/ — that's Sphinx's, already in the repo
   notebooks/
   ```
4. Seeded `experiments/phase1_baseline/configs/station_v0_bogota.yaml`
   (currently a copy of `V2Ggrid.yaml` — **your first real task is editing
   this**, see Week 1).

**Your remaining one-time setup (do this before Week 1):**
```bash
# 1. Fork on github.com (StavrosOrf/EV2Gym → your account)
# 2. Clone YOUR fork locally, then reproduce the scaffolding above
#    (or ask Claude Code to redo it directly inside your cloned fork).
git remote add upstream https://github.com/StavrosOrf/EV2Gym.git
git checkout -b semana-1
```
Place the 3 papers + regulatory PDFs into `thesis_docs/references/`.
Copy `CLAUDE.md` (separate file) into the repo root.

---

## Phase → Objective Mapping (unchanged from proposal, timeline compressed)

| Phase | Proposal objective | Branch | Weeks |
|---|---|---|---|
| 1. Baseline characterization | Objective 1 | `semana-1` | 1 |
| 2. Grid model validation | Objective 2 | `semana-2` | 2 |
| 3. MPC/optimal baseline | Objective 3 (part 1) | `semana-3` | 3 |
| 4. RL baseline (vanilla + PI-TD3) | Objective 3 (part 2) | `semana-4`, `semana-5` | 4–5 |
| 5. Infrastructure guidelines | Objective 4 | `semana-6` | 6 |
| 6. Replicability + writing catch-up | Objective 5 | `semana-7` | 7 |
| 7. Consolidation & submission | — | `semana-8` → `main` | 8 |

---

## Week 1 — Station Config + Baseline Run (Objective 1)
- [ ] Edit `station_v0_bogota.yaml`: pick the representative station type
      (`scenario: public/work/residential`), set `number_of_charging_stations`,
      connector assumptions (Tipo 2 AC / CCS Combo 2 DC), and transformer
      `max_power` to something plausible for a Bogotá public station.
- [ ] Decide and document (1 paragraph, `thesis_docs/chapters/01_baseline.md`)
      which real/composite station you're representing and why — this is
      an assumption, state it as one.
- [ ] Run `ChargeAsFastAsPossible` (AFAP) = "operación actual no gestionada"
      → save stats to `experiments/phase1_baseline/results/baseline_afap.csv`.
- **Milestone:** tag `v0.1-baseline`. Merge `semana-1 → main`, then
  `git checkout main && git checkout -b semana-2`.

## Week 2 — Grid Model Sanity Check + Round Robin (Objectives 1–2)
- [ ] Run `RoundRobin` heuristic on the same config — second baseline point
      and a sanity check that grid constraints (voltage, transformer)
      actually bind under this station's load.
- [ ] Write the model-validation note: what's realistic here vs. what's a
      simplification (e.g., synthetic bus network vs. a real Bogotá feeder
      topology — you almost certainly don't have the latter, say so).
- **Milestone:** tag `v0.2-model-validated`.

## Week 3 — MPC/Optimal Baseline (Objective 3, part 1)
- [ ] Get the Gurobi academic license sorted **now** if not done — the
      single biggest external dependency risk in the compressed plan.
- [ ] Run the Gurobi-based oracle/MPC baseline (`ev2gym/baselines/mpc/` or
      `gurobi_models/`) on the same scenario set.
- [ ] If Gurobi licensing isn't ready by mid-week, flag it explicitly
      rather than silently substituting a weaker solver.

## Week 4–5 — RL Baseline, Scoped Down (Objective 3, part 2)
- [ ] Train a **vanilla TD3 or SAC** (Stable-Baselines3) on a *reduced*
      version of the scenario: shorter simulation length, fewer stochastic
      seeds during training, fewer total timesteps than the paper's
      original (hours, not days). Explicitly log the reduced training
      budget in `thesis_docs/chapters/00_lab_log.md`.
- [ ] If time allows, bring in **PI-TD3** from `EV2Gym_PI-TD3` as the
      headline physics-informed comparison — this is the differentiator of
      your thesis vs. a purely heuristic/MPC comparison, worth prioritizing
      over polishing the vanilla RL baseline if you must cut something.
- [ ] Run all 4 algorithms (AFAP, RR, MPC, RL) over the **same replay
      files** for ≥20–30 stochastic scenarios (scaled down from the
      papers' 50 given the compressed timeline — document the reduction).
- **Deliverable:** comparison table + 1–2 plots (violin/boxplot style) in
  `experiments/phase2_algorithms/results/`.
- **Milestone:** tag `v0.3-algorithms-compared`.

## Week 6 — Infrastructure Guidelines (Objective 4)
- [ ] Pick the recommended algorithm (explicit trade-off discussion:
      satisfaction vs. profit vs. voltage compliance).
- [ ] Stress-test at 2–3 load multipliers (e.g., 1.0×, 1.3×, 1.6×, using
      the `load_multiplier` field in `network_info`) instead of the full
      0.5×–1.25× sweep from the paper — enough points to show a trend.
- [ ] Draft concrete infrastructure lineamientos (chargers, capacity,
      PV integration) tied to OCPP/CCS Combo 2 and Ley 1964.
- **Milestone:** tag `v0.4-infra-guidelines`.

## Week 7 — Replicability (Objective 5) + Writing Catch-up
- [ ] Re-run the winning strategy on one alternative city-context scenario
      (different load multiplier / tariff assumption standing in for
      Medellín/Cali/Barranquilla/Bucaramanga).
- [ ] Document restrictions/critical assumptions explicitly.
- [ ] Reserve at least half this week for writing — by now you should have
      draft content for baseline, model validation, and algorithm
      comparison chapters; don't let writing pile up entirely into Week 8.
- **Milestone:** tag `v0.5-replicability`.

## Week 8 — Consolidation & Submission
- [ ] Assemble the full document (Word, APA citations) from
      `thesis_docs/chapters/*.md`.
- [ ] Clean `main`: fresh clone → `pip install -e .` → one script/notebook
      reproduces every reported number by config file name.
- [ ] Final read-through against your original proposal's success metrics
      (>90% satisfaction, <15% energy error, ±5% voltage compliance) —
      report actual numbers achieved, gaps included.
- **Milestone:** tag `v1.0-thesis-submission`.

---

## What Got Cut / Compressed vs. the 16-Week Plan (be upfront about this)
- Stochastic scenario counts per algorithm: 50 → ~20–30.
- RL training budget: hours/days on HPC → hours on a laptop; expect lower
  absolute performance than the papers report, and say so.
- Load-scaling generalization sweep: 8 points (0.5×–1.25×) → 2–3 points.
- Replicability check: 1 alternative city instead of exploring all four.
None of this invalidates the thesis — it's a standard scope reduction for
a compressed timeline, as long as it's stated explicitly rather than
implied to match the original papers' scale.

## Git Discipline Checklist (apply every week)
- Commit early/often (`feat:`, `fix:`, `exp:`, `docs:` prefixes).
- `.gitignore` large binaries (`*.pkl`, replay files) — commit summary
  CSVs + plots only.
- Merge every `semana-N` branch into `main` at week's end (even solo) —
  gives you a clean changelog for the reproducibility appendix. Create
  `semana-(N+1)` from the freshly updated `main`.
- Tag every milestone above.
