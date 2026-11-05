"""
Week 8 advisor review, C3 after training: apply the selection and carried-
model rules fixed in ev2gym_thesis/rl/config_safe.py (doc safe_selection_rule)
to the TD3_safe runs, copy each seed's final checkpoint (+ its
_vecnormalize.pkl) from the run root outside OneDrive into
experiments/phase2_algorithms/models/TD3_safe_dc42_ts<seed>/, and write
results/review_td3_safe_selection.json.

Reads each seed's own state.json and validation CSV: no step number is typed
by hand. Usage:
  PYTHONPATH=. python scripts/select_td3_safe.py --root C:/ev2gym_runs/w8_td3_safe
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from ev2gym_thesis.rl import config_safe as cfg

DEST = "experiments/phase2_algorithms/models"
OUT = "results/review_td3_safe_selection.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102])
    a = ap.parse_args()
    out = {"selection_rule": cfg.SELECTION_RULE_VERSION, "carried_model_rule": cfg.CARRIED_MODEL_RULE, "seeds": {}}
    for s in a.seeds:
        name = f"TD3_safe_dc42_ts{s}"
        st_path = os.path.join(a.root, "models", name, "state.json")
        if not os.path.exists(st_path):
            out["seeds"][s] = {"status": "not trained"}
            continue
        st = json.load(open(st_path))
        val = pd.read_csv(os.path.join(a.root, "logs", f"{name}_validation.csv"))
        m = val.criterion_value.values
        fi = cfg.final_index(m, st.get("conv_eval_index"), lower_is_better=False)
        ckpt = val.checkpoint_path.iloc[fi]
        dst_dir = os.path.join(DEST, name)
        os.makedirs(dst_dir, exist_ok=True)
        for src in (ckpt, ckpt.replace(".zip", "_vecnormalize.pkl")):
            shutil.copy2(src, os.path.join(dst_dir, os.path.basename(src)))
        manifests = sorted(f for f in os.listdir(os.path.join(a.root, "models", name)) if f.startswith("manifest"))
        for f in manifests:
            shutil.copy2(os.path.join(a.root, "models", name, f), os.path.join(dst_dir, f))
        shutil.copy2(os.path.join(a.root, "logs", f"{name}_validation.csv"), os.path.join(dst_dir, "validation.csv"))
        out["seeds"][s] = {"converged": st.get("conv_eval_index") is not None,
                           "convergence_step": int(val.timesteps.iloc[st["conv_eval_index"]]) if st.get("conv_eval_index") is not None else None,
                           "final_step": int(val.timesteps.iloc[fi]), "last_step": int(val.timesteps.iloc[-1]),
                           "stop_reason": st.get("stop_reason"), "validation_energy_kwh": float(m[fi]),
                           "checkpoint": os.path.join(dst_dir, os.path.basename(ckpt)).replace("\\", "/")}
    trained = {s: v for s, v in out["seeds"].items() if "final_step" in v}
    if trained:
        best = max(trained, key=lambda s: trained[s]["validation_energy_kwh"])
        out["carried_model"] = {"train_seed": best, **trained[best]}
    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
