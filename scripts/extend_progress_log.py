"""
Week 3, Entregable 10: appends a new "2.2. Week 3" section to the user's
personal Progress_Log_Thesis_Project.docx WITHOUT rewriting anything
already in it.

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


if __name__ == "__main__":
    if not os.path.exists(PROGRESS_LOG_PATH):
        raise FileNotFoundError(
            f"{PROGRESS_LOG_PATH!r} not found relative to the current working "
            f"directory. Run this script with PYTHONPATH=. from the repo root "
            f"(PG_IIND/), so the relative path resolves to the parent 'PG "
            f"Industrial' folder where this file actually lives."
        )
    doc = Document(PROGRESS_LOG_PATH)
    n_paragraphs_before = len(doc.paragraphs)
    build_week3_section(doc)
    doc.save(PROGRESS_LOG_PATH)
    print(f"Appended Week 3 section to {PROGRESS_LOG_PATH} "
          f"({n_paragraphs_before} paragraphs before -> {len(doc.paragraphs)} after). "
          f"Nothing before paragraph {n_paragraphs_before} was modified.")
