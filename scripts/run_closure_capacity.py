"""
Closure brief, Part C: capacity threshold (C1) and what closes the gap (C2),
on the NON-grid reference config. Justification: Week 7's grid-enabled runs
reproduced every non-grid station metric exactly (0.0 difference, 500 cells
x 5 arms), so the feeder adds nothing to station-side capacity metrics.

C1 (demand sweep): arms AFAP, Round Robin and the final RL model
    (TD3_vanilla extended, training seed 102, 850k) at each demand level,
    50 scenario seeds x 2 EVAL_DAYS, 8 ports, 100 kW transformer.
    config_name: station_v0_bogota_sp<N> (N = round(30 x level)).
C2 (gap closers, AFAP and Round Robin only; the RL policy's observation and
    action dimensions are tied to 8 ports, so it cannot run the port
    variants -- declared): at one demand level, 10 and 12 ports with the
    100 kW limit; 8 ports with transformer limits at the next two standard
    ratings; and every combination.
    config_name: station_v0_bogota_sp<N>_p<P>_tx<kW>.
C2 constant-demand variants (--c2-constant-demand, added after the first C2
    run showed the confound): EV2Gym draws arrivals PER PORT
    (utils.py::EV_spawner, line 490/538), so adding ports also adds
    potential arrivals -- 10 / 12 ports at the same spawn_multiplier face
    25% / 50% more demand. These variants scale spawn_multiplier by 8/P
    (sp22 x 8/10 = 17.6, ...) so the station-level arrival intensity equals
    the 8-port reference and only the port count changes.
    config_name: station_v0_bogota_sp<N>_p<P>_tx<kW>_cd.

Reuses the real row builders (backfill_registry.run_single for the
heuristics, evaluate_rl.eval_td3 via run_week7_grid.run_cell for RL) and the
Week 7 per-process safety hooks. Workers write shards; --merge appends to the
registry once, analysis_row=True, simulate_grid=False, demand level / ports /
rating in the existing notes, n_ports and transformer_kw fields.

Usage:
  PYTHONPATH=. python scripts/run_closure_capacity.py --worker 0 --n-workers 3 --c1-levels 0.5,0.75,2.0,2.5
  PYTHONPATH=. python scripts/run_closure_capacity.py --worker 0 --n-workers 3 --c2-levels 0.75,1.0 --c2-ports 10,12 --c2-kw 100.6,134.2
  PYTHONPATH=. python scripts/run_closure_capacity.py --merge
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

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS
from ev2gym_thesis.registry import REGISTRY_COLUMNS, append_runs, get_git_commit

from scripts import run_week7_grid as w7
from scripts.backfill_registry import run_single as heuristic_run_single
from scripts.run_week5_grid import _with_week5_fields

BASE_CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
CONFIG_DIR = "experiments/phase3_infra_replicability/configs/closure"
SHARD_DIR = "experiments/phase3_infra_replicability/results/closure_shards"
BASE_SPAWN = 30
C1_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", w7.FINAL_RL_NAME]
C2_ARMS = ["ChargeAsFastAsPossible", "RoundRobin"]


# doc:begin closure_configs
def variant_config(level, ports=8, kw=100.0, write=False, cd=False):
    """Non-grid reference config with only spawn_multiplier,
    number_of_charging_stations and transformer.max_power changed.

    Workers call this with write=False: the files are generated ONCE by
    --prepare before any worker starts. (Rewriting them from parallel
    workers raced with readers and crashed a worker -- same failure class
    as Week 7's day-config race.)"""
    sp = int(round(BASE_SPAWN * level))
    name = f"station_v0_bogota_sp{sp}" + ("" if (ports, kw) == (8, 100.0) else f"_p{ports}_tx{kw:g}")
    if cd:
        assert ports != 8, "constant-demand variants only change the port count"
        name += "_cd"
        sp = sp * 8 / ports  # same station-level arrival intensity as 8 ports at this level
    path = f"{CONFIG_DIR}/{name}.yaml"
    if not write:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} missing -- run --prepare before launching workers")
        return name, path
    src = open(BASE_CONFIG, encoding="utf-8").read()
    lines = src.splitlines()
    old_sp = next(l for l in lines if l.startswith("spawn_multiplier:"))
    old_cs = next(l for l in lines if l.startswith("number_of_charging_stations:"))
    new = src.replace(old_sp, f"spawn_multiplier: {sp:.10g} # closure brief demand level {level}x (base 30)"
                      + (f", scaled by 8/{ports} for constant station demand" if cd else ""))
    new = new.replace(old_cs, f"number_of_charging_stations: {ports} # closure brief port variant (base 8)")
    # transformer.max_power is the first 'max_power:' line inside the 'transformer:' block
    i = next(k for k, l in enumerate(lines) if l.startswith("transformer:"))
    j = next(k for k in range(i + 1, len(lines)) if lines[k].strip().startswith("max_power:"))
    new_lines = new.splitlines()
    new_lines[j] = f"  max_power: {kw:g} # closure brief transformer variant, kW (base 100)"
    os.makedirs(CONFIG_DIR, exist_ok=True)
    path = f"{CONFIG_DIR}/{name}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    return name, path
# doc:end closure_configs


def specs(c1_levels, c2_levels, c2_ports, c2_kw, n_seeds=50, cd_levels=(), cd_kw=()):
    out = []
    for lvl in c1_levels:
        for seed in SEEDS[:n_seeds]:
            for day in EVAL_DAYS:
                for arm in C1_ARMS:
                    out.append(("C1", lvl, 8, 100.0, arm, seed, day))
    variants = ([(p, 100.0) for p in c2_ports] + [(8, k) for k in c2_kw]
                + [(p, k) for p in c2_ports for k in c2_kw])
    for c2_level in c2_levels:
        for ports, kw in variants:
            for seed in SEEDS[:n_seeds]:
                for day in EVAL_DAYS:
                    for arm in C2_ARMS:
                        out.append(("C2", c2_level, ports, kw, arm, seed, day))
    for cd_level in cd_levels:
        for ports in c2_ports:
            for kw in cd_kw:
                for seed in SEEDS[:n_seeds]:
                    for day in EVAL_DAYS:
                        for arm in C2_ARMS:
                            out.append(("C2cd", cd_level, ports, kw, arm, seed, day))
    return out


def run_spec(part, level, ports, kw, arm, seed, day, commit):
    cd = part == "C2cd"
    name, path = variant_config(level, ports, kw, cd=cd)
    if arm == "ChargeAsFastAsPossible":
        row = heuristic_run_single(name, path, ports, kw, ChargeAsFastAsPossible, arm, "heuristic", seed, day, commit)
        row = _with_week5_fields(row, seed, day)
    elif arm == "RoundRobin":
        row = heuristic_run_single(name, path, ports, kw, RoundRobin, arm, "heuristic", seed, day, commit)
        row = _with_week5_fields(row, seed, day)
    else:
        assert ports == 8 and kw == 100.0, "the RL policy is tied to 8 ports / the trained 100 kW station"
        row, _ = w7.run_cell(arm, name, path, seed, day, commit, require_voltage=False)
    row["simulate_grid"] = False
    sp = int(round(BASE_SPAWN * level)) * (8 / ports if cd else 1)
    row["notes"] = (row.get("notes") or "") + (f",closure_part={part},demand_level={level},spawn_multiplier="
                                                f"{sp:.10g},ports={ports},transformer_kw={kw:g}"
                                                + (",constant_station_demand=True" if cd else ""))
    return row


def worker(idx, n, all_specs):
    w7.enable_process_hooks()
    commit = get_git_commit()
    os.makedirs(SHARD_DIR, exist_ok=True)
    shard = f"{SHARD_DIR}/rows_w{idx}.csv"
    done = set()
    if os.path.exists(shard):
        d = pd.read_csv(shard, dtype=str, keep_default_na=False)
        done = set(zip(d.config_name, d.algorithm, d.seed, d.eval_day))
    mine = [s for i, s in enumerate(all_specs) if i % n == idx]
    t0 = time.time()
    for k, (part, lvl, ports, kw, arm, seed, day) in enumerate(mine):
        name, _ = variant_config(lvl, ports, kw, cd=(part == "C2cd"))
        key = (name, arm, str(seed), "%04d-%02d-%02d" % day)
        if key in done:
            continue
        row = run_spec(part, lvl, ports, kw, arm, seed, day, commit)
        new = not os.path.exists(shard)
        with open(shard, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REGISTRY_COLUMNS)
            if new:
                w.writeheader()
            w.writerow({c: row.get(c) for c in REGISTRY_COLUMNS})
        done.add(key)
        with open(f"{SHARD_DIR}/progress_w{idx}.json", "w") as f:
            json.dump({"worker": idx, "done": k + 1, "of": len(mine), "elapsed_s": round(time.time() - t0, 1),
                       "utc": datetime.datetime.utcnow().isoformat()}, f)
    print(f"worker {idx}: finished {len(mine)} cells in {time.time() - t0:.0f}s", flush=True)


def merge():
    from scripts.evaluate_mpc import analysis_row_existing_keys
    existing = analysis_row_existing_keys()
    rows = []
    for p in sorted(glob.glob(f"{SHARD_DIR}/rows_w*.csv")):
        rows += pd.read_csv(p, dtype=str, keep_default_na=False).to_dict("records")
    todo = []
    for r in rows:
        key = (r["config_name"], r["algorithm"], str(r["seed"]), r["eval_day"])
        if key not in existing:
            for c in ("analysis_row", "superseded", "simulate_grid"):
                r[c] = r[c] == "True"
            todo.append(r)
            existing.add(key)
    res = append_runs(todo, force=True) if todo else {"appended": 0}
    print(f"merge: {len(rows)} shard rows, appended {res['appended']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int)
    ap.add_argument("--n-workers", type=int, default=1)
    ap.add_argument("--c1-levels", default="")
    ap.add_argument("--c2-levels", default="")
    ap.add_argument("--c2-ports", default="10,12")
    ap.add_argument("--c2-kw", default="")
    ap.add_argument("--c2-constant-demand-levels", default="")
    ap.add_argument("--c2-constant-demand-kw", default="100,134.2")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--prepare", action="store_true", help="write every variant config once, before the workers")
    a = ap.parse_args()
    if a.merge:
        merge()
    elif a.prepare:
        lv = [float(x) for x in a.c1_levels.split(",") if x]
        c2 = [float(x) for x in a.c2_levels.split(",") if x]
        ports = [int(x) for x in a.c2_ports.split(",") if x]
        kws = [float(x) for x in a.c2_kw.split(",") if x]
        cdl = [float(x) for x in a.c2_constant_demand_levels.split(",") if x]
        cdk = [float(x) for x in a.c2_constant_demand_kw.split(",") if x]
        seen = set()
        for part, lvl, p, k, *_ in specs(lv, c2, ports, kws, n_seeds=1, cd_levels=cdl, cd_kw=cdk):
            if (part, lvl, p, k) not in seen:
                seen.add((part, lvl, p, k))
                print(*variant_config(lvl, p, k, write=True, cd=(part == "C2cd")))
    else:
        lv = [float(x) for x in a.c1_levels.split(",") if x]
        ports = [int(x) for x in a.c2_ports.split(",") if x]
        kws = [float(x) for x in a.c2_kw.split(",") if x]
        c2 = [float(x) for x in a.c2_levels.split(",") if x]
        cdl = [float(x) for x in a.c2_constant_demand_levels.split(",") if x]
        cdk = [float(x) for x in a.c2_constant_demand_kw.split(",") if x]
        worker(a.worker, a.n_workers, specs(lv, c2, ports, kws, cd_levels=cdl, cd_kw=cdk))
