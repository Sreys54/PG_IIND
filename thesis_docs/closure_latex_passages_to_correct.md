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
