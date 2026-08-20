"""
Week 4 verification (user-directed, 2026-08-19): before writing anything
into the chapter about the Balanced oracle's "ObjVal identical across
weights" finding, prove it is not a silently-inert objective term rather
than a genuine "satisfaction is free at this station" result. See
thesis_docs/chapters/00_lab_log.md's 2026-08-19 entry for the report this
script's output feeds.

Checks, in order (code-order review -- var created, then constrained, then
referenced in setObjective, no shadowing -- was done by reading
ev2gym_thesis/oracle/balanced_model.py directly and is not repeated here):
1. Report the satisfaction penalty's value at the optimum directly,
   evaluated separately from ObjVal (necessary, not sufficient).
2. Absurd-weight probe (weight=1e6) -- proves nothing alone under either
   hypothesis, run anyway because it's cheap.
3. Positive control (decisive): a stressed cell (halved transformer
   capacity) where perfect satisfaction is much harder to achieve for
   free. If ObjVal is STILL identical across weights here, the term is
   dead and the "satisfaction is free" finding is not trustworthy.
4. Compare solutions (action arrays), not just objective values, between
   Balanced and Tracking-only on the original (unstressed) cell.

Usage: PYTHONPATH=. python scripts/verify_balanced_oracle_objective.py
"""
import pickle

import numpy as np

from ev2gym.baselines.gurobi_models.tracking_error import PowerTrackingErrorrMin

from ev2gym_thesis.oracle.replay_utils import build_g2v_replay_for_cell
from ev2gym_thesis.oracle.balanced_model import PowerTrackingErrorMinBalanced

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
REFERENCE_DAY = (2022, 1, 17)
REFERENCE_SEED = 0


def user_satisfaction_value(model: PowerTrackingErrorMinBalanced) -> float:
    """Sums user_satisfaction[p,i,t].X directly from the solved model --
    independent of ObjVal, so this is a real, separate measurement, not an
    inference from the objective."""
    total = 0.0
    for p in range(model.number_of_ports_per_cs):
        for i in range(model.n_cs):
            for t in range(model.sim_length):
                var = model.m.getVarByName(f"user_satisfaction[{p},{i},{t}]")
                if var is not None:
                    total += var.X
    return total


def stress_transformer(replay_path: str, factor: float, out_path: str) -> str:
    """Scales tra_max_amps/tra_min_amps by `factor` on a copy of the
    replay -- a positive-control cell where matching the setpoint AND
    fully satisfying every EV is much harder. Diagnostic only, not part of
    the production oracle pipeline (not called from evaluate_oracle.py)."""
    with open(replay_path, "rb") as f:
        replay = pickle.load(f)
    replay.tra_max_amps = replay.tra_max_amps * factor
    replay.tra_min_amps = replay.tra_min_amps * factor
    with open(out_path, "wb") as f:
        pickle.dump(replay, f)
    return out_path


if __name__ == "__main__":
    g2v_path = build_g2v_replay_for_cell(REFERENCE_CONFIG_PATH, REFERENCE_DAY, REFERENCE_SEED)

    print("=== Check 1: satisfaction penalty value at optimum, weight=1.0 ===")
    m1 = PowerTrackingErrorMinBalanced(replay_path=g2v_path, satisfaction_weight=1.0)
    sat_value = user_satisfaction_value(m1)
    print(f"user_satisfaction.sum() (measured directly, independent of ObjVal) = {sat_value}")
    print(f"ObjVal = {m1.m.ObjVal}")
    print(f"Consistent with ObjVal = power_error.sum() + 1.0*0? {abs(sat_value) < 1e-6}")

    print("\n=== Check 2: absurd-weight probe, weight=1e6 (necessary, not sufficient) ===")
    m2 = PowerTrackingErrorMinBalanced(replay_path=g2v_path, satisfaction_weight=1e6)
    sat_value_2 = user_satisfaction_value(m2)
    print(f"ObjVal at weight=1e6: {m2.m.ObjVal}, user_satisfaction.sum()={sat_value_2}")
    print(f"Identical to weight=1.0's ObjVal ({m1.m.ObjVal})? {abs(m2.m.ObjVal - m1.m.ObjVal) < 1e-3}")

    print("\n=== Check 3 (DECISIVE): positive control, transformer capacity halved ===")
    stressed_path = stress_transformer(g2v_path, 0.5, g2v_path.replace(".pkl", "__stressed.pkl"))
    objvals = {}
    sats = {}
    for w in [0.5, 1.0, 2.0]:
        m = PowerTrackingErrorMinBalanced(replay_path=stressed_path, satisfaction_weight=w)
        objvals[w] = m.m.ObjVal
        sats[w] = user_satisfaction_value(m)
        print(f"  stressed cell, weight={w}: ObjVal={m.m.ObjVal:.4f}, user_satisfaction.sum()={sats[w]:.4f}")
    all_same = len(set(round(v, 3) for v in objvals.values())) == 1
    all_sat_zero = all(abs(s) < 1e-6 for s in sats.values())
    print(f"All ObjVals identical under stress? {all_same}")
    print(f"All satisfaction penalties still exactly 0 under stress? {all_sat_zero}")
    if all_same and all_sat_zero:
        print("  -> satisfaction really is achievable for free even under this stress level "
              "(station has more slack than the stress factor removed) -- inconclusive, "
              "not proof the term is dead, but does not yet demonstrate it's live either.")
    elif not all_same:
        print("  -> TERM IS LIVE: objective differentiates by weight once satisfaction has "
              "a real cost. This is the positive evidence the check was designed to produce.")
    else:
        print("  -> objective identical but satisfaction penalty nonzero and NOT scaling the "
              "objective -- this WOULD indicate a dead term. Investigate before trusting anything.")

    print("\n=== Check 4: compare Balanced vs. Tracking-only solutions (action arrays), original cell ===")
    m_tracking = PowerTrackingErrorrMin(replay_path=g2v_path)
    actions_match = np.allclose(m1.actions, m_tracking.actions, atol=1e-6)
    print(f"Balanced (weight=1.0) actions identical to Tracking-only actions? {actions_match}")
    if not actions_match:
        diff = np.abs(m1.actions - m_tracking.actions)
        print(f"  max abs diff: {diff.max():.6f}, at index {np.unravel_index(diff.argmax(), diff.shape)}")
