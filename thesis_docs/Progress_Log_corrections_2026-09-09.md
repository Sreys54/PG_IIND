# Progress Log — Correction Sheet (generated 2026-09-09, from `main`)

Cross-check of the compiled Progress Log PDF ("Thesis_IIND (1).pdf", Weeks 1–5)
against the repository state on `main` (`thesis_docs/chapters/*.md`, `CLAUDE.md`,
`ev2gym_thesis/`, `results/master_results.csv`, `PROJECT_ROADMAP.md`).

Every item below is either (a) a claim in the PDF that a later week of this same
project already corrected, (b) a number the Week 5 grid rebuild superseded, or
(c) content that exists in the chapter / weekly Word doc but was never transcribed
into the Progress Log. Apply to the LaTeX source, then recompile.

Severity: **HIGH** = a checkable factual error or a contradiction that would show
in the final thesis; **MED** = stale number or missing framing; **LOW** = wording.

---

## PART 1 — Replace existing text

### C1 (HIGH) — §8.1.4, "Connector standard and charging power"

**Remove:**

> Connector standard and charging power: CCS Combo 2, 50 kW DC. This is not a
> modeling choice but a direct transcription of Colombian regulation: Resolucion
> 40223 de 2021 (Ministerio de Minas y Energia) sets CCS Combo 2 as the minimum
> required DC fast-charging connector for publicly accessible stations in
> Colombia. Using a different connector or power level in the simulation would
> misrepresent the regulatory floor the thesis is meant to reflect.

**Replace with:**

> Connector standard and charging power: CCS Combo 2, 50 kW DC — a **declared
> simplification on market-practice grounds, not a regulatory-floor claim**
> (this framing corrected in Week 5 Part A, 2026-09-08; the original text of
> this section asserted a CCS Combo 2 regulatory mandate that is wrong).
> Reading Articulo 4o of Resolucion 40223 de 2021 directly
> (`thesis_docs/references/regulatory/res_40223_2021.html`): the minimum
> mandated connector standard is **Tipo 1 (SAE J1772) for AC and CCS Combo 1
> (SAE J1772-based) for DC**. "CCS Combo 2" does not appear anywhere in the
> resolution. A DC station equipped only with CCS Combo 2 would **not**, by
> itself, satisfy Article 4's minimum, which requires Combo 1 to be present.
> The mandate is a *minimum* (operators may add other connector types) and
> binds only stations installed from 12 months after the resolution's entry
> into force (Art. 4, Paragrafo 3). This project keeps CCS Combo 2 in the
> config because Enel Colombia's own August 2025 public fast-charging network
> reports CCS1, CCS2 and GBT connectors in active use — i.e. CCS2 is a real,
> currently deployed standard in Bogota, at the higher-capability end of what
> is installed. Because EV2Gym has no connector-type state, this assumption
> has **zero effect on any simulation result**; the correction concerns only
> what regulatory alignment the thesis may claim.

Also, in §8.1.5 References, the Resolucion 40223 de 2021 entry should read
"basis for the AC Tipo 1 / DC CCS Combo 1 minimum connector standard" — **not**
"CCS Combo 2".

Note: §1.1.2 ("Design"), which reproduces the approved proposal verbatim, still
says "CCS Combo 2". Leave it — it is frozen proposal text. Add a single footnote
there: *"The approved proposal's CCS Combo 2 reference is not attributed to a
specific article; see §8.1.4 for the corrected reading of Res. 40223/2021."*

---

### C2 (MED) — §8.1.4, "EV charging-power fields", the ZeroDivisionError claim

**Remove:**

> This is a workaround for a specific mechanic in EV2Gym's own charging model
> (ev2gym/models/ev.py, function _charge), which uses max_ac_charge_power as a
> normalization denominator even for DC-only chargers. Leaving it at its
> conceptually correct value of 0 for a DC-only station raises a
> ZeroDivisionError.

**Replace with:**

> This is a defensive workaround, applied as a harmless safeguard. The original
> text of this section stated that leaving `max_ac_charge_power` at 0 for a
> DC-only station raises a `ZeroDivisionError` in `ev2gym/models/ev.py`; that
> specific failure mode **could not be reproduced against the current EV2Gym
> code** (checked 2026-09-09): in `ev.py` `max_ac_charge_power` appears as a
> numerator (`ev.py:297`) and as a power cap (`ev.py:415-416`), not as a
> normalization denominator, so a value of 0 does not by itself divide by
> zero. Setting `max_ac_charge_power = max_dc_charge_power = 50` is kept
> anyway because it is numerically harmless and the station's real power
> ceiling is enforced independently through
> `charging_station.max_charge_current`. It is a code-mechanic safeguard, not
> a modeling assumption.

---

### C3 (HIGH) — §8.3.11 and any Week 2/3 text using "AFAP overload 5.33 kWh / 1-in-5 / 20%"

Every Week 2–4 number computed on the old **5 seeds × 10 EVAL_DAYS = 50-cell**
grid was superseded in Week 5 Part B (Gate 4) by the regenerated **50 seeds ×
2 day-types = 100-cell** grid. Add this standing note at the first place Week 3
reports a grid mean (start of §8.3.11), and repeat a one-line pointer wherever
5.33 kWh appears:

> **Superseded by the Week 5 grid rebuild (§10.8).** The overload figures in
> this section are computed on the original 5-seed × 10-day grid, which Week 5
> Gate 3/Gate 4 showed was not statistically independent across the day axis.
> On the regenerated 50-seed × 2-day grid, AFAP's mean transformer overload is
> **14.22 kWh/day** (not 5.33) and **28 of 50 independent arrival scenarios
> (56%) show overload** — a majority-case outcome, not a 1-in-5 tail. Round
> Robin's overload advantage over AFAP, whose 5-seed 95% CI touched zero
> ([−12.26, 0.00]), becomes decisive on the 50-seed cluster bootstrap
> ([−19.25, −9.62]). The corrected numbers are the ones carried into the
> Objective 4 comparison; the 5-seed figures here are retained only to show
> the state of evidence at the time.

(Same note applies to any Week 3/4 statement of "TD3 near-eliminates overload":
on 50 seeds every TD3 checkpoint shows 4.5–10.9 kWh mean overload — see the new
§10.x.6 below.)

---

### C4 (MED) — §8.3, TD3 section — broken `[?]` citations

Two literal unresolved `[?]` markers on the "twin critics, delayed policy
updates, and target policy smoothing [?]" and "…environment construction …
and analysis [?]" sentences. Bind them to:

- Fujimoto, S., van Hoof, H., & Meger, D. (2018). *Addressing Function
  Approximation Error in Actor-Critic Methods.* ICML 2018. (TD3)
- Raffin, A., Hill, A., Gleave, A., Kanervisto, A., Ernestus, M., & Dormann,
  N. (2021). *Stable-Baselines3: Reliable Reinforcement Learning
  Implementations.* JMLR 22(268), 1–8.

Add a "8.3.13 References" list to the Week 3 section (currently it has none),
including these two plus the EV2Gym paper (Orfanoudakis et al., 2025).

---

### C5 (MED) — §10.2 / §10.4.2, Colombian tariff constants — provenance and "lower bound"

After the two bullet values (1450 COP/kWh retail; 865.7615 COP/kWh purchase),
insert:

> The two constants are **not the same-year figures**. The retail tariff,
> 1,450 COP/kWh, is a single published point from an Enel Colombia article of
> **August 2025** ("Estas son las estaciones de carga … en Bogota"; exact
> quote: *"La recarga tendra un valor de 1.450 pesos por kilovatio, que puede
> variar segun el costo de la energia"*). A recency search on 2026-09-08
> restricted to Enel X and Enel Colombia found no more recent published EV
> retail price. The energy purchase cost, 865.7615 COP/kWh, is Enel Colombia's
> regulated **August 2026** Nivel de Tension 2 tariff sheet, with the
> solidarity contribution (×1.20). Pairing a 2025 revenue figure with a 2026
> cost figure is deliberate and its direction is known: Colombian retail
> prices trend upward (the Nivel 2 CU rose **+19.2% January–August 2026**), so
> this pairing **understates** the operator's margin. Every profitability
> number in this thesis computed from these constants is therefore a **lower
> bound on the operator's margin, not a central estimate, and is reported as
> such** (`ev2gym_thesis/prices/colombia.py`). A ±20% sensitivity band on the
> retail price was run; the algorithm ranking on gross margin is invariant for
> any retail price above the purchase cost (formal proposition, §S5.1 of
> Chapter 5), so the ranking conclusions do not depend on the exact 1,450
> figure.

---

### C6 (LOW) — §8.1.3

"Phase 2 (Weeks 3–5) introduces MPC and reinforcement learning" — append:
"(in practice MPC was implemented in Week 5, after Week 3's vanilla TD3 and
Week 4's oracle plus reward ablation; see the roadmap-deviation notes in each
week's entry)."

---

## PART 2 — Add missing content

The Progress Log's Week 4 section stops at "9.4 Oracle Evaluation Pipeline" and
its Week 5 section stops before the Part B comparison results. Both bodies of
results already exist in `thesis_docs/chapters/04_oracle_and_pitd3.md` (S4.4–S4.10)
and `05_algorithm_comparison.md` (S5.5–S5.10) and in the WeekN Word docs. Insert
the following, keeping the PDF's numbered style.

### ADD 9.5 — Physics-informed reward: falsified before training

> Two reward-only adaptations inspired by the PI-TD3 paper were implemented,
> verified analytically, and **rejected before any training compute was spent**,
> for two independent, well-diagnosed structural reasons (full mechanism in
> `04_oracle_and_pitd3.md` S4.3). A genuine ambiguity in the paper's Eq. 14 was
> recorded rather than resolved either way. **No `PI_TD3` arm exists anywhere
> in this thesis's registry, code, or results.** Week 4's second training arm
> is instead `TD3_TrackingOnly`, a controlled reward ablation.

### ADD 9.6 — `TD3_TrackingOnly` reward ablation: training and evaluation

> All 3 TRAIN_SEEDS trained at the same 60,000-timestep/seed budget as
> `TD3_vanilla`. Per-seed wall-clock: 55.72 / 54.61 / 58.10 min; total 168.43
> min (2.807 h), 1.4% under the pre-training calibration estimate. Evaluated on
> the same 50-cell grid as every other arm (`scripts/evaluate_rl.py`); 150 rows
> appended (3 seeds × 50 cells). Main-grid registry at end of Week 4: **550
> rows = 11 algorithms × 50 cells**, confirmed by `TestRegistryCount`.

### ADD 9.7 — Week 4 analysis (headline results)

> **(a) Reward ablation — mixed result, not a validation.** Pooled n=150 matched
> cells, paired bootstrap: `TD3_vanilla` (composite reward) is better on
> tracking error (+12.95%), energy tracking error, transformer overload
> (+1.75 kWh) and battery degradation; `TD3_TrackingOnly` is better on
> ENTSO-E-priced energy cost and on both satisfaction metrics
> (`min_energy_user_satisfaction` +7.59%). Neither dominates. An earlier draft
> called this "retroactively validates Week 3's choice"; that was corrected
> (2026-08-20) — the evidence *partially* supports Week 3's reasoning, at a
> real cost on two of the thesis's three objective axes. The counterintuitive
> direction (training on tracking error alone yields *worse* realized tracking
> error) is recorded as a hypothesis (reduced-budget reward shaping /
> regularization), with an out-of-scope test proposed, not as an established
> mechanism.
>
> **(b) Optimality gap vs. the tracking-error oracle** (metrics the oracle
> actually optimizes):
>
> | Algorithm | tracking_error gap (% of oracle) |
> |---|---:|
> | Round Robin | **136.3%** (closest online algorithm) |
> | TD3_vanilla (best seed) | 421.9% |
> | TD3_TrackingOnly (best seed) | 482.0% |
> | RandomPolicy | 612.0% |
> | AFAP | 894.0% |
>
> **Week 4 headline, stated plainly: under this 60,000-timestep CPU training
> budget, reinforcement learning does not beat a trivial round-robin heuristic
> on tracking error — by a wide margin, consistently across two reward
> functions and six independent training seeds.** The claim is bounded to the
> training regime actually used; whether the papers' HPC-scale budget would
> close, keep, or reverse this gap is not established by this project.
>
> **(c) Cross-training-seed dispersion** persists for the second reward arm
> too (`TD3_TrackingOnly` `total_transformer_overload` relative spread 63.8%) —
> a real limitation of the reduced training budget, not specific to the
> vanilla reward.
>
> **(d) Success targets:** `average_user_satisfaction` > 90% met by every arm
> (worst 97.6%). The proposal's "<15% energy not served vs. unmanaged baseline"
> target was still un-operationalized at end of Week 4; a candidate definition
> `(1 − average_user_satisfaction) × 100` was proposed for Week 5 to adopt
> (worst arm 2.57%, well under 15%). Voltage band: not applicable
> (`simulate_grid=False` through Week 4).

### ADD 9.8 — Week 4 verdict

> 1. Oracle: a real, dominant, verified upper bound on tracking error, with a
>    quantified tie-break noise floor.
> 2. Physics-informed reward adaptation: genuinely falsified, not abandoned —
>    two designs, both built and rejected before training, for two independent
>    diagnosed reasons. No `PI_TD3` arm exists.
> 3. Reward ablation: mixed result. `TD3_vanilla` wins on tracking / overload /
>    degradation; `TD3_TrackingOnly` wins on cost and both satisfaction
>    metrics. Week 3's reasoning is partially, not fully, supported.
> 4. Real headline: under this training budget, RL does not beat Round Robin on
>    tracking error, by a wide margin, across two rewards and six seeds. Points
>    Objective 4 toward Round Robin, not RL, on current evidence.
> 5. Both TD3 reward arms show substantial cross-training-seed dispersion (up
>    to 63.8% relative spread).
> 6. Energy-not-served target: proposed operationalization, not yet adopted;
>    every arm clears <15% by a wide margin.

### ADD 9.9 — Week 4 Summary

> Week 4 established a perfect-information benchmark and closed Week 3's open
> reward question. It did not produce a deployable new controller; its
> contribution is the bound (oracle) and the negative/mixed results (PI-TD3
> falsification, reward ablation) that together move the Objective 4
> recommendation toward the simplest causal heuristic.

---

### ADD 10.12 — Week 5 Part B: consolidated 13-arm comparison (50-seed × 2-day grid)

> All 13 arms, 100 rows each (50 seeds × 2 day-types = 1,300 rows), on the
> Gate 4-corrected, price-neutral code. Cluster bootstrap (cluster = scenario
> seed) throughout. Every pre-Week-5 registry row is retained but flagged
> `superseded=True` and excluded from every current table and figure; only the
> 1,300 `analysis_row=True` rows are statistically valid.
>
> | Algorithm | EVs served | Overload (kWh) | Avg. sat. | Min. sat. | Tracking error |
> |---|---:|---:|---:|---:|---:|
> | AFAP | 13.44 | 14.22 | 100.0% | 100.00 | 56,257 |
> | Round Robin | 13.44 | 0.00 | 99.91% | 98.80 | 13,581 |
> | RandomPolicy | 13.44 | 3.32 | 100.0% | 100.00 | 39,858 |
> | Optimal_Oracle_Tracking | 13.44 | 0.00 | 100.0% | 100.00 | 5,937 |
> | Optimal_Oracle_Balanced | 13.44 | 0.00 | 100.0% | 100.00 | 5,869 |
> | MPC_TrackingG2V | 13.44 | 0.00 | 100.0% | 100.00 | 8,586 |
> | MPC_EnergyMaxG2V | 13.44 | ~0.00 | 100.0% | 100.00 | 43,135 |
> | TD3_vanilla ×3 | 13.44 | 4.5–5.0 | 98.0–98.3% | 82.9–83.9 | 30.9k–35.0k |
> | TD3_TrackingOnly ×3 | 13.44 | 4.6–10.9 | 98.3–99.1% | 85.7–90.2 | 33.5k–36.5k |
>
> **New finding, only visible with 50 real seeds: every TD3 checkpoint (both
> reward families, all 6 seeds) shows real, non-trivial transformer overload
> (4.5–10.9 kWh mean)** — not the near-elimination the 5-seed Week 3/4 sample
> suggested. TD3 was never trained with a hard capacity constraint (only a soft
> reward penalty), and at 50 seeds that penalty visibly does not generalize.
> This sharpens Week 4's finding: RL now also loses to Round Robin on the very
> metric (overload) its reward explicitly penalizes.

### ADD 10.13 — Week 5: AFAP overload distribution (n=50)

> Mean 14.22 kWh; median 10.32 kWh; max 78.63 kWh (per-seed mean); **28/50
> seeds (56%) show some overload**. This retires the earlier 5-seed "1-in-5,
> 20%, atypically quiet reference cell" framing: on 50 independent arrival
> draws, unmanaged charging exceeding the transformer's rating is the
> **majority-case outcome**, at a mean magnitude ~2.7× the earlier estimate.

### ADD 10.14 — Week 5: optimality gap and the value-of-information reading

> | Algorithm | tracking_error gap (% of oracle) |
> |---|---:|
> | MPC_TrackingG2V | **44.6%** |
> | Round Robin | 128.8% |
> | every TD3 checkpoint | 420–514% |
> | RandomPolicy | 571% |
> | MPC_EnergyMaxG2V | 627% |
> | AFAP | 848% |
>
> **`MPC_TrackingG2V` closes the gap Week 4 called unclosed — but it is not a
> deployment recommendation.** Both MPC arms inherit `MPC.__init__`'s knowledge
> of the exact departure time of every connected EV and the exact arrival
> time/desired energy of any EV arriving within the rolling horizon — information
> no real Bogota operator has today. Read correctly, `MPC_TrackingG2V`'s gap is
> an **upper bound on the value of building a declared-departure app feature or
> a reservation system** (the gap between Round Robin's 128.8% and MPC's 44.6%
> is "the size of the prize"), bounded above and not estimated, since real
> declared departure times are noisier than the perfect information modeled
> here. `MPC_EnergyMaxG2V` (unmodified `eMPC_G2V` under a flat price constant)
> even dominates AFAP on gross margin outright — same causality caveat.

### ADD 10.15 — Week 5: target compliance (full 50-seed grid)

> - **User satisfaction > 90%: every arm passes** (`average_user_satisfaction`
>   97.98%–100.0%; worst `TD3_vanilla_ts100`).
> - **Energy not served < 15%: adopted formally this week.** Compliance metric:
>   `ENS_rel(a,s) = (E_AFAP(s) − E_a(s)) / E_AFAP(s)`, net delivered energy,
>   paired within seed; an arm passes only if the 95% cluster-bootstrap CI
>   upper bound is below 0.15. **Every arm passes**; worst case
>   `TD3_vanilla_ts100/ts101` at CI upper ≈ 12.1% / 12.0% — the closest margin
>   in the comparison but still under 15%. `ENS_abs` (vs. actually requested
>   energy) confirms the station is not fleet-level capacity-inadequate:
>   AFAP's own `ENS_abs` is 0.025%.
> - **Voltage band: not applicable** — `simulate_grid=False`; `voltage_violation`
>   is structurally zero for every arm because the constraint is not modeled.
>   Tested only in Week 6 (IEEE 34-bus).

### ADD 10.16 — Week 5: recommended strategy for Objective 4 — Round Robin

> **Recommendation: Round Robin.** On the three declared axes:
> - **Technical compliance:** the only fully causal, deployable-today arm that
>   reduces AFAP's transformer overload to exactly zero, on a station where
>   that overload is real and substantial (56% of arrival scenarios). No
>   forecast, no training, no information advantage over a real operator.
> - **Economic cost of that compliance:** 503.9 COP/day of foregone margin
>   against a ~118,000 COP/day gross revenue base — under 1%. Gross margin is
>   retired as a ranking metric: under Colombia's flat tariff it is
>   proportional to energy delivered (formal proposition), so it cannot
>   distinguish a strategy that respects the transformer rating from one that
>   ignores it.
> - **User satisfaction / energy not served:** clears both targets by a wide
>   margin (99.9% average satisfaction; `ENS_rel` CI upper 0.75%).
>
> **What beats Round Robin and why it does not change the recommendation:**
> `MPC_TrackingG2V` and `MPC_EnergyMaxG2V` outperform it but are non-causal
> (above); both oracle variants dominate by construction and were never
> candidates; every trained RL arm loses to Round Robin on every axis measured
> (tracking error, overload, and 20×–70× more expensive per kWh of overload
> avoided). Bounded to `station_v0_bogota`'s scale and Colombia's current
> flat-tariff structure; says nothing about voltage compliance (Week 6) or a
> more heavily oversubscribed station.

### ADD 10.17 — Week 5: MPC horizon sensitivity and TD3 training-budget control

> - **MPC horizon** ({5, 10, 20} steps, 10-seed subset): a real monotonic
>   effect — tracking error falls 21% from horizon=10 (used for the main grid)
>   to horizon=20, at ~2× per-cell compute; overload and energy delivered are
>   horizon-independent (transformer capacity is a hard constraint). Horizon=20
>   would widen `MPC_TrackingG2V`'s lead, not narrow it — flagged for Week 6,
>   not re-run this week.
> - **TD3 budget curve** (`TD3_vanilla_ts100`, checkpoints 10k–60k steps,
>   10-seed subset): **no monotonic improvement**; transformer overload gets
>   *worse* at later checkpoints (0.34 kWh at 10k → 6.75–10.97 kWh at
>   50k–60k), tracking error flat/noisy throughout. This is evidence *against*
>   "the 60k budget is simply binding and a longer run would close the gap" —
>   the trajectory looks plateaued (or never trending) well before 60k. It
>   strengthens Week 4's conclusion rather than qualifying it.

---

## PART 3 — Repository-side inconsistencies to fix too (so they don't propagate)

These are inside `thesis_docs/chapters/`, not the PDF, but the PDF is transcribed
from them, so fixing them at the source prevents the same errors next week.

1. **`05_algorithm_comparison.md` S5.1** — the prose still says AFAP overload
   "mean 5.33 kWh/day", "1-in-5, 20%", "atypically quiet". Only the S5.1 margin
   table carries a Gate 4 "Updated" note. Add the same supersession note to the
   S5.1 *capacity-constrained* discussion, or move that discussion under S5.6
   and leave a pointer.
2. **`03_algorithms.md`** — the AFAP and Round Robin "Results" tables are still
   entirely on the 5-seed × 10-day grid (AFAP overload 5.33 kWh, "5 seeds x 10
   eval days"). Add a supersession banner pointing to `05_algorithm_comparison.md`
   S5.6, or regenerate the tables on the 50-seed grid.
3. **`03_rl_baseline.md` §3.8 / §3.9** — same 5-seed grid; already carries the
   2026-08-18 evaluation-bug correction but not the Week 5 grid-rebuild note.
4. **Week 3 and Week 4 chapters have no reference list** — Fujimoto et al.
   (2018) and Raffin et al. (2021) are cited implicitly (the `[?]` in the PDF)
   but never listed anywhere.
5. **`CLAUDE.md` "Current Phase"** block still says "Active phase: Week 3" at the
   top, with three stacked correction notes below it (Week 4, then Week 4-closed,
   then Week 5). It is readable but a fresh session could misread the stale
   header. Consider collapsing to a single current-state block.
