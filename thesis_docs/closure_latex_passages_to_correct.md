# Passages to correct in the external LaTeX (Overleaf) document — closure brief A.1/A.2, 2026-10-06

The Overleaf `.tex` source is not on this machine, so it could not be read
or edited. The passages below are the stale sentences found in the Word
documents the thesis text was written from. They are quoted exactly, so
each can be found in Overleaf with its search box. For every passage
below, use the corrected wording given in its entry.

Values are from the current statistical grid (`analysis_row=True`; 50
scenario seeds × 2 day types; cluster bootstrap, n_clusters = 50).

## Battery capacity (A.1): 60 kWh → 70 kWh

The configured battery is `ev.battery_capacity: 70`
(`experiments/phase1_baseline/configs/station_v0_bogota.yaml`). 60 kWh was
never simulated.

| Search for | Found in | Replace with |
|---|---|---|
| `All simulated vehicles share one 60 kWh battery profile for Week 1.` | `../Week1_Parameter_and_Method_Justification.docx` (para. 25); `thesis_docs/Progress_Log_Thesis_Project_corrected_2026-09-09.docx` (para. 121, section 8.1.4) | `All simulated vehicles share one 70 kWh battery profile.` |
| `Uniform, 60 kWh battery` | `../Progress_Log_Thesis_Project.docx` (para. 144, table) | `Uniform, 70 kWh battery` |

## AFAP overload and the random control (A.2): 5-seed grid values

| Search for | Found in | Replace with |
|---|---|---|
| `the random-policy control shows WORSE overload (12.74 kWh) than even unmanaged AFAP (5.33 kWh)` | `../Progress_Log_Thesis_Project.docx` (para. 62) | Pre-correction Week 3 claim, reversed on 2026-08-18. Current grid: the random control 3.32 kWh/day [1.75, 5.17] against AFAP 14.22 kWh/day [9.58, 19.28]; the control is *lower* than AFAP, so a low overload alone does not show learning. |
| `RandomPolicy achieves approximately 0.22 kWh of transformer overload, compared with 5.33 kWh for AFAP` | corrected Progress Log, para. 287 (section 8.3.11) | `On the current grid, RandomPolicy averages 3.32 kWh/day [1.75, 5.17] of transformer overload, against 14.22 kWh/day [9.58, 19.28] for AFAP (n_clusters = 50).` |
| any table cell `5.33` for AFAP overload | `../Progress_Log_Thesis_Project.docx` (para. 181, table) | `14.22 [9.58, 19.28]` (current grid), or label the table "superseded 5-seed grid". |
| Week 3 table `Energy charged -0.08%` (Round Robin vs. AFAP) | chapter 03 source text | `-0.47% [-0.75%, -0.23%]` |

## Cost of the transformer limit (A.2): 503.9 / 88.6 → 551.9 COP/day

| Search for | Found in | Replace with |
|---|---|---|
| `About 503.9 COP/day of foregone margin` | corrected Progress Log, para. 453 (section 10.16) | `About 551.9 COP/day [274.3, 874.2] of foregone margin` |
| `88.6 COP/day` | chapter 05 source text (5-seed table) | `551.9 COP/day [274.3, 874.2]` (38.8 COP per kWh of overload avoided) |

## Satisfaction and energy targets (closure Checkpoint B): withdraw the "users" reading

EV2Gym drops arrivals at occupied ports, so satisfaction and `ENS_rel`
cover served EVs only. Demand not served is 34.6% [30.8, 38.4] for Round
Robin at the reference demand.

| Search for | Found in | Replace with |
|---|---|---|
| `average_user_satisfaction > 90% is met by every algorithm and arm tested this week` | corrected Progress Log, para. 364 (section 9.7) | add: `(for the EVs that obtained a port; counting rejected arrivals, no arm meets it)` |
| `Round Robin satisfaction 99.89% [99.83, 99.94]` and the other `13.3` bullets | corrected Progress Log, paras. 519–523 | add: `served EVs only; demand not served 34.6–65.0% at 1.0–1.6×` |
| `sat Y, ENS Y` (section 13.4) | corrected Progress Log, paras. 525–529 | add: `on demand not served, every arm fails the 15% target` |

The corrected Progress Log itself is not edited in place. Its new section
15.1 records each of these corrections with the paragraph's section
number.

## Final capacity brief (2026-10-07): passages the DC session-duration results change

The `.tex` file is not on this machine. Search the Overleaf document for
these passages; Chapter 6 S6.6, Chapter 7 S7.10 and Chapter 8 L7 hold the
full argument.

| Search for (in your LaTeX) | Change |
|---|---|
| Any statement that Round Robin "keeps the 100 kW transformer within its rating", "zero overload up to 2.5×", or "removes the overload" | Add: "under EV2Gym's Dutch session durations (mean 300.6 min). EV2Gym's Round Robin follows a median-smoothed power setpoint, not the transformer; under 42-minute DC sessions it overloads in 65/100 runs at the reference demand." |
| "34.6%" demand not served / "the 8 ports bind" / "12 ports at 1.0×" / "10 ports at 0.733×" | Mark as a Dutch-duration sensitivity. Under 42-minute DC sessions: lower-bound rejections 0.9/day (not 8.9), DNS 2.4% (AFAP) and 5.0% (transformer-capped Round Robin) at the same spawn multiplier; **the binding constraint is power, not ports.** |
| Capacity guideline stated in multiples ("below 0.733× the guideline holds", "1.3–1.6× demand growth") | Restate in physical units: "8 ports and 112.5 kVA under a transformer-capped round-robin load manager serve up to 47 arrivals/day (763 kWh/day) with demand not served ≤ 15%; at 57 arrivals/day (911 kWh/day) 10 ports on the same unit." |
| Round Robin as "the recommended strategy" for Objective 4 | Qualify: "a load manager that reads the transformer rating (round-robin allocation capped at the rating); EV2Gym's setpoint-following Round Robin does not meet the criteria under DC sessions." |
| Any description of the simulated sessions as DC fast-charging sessions, or of arrival/energy data without a source | Add: "EV2Gym's session durations are ElaadNL Dutch public-charging data (mean 300.6 min, minimum 225 min); the DC model uses an external, non-Colombian reference of 42 min (U.S. DOE, 2023), bracket 32–78 min." |
| "No single Enel site has 8 DC ports" or similar | Replace with: "Enel's upgraded Unicentro Bogotá site serves up to 10 vehicles simultaneously (Blu Radio, 2026)." |
| The final compliance table | Replace with the DC table (handback `Dwell_Capacity_...docx`, Part 1): only the transformer-capped Round Robin meets every evaluable target at 1.0× and 1.3×; at 1.6× no arm meets the satisfaction target counting rejected arrivals. |
| Final RL model results presented without qualification in a capacity context | Add: "trained on Dutch durations; out of its training distribution under DC sessions." |

**Add to the LaTeX bibliography (APA 7):**
- Blu Radio. (2026, May 13). *Conductores en Bogotá podrán cargar hasta el 50 % de batería de su carro eléctrico en menos tiempo* (C. Durán, Author). https://www.bluradio.com/motor/conductores-en-boogta-podran-cargar-hasta-el-50-de-bateria-de-su-carro-electrico-en-menos-tiempo-so35
- Enel Colombia. (2024, May). *Avances en infraestructura de recarga de vehículos eléctricos.* https://www.enel.com.co/es/historias/archive/2024/05/infraestructura-de-recarga-de-vehiculos-electricos.html
- Hardman, S. (2026). Exploring electric vehicle driver activities and expenditure while using DC fast chargers. *Findings.* https://doi.org/10.32866/001c.162484
- U.S. Department of Energy, Vehicle Technologies Office. (2023, December 4). *FOTW #1319: EV charging at paid DC fast charging stations average 42 minutes per session* [Fact of the Week]. https://www.energy.gov/cmei/vehicles/articles/fotw-1319-december-4-2023-ev-charging-paid-dc-fast-charging-stations-average

