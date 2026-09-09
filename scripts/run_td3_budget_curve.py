"""
Week 5, Part B: TD3 training-budget control. Checkpoints were confirmed
present (Gate 4 pre-flight) at 10k/20k/30k/40k/50k/60k steps for every
training seed -- no retraining needed, the hard gate cleared.

Evaluates TD3_vanilla_ts100's checkpoints at each of those 6 budgets on a
10-seed subset (seeds 0-9, both day types = 20 cells/checkpoint), via the
real production _TD3Stepper/_run_and_capture from scripts.evaluate_rl --
not a reimplementation.

Usage:
    PYTHONPATH=. python scripts/run_td3_budget_curve.py
"""
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS
from ev2gym_thesis.rl.env_factory import make_env, DEFAULT_REWARD_FN
from ev2gym_thesis.rl.eval_utils import load_trained_agent

from scripts.evaluate_rl import _TD3Stepper, _run_and_capture

MODEL_DIR = "experiments/phase2_algorithms/models/TD3_vanilla_ts100/checkpoints"
CHECKPOINT_STEPS = [10000, 20000, 30000, 40000, 50000, 60000]
SUBSET_SEEDS = list(range(10))


def checkpoint_paths(step):
    model_path = f"{MODEL_DIR}/td3_vanilla_ts100_{step}_steps.zip"
    vecnorm_path = f"{MODEL_DIR}/td3_vanilla_ts100_vecnormalize_{step}_steps.pkl"
    return model_path, vecnorm_path


def main():
    rows = []
    for step in CHECKPOINT_STEPS:
        model_path, vecnorm_path = checkpoint_paths(step)
        print(f"--- checkpoint={step} steps ---")
        for seed in SUBSET_SEEDS:
            for eval_day in EVAL_DAYS:
                env = make_env("experiments/phase1_baseline/configs/station_v0_bogota.yaml",
                                eval_day, seed, reward_fn=DEFAULT_REWARD_FN)
                model, venv = load_trained_agent(model_path, env, vecnormalize_path=vecnorm_path)
                stepper = _TD3Stepper(model, venv, env, scenario_seed=seed)
                stats, _, _ = _run_and_capture(stepper, env)
                rows.append({
                    "checkpoint_steps": step, "seed": seed,
                    "eval_day": f"{eval_day[0]:04d}-{eval_day[1]:02d}-{eval_day[2]:02d}",
                    "tracking_error": stats["tracking_error"],
                    "total_transformer_overload": stats["total_transformer_overload"],
                    "average_user_satisfaction": stats["average_user_satisfaction"],
                    "total_energy_charged": stats["total_energy_charged"],
                })
        print(f"  {len(SUBSET_SEEDS)*len(EVAL_DAYS)} cells done for checkpoint={step}")

    df = pd.DataFrame(rows)
    df.to_csv("results/week5_td3_budget_curve.csv", index=False)

    print("\n=== Summary: mean tracking_error / overload / satisfaction by checkpoint ===")
    summary = df.groupby("checkpoint_steps").agg(
        tracking_error_mean=("tracking_error", "mean"),
        overload_mean=("total_transformer_overload", "mean"),
        satisfaction_mean=("average_user_satisfaction", "mean"),
        energy_charged_mean=("total_energy_charged", "mean"),
    )
    print(summary.to_string())
    summary.to_csv("results/week5_td3_budget_curve_summary.csv")

    # Compare against Round Robin's oracle gap headline (136.3% at 60k full grid)
    print("\nWrote results/week5_td3_budget_curve.csv and _summary.csv")


if __name__ == "__main__":
    main()
