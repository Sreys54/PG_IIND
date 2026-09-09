"""
Week 5, Part B, Gate 2: time-calibrate both candidate MPC arms on
station_v0_bogota's reference cell (SEEDS[0], REFERENCE_DAY) -- the same
cell Week 4's Entregable 3 oracle calibration used, so the two numbers are
comparable.

Runs a FULL EPISODE (96 steps) for each controller, not a single solve --
unlike the offline oracle, an MPC controller re-solves at every step, so
per-cell cost is the sum of 96 receding-horizon solves, not one.

Two candidates, per the Gate 1 report (approved 2026-09-08):
  - MPCTrackingG2V (ev2gym_thesis/mpc/tracking_mpc.py) -- new code, the
    primary arm.
  - eMPC_G2V (ev2gym/baselines/mpc/eMPC.py, unmodified), registered under
    the honest name MPC_EnergyMaxG2V for evaluation purposes -- shipped
    code, included only if this calibration shows it's cheap enough to be
    worth the second arm.

Every episode starts through env_factory.reset_for_evaluation, not
env.reset() -- the Week 3 bug this project will not repeat a third time.

Usage:
    PYTHONPATH=. python scripts/calibrate_mpc_timing.py
"""
import time

from ev2gym.baselines.mpc.eMPC import eMPC_G2V

from ev2gym_thesis.eval_protocol import SEEDS, REFERENCE_DAY
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from ev2gym_thesis.mpc.tracking_mpc import MPCTrackingG2V, DEFAULT_CONTROL_HORIZON

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"


def run_one_episode(agent_cls, label, control_horizon=DEFAULT_CONTROL_HORIZON):
    seed = SEEDS[0]
    day = REFERENCE_DAY
    print(f"\n=== {label} (control_horizon={control_horizon}) ===")
    print(f"Cell: config={REFERENCE_CONFIG_PATH}, day={day}, scenario_seed={seed}")

    t_construct0 = time.perf_counter()
    env = make_env(REFERENCE_CONFIG_PATH, day, seed)
    reset_for_evaluation(env, seed)
    agent = agent_cls(env, control_horizon=control_horizon)
    construct_s = time.perf_counter() - t_construct0

    step_times = []
    t0 = time.perf_counter()
    done = False
    truncated = False
    steps = 0
    while not done and not truncated:
        t_step0 = time.perf_counter()
        actions = agent.get_action(env)
        step_times.append(time.perf_counter() - t_step0)
        _, _, done, truncated, stats = env.step(actions)
        steps += 1
    episode_s = time.perf_counter() - t0

    print(f"Agent/env construction: {construct_s:.2f}s")
    print(f"Episode steps: {steps}")
    print(f"Total episode wall-clock (get_action + env.step, all {steps} steps): {episode_s:.2f}s")
    print(f"  mean per-step get_action time: {sum(step_times)/len(step_times):.4f}s")
    print(f"  max per-step get_action time:  {max(step_times):.4f}s")
    print(f"  min per-step get_action time:  {min(step_times):.4f}s")
    per_cell_s = construct_s + episode_s
    print(f"Per-cell total (construct + full episode): {per_cell_s:.2f}s")

    n_cells = len(SEEDS) * 10  # EVAL_DAYS has 10 entries
    print(f"Linear extrapolation to the full {n_cells}-cell grid: "
          f"{n_cells} x {per_cell_s:.2f}s = {n_cells*per_cell_s/60:.1f} min")

    print(f"\nFinal stats for this cell: total_ev_served={stats.get('total_ev_served')}, "
          f"tracking_error={stats.get('tracking_error'):.2f}, "
          f"total_transformer_overload={stats.get('total_transformer_overload'):.4f}, "
          f"average_user_satisfaction={stats.get('average_user_satisfaction'):.4f}")

    return per_cell_s, n_cells


def main():
    results = {}
    per_cell_s, n_cells = run_one_episode(MPCTrackingG2V, "MPCTrackingG2V (new code)")
    results["MPCTrackingG2V"] = per_cell_s

    per_cell_s2, _ = run_one_episode(eMPC_G2V, "MPC_EnergyMaxG2V (= eMPC_G2V, unmodified, relabeled)")
    results["MPC_EnergyMaxG2V"] = per_cell_s2

    print("\n=== Summary ===")
    for name, per_cell_s in results.items():
        print(f"{name}: {per_cell_s:.2f}s/cell -> {n_cells}-cell grid = {n_cells*per_cell_s/60:.1f} min")
    total_min = sum(results.values()) * n_cells / 60
    print(f"Both arms, {n_cells} cells each ({2*n_cells} cells total): {total_min:.1f} min")

    print("\nSTOP: per CLAUDE.md rule 2 / section 11 of the Week 5 brief, do not "
          "launch a full-grid MPC run without the user's explicit scope choice.")


if __name__ == "__main__":
    main()
