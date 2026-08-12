"""
Week 2 Deliverable 2 gate: verify that the `seed` argument to EV2Gym actually
reaches the EV-spawn RNG, before any multi-seed protocol is built on top of
it. Runs the same config and algorithm on the same day with seed=0 and
seed=1 and asserts total_energy_charged differs between the two runs. If it
does not, the multi-seed protocol is void and this script says so rather
than silently proceeding.

Uses station_v0_bogota.yaml read-only (not modified) and does not write to
any Week 1 result file.
"""
from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"


def run(seed):
    env = EV2Gym(config_file=CONFIG, seed=seed, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=seed)
    agent = ChargeAsFastAsPossible()
    stats = None
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break
    return stats, str(env.sim_starting_date)


if __name__ == "__main__":
    stats0, date0 = run(seed=0)
    stats1, date1 = run(seed=1)

    print(f"seed=0: sim_date={date0}, total_ev_served={stats0['total_ev_served']}, "
          f"total_energy_charged={stats0['total_energy_charged']}")
    print(f"seed=1: sim_date={date1}, total_ev_served={stats1['total_ev_served']}, "
          f"total_energy_charged={stats1['total_energy_charged']}")

    assert date0 == date1, "sim_date differs between seeds -- config bug, not a seed check"

    if stats0["total_energy_charged"] == stats1["total_energy_charged"]:
        print("\nFAIL: total_energy_charged is IDENTICAL between seed=0 and seed=1.")
        print("The seed is NOT reaching the EV-spawn RNG. The multi-seed protocol is void.")
    else:
        diff = stats1["total_energy_charged"] - stats0["total_energy_charged"]
        print(f"\nPASS: total_energy_charged differs by {diff:.4f} kWh between seed=0 and seed=1.")
        print("The seed reaches the EV-spawn RNG; the multi-seed protocol is valid.")
