# Chapter 5 — Algorithm Comparison (Week 5)

> Status: this chapter is being built incrementally. **S5.1 below is
> written now, ahead of the rest of the chapter, per an explicit
> instruction from the 2026-09-08 Part A review session**: the Colombian
> gross-margin ranking has a formal, provable structure that changes how
> Section 17's Objective 4 trade-off figure must be built, and that had to
> be settled before any figure work started, not discovered after. The
> remaining sections (MPC selection and causality audit, horizon choice,
> the consolidated comparison, target compliance, the training-budget
> control, the recommended-strategy matrix) are written during Part B, per
> `PROJECT_ROADMAP.md`'s Week 5 entry and the Week 5 brief's section 19.

## S5.1 Colombian gross margin: what it does and does not measure

### The result

**`ChargeAsFastAsPossible` (AFAP) has the highest mean gross margin of
every algorithm in the registry — 114,913 COP, above Round Robin
(114,824), above both oracle variants (114,774 / 114,320), and above every
trained RL arm (100,079–110,127).** AFAP is also the only algorithm that
routinely overloads the station's transformer (mean 5.33 kWh/day, 95% CI
excluding zero — `01_baseline.md`, `03_algorithms.md`). Stated plainly,
because it is the central result of this chapter and must not be left for
a reader to notice on their own: **under Colombia's flat-tariff economics,
the algorithm that violates the transformer's rating is the most
profitable one.**

### Is this station meaningfully capacity-constrained, or is 5.33 kWh/day mostly noise?

Checked directly on the 50-cell main grid, not inferred from the reference
cell alone (2026-09-08 review, item 4) — because the reference cell itself
(seed=42, 0.132 kWh) turns out to be one of the *quietest* cells in the
grid, and reading the mean off that context alone would understate the
real picture:

| | value |
|---|---:|
| mean | 5.330 kWh |
| median | **0.000 kWh** |
| max | 37.323 kWh |
| cells with any overload (of 50) | **10 (20%)** |

**The distribution is sharply bimodal, and the split is not by day — it is
entirely by scenario seed.** Broken down by `(seed, eval_day)`: every one
of the 10 `seed=0` cells shows overload (either 10.643 kWh on the 4
weekend `EVAL_DAYS` or 37.323 kWh on the 6 weekday `EVAL_DAYS` — an exact,
repeated value within each category, consistent with `seed=0`'s specific
EV-arrival draw producing a reproducibly more clustered arrival pattern
under this station's weekday-vs-weekend arrival distributions); **every
one of the 40 `seed ∈ {1,2,3,4}` cells shows exactly 0.000 kWh**, despite
serving a similar number of EVs (12–15, comparable to `seed=0`'s 14 on
every cell). This is a property of arrival-timing *clustering* under one
specific stochastic draw, not of EV count, day of week, or season as such.

**Conclusion: this station is genuinely, substantially capacity-constrained
— not "barely constrained" — but the risk is concentrated in a minority
(1-in-5, 20%) of stochastic arrival patterns, not spread evenly across
all days.** A mean of 5.33 kWh/day is the correct summary statistic for
exactly this kind of tail risk (it is what a mean does when 80% of mass
sits at zero and 20% sits at 10.6–37.3), and Round Robin's own value is
real precisely because it reliably neutralizes this recurring, if
intermittent, risk — not because it shaves a uniformly small daily cost.
This is the situation the Objective 4 recommendation is written for:
"manage the existing transformer," not "the transformer is adequate and
the interesting question begins at higher demand." The Week 1 reference
cell (`seed=42`, 0.132 kWh) is accurate but atypically quiet relative to
this distribution — a third, less-clustered draw outside `SEEDS` — and
should not be read as representative of the grid's actual overload risk
on its own.

### Why — a formal proposition, not a coincidence

**Proposition.** With a flat retail tariff `p` (COP/kWh) and a flat energy
purchase cost `c` (COP/kWh), the gross margin of algorithm `i` on a given
cell is

```
margin_i = E_i × (p − c)
```

where `E_i` is the energy delivered (`total_energy_charged`). Since `p`
and `c` are the same constants for every algorithm (`RETAIL_TARIFF_COP_PER_KWH`,
`ENERGY_PURCHASE_COST_COP_PER_KWH` — `ev2gym_thesis/prices/colombia.py`),
`(p − c)` is a positive scalar shared by every algorithm, so **the margin
ranking is identical to the energy-delivered ranking, for any `p > c`.**
This was verified computationally at `p` = 1,160 / 1,450 / 1,740 COP/kWh
(±20%, Part A's sensitivity check) — identical algorithm ordering all
three times, exactly as the proposition predicts, and would hold at any
other `p > c` for the same algebraic reason, not merely at the three
tested points.

**Consequence: gross margin, under this project's flat-tariff Colombian
economics, is a re-labeling of energy delivered.** AFAP delivers the most
energy (mean 196.69 kWh/day) because it charges every connected EV at
maximum rate with no regard for the transformer's rating; that is
precisely the behavior that produces its overload. The metric that would
normally answer "which algorithm makes the operator the most money"
cannot distinguish a strategy that earns its energy delivery honestly from
one that earns it by ignoring a hard operating constraint.

### Why both oracle variants also lose to AFAP and Round Robin on margin (114,774 and 114,320 vs. 114,913 and 114,824)

This is expected, not a bug, and the mechanism follows directly from what
each oracle variant actually optimizes (`04_oracle_and_pitd3.md` S4.2):
`Optimal_Oracle_Tracking` minimizes Σ(power − power_setpoint)², and
`Optimal_Oracle_Balanced` adds a satisfaction penalty on top of the same
tracking objective — **neither one's objective rewards delivering more
energy.** A power setpoint below what the connected fleet could physically
absorb makes tracking that setpoint exactly, rather than exceeding it,
the optimal action — the oracle is willing to deliver slightly less energy
than AFAP would (195.67–196.45 kWh vs. AFAP's 196.69 kWh) whenever doing
so gets `power` closer to `power_setpoint`. Under the margin formula
above, giving up a small amount of energy to hit a tracking target costs
a proportional amount of margin, with no mechanism in either oracle's
objective to care. **This is the oracle behaving exactly as designed on
the metric it actually optimizes (tracking error) — it is not evidence of
a bound that has been beaten, since margin was never the quantity either
oracle bounds** (S4.2's existing restriction: transformer overload and
satisfaction are the only metrics either oracle variant provides a
defensible bound on; tracking error for `Optimal_Oracle_Tracking`
specifically). A reader who expected the "optimal" oracle to win every
column has been told what the oracle is not (S4.1): it is not a
profit-maximizing controller, and was never claimed to be one.

### Gross margin is retired as a ranking metric

**Gross margin (`gross_margin_cop`, `results/economics_cop.csv`) is
reported in every table in this chapter, since Objective 1 asks for
revenue characterization and the absolute COP figures matter for that
question — but it is not used to rank or recommend a control strategy
anywhere in this thesis.** Caption note to be attached to every table
that includes it: *"Gross margin is proportional to energy delivered
under this project's flat Colombian tariff (S5.1) and does not
discriminate between control strategies that respect the transformer's
rating and those that do not; it is reported for Objective 1's revenue
question, not used for ranking."*

### Replacing the Objective 4 trade-off figure

Section 17 of the Week 5 brief specified a figure plotting satisfaction
against profit in COP, with overload as marker size — **rejected as
specified.** Under the proposition above, the profit axis of that figure
carries no information beyond the energy-delivered axis, and every
algorithm's overload is close to its "distance from AFAP" on that same
axis (the algorithms that avoid the most overload are, mechanically, the
algorithms that deliver the least energy relative to AFAP) — the intended
three-way trade-off collapses toward a single line, exactly as flagged
before any plotting was attempted.

**Proposed replacement: cost of respecting the constraint — margin
foregone relative to AFAP, against transformer overload avoided relative
to AFAP.** This asks the actual question an operator faces ("what does
keeping the transformer inside its rating cost me, per algorithm"),
rather than the degenerate "who earns more" question. Computed on the
550-row main grid (mean per cell, relative to AFAP's own mean):

| Algorithm | Margin foregone vs. AFAP (COP) | Overload avoided vs. AFAP (kWh) | COP per kWh overload avoided | Avg. satisfaction |
|---|---:|---:|---:|---:|
| RandomPolicy | 58.7 | 5.106 | 11.5 | 100.0% |
| RoundRobin | 88.6 | 5.330 | **16.6** | 99.997% |
| Optimal_Oracle_Balanced | 138.9 | 5.330 | 26.1 | 100.0% |
| Optimal_Oracle_Tracking | 592.6 | 5.330 | 111.2 | 100.0% |
| TD3_vanilla_ts102 | 6,885.3 | 4.368 | 1,576.2 | 99.08% |
| TD3_TrackingOnly_ts100 | 4,785.6 | 2.366 | 2,022.4 | 99.20% |
| TD3_vanilla_ts100 | 14,833.9 | 4.878 | 3,041.0 | 97.60% |
| TD3_TrackingOnly_ts102 | 9,391.5 | 3.145 | 2,985.8 | 98.49% |
| TD3_vanilla_ts101 | 13,172.4 | 2.676 | 4,921.9 | 97.89% |
| TD3_TrackingOnly_ts101 | 12,995.3 | 1.164 | 11,166.9 | 98.00% |

**Reading this table is the actual Objective 4 finding this chapter needs,
not a robustness check attached to one:** Round Robin eliminates 100% of
AFAP's overload for 88.6 COP/day of foregone margin — effectively free,
16.6 COP per kWh of overload avoided. RandomPolicy is nominally cheaper
per kWh but does not fully eliminate overload (5.11 of 5.33 kWh avoided,
not all of it) and offers no real control logic behind that number — a
coincidence of one uncontrolled policy's action distribution, not a
strategy. Both oracle variants fully eliminate overload at a low but
non-zero cost (26–111 COP/kWh), the perfect-information cost of the same
compliance Round Robin achieves nearly free with no forecast at all — a
second, sharper way to see this chapter's earlier finding that a trivial
heuristic already captures nearly all of the achievable transformer
benefit. **Every trained RL arm is 60×–670× more expensive per kWh of
overload avoided than Round Robin**, while also not fully eliminating the
overload (avoiding only 1.16–4.88 of AFAP's 5.33 kWh) and costing real
satisfaction (97.6–99.2% vs. 100% for every heuristic/oracle variant).
This table, not a satisfaction-vs-margin scatter, is the figure `f`
(numbered in S17.1's rename table) that answers Objective 4's actual
question — full figure spec, caption, and `FIGURE_SPECS` entry to be
added during Part B's figure-build deliverable (section 17).

**Updated, 2026-09-09 (Gate 4): the table above used the 5-seed Part A
grid, since superseded — recomputed on the real 50-seed grid below, same
metric, same interpretation, now on a properly-powered sample and
including the two MPC arms.**

| Algorithm | Margin foregone vs. AFAP (COP) | Overload avoided vs. AFAP (kWh) | COP per kWh overload avoided | Avg. satisfaction |
|---|---:|---:|---:|---:|
| **MPC_EnergyMaxG2V** | **−23.2 (earns *more* than AFAP)** | 13.25 | — | 100.0% |
| RandomPolicy | 259.7 | 10.22 | 25.4 | 100.0% |
| Optimal_Oracle_Balanced | 328.7 | 13.25 | 24.8 | 100.0% |
| Round Robin | 503.9 | 13.25 | **38.0** | 99.90% |
| MPC_TrackingG2V | 551.8 | 13.25 | 41.6 | 100.0% |
| Optimal_Oracle_Tracking | 783.2 | 13.25 | 59.1 | 100.0% |
| TD3_TrackingOnly_ts100 | 5,750.3 | 2.97 | 1,935.2 | 99.09% |
| TD3_TrackingOnly_ts102 | 7,604.5 | 8.94 | 850.1 | 98.73% |
| TD3_vanilla_ts102 | 9,913.0 | 8.84 | 1,122.0 | 98.40% |
| TD3_TrackingOnly_ts101 | 10,742.7 | 3.97 | 2,704.0 | 98.26% |
| TD3_vanilla_ts101 | 11,696.6 | 9.05 | 1,293.2 | 98.02% |
| TD3_vanilla_ts100 | 12,354.8 | 8.72 | 1,417.2 | 97.93% |

**The 50-seed grid sharpens every part of this finding, and adds a new
one.** Round Robin's cost of eliminating AFAP's overload is still
negligible in absolute terms — 503.9 COP against a ~118,000 COP daily
gross revenue, well under 1% — but no longer literally "cheapest": at
this sample size, `MPC_EnergyMaxG2V` **dominates AFAP outright** (higher
mean margin, essentially zero overload), and `Optimal_Oracle_Balanced`/
`RandomPolicy` show a lower COP/kWh ratio than Round Robin. This does not
change the recommendation (S5.8) — `MPC_EnergyMaxG2V` shares
`MPC_TrackingG2V`'s exact causality caveat (S5.5: both inherit `MPC.__init__`'s
non-causal departure-time and near-horizon-arrival knowledge) and is not
a deployable strategy today, and `RandomPolicy`'s favorable ratio is the
same coincidence-not-a-strategy problem noted in the original table. Round
Robin remains the cheapest arm that is both fully causal and a real
control policy. **Every trained RL arm is still 20×–70× more expensive per
kWh of overload avoided than Round Robin**, and still does not fully
eliminate the overload (avoiding only 2.97–9.05 of AFAP's 13.25 kWh, vs.
Round Robin's full 13.25) — this conclusion strengthens, not weakens, on
the larger sample. Full data: `results/week5_margin_vs_overload.csv`.

## S5.2 Week 1 reference cell — reconciled

Raised in the 2026-09-08 review: whether the Week 1 reference cell
(`seed=42`, `eval_day=2022-01-17`) reported in Part A (14 EVs served,
240.93/240.81 kWh charged, 0.132/0.0 kWh transformer overload for
AFAP/Round Robin) is consistent with the project's standing facts.

**Checked directly against three independent sources, not from memory:**

| Source | AFAP | Round Robin |
|---|---|---|
| `CLAUDE.md` (line 174-180, "Week 1 baseline: CONFIRMED (2026-08-11)") | 14 EVs, 240.93 kWh, 0.132 kWh overload | 14 EVs, 240.81 kWh, 0.0 kWh overload |
| `01_baseline.md` §1.3 results table | 14 EVs, 240.93 kWh, 0.132 kWh overload | 14 EVs, 240.81 kWh, 0.0 kWh overload |
| `results/master_results.csv`, `seed=42, eval_day=2022-01-17` row | 14 EVs, 240.926874 kWh, 0.132342 kWh overload | 14 EVs, 240.806523 kWh, 0.0 kWh overload |

**All three agree exactly.** The figures used in Part A's report (and
above) are correct and are the project's current standing facts.

**Where "11 EVs / 42.17 kWh overload, 13 EVs / 0.00 kWh" comes from:**
`00_lab_log.md`'s own 2026-08-05 entry ("Week 1 baseline reproduction
attempt"), lines 2079–2096. These are **pre-project "previously reported
reference values"** of unknown origin — the log states explicitly at the
time that "no seed was recorded anywhere in this repo... for whatever run
originally produced the reference values below, that prior result cannot
be reproduced from this config alone." The same entry's first reproduction
attempt (on the unedited 150-station `V2Ggrid.yaml` copy, before Week 1's
config fix) produced 92 EVs/1,260 kWh — nowhere close to either the 11/13
figures or the 14-EV figures — and was diagnosed as using the wrong,
not-yet-edited config. Once `station_v0_bogota.yaml` was corrected to the
8-station/100kW/CCS-DC scenario later the same day (`00_lab_log.md`,
"Week 1 config fix" entry), the re-run produced exactly the 14 EVs /
240.93 / 240.81 kWh / 0.132 / 0.0 kWh figures reported ever since — the
log explicitly flags at that point that these do **not** match the old
11/13 reference and states the qualitative pattern (AFAP overloads, RR
doesn't) and rough order of magnitude, not the exact old numbers, were
the validation criteria. `CLAUDE.md`'s 2026-08-11 "CONFIRMED" entry is the
user's own later ratification of the 14-EV figures as the official Week 1
baseline — the 11/13 figures were superseded at that point, five weeks
before this session, not overwritten silently.

**No change since Week 1 affected this row.** The Week 2 evaluation
protocol, the Week 3 `reset_for_evaluation` correction, and every later
correction in this project all concern the 50-cell `SEEDS × EVAL_DAYS`
evaluation grid (`seed ∈ {0,1,2,3,4}`) — `seed=42` is outside that set by
construction (it predates `SEEDS` and is kept only as the fixed Week 1
reference point, `notes="week1_reference_day"`) and was never touched by
any of those fixes. The registry row is the same one written on
2026-08-05 and has not been regenerated since.

**Conclusion:** `CLAUDE.md` and `01_baseline.md` currently agree with each
other and with the registry, all three at 14 EVs / 240.93 / 240.81 kWh —
the 11 EVs / 42.17 kWh figures are the abandoned pre-project reference
that this project explicitly moved past on 2026-08-05, not a value any
current project document asserts. No correction was needed to Part A's
numbers; this section exists so the reconciliation is on record and the
11/13 figures are not mistaken for current standing facts again.

## S5.3 Connector-standard citation (Res. 40223/2021) — refined

Corrected 2026-09-08 in `CLAUDE.md`, `01_baseline.md` §1.1(a),
`02_model_validation.md`, and `PROJECT_ROADMAP.md`'s Week 6 entry, per the
2026-09-08 review's sharper framing:

- **Res. 40223/2021 Art. 4 is a minimum, not an exclusive standard.** It
  requires at least one Tipo 1 (SAE J1772) connector in every Nivel 2 and
  Nivel 3-CA station, and at least one **CCS Combo 1** connector in every
  Nivel 3-CD (DC) station. It does not prohibit CCS Combo 2, and it does
  not mention it. The accurate statement is therefore not "the regulatory
  floor is weaker than the config" but **"a DC station equipped only with
  CCS Combo 2 would not, by itself, satisfy Article 4's minimum, which
  requires Combo 1 to be present."** `station_v0_bogota`'s CCS2-only
  assumption abstracts connector type entirely (EV2Gym has no
  connector-type state), so this has zero effect on any simulation
  result — the correction is about what the chapter may claim
  regulatory alignment with, not about the model.
- **Scope:** Art. 4 Paragrafo 3 makes the minimum enforceable starting 12
  months after the resolution's entry into force (9 July 2021), and only
  for stations installed after that date — relevant for Week 6's
  infrastructure guidelines, where a reader will ask what binds a new
  build today (this minimum) versus what was grandfathered (nothing
  installed before the 12-month mark).
- **The anteproyecto (`thesis_docs/references/Project_Proposal_EN_Santiago_Reyes.docx`,
  paragraphs 16 and 40) also mentions "CCS Combo 2"** as a general
  interoperability preference, without citing Res. 40223/2021 by number
  or article in either instance — flagged here for the record, not
  edited: it is the student's own already-submitted proposal document,
  out of scope for this project's chapter-correction convention, and
  neither passage makes the specific wrong regulatory-citation claim the
  chapters made (it does not attribute the CCS2 preference to a specific
  article of Res. 40223/2021).

## S5.4 Annex — 2026 monthly Costo Unitario (CU) series, Nivel 2

Full series behind Part A's Section 4.2 finding (base case: August, S5.1's
`ENERGY_PURCHASE_COST_COP_PER_KWH` and every other month's parameters).
Sensitivity/indexation evidence only — **the average across this table is
never used as a model parameter**, per the brief's explicit instruction;
the base case is always the single most recent published month.

| Month | Generación | Transmisión | Distribución | Comercialización | Pérdidas | Restricciones | CU sin contribución | CU con contribución | Extraction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Enero | 247.1961 | 52.9743 | 191.7479 | 76.4615 | 19.2849 | 17.7949 | 605.4596 | 726.5515 | Regex (text layer) |
| **Febrero** | 332.9887 | 50.6152 | 185.2724 | 75.0193 | 23.8141 | 18.2760 | 685.9857 | 823.1828 | **Manual, visual read of a 600dpi page crop — this PDF's CU table has no extractable text layer (confirmed: 0 characters in that page region). See `thesis_docs/sources/enel_tariffs/2026-febrero_cu_table_crop.png` for the audit image. Values still pass both invariants (component sum, 1.20x contribution factor) like every other month.** |
| Marzo | 294.1060 | 57.6320 | 184.8592 | 83.6490 | 23.2021 | 28.0551 | 671.5034 | 805.8041 | Regex (text layer) |
| Abril | 306.1200 | 55.9536 | 186.4289 | 81.8842 | 21.0877 | 25.8997 | 677.3741 | 812.8489 | Regex (text layer) |
| Mayo | 336.2390 | 38.4612 | 191.3385 | 81.7983 | 22.1548 | 31.6946 | 701.6864 | 842.0237 | Regex (text layer) |
| Junio | 357.3264 | 46.9108 | 187.8443 | 80.9159 | 22.6826 | 22.6959 | 718.3759 | 862.0511 | Regex (text layer) |
| Julio | 365.3973 | 60.4433 | 184.3191 | 81.1308 | 24.3755 | 22.6521 | 738.3181 | 885.9817 | Regex (text layer) |
| **Agosto (base case)** | 374.9931 | 49.3138 | 183.7335 | 83.3438 | 23.9960 | 6.0877 | **721.4679** | **865.7615** | Regex (text layer) |

All values COP/kWh, con contribución = 1.20 × sin contribución exactly
(within rounding), verified per month by `scripts/fetch_enel_tariffs.py`.
Source PDFs: `thesis_docs/sources/enel_tariffs/2026-<month>.pdf`, all
retrieved 2026-09-08. January-to-August change: +19.2% (605.4596 →
721.4679, sin contribución), driven by Generación (+51.7%) while
Restricciones fell (17.7949 → 6.0877) — full discussion in `00_lab_log.md`'s
2026-09-08 entry.

## S5.5 MPC selection and the causality audit

### Class inventory and why every shipped class was rejected

`ev2gym/baselines/mpc/` ships 8 controller classes, all inheriting the
same abstract `MPC` base (`ev2gym/baselines/mpc/mpc.py`). Read from
source, not inferred from filenames:

| Class | File | G2V/V2G | Control-horizon | Objective |
|---|---|---|---|---|
| `V2GProfitMaxOracle` | `V2GProfitMax.py:16` | V2G | `env.simulation_length` (full day) | Minimize Σ price×power |
| `V2GProfitMaxLoadsOracle` | `V2GProfitMax.py:172` | V2G | full day | Same + transformer load/PV constraints |
| `eMPC_V2G` / `eMPC_V2G_v2` | `eMPC.py:16` / `eMPC_v2.py:16` | V2G | 10 (default) | Minimize Σ price×power over horizon |
| `eMPC_G2V` / `eMPC_G2V_v2` | `eMPC.py:166` / `eMPC_v2.py:261` | G2V only, no discharge variable | 10 (default) | Same, charging only |
| `OCMF_V2G` | `ocmf_mpc.py:16` | V2G | 10 (default) | Σ price×power minus a price-weighted flexibility-reservation bonus |
| `OCMF_G2V` | `ocmf_mpc.py:186` | G2V only | 10 (default) | Same, charging only |

**All rejected as shipped.** `V2GProfitMax*Oracle`: `control_horizon =
simulation_length` and a self-declared `algo_name = "Optimal (Offline)"`
— structurally an offline oracle, not MPC, duplicating Week 4's role while
allowing V2G capability no other arm has. The V2G variants generally:
break parity with every other arm under this project's `v2g_enabled:
False` config. The shipped price objective, even restricted to G2V
(`eMPC_G2V`, `eMPC_G2V_v2`, `OCMF_G2V`): under S5.1's proposition, a flat
Colombian tariff makes `minimize Σ price×power` equivalent to `maximize
energy delivered`, so this objective is not evaluated on this thesis's
declared tracking axis at all, and does not represent a distinct control
philosophy from a capacity-aware AFAP (see below for why this arm is kept
anyway, under an honest name).

### Causality — the central audit finding

**Every class inheriting `MPC.__init__` knows two things no other arm in
this thesis knows:** the exact departure time of every currently-connected
EV (built from `EV.time_of_departure` at construction — `mpc.py:108-159`
— regardless of `control_horizon`), and the exact arrival time, location,
and desired capacity of any EV that will arrive within the rolling
`control_horizon` window (bounded foresight, not full-day, for the
receding-horizon classes; full-day for the two Oracle classes). Compared
directly: `PublicPST` withholds both by construction (EV2Gym paper Sec.
III-A, the same principle that closed off a faithful PI-TD3 port in Week
4 — `04_oracle_and_pitd3.md` S4.3); AFAP and Round Robin use neither —
checked directly, `heuristics.py` never references `time_of_departure`
outside the unrelated `ChargeAsLateAsPossible*` classes this project does
not use. (`env.power_setpoints`, read a few steps ahead by the tracking
MPC below, is not part of this asymmetry — it is EV2Gym's own published
operational signal, already read one step at a time by Round Robin and
the RL state, not private information about a user's intent.)

### Reframed: this asymmetry is the value of information, not a defect to apologize for

Both non-causal information sources have a real operational analogue a
Colombian CPO could actually acquire: **declared departure time** is
exactly what a charging app already collects when a driver states when
they plan to leave — Enel's own network bills through the EVX Smart
Charging app (Part A, §3), so the data channel already exists; **near-term
arrival knowledge** is what a reservation/booking system provides. So the
gap between an MPC controller with this information and the best
information-symmetric arm is not a flaw to be minimized in a limitations
paragraph — **it is an upper bound on what the operator would gain by
building that data channel: adding declared-departure capture to the
existing app, or a reservation system at the station.** That is a direct,
quantifiable input to Objective 4's infrastructure and operations
guidance, not a caveat on the MPC arm's validity.

**The direction of this claim must stay disciplined, stated as an upper
bound, not an estimate:** real declared departure times are noisy —
drivers misreport, change plans, or don't use the app — so the realizable
operational gain is strictly smaller than the measured gap between
`MPC_TrackingG2V` and the best causal arm. The gap this project measures
is "what perfect information would buy," not "what a real app-based
system would buy" — the second number is smaller and this project does
not claim to have measured it.

### Two arms, not one, on Gate 2's evidence

Recommended primary arm: **`MPC_TrackingG2V`** (`ev2gym_thesis/mpc/tracking_mpc.py`,
new code, no shipped class matches this objective) — minimizes
Σ(station power − power setpoint)² over a receding horizon, matching
`Optimal_Oracle_Tracking`'s exact objective (`tracking_error.py:168-170`),
so its gap to that oracle is a meaningful "how well can a receding-horizon
controller with better-than-real information hit the declared PST
objective" measurement, feeding directly into the value-of-information
argument above.

**A second arm is included, per the 2026-09-08 review's reasoning: under
Colombia's flat tariff, "maximize profit" is not a redundant restatement
of AFAP — it is "maximize energy delivered subject to the transformer's
hard capacity constraint," a real, distinct question AFAP does not answer
(AFAP ignores the transformer entirely) and Part A's economics already
established as the operator's actual objective under flat pricing.**
Registered as **`MPC_EnergyMaxG2V`** — `eMPC_G2V`, unmodified, run and
labeled under this name so no reader mistakes the (inert, under Colombian
pricing) price objective for doing real work. Gate 2's timing (below)
showed this second arm costs almost nothing beyond the first, so it is
included rather than dropped.

### Gate 2 — timing calibration

Both arms run as one full 96-step episode (receding-horizon MPC re-solves
every step, unlike the single-shot oracle) on the same reference cell
Week 4's Entregable 3 used (`station_v0_bogota`, `SEEDS[0]=0`,
`REFERENCE_DAY=2022-01-17`) — real code, real config, not a shrunk model:

| Quantity | `MPCTrackingG2V` | `MPC_EnergyMaxG2V` (`eMPC_G2V`) |
|---|---:|---:|
| Agent/env construction | 4.49s | 4.47s |
| Full episode (96 steps, all `get_action` + `env.step`) | 2.38s | 3.98s |
| Mean per-step solve time | 0.0245s | 0.0412s |
| Max per-step solve time | 0.0747s | 0.0590s |
| **Per-cell total** | **6.87s** | **8.45s** |
| Extrapolated to 50 cells | 5.7 min | 7.0 min |

**Both arms, 50 cells each (100 cells total): 12.8 minutes** — no
MIP-gap/time-limit relaxation needed at this station size, matching the
Week 4 oracle precedent. `control_horizon=10` (the shipped default,
per-class) used for this calibration; final horizon choice is section 14's
own deliverable, run on a small subset after this scope is approved, not
decided here.

Reference-cell result quality, reported for completeness (not the basis
of any decision at this gate): `MPCTrackingG2V` — `tracking_error=9232.29`,
`total_transformer_overload=0.0`, `average_user_satisfaction=1.0`. For
context, this same cell's already-registered values (`04_oracle_and_pitd3.md`
S4.7) are `tracking_error` = 6388–6482 (either oracle variant), 14477
(Round Robin), 33111 (TD3 seed 100), 72374 (AFAP) — `MPCTrackingG2V`
already sits meaningfully closer to the oracle than Round Robin does on
this one cell, consistent with its larger (if bounded) information
advantage. `MPC_EnergyMaxG2V` — `tracking_error=67783.46` (close to
AFAP's, as expected: it does not target tracking at all),
`total_transformer_overload=0.0` (unlike AFAP, since the transformer limit
is a hard constraint in its model), `average_user_satisfaction=1.0`.
Neither number is a full-grid claim — 1 cell only, reported per section
11's instruction, full-grid numbers come after scope approval.

### Scope candidates for the full-grid run

| Candidate | Arms | Cells | Wall-clock |
|---|---|---|---:|
| A — tracking arm only | `MPCTrackingG2V` | 50 | 5.7 min |
| B — both arms (recommended) | `MPCTrackingG2V` + `MPC_EnergyMaxG2V` | 100 | 12.8 min |
| C — both arms + horizon-sensitivity subset | B + 2 more horizons × 1 seed × 3 days × 2 arms (section 14) | 100 + ~12 | ~13.7 min (subset assumed similar per-cell cost) |
| D — both arms, full horizon sensitivity at all 3 candidate horizons over the full grid | 6× the full grid | 600 | ~77 min (not recommended — section 14 explicitly calls for a small subset, not a full re-run per horizon) |

**Correction, 2026-09-09 (Gate 4): the reference-cell numbers above are
superseded, not by a scope change but by a code fix found while building
the grid runner.** `eMPC_G2V`'s objective (which `MPC_EnergyMaxG2V`
inherits) reads `env.charge_prices` directly — the same live ENTSO-E
price dependency Gate 4 removed from `generate_power_setpoints`. Fixed via
`ev2gym_thesis/mpc/energy_max_mpc.py` (flat price constant, wrapper-level,
`eMPC_G2V` itself untouched). Both MPC arms were then run on the
regenerated, price-neutral 50-seed × 2-day grid — see S5.6 for the real
numbers; scope candidate B (both arms) was executed in full, exactly as
recommended, alongside all 11 other arms and the horizon-sensitivity
subset, in the single homogeneous Gate 4 grid pass, not a separate MPC-only
run.

## S5.6 Consolidated comparison — the regenerated 50-seed × 2-day grid

**All 13 arms, 100 rows each (50 seeds × 2 day types = 1300 rows total),
on the Gate 4-corrected code.** Cluster bootstrap (cluster = scenario
seed) throughout — see S5.2/Gate 3/Gate 4 for why the seed, not the row,
is the independent unit in this project's evaluation design.

### Master comparison table

| Algorithm | EVs served | Overload (kWh) | Avg. satisfaction | Min. satisfaction | Tracking error | Battery degr. |
|---|---:|---:|---:|---:|---:|---:|
| AFAP | 13.44 | 14.22 | 100.0% | 100.00 | 56,257 | 0.000473 |
| Round Robin | 13.44 | 0.00 | 99.91% | 98.80 | 13,581 | 0.000450 |
| RandomPolicy | 13.44 | 3.32 | 100.0% | 100.00 | 39,858 | 0.000456 |
| Optimal_Oracle_Tracking | 13.44 | 0.00 | 100.0% | 100.00 | 5,937 | 0.000421 |
| Optimal_Oracle_Balanced | 13.44 | 0.00 | 100.0% | 100.00 | 5,869 | 0.000434 |
| **MPC_TrackingG2V** | 13.44 | 0.00 | 100.0% | 100.00 | **8,586** | 0.000425 |
| MPC_EnergyMaxG2V | 13.44 | ~0.00 | 100.0% | 100.00 | 43,135 | 0.000444 |
| TD3_vanilla_ts100 | 13.44 | 4.98 | 97.98% | 82.94 | 30,888 | 0.000404 |
| TD3_vanilla_ts101 | 13.44 | 4.48 | 98.07% | 83.26 | 34,999 | 0.000413 |
| TD3_vanilla_ts102 | 13.44 | 4.70 | 98.34% | 83.94 | 34,453 | 0.000417 |
| TD3_TrackingOnly_ts100 | 13.44 | 10.88 | 99.09% | 90.22 | 36,472 | 0.000426 |
| TD3_TrackingOnly_ts101 | 13.44 | 9.27 | 98.30% | 85.68 | 33,865 | 0.000422 |
| TD3_TrackingOnly_ts102 | 13.44 | 4.64 | 98.74% | 87.04 | 33,450 | 0.000422 |

Full CSV with cluster-bootstrap CIs on every metric:
`results/week5_master_comparison.csv`.

**A genuinely new finding, only visible with 50 real seeds: every TD3
checkpoint (both reward families, all 6 seeds) now shows real,
non-trivial transformer overload (4.5–10.9 kWh mean) — not the
near-elimination the 5-seed Week 3/4 sample suggested (means then ranged
0.0–5.3 kWh with wide, uncharacterized seed-to-seed variance).** TD3 was
never trained with an explicit hard capacity constraint the way the
oracle and MPC arms have one baked into their optimization — it learns
overload-avoidance only through a soft penalty term in the reward
(`SqTrError_TrPenalty_UserIncentives`'s `-100 × tr.get_how_overloaded()`,
or not at all for `TD3_TrackingOnly`) — and at 50 seeds that soft penalty
visibly does not generalize as reliably as the earlier, underpowered
sample implied. This sharpens Week 4's finding rather than reversing it:
RL was already shown to lose to Round Robin on tracking error; it now
also loses to Round Robin on the metric (overload) its reward explicitly
penalizes.

### Old vs. new confidence interval — the correction's magnitude, made visible

Headline pairing: Round Robin vs. AFAP, `total_transformer_overload`.

| Version | Point estimate | 95% CI | n (pairs / clusters) |
|---|---:|---|---|
| OLD — naive bootstrap, 5 seeds × 10 `EVAL_DAYS` (pre-Gate 3/4, superseded) | −4.80 kWh | [−12.26, 0.00] | 10 / 5 |
| NEW — cluster bootstrap, 50 seeds × 2 day types | −14.22 kWh | [−19.25, −9.62] | 100 / 50 |

**The old interval's upper bound touched zero — Round Robin's overload
advantage over AFAP was not statistically distinguishable from noise on
the original 5-seed sample.** The new, cluster-corrected, 50-seed interval
excludes zero decisively and is narrower in absolute width (9.64 vs. 12.26
kWh) despite the explicit cluster correction, because the number of
independent clusters grew 10× (5 → 50) — the original finding wasn't
wrong, it was underpowered, and the correction fixed a bias (the naive
interval's false precision from correlated rows) that happened to matter
less than the seed-count itself once both were fixed together.

### AFAP transformer overload — seed-level distribution (n=50, not 5)

| | value |
|---|---:|
| Mean | 14.22 kWh |
| Median | 10.32 kWh |
| Max | 78.63 kWh (per-seed mean); 120.80 kWh (single-cell max) |
| **Seeds with any overload** | **28/50 (56%)** |

This retires the earlier, 5-seed-based framing ("1 of 5 seeds") entirely —
with 50 independent scenario draws, transformer overload under AFAP is
not a rare tail event, it is the **majority-case outcome**: on 56% of
independent arrival realizations, unmanaged charging exceeds the
transformer's rating, at a mean magnitude (14.22 kWh) roughly 2.7× larger
than the earlier 5-seed estimate (5.33 kWh) suggested. Full distribution:
`results/week5_seed_overload_distribution.csv`.

### Optimality gap vs. the oracle — `MPC_TrackingG2V` closes the gap Week 4 called unclosed

| Algorithm | `tracking_error` gap (% of oracle) |
|---|---:|
| **MPC_TrackingG2V** | **44.6%** |
| Round Robin | 128.8% |
| TD3_vanilla_ts100 | 420.3% |
| TD3_TrackingOnly_ts102 | 463.4% |
| TD3_TrackingOnly_ts101 | 470.4% |
| TD3_vanilla_ts102 | 480.3% |
| TD3_vanilla_ts101 | 489.5% |
| TD3_TrackingOnly_ts100 | 514.3% |
| RandomPolicy | 571.4% |
| MPC_EnergyMaxG2V | 626.6% |
| AFAP | 847.6% |

Week 4's headline was "every online algorithm sits far from the oracle,
Round Robin closest at 136.3%." `MPC_TrackingG2V` — the arm this chapter
built specifically to bound the value of departure/near-term-arrival
information — closes that gap to 44.6%, decisively ahead of every causal
arm. **Read correctly, per S5.5's value-of-information framing, this is
not "the new best algorithm to deploy."** `MPC_TrackingG2V` is not
causal (S5.5): it knows information (exact departure times, near-horizon
arrivals) no real Bogotá operator has today. Its gap to the oracle is the
honest answer to "how much of Round Robin's remaining distance from
perfect information is closeable at all, given perfect knowledge of user
departure intent" — a bound on the value of building a reservation/
declared-departure system, not a deployment recommendation. **Round Robin
remains the best-performing arm among those that could actually be
deployed with today's information.** Full table: `results/week5_optimality_gap.csv`.

## S5.7 Target compliance

Against the anteproyecto's three quantitative targets, on the full
50-seed grid:

**Voltage compliance: not applicable this week**, unchanged from Week 4 —
`simulate_grid=False` throughout; `voltage_violation` is structurally
zero for every arm because the constraint isn't modeled, not because it's
satisfied. Week 6 (IEEE 34-bus, `simulate_grid=True`) is where this
target is actually tested.

**User satisfaction > 90%: every arm passes**, `average_user_satisfaction`
ranging 97.98%–100.0% (worst: `TD3_vanilla_ts100`). `min_energy_user_satisfaction`
(a stricter, per-EV worst-case view, reported on its own 0–100 scale per
this project's existing registry convention) is lower for TD3 arms
(82.94–90.22) but was never the target metric — `average_user_satisfaction`
is, per Week 4's S4.9 adoption, carried forward unchanged.

**Energy not served (`ENS_rel`) < 15%, adopted formally this week
(S4.9's Week 4 proposal → Week 5 adoption):**

`ENS_rel(a, s) = (E_AFAP(s) − E_a(s)) / E_AFAP(s)`, `E` = net delivered
energy (`total_energy_charged − total_energy_discharged`), summed over
both day-type rows per seed, paired within seed. **An arm passes only if
the 95% cluster-bootstrap CI's upper bound is below 0.15** — a point
estimate alone does not establish compliance.

| Algorithm | `ENS_rel` point | 95% CI | Passes (CI upper < 15%)? | `ENS_abs` diagnostic |
|---|---:|---|---|---:|
| AFAP | 0.00% | [0.00, 0.00] | Yes | 0.025% |
| Round Robin | 0.47% | [0.24, 0.75] | Yes | 0.497% |
| RandomPolicy | 0.05% | [0.04, 0.05] | Yes | 0.070% |
| Optimal_Oracle_Tracking | 0.50% | [0.47, 0.52] | Yes | 0.522% |
| Optimal_Oracle_Balanced | 0.11% | [0.10, 0.11] | Yes | 0.132% |
| MPC_TrackingG2V | 0.49% | [0.47, 0.52] | Yes | 0.519% |
| MPC_EnergyMaxG2V | −0.003% | [−0.003, −0.002] | Yes | 0.022% |
| TD3_vanilla_ts100 | 9.98% | [7.99, 12.12] | Yes | 9.999% |
| TD3_vanilla_ts101 | 9.97% | [8.04, 11.99] | Yes | 10.058% |
| TD3_vanilla_ts102 | 8.56% | [6.82, 10.32] | Yes | 8.697% |
| TD3_TrackingOnly_ts100 | 4.76% | [3.42, 6.23] | Yes | 4.776% |
| TD3_TrackingOnly_ts101 | 9.22% | [6.92, 11.87] | Yes | 9.363% |
| TD3_TrackingOnly_ts102 | 6.49% | [4.83, 8.26] | Yes | 6.478% |

**Every arm clears the 15% target on the CI-upper-bound test, worst case
`TD3_vanilla_ts100`/`ts101` at ~12.1%/12.0%** — still comfortably under
15%, but the closest margin in the whole comparison. `MPC_EnergyMaxG2V`'s
slightly negative `ENS_rel` (delivering marginally more net energy than
AFAP on average) is reported as measured, not clipped to zero, per the
brief's explicit instruction.

`ENS_abs` — energy not served relative to `R(s)`, the actual requested
energy of EVs departing within the simulation horizon (computed directly
from each cell's real `EVs_profiles`, not a proxy metric — see
`scripts/analyze_week5_results.py::requested_energy_by_cell`) — confirms
the station is not fleet-level capacity-inadequate: **AFAP's own `ENS_abs`
is 0.025%**, meaning the unmanaged baseline itself serves essentially all
requested energy in aggregate. This is the diagnostic that separates
"the station lacks enough capacity" (not the case here) from "the
station's capacity is being used badly at the wrong times" (S5.1/S5.6's
actual finding) — exactly the distinction the brief asked this metric to
draw. Every EV that arrived within the simulation horizon is accounted
for in `R(s)`; EVs still connected at the horizon's end are excluded from
`R` and tracked separately as a diagnostic (`results/week5_requested_energy_by_cell.csv`).

Definition set for this project, per the brief's own framing — `ENS_rel`
is the compliance gate (matches the proposal's literal "vs. baseline no
gestionado" wording); `ENS_abs` is diagnostic only, reported for every
arm including AFAP, never used to judge compliance.

## S5.8 Recommended strategy for Objective 4

**Recommendation: Round Robin.** Argued from the evidence assembled in
this chapter, on the three declared axes:

- **Technical compliance.** Round Robin is the only fully causal,
  deployable-today arm that reduces AFAP's transformer overload to
  exactly zero, on a station where that overload is real and substantial
  — 56% of independent arrival scenarios (S5.6), not a rare edge case.
  It does this with no forecast, no training, and no information
  advantage over what a real Bogotá operator has today.
- **Economic cost of that compliance is negligible.** 503.9 COP/day
  foregone margin against a ~118,000 COP/day gross revenue base (S5.1) —
  under 1%. Gross margin itself is retired as a ranking metric (S5.1) for
  the reason this number illustrates: under Colombia's flat tariff, margin
  tracks energy delivered almost perfectly, so a strategy that
  occasionally forgoes a small amount of energy to respect a hard
  constraint will always look slightly worse on margin than one that
  doesn't — that is the cost of the constraint being real, not a mark
  against the strategy.
- **User satisfaction and energy-not-served.** Round Robin clears both
  targets by a wide margin (99.90% average satisfaction, `ENS_rel` CI
  upper bound 0.75% — S5.7), indistinguishable in practice from AFAP's
  own 100%/0%.

**What beats Round Robin, and why none of it changes the recommendation:**

- `MPC_TrackingG2V` (44.6% gap to the oracle, S5.6) and `MPC_EnergyMaxG2V`
  (dominates AFAP on margin outright, S5.1) both outperform Round Robin on
  their respective axes. Both are excluded from the recommendation for the
  same reason: both inherit `MPC.__init__`'s non-causal knowledge of
  connected-EV departure times and near-horizon arrivals (S5.5) — neither
  is deployable with the information a real Bogotá public-station operator
  has today. Their value is as an **upper bound on what a declared-
  departure app feature or a reservation system could buy**, not as
  competing recommendations. If Objective 4's infrastructure guidance
  includes a software/operational recommendation, it is this: **the gap
  between Round Robin and `MPC_TrackingG2V` (128.8% vs. 44.6% oracle gap)
  is the size of the prize available from adding departure-time capture to
  the existing charging app** — bounded above, not estimated, since real
  declared departure times are noisier than the perfect information this
  chapter modeled (S5.5's explicit caveat).
- Both perfect-information oracle variants dominate everything by
  construction (S4.1) and were never candidate recommendations.
- Every trained RL arm loses to Round Robin on every axis measured this
  week: tracking error (420%+ oracle gap vs. 128.8%), transformer
  overload (now confirmed real and non-trivial at 50 seeds, S5.6, where
  Week 3/4's 5-seed sample understated it), and cost-per-kWh-of-overload-
  avoided (20×–70× more expensive). This is the same conclusion Week 4
  reached, now on a properly-powered sample rather than reversed by it —
  if anything, more RL checkpoints show real overload than the small
  sample suggested, sharpening rather than softening the finding.

**Bounded, not general:** this recommendation is specific to
`station_v0_bogota`'s scale (8 ports, 100 kW transformer, 4:1
oversubscription) and Colombia's current flat-tariff structure (Part A).
It says nothing about voltage compliance (Week 6), nothing about a larger
or more heavily oversubscribed station where Round Robin's simple
setpoint-tracking might itself start to strain, and nothing about whether
a longer RL training budget would close the gap this week's evidence
shows (S5.10 below addresses that last question directly, on the evidence
available).

## S5.9 MPC horizon sensitivity

`MPC_TrackingG2V` only, 3 candidate horizons ({5, 10, 20} steps), 10-seed
subset (seeds 0–9, both day types = 20 cells/horizon), per section 14's
explicit "small subset" instruction:

| Horizon | Mean tracking error | Mean overload | Mean per-cell runtime |
|---|---:|---:|---:|
| 5 | 10,643 | 0.00 | 1.56s |
| **10 (used for the main grid)** | **8,427** | 0.00 | 2.84s |
| 20 | 6,673 | 0.00 | 5.66s |

**A real, monotonic difference exists — this is not the "no meaningful
difference" case.** Tracking error falls 21% from horizon=10 to
horizon=20, at roughly 2× the per-cell compute cost; energy delivered and
overload are unaffected by horizon choice (transformer capacity is
already a hard constraint regardless of how far ahead the model plans).
**Horizon=10 is the value actually used for every `MPC_TrackingG2V` row
in S5.6** — set for this project as the shipped classes' own default,
not re-optimized before the main grid ran (Gate 2's calibration measured
it, Gate 4's fix was orthogonal to it). Declared here as an open,
quantified opportunity rather than silently accepted: **horizon=20 would
tighten `MPC_TrackingG2V`'s already-decisive 44.6% oracle gap further**,
at a compute cost (5.66s/cell × 100 cells ≈ 9.4 min for a full-grid rerun)
well within this project's demonstrated budget. Not re-run this week —
flagged for Week 6 or the final consolidation pass rather than absorbed
into this week's already-large scope silently. `MPC_TrackingG2V`'s
value-of-information conclusion (S5.5, S5.8) is unaffected either way: a
larger horizon would only widen its lead over every causal arm, not
narrow it.

## S5.10 TD3 training-budget control

`TD3_vanilla_ts100`, checkpoints at 10k/20k/30k/40k/50k/60k steps
(confirmed present, no retraining needed — Gate 4's hard-gate check
cleared), 10-seed subset (seeds 0–9, both day types = 20 cells/checkpoint):

| Checkpoint (steps) | Tracking error | Overload (kWh) | Satisfaction |
|---:|---:|---:|---:|
| 10,000 | 27,512 | 0.34 | 99.28% |
| 20,000 | 30,266 | 0.65 | 99.41% |
| 30,000 | 30,475 | 0.35 | 98.97% |
| 40,000 | 29,034 | 4.21 | 97.62% |
| 50,000 | 31,164 | 10.97 | 98.12% |
| **60,000 (the arm used everywhere else in this thesis)** | 30,213 | 6.75 | 97.83% |

**No monotonic improvement with training budget — if anything, transformer
overload gets WORSE at later checkpoints (0.34 kWh at 10k → 6.75–10.97 kWh
at 50k–60k), and tracking error is flat/noisy throughout (27,512–31,164
across the whole range, no clear downward trend).** This is a real,
measured result, not an artifact of this being a 10-seed subset showing
noise — it is consistent with, and reinforces, the substantial
cross-training-seed dispersion already documented in Weeks 3–4 (up to
63.8% relative spread on individual metrics at this same 60k budget).
**This is evidence against, not for, "the 60,000-timestep budget is
binding and a longer run would close the gap":** if the budget were
simply insufficient, later checkpoints should show a clear, if noisy,
improving trend; instead the trajectory looks like it plateaued (or
never had a clear trend at all) well before 60k steps, with overload
actually increasing at some later checkpoints. **This strengthens Week
4's conclusion rather than qualifying it** — the RL-vs-Round-Robin gap
does not look like an artifact of an undertrained model that a longer
run would fix; it looks like a property of this training setup at this
problem scale. Full per-cell data: `results/week5_td3_budget_curve.csv`.
