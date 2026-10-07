"""
Week 3, Entregable 10 (extended Week 4, Entregable 13): appends a new
section per week to the user's personal Progress_Log_Thesis_Project.docx
WITHOUT rewriting anything already in it.

That file lives OUTSIDE this git repository, one directory above the repo
root (../Progress_Log_Thesis_Project.docx relative to PG_IIND/) -- it is
the user's own document, not a build artifact of this repo, so it is not
committed or regenerated from scratch the way the other hand-back
documents are. This script only appends.

Note found while building this script: the file's Weekly Progress Log
section (part 2) contains a "2.1. Week 1" subsection but NO "2.2. Week 2"
subsection -- Week 2's own instructions apparently asked for this file to
be extended too, but that never happened. This script adds Week 3 as
"2.2." (continuing the document's own existing "2.<n>. Week <n>" numbering
scheme, not the "3.x" numbering guessed at in the Week 3 task brief, since
the document's own established convention takes precedence) -- it does
NOT attempt to backfill a Week 2 section, since fabricating that content
now, after the fact, risks misrepresenting what was actually reported
in real time. Flagged for the user rather than silently patched over.

Usage: PYTHONPATH=. python scripts/extend_progress_log.py
"""
import os

from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx import Document

PROGRESS_LOG_PATH = "../Progress_Log_Thesis_Project.docx"

BLACK = RGBColor(0, 0, 0)
FONT = "Times New Roman"
SIZE = 12


def _set_run(run, bold=False):
    run.font.name = FONT
    run.font.size = Pt(SIZE)
    run.font.color.rgb = BLACK
    run.bold = bold


def add_heading(doc, text: str):
    p = doc.add_paragraph()
    run = p.add_run(text)
    _set_run(run, bold=True)
    return p


def add_body(doc, text: str):
    p = doc.add_paragraph()
    run = p.add_run(text)
    _set_run(run, bold=False)
    return p


def add_bullet(doc, text: str):
    p = doc.add_paragraph()
    run = p.add_run(f"- {text}")
    _set_run(run, bold=False)
    return p


def add_table(doc, header: list, rows: list):
    # No named table style is applied -- the source document's own tables
    # (checked before writing this) also have style=None; it doesn't define
    # a "Table Grid" style, so setting one here raises KeyError.
    table = doc.add_table(rows=1, cols=len(header))
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(header):
        p = hdr_cells[i].paragraphs[0]
        run = p.add_run(h)
        _set_run(run, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            run = cells[i].paragraphs[0].add_run(str(val))
            _set_run(run, bold=False)
    return table


def build_week3_section(doc):
    add_heading(doc, "2.2. Week 3 — RL Baseline Vanilla: TD3 (Specific Objective 3)")
    add_body(doc,
        "Scope deviation, decided before any code was written this week: the "
        "original plan assigned Week 3 to the MPC/Gurobi baseline and RL to "
        "Weeks 4-5. This was deliberately reversed — Week 3 = RL vanilla "
        "(TD3), Week 4 = a perfect-information reference computed with a free "
        "solver (no Gurobi) plus PI-TD3, Week 5 = the full comparison. Reasons: "
        "RL training is the highest-lead-time, highest-risk item in the "
        "compressed 8-week plan, and Week 2 confirmed only a restricted, "
        "non-production Gurobi license is available in this environment, not "
        "an academic one — keeping MPC in Week 3 would have made the week "
        "depend on a licensing question that was never resolved.")

    add_heading(doc, "2.2.1. Training Configuration")
    add_body(doc,
        "Algorithm: TD3 (Twin Delayed DDPG) vanilla, via Stable-Baselines3. "
        "Chosen over SAC specifically because the physics-informed PI-TD3 "
        "method planned for Week 4 is defined as an ablation on top of TD3 "
        "in the source paper — using TD3 now keeps that comparison a "
        "single-factor ablation instead of two simultaneous changes.")
    add_body(doc,
        "Reward function: SqTrError_TrPenalty_UserIncentives (tracking error "
        "plus transformer-overload and user-dissatisfaction penalties), "
        "chosen over the environment's bare tracking-only default because it "
        "is the closer match to this thesis's declared success criteria. "
        "State function: PublicPST, the environment's own default for this "
        "problem variant. Both selected from what exists in the EV2Gym "
        "library, not newly written.")
    add_body(doc,
        "Every hyperparameter has a declared origin (SB3 default, TD3 paper, "
        "or set for this project's CPU budget) — network architecture "
        "reduced to [64, 64] from the paper's [400, 300], replay buffer "
        "reduced to 50,000 from SB3's default 1,000,000, both reduced "
        "specifically for the CPU-only budget. Training budget: an explicit "
        "5,000-timestep calibration run (18.09 steps/s measured) was "
        "presented as a table of 4 candidate budgets and the user confirmed "
        "60,000 timesteps per training seed (three seeds: 100, 101, 102) "
        "before any long run was launched — a drastic, declared reduction "
        "against the source papers' 5-48 hour HPC training runs.")

    add_heading(doc, "2.2.2. Results Obtained — TD3 vs. AFAP / Round Robin / Random Control")
    add_body(doc,
        "Training: all 3 seeds completed, 167.6 minutes (2.79 hours) total "
        "wall-clock, matching the calibration estimate almost exactly. "
        "Evaluated on the identical 50-cell grid (5 seeds x 10 days) already "
        "used for AFAP/Round Robin, plus a random-policy negative control "
        "(same action space, untrained, action-space seeded with the "
        "scenario seed).")
    add_table(doc,
        ["Algorithm", "EVs served", "Profit/Cost", "Avg. satisfaction", "Min. energy satisfaction", "Transformer overload (kWh)"],
        [
            ["AFAP (uncontrolled)", "13.44", "-45.73", "100%", "100.00", "5.33"],
            ["Round Robin", "13.44", "-44.51", "100%", "99.95", "0.00"],
            ["TD3 (seed 100)", "13.00", "-28.59", "99.6%", "93.06", "0.00"],
            ["TD3 (seed 101)", "10.40", "-36.69", "99.5%", "92.31", "0.00"],
            ["TD3 (seed 102)", "12.80", "-39.69", "98.4%", "86.71", "0.98"],
            ["Random policy (control)", "13.90", "-48.19", "100%", "100.00", "12.74"],
        ])

    add_heading(doc, "2.2.3. Interpretation")
    add_body(doc,
        "TD3 learns a real, demonstrated overload-avoidance behavior: it "
        "matches Round Robin's near-elimination of transformer overload "
        "across all 3 training seeds, and — critically — the "
        "random-policy control shows WORSE overload (12.74 kWh) than even "
        "unmanaged AFAP (5.33 kWh). Without that control, \"TD3 beats AFAP\" "
        "could not be distinguished from \"any policy that spreads power "
        "around beats AFAP at this station's 4:1 oversubscription ratio\" — "
        "the control rules that out.")
    add_body(doc,
        "This comes at a real, consistent cost: lower and seed-inconsistent "
        "EVs served (10.4-13.0 vs. 13.44 for both baselines), and materially "
        "lower worst-case user satisfaction (down to 86.7% for the worst "
        "seed, vs. ~100% for every non-RL policy tested). TD3 also tracks "
        "the power setpoint measurably WORSE than the much simpler Round "
        "Robin heuristic, despite optimizing a tracking-based reward — "
        "consistent with a declared reward-vs-evaluation-metric "
        "misalignment: the training reward and the reported evaluation "
        "metrics are related but not identical quantities. Training-seed "
        "dispersion is itself substantial and reported separately from "
        "scenario-level uncertainty (e.g. EVs served varies 21.5% and "
        "tracking error varies 48.9% purely from training-seed choice, "
        "holding the evaluation grid fixed).")

    add_heading(doc, "2.2.4. Limitations Identified")
    add_bullet(doc, "Training budget is a drastic, declared reduction against the source papers (2.79h total vs. 5-48h per single HPC run) — the observed weak learning signal must be read against this, not treated as a ceiling on what TD3 could achieve with more budget.")
    add_bullet(doc, "The apparently better profit figures for TD3 are not an intentional achievement — profitability has no representation in the training reward at all, and is very likely a side effect of serving fewer EVs.")
    add_bullet(doc, "Trained and evaluated on the single reference station only — the CPU budget did not extend to the station-size sensitivity sweep.")
    add_bullet(doc, "A perfect-information reference point does not exist yet, so no strategy tested so far (including TD3) can be described as the best achievable — only as the best-performing among the strategies actually tested.")

    add_heading(doc, "2.2.5. Next Steps (Week 4)")
    add_bullet(doc, "Implement the perfect-information reference (offline upper bound) using a free solver (HiGHS/CVXPY/OR-Tools) — no Gurobi dependency.")
    add_bullet(doc, "Add PI-TD3 as a physics-informed ablation on top of this week's vanilla-TD3 wrapper.")
    add_bullet(doc, "Begin the full cross-algorithm comparison scheduled for Week 5.")


def build_week4_section(doc):
    add_heading(doc, "2.3. Week 4 — Perfect-Information Oracle, Reward Falsification, and Reward Ablation (Specific Objective 3)")
    add_body(doc,
        "Scope amended twice, both kept in the project record rather than "
        "silently revised. Amendment 1 (2026-08-19): an academic Gurobi "
        "license became active on this machine (unlimited size, expires "
        "2027-08-14), so the perfect-information reference uses Gurobi "
        "directly rather than the free-solver fallback Week 2-3 had "
        "planned around — a reduction in deviation from the original plan, "
        "not a new one. Amendment 2 (2026-08-19): the originally planned "
        "trained \"PI-TD3\" arm was replaced with a falsified "
        "physics-adaptation investigation plus a reward ablation "
        "(TD3_TrackingOnly) that actually trained — no arm named PI_TD3 "
        "exists anywhere in this project's registry, code, or results.")

    add_heading(doc, "2.3.1. Perfect-Information Oracle")
    add_body(doc,
        "Two Gurobi-based oracle variants were built as a thin wrapper "
        "around EV2Gym's own PowerTrackingErrorrMin model (never edited in "
        "place): Optimal_Oracle_Tracking (tracking error only) and "
        "Optimal_Oracle_Balanced (tracking error plus a departure-"
        "satisfaction penalty, dimensionally corrected from a bug found in "
        "the library's own profit_max.py precedent). Both forced to G2V-only "
        "(matching every other algorithm compared in this thesis) and run "
        "over the same 50-cell evaluation grid (5 seeds x 10 days) used "
        "throughout this project. Result: both oracle variants dominate "
        "every online algorithm on tracking error by a wide margin (a "
        "2x-11x gap), with the two variants tying exactly on EVs served, "
        "transformer overload, and both satisfaction metrics but showing a "
        "small, fully explained, non-zero gap on tracking error and profit "
        "(an LP-tie-break vs. nonlinear-simulator model mismatch, "
        "quantified as an explicit noise floor rather than dismissed as "
        "unexplained variance).")

    add_heading(doc, "2.3.2. Physics-Informed Reward Adaptation: Falsified, Not Abandoned")
    add_body(doc,
        "The PI-TD3 paper's actual novel mechanism (read in full: "
        "arXiv:2510.12335v2) turned out to be a K-step differentiable-"
        "rollout actor update, not primarily a reward term — porting it "
        "faithfully would mean replacing Stable-Baselines3's training loop "
        "entirely, and this station has no power-flow model to "
        "differentiate through (simulate_grid=False). A thinner, reward-"
        "only adaptation was attempted instead, explicitly declared as "
        "such. Two structurally different designs were built and verified "
        "before either was trusted with training compute, and both failed, "
        "for two independent, well-diagnosed reasons: Design 1 (an "
        "instantaneous transformer-capacity margin) was rank-correlated "
        "1.0 with the reward's existing overload penalty at every weight "
        "tested — both are monotonic functions of the same instantaneous "
        "scalar, so no weight could ever make them disagree. Design 2 (a "
        "capacity-headroom term using the environment's own connected-"
        "fleet demand potential) broke that tie but was found to reward "
        "charging EVs to full faster regardless of whether that caused a "
        "real overload — confirmed by a heuristic that already nearly "
        "eliminates overload being penalized 32x more often than one that "
        "overloads routinely. The repair that would fix this needs each "
        "EV's departure time, which this project's chosen state function "
        "withholds deliberately, matching a real public station operator's "
        "actual information. Recorded as a conditional stretch goal for "
        "the Week 6 grid-enabled phase, not a commitment.")

    add_heading(doc, "2.3.3. TD3_TrackingOnly: A Reward Ablation")
    add_body(doc,
        "With the physics-adaptation line closed, the freed training "
        "budget went to a question Week 3 assumed rather than measured: "
        "does encoding transformer-overload and user-satisfaction "
        "penalties into the training reward actually buy anything over "
        "optimizing tracking error alone? TD3_TrackingOnly held every "
        "hyperparameter identical to Week 3's vanilla-TD3 arm (60,000 "
        "timesteps/seed, the same 3 training seeds, state function, "
        "network architecture) and changed only the reward function, to "
        "EV2Gym's own bare tracking-only default — a genuinely single-"
        "variable comparison.")
    add_table(doc,
        ["Algorithm", "Avg. satisfaction", "Min. energy satisfaction", "Transformer overload (kWh)", "Tracking error"],
        [
            ["Round Robin", "100.0%", "99.95", "0.00", "12,272.97"],
            ["TD3_vanilla (mean, 3 seeds)", "98.2%", "82.5", "1.36", "29,211.59"],
            ["TD3_TrackingOnly (mean, 3 seeds)", "98.6%", "86.4", "3.10", "32,286.50"],
            ["Optimal_Oracle_Tracking", "100.0%", "100.00", "0.00", "5,192.86"],
        ])

    add_heading(doc, "2.3.4. Results Obtained")
    add_body(doc,
        "Training: all 3 seeds completed, 168.43 minutes total wall-clock "
        "(within 1.4% of the pre-training calibration estimate). "
        "Evaluated on the identical 50-cell grid: 150 rows appended, "
        "bringing the main-grid registry to exactly 550 rows (11 "
        "algorithms x 50 cells). Pooled paired-bootstrap comparison "
        "(n=150, matched training-seed-to-training-seed) against "
        "TD3_vanilla: TD3_TrackingOnly achieves better profit (+5.0%) and "
        "satisfaction (+0.4% average, +7.6% worst-case), but worse "
        "tracking error (+13.0%), transformer overload (+1.75 kWh), and "
        "battery degradation (+2.6%) — every one of these differences is "
        "statistically significant (95% CI excludes zero). Against the "
        "oracle: every TD3 variant (both reward arms, all 6 checkpoints) "
        "sits farther from the tracking-error bound than the simple Round "
        "Robin heuristic does, including the arm trained solely to "
        "minimize tracking error.")

    add_heading(doc, "2.3.5. Interpretation")
    add_body(doc,
        "The reward ablation retroactively validates Week 3's reward "
        "choice rather than merely asserting it: the composite reward "
        "(tracking + overload + satisfaction penalties) achieves real, if "
        "modest and seed-dependent, improvements in tracking error AND "
        "overload avoidance over optimizing tracking alone — the two axes "
        "it was designed to improve — at a real cost in profit and "
        "worst-case satisfaction. The cross-cutting finding first observed "
        "in Week 3 is reinforced, not just repeated: every RL variant "
        "tested across both weeks tracks the power setpoint worse than the "
        "simple Round Robin heuristic, and this persists even for the arm "
        "trained exclusively on tracking error — ruling out reward-shaping "
        "distraction as the explanation. This is now the single most "
        "robust finding spanning this project's RL work to date.")

    add_heading(doc, "2.3.6. Limitations Identified")
    add_bullet(doc, "Both TD3 reward arms show substantial cross-training-seed dispersion (up to 63.8% relative spread on individual metrics) at the declared, reduced 60,000-timestep/seed budget — a real limitation of this project's compute scope, not resolved this week.")
    add_bullet(doc, "The proposal's declared \"<15% energy error\" success target has not yet been operationalized as a concrete percentage against a specific registry metric — flagged explicitly as an open item for Week 5's final comparison rather than resolved with a guessed formula.")
    add_bullet(doc, "The physics-informed reward line is closed for this station configuration (simulate_grid=False, PublicPST) — a faithful port remains possible only if Week 6-7's grid-enabled phase provides a real voltage/power-flow signal to adapt.")
    add_bullet(doc, "Voltage-band compliance (the proposal's third declared success target) remains untested — no voltage data exists until the grid-enabled phase.")

    add_heading(doc, "2.3.7. Next Steps (Week 5)")
    add_bullet(doc, "The full cross-algorithm comparison (all 11 arms: 2 heuristics, 1 random control, 6 TD3 checkpoints across 2 reward arms, 2 oracle variants) scheduled for Week 5.")
    add_bullet(doc, "Operationalize the proposal's \"<15% energy error\" target against a specific, named registry metric before the final comparison is written up.")
    add_bullet(doc, "Carry forward the reward-ablation finding (composite reward beats tracking-only, even on tracking error itself) as a design conclusion for any further RL work in Weeks 6-7.")


def build_week5_section(doc):
    add_heading(doc, "2.4. Week 5 — Colombian Price Re-Basing and Full Algorithm Comparison (Specific Objectives 1, 3, 4)")
    add_body(doc,
        "Two parts, executed in sequence with an explicit approval gate "
        "between them. Part A re-based the project's economics on "
        "Colombian prices, retroactively, across every prior week's "
        "results. Part B, gated on Part A's approval, added the online "
        "MPC arm the roadmap originally assigned to Week 3 and produced "
        "the consolidated comparison across all algorithm families.")

    add_heading(doc, "2.4.1. Part A: Colombian Price Re-Basing")
    add_body(doc,
        "Every result through Week 4 used ENTSO-E day-ahead prices, a "
        "Netherlands dataset EV2Gym ships by default -- the weakest point "
        "in the thesis's economics up to that point. Two verified "
        "constants replace it: a retail tariff of 1,450 COP/kWh (Enel "
        "Colombia, August 2025, a single published point, not a time "
        "series) and an energy purchase cost of 865.7615 COP/kWh (Enel "
        "Colombia's own regulated tariff sheet, Nivel de Tension 2, August "
        "2026 -- the most recently published month, not an average). Both "
        "extracted and invariant-validated from stored source PDFs "
        "(scripts/fetch_enel_tariffs.py), not the live, rotating URLs.")
    add_body(doc,
        "A structural finding came out of the audit that gated this work: "
        "EV2Gym's own total_profits column is not a profit or revenue "
        "figure. Traced to source, it is the negated cost of energy "
        "purchased under ENTSO-E prices -- EV2Gym has no concept of a "
        "retail tariff charged to the driver at all. Every \"profit\" "
        "mention describing this column in Weeks 1-4's chapters was "
        "corrected forward with a dated note, not rewritten in place; the "
        "actual Colombian-peso economics (retail revenue, purchase cost, "
        "gross margin -- explicit names, never \"profit\" alone) live in a "
        "new derived table, results/economics_cop.csv, recomputed from "
        "each row's already-recorded energy delivered -- valid without "
        "re-simulating anything, since every algorithm in this project was "
        "verified, not assumed, to be price-independent.")
    add_body(doc,
        "The headline result: under Colombia's flat retail/purchase "
        "spread, gross margin is proportional to energy delivered -- "
        "formally, margin = energy x (retail - cost), a positive constant "
        "shared by every algorithm, so the margin ranking is identical to "
        "the energy-delivered ranking for any positive retail-cost spread. "
        "Consequence: AFAP, the algorithm that overloads the transformer, "
        "has the highest nominal gross margin of any arm in this project. "
        "Gross margin was retired as a ranking metric as a direct result "
        "-- reported for revenue characterization, never used to recommend "
        "a control strategy -- and the Objective 4 trade-off question was "
        "reframed around the actual decision an operator faces: the cost "
        "of respecting the transformer's rating, not who nominally earns "
        "more.")
    add_body(doc,
        "A second correction, found while verifying a connector-standard "
        "citation this chapter had inherited: Resolucion 40223 de 2021, "
        "read directly, mandates at minimum one Tipo 1 (SAE J1772) "
        "connector for AC stations and one CCS Combo 1 connector for DC "
        "stations -- not CCS Combo 2, which does not appear in the "
        "resolution's text at all. This project's config still uses CCS2, "
        "now justified by documented Enel Colombia market practice rather "
        "than an incorrect regulatory-floor claim; propagated to every "
        "file that carried the original claim, including this project's "
        "own standing-facts file (CLAUDE.md).")

    add_heading(doc, "2.4.2. Part B: MPC Causality Audit and the Two New Arms")
    add_body(doc,
        "Every controller in EV2Gym's shipped ev2gym/baselines/mpc/ "
        "library, audited class by class, turned out to be non-causal on "
        "two axes no other algorithm in this project has access to: exact "
        "departure times of connected EVs, and exact arrival information "
        "within its planning horizon -- both baked into the shared base "
        "class's constructor, independent of the receding-horizon window "
        "length. The shipped price-linear objective was also found to be "
        "provably inert under Colombia's flat tariff (Part A's own "
        "finding: it degenerates to maximizing delivered energy, not "
        "genuine price arbitrage), and, separately, was still reading live "
        "ENTSO-E prices at the point of decision -- fixed via a new "
        "wrapper class, never editing the shipped library file.")
    add_body(doc,
        "Two new arms were built as a result. MPC_TrackingG2V (new code, "
        "matching the perfect-information oracle's own tracking objective "
        "on a receding horizon) is the primary arm; MPC_EnergyMaxG2V (the "
        "shipped eMPC_G2V class, price input neutralized, honestly "
        "renamed) represents flat-price energy delivery under a hard "
        "transformer constraint. Both are explicitly framed as an upper "
        "bound on the value of information a real operator could actually "
        "acquire -- for example by adding declared-departure capture to "
        "the existing charging app -- not as deployable recommendations.")

    add_heading(doc, "2.4.3. A Structural Correction to the Evaluation Grid")
    add_body(doc,
        "Before the new arms were run at scale, a review of the existing "
        "5-seed x 10-day evaluation grid found that, for a fixed scenario "
        "seed, EV2Gym's own arrival-distribution selection depends only on "
        "whether the simulated date is a weekday or a weekend, not the "
        "specific calendar date -- so 6 of the original 10 EVAL_DAYS "
        "produced byte-identical EV populations for every algorithm, and "
        "the other 4 produced a second identical set. A second, related "
        "problem was then found and fixed at the source: EV2Gym's own "
        "power-setpoint generator wove that same day's real ENTSO-E price "
        "curve into the operational tracking target itself, so even the "
        "duplicated-population cells were not fully redundant across dates "
        "-- fixed by making the setpoint's random spread price-neutral, "
        "governed only by the scenario seed.")
    add_body(doc,
        "With that fixed, the day axis became genuinely redundant, and the "
        "evaluation design was rebuilt around what actually varies: 50 "
        "independent scenario seeds x 2 representative day types (one "
        "weekday, one weekend), 1,300 rows total across all 13 algorithm "
        "arms, run in a single homogeneous pass rather than a backfill. A "
        "matching statistical correction, a cluster bootstrap that "
        "resamples the scenario seed rather than the individual row, was "
        "added alongside the project's existing bootstrap function, not "
        "replacing it. All 953 pre-existing registry rows were kept, "
        "marked superseded rather than deleted, as provenance.")
    add_body(doc,
        "The corrected, properly-powered sample changed two conclusions "
        "materially. AFAP's transformer overload -- previously "
        "characterized from 5 seeds as a small, occasional cost (mean "
        "5.33 kWh, only 1 seed showing any overload) -- is, on 50 real "
        "seeds, a majority-case outcome: mean 14.22 kWh, median 10.32 kWh, "
        "56% of independent scenarios showing real overload. And a "
        "confidence interval that had not excluded zero on the small "
        "sample (Round Robin's overload advantage over AFAP) excludes it "
        "decisively on the corrected one.")

    add_heading(doc, "2.4.4. Consolidated Comparison Results")
    add_table(doc,
        ["Algorithm", "Overload (kWh)", "Avg. satisfaction", "Tracking error", "Gap to oracle"],
        [
            ["AFAP", "14.22", "100.0%", "56,257", "847.6%"],
            ["Round Robin", "0.00", "99.91%", "13,581", "128.8%"],
            ["MPC_TrackingG2V", "0.00", "100.0%", "8,586", "44.6%"],
            ["MPC_EnergyMaxG2V", "~0.00", "100.0%", "43,135", "626.6%"],
            ["Optimal_Oracle_Tracking", "0.00", "100.0%", "5,937", "--"],
            ["TD3_vanilla (mean, 3 seeds)", "4.7", "98.1%", "33,447", "463.4%"],
            ["TD3_TrackingOnly (mean, 3 seeds)", "8.3", "98.7%", "34,596", "482.7%"],
        ])
    add_body(doc,
        "MPC_TrackingG2V -- built specifically to bound the value of "
        "perfect departure-time information -- closes the gap to the "
        "oracle that Week 4 called unclosed, from Round Robin's 128.8% "
        "down to 44.6%. Read correctly, this is not a new recommended "
        "algorithm: it is not causal, and the gap between it and Round "
        "Robin is the size of the prize available from acquiring real "
        "departure-time information, not a deployable result. Every "
        "trained RL checkpoint still loses to Round Robin on every axis "
        "measured this week, now confirmed on a properly-powered sample "
        "rather than a 5-seed one.")

    add_heading(doc, "2.4.5. Target Compliance")
    add_body(doc,
        "All three quantitative proposal targets checked against the "
        "50-seed grid. User satisfaction (>90%): every arm passes, worst "
        "case 97.98%. Energy not served, adopted formally this week as "
        "ENS_rel = (E_AFAP - E_algorithm)/E_AFAP relative to the unmanaged "
        "baseline, gated on the 95% cluster-bootstrap confidence "
        "interval's upper bound rather than the point estimate alone: "
        "every arm passes, worst case (TD3_vanilla) at roughly 12% against "
        "the 15% threshold. A diagnostic-only absolute version (energy not "
        "served relative to each cell's actual requested energy, computed "
        "directly from the EV population, not a proxy) confirms the "
        "station itself is not capacity-inadequate -- AFAP's own value is "
        "0.025%. Voltage compliance remains not applicable: no grid model "
        "exists until Week 6.")

    add_heading(doc, "2.4.6. Recommended Strategy for Objective 4")
    add_body(doc,
        "Round Robin. Argued from evidence, not assumed: it is the only "
        "fully causal, deployable-today arm that eliminates AFAP's real "
        "and substantial transformer overload entirely, at a negligible "
        "economic cost (under 1% of daily gross revenue foregone), while "
        "clearing both the satisfaction and energy-not-served targets by a "
        "wide margin. Everything that beats it on some axis -- both MPC "
        "arms, both oracle variants -- does so using information a real "
        "Bogota operator does not have today; their value is as a bound on "
        "what acquiring that information (a declared-departure app "
        "feature, a reservation system) could be worth, not as competing "
        "recommendations. This finding is specific to this station's scale "
        "and Colombia's current flat-tariff structure, and says nothing "
        "about voltage compliance, which is Week 6's question.")

    add_heading(doc, "2.4.7. Limitations Identified")
    add_bullet(doc, "The retail tariff (August 2025) and the purchase cost (August 2026) are from different dates -- the mismatch compresses the measured margin, so every profitability figure in this project is a declared lower bound, not a central estimate.")
    add_bullet(doc, "Voltage-band compliance remains untested this week -- no grid model exists until Week 6's IEEE 34-bus phase.")
    add_bullet(doc, "The MPC arms' causal-information advantage is a declared upper bound, not an estimate of what a real declared-departure system would deliver -- real departure declarations are noisier than the perfect information modeled here.")
    add_bullet(doc, "Horizon sensitivity and the TD3 training-budget control were run on 10-seed subsets, not the full 50-seed grid, per the brief's own scope instruction -- see the full chapter for whichever of those two results landed before this document was generated.")

    add_heading(doc, "2.4.8. Next Steps (Week 6)")
    add_bullet(doc, "IEEE 34-bus grid-enabled phase (simulate_grid=True) -- the first point at which voltage compliance, the proposal's third quantitative target, can actually be tested.")
    add_bullet(doc, "A faithful PI-TD3 port remains a conditional stretch goal, contingent on Week 6's own scope, not a commitment carried over from Week 4.")
    add_bullet(doc, "Infrastructure guidelines (Objective 4) build directly on this week's recommended-strategy finding and its stated boundary conditions.")


def build_week4_correction_section(doc):
    """Same-day acceptance review (2026-08-20), appended AFTER
    build_week4_section's own 2.3.1-2.3.7 -- not a rewrite of them.
    2.3.5/2.3.6/2.3.7 above (already saved in the real file before this
    review) overstated the reward-ablation verdict, understated the
    RL-vs-Round-Robin gap-to-oracle finding, and listed the energy-error
    target as still fully open even though a mapping has now been
    proposed. All three corrected here as a new, clearly-dated subsection,
    per this project's standing convention: never silently rewrite a
    prior claim, add a marked correction instead."""
    add_heading(doc, "2.3.8. Correction (2026-08-20, same-day acceptance review)")
    add_body(doc,
        "The results reported in 2.3.4 above are unchanged; three "
        "interpretive claims in 2.3.5-2.3.7 were reviewed the same day "
        "and found to be stated more strongly -- or more weakly -- than "
        "the evidence supports. Corrected here, not rewritten in place.")
    add_bullet(doc,
        "2.3.5 called the reward ablation a validation of Week 3's reward "
        "choice. Corrected: it is a trade-off, not a validation. "
        "TD3_vanilla wins on tracking error, energy tracking error, "
        "transformer overload, and battery degradation; TD3_TrackingOnly "
        "wins on profit and both satisfaction metrics -- two of this "
        "thesis's three declared objective axes (satisfaction, "
        "profitability, technical compliance). Neither dominates. The "
        "counterintuitive direction -- optimizing tracking error alone "
        "producing a worse realized tracking error -- is recorded as a "
        "hypothesis (reduced training-budget reward shaping aiding "
        "credit assignment), not an established mechanism; a longer "
        "single-seed run would test it and is explicitly out of scope "
        "this week.")
    add_bullet(doc,
        "2.3.5 mentioned the RL-vs-Round-Robin tracking-error gap only in "
        "passing. Corrected: this is the week's real headline and is "
        "stated as such. Under a 60,000-timestep CPU training budget, "
        "reinforcement learning does not beat the simple Round Robin "
        "heuristic on tracking error, by a wide margin, consistently "
        "across two reward functions and six independent training seeds "
        "(Round Robin: 136.3% gap to the tracking-error oracle bound; "
        "every TD3 checkpoint: 422-612%). Bounded explicitly to this "
        "training budget, not claimed as a general property of RL vs. "
        "heuristics. Consequence for Objective 4's recommended-strategy "
        "question, surfaced now rather than left for Week 6: on current "
        "evidence the recommendation points toward Round Robin, not an "
        "RL method -- a legitimate, defensible conclusion this thesis is "
        "fully able to reach.")
    add_bullet(doc,
        "2.3.6/2.3.7 listed the \"<15% energy error\" target as fully "
        "open. Corrected: a concrete mapping has now been proposed (not "
        "yet adopted) -- (1 - average_user_satisfaction) x 100, using "
        "EV2Gym's own per-EV satisfaction ratio against each EV's "
        "requested (not idealized-max-rate) energy, read from source "
        "(ev2gym/models/ev.py, ev2gym/utilities/utils.py). Computed for "
        "every algorithm and arm tested through Week 4: worst observed "
        "value is 2.57% (TD3_vanilla, cross-check definition), over 5x "
        "under the 15% threshold -- every arm clears the target "
        "comfortably under either of two candidate definitions checked "
        "against each other. Week 5's task is to adopt or revise this "
        "proposal, not to define one from scratch.")


# doc:begin week6_part0_progress_log
# Week 6 Part 0: appended to the in-repo corrected Progress Log
# (thesis_docs/Progress_Log_Thesis_Project_corrected_2026-09-09.docx), per
# the user's instruction -- that file's week sections are numbered as
# top-level sections ("9. Week 4", "10. Week 5", "11. Standing Corrections"),
# so this is "12.". Extend, never rewrite; plain black text, bold titles, no
# Word Heading styles (the existing sections do use Heading styles -- this
# addition follows the user's standing rule instead, declared here).
CORRECTED_PROGRESS_LOG_PATH = "thesis_docs/Progress_Log_Thesis_Project_corrected_2026-09-09.docx"
WEEK6_PART0_TITLE = "12. Week 6, Part 0 -- Extended Training of the Selected RL Policy"


def build_week6_part0_section(doc):
    add_heading(doc, WEEK6_PART0_TITLE)

    add_heading(doc, "12.1. Objective")
    add_body(doc,
        "At the advisor's request, the best already-trained RL arm was trained until its learning curve "
        "stabilised, so that a single RL model can be carried into Objectives 4 and 5. No trained arm beat "
        "Round Robin in Week 5 (S5.8). TD3_vanilla (reward SqTrError_TrPenalty_UserIncentives) was extended "
        "because it is the best RL arm on the Week 5 tracking-error ranking, not because it is an overall "
        "winner. The experiment answers one question: was the RL result limited by its 60,000-step training "
        "budget?")

    add_heading(doc, "12.2. Design")
    add_bullet(doc, "Identical algorithm, hyperparameters, reward, state, station configuration and training seeds "
                    "(100, 101, 102) as the original runs. Trained from scratch, three seeds in parallel, one torch "
                    "thread per process, simulate_grid = False.")
    add_bullet(doc, "Deterministic validation every 10,000 steps on 20 fixed cells (seeds 1,000,000-1,000,009 on "
                    "one weekday and one weekend day), disjoint by construction from every training scenario and "
                    "from the evaluation grid. Each saved checkpoint is reloaded with frozen normalisation "
                    "statistics before it is scored.")
    add_bullet(doc, "Selection criterion: validation-mean tracking error. Transformer overload and energy user "
                    "satisfaction were logged as secondary metrics.")
    add_bullet(doc, "Convergence rule (labelled assumption, fixed before launch): over windows of W = 5 evaluations, "
                    "the relative change of the window mean is below 2% and the relative standard deviation is "
                    "below 5%, on 3 consecutive evaluations. Then 100,000 confirmation steps, or a hard stop at "
                    "10:15 (UTC-5).")
    add_bullet(doc, "Primary checkpoint: the best criterion value at or after convergence; the last checkpoint is "
                    "kept as a sensitivity case. The primary comparator is the new run's own 60,000-step "
                    "checkpoint, because the Week 3-5 models were trained before the Week 5 power-setpoint fix "
                    "and evaluated after it.")
    add_bullet(doc, "Implementation safeguards, each covered by a test:")
    add_bullet(doc, "  the monitor restores the random generators EV2Gym reseeds, so it does not change training;")
    add_bullet(doc, "  an output-identical cache of EV2Gym's price table raised throughput from 13.8 to 86 steps/s "
                    "per seed;")
    add_bullet(doc, "  a leakage guard redraws any training scenario that lands on an evaluation seed "
                    "(0 hits in 21,354 episodes).")

    add_heading(doc, "12.3. Convergence")
    add_table(doc, ["Seed", "Converged at", "Stopped at", "Wall clock", "Validation TE at 60k",
                    "Validation TE, last 5 evaluations", "Primary checkpoint"],
              [["100", "380,000", "480,000", "2.19 h", "33,070", "45,476 +/- 2,093", "400,000"],
               ["101", "560,000", "660,000", "2.88 h", "33,650", "47,569 +/- 1,109", "630,000"],
               ["102", "810,000", "910,000", "3.69 h", "30,798", "45,978 +/- 1,064", "850,000"]])
    add_body(doc,
        "All three seeds met the convergence rule and stopped on their own well before the deadline. There "
        "were no crashes or resumes. The curves stabilised at a worse level than the policy had at 30k-70k "
        "steps, which is where every seed reached its best validation tracking error. The first 60,000 steps "
        "fall within the original run-to-run noise band. This is a comparison, not a reproduction: the "
        "setpoint generator and the thread count differ from the original runs.")

    add_heading(doc, "12.4. Test-Grid Results (50 seeds x 2 day types, n_clusters = 50)")
    add_table(doc, ["Checkpoint family (3-seed mean)", "Tracking error", "Overload (kWh)", "Avg. satisfaction",
                    "ENS_rel range"],
              [["Original 60k (pre-fix, reference)", "33,447", "4.72", "98.13%", "8.56-9.98%"],
               ["New run 60k (primary comparator)", "32,509", "6.08", "97.82%", "3.91-20.04%"],
               ["Extended, primary checkpoint", "43,211", "6.82", "99.64%", "1.61-2.20%"],
               ["Extended, last checkpoint", "46,243", "7.95", "99.81%", "0.92-1.70%"],
               ["Round Robin", "13,581", "0.00", "99.91%", "0.47%"]])
    add_body(doc,
        "Extended primary vs. new-run 60k (paired cluster bootstrap, 95% CI):")
    add_bullet(doc, "tracking error +10,701 [+9,042, +12,472];")
    add_bullet(doc, "overload +0.74 kWh [-1.98, +3.40];")
    add_bullet(doc, "average satisfaction +0.018 [+0.016, +0.021].")
    add_body(doc,
        "Extended primary vs. Round Robin: tracking error +29,629, overload +6.82 kWh, satisfaction -0.0027, "
        "with every CI excluding zero. One new-run 60k checkpoint (seed 101) fails the <15% energy-not-served "
        "target (20.04%, CI upper bound 22.85%). Across training seeds, the spread of tracking error went from "
        "8.3% to 7.3% and the spread of overload from 30.8% to 82.9%.")

    add_heading(doc, "12.5. Verdict")
    add_bullet(doc, "Extended training did not improve the selection criterion. Test tracking error is worse "
                    "than the same seed's new-run 60k checkpoint for all three seeds: +13,241 / +10,243 / +8,620, "
                    "every 95% cluster-bootstrap CI excluding zero, n_clusters = 50. The convergence rule "
                    "detected a plateau, not an improvement.")
    add_bullet(doc, "User outcomes improved and their across-seed spread shrank. Average satisfaction +0.018 "
                    "[+0.016, +0.021]. ENS_rel fell from 3.9-20.0% to 1.6-2.2%, with its range across seeds "
                    "going from 16.1 to 0.6 pp. Overload did not change significantly (+0.74 kWh "
                    "[-1.98, +3.40]).")
    add_bullet(doc, "Interpretation, verified against the data: the extended policies deliver more energy "
                    "(+18.6 kWh/day [+15.9, +21.2]) and achieve a BETTER total training reward (+3,997 "
                    "[+2,340, +5,790]). Extended training optimised its own reward better, and that reward "
                    "values satisfaction over setpoint tracking. The proposed wording 'rather than reaching "
                    "a better reward' was not supported by the data and was dropped.")
    add_bullet(doc, "Round Robin has lower tracking error and overload than every implementable arm (all CIs "
                    "exclude zero). The gap is not a budget artefact for the one arm that was extended "
                    "(about 14x its original budget). The Round Robin recommendation stands.")
    add_heading(doc, "12.6. Final RL Model (Author's Decision)")
    add_body(doc,
        "The single RL model for the rest of the thesis is TD3_vanilla extended, training seed 102, primary "
        "checkpoint at 850,000 steps (validation tracking error 40,378, against 42,531 for seed 100 and "
        "46,554 for seed 101). It is kept for four reasons: the advisor's request for one stabilised model; "
        "the lowest overload of all 15 TD3 checkpoints (3.58 kWh/day); its ENS_rel of 2.20% and "
        "average satisfaction of 99.59%; and being the longest-trained seed. Its worse tracking than its own "
        "60k checkpoint (41,195 against 32,575, +8,620 [+6,877, +10,419]) is declared as the accepted "
        "trade-off.")

    add_heading(doc, "12.7. Limitations")
    add_bullet(doc, "The Week 3-5 RL models were trained before the power-setpoint fix and evaluated after it. "
                    "The new-run 60k checkpoints are statistically indistinguishable from them on tracking error "
                    "(-937, CI [-2,125, +236]).")
    add_bullet(doc, "Training ran on a laptop CPU for 2.2-3.7 h per seed (480k-910k steps). The reference papers "
                    "trained for 5-48 h on HPC, so no equivalence is claimed.")
    add_bullet(doc, "Convergence means the validation criterion stopped changing, not that the policy improved. "
                    "The thresholds are empirically set.")


# doc:begin week7_progress_log
# Week 7 (final practical phase): sections "13." (Objective 4) and "14."
# (Objective 5), continuing section "12." (Week 6 Part 0). Numbers are read
# from the results CSVs at render time, never typed in.
WEEK7_O4_TITLE = "13. Week 7 -- Objective 4: Infrastructure Guidelines on the Grid-Enabled Model"
WEEK7_O5_TITLE = "14. Week 7 -- Objective 5: Replicability in Medellin"


def _f(x, nd=2):
    return f"{x:,.{nd}f}"


def build_week7_o4_section(doc):
    import pandas as pd
    eq = pd.read_csv("results/week7_grid_base_equivalence_all_arms.csv")
    mc = pd.read_csv("results/week7_grid_master_comparison.csv")
    sz = pd.read_csv("results/week7_transformer_sizing.csv")
    va = pd.read_csv("results/week7_voltage_attribution.csv")
    tc = pd.read_csv("results/week7_target_compliance.csv")
    mg = pd.read_csv("results/week7_grid_margin_bogota.csv")
    probe = pd.read_csv("results/week7_voltage_probe.csv")
    add_heading(doc, WEEK7_O4_TITLE)
    add_heading(doc, "13.1. Objective and Model")
    add_body(doc,
        "The reference station (8 ports, 100 kW transformer) was placed on bus 27, the electrically farthest bus, "
        "of EV2Gym's 34-node feeder (RL-ADN network, not validated against the IEEE data). Five arms were run on five "
        "growth settings, 50 scenario seeds x 2 day types each: AFAP, Round Robin, MPC_TrackingG2V, the final RL "
        "model (TD3 extended, seed 102) and the tracking oracle. Axis 1 raises the station demand (spawn multiplier "
        "1.0/1.3/1.6x); Axis 2 raises the feeder's background load (1.0/1.3/1.6). Statistics use the paired cluster "
        "bootstrap over scenario seeds (n_clusters = 50).")
    add_heading(doc, "13.2. Validation of the Grid-Enabled Model")
    add_body(doc,
        f"At the base setting, every grid row equals the non-grid row of the same arm, seed and day on every station "
        f"metric (maximum absolute difference {eq.max_abs_diff.max():g} over {int(eq.n_cells.iloc[0])} cells and "
        f"{int(eq.n_arms.iloc[0])} arms). The grid adds voltage and changes nothing else. The final RL model sees "
        f"bit-identical observations under the grid. EV2Gym has no key to place a station on a bus; a wrapper "
        f"outside the library was needed, because otherwise the 8 stations would be spread over 8 buses with "
        f"800 kW of transformers.")
    lo = probe.groupby("load_multiplier").n_bus_steps_outside.apply(lambda s: (s > 0).any())
    add_body(doc,
        f"Voltage band: EV2Gym measures 0.95-1.05 p.u. (+/-5%). The metric first trips at load multiplier "
        f"{min(lo[lo].index):g}. At the nominal load, the feeder is already outside the band at bus 27 with the "
        f"station idle, so voltage is reported only as the station's increment over the idle station of the same "
        f"cell. No absolute RETIE compliance claim is made.")
    add_heading(doc, "13.3. Results by Guideline")
    for st in ["base", "spawn1.3", "spawn1.6", "load1.3", "load1.6"]:
        rr = mc[(mc.setting == st) & (mc.algorithm == "RoundRobin")].iloc[0]
        af = sz[(sz.setting == st) & (sz.algorithm == "ChargeAsFastAsPossible")].iloc[0]
        rl = mc[(mc.setting == st) & (mc.algorithm == "TD3_vanilla_extended_ts102")].iloc[0]
        vrr = va[(va.setting == st) & (va.algorithm == "RoundRobin")].iloc[0]
        vaf = va[(va.setting == st) & (va.algorithm == "ChargeAsFastAsPossible")].iloc[0]
        mrr = mg[(mg.setting == st) & (mg.algorithm == "RoundRobin")].iloc[0]
        add_bullet(doc,
            f"{st}: Round Robin satisfaction {rr.average_user_satisfaction_mean*100:.2f}% "
            f"[{rr.average_user_satisfaction_ci_low*100:.2f}, {rr.average_user_satisfaction_ci_high*100:.2f}], "
            f"overload {_f(rr.total_transformer_overload_mean)} kWh/day; AFAP overloads in "
            f"{int(af.seeds_with_overload)}/50 seeds, 95th-percentile peak {_f(af.peak_kw_p95, 1)} kW (next standard "
            f"size {af.next_standard_kva_unity_pf:g} kVA); final RL tracking error {_f(rl.tracking_error_mean, 0)} vs "
            f"Round Robin {_f(rr.tracking_error_mean, 0)}; station-attributable out-of-band samples: AFAP "
            f"{_f(vaf.delta_bus_steps_outside_mean)} [{_f(vaf.delta_bus_steps_outside_ci_low)}, "
            f"{_f(vaf.delta_bus_steps_outside_ci_high)}], Round Robin {_f(vrr.delta_bus_steps_outside_mean)} "
            f"[{_f(vrr.delta_bus_steps_outside_ci_low)}, {_f(vrr.delta_bus_steps_outside_ci_high)}]; feeder out of band "
            f"with the station idle in {int(vrr.cells_idle_feeder_outside_band)}/100 cells; Round Robin concedes "
            f"{_f(mrr.margin_conceded_vs_afap_cop_per_day, 0)} COP/day vs AFAP "
            f"[{_f(mrr.conceded_ci_low, 0)}, {_f(mrr.conceded_ci_high, 0)}].")
    add_heading(doc, "13.4. Target Compliance")
    for st in ["base", "spawn1.3", "spawn1.6", "load1.3", "load1.6"]:
        g = tc[tc.setting == st]
        parts = [f"{a}: sat {'Y' if r.satisfaction_target_met_ci_lower_gt_90pct else 'N'}, "
                 f"ENS {'Y' if r.ens_target_met_ci_upper_lt_15pct else 'N'}, "
                 f"voltage-increment {int(r.voltage_cells_station_adds_outside_samples)}/{int(r.voltage_cells_total)} cells"
                 for a, r in zip(g.algorithm, g.itertuples())]
        add_bullet(doc, f"{st}: " + "; ".join(parts) + ".")
    add_body(doc, "Full argument, tables and figures (f15-f17): thesis_docs/chapters/06_infrastructure.md.")


def build_week7_o5_section(doc):
    import pandas as pd
    from ev2gym_thesis.prices import medellin as med
    rep = pd.read_csv("results/week7_replicability_margin.csv")
    inv = pd.read_csv("results/week7_ranking_invariance.csv")
    add_heading(doc, WEEK7_O5_TITLE)
    add_heading(doc, "14.1. City, Data and Invariants")
    add_body(doc,
        f"Medellin (EPM). Source: EPM regulated-market tariff sheet, September 2026, accessed 2026-10-05. "
        f"Nivel II commercial with contribution: Punta {med.EPM_NIVEL2_PUNTA_CON_CONTRIBUCION} and Fuera de Punta "
        f"{med.EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION} COP/kWh. Without contribution: "
        f"{med.EPM_NIVEL2_PUNTA_SIN_CONTRIBUCION} / {med.EPM_NIVEL2_FUERA_PUNTA_SIN_CONTRIBUCION}. Both Week 5 "
        f"invariants hold (component sum; 1.20x contribution). EPM publishes no EV charging price, so Bogota's 1,450 "
        f"COP/kWh is used only as a labelled sensitivity. The intraday spread is "
        f"{med.INTRADAY_SPREAD_MEDELLIN*100:.2f}%, against 1.57% in Bogota.")
    add_heading(doc, "14.2. Tariff Transfer")
    ng = rep[(rep.dataset == "nongrid") & (rep.algorithm == "RoundRobin")].set_index("price_scenario")
    add_body(doc,
        f"Round Robin's cost of respecting the 100 kW limit (margin conceded vs AFAP, non-grid rows): Bogota "
        f"{_f(ng.loc['bogota_base','margin_conceded_vs_afap_cop_per_day'],1)} COP/day "
        f"[{_f(ng.loc['bogota_base','conceded_ci_low'],1)}, {_f(ng.loc['bogota_base','conceded_ci_high'],1)}], Medellin "
        f"{_f(ng.loc['medellin_base','margin_conceded_vs_afap_cop_per_day'],1)} COP/day "
        f"[{_f(ng.loc['medellin_base','conceded_ci_low'],1)}, {_f(ng.loc['medellin_base','conceded_ci_high'],1)}], "
        f"n_clusters = 50. The ranking of the arms by margin equals their ranking by energy in all "
        f"{inv.price_scenario.nunique()} price scenarios and all {inv.dataset.nunique()} datasets: "
        f"{bool(inv.same_as_energy_ranking.all() and inv.ranking_identical_across_all_price_scenarios.all())}.")
    add_heading(doc, "14.3. What Transfers")
    add_bullet(doc, "Transfers fully: the strategy ranking and recommendation (tariff-invariant under a flat price) "
                    "and the relative cost of the transformer limit.")
    add_bullet(doc, "Replaced: energy purchase cost and intraday spread. Unavailable, so kept and declared: the retail "
                    "price, arrival data (Dutch in both cities), per-station demand, the feeder and the climate.")
    add_bullet(doc, "Demand: city EV registrations (Medellin/Bogota = 0.40, Jan-Aug 2025) do not give per-station "
                    "demand. Guidelines are conditional on the demand level, and the 0.4-0.9x runs are proposed, "
                    "not run.")
    add_body(doc, "Full argument: thesis_docs/chapters/07_replicability.md.")
# doc:end week7_progress_log


# doc:begin closure_progress_log
CLOSURE_TITLE = "15. Closure -- Corrections, Capacity Threshold and Colombian Replicability"


def build_closure_section(doc):
    """Closure brief (2026-10-06). Appended after section 14; earlier
    paragraphs are corrected by reference (15.1), never edited."""
    import pandas as pd
    brk = pd.read_csv("results/closure_c1_breaking_levels.csv").set_index("algorithm")
    c2 = pd.read_csv("results/closure_c2_options.csv")
    tc = pd.read_csv("results/closure_target_compliance.csv").set_index("algorithm")
    cost = pd.read_csv("results/closure_multicity_rr_cost.csv")
    tar = pd.read_csv("results/closure_multicity_tariffs.csv").set_index("city")
    vc = pd.read_csv("results/closure_voltage_contribution.csv").set_index("setting")
    add_heading(doc, CLOSURE_TITLE)

    add_heading(doc, "15.1. Corrections to Earlier Sections (dated 2026-10-06)")
    add_bullet(doc, "Section 8.1.4 (Week 1 parameters), 'one 60 kWh battery profile': the configured battery is 70 kWh "
                    "(station_v0_bogota.yaml, ev.battery_capacity). 60 kWh was never simulated.")
    add_bullet(doc, "Section 8.3.11 (Week 3 corrected experiment), AFAP overload '5.33 kWh' and the RandomPolicy comparison: these "
                    "are values from the superseded 5-seed grid. The current grid gives AFAP 14.22 kWh/day [9.58, 19.28] "
                    "and the random control 3.32 kWh/day [1.75, 5.17], n_clusters = 50.")
    add_bullet(doc, "Section 10.16 (Week 5), '503.9 COP/day': the current value is 551.9 COP/day [274.3, 874.2] "
                    "(regenerated from the analysis rows; the 503.9 came from a stale CSV).")
    add_bullet(doc, "Sections 9.7 and 10.15 (success targets) and 13.3-13.4 (Week 7), 'satisfaction met / unchanged' and "
                    "'ENS met by every arm': withdrawn as statements about the station's users. EV2Gym silently "
                    "drops arrivals at occupied ports, so these metrics cover served EVs only (15.2).")
    add_bullet(doc, "Section 14.2-14.3 (Week 7), ranking invariance and the equal relative cost in both cities: "
                    "these are consequences of a proposition (15.4), not empirical findings.")

    add_heading(doc, "15.2. Arrivals at Full Ports")
    add_body(doc,
        "EV2Gym draws arrivals per port and never creates an EV whose port is occupied (utils.py, EV_spawner). "
        "A replay of the spawner's random draws, from outside the library, counts these rejected arrivals. "
        "Demand not served (rejected energy plus shortfall, over total requested) for Round Robin at the reference "
        "demand is 34.6% [30.8, 38.4] (lower bound, n_clusters = 50). The 8 ports, not the transformer or the "
        "policy, are the binding constraint.")

    add_heading(doc, "15.3. Capacity Threshold and What Closes It")
    for arm, label in [("RoundRobin", "Round Robin"), ("ChargeAsFastAsPossible", "AFAP"),
                       ("TD3_vanilla_extended_ts102", "Final RL model")]:
        r = brk.loc[arm]
        unit = "kW" if r.first_criterion_broken == "peak" else "%"
        v = (r.value, r.ci_low, r.ci_high) if unit == "kW" else (100 * r.value, 100 * r.ci_low, 100 * r.ci_high)
        add_bullet(doc, f"{label}: breaks at {r.breaking_level_label} on {r.first_criterion_broken} "
                        f"({v[0]:.2f} {unit} [{v[1]:.2f}, {v[2]:.2f}], n_clusters = {int(r.n_clusters)}).")
    for lvl, ports in [(0.75, 10), (1.0, 12)]:
        r = c2[(c2.level == lvl) & (c2.algorithm == "RoundRobin") & (c2.ports == ports)
               & c2.station_demand.str.startswith("constant") & (c2.transformer_kw == 100.0)].iloc[0]
        add_bullet(doc, f"At {r.level_label}: {ports} ports with Round Robin on the 100 kW transformer (constant "
                        f"station demand) give demand not served {100 * r.dns_lower_mean:.2f}% "
                        f"[{100 * r.dns_lower_ci_low:.2f}, {100 * r.dns_lower_ci_high:.2f}] and "
                        f"+{r.delta_gross_margin_cop:,.0f} COP/day of margin. A larger transformer changes nothing "
                        f"for Round Robin.")

    add_heading(doc, "15.4. Replicability Across the Six Categoria Especial Cities")
    add_body(doc,
        "Proposition: under a flat tariff, margin = energy x (retail - cost), so the margin ranking equals the energy "
        "ranking and the relative cost of the transformer limit equals the relative energy foregone, whatever the "
        "price. Cities (CGN, vigencia 2026): Bogota, Medellin, Cali, Barranquilla, Cartagena, Bucaramanga.")
    for city, t in tar.iterrows():
        c = cost[(cost.city == city) & (cost.retail_price_label == "1450_reference")].iloc[0]
        sp = "none published" if pd.isna(t.intraday_spread) else f"{100 * t.intraday_spread:.2f}%"
        tou = "" if pd.isna(c.conceded_tou_cop_day) else f", two-band {c.conceded_tou_cop_day:,.0f}"
        add_bullet(doc, f"{city} ({t.operator}, {t.sheet_month}): Nivel 2 flat cost {t.flat_cost_con_contribucion:,.2f} "
                        f"COP/kWh, spread {sp}, unit margin at 1,450 = {t.unit_margin_at_1450:,.1f}; Round Robin's "
                        f"cost of the limit {c.conceded_flat_cop_day:,.0f} COP/day flat{tou}.")
    add_body(doc, "The spread is not small everywhere: Air-e (Barranquilla) publishes a 10% two-band option, under which "
                  "Round Robin's cost of the limit is about 3.6 times the flat value. Below 0.733x the Bogota demand the "
                  "guideline holds (0.5x tested); no city is mapped onto the demand axis.")

    add_heading(doc, "15.5. Voltage")
    b = vc.loc["base"]
    v123 = pd.read_csv("results/closure_ieee123_voltage.csv")
    rr123 = v123[(v123.level == 1.0) & (v123.algorithm == "RoundRobin")].iloc[0]
    add_body(doc,
        f"EV2Gym has no feeder-to-station feedback (source-confirmed). On the 34-node feeder, which is out of band "
        f"with the station idle, Round Robin lowers the feeder's daily minimum voltage {100 * b.rr_reduction_vs_afap:.1f}% "
        f"less than AFAP [{100 * b.reduction_ci_low:.1f}, {100 * b.reduction_ci_high:.1f}] at the base setting. Of "
        f"EV2Gym's shipped feeders only node_123 is in band with the station idle; AFAP and Round Robin rerun on it "
        f"(50 seeds, weekday only, 1.0-1.6x) leave the +/-5% band in {int(v123.cells_out_of_band.sum())} cells "
        f"(lowest bus {v123.min_voltage_pu_worst.min():.4f} p.u.), and Round Robin's reduction there is "
        f"{100 * rr123.rr_reduction_vs_afap:.1f}% [{100 * rr123.reduction_ci_low:.1f}, {100 * rr123.reduction_ci_high:.1f}] "
        f"at 1.0x. node_123 is a test network, not a Colombian feeder.")

    add_heading(doc, "15.6. Final Target Compliance (reference demand, n_clusters = 50)")
    for arm, r in tc.iterrows():
        yn = lambda x: "met" if bool(x) else "not met"
        add_bullet(doc, f"{arm}: satisfaction (served EVs) {yn(r.sat_served_met)}; satisfaction counting rejected "
                        f"arrivals {100 * r.sat_all_arrivals_mean:.1f}% ({yn(r.sat_all_arrivals_met)}); ENS_rel "
                        f"{yn(r.ens_rel_met)}; demand not served {100 * r.dns_lower_mean:.1f}% ({yn(r.dns_met)}); "
                        f"transformer {yn(r.transformer_met)}; voltage {r.voltage_status}.")
    add_body(doc, "Full argument: thesis_docs/Closure_Parameter_Method_and_Implementation_Justification.docx and "
                  "chapters 06-08.")
# doc:end closure_progress_log


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["week5", "week6_part0", "week7", "closure"], required=True,
                    help="which section to append (each runs once; nothing already in the file is modified)")
    args = ap.parse_args()
    path = CORRECTED_PROGRESS_LOG_PATH if args.section in ("week6_part0", "week7", "closure") else PROGRESS_LOG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path!r} not found relative to the current working directory. Run this script with "
            f"PYTHONPATH=. from the repo root (PG_IIND/)."
        )
    doc = Document(path)
    n_paragraphs_before = len(doc.paragraphs)
    if args.section == "week5":
        # Week 3, Week 4, and the Week 4 correction were already appended in
        # earlier sessions; Week 5 was appended as "2.4. Week 5".
        build_week5_section(doc)
    elif args.section == "closure":
        if any(p.text.strip() == CLOSURE_TITLE for p in doc.paragraphs):
            raise SystemExit(f"{CLOSURE_TITLE!r} already present in {path} -- not appending twice.")
        build_closure_section(doc)
    elif args.section == "week7":
        if any(p.text.strip() in (WEEK7_O4_TITLE, WEEK7_O5_TITLE) for p in doc.paragraphs):
            raise SystemExit(f"Week 7 sections already present in {path} -- not appending twice.")
        build_week7_o4_section(doc)
        build_week7_o5_section(doc)
    else:
        if any(p.text.strip() == WEEK6_PART0_TITLE for p in doc.paragraphs):
            raise SystemExit(f"{WEEK6_PART0_TITLE!r} already present in {path} -- not appending twice.")
        build_week6_part0_section(doc)
    doc.save(path)
    print(f"Appended {args.section} section to {path} "
          f"({n_paragraphs_before} paragraphs before -> {len(doc.paragraphs)} after). "
          f"Nothing before paragraph {n_paragraphs_before} was modified.")
# doc:end week6_part0_progress_log
