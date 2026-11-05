# Response to the advisor review of 2026-11-01 (draft, 2026-11-03)

Point by point, in the review's numbering. "Done" means implemented and
measured in this repository; "Text" means a change the author makes in the
article; numbers come from `thesis_docs/review_2026-11-01_numbers.md` and
the method is in
`thesis_docs/Week8_Advisor_Review_Parameter_Method_and_Implementation_Justification.md`
(cited below as "handback").

**3.1 Incomplete abstract, limitations, conclusions, references.** Text.
The consolidated limitations now include the Week 8 items
(`thesis_docs/chapters/08_limitations.md`, L10, items 50-56).

**3.2 Objectives vs results.** Done (comparison against feasible
alternatives) + Text. The general objective is now answered against two
alternatives a real station could use, not against an overloading AFAP:
- a fixed 12.5 kW per port (FIX12.5): RR-TA delivers 552.9 vs 307.2
  kWh/day at 1.0× and 143,557 COP/day more margin;
- a larger transformer with unmanaged charging (AFAP on 300 kVA, which
  does not overload at 1.0×): RR-TA delivers 33.9 kWh/day less; respecting
  the 112.5 kVA unit costs 19,822 COP/day, 5.8% of that margin.
The cost of respecting the 100 kW unit against unmanaged charging is
19,822 COP/day [17,076, 22,792] at 1.0×.

**3.3 EV2Gym's satisfaction measures the battery level.** Done. Confirmed:
s = current / desired capacity = 1 − (R/C)(1 − f). Energy satisfaction f
(rejected drivers at 0) and the service level (f ≥ 0.9) are implemented
(`ev2gym_thesis/metrics/service.py`) and reported for every arm in both
regimes; EV2Gym's metric is kept as `ev2gym_battery_level_satisfaction`.
Your identity check holds on every arm within 0.1 points. Labelled
assumption: the 90% target applies to the mean of f including rejected
drivers. Consequence: in the long-dwell regime no arm meets it (≈ 60% once
rejected drivers count; the ports bind).

**3.4 The final RL agent does not beat the random policy.** Done (diagnosis
and a new agent, C3).
- Your hypothesis holds: from 60k to 850k steps the deviation from
  min(setpoint, potential, rating) improved by 2,492 [308, 4,747] per day
  while the reported tracking error worsened by 8,620 [6,877, 10,419]; same
  for every seed and checkpoint. The reported metric is not the optimised
  one.
- On its own reward the agent is beaten by the random policy (+3,576 per
  day [1,860, 5,344]), EV2Gym RR (+18,335) and MPC-T (+15,696): it did not
  reach the optimum of its own reward, so the sentence "the limit is the
  reward, not the budget" is withdrawn.
- Your scale estimate of the overload term (−1,432 per day) used the
  registry's overload as kWh; it is kW summed over steps (3.10 below), so
  the term is −358 per day. Your conclusion that the satisfaction term is
  the smallest stands (−60 per day for the final model).
- TD3 final vs Random: worse on energy, EV2Gym satisfaction, ENS_rel and
  margin (CIs exclude 0); overload and tracking error not different.
- Selection rule with file and line, seed disjointness (validation seeds
  ≥ 1,000,000 are unreachable by training draws; test seeds are rejected by
  a guard), scenarios vary by seed (dates add nothing), budget in episodes
  (625 / 8,854 days), the 27 state elements: handback A4.
- New agent, TD3_safe (DC regime, safety layer, causal state, reward =
  energy delivered; selection rule fixed before training, validation only):
  it beats the random policy under the same safety layer by +95.9 kWh/day
  [90.7, 101.2] at 1.0× (DNS −15.3 points), never overloads, but stays
  below RR-TA (−16.9 kWh/day [−20.1, −13.7] at 1.0×, −29.4 at 1.6×) and
  slightly below PS. The three training seeds agree within 4.5 kWh/day.
  Handback C3.
- More training does not change this (pre-registered sensitivity, 2,000,000
  steps per seed, no stopping rule): the best checkpoint gains 9.7 kWh/day
  [7.3, 12.1] over TD3_safe and still delivers 7.2 kWh/day [−10.0, −4.6]
  less than RR-TA at 1.0×; all six long-budget checkpoints stay below
  RR-TA at every level, with zero overload. Handback C3 follow-up.

**3.5 The comparison is not yet fair.** Done for the DC regime. One safety
layer (common scaling factor, 0.999 × rating) for every causal arm; PS,
FIX12.5, RR+S and Random+S added; an MPC with the operator's objective and a
soft departure constraint (never infeasible: 0 infeasible solves) and an
energy oracle (Oracle-E, the upper bound on energy within 100 kW: 581.7
kWh/day at 1.0×). MPC-T and Oracle-T stay in the long-dwell regime. TD3 is
retrained in the DC regime with the hard constraint (TD3_safe: 536.1
kWh/day at 1.0×, zero overload, below RR-TA's 552.9).

**3.6 Causality and the value of departure times.** Done. Information
table (handback A6). EV2Gym's RR and every agent whose state reads the
setpoint are not causal. MPC-soft minus MPC-soft-est (same model, true vs
estimated departures and no look-ahead) = 66.1 kWh/day at 1.0×: the value
of knowing departure times, reported as such, not as a bound.

**3.7 MPC and RL formulation.** Done (handback C2 LaTeX; A4 MDP facts).
MPC-E minimises energy subject to meeting departures; it receives a flat
price, no Dutch price reaches any decision; its +3.1 COP/day is +0.0053
kWh/day of solver tolerance.

**3.8 1.6× is not +60%.** Done. Demand levels are now defined by offered
energy with station-level Poisson arrivals: 627 / 814 / 1,002 kWh/day.
The 45-minute dead time is 30 minutes (2 steps) measured; removing it and
the per-port draws, the 10-port recommendation at 1.6× disappears (it was
an artefact of the dead time). A further finding: the previous DC sessions
were connected 15 minutes longer than labelled; with the exact window the
port count stops binding and the transformer binds. New thresholds (8 or 10
ports, 112.5 kVA): RR-TA 40.2 arrivals/day = 659 kWh/day, PS 36.6 = 596;
at +60% RR-TA needs a 150 kVA unit with the same 8 ports, unmanaged charging
400 kVA.

**3.9 Table IV row.** Done. The margin and the DNS of the RR 14-port row
are mutually consistent; the offered demand is 1,009.5 kWh/day, not 911:
the "constant demand" scaling only held at 10 ports. Tables are now built
from the registries (`scripts/build_paper_tables.py`) with a consistency
test.

**3.10 Statistical rigour.** Done. One rule: ratio of totals inside every
resample; your three discrepancies are exactly that effect (75.50 → 75.86%,
2.67 → 2.84%, 34.29 → 38.28%). Every table states the interval method,
resampling unit, n_clusters and number of resamples; intervals are per
comparison throughout. New: **EV2Gym's overload is in kW summed over
steps**, 4 × the kWh at 15-minute steps; all overload energies in the
article must be divided by 4.

**3.11 DC session model.** Done (Block D). (1) Load-dependent departure
(stay until charged, cap 90 min): the largest effect — RR-TA's DNS at 1.6×
falls from 18.0% to 9.2% and it meets both service targets up to 1.6× with
8 ports and 100 kW; PS overtakes RR-TA. Your concern was right: fixed
departures overstate the managed arms' energy not served. (2) 5-minute step:
RR-TA's DNS falls 2.8 points (1.0×) and 4.2 points (1.6×); no level changes
status. (3) 22 kWh per session: DNS +8 to +10 points for the managed arms;
RR-TA fails at 1.0×, and neither RR-TA nor PS meets the targets even at
0.5× (19.2 arrivals/day, 434 kWh/day).

**3.12 Grid, transformer, regulation.** Done + Text. On node_123 with the
station on bus 115 (the feeder's lowest bus), the station lowers the minimum
voltage by 0.00015 p.u. (1.0×) to 0.00020 p.u. (1.6×) under unmanaged
charging; 0 of 50 cases leave 0.95-1.05 or 0.90-1.10 p.u., feeder-wide or at
the station bus, for AFAP, PS and RR-TA. Statistically non-zero, physically
negligible. Why 100 kW: the Week 1 sweep had no stored rows; re-run: AFAP
overload 0 / 0 / 0.033 / 12.5 / 32.6 kWh at 250 / 150 / 100 / 75 / 50 kW,
so 100 kW is the largest rating at which unmanaged charging overloads (the
problem was built so the transformer binds). P95 vs maximum peak: both are
now reported. Citations (CREG 024/2005, RETIE 40284/2026, NTC 1340, power
factor note, kVA in Table I): Text.

**3.13 Economic assumptions.** Text (retail price source). The cost of the
limit scales with (p − c), so a 1,690 COP/kWh price multiplies absolute
margins and costs by 1.41 and leaves shares unchanged.

**3.14 Writing and references.** Text.

**3.15 Minor details.** The fifteen TD3 checkpoints are TD3_vanilla,
TD3_TrackingOnly, extended (rule-selected), extended (last) and new-run 60k,
each × 3 seeds (handback A4). The 850k checkpoint exists only for seed 102.
