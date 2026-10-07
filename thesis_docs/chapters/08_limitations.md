# Chapter 8 — Consolidated Limitations (Weeks 1–7)

This chapter is the single list of the thesis's declared limitations, for
the final document. **Labelled assumption (2026-10-05):** no consolidated
list existed before Week 7; each chapter kept its own section. This file
gathers them, groups them by kind and points to the section with the full
argument. Items marked **[W7]** are new in the final practical phase, and
items marked **[corrected]** replace an earlier statement that was wrong.

## L1. Scenario and data realism

1. **Arrival, departure and energy-demand distributions are EV2Gym's Dutch
   public-charging data**, not Colombian sessions. This holds in Bogotá and
   in Medellín alike (07 S7.2); no Colombian session-level dataset was
   available.
2. **One station design.** The station has 8 ports at 50 kW and one 100 kW
   transformer (4:1 oversubscription). Its port count is grounded in the
   Enel X inventory, but the DC hardware is a modelling assumption
   (01 §1.4). The guidelines are about this design and are not general.
3. **Fleet specification.** The fleet is homogeneous, with 70 kWh
   batteries. **[W7, corrected]** Some documents state 60 kWh: the Week 1
   Word handback, the external Progress Log and §8.1.4 of the corrected
   in-repo Progress Log. The configuration has always used 70 kWh, and the
   author must correct those documents (overnight report, Checkpoint 1a).
4. **Connector standard.** The station uses CCS Combo 2 only. Res. 40223 de
   2021, Art. 4, requires at least one Tipo 1 (AC) connector and at least
   one CCS Combo 1 connector on Level 3 DC stations. A CCS2-only DC station
   does **not** by itself satisfy it. The choice is a market-practice
   simplification, and it has no effect on any simulated quantity (05
   S5.3; 06 S6.4).
5. **Evaluation scope.** 50 scenario seeds × 2 representative day types,
   with one weekday and one weekend representative, which is provably
   lossless for the EV population (05 S5.2). It is not a calendar-year
   study.
6. **Climate.** The Week 2 Bogotá ambient-temperature degradation model is
   uncited in parts (02, residual limitations) and is not part of the main
   grid. It was not transferred to Medellín (07 S7.2).

## L2. Economics

7. **Flat tariffs only.** The Colombian tariff gives no intraday price
   signal worth exploiting: the Punta / Fuera de Punta spread is 1.57% in
   Bogotá and 0.69% in Medellín. Margin is therefore proportional to energy
   delivered, and it cannot discriminate between strategies except through
   energy (05 S5.1; 07 S7.3). *Closure (2026-10-06):* this is now stated
   as Proposition 7.1, with proof (07 S7.3a). It holds exactly only under
   a flat tariff. Air-e (Barranquilla) publishes a 10% two-band Nivel 2
   option under which it does not hold exactly (07 S7.7; item 31).
8. **Retail price.** Bogotá's 1,450 COP/kWh is a single Enel figure from
   August 2025, paired with a 2026 cost, so margins are lower bounds.
   **[W7]** Medellín's retail EV price is not published by EPM. Bogotá's
   value is used there as a labelled sensitivity, so **no absolute claim
   about Medellín's margin** is made (07 S7.1).
9. **[W7, corrected]** S5.1 and S5.8's cost of the transformer limit (503.9
   COP/day) came from a stale pre-Gate-4 CSV. The value on the current
   analysis rows is 551.9 COP/day, CI [274, 874] (05 S5.8 correction note).

## L3. Algorithms and learning

10. **MPC_TrackingG2V, MPC_EnergyMaxG2V and both oracles are non-causal.**
    They know departure times or the whole day. They are
    value-of-information bounds, not deployable options (05 S5.5).
11. **RL training budget and compute.** Training ran on a laptop CPU. The
    final model trained for 910,000 steps (2.2–3.7 h per seed), against
    5–48 h on HPC in the source papers; no equivalence is claimed (05
    S5.11).
12. **Reward–metric misalignment.** The training reward values user
    satisfaction alongside tracking. Extended training improved that reward
    and worsened tracking error, a misalignment measured directly in 05
    S5.11 and declared since 03 S3.10.
13. **Pre-fix training.** The Week 3–5 RL models were trained with the
    pre-fix `generate_power_setpoints` and evaluated after the fix (05
    S5.11).
14. **Only `TD3_vanilla` was extended.** `TD3_TrackingOnly` was not, and no
    claim is made about whether its gap is a budget artefact (05 S5.11).
15. **Convergence rule thresholds are empirically set.** "Converged" means
    the validation criterion stopped changing, not that the policy improved
    (05 S5.11).

## L4. Grid and voltage [W7]

16. **The feeder is EV2Gym's 34-node network (RL-ADN)**, called IEEE 34-bus
    by the library. It is not validated against the IEEE published data,
    and it stands in for an Enel or EPM feeder, none of which is public (06
    S6.1).
17. **Station placement is a labelled assumption.** The station sits on bus
    27, the electrically farthest and most voltage-sensitive bus, and is
    placed there by a wrapper because EV2Gym has no placement key (06
    S6.1).
18. **Voltage is stated exactly as Step 1d left it.** The ±5% metric trips
    on this feeder from `load_multiplier` 0.8 upwards, and at the nominal
    load it trips **even with the station idle** (15 of 20 probe cells).
    The feeder itself is outside the band at bus 27. Voltage results are
    therefore reported only as the **station's increment over the
    idle-station run of the same cell**. **No absolute RETIE compliance
    claim is made for the feeder or the station** (06 S6.2, S6.5). The
    Colombian regulatory source of the ±5% band is the thesis's adopted
    target and is not re-verified in Week 7.
19. **Background load and PV come from EV2Gym's generator and Dutch PV
    data.** Growing the station's demand (Axis 1) also resamples the
    feeder's background draw for the same seed, because the EV population
    consumes random numbers before the grid samples its load. Axis 1
    voltage effects are therefore attributed within each cell against its
    own idle baseline, never across settings (06 S6.5).
20. **No feedback from the feeder to the station.** In EV2Gym the feeder's
    voltage never curtails the station, and the station transformer does
    not see the bus's background load. Raising the feeder load (Axis 2)
    therefore leaves every station metric exactly unchanged; only the
    voltage changes. A real operator could curtail charging, and a shared
    transformer would carry other customers' load. Axis 2 results are
    therefore voltage-only (06 S6.4).
21. **Transformer sizing from 50 seeds is directional for the tail.** The
    95th percentile rests on 2–3 tail seeds (06 S6.4). *Correction
    (2026-10-06, closure A.4):* sizing figures are now converted at
    pf 0.894, derived from CREG 015/2018, and at unity power factor. They
    are mapped to Enel's ET-013 standard ratings, and both readings give
    225 kVA for AFAP (item 29).

## L5. Replicability [W7]

22. **Only the tariff is city-specific and available.** Arrivals, demand
    level, feeder and climate are the same declared stand-ins in every
    city, so the physical results are conditional outside Bogotá, not
    established (07 S7.2, S7.6, S7.9). *Closure:* extended to all six
    categoría especial cities (07 S7.7).
23. **Demand mapping is not defended by any source.** City-level EV
    registrations (Medellín / Bogotá = 0.40, January–August 2025) do not
    give per-station demand. Both naive mappings fall below the 1.0–1.6×
    range studied (07 S7.4). *Closure (2026-10-06):* lower-demand stations
    are now covered down to 0.5× (07 S7.8). No city is mapped onto the
    axis, because there is still no per-station source.
24. **EPM's Fuera de Punta CU** satisfies the component-sum invariant only
    at the inclusive 0.01 COP/kWh rounding bound (07 S7.1).

## L6. Closure brief findings and limitations [closure, 2026-10-06]

25. **Arrivals at a full station are silently dropped by EV2Gym.** An
    arrival drawn for an occupied port is never created
    (`utils.py::EV_spawner`, lines 490 and 531–537). Every registry metric
    therefore covers served EVs only. This includes satisfaction,
    `ENS_rel` and EVs served. Demand not served, which counts rejected
    arrivals, is a post-processing reconstruction
    (`ev2gym_thesis/demand/censoring.py`) with three labelled
    assumptions:
    - a lower bound (rejected drivers would have taken any free port);
    - an upper bound (every blocked draw is a lost customer);
    - each rejected arrival requests the day's mean requested energy.

    On the lower bound, Round Robin fails the 15% target from 0.733×
    (06, Guideline 2). **Every Week 7 statement that satisfaction "is
    unchanged" or "never below 90%" is withdrawn** as a statement about
    the station's users.
26. **Arrivals are drawn per port.** In EV2Gym, more ports also means more
    potential arrivals. Port comparisons are therefore reported at
    constant station demand (spawn multiplier × 8/P) as the primary
    reading, and as run as a secondary reading (06, C2).
27. **Demand levels are quantised.** The spawn multiplier is rounded, so
    "0.75×" is 0.733× (spawn 22). The constant-demand variants use
    non-integer multipliers (17.6, 14.67, 24, 20), which EV2Gym accepts
    because the multiplier enters only as a factor (`utils.py`, line 538).
28. **Port counts above 12 were not simulated.** The number of ports that
    keeps DNS below 15% at 1.3–2.5× is not stated. The RL policy cannot
    run other port counts, because its observation and action spaces are
    fixed at 8, so it is absent from C2.
29. **Power factor.** The 0.894 used for kVA is derived from CREG 015/2018's
    50% reactive-energy threshold. The compiled text places that clause
    next to a "Legislación Anterior" note, which is a verification caveat.
    Recommended ratings are stated at both 0.894 and unity power factor.
    The operator's ET-013 list is used as the set of standard ratings.
    NTC 819 (ICONTEC) is paywalled and was not consulted.
30. **City tariffs.**
    - EMCALI's latest retrievable sheet is January 2026.
    - The EMCALI charging price (2,500 COP/kWh) is from the press.
    - EPM, Air-e and Afinia publish no per-kWh charging price.
    - ESSA prices per a unit not defined in kWh.
    - Afinia's Nivel 2 two-band row is identified indirectly.

    Absolute margins outside Bogotá are therefore sensitivities, not
    claims (07 S7.7).
31. **Two-band tariffs break exact ranking invariance.** Proposition 7.1
    holds only for a flat (monomial) tariff. Under Air-e's 10% two-band
    option, Round Robin's cost of the limit is 3.6× its flat value, and
    the margin ranking shifts in 12 of 22 positions (07 S7.7).
32. **Lower demand is monotone on average, not per cell.** 18 of 100 cells
    show higher DNS at 0.5× than at 0.733× under Round Robin. No city can
    be mapped onto the demand axis, because no per-station demand source
    exists (07 S7.8).
33. **The 37% voltage reduction is a base-setting figure.** It is the
    ratio of mean drops in the feeder-wide daily minimum voltage relative
    to the idle station: 36.4% [22.3, 47.0]. At 1.3× and 1.6× demand it is
    24.7% and 22.7% (06, Guideline 3).
34. **Feeders.** Of EV2Gym's four shipped networks:
    - node_34 is out of band when idle;
    - node_25 and node_69 cannot run as shipped, because their bus files
      have no nominal loads;
    - node_123 is in band when idle.

    The AFAP and Round Robin voltage runs on node_123 cover the weekday
    evaluation day only. On the weekend day, EV2Gym's background-load
    generator loops until a 123-bus sample has no NaN, and it did not
    finish within 240 s. MPC, the RL model and the oracle were not rerun
    there, as the brief scopes the rerun to AFAP and RR. The ±5% result on
    node_123 (met by both, with a 0.022 p.u. margin) concerns a test
    network, not a Colombian feeder (06, Guideline 3).
