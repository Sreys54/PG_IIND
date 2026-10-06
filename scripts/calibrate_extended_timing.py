"""
Week 6, Part 0, Gate 1: wall-clock calibration for the extended TD3 run.

Launches N concurrent scripts/train_td3_extended.py processes (one per
training seed) for a fixed number of steps with ONE full 20-cell validation
evaluation at the end, into a throwaway output root, and records per-seed
training throughput (validation time excluded) and validation overhead.

Usage:
    PYTHONPATH=. python scripts/calibrate_extended_timing.py --label par3_nocache --seeds 100 101 102
    PYTHONPATH=. python scripts/calibrate_extended_timing.py --label par3_cache_t2 --seeds 100 101 102 --price-cache --torch-threads 2
"""
import argparse
import csv
import datetime
import os
import shutil
import subprocess
import sys
import time

import pandas as pd
import psutil

OUT_CSV = "experiments/phase2_algorithms/results/week6_part0/timing_calibration.csv"
TMP_ROOT = "C:/Users/Santi/AppData/Local/Temp/ev6t"  # short path: Windows MAX_PATH (260) is exceeded under the session scratchpad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--steps", type=int, default=5000)
    p.add_argument("--price-cache", action="store_true")
    p.add_argument("--torch-threads", type=int, default=None)
    a = p.parse_args()

    root = os.path.join(TMP_ROOT, a.label)
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    procs = []
    t0 = time.time()
    for s in a.seeds:
        cmd = [sys.executable, "scripts/train_td3_extended.py", "--seed", str(s),
               "--deadline", "2099-01-01T00:00:00-05:00", "--max-steps", str(a.steps),
               "--eval-freq", str(a.steps), "--buffer-freq", str(a.steps), "--output-root", root]
        if a.price_cache:
            cmd.append("--price-cache")
        if a.torch_threads:
            cmd += ["--torch-threads", str(a.torch_threads)]
        log = open(os.path.join(root, f"ts{s}.log"), "w")
        procs.append((s, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                          env={**os.environ, "PYTHONPATH": "."}), log))
    peak_rss = {s: 0 for s in a.seeds}
    while any(pr.poll() is None for _, pr, _ in procs):
        for s, pr, _ in procs:
            try:
                peak_rss[s] = max(peak_rss[s], psutil.Process(pr.pid).memory_info().rss)
            except psutil.NoSuchProcess:
                pass
        time.sleep(2)
    total = time.time() - t0

    rows = []
    for s, pr, log in procs:
        log.close()
        name = f"TD3_vanilla_extended_ts{s}"
        val = pd.read_csv(os.path.join(root, "logs", f"{name}_validation.csv"))
        last = val[val.timesteps == a.steps].iloc[0]
        train_s = last.wall_clock_s - last.validation_wall_clock_s
        buf = os.path.join(root, "models", name, "replay_buffers", f"replay_buffer_{a.steps}_steps.pkl")
        ckpt = os.path.join(root, "models", name, "checkpoints", f"td3_vanilla_extended_ts{s}_{a.steps}_steps.zip")
        rows.append({
            "label": a.label, "utc": datetime.datetime.utcnow().isoformat(), "n_concurrent": len(a.seeds),
            "seed": s, "price_cache": a.price_cache, "torch_threads": a.torch_threads or "default",
            "exit_code": pr.returncode, "steps": a.steps, "train_wall_s": round(train_s, 1),
            "train_steps_per_s": round(a.steps / train_s, 2),
            "validation_wall_s": round(last.validation_wall_clock_s, 1),
            "process_total_wall_s": round(total, 1), "peak_rss_mb": round(peak_rss[s] / 2**20),
            "replay_buffer_mb_at_steps": round(os.path.getsize(buf) / 2**20, 2),
            "checkpoint_kb": round(os.path.getsize(ckpt) / 2**10),
            "criterion_at_steps": round(last.criterion_value, 2),
        })
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    new = not os.path.exists(OUT_CSV)
    with open(OUT_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        if new:
            w.writeheader()
        w.writerows(rows)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
