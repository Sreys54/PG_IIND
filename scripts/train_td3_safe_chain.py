"""
Week 8 advisor review, C3: train the TD3_safe seeds one after another in a
single process slot (laptop limit: at most 2 heavy processes, the other
slot runs the evaluations), sharing one final deadline.

Each seed is launched with its own --deadline = now + (final deadline - now)
/ (seeds still to train), computed at its launch, so a seed that converges
early (convergence + 100,000 steps) leaves its unused time to the next ones.
A seed whose run already finished (state.json with finished_utc) is skipped;
one that stopped part-way is resumed with --resume.

Usage (the user approves the launch at Gate 2; CLAUDE.md rule 2):
  PYTHONPATH=. python scripts/train_td3_safe_chain.py --final-deadline 2026-11-04T14:00:00-05:00 \
      --seeds 100 101 102 --state service_causal --output-root C:/ev2gym_runs/w8_td3_safe
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--final-deadline", required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102])
    p.add_argument("--state", default=None)
    p.add_argument("--output-root", required=True)
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--eval-freq", type=int, default=None)
    a = p.parse_args()
    final = datetime.datetime.fromisoformat(a.final_deadline)
    assert final.tzinfo is not None
    for i, seed in enumerate(a.seeds):
        state_path = os.path.join(a.output_root, "models", f"TD3_safe_dc42_ts{seed}", "state.json")
        resume = False
        if os.path.exists(state_path):
            st = json.load(open(state_path))
            if st.get("finished_utc"):
                print(f"seed {seed}: finished ({st.get('stop_reason')}), skipped", flush=True)
                continue
            resume = True
        now = datetime.datetime.now(final.tzinfo)
        left = len(a.seeds) - i
        deadline = now + (final - now) / left
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "train_td3_safe.py"), "--seed", str(seed),
               "--deadline", deadline.isoformat(timespec="seconds"), "--price-cache", "--torch-threads", "1",
               "--output-root", a.output_root]
        if a.state:
            cmd += ["--state", a.state]
        if a.max_steps:
            cmd += ["--max-steps", str(a.max_steps)]
        if a.eval_freq:
            cmd += ["--eval-freq", str(a.eval_freq)]
        if resume:
            cmd.append("--resume")
        print(f"seed {seed}: launch, deadline {deadline.isoformat(timespec='seconds')}, resume={resume}", flush=True)
        r = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONPATH": ROOT})
        print(f"seed {seed}: exit code {r.returncode}", flush=True)
        if r.returncode != 0:
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
