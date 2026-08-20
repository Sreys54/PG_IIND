"""
Week 4, Entregable 4: evaluate the tracking-only perfect-information oracle
(PowerTrackingErrorrMin, G2V-forced, unmodified -- see Gate 1/S4.2's
selection rationale) on the same 50-cell grid (SEEDS x EVAL_DAYS) used for
every other algorithm in this thesis, via env_factory.make_env /
config_utils.make_day_config -- the identical mechanism backfill_registry.py
and evaluate_rl.py use, so this is a paired comparison over literally
identical scenarios, not merely similar ones (verified per-cell, not
assumed -- see ev2gym_thesis.oracle.replay_utils.verify_parity below).

Algorithm: "Optimal_Oracle_Tracking", algorithm_family="optimal" -- no
training seed, no name-collision problem. total_reward is left blank in
every row: the oracle bypasses reward_function/state_function entirely
(reads a pickled replay directly, never calls env.step() during solving),
so total_reward is not a comparable or even meaningful quantity for these
rows (thesis_docs/chapters/04_oracle_and_pitd3.md S4.5).

Stepping is done on the RAW env directly (no VecEnv/DummyVecEnv wrapper at
all -- the oracle needs no SB3 machinery), so this evaluation path is
STRUCTURALLY immune to the DummyVecEnv auto-reset timeseries bug Week 3
found (thesis_docs/chapters/00_lab_log.md, 2026-08-13 entry): there is no
VecEnv here to auto-reset. Still verified explicitly after the episode loop
(env.current_power_usage.sum() > 0), not just assumed immune.

Gurobi's PowerTrackingErrorrMin calls sys.exit() if a solve does not reach
GRB.Status.OPTIMAL (confirmed by reading the source -- a real, if
surprising, behavior of the unmodified library class). Caught here via
try/except SystemExit so one infeasible/non-optimal cell cannot kill the
whole 50-cell run; that cell is recorded with an explicit marker in notes
and reported, never silently dropped.

--variant {tracking,balanced} selects which oracle model runs (default
tracking); see ev2gym_thesis/oracle/balanced_model.py for the balanced
variant's departure-satisfaction penalty and its S4.2 Amendment 1 design
rationale.

Usage:
    PYTHONPATH=. python scripts/evaluate_oracle.py                        # dry run, tracking
    PYTHONPATH=. python scripts/evaluate_oracle.py --execute              # run tracking variant
    PYTHONPATH=. python scripts/evaluate_oracle.py --execute --variant balanced  # run balanced variant
"""
import argparse
import datetime
import sys
import time

from ev2gym.baselines.gurobi_models.tracking_error import PowerTrackingErrorrMin

from ev2gym_thesis.eval_protocol import SEEDS, EVAL_DAYS
from ev2gym_thesis.rl.env_factory import make_env
from ev2gym_thesis.oracle.replay_utils import build_g2v_replay_for_cell, verify_parity
from ev2gym_thesis.oracle.balanced_model import PowerTrackingErrorMinBalanced, SATISFACTION_PENALTY_WEIGHT
from ev2gym_thesis.registry import append_runs, save_timeseries, stats_to_row, get_git_commit, load_existing_keys

REFERENCE_CONFIG_NAME = "station_v0_bogota"
REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
N_PORTS = 8
TRANSFORMER_KW = 100

# doc:begin oracle_variants
VARIANTS = {
    "tracking": {
        "algorithm_name": "Optimal_Oracle_Tracking",
        "model_cls": PowerTrackingErrorrMin,
        "model_kwargs": {},
        "notes_base": "reward=none,state=none,solver=gurobi,objective=tracking_error_only,mip_gap=default_full_optimality",
    },
    "balanced": {
        "algorithm_name": "Optimal_Oracle_Balanced",
        "model_cls": PowerTrackingErrorMinBalanced,
        "model_kwargs": {"satisfaction_weight": SATISFACTION_PENALTY_WEIGHT},
        "notes_base": (f"reward=none,state=none,solver=gurobi,"
                        f"objective=tracking_error_plus_satisfaction_penalty,"
                        f"satisfaction_weight={SATISFACTION_PENALTY_WEIGHT},"
                        f"mip_gap=default_full_optimality"),
    },
}
# doc:end oracle_variants


def run_single(seed, eval_day, git_commit, variant: str):
    spec = VARIANTS[variant]
    algorithm_name = spec["algorithm_name"]
    notes_base = spec["notes_base"]

    year, month, day = eval_day
    eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
    run_id = f"{REFERENCE_CONFIG_NAME}__{algorithm_name}__seed{seed}__{eval_day_str}"

    t0 = time.perf_counter()
    g2v_replay_path = build_g2v_replay_for_cell(REFERENCE_CONFIG_PATH, eval_day, seed)
    env = make_env(REFERENCE_CONFIG_PATH, eval_day, seed)
    verify_parity(g2v_replay_path, env)

    try:
        oracle = spec["model_cls"](replay_path=g2v_replay_path, **spec["model_kwargs"])
    except SystemExit:
        runtime_s = time.perf_counter() - t0
        print(f"  ! {run_id}: Gurobi did not reach OPTIMAL status -- recorded as infeasible/failed, not dropped.")
        row = {
            "run_id": run_id, "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "git_commit": git_commit, "config_name": REFERENCE_CONFIG_NAME,
            "n_ports": N_PORTS, "transformer_kw": TRANSFORMER_KW,
            "oversubscription_ratio": round(N_PORTS * 50 / TRANSFORMER_KW, 3),
            "algorithm": algorithm_name, "algorithm_family": "optimal", "seed": seed,
            "eval_day": eval_day_str, "sim_steps": 96, "runtime_s": round(runtime_s, 4),
            "notes": notes_base + ",status=NOT_OPTIMAL_OR_INFEASIBLE",
        }
        row.update(stats_to_row({}))
        row["total_reward"] = None
        return row

    if oracle.m.status != 2:  # GRB.Status.OPTIMAL == 2
        print(f"  ! {run_id}: Gurobi status={oracle.m.status} (not OPTIMAL) -- recorded, not dropped.")
        status_note = f",status_code={oracle.m.status}"
    else:
        status_note = ",status=OPTIMAL"

    transformer_power_ts = []
    n_connected_ts = []
    stats = None
    for t in range(env.simulation_length):
        actions = oracle.get_action(env)
        _, _, done, _, stats = env.step(actions)
        transformer_power_ts.append([tr.current_power for tr in env.transformers])
        n_connected_ts.append(sum(cs.n_evs_connected for cs in env.charging_stations))
        if done:
            break
    runtime_s = time.perf_counter() - t0

    assert env.current_power_usage.sum() > 0, (
        f"{run_id}: env.current_power_usage is all-zero after stepping -- "
        f"live-state check failed (see module docstring on why this path "
        f"should be structurally immune to Week 3's auto-reset bug)."
    )

    save_timeseries(run_id, station_power=env.current_power_usage.copy(),
                     transformer_power=transformer_power_ts, n_connected_evs=n_connected_ts)

    row = {
        "run_id": run_id, "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "git_commit": git_commit, "config_name": REFERENCE_CONFIG_NAME,
        "n_ports": N_PORTS, "transformer_kw": TRANSFORMER_KW,
        "oversubscription_ratio": round(N_PORTS * 50 / TRANSFORMER_KW, 3),
        "algorithm": algorithm_name, "algorithm_family": "optimal", "seed": seed,
        "eval_day": eval_day_str, "sim_steps": 96, "runtime_s": round(runtime_s, 4),
        "notes": notes_base + status_note,
    }
    row.update(stats_to_row(stats))
    row["total_reward"] = None  # undefined for the oracle -- never populate with a number nothing else is comparable to (S4.5)
    return row


def all_run_specs():
    return [(seed, eval_day) for seed in SEEDS for eval_day in EVAL_DAYS]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true",
                         help="Actually run the evaluation. Without this flag, only reports the plan.")
    parser.add_argument("--variant", choices=list(VARIANTS.keys()), default="tracking",
                         help="Which oracle variant to run (default: tracking).")
    args = parser.parse_args()
    algorithm_name = VARIANTS[args.variant]["algorithm_name"]

    specs = all_run_specs()
    print(f"Algorithm: {algorithm_name} (algorithm_family=optimal). "
          f"Scenario seeds: {len(SEEDS)}, eval days: {len(EVAL_DAYS)}. Total runs: {len(specs)}")

    if not args.execute:
        print("Dry run only -- did NOT write to the registry. Re-run with --execute.")
        sys.exit(0)

    git_commit = get_git_commit()
    existing_keys = load_existing_keys()
    appended_total, skipped_total, non_optimal_total = 0, 0, 0

    for i, (seed, eval_day) in enumerate(specs):
        year, month, day = eval_day
        eval_day_str = f"{year:04d}-{month:02d}-{day:02d}"
        key = (REFERENCE_CONFIG_NAME, algorithm_name, str(seed), eval_day_str)
        if key in existing_keys:
            skipped_total += 1
            print(f"[{i+1}/{len(specs)}] {algorithm_name}__seed{seed}__{eval_day_str}: skipped (already in registry)")
            continue

        row = run_single(seed, eval_day, git_commit, args.variant)
        if "NOT_OPTIMAL" in row["notes"] or "status_code=" in row["notes"]:
            non_optimal_total += 1

        result = append_runs([row])
        existing_keys.add(key)
        appended_total += result["appended"]
        skipped_total += result["skipped"]
        print(f"[{i+1}/{len(specs)}] {row['run_id']}: appended, runtime={row['runtime_s']}s, "
              f"total_ev_served={row['total_ev_served']}, "
              f"total_transformer_overload={row['total_transformer_overload']}, "
              f"tracking_error={row['tracking_error']}")

    print(f"\nEvaluation complete. appended={appended_total}, skipped={skipped_total}, "
          f"non-optimal/infeasible cells={non_optimal_total}")
    if non_optimal_total > 0:
        print(f"WARNING: {non_optimal_total} cell(s) did not reach OPTIMAL status -- "
              f"see their `notes` column before treating the grid mean as a clean bound.")
