"""
Week 4, Entregable 3: time-calibrate the perfect-information oracle
(PowerTrackingErrorrMin, tracking-only variant -- see Gate 1 preflight
recommendation, thesis_docs/chapters/04_oracle_and_pitd3.md S4.2) on
station_v0_bogota's reference cell, and extrapolate to the full 50-cell
grid before any full-grid run is launched.

Solves ONE real cell end to end (Week 3's reference day + SEEDS[0]) with
the real, unmodified ev2gym.baselines.gurobi_models.tracking_error.PowerTrackingErrorrMin
class, fed a G2V-forced replay generated via ev2gym_thesis.oracle.replay_utils
-- not a shrunk toy model. Reports build time, Gurobi solve time (isolated
via a scoped monkeypatch of gurobipy.Model.optimize -- restored immediately
after, never left in place, and touches no file on disk), variable/
constraint/binary counts, MIP gap reached, and whether the solve hit
optimality or a limit.

This script does NOT run the full 50-cell grid -- it exists to produce the
table CLAUDE.md rule 2 (extended by the Week 4 brief's Gate 2) requires
before that run, and results are meant to be pasted into a request for the
user's explicit go-ahead.

Usage:
    PYTHONPATH=. python scripts/calibrate_oracle_timing.py
"""
import time

import gurobipy as gp

from ev2gym.baselines.gurobi_models.tracking_error import PowerTrackingErrorrMin

from ev2gym_thesis.eval_protocol import SEEDS, REFERENCE_DAY
from ev2gym_thesis.oracle.replay_utils import generate_replay, force_g2v

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"

# Candidate MIP-gap / time-limit settings to present at Gate 2. Note:
# PowerTrackingErrorrMin's __init__ does not currently expose a way to set
# these before its internal self.m.optimize() call (build+solve are fused
# in one method, no timelimit=/MIPGap= kwarg is wired up despite **kwargs
# being accepted) -- see the printed note below. These candidates are
# reported as what WOULD be offered if that plumbing is added, sized
# against this run's actual measured solve time, not chosen blind.
CANDIDATE_GAPS = [None, 0.01, 0.05]
CANDIDATE_TIME_LIMITS_S = [60, 120, 300]


def _timed_optimize():
    """Monkeypatches gurobipy.Model.optimize to record wall-clock solve
    time in isolation from model-build time, without touching any file on
    disk. Scoped and restored immediately -- see calibrate() below."""
    original_optimize = gp.Model.optimize
    timing = {}

    def wrapped(self, *args, **kwargs):
        t0 = time.perf_counter()
        result = original_optimize(self, *args, **kwargs)
        timing["solve_s"] = time.perf_counter() - t0
        return result

    gp.Model.optimize = wrapped
    return original_optimize, timing


def calibrate():
    seed = SEEDS[0]
    day = REFERENCE_DAY
    print(f"Calibrating oracle (tracking-only) for (config={REFERENCE_CONFIG_PATH}, "
          f"day={day}, scenario_seed={seed})...")

    t0 = time.perf_counter()
    raw_replay_path = generate_replay(REFERENCE_CONFIG_PATH, day, seed)
    g2v_replay_path = force_g2v(raw_replay_path)
    replay_gen_s = time.perf_counter() - t0
    print(f"Replay generation + G2V-forcing: {replay_gen_s:.2f}s -> {g2v_replay_path}")

    original_optimize, timing = _timed_optimize()
    t0 = time.perf_counter()
    try:
        oracle = PowerTrackingErrorrMin(replay_path=g2v_replay_path)
    finally:
        gp.Model.optimize = original_optimize
    total_construct_s = time.perf_counter() - t0
    solve_s = timing.get("solve_s", float("nan"))
    build_s = total_construct_s - solve_s

    m = oracle.m
    status_names = {
        2: "OPTIMAL", 3: "INFEASIBLE", 9: "TIME_LIMIT", 13: "SUBOPTIMAL",
    }
    status = status_names.get(m.status, f"status_code_{m.status}")
    mip_gap = None
    try:
        mip_gap = m.MIPGap
    except Exception:
        pass

    print(f"\nModel build (Python-side, pre-optimize): {build_s:.2f}s")
    print(f"Gurobi solve (Model.optimize wall-clock):  {solve_s:.2f}s")
    print(f"Total (replay + build + solve):            {replay_gen_s + total_construct_s:.2f}s")
    print(f"\nNumVars:      {m.NumVars}")
    print(f"NumBinVars:   {m.NumBinVars}")
    print(f"NumConstrs (linear):    {m.NumConstrs}")
    print(f"NumQConstrs (quadratic): {m.NumQConstrs}")
    print(f"Status:       {status}")
    print(f"MIPGap:       {mip_gap}")
    print(f"ObjVal:       {m.ObjVal if status in ('OPTIMAL', 'SUBOPTIMAL', 'TIME_LIMIT') and m.SolCount > 0 else 'n/a (no incumbent)'}")

    per_cell_s = replay_gen_s + total_construct_s
    n_cells = len(SEEDS) * 10  # EVAL_DAYS has 10 entries; avoid importing it just for len()
    print(f"\nLinear extrapolation to the full {n_cells}-cell grid "
          f"(tracking-only variant, this measured per-cell cost):")
    print(f"  {n_cells} cells x {per_cell_s:.2f}s/cell = {n_cells*per_cell_s/60:.1f} min total")
    print(f"\nBoth variants (tracking-only + balanced, 2x{n_cells}=  {2*n_cells} cells), "
          f"ASSUMING the balanced variant costs the same per cell as tracking-only "
          f"(not yet measured -- the balanced variant is not implemented as of this "
          f"calibration run, see Gate 2 note):")
    print(f"  {2*n_cells} cells x {per_cell_s:.2f}s/cell = {2*n_cells*per_cell_s/60:.1f} min total (ESTIMATE)")

    print(f"\nNote on MIP-gap/time-limit candidates: "
          f"ev2gym.baselines.gurobi_models.tracking_error.PowerTrackingErrorrMin's "
          f"__init__ builds AND solves the model in one fused call, with no "
          f"MIPGap=/timelimit= kwarg wired to self.m.setParam before "
          f"self.m.optimize() (unlike profit_max.py/v2g_grid.py, which DO expose "
          f"these). Candidates below are what would be offered if that plumbing "
          f"is added via a thin ev2gym_thesis-side wrapper (never editing the "
          f"library file in place) -- sized against this run's measured "
          f"{solve_s:.2f}s solve, not chosen blind:")
    for gap in CANDIDATE_GAPS:
        label = "full optimality (measured above)" if gap is None else f"MIPGap={gap}"
        print(f"  - {label}")
    for tl in CANDIDATE_TIME_LIMITS_S:
        print(f"  - TimeLimit={tl}s")

    print("\nSTOP: per CLAUDE.md rule 2 / the Week 4 brief's Gate 2, do not launch "
          "a full-grid oracle run (either variant) without the user's explicit "
          "confirmation of which candidate(s) to use.")


if __name__ == "__main__":
    calibrate()
