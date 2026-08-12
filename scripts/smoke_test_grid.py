"""
De-risking smoke test for the simulate_grid=True + IEEE 34-bus pipeline
(Objectives 4-5 infrastructure, not a Week 2 deliverable in itself -- see
thesis_docs/chapters/02_model_validation.md's grid-scope resolution).

Purpose: confirm NOW that the grid-enabled path still loads, resolves a
power flow, and emits voltage_violation / voltage_violation_counter without
error -- not to produce an interpretable result. Registers exactly ONE row
with notes="pipeline_smoke_test_grid" (config_name="v2ggrid_smoke_test"),
which MUST be filtered out of every figure and results table.

Runs ev2gym/example_config_files/V2Ggrid.yaml unmodified (upstream example,
not a project config we're protecting) with ChargeAsFastAsPossible.
"""
import datetime

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

from ev2gym_thesis.registry import append_runs, stats_to_row, get_git_commit

CONFIG = "ev2gym/example_config_files/V2Ggrid.yaml"
SEED = 12345

if __name__ == "__main__":
    env = EV2Gym(config_file=CONFIG, seed=SEED, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=SEED)
    agent = ChargeAsFastAsPossible()

    stats = None
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break

    print(f"sim_date: {env.sim_starting_date}")
    print(f"voltage_violation: {stats.get('voltage_violation')}")
    print(f"voltage_violation_counter: {stats.get('voltage_violation_counter')}")

    assert "voltage_violation" in stats, "voltage_violation missing from stats -- grid pipeline broken"
    assert "voltage_violation_counter" in stats, "voltage_violation_counter missing from stats -- grid pipeline broken"
    print("\nPASS: simulate_grid=True + IEEE 34-bus pipeline ran to completion and "
          "emitted both voltage metrics. Not interpreting the values -- this is a "
          "pipeline smoke test only.")

    row = {
        "run_id": f"v2ggrid_smoke_test__ChargeAsFastAsPossible__seed{SEED}",
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "git_commit": get_git_commit(),
        "config_name": "v2ggrid_smoke_test",
        "n_ports": 150,
        "transformer_kw": "",  # not a single value -- multiple transformers derived from the IEEE 34-bus topology
        "oversubscription_ratio": "",  # not meaningful in the same sense for a multi-transformer grid scenario
        "algorithm": "ChargeAsFastAsPossible",
        "algorithm_family": "heuristic",
        "seed": SEED,
        "eval_day": str(env.sim_starting_date).split(" ")[0],
        "sim_steps": env.simulation_length,
        "runtime_s": "",
        "notes": "pipeline_smoke_test_grid",
    }
    row.update(stats_to_row(stats))
    result = append_runs([row])
    print(f"\nRegistered: appended={result['appended']}, skipped={result['skipped']} "
          f"(config_name='v2ggrid_smoke_test' -- MUST be excluded from all figures/tables)")
