"""
Week 6, Part 0, Part B.3: evaluate the extended-training checkpoints on the
final Week 5 evaluation grid (SEEDS = 0..49 x EVAL_DAYS = 2 representative
days = 100 cells), through the REAL Week 5 evaluation path -- no
re-implementation:
  - scripts.evaluate_rl.eval_td3             (episode loop + row builder)
  - scripts.run_week5_grid._with_week5_fields (day_type/scenario_id/analysis_row/superseded)
  - ev2gym_thesis.registry.append_runs       (append-only registry writes)

Three checkpoints per training seed (100/101/102) = 9 arms x 100 cells = 900 rows:
  TD3_vanilla_extended_ts{s}       primary checkpoint (best validation
                                   tracking_error at/after convergence)
  TD3_vanilla_extended_last_ts{s}  last checkpoint (sensitivity)
  TD3_vanilla_new60k_ts{s}         the NEW run's own 60,000-step checkpoint --
                                   the primary, environment-matched budget
                                   control (user decision, Gate 1 item 2)
Training budget, selected step and selection rule are recorded in the
existing `notes` field only (no new registry columns).

The opt-in price-table cache (ev2gym_thesis/rl/price_data_cache.py) is
enabled: output-identical by a pinned test, ~10x faster env construction.

Usage:
    PYTHONPATH=. python scripts/evaluate_week6_part0.py            # dry run
    PYTHONPATH=. python scripts/evaluate_week6_part0.py --execute
"""
import argparse
import json
import os
import sys
import time

import torch

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS, TRAIN_SEEDS
from ev2gym_thesis.registry import append_runs, get_git_commit
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.rl.env_factory import DEFAULT_REWARD_FN

from scripts.evaluate_mpc import analysis_row_existing_keys
from scripts.evaluate_rl import eval_td3, REFERENCE_CONFIG_NAME
from scripts.run_week5_grid import _with_week5_fields

MODELS_DIR = "experiments/phase2_algorithms/models"
NEW60K_STEP = 60_000


# doc:begin week6_part0_arms
def extended_arms():
    """(algo_name, train_seed, checkpoint_path, notes_suffix) for all 9 arms,
    read from each run's own state.json -- the step numbers are never typed
    in by hand."""
    arms = []
    for s in TRAIN_SEEDS:
        run = f"TD3_vanilla_extended_ts{s}"
        state = json.load(open(os.path.join(MODELS_DIR, run, "state.json")))
        ckpt = lambda step: os.path.join(MODELS_DIR, run, "checkpoints", f"{run.lower()}_{step}_steps.zip")
        budget = state["last_step"]
        conv = state["evals"][state["conv_eval_index"]]["timesteps"] if state["conv_eval_index"] is not None else None
        common = f",train_budget_steps={budget},convergence_step={conv},env=post_setpoint_fix"
        if state["primary_step"] is not None:
            arms.append((f"TD3_vanilla_extended_ts{s}", s, ckpt(state["primary_step"]),
                         f",checkpoint_step={state['primary_step']},selection=primary_best_validation_after_convergence" + common))
        arms.append((f"TD3_vanilla_extended_last_ts{s}", s, ckpt(state["last_step"]),
                     f",checkpoint_step={state['last_step']},selection=last_checkpoint" + common))
        arms.append((f"TD3_vanilla_new60k_ts{s}", s, ckpt(NEW60K_STEP),
                     f",checkpoint_step={NEW60K_STEP},selection=new_run_60k_budget_control" + common))
    for _, _, path, _ in arms:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
    return arms
# doc:end week6_part0_arms


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    arms = extended_arms()
    specs = [(arm, seed, day) for arm in arms for seed in SEEDS for day in EVAL_DAYS]
    for name, s, path, notes in arms:
        print(f"{name:34s} {path}  notes+={notes}")
    print(f"{len(arms)} arms x {len(SEEDS)} seeds x {len(EVAL_DAYS)} days = {len(specs)} cells")
    if not a.execute:
        print("Dry run only -- re-run with --execute.")
        sys.exit(0)

    torch.set_num_threads(1)
    price_data_cache.enable()
    git_commit = get_git_commit()
    existing = analysis_row_existing_keys()
    appended = skipped = errors = 0
    t0 = time.perf_counter()
    for i, ((name, train_seed, path, notes), seed, day) in enumerate(specs):
        day_str = "%04d-%02d-%02d" % day
        key = (REFERENCE_CONFIG_NAME, name, str(seed), day_str)
        if key in existing:
            skipped += 1
            continue
        try:
            row = eval_td3(name, train_seed, path, DEFAULT_REWARD_FN, seed, day, git_commit)
        except Exception as exc:
            errors += 1
            print(f"[{i+1}/{len(specs)}] {name} seed{seed} {day_str}: ERROR {exc!r}")
            continue
        row = _with_week5_fields(row, seed, day)
        row["notes"] = row["notes"] + notes
        appended += append_runs([row], force=True)["appended"]
        existing.add(key)
        if (i + 1) % 100 == 0 or i + 1 == len(specs):
            print(f"[{i+1}/{len(specs)}] appended={appended} skipped={skipped} errors={errors} "
                  f"elapsed={(time.perf_counter() - t0) / 60:.1f} min", flush=True)
    print(f"Done. appended={appended}, skipped={skipped}, errors={errors}")


if __name__ == "__main__":
    main()
