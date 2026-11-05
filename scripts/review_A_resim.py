"""
Week 8 advisor review, Block A: instrumented re-simulation of the stored
grids, because the registries and the stored time series hold no per-EV
delivered energy, setpoint, charge potential or reward terms (Gate 0
inventory). Same seeds, configs and runner functions as the original rows;
every re-simulated case must reproduce its registry row (asserted on energy,
overload, tracking error, EV2Gym satisfaction and EVs served).

Grids:
  long  station_v0_bogota (EV2Gym's native sessions), the 22 registry arms of
        the long-dwell statistics set + RR-TA (instrumented only, not in the
        master registry: A4 needs its post-hoc reward);
  dc    the Final-capacity-brief DC configs (EV2Gym spawner + 42-min
        transform), 8 ports / 100 kW, levels 1.0x/1.3x/1.6x, arms AFAP, RR,
        RR-TA, the final RL model, MPC-T, Oracle-T (results/dwell_registry.csv).
The runners' save_timeseries is disabled: nothing in results/timeseries/ or
in any registry is written. Outputs (experiments/phase4_review/A/):
  cases_w*.csv   one row per case: per-EV aggregates (sum of f, of EV2Gym's
                 s, of requested and delivered energy; drivers with f >= 0.9),
                 the three post-hoc terms of SqTrError_TrPenalty_UserIncentives,
                 overload steps, peak;
  evs_w*.csv     one row per served EV.

Usage:
  PYTHONPATH=. python scripts/review_A_resim.py --worker 0 --workers 2
  PYTHONPATH=. python scripts/review_A_resim.py --merge
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin
from ev2gym.rl_agent.reward import SquaredTrackingErrorReward

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.heuristics import RoundRobinTransformerCapped
from ev2gym_thesis.metrics import service
from ev2gym_thesis.registry import get_git_commit

OUT = "experiments/phase4_review/A"
LONG_NAME, LONG_PATH = "station_v0_bogota", "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
MODELS_DIR = "experiments/phase2_algorithms/models"
DC_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "RoundRobin_TransformerCapped", "TD3_vanilla_extended_ts102",
           "MPC_TrackingG2V", "Optimal_Oracle_Tracking"]
CHECK = ["total_energy_charged", "total_transformer_overload", "tracking_error", "average_user_satisfaction",
         "total_ev_served"]


def _noop(*a, **k):
    return None


def _silence_timeseries():
    from scripts import backfill_registry, evaluate_mpc, evaluate_oracle, evaluate_rl
    for m in (backfill_registry, evaluate_mpc, evaluate_oracle, evaluate_rl):
        if hasattr(m, "save_timeseries"):
            m.save_timeseries = _noop


def td3_arms():
    from scripts.evaluate_rl import DEFAULT_REWARD_FN
    from scripts.evaluate_week6_part0 import extended_arms
    arms = {f"TD3_vanilla_ts{s}": (s, f"{MODELS_DIR}/TD3_vanilla_ts{s}/final_model.zip", DEFAULT_REWARD_FN)
            for s in (100, 101, 102)}
    arms.update({f"TD3_TrackingOnly_ts{s}": (s, f"{MODELS_DIR}/TD3_TrackingOnly_ts{s}/final_model.zip",
                                             SquaredTrackingErrorReward) for s in (100, 101, 102)})
    for name, s, path, _ in extended_arms():
        arms[name] = (s, path, DEFAULT_REWARD_FN)
    return arms


LONG_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "RoundRobin_TransformerCapped", "RandomPolicy",
             "MPC_TrackingG2V", "MPC_EnergyMaxG2V", "Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced"] + \
    [f"TD3_vanilla_ts{s}" for s in (100, 101, 102)] + [f"TD3_TrackingOnly_ts{s}" for s in (100, 101, 102)] + \
    [f"TD3_vanilla_{k}_ts{s}" for k in ("extended", "extended_last", "new60k") for s in (100, 101, 102)]


def run_long(arm, seed, day, commit, td3):
    from scripts import evaluate_mpc, evaluate_oracle, evaluate_rl
    from scripts.backfill_registry import run_single
    heur = {"ChargeAsFastAsPossible": ChargeAsFastAsPossible, "RoundRobin": RoundRobin,
            "RoundRobin_TransformerCapped": RoundRobinTransformerCapped}
    if arm in heur:
        return run_single(LONG_NAME, LONG_PATH, 8, 100, heur[arm], arm, "heuristic", seed, day, commit)
    if arm == "RandomPolicy":
        return evaluate_rl.eval_random_policy(seed, day, commit)
    if arm.startswith("MPC_"):
        return evaluate_mpc.run_single("tracking" if arm == "MPC_TrackingG2V" else "energy_max", seed, day, commit)
    if arm.startswith("Optimal_Oracle_"):
        return evaluate_oracle.run_single(seed, day, commit, arm.split("_")[-1].lower())
    s, path, rfn = td3[arm]
    return evaluate_rl.eval_td3(arm, s, path, rfn, seed, day, commit)


def specs():
    out = [("long", 1.0, arm, s, d) for arm in LONG_ARMS for s in SEEDS for d in EVAL_DAYS]
    out += [("dc", lv, arm, s, d) for lv in (1.0, 1.3, 1.6) for arm in DC_ARMS for s in SEEDS for d in EVAL_DAYS]
    return out


def case_record(rec):
    evs = rec["evs"] + rec["connected_at_end"]
    st = rec["steps"]
    h = rec["timescale"] / 60
    over = np.array([x["overload_kw"] for x in st])
    power = np.array([x["power_kw"] for x in st])
    tot = service.episode_totals(rec)
    return {"n_served_rec": len(evs), "sum_f": sum(e["f"] for e in evs),
            "n_f_ge_09": sum(e["f"] >= 0.9 - 1e-12 for e in evs), "sum_s_ev2gym": sum(e["s_ev2gym"] for e in evs),
            "sum_requested_kwh": sum(e["requested_kwh"] for e in evs),
            "sum_delivered_kwh": sum(e["delivered_kwh"] for e in evs),
            "sum_battery_kwh": sum(e["battery_kwh"] for e in evs),
            "r_tracking": tot["r_tracking"], "r_overload": tot["r_overload"], "r_user": tot["r_user"],
            "sq_dev_min_target": -tot["r_tracking"],
            "overload_kwh_rec": float(over.sum() * h), "overload_steps": int((over > 1e-9).sum()),
            "peak_station_kw": float(power.max()), "energy_kwh_rec": float(power.sum() * h)}


def registry_index(regime):
    if regime == "long":
        m = pd.read_csv("results/master_results.csv", low_memory=False)
        m = m[(m.analysis_row == True) & (m.config_name == LONG_NAME)]
    else:
        m = pd.read_csv("results/dwell_registry.csv", low_memory=False)
    return m.drop_duplicates(["config_name", "algorithm", "seed", "eval_day"]).set_index(
        ["config_name", "algorithm", "seed", "eval_day"])


def worker(idx, n):
    from scripts import review_dc
    from scripts.run_dwell_capacity import run_spec
    review_dc.process_hooks()
    _silence_timeseries()
    service.enable_recording()
    commit = get_git_commit()
    td3 = td3_arms()
    reg = {r: registry_index(r) for r in ("long", "dc")}
    os.makedirs(OUT, exist_ok=True)
    cpath, epath = os.path.join(OUT, f"cases_w{idx}.csv"), os.path.join(OUT, f"evs_w{idx}.csv")
    done = set(pd.read_csv(cpath).run_key) if os.path.exists(cpath) else set()
    all_specs = specs()
    for i, (regime, lv, arm, s, d) in enumerate(all_specs):
        if i % n != idx:
            continue
        ds = "%04d-%02d-%02d" % d
        key = f"{regime}|{lv}|{arm}|{s}|{ds}"
        if key in done:
            continue
        row = run_long(arm, s, d, commit, td3) if regime == "long" else \
            run_spec("week8_A_resim", 42, lv, 8, 100.0, False, arm, s, d, commit)
        rec = service.LAST.pop("episode")
        ref_key = (row["config_name"], arm, s, ds)
        ref = reg[regime].loc[ref_key] if ref_key in reg[regime].index else None
        out = {"run_key": key, "regime": regime, "level": lv, "algorithm": arm, "seed": s, "eval_day": ds,
               "config_name": row["config_name"], "in_registry": ref is not None}
        out.update({c: row[c] for c in CHECK})
        if ref is not None:
            for c in CHECK:
                a, b = float(row[c]), float(ref[c])
                assert abs(a - b) <= 1e-6 * max(1.0, abs(b)), f"{key}: {c} re-simulated {a} != registry {b}"
        cr = case_record(rec)
        assert abs(cr["energy_kwh_rec"] - float(row["total_energy_charged"])) < 1e-6 * max(1, cr["energy_kwh_rec"])
        out.update(cr)
        review_dc.append_csv(cpath, out)
        for e in rec["evs"] + rec["connected_at_end"]:
            review_dc.append_csv(epath, {"run_key": key, **e})
        if i % 50 == idx:
            print(i, len(all_specs), key, flush=True)


def merge():
    for kind in ("cases", "evs"):
        df = pd.concat([pd.read_csv(p) for p in sorted(glob.glob(os.path.join(OUT, f"{kind}_w*.csv")))])
        if kind == "cases":
            df = df.drop_duplicates("run_key")
        df.to_csv(os.path.join(OUT, f"A_{kind}.csv"), index=False)
        print(kind, len(df))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    merge() if a.merge else worker(a.worker, a.workers)
