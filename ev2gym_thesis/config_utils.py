"""
Helper to run a base config on a different calendar day without editing the
base YAML file. EV2Gym's config_file argument only accepts a path, and the
simulated day is read once from config['year'/'month'/'day'] inside
EV2Gym.__init__ (see ev2gym/models/ev2gym_env.py), so varying the day across
EVAL_DAYS/TRAIN_DAYS requires writing a day-specific copy of the YAML.

The written file IS the actual config used for that run, so reproducibility
is preserved: the base config_name plus (year, month, day) fully determine
its contents.
"""
import os

import yaml


def make_day_config(base_config_path: str, year: int, month: int, day: int, out_dir: str) -> str:
    with open(base_config_path) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)

    cfg["random_day"] = False
    cfg["year"] = year
    cfg["month"] = month
    cfg["day"] = day

    os.makedirs(out_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(base_config_path))[0]
    out_path = f"{out_dir}/{base_name}__{year}{month:02d}{day:02d}.yaml"
    with open(out_path, "w") as f:
        yaml.dump(cfg, f)
    return out_path
