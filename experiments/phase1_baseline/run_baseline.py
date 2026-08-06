"""
Week 1 baseline reproduction run: AFAP and Round Robin on station_v0_bogota.yaml.

NOTE (assumption, see thesis_docs/chapters/00_lab_log.md):
The config has random_day: True, so EV2Gym does NOT use a fixed calendar date
by default -- the simulated day is drawn from random.randint() seeded by the
`seed` argument passed to the EV2Gym constructor. To keep the config
untouched (per instructions) while still giving AFAP and Round Robin the
SAME simulated day/EV-arrival scenario for a fair comparison, both runs here
use the same fixed seed (SEED = 42). This is NOT necessarily the same day
used to produce previously reported reference values, since no seed was
recorded anywhere in this repo for that prior run.
"""
import json
from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
SEED = 42


def run(agent_cls, name):
    env = EV2Gym(config_file=CONFIG, seed=SEED, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=SEED)
    try:
        agent = agent_cls(env)
    except TypeError:
        agent = agent_cls()
    stats = None
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break
    print(f"\n=== {name} (seed={SEED}, sim_date={env.sim_starting_date}) ===")
    print(json.dumps(stats, indent=2, default=str))
    return stats, str(env.sim_starting_date)


if __name__ == "__main__":
    afap_stats, afap_date = run(ChargeAsFastAsPossible, "AFAP")
    rr_stats, rr_date = run(RoundRobin, "RoundRobin")

    with open("experiments/phase1_baseline/results/raw_stats.json", "w") as f:
        json.dump({
            "seed": SEED,
            "afap": {"sim_date": afap_date, "stats": afap_stats},
            "round_robin": {"sim_date": rr_date, "stats": rr_stats},
        }, f, indent=2, default=str)
