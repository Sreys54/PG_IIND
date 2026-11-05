"""
Week 8 advisor review, A8: the Week 1 transformer sweep (250, 150, 100, 75,
50 kW), re-run because no stored rows exist (the Week 1 progress log says
the raw output is in 00_lab_log.md; it is not -- searched 2026-11-03).

Protocol: the Week 1 reference config (experiments/phase1_baseline/configs/
station_v0_bogota.yaml: 8 ports, spawn_multiplier 30, 2022-01-17) with only
transformer.max_power changed, AFAP (ChargeAsFastAsPossible):
  (a) the Week 1 single case, scenario seed 42 (experiments/phase1_baseline/
      results/baseline_afap.csv: 0.132 kWh overload at 100 kW);
  (b) the current evaluation grid, seeds 0-49 x {2022-01-17, 2022-03-05}.
Output: experiments/phase4_review/A/A8_week1_transformer_sweep.csv
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

BASE = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
RATINGS = [250, 150, 100, 75, 50]
TMP = os.path.join(os.environ.get("TEMP", "/tmp"), f"w8_a8_{os.getpid()}")


def config_for(kw):
    os.makedirs(TMP, exist_ok=True)
    text = open(BASE, encoding="utf-8").read()
    text = re.sub(r"(?m)^  max_power: *[\d.]+.*$", f"  max_power: {kw} # A8 Week 1 sweep re-run", text)
    p = os.path.join(TMP, f"station_v0_bogota_tr{kw}.yaml")
    open(p, "w", encoding="utf-8").write(text)
    return p


def run(cfg, seed, day):
    env = make_env(cfg, day, seed, day_config_dir=TMP)
    reset_for_evaluation(env, seed)
    ag = ChargeAsFastAsPossible()
    for _ in range(env.simulation_length):
        _, _, _, _, st = env.step(ag.get_action(env))
    return st, float(env.current_power_usage.max())


def main(grid=True):
    from scripts import review_dc
    review_dc.process_hooks()
    rows = []
    for kw in RATINGS:
        cfg = config_for(kw)
        cells = [("week1_seed42", 42, (2022, 1, 17))] + ([("grid", s, d) for s in SEEDS for d in EVAL_DAYS] if grid else [])
        for kind, s, d in cells:
            st, peak = run(cfg, s, d)
            rows.append({"set": kind, "transformer_kw": kw, "seed": s, "eval_day": "%04d-%02d-%02d" % d,
                         # EV2Gym reports kW summed over 15-min steps; x 0.25 h = kWh
                         "total_transformer_overload_ev2gym_kw_steps": float(st["total_transformer_overload"]),
                         "total_transformer_overload_kwh": float(st["total_transformer_overload"]) * 0.25,
                         "total_energy_charged_kwh": float(st["total_energy_charged"]), "peak_station_kw": peak})
    df = pd.DataFrame(rows)
    df.to_csv("experiments/phase4_review/A/A8_week1_transformer_sweep_by_case.csv", index=False)
    summ = df.groupby(["set", "transformer_kw"]).agg(n=("seed", "size"),
                                                     overload_kwh_mean=("total_transformer_overload_kwh", "mean"),
                                                     overload_ev2gym_kw_steps_mean=("total_transformer_overload_ev2gym_kw_steps", "mean"),
                                                     days_with_overload=("total_transformer_overload_kwh",
                                                                         lambda v: int((v > 0).sum())),
                                                     peak_kw_mean=("peak_station_kw", "mean"),
                                                     peak_kw_max=("peak_station_kw", "max")).reset_index()
    summ.to_csv("experiments/phase4_review/A/A8_week1_transformer_sweep.csv", index=False)
    print(summ.to_string())


if __name__ == "__main__":
    main(grid="--no-grid" not in sys.argv)
