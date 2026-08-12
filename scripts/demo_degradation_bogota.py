"""
Preliminary demo of the Bogota degradation wrapper on ONE real simulation
(not the full 500-run registry backfill, which is still paused). Runs
station_v0_bogota.yaml with AFAP, seed=0, day=2022-01-17 (already present
in the partial registry from today's backfill run), and for every EV that
had a session, compares:
  - the original ev.py calendar-aging loss (theta fixed at 298.15K = 25C)
  - the Bogota-recalibrated calendar-aging loss, outdoor profile, delta_t=0
  - the Bogota-recalibrated calendar-aging loss, outdoor profile, delta_t=+5C
  - the Bogota-recalibrated calendar-aging loss, underground profile, delta_t=0
and reports the aggregate percentage difference vs. the 25C default, plus
the measured Jensen's-gap (integrated vs. point-estimate).
"""
import numpy as np

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

from ev2gym_thesis.degradation_bogota import recompute_calendar_degradation
from ev2gym_thesis.ambient_bogota import outdoor_ambient_c, underground_ambient_c

CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
SEED = 0


def main():
    env = EV2Gym(config_file=CONFIG, seed=SEED, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=SEED)
    agent = ChargeAsFastAsPossible()
    stats = None
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break

    sim_starting_date = env.sim_starting_date
    timescale = env.timescale

    original_cal, bogota_out_0, bogota_out_5, bogota_under_0, points, integrated = [], [], [], [], [], []
    n_evs_with_session = 0

    for ev in env.EVs:
        if not ev.historic_soc:
            continue
        n_evs_with_session += 1
        d_cal_original, _ = ev.get_battery_degradation()
        original_cal.append(d_cal_original)

        r_out_0 = recompute_calendar_degradation(
            ev, sim_starting_date, timescale, outdoor_ambient_c, delta_t_charging_c=0.0)
        r_out_5 = recompute_calendar_degradation(
            ev, sim_starting_date, timescale, outdoor_ambient_c, delta_t_charging_c=5.0)
        r_under_0 = recompute_calendar_degradation(
            ev, sim_starting_date, timescale, underground_ambient_c, delta_t_charging_c=0.0)

        bogota_out_0.append(r_out_0["d_cal"])
        bogota_out_5.append(r_out_5["d_cal"])
        bogota_under_0.append(r_under_0["d_cal"])
        points.append(r_out_0["d_cal_point_estimate"])
        integrated.append(r_out_0["d_cal"])

    original_cal = np.array(original_cal)
    bogota_out_0 = np.array(bogota_out_0)
    bogota_out_5 = np.array(bogota_out_5)
    bogota_under_0 = np.array(bogota_under_0)
    points = np.array(points)
    integrated = np.array(integrated)

    print(f"EVs with a session: {n_evs_with_session}")
    print(f"sim_date: {sim_starting_date}, seed={SEED}\n")

    print("--- Sum of calendar-aging loss across all EVs (dimensionless capacity-loss units) ---")
    print(f"Original (theta=298.15K=25C fixed):        {original_cal.sum():.6e}")
    print(f"Bogota outdoor, delta_t=0:                  {bogota_out_0.sum():.6e}  "
          f"({(bogota_out_0.sum()/original_cal.sum()-1)*100:+.2f}% vs default)")
    print(f"Bogota outdoor, delta_t=+5C (charging steps):{bogota_out_5.sum():.6e}  "
          f"({(bogota_out_5.sum()/original_cal.sum()-1)*100:+.2f}% vs default)")
    print(f"Bogota underground, delta_t=0:               {bogota_under_0.sum():.6e}  "
          f"({(bogota_under_0.sum()/original_cal.sum()-1)*100:+.2f}% vs default)")

    print("\n--- Jensen's-gap: integrated A_eff vs point-estimate at mean session temperature ---")
    gap_pct = (integrated.sum() - points.sum()) / integrated.sum() * 100
    print(f"Sum(integrated) = {integrated.sum():.6e}, Sum(point-estimate) = {points.sum():.6e}")
    print(f"Point-estimate underestimates integrated calendar degradation by {gap_pct:.3f}%")


if __name__ == "__main__":
    main()
