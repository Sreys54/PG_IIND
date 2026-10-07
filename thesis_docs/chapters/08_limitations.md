# Chapter 8 — Consolidated Limitations (Weeks 1–7 and final capacity brief)

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
   *[corrected 2026-10-07, final capacity brief]* An 8-port site is not
   larger than what Enel deploys: Enel's upgraded Unicentro Bogotá site
   serves up to 10 vehicles simultaneously (Blu Radio, 2026; item 42).
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

## L7. Session duration and the DC capacity model [final capacity brief, 2026-10-06]

35. **Weeks 1–7 used Dutch AC session durations.** EV2Gym draws each
    connection from the `public` column of
    `ev2gym/data/mean-session-length-per.csv`. That is ElaadNL data on Dutch
    public charging, with means of 2.8–12.5 h by arrival time
    (`utils.py::spawn_single_EV`, lines 232–240). Each draw is floored at
    `min_time_of_stay` = 200 min and has 2 steps added (lines 251–252 and
    336–338). The spawner never reads the charger's power or type.
    - The simulated mean is **300.6 min [296.5, 304.7]**, and no session is
      shorter than 225 min. That is 7.2 times the 42-minute paid DC
      reference (results/dwell_a_session_summary.csv; Checkpoint A).
    - **The Weeks 1–5 algorithm comparison (05) and the Week 7 and closure
      capacity results (06, Guideline 2 and C3) all rest on these
      durations.** They were not rerun. The closure's capacity results are
      kept as a declared sensitivity, and the capacity guideline now uses
      the DC model (06 S6.6).
36. **The DC session duration is an external reference, not Colombian
    data.** The central value is 42 min, the mean of 1,412,050 paid US DC
    sessions, 2020–2023, excluding Tesla (U.S. Department of Energy [DOE],
    2023). The bracket is:
    - low, 32 min: self-reported, California (Hardman, 2026);
    - high, 78 min: free US sessions (U.S. DOE, 2023).

    The CV of 0.5 is a labelled assumption, supported by the survey's
    per-activity SDs (Hardman, 2026, Supplemental Information, Table 3).
    Enel publishes no per-session statistics. Its own figures are
    statements, not distributions: 50% in 25–30 min and full in a little
    over an hour at Unicentro (Blu Radio, 2026), and about 1 h 30 min to
    100% (Enel Colombia, 2024). That last page could not be saved; it was
    bot-blocked and the Internet Archive was offline. The US fleet and
    charger mix differ from Bogotá's.
37. **Energy per session is not rescaled.** EV2Gym's energy requested comes
    from the Dutch per-arrival demand table (12.3–21.6 kWh means), drawn as
    Normal(e, 0.5e). The homogeneous 70 kWh battery only caps it and sets
    the arrival state of charge. The simulated mean is 15.0 kWh (Dutch,
    1.0×) and 16.1 kWh (DC, 42 min). That is 27–32% below the 22.0 kWh paid
    DC reference (U.S. DOE, 2023), so DC demand per session is understated.
38. **How the DC model is applied.** The transform
    (`ev2gym_thesis/demand/dc_sessions.py`) rewrites departures inside
    EV2Gym's spawner, from outside the library:
    - arrivals that the Dutch population already had keep their energy
      bitwise;
    - arrivals that exist only because ports now free up draw their energy
      from the library under a keyed RNG.

    Three properties of the simulator remain:
    - **15-minute resolution.** A 42-minute session is simulated as 3 steps
      (45 min), a ±7.5-minute resolution (±18%). At 32 minutes, 29% of
      sessions are a single step.
    - **A 3-step port cooldown.** A port takes a new arrival only after 3
      free steps (45 min; `utils.py`, lines 534–536). This is kept as the
      library's behaviour. It is conservative, because it overstates the
      ports needed.
    - **The setpoint guard.** For 1-step sessions only, the power setpoint
      is computed as if the session lasted 2 steps, to avoid a library
      crash. This affects the tracking target and EV2Gym's Round Robin.
39. **EV2Gym's Round Robin follows the power setpoint, not the
    transformer.** It charges ceil(setpoint / port power) EVs
    (`heuristics.py`, lines 58–77). The setpoint is each EV's requested
    energy × 1.8, spread over its stay and median-smoothed over 5 steps.
    - **Under Dutch durations** the setpoint stays below 100 kW. That is
      why Round Robin showed zero overload in Weeks 1–7, and why it
      delivered almost all the energy.
    - **Under DC durations** the median filter erases short-session spikes,
      so Round Robin under-delivers and still overloads (06 S6.6).
    - **The Weeks 1–7 statement "Round Robin keeps the 100 kW transformer
      within its rating" is therefore conditional on long stays.** It is a
      property of the setpoint, not of a transformer-aware policy.
    - The diagnostic `RoundRobin_TransformerCapped`
      (`ev2gym_thesis/heuristics.py`) is the same allocation with the
      rating as its budget. It was added by this brief and was not part of
      the Weeks 1–7 comparison.
40. **The final RL model is out of its training distribution under DC
    durations.** It was trained on Dutch durations. It was evaluated under
    the transform without retraining, and every row is labelled
    `out_of_training_distribution=dc_session_durations`. Its DC results
    are not evidence about RL under DC charging.
41. **The demand multiplier is not comparable across session models.**
    EV2Gym's arrivals are drawn per port, and blocked draws are lost. The
    same `spawn_multiplier` therefore offers a different number of
    arrivals under long and short stays. At 1.0× that is 22.3 arrivals and
    327 kWh/day (Dutch) against 38.9 arrivals and 627 kWh/day (DC, 42 min)
    (`results/dwell_d_physical_units.csv`). For this reason every
    threshold is stated in physical units (06 S6.6; 07 S7.4).
42. **[corrected] Site size.** The earlier limitation was that an 8-port DC
    site exceeds anything Enel deploys. It no longer holds. Enel's
    upgraded Unicentro Bogotá site serves up to 10 vehicles
    simultaneously, with eight 30 kW hoses and two of up to 75 kW (Blu
    Radio, 2026). What remains an assumption is the uniform 50 kW per port,
    not the port count (01 §1.1).

**References for L7 (APA 7).**
- Blu Radio. (2026, May 13). *Conductores en Bogotá podrán cargar hasta el 50 % de batería de su carro eléctrico en menos tiempo* (C. Durán, Author). https://www.bluradio.com/motor/conductores-en-boogta-podran-cargar-hasta-el-50-de-bateria-de-su-carro-electrico-en-menos-tiempo-so35
- Enel Colombia. (2024, May). *Avances en infraestructura de recarga de vehículos eléctricos.* https://www.enel.com.co/es/historias/archive/2024/05/infraestructura-de-recarga-de-vehiculos-electricos.html
- Hardman, S. (2026). Exploring electric vehicle driver activities and expenditure while using DC fast chargers. *Findings.* https://doi.org/10.32866/001c.162484
- U.S. Department of Energy, Vehicle Technologies Office. (2023, December 4). *FOTW #1319: EV charging at paid DC fast charging stations average 42 minutes per session* [Fact of the Week]. https://www.energy.gov/cmei/vehicles/articles/fotw-1319-december-4-2023-ev-charging-paid-dc-fast-charging-stations-average
