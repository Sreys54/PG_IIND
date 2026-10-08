"""
Final capacity brief, Parts B-C: capacity threshold and growth scenario under
DC session durations (ev2gym_thesis/demand/dc_sessions.py), on the NON-grid
reference config (the closure run measured a 0.0 grid / non-grid difference
on every station metric).

Configs. Each run's config is the non-grid reference YAML with only
spawn_multiplier, number_of_charging_stations and transformer.max_power
changed (as in the closure run), plus a sidecar <name>.dwell.json holding the
session-duration model {mean_min, cv}. EV2Gym consumes no session-duration
key, so the sidecar, not a new YAML key, carries it (CLAUDE.md config rule);
the runner enables the transform from the sidecar, so a run is reproducible
from its config pair alone.
    config_name: station_v0_bogota_dc<M>_sp<N>[_p<P>_tx<kW>][_cd]

Parts:
  C1   arms AFAP, Round Robin and the final RL model (TD3_vanilla extended,
       seed 102, 850k; trained on Dutch durations, so OUT OF ITS TRAINING
       DISTRIBUTION here -- labelled in notes), 8 ports, 100 kW, a demand
       sweep at the central 42-minute variant.
  C1rr Round Robin only, the same sweep at 32 and 78 minutes (threshold
       sensitivity).
  C2   Round Robin (plus AFAP, a labelled addition, when the plan lists it), growth levels 1.3x and 1.6x, ports 8..16 x
       transformer ratings, at constant station demand (spawn_multiplier x
       8/P: EV2Gym draws arrivals per port, closure finding). The RL policy
       is tied to 8 ports and is excluded, as in the closure run.
  Diagnostic (plan dwell_diag.json): RoundRobin_TransformerCapped
       (ev2gym_thesis/heuristics.py), EV2Gym's Round Robin allocation with the
       transformer rating as its power budget instead of the setpoint, on the
       C1, C1rr and C2 grids. Added after C1 showed the setpoint coupling.
  censoring  the policy-independent rejected-arrival replay, once per
       (config, seed, day), to results shards (never the registry).

Workers write shards; --merge writes results/dwell_registry.csv, a SEPARATE
file with the master registry's exact schema (REGISTRY_COLUMNS) and the same
row builders, analysis_row=True, simulate_grid=False, "dwell_part=" in notes.
results/master_results.csv is never opened for writing by this brief
(labelled choice: the DC session model is a different population model, and
a separate file removes any risk to existing registry rows and to the
existing registry pins). Timeseries go to results/timeseries/<run_id>.npz as
usual (new files only; run_ids contain the dc<M> config name).

Usage:
  PYTHONPATH=. python scripts/run_dwell_capacity.py --prepare --plan <plan.json>
  PYTHONPATH=. python scripts/run_dwell_capacity.py --worker 0 --n-workers 2 --plan <plan.json>
  PYTHONPATH=. python scripts/run_dwell_capacity.py --merge
"""
import argparse
import csv
import datetime
import glob
import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.demand import dc_sessions
from ev2gym_thesis.heuristics import RoundRobinTransformerCapped
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.registry import REGISTRY_COLUMNS, get_git_commit

from scripts import run_week7_grid as w7
from scripts.backfill_registry import run_single as heuristic_run_single
from scripts.run_week5_grid import _with_week5_fields

BASE_CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
CONFIG_DIR = "experiments/phase3_infra_replicability/configs/dwell"
SHARD_DIR = "experiments/phase3_infra_replicability/results/dwell_shards"
BASE_SPAWN = 30
CV = 0.5
C1_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", w7.FINAL_RL_NAME]
BOUND_ARMS = ("MPC_TrackingG2V", "Optimal_Oracle_Tracking")  # last run, Part 2: non-causal upper bounds
RR_CAPPED = "RoundRobin_TransformerCapped"  # diagnostic arm (ev2gym_thesis/heuristics.py), plan dwell_diag.json


# doc:begin dwell_configs
def variant_config(level, mean_min, ports=8, kw=100.0, cd=False, write=False):
    """(name, yaml path) of a DC-session variant; write=True creates the YAML
    and its .dwell.json sidecar (done once by --prepare, never by workers)."""
    sp = int(round(BASE_SPAWN * level))
    name = f"station_v0_bogota_dc{mean_min:g}_sp{sp}" + ("" if (ports, kw) == (8, 100.0) else f"_p{ports}_tx{kw:g}")
    if cd:
        assert ports != 8, "constant-demand variants only change the port count"
        name += "_cd"
        sp = sp * 8 / ports
    path = f"{CONFIG_DIR}/{name}.yaml"
    if not write:
        if not (os.path.exists(path) and os.path.exists(dc_sessions.sidecar_path(path))):
            raise FileNotFoundError(f"{path} or its sidecar missing -- run --prepare first")
        return name, path
    src = open(BASE_CONFIG, encoding="utf-8").read()
    lines = src.splitlines()
    old_sp = next(l for l in lines if l.startswith("spawn_multiplier:"))
    old_cs = next(l for l in lines if l.startswith("number_of_charging_stations:"))
    new = src.replace(old_sp, f"spawn_multiplier: {sp:.10g} # dwell brief demand level {level}x (base 30)"
                      + (f", scaled by 8/{ports} for constant station demand" if cd else ""))
    new = new.replace(old_cs, f"number_of_charging_stations: {ports} # dwell brief port variant (base 8)")
    i = next(k for k, l in enumerate(lines) if l.startswith("transformer:"))
    j = next(k for k in range(i + 1, len(lines)) if lines[k].strip().startswith("max_power:"))
    new_lines = new.splitlines()
    new_lines[j] = f"  max_power: {kw:g} # dwell brief transformer variant, kW (base 100)"
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    with open(dc_sessions.sidecar_path(path), "w", encoding="utf-8") as f:
        json.dump({"session_model": "lognormal connection duration, ev2gym_thesis/demand/dc_sessions.py",
                   "mean_min": float(mean_min), "cv": CV,
                   "rounding": "nearest timestep, floor 1 step",
                   "label": "external reference, not Colombian (U.S. DOE 2023 / Hardman 2026)"}, f, indent=2)
    return name, path
# doc:end dwell_configs


def specs(plan, n_seeds=50):
    """plan: {"C1": {"mean": 42, "levels": [...]}, "C1rr": {"means": [32, 78], "levels": [...]},
              "C2": {"mean": 42, "levels": [1.3, 1.6], "ports": [...], "kw": [...]}}"""
    out = []
    seeds, days = SEEDS[:n_seeds], EVAL_DAYS
    if "C1" in plan:
        for lvl in plan["C1"]["levels"]:
            for arm in plan["C1"].get("arms", C1_ARMS):
                out += [("C1", plan["C1"]["mean"], lvl, 8, 100.0, False, arm, s, d) for s in seeds for d in days]
    if "C1rr" in plan:
        for m in plan["C1rr"]["means"]:
            for lvl in plan["C1rr"]["levels"]:
                for arm in plan["C1rr"].get("arms", ["RoundRobin"]):
                    out += [("C1rr", m, lvl, 8, 100.0, False, arm, s, d) for s in seeds for d in days]
    if "C2" in plan:
        c2 = plan["C2"]
        for lvl in c2["levels"]:
            for p in c2["ports"]:
                for kw in c2["kw"]:
                    if (p, kw) == (8, 100.0):
                        continue  # the C1 rows at this level are the reference
                    for arm in c2.get("arms", ["RoundRobin"]):
                        out += [("C2", c2["mean"], lvl, p, kw, p != 8, arm, s, d) for s in seeds for d in days]
    return out


def run_spec(part, mean_min, level, ports, kw, cd, arm, seed, day, commit):
    name, path = variant_config(level, mean_min, ports, kw, cd)
    dc_sessions.enable(dc_sessions.model_for_config(path))
    try:
        if arm == "ChargeAsFastAsPossible":
            row = _with_week5_fields(heuristic_run_single(name, path, ports, kw, ChargeAsFastAsPossible, arm,
                                                          "heuristic", seed, day, commit), seed, day)
        elif arm == RR_CAPPED:
            row = _with_week5_fields(heuristic_run_single(name, path, ports, kw, RoundRobinTransformerCapped, arm,
                                                          "heuristic", seed, day, commit), seed, day)
            row["notes"] += ",diagnostic_arm=round_robin_budget_is_transformer_rating"
        elif arm == "RoundRobin":
            row = _with_week5_fields(heuristic_run_single(name, path, ports, kw, RoundRobin, arm, "heuristic",
                                                          seed, day, commit), seed, day)
        elif arm in BOUND_ARMS:
            assert ports == 8 and kw == 100.0, "bounds are run on the reference station only"
            row, _ = w7.run_cell(arm, name, path, seed, day, commit, require_voltage=False)
            row["notes"] += ",upper_bound_noncausal=knows_departure_times,tracks_ev2gym_power_setpoint=True"
        else:
            assert ports == 8 and kw == 100.0, "the RL policy is tied to 8 ports / the trained 100 kW station"
            row, _ = w7.run_cell(arm, name, path, seed, day, commit, require_voltage=False)
            row["notes"] += ",out_of_training_distribution=dc_session_durations"
    finally:
        dc_sessions.disable()
    row["simulate_grid"] = False
    sp = int(round(BASE_SPAWN * level)) * (8 / ports if cd else 1)
    row["notes"] = (row.get("notes") or "") + (
        f",dwell_part={part},session_model=dc_lognormal,dwell_mean_min={mean_min:g},dwell_cv={CV},"
        f"demand_level={level},spawn_multiplier={sp:.10g},ports={ports},transformer_kw={kw:g}"
        + (",constant_station_demand=True" if cd else ""))
    return row


# doc:begin dwell_censoring_cell
def censoring_cell(mean_min, level, ports, kw, cd, seed, day):
    """Policy-independent rejected-arrival replay for one cell (the config's
    population under its sidecar's DC model)."""
    name, path = variant_config(level, mean_min, ports, kw, cd)
    recs, cens, facts = dc_sessions.cell_sessions(path, day, seed, f"{CONFIG_DIR}/_tmp_censor_pid{os.getpid()}",
                                                  dc_sessions.model_for_config(path))
    T = facts["simulation_length"]
    return {"config_name": name, "dwell_mean_min": mean_min, "level": level, "ports": ports, "transformer_kw": kw,
            "constant_demand": cd, "seed": seed, "eval_day": "%04d-%02d-%02d" % day, **cens,
            "requested_kwh_spawned": sum(r["energy_requested_kwh"] for r in recs),
            "mean_duration_min": (sum(r["duration_min"] for r in recs) / len(recs)) if recs else 0.0,
            "mean_port_occupancy": sum(min(r["departure_step"], T) - r["arrival_step"] for r in recs) / (ports * T)}
# doc:end dwell_censoring_cell


def _append(path, rec, fields):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow({c: rec.get(c) for c in fields})


def worker(idx, n, all_specs, do_censoring=True):
    w7.enable_process_hooks()
    commit = get_git_commit()
    os.makedirs(SHARD_DIR, exist_ok=True)
    shard, cshard = f"{SHARD_DIR}/rows_w{idx}.csv", f"{SHARD_DIR}/censoring_w{idx}.csv"
    done, cdone = set(), set()
    if os.path.exists(shard):
        d = pd.read_csv(shard, dtype=str, keep_default_na=False)
        done = set(zip(d.config_name, d.algorithm, d.seed, d.eval_day))
    if os.path.exists(cshard):
        d = pd.read_csv(cshard, dtype=str, keep_default_na=False)
        cdone = set(zip(d.config_name, d.seed, d.eval_day))
    mine = [s for i, s in enumerate(all_specs) if i % n == idx]
    t0 = time.time()
    cfields = None
    for k, (part, m, lvl, ports, kw, cd, arm, seed, day) in enumerate(mine):
        name, _ = variant_config(lvl, m, ports, kw, cd)
        ds = "%04d-%02d-%02d" % day
        if do_censoring and (name, str(seed), ds) not in cdone:
            rec = censoring_cell(m, lvl, ports, kw, cd, seed, day)
            cfields = cfields or list(rec.keys())
            _append(cshard, rec, cfields)
            cdone.add((name, str(seed), ds))
        if (name, arm, str(seed), ds) in done:
            continue
        row = run_spec(part, m, lvl, ports, kw, cd, arm, seed, day, commit)
        _append(shard, row, REGISTRY_COLUMNS)
        done.add((name, arm, str(seed), ds))
        with open(f"{SHARD_DIR}/progress_w{idx}.json", "w") as f:
            json.dump({"worker": idx, "done": k + 1, "of": len(mine), "elapsed_s": round(time.time() - t0, 1),
                       "utc": datetime.datetime.utcnow().isoformat()}, f)
    print(f"worker {idx}: finished {len(mine)} cells in {time.time() - t0:.0f}s", flush=True)


DWELL_REGISTRY = "results/dwell_registry.csv"


def merge():
    """Shards -> results/dwell_registry.csv (deduplicated on (config,
    algorithm, seed, eval_day)); rewritten whole from the shards each time,
    so a rerun is idempotent. Censoring shards -> results/dwell_censoring_by_cell.csv."""
    rows = []
    for p in sorted(glob.glob(f"{SHARD_DIR}/rows_w*.csv")):
        rows.append(pd.read_csv(p, dtype=str, keep_default_na=False))
    reg = pd.concat(rows, ignore_index=True)
    reg = reg.drop_duplicates(subset=["config_name", "algorithm", "seed", "eval_day"], keep="first")
    reg = reg[REGISTRY_COLUMNS]
    reg.to_csv(DWELL_REGISTRY, index=False)
    cens = pd.concat([pd.read_csv(p, dtype=str, keep_default_na=False)
                      for p in sorted(glob.glob(f"{SHARD_DIR}/censoring_w*.csv"))], ignore_index=True)
    cens = cens.drop_duplicates(subset=["config_name", "seed", "eval_day"], keep="first")
    cens.to_csv("results/dwell_censoring_by_cell.csv", index=False)
    print(f"merge: {len(reg)} runs -> {DWELL_REGISTRY}; {len(cens)} censoring cells")


def load_plan(path):
    return json.load(open(path, encoding="utf-8"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int)
    ap.add_argument("--n-workers", type=int, default=1)
    ap.add_argument("--plan")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--prepare", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge()
    elif a.prepare:
        seen = set()
        for part, m, lvl, p, k, cd, *_ in specs(load_plan(a.plan), n_seeds=1):
            if (m, lvl, p, k, cd) not in seen:
                seen.add((m, lvl, p, k, cd))
                print(*variant_config(lvl, m, p, k, cd, write=True))
    else:
        worker(a.worker, a.n_workers, specs(load_plan(a.plan)))
