"""
Week 8 advisor review, Block B item 4: calibrate the station-level
generator's arrivals/day so that the mean offered energy over the 100
evaluation cases (seeds 0-49 x {weekday 2022-01-17, weekend 2022-03-05}) is
627 kWh/day x level (1.0x, 1.3x, 1.6x), then write the 8-port / 100 kW
configs and sidecars.

Offered energy of a case = sum of the sampled requested energy of every
driver in the stream (served or rejected; drivers whose departure would fall
past the horizon are excluded, as the library does). The stream does not
depend on the control or on the number of ports, so the calibration needs
no simulation. Bisection on arrivals/day; the realised mean is a step
function of arrivals/day (inverse-CDF counts), so it stops at the first
value within 0.1% of the target.

Usage:  PYTHONPATH=. python scripts/calibrate_station_arrivals.py
Output: experiments/phase4_review/calibration.csv + configs.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.rl.env_factory import make_env


def main():
    tmp = os.path.join(os.environ.get("TEMP", "/tmp"), "w8_calib_cfg")
    envs = [make_env(rc.BASE_CONFIG, d, 0, day_config_dir=tmp) for d in rc.CALIBRATION_DAYS]
    rows = []
    for level in rc.LEVELS:
        target = rc.OFFERED_KWH_1X * level
        lo, hi = 10.0, 120.0
        for _ in range(60):
            mid = (lo + hi) / 2
            a, e = rc.offered_mean(mid, envs)
            if abs(e - target) / target < 0.001:
                break
            lo, hi = (mid, hi) if e < target else (lo, mid)
        per_type = {}
        for env, d in zip(envs, rc.CALIBRATION_DAYS):
            per_type[d] = rc.offered_mean(mid, [env])
        rows.append({"level": level, "target_offered_kwh_per_day": target, "arrivals_per_day": round(mid, 4),
                     "mean_offered_arrivals_per_day": a, "mean_offered_kwh_per_day": e,
                     "offered_kwh_per_port_per_day_8_ports": e / 8,
                     "rel_error": (e - target) / target,
                     "weekday_offered_arrivals": per_type[rc.CALIBRATION_DAYS[0]][0],
                     "weekday_offered_kwh": per_type[rc.CALIBRATION_DAYS[0]][1],
                     "weekend_offered_arrivals": per_type[rc.CALIBRATION_DAYS[1]][0],
                     "weekend_offered_kwh": per_type[rc.CALIBRATION_DAYS[1]][1], "n_cases": 100})
        print(rows[-1], flush=True)
    os.makedirs(os.path.dirname(rc.CALIBRATION_CSV), exist_ok=True)
    with open(rc.CALIBRATION_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for level in rc.LEVELS:
        print(rc.write_config(level))


if __name__ == "__main__":
    main()
