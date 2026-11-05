# Week 8 — Parameter, Method, and Implementation Justification: Response to the Advisor Review of 2026-11-01

**Status: complete (2026-11-03). Branch semana-8; everything staged,
nothing committed.**

This document follows the usual mechanism: a Markdown record rendered to
`.docx` by `scripts/render_docx.py`. Every number in it is generated into
`thesis_docs/review_2026-11-01_numbers.md` by `scripts/review_numbers.py`
from the result files, and the point-by-point answer to the review is
`thesis_docs/review_2026-11-01_response.md`. The decision log is
`thesis_docs/chapters/00_lab_log.md` (2026-11-03 entry).

**Statistics, the same in every table of this document.** Cluster bootstrap
over the scenario seed (the independent unit; n_clusters = 50, 100 cases =
50 seeds × {weekday 2022-01-17, weekend 2022-03-05}), 10,000 resamples,
percentile 95% intervals, **per comparison** (no multiplicity adjustment:
read one interval at a time, not a family). Energy percentages and
per-driver means are **ratios of totals**, recomputed inside every resample
(`ev2gym_thesis/stats_utils.py::cluster_bootstrap_ratio`). Overload is in
kWh (see A, finding 1). Denominators are days.

## Headline Results Summary

1. **EV2Gym's transformer overload was never in kWh.**
   `total_transformer_overload` sums the overload kW of every 15-minute
   step without the step length; every "kWh/day" overload since Week 1 is
   4 × the energy (ratio 4.000 on 1,310 cases).
2. **The previous DC sessions were 15 minutes longer than labelled** (mean
   57.0 min, not 42), and EV2Gym's per-port spawner added 30 minutes of dead
   time after every departure. With station-level arrivals and the exact
   connection window, **the port count stops binding: power does.** The
   10-port recommendation at 1.6× was an artefact of the dead time.
3. **Fair comparison in the DC regime** (station-level arrivals, 8 ports,
   100 kW, one safety layer for every causal arm). At 1.0× (627 kWh/day
   offered):
   - the upper bound on energy within 100 kW (Oracle-E) is 581.7 kWh/day
     (DNS 7.3%); MPC-soft with true departure times reaches it;
   - **RR-TA is the best causal arm** (TD3_safe included): 552.9 kWh/day,
     DNS 11.8% [10.9, 12.8], mean energy satisfaction 91.2% [90.4, 91.9];
     it meets every target at 1.0× and none of the service targets at 1.3×
     or 1.6×;
   - proportional sharing (PS) delivers 6,360 COP/day less margin than
     RR-TA; a fixed 12.5 kW per port (FIX12.5) delivers about half the
     energy (DNS 51.0%);
   - knowing departure times is worth about 66 kWh/day at 1.0× (MPC-soft
     minus MPC-soft-est);
   - the cost of respecting the transformer against unmanaged charging is
     19,822 COP/day [17,076, 22,792] at 1.0× (AFAP − RR-TA margin).
4. **RL diagnosis (long-dwell).** The advisor's hypothesis holds: training
   improved the agent's own tracking term while the reported tracking
   error worsened. On its own reward the final model is beaten by the
   random policy, by EV2Gym's Round Robin and by MPC-T.
5. **Aggregation.** The three discrepancies the advisor found (75.5 vs
   75.8%, 2.7 vs 2.84%, 34.3 vs 38.2%) are exactly the mean-of-ratios vs
   ratio-of-totals difference; the ratio of totals is now the only rule.

6. **Capacity (C4).** With the 112.5 kVA unit RR-TA serves up to 40.2
   offered arrivals/day (659 kWh/day) at 8 or 10 ports; at +60% (1,002
   kWh/day) it needs a 150 kVA unit with the same 8 ports, while unmanaged
   charging needs 400 kVA.
7. **Voltage (C5).** On node_123 no arm leaves 0.95-1.05 p.u. or 0.90-1.10
   p.u.; the station moves the minimum by 0.0002 p.u. at most.
8. **Sensitivities (D).** If drivers stay until charged (cap 90 min),
   RR-TA and PS meet the service targets up to 1.6× on the 100 kW unit;
   22 kWh sessions make every managed arm fail even at 0.5×.

9. **RL with a hard constraint (C3).** TD3_safe (TD3 + the same safety
   layer, causal state, reward = energy delivered) never overloads (0 of
   900 test days, three seeds) and clearly beats the random policy under
   the same layer (+95.9 kWh/day [90.7, 101.2] at 1.0×). It does not beat
   the simple transformer-aware rotation: −16.9 kWh/day [−20.1, −13.7]
   against RR-TA at 1.0×, −29.4 at 1.6×, and it sits 5-6 kWh/day below PS
   at every level. It meets no service target at any level. The three
   seeds agree within 5 kWh/day at 1.0×. RR-TA stays the recommendation.
   A pre-registered long-budget sensitivity (2,000,000 steps per seed,
   no stopping rule) narrows but does not close the gap: the best
   checkpoint is still 7.2 kWh/day [−10.0, −4.6] below RR-TA at 1.0×.

**Gate 3 report (Blocks A-C complete, 2026-11-03 22:45 UTC−5).** No stop
was required. Every Block A-C item is complete with the numbers above; C3
ended well before the extended deadline (2026-11-05 23:59) because each
seed met the pre-registered convergence rule (convergence + 100,000 steps):
seeds 100/101/102 stopped at 230,000 / 230,000 / 300,000 steps, 3.65 h of
training in total. The stopping rule was not changed after seeing results.
Open for the author: the text items of the response (3.1, 3.12 citations,
3.13 price source, 3.14).

## Part 1 — Gate 0: audit and timing

**Repo, tests, solver.** Branch `semana-8` at `8b2fc50`, clean. Full suite
`Ran 174 tests ... OK` (the brief expected 155; the difference is the Week 8
safe-RL tests). Gurobi academic licence 2853634, valid to 2027-08-14,
solves a 3,000-variable model.

**EV2Gym code facts cited by the advisor** (this repo's copy):

| Fact | Location | Verdict |
|---|---|---|
| `EV_spawner`: a port's draw is evaluated only if the port was free at t, t−1, t−2; probability τ·(Δt/60)·multiplier/100 | `ev2gym/utilities/utils.py` lines 534-538; occupancy t+1..dep−1 at line 551 | Matches; the measured idle gap is 2 steps (30 min) after the departure step |
| `get_user_satisfaction` = current / desired capacity | `ev2gym/models/ev.py` lines 204-214 | Matches |
| `spawn_single_EV`: desired = config × battery; arrival = battery − requested | `utils.py` lines 223, 314 | Matches; `desired_capacity` = 1 in the config |
| `generate_power_setpoints` iterates `EVs_profiles`, uses departure times, multiplier (100 + flex)/100, Dutch prices | `utils.py` lines 664-772 | Matches except the prices: `prices = np.ones` since 2026-09-08 (line 694) |
| `median_smoothing`, centred t−2..t+2 | `utils.py` lines 652-661, 772 | Matches (window 5 × 15/timescale) |
| MPC infeasible → `INFEASIBLE (applying default actions)` → zeros | `ev2gym/baselines/mpc/eMPC.py` lines 133-137, 269-273; `ocmf_mpc.py` 153-157; `ev2gym_thesis/mpc/tracking_mpc.py` 141-143 | Matches |
| `get_statistics` voltage band 0.95-1.05 p.u., fixed | `utils.py` lines 67-78 | Matches |

**Timing** (one process, seed 0, weekday; `experiments/phase4_review/gate0_timing.csv`):
heuristics 0.35-0.44 s per case, MPC-T 2.7-2.8 s, MPC-E 4.3-4.8 s, oracles
0.7-1.1 s, TD3 0.48 s, a node_123 grid case 1.06 s; one TD3_safe gradient
step 11.0 ms.

## Part 2 — Block A: post-processing and audit

**Re-simulation.** The stored per-case series hold only station power,
transformer power and connected EVs, so A1 and A4 needed per-EV and per-step
data: `scripts/review_A_resim.py` re-ran 4,100 cases with a recorder
(`ev2gym_thesis/metrics/service.py`) through the original runner functions,
same seeds and configs. **Every case reproduced its registry row** on
energy, overload, tracking error, EV2Gym satisfaction and EVs served
(asserted). Workbook: `results/review_A_post_processing.xlsx` (17 sheets).

**Finding 1 — overload units.** `total_transformer_overload` =
Σ_t overload_kW(t) (`ev2gym_env.py` line 526; `utils.py` line 26), labelled
kWh by `utils.py` line 172. Energy = Σ_t overload_kW(t) × Δt = registry /
4 at Δt = 0.25 h. Example: Week 1's 0.132 is 0.033 kWh.

**Finding 2 — delivered energy per EV.** EV2Gym rounds `current_capacity`
up to 0.01 kWh after every step (`ev.py`, `my_ceil`); the recorder uses
`total_energy_exchanged` instead (found by a conservation test).

**A1 — energy satisfaction.** f_i = min(1, e_i / R_i); rejected drivers
count with f = 0. EV2Gym's metric is kept as
`ev2gym_battery_level_satisfaction` with its real definition
s = 1 − (R/C)(1 − f); the advisor's check holds on every arm within 0.1
points (test). Labelled assumption: the 90% target applies to the mean of f
including rejected drivers; the service level (share with f ≥ 0.9) is
reported beside it.
- Long-dwell: served drivers 98-100% for every non-RL arm; including the
  rejected (lower bound 8.9/day) about 60% for every arm, so **no arm meets
  the satisfaction target in the long-dwell regime**: the 8 ports bind.
- DC with the previous spawner, 1.0×: AFAP 97.5%, RR-TA 95.6%, RR 78.6%,
  final RL model 73.1%, Oracle-T 63.9%, MPC-T 53.7%.

**A2 — one aggregation rule.** 897 percentages inventoried in chapters
03-08, the three latest handbacks and the figure captions, each with how
its family is computed today (`A2_percentage_inventory.csv`). Every energy
percentage is recomputed both ways (`A2_recomputed.csv`); the advisor's
three cases: RR tracking-error reduction 75.50% (mean of ratios) → 75.86%
(ratio of totals); DC RR-TA ENS_rel 2.67% → 2.84%; long-dwell AFAP DNS lower
bound 34.29% → 38.28%.

**A3 — Table IV.** Every margin in the table equals E × 584.24 COP/kWh
exactly. The root cause is the offered-demand denominator: the "constant
station demand" scaling (spawn × 8/ports) keeps 911 kWh/day only at 10
ports; at 12/14/16 ports EV2Gym offers 968/1,008/1,062 kWh/day because more
ports means fewer blocked draws. The RR 14-port row (877.4 kWh, DNS 13.1%)
is consistent with 1,009.5 kWh offered. `scripts/build_paper_tables.py`
now generates the article tables from the registries (`.xlsx` and
Markdown), and `ev2gym_thesis/tests/test_review_A.py` checks margin =
E (p − c) within 0.5% and DNS = 1 − E / E_offered within 0.5 points.

**A4 — RL diagnosis (long-dwell grid).** The decomposition of
`SqTrError_TrPenalty_UserIncentives` reproduces the environment's reward to
1e-11 for every arm evaluated with it.
- 60k → 850k (seed 102): tracking term (deviation from min(setpoint,
  potential, rating)) +2,492 [308, 4,747] per day (better); reported
  tracking error +8,620 [6,877, 10,419] (worse); overload term +158 (n.s.);
  user term +48. The pattern holds for every seed and checkpoint.
- On TD3's own reward, arm minus TD3 final per day: Random +3,576 [1,860,
  5,344], EV2Gym RR +18,335, MPC-T +15,696, RR-TA +21 (tie), AFAP −4,802.
  The agent did not find the optimum of its own reward; the limit was
  training, state or exploration, not only the reward design.
- TD3 final vs Random (Table II metrics): energy −4.14 kWh/day, EV2Gym
  satisfaction −0.41 points, ENS_rel +2.05 points, margin −2,417 COP/day
  (all CIs exclude 0); overload and tracking error not significantly
  different.
- Facts for the text (selection rule with file and line, seed disjointness,
  budget in episodes — 60,000 steps = 625 days, 850,000 = 8,854 — the 27
  PublicPST elements, the MDP, and the fifteen checkpoints = 5 families × 3
  seeds): sheets "A4 facts" and "A4 PublicPST state".

**A5 — MPC facts.** MPC_TrackingG2V is this project's code; it minimises
Σ (station power − setpoint)² (kW²) under hard battery/departure bounds and
the transformer limit, H = 10, and returns zeros when infeasible.
MPC_EnergyMaxG2V is EV2Gym's `eMPC_G2V` with a flat price of 1.0: it
**minimises** energy subject to meeting every departure. No Dutch price
reaches any control decision. Its "+3.1 COP/day" over AFAP is +0.0053
kWh/day (−0.020 to +0.024 per case): solver tolerance.

**A6 — information table** (`ev2gym_thesis/review_information.py`; sheet
"A6 information"). EV2Gym's RR, every state that reads the setpoint
(PublicPST, ServiceState) and the setpoint-tracking controllers receive
departure, energy and next-step arrival information through the setpoint
and are not causal.

**A7 — long-dwell DNS bounds** (ratio of totals): AFAP 38.3% (lower) to
72.2% (upper); all arms 38.3-50.5% (lower), 72.2-77.7% (upper).

**A8 — facts.** Week 1 sweep (re-run, no stored rows existed): AFAP overload
0 / 0 / 0.033 / 12.5 / 32.6 kWh at 250 / 150 / 100 / 75 / 50 kW. DC peaks
(previous spawner, 1.0×): AFAP P95 199.7 kW, maximum 260.7 kW, 97/100 days
above 100 kW; RR-TA 99.9 kW every day. Week 2 outputs and every remaining
"60 kWh" (only in `.docx` deliverables): sheets "A8 week2 outputs" and
"A8 60 kWh".

## Part 3 — Block B: station-level arrivals

`ev2gym_thesis/demand/station_arrivals.py` replaces EV2Gym's spawner in the
DC regime from outside the library.
- **Stream.** Poisson count per step, λ_s = τ(clock(s)) / Στ × arrivals/day,
  τ = EV2Gym's 15-min public profile read from 05:00; inverse-CDF counts from
  one keyed uniform per step (nested streams across demand levels); each
  driver's energy drawn by the library's `spawn_single_EV` under a keyed
  seed; dwell from the lognormal (mean 42 min, CV 0.5). Identical for every
  arm (test).
- **Ports online.** First free port by index, no dead time; rejection only
  when every port is busy (test); under fixed departures the online
  assignment is asserted equal to the reset-time plan at every step.
- **Exact DNS** = (E_rejected + R_served − E_delivered) / (E_rejected +
  R_served).
- **Connection window**: exactly the sampled duration (mean 42.0 min; 14%
  of sessions last one step).
- **Calibration** (B4, `experiments/phase4_review/calibration.csv`):
  EV2Gym's weekday and weekend τ both sum to 100, so one arrivals/day per
  level serves both day types. 1.0×: 38.31 arrivals/day, 627.3 kWh/day
  (78.4 per port); 1.3×: 49.32, 814.3 (101.8); 1.6×: 60.70, 1,002.4
  (125.3). Relative error below 0.1%.

**Gate 1** (1.0×, 8 ports; V0 previous spawner, V1 station arrivals with the
old window and dead time, V2 without dead time, V3 exact window):

| | V0 | V1 | V2 | V3 |
|---|---|---|---|---|
| Rejected drivers/day | 0.88 (upper bound 21.6) | 0.83 | 0.15 | 0.05 |
| Port occupancy | 19.0% | 18.8% | 19.1% | 14.2% |
| DNS, AFAP | 2.7% | 2.9% | 1.2% | 6.4% |
| DNS, RR-TA | 5.5% | 6.7% | 5.5% | 11.8% |
| Mean f incl. rejected, RR-TA | 95.5% | 94.7% | 95.9% | 91.2% |

Capacity (RR-TA): with the dead time (V1) 8 ports fail at 1.6× and 10 pass
(the previous recommendation); without it (V2) 8 ports pass the previous
criteria at 1.6×; with the A1 criterion neither 8 nor 10 ports suffice at
1.6×; with the exact window (V3) RR-TA fails at 1.3× and 10 ports change
nothing.

**Gate 2 calibration** (gradient phase, steps/s per seed): 58.5 alone, 50.7
beside one evaluation worker, 49.0/47.8 for two seeds in parallel.

## Part 4 — Block C: fair comparison in the DC regime

*(C1-C6 complete. C3 trained 2026-11-03 18:37-22:18 UTC−5, approved by the
author, final deadline 2026-11-05 23:59, unused because every seed
converged.)*

**C1 arms.** AFAP; PS = AFAP + the safety layer
(`ev2gym_thesis/rl/safety.py`, common scaling factor, 0.999 × rating, the
only safety layer); FIX12.5 (every port at 12.5 kW); RR (EV2Gym, unchanged,
not causal); RR+S; RR-TA; Random+S; TD3_safe; MPC-soft; MPC-soft-est;
Oracle-E. MPC-T and Oracle-T are not rerun in the DC regime: they track
EV2Gym's setpoint and stay in the long-dwell regime only.

**C2 formulations** (`ev2gym_thesis/mpc/operator_mpc.py`; Δt = 0.25 h; P in
kW, E in kWh). MPC-soft at step t, horizon H = 10:

```latex
\max_{P,\sigma}\; \sum_{k=t}^{t+H-1}\sum_{i\in\mathcal{C}_k} P_{i,k}\,\Delta t \;-\; \rho \sum_{i\in\mathcal{D}} \sigma_i
\quad\text{s.t.}\quad
0 \le P_{i,k} \le P^{\max}_i\, a_{i,k},\qquad
\sum_{i} P_{i,k} \le 0.999\,P^{\mathrm{tr}}_k,
```
```latex
\sum_{k} P_{i,k}\,\Delta t \le R_i,\qquad
\sum_{k} P_{i,k}\,\Delta t \ge R_i - \sigma_i,\;\; \sigma_i \ge 0\;\; (i \in \mathcal{D}),
```

with R_i the remaining requested energy (desired − current capacity; η = 1,
so E_{i,k+1} = E_{i,k} + P_{i,k}Δt and E ≤ C reduce to the cumulative bound),
P^max_i = min(port rating 49.88 kW, EV maximum 50 kW), a_{i,k} = 1 while
EV i is connected, and 𝒟 the EVs that depart inside the horizon.
ρ = 10 (labelled): since delivered energy never exceeds the request,
σ_i = R_i − Σ_k P_{i,k}Δt at the optimum, so energy to an EV leaving inside
the horizon is worth 1 + ρ and any other energy 1 — earliest-departure
priority without lowering total energy. P = 0, σ = R is always feasible:
**0 infeasible solves** were recorded. MPC-soft-est uses only connected EVs
with departure estimated as arrival + 42 min (3 steps). Oracle-E is the same
model solved once at step 0 over the whole day with every accepted driver,
so its objective is (1 + ρ) × energy − constant: it maximises energy within
100 kW.

**C3 — TD3_safe** (`scripts/train_td3_safe.py`, design and every constant's
origin in `ev2gym_thesis/rl/config_safe.py`; selection
`results/review_td3_safe_selection.json`; analysis
`scripts/review_C3_analyze.py` → `results/review_C3_td3_safe_comparisons.csv`,
`results/review_C3_td3_safe_seeds.csv`; figure `w8_f4_td3_safe_validation`).
- *Environment:* the DC regime at 1.0× with station-level arrivals (the
  same generator as C1, training seeds drawn from [0, 10⁶), never the test
  seeds 0-49 or the validation seeds 1,000,000-1,000,009).
- *Constraint:* the safety layer of every causal arm (common scaling factor,
  0.999 × rating) is applied inside the training environment, so the agent
  learns only the allocation; the limit is never a reward term.
- *State:* `ServiceStateCausal`, 35 elements (`ServiceState` without
  EV2Gym's non-causal power setpoint) — the author's decision of
  2026-11-03. TD3_safe is therefore a causal arm.
- *Reward:* `ServedEnergyReward` = energy delivered in the step / (rating ×
  Δt); the episode return is the day's energy / 25 kWh, so the agent
  maximises energy served (equivalently minimises DNS) with no weight to
  tune.
- *Hyperparameters:* the TD3 authors' reference implementation (actor and
  critics 256-256, Adam 3·10⁻⁴, γ 0.99, τ 0.005, policy delay 2, target
  noise 0.2 clipped at 0.5, batch 256, exploration σ 0.1); learning starts
  at 10,000 steps and a 300,000-transition buffer are set for this
  project (reasons in `config_safe.py`).
- *Validation and selection (fixed before training):* every 10,000 steps,
  deterministic policy with frozen normalisation and the safety layer, on
  20 validation cells (10 seeds × {2022-01-31 weekday, 2022-03-12
  weekend}); criterion = mean energy delivered. Convergence = over 50,000-
  step windows, change of the mean < 2% and coefficient of variation < 5%
  on 3 consecutive evaluations; each run stops 100,000 steps after
  convergence. Final checkpoint = best validation value at or after
  convergence; carried model = the seed whose final checkpoint validates
  best. The test grid never enters the selection.

| Training seed | Converged at | Final checkpoint | Stopped at | Validation energy (kWh/d) | Test energy 1.0× (kWh/d) | Test DNS 1.0× | Test mean f 1.0× |
|---|---|---|---|---|---|---|---|
| 100 (carried) | 130,000 | 150,000 | 230,000 | 529.0 | 536.1 [520.5, 551.5] | 14.5% [13.6, 15.4] | 89.3% [88.6, 90.0] |
| 101 | 130,000 | 200,000 | 230,000 | 519.5 | 535.4 [520.0, 550.2] | 14.6% [13.7, 15.6] | 89.1% [88.4, 89.8] |
| 102 | 200,000 | 280,000 | 300,000 | 527.3 | 539.9 [524.6, 554.6] | 13.9% [12.9, 14.9] | 89.8% [89.1, 90.6] |

Training wall-clock 1.12 / 1.09 / 1.44 h (52-61 steps/s, one process); no
seed reached its share of the deadline. Seed 102 is marginally better on the
test grid than the carried seed 100; the carried model is not changed,
because selection uses validation only. The test path was checked to
reproduce the training validation exactly (20k checkpoint: 488.6534
kWh/day both ways).

TD3_safe (carried) minus each causal arm, test grid (kWh/day; DNS and mean f
in percentage points; n_clusters = 50):

| Level | vs RR-TA | vs PS | vs Random+S | vs MPC-soft-est |
|---|---|---|---|---|
| 1.0× energy | −16.9 [−20.1, −13.7] | −6.0 [−8.2, −3.9] | +95.9 [90.7, 101.2] | +20.5 [15.2, 25.9] |
| 1.0× DNS | +2.69 [2.18, 3.21] | +0.95 [0.61, 1.30] | −15.29 [−16.04, −14.54] | −3.27 [−4.15, −2.43] |
| 1.0× mean f | −1.89 [−2.38, −1.39] | −1.02 [−1.35, −0.70] | +12.52 [11.87, 13.17] | +4.17 [3.36, 4.99] |
| 1.3× energy | −20.7 [−24.6, −16.9] | −5.1 [−7.8, −2.5] | +111.3 [105.8, 117.0] | +12.4 [6.9, 18.0] |
| 1.6× energy | −29.4 [−34.1, −24.8] | −5.4 [−8.7, −2.1] | +120.3 [113.4, 127.4] | −1.0 [−7.4, 5.2] |

Reading. With the constraint enforced and a reward aligned with the
service metric, the agent learns a real allocation (it beats random
allocation under the same layer by 96-120 kWh/day and a causal MPC with
estimated departures up to 1.3×), but it does not find the transformer-
aware rotation: RR-TA delivers more at every level and the gap widens with
demand. The spread across the three seeds (4.5 kWh/day at 1.0×, 10.1 at
1.6×) is small against that gap, so the conclusion does not depend on the
seed. As in chapter 08 item 48,
the claim is bounded to this design (one algorithm, this state and reward,
no tuning, a budget set by the convergence rule).

**C3 follow-up — long-budget sensitivity** (approved by the author after
seeing the C3 results; rule fixed before the runs in `config_safe.py`, doc
`long_budget_sensitivity`, first at 1,000,000 steps and amended to
2,000,000 before any long-run result; `scripts/review_C3_long.py` →
`results/review_C3_long_budget.csv`, `results/review_td3_safe_long_selection.json`;
figure `w8_f5_td3_safe_long_validation`).
Seeds 100/101/102 retrained from scratch with the C3 design and no stopping
rule to 2,000,000 steps each (11.3 / 11.3 / 10.1 h; seeds 100 and 101 in
parallel); the first 230,000 steps reproduce C3 exactly (deterministic).
Two checkpoints per seed tested on the C3 test grid: the last (2M) and the
best validation value over the run (490k / 580k / 310k steps; validation
535.9 / 533.5 / 530.1 kWh/day). The carried TD3_safe model is unchanged.

| Checkpoint | 1.0× energy (kWh/d) | minus TD3_safe | minus RR-TA | minus PS | 1.6× minus RR-TA |
|---|---|---|---|---|---|
| best-validation, seed 100 (490k) | 545.8 | +9.7 [7.3, 12.1] | −7.2 [−10.0, −4.6] | +3.7 [1.7, 5.7] | −16.2 [−19.8, −12.8] |
| best-validation, seed 101 (580k) | 544.4 | +8.3 [6.0, 10.6] | −8.5 [−11.2, −5.9] | +2.3 [0.4, 4.3] | −16.7 [−21.3, −12.3] |
| best-validation, seed 102 (310k) | 541.0 | +4.9 [2.4, 7.5] | −11.9 [−14.9, −9.0] | −1.0 [−3.4, 1.2] | −28.3 [−32.6, −24.1] |
| last (2M), seed 100 | 541.3 | +5.2 [2.0, 8.3] | −11.7 [−15.0, −8.6] | — | −24.8 [−29.6, −20.2] |
| last (2M), seed 101 | 542.6 | +6.5 [3.6, 9.5] | −10.3 [−13.4, −7.2] | — | −24.9 [−29.5, −20.4] |
| last (2M), seed 102 | 540.9 | +4.8 [1.5, 8.1] | −12.0 [−14.9, −9.3] | — | −25.2 [−29.4, −20.9] |

(Every difference: paired, cluster bootstrap over the scenario seed,
n_clusters = 50, 10,000 resamples; "minus PS" for the last checkpoints and
all 1.3× rows are in the CSV.) Reading. Training longer helps a little and
non-monotonically: validation rises to a peak between 310,000 and 580,000
steps and then drifts back to the C3 plateau, so the 2M checkpoints are
worse than the best ones. The best checkpoints gain 5-13 kWh/day over the
carried model and two of them overtake PS, but **every one of the six
long-budget checkpoints stays below RR-TA at every level** (all intervals
exclude zero), none meets the mean-f target at any level (best 1.0× lower
bound 89.8%), and all keep zero overload (0 of 1,800 test days). The C3
conclusion is therefore not an artefact of the stopping rule.

**C6 master table, 1.0×** (`results/review_C_master_1.0x.csv`; 1.3× and
1.6× in `review_C_dc_comparison.xlsx`):

| Arm | Causal | Energy (kWh/d) | DNS | Mean f incl. rejected | Service level | Overload (kWh/d) | Days overload | Peak P95 / max (kW) | Margin (COP/d), diff vs RR-TA |
|---|---|---|---|---|---|---|---|---|---|
| AFAP | yes | 586.9 ± 17.8 | 6.4% [5.8, 7.1] | 95.9% [95.5, 96.3] | 88.5% | 35.9 | 98 | 228.2 / 261.1 | +19,822 [17,076, 22,792] |
| PS | yes | 542.1 ± 15.4 | 13.6% [12.7, 14.5] | 90.3% [89.6, 90.9] | 76.5% | 0 | 0 | 99.9 / 99.9 | −6,360 [−7,957, −4,799] |
| FIX12.5 | yes | 307.2 ± 10.0 | 51.0% [50.1, 51.9] | 58.2% [57.4, 59.0] | 23.7% | 0 | 0 | 86.5 / 100.0 | −143,557 |
| RR | no | 418.3 ± 19.2 | 33.3% [31.7, 35.0] | 70.5% [69.0, 72.0] | 57.8% | 18.0 | 77 | 199.5 / 232.7 | −78,659 |
| RR+S | no | 401.8 ± 18.2 | 35.9% [34.4, 37.6] | 68.5% [67.0, 69.9] | 53.6% | 0 | 0 | 99.9 / 99.9 | −88,321 |
| RR-TA | yes | 552.9 ± 16.1 | 11.8% [10.9, 12.8] | 91.2% [90.4, 91.9] | 79.9% | 0 | 0 | 99.9 / 99.9 | — |
| Random+S | yes | 440.1 ± 13.8 | 29.8% [28.8, 30.8] | 76.7% [75.9, 77.6] | 54.0% | 0 | 0 | 99.9 / 99.9 | −65,900 |
| TD3_safe | yes | 536.1 ± 15.5 | 14.5% [13.6, 15.4] | 89.3% [88.6, 90.0] | 73.6% | 0 | 0 | 99.9 / 99.9 | −9,851 [−11,765, −7,989] |
| MPC-soft | no | 581.7 ± 17.2 | 7.3% [6.5, 8.0] | 95.2% [94.6, 95.7] | 87.0% | 0 | 0 | 99.9 / 99.9 | +16,791 [14,547, 19,276] |
| MPC-soft-est | yes | 515.5 ± 16.3 | 17.8% [16.7, 18.9] | 85.1% [84.1, 86.1] | 76.5% | 0 | 0 | 99.9 / 99.9 | −21,853 |
| Oracle-E | no | 581.7 ± 17.2 | 7.3% [6.5, 8.0] | 95.2% [94.7, 95.7] | 87.2% | 0 | 0 | 99.9 / 99.9 | +16,788 |

Oracle-E dominates every causal arm on every case (test; RR-TA max(arm −
Oracle-E) = −0.011 kWh). MPC-soft and Oracle-E differ by at most 0.1 kWh
per case (numerical). Targets (mean f CI low ≥ 90%, DNS CI high ≤ 15%, zero
overload days): at 1.0× RR-TA, MPC-soft and Oracle-E meet all three; at
1.3× and 1.6× only the non-causal MPC-soft and Oracle-E meet the service
targets with the transformer respected. TD3_safe meets the overload target
at every level and neither service target at any level (its mean-f upper
bound at 1.0× is 90.0%).

**C4 — capacity and infrastructure** (`results/review_C4_summary.csv`,
`results/review_C4_comparisons.csv`). Criteria (labelled): a configuration
meets when the exact-DNS upper bound is ≤ 15% and the mean-f lower bound is
≥ 90%; a transformer suffices for an arm when the arm's maximum daily peak
over the 100 days does not exceed its rating (P95 reported beside it).
ET-013 sizes at PF 0.894: 112.5 / 150 / 225 / 300 / 400 kVA = 100 / 134.2 /
201.2 / 268.3 / 357.8 kW. "112.5 kVA unit" = the 100 kW reference rating
(labelled).

| Question | Answer |
|---|---|
| Capacity threshold, 112.5 kVA, RR-TA | 40.22 arrivals/day = 659 kWh/day (≈ 1.05×), identical at 8 and 10 ports |
| Capacity threshold, 112.5 kVA, PS | 36.60 arrivals/day = 596 kWh/day, identical at 8 and 10 ports |
| Criterion that breaks first | mean f (both arms); DNS is still below 15% at the threshold |
| 1.6× (1,002 kWh/day) with 112.5 kVA | no port count (8, 12, 14, 16) meets, for RR-TA or PS: power binds, not ports |
| 1.6× with 8 ports, transformer needed | RR-TA: 150 kVA (DNS 11.2%, mean f 92.1%); PS: 225 kVA (DNS 8.7%, f 94.0%; 150 kVA fails) |
| AFAP at 8 ports, transformer by maximum peak | 300 kVA at 1.0× (peak 261.1 kW); 400 kVA at 1.3× (299.3 kW) and 1.6× (349.2 kW); by P95: 300 kVA up to 1.3× |
| EV2Gym RR at 1.6× | needs 400 kVA (peak 270-273 kW) and still fails the service targets at 8-16 ports |
| Under D3 (22 kWh per session) | neither RR-TA nor PS meets the targets even at 19.15 arrivals/day (0.5×, 434 kWh/day; the bisection floor) |

RR-TA against the feasible alternatives (paired, per day):
- vs FIX12.5: +245.7 kWh [236.5, 254.8] and +143,557 COP [138,193,
  148,893] at 1.0×; +334.7 kWh and +195,567 COP at 1.6×.
- vs AFAP on a 300 kVA unit (no overload at 1.0×; 2/100 days at 1.3×,
  10/100 at 1.6×): −33.9 kWh [−39.0, −29.2] at 1.0×. **Cost of respecting
  the 112.5 kVA unit: 19,822 COP/day [17,076, 22,792], 5.8% of AFAP's
  margin** at 1.0×; 41,580 COP/day (9.3%) at 1.3×; 66,242 COP/day (12.1%)
  at 1.6×.

**C5 — voltage** (`results/review_C5_voltage_summary.csv`; node_123 as
shipped, the 8 ports on bus 115, weekday, 50 seeds, `simulate_grid = True`,
station-level arrivals; one case per seed, so the seed is the resampling
unit). The station bus is the feeder's lowest bus. Mean minimum voltage
with the station idle: 0.97715 p.u. at 1.0× and 0.97688 at 1.6×. The
station lowers the minimum by 0.00015 p.u. [0.00012, 0.00017] (AFAP, 1.0×)
and 0.00020 [0.00017, 0.00023] (AFAP, 1.6×); PS and RR-TA by 0.00013-0.00018
p.u. **0 of 50 cases** fall outside 0.95-1.05 p.u. (EV2Gym's criterion) or
0.90-1.10 p.u. (CREG 024 de 2005), feeder-wide or at the station bus, for
every arm and level. The differences are statistically distinguishable from
zero but physically negligible: about 0.4% of the ±5% band's half-width.
node_123 is a test feeder, not a Colombian one.

## Part 5 — Block D: DC sensitivities

Each sensitivity is paired with the C1 base run of the same arm, level,
seed and day (`results/review_D_summary.csv`; differences with 95% cluster
intervals; "meets" = DNS upper bound ≤ 15% and mean-f lower bound ≥ 90%;
zero overload holds for PS and RR-TA in every run).
- **D1 — load-dependent departure.** A driver whose sampled dwell has ended
  stays while the battery is below the desired level, at most 90 minutes
  after arrival (EV2Gym's `is_departing` wrapped from outside: it is
  evaluated after the step's charge). Ports are assigned online; a port whose
  driver may still stay is treated as busy (conservative).
- **D2 — 5-minute step** (288 steps; dwell rounded to 5 min; EV2Gym's median
  filter rescales itself). The stream is drawn per 5-minute step, so its
  offered energy differs slightly from the 15-minute stream (615 vs 627
  kWh/day at 1.0×).
- **D3 — 22 kWh per session.** Every driver's requested energy is scaled by
  1.3553 (calibrated so that the 1.0× stream's mean is 22.0 kWh, capped at
  battery − 15 kWh); arrivals/day unchanged, so offered energy rises 35%.

| Sensitivity | Level | Arm | DNS (base; difference) | Mean f incl. rejected (base) | Port occupancy (base) | Offered kWh/day | Meets service targets |
|---|---|---|---|---|---|---|---|
| D1 | 1× | AFAP | 0.3% (base 6.4%; diff -6.2 [-6.8, -5.5]) | 99.8% (base 95.9%) | 15.0% (base 14.2%) | 627 | yes |
| D1 | 1× | PS | 1.2% (base 13.6%; diff -12.4 [-13.3, -11.5]) | 99.0% (base 90.3%) | 16.8% (base 14.2%) | 627 | yes |
| D1 | 1× | RR-TA | 2.1% (base 11.8%; diff -9.7 [-10.6, -8.8]) | 98.3% (base 91.2%) | 16.5% (base 14.2%) | 627 | yes |
| D1 | 1.6× | AFAP | 1.5% (base 6.7%; diff -5.1 [-5.7, -4.5]) | 98.6% (base 95.6%) | 23.6% (base 22.5%) | 1,002 | yes |
| D1 | 1.6× | PS | 7.1% (base 20.4%; diff -13.3 [-14.0, -12.5]) | 93.5% (base 84.6%) | 28.4% (base 22.5%) | 1,002 | yes |
| D1 | 1.6× | RR-TA | 9.2% (base 18.0%; diff -8.7 [-9.4, -8.1]) | 91.9% (base 85.8%) | 28.2% (base 22.5%) | 1,002 | yes |
| D2 | 1× | AFAP | 5.4% (base 6.4%; diff -1.0 [-1.8, -0.3]) | 96.7% (base 95.9%) | 13.8% (base 14.2%) | 615 | yes |
| D2 | 1× | PS | 12.1% (base 13.6%; diff -1.5 [-2.7, -0.3]) | 91.5% (base 90.3%) | 13.8% (base 14.2%) | 615 | yes |
| D2 | 1× | RR-TA | 9.0% (base 11.8%; diff -2.8 [-4.0, -1.6]) | 93.9% (base 91.2%) | 13.8% (base 14.2%) | 615 | yes |
| D2 | 1.6× | AFAP | 6.0% (base 6.7%; diff -0.7 [-1.4, -0.0]) | 96.1% (base 95.6%) | 21.4% (base 22.5%) | 961 | yes |
| D2 | 1.6× | PS | 18.7% (base 20.4%; diff -1.7 [-2.8, -0.6]) | 86.1% (base 84.6%) | 21.4% (base 22.5%) | 961 | no |
| D2 | 1.6× | RR-TA | 13.7% (base 18.0%; diff -4.2 [-5.3, -3.2]) | 90.1% (base 85.8%) | 21.4% (base 22.5%) | 961 | no |
| D3 | 1× | AFAP | 12.4% (base 6.4%; diff +5.9 [+5.6, +6.3]) | 91.7% (base 95.9%) | 14.2% (base 14.2%) | 849 | yes |
| D3 | 1× | PS | 21.8% (base 13.6%; diff +8.2 [+7.9, +8.5]) | 83.8% (base 90.3%) | 14.2% (base 14.2%) | 849 | no |
| D3 | 1× | RR-TA | 19.9% (base 11.8%; diff +8.0 [+7.6, +8.5]) | 85.0% (base 91.2%) | 14.2% (base 14.2%) | 849 | no |
| D3 | 1.6× | AFAP | 12.5% (base 6.7%; diff +5.8 [+5.6, +6.1]) | 91.4% (base 95.6%) | 22.5% (base 22.5%) | 1,357 | yes |
| D3 | 1.6× | PS | 29.9% (base 20.4%; diff +9.5 [+9.3, +9.8]) | 76.4% (base 84.6%) | 22.5% (base 22.5%) | 1,357 | no |
| D3 | 1.6× | RR-TA | 27.8% (base 18.0%; diff +9.8 [+9.4, +10.2]) | 77.7% (base 85.8%) | 22.5% (base 22.5%) | 1,357 | no |

Reading. **The fixed-departure assumption drives the DC service gap.**
When drivers stay until charged (up to 90 min), RR-TA and PS meet both
service targets up to 1.6× with 8 ports and the 100 kW unit, and PS
overtakes RR-TA. The 5-minute step helps RR-TA most (finer rotation) but
does not change which levels pass. Rescaling sessions to 22 kWh raises DNS
by 8-10 points for the managed arms; RR-TA then fails even at 1.0×. Under
D3 neither RR-TA nor PS meets both targets at any level the bisection
evaluated, down to its floor of 0.5× (19.15 arrivals/day, 434 kWh/day):
no capacity threshold exists in range (`results/review_C4_summary.csv`).


## Part 6 — Implementation

New modules: `ev2gym_thesis/demand/station_arrivals.py`,
`ev2gym_thesis/demand/review_configs.py`, `ev2gym_thesis/metrics/service.py`,
`ev2gym_thesis/mpc/operator_mpc.py`, `ev2gym_thesis/review_information.py`,
`ev2gym_thesis/review_labels.py`; additions to `stats_utils.py`
(`cluster_bootstrap_ratio`), `xlsx_export.py` (multi-sheet export),
`rl/config_safe.py` (dc42 = station arrivals, selection and carried-model
rules, `enable_regime`), `rl/state_service.py` (`ServiceStateCausal`).
Scripts: `review_gate0_timing.py`, `calibrate_station_arrivals.py`,
`review_dc.py`, `review_gate1*.py`, `review_A_*.py`, `review_A2_A3.py`,
`review_A8_*.py`, `review_C_run.py`, `review_C4_*.py`, `review_C5_voltage.py`,
`review_C6_tables.py`, `review_C_workbook.py`, `review_D_*.py`,
`build_paper_tables.py`, `review_figures.py`, `review_numbers.py`,
`train_td3_safe_chain.py`, `select_td3_safe.py`. Tests:
`test_station_arrivals.py` (9), `test_review_A.py` (6), `test_review_C.py`
(5). Nothing in `ev2gym/` was modified.
