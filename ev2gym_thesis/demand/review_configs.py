"""
Week 8 advisor review: DC-regime configs for the station-level arrival
generator (station_arrivals.py), and the calibration of arrivals/day to the
target offered energy (Block B, item 4).

Every config is a copy of the Final-capacity-brief DC config
(experiments/phase3_infra_replicability/configs/dwell/station_v0_bogota_dc42_sp30.yaml)
with only number_of_charging_stations and transformer.max_power changed;
the demand lives in the `<config>.arrivals.json` sidecar. spawn_multiplier
and ev.min_time_of_stay stay in the YAML but are not read by the generator.

Demand levels by offered energy (labelled assumption, Week 8 brief B4): 1.0x
keeps the current DC offered energy, 627 kWh/day (results/dwell_d_physical_units.csv,
DC 42 min, 1.0x: 627.2 kWh/day, served plus rejected lower bound); 1.3x and
1.6x scale it (815.1 and 1,003.2 kWh/day). EV2Gym's weekday and weekend
arrival profiles both sum to 100 (distribution-of-arrival[-weekend].csv,
'public'), i.e. the library gives both day types the same expected daily
arrival total; one arrivals/day value is therefore calibrated per level and
used for both day types, each with its own tau shape (B4: "the same daily
total multiplier").
"""
import os
import re
import tempfile

import numpy as np

from ev2gym_thesis.demand import station_arrivals as sa
from ev2gym_thesis.demand.dc_sessions import DwellModel

BASE_CONFIG = "experiments/phase3_infra_replicability/configs/dwell/station_v0_bogota_dc42_sp30.yaml"
CONFIG_DIR = "experiments/phase4_review/configs"
OFFERED_KWH_1X = 627.0
LEVELS = (1.0, 1.3, 1.6)
CALIBRATION_DAYS = ((2022, 1, 17), (2022, 3, 5))
CALIBRATION_SEEDS = range(0, 50)
CALIBRATION_CSV = "experiments/phase4_review/calibration.csv"  # scripts/calibrate_station_arrivals.py


def calibrated_arrivals_per_day(level: float) -> float:
    import pandas as pd
    c = pd.read_csv(CALIBRATION_CSV)
    row = c[np.isclose(c["level"], level)]
    assert len(row) == 1, f"level {level} not calibrated in {CALIBRATION_CSV}"
    return float(row["arrivals_per_day"].iloc[0])


def config_name(level=None, ports=8, kw=100.0, arrivals_per_day=None, extra_connected_steps=0,
                dead_time_steps=0, tag=""):
    lv = f"{level:.2f}x" if arrivals_per_day is None else f"a{arrivals_per_day:.3f}"
    name = f"station_v0_bogota_dc42_poisson_{lv}_p{ports}_tr{kw:g}"
    if extra_connected_steps:
        name += f"_conn+{extra_connected_steps}"
    if dead_time_steps:
        name += f"_dead{dead_time_steps}"
    return name + (f"_{tag}" if tag else "")


def write_if_changed(path: str, text: str):
    """Atomic write, skipped when the file already holds this text: several
    worker processes write the same config, and a reader must never see a
    half-written YAML (found when two C5 workers raced, 2026-11-03)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def write_config(level=None, ports=8, kw=100.0, arrivals_per_day=None, extra_connected_steps=0,
                 dead_time_steps=0, tag="", out_dir=CONFIG_DIR, dwell=DwellModel(42.0, 0.5), timescale=15,
                 load_dependent_departure_cap_min=0.0, energy_scale=1.0) -> str:
    """Write (or overwrite identically) a config + sidecar; return the YAML path.
    Either a calibrated level or an explicit arrivals_per_day."""
    if arrivals_per_day is None:
        arrivals_per_day = calibrated_arrivals_per_day(level)
    name = config_name(level, ports, kw, None if level is not None else arrivals_per_day,
                       extra_connected_steps, dead_time_steps, tag)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name + ".yaml").replace("\\", "/")
    text = open(BASE_CONFIG, encoding="utf-8").read()
    text = re.sub(r"(?m)^number_of_charging_stations: *\d+.*$",
                  f"number_of_charging_stations: {ports} # Week 8 review port variant (base 8)", text)
    text = re.sub(r"(?m)^  max_power: *[\d.]+.*$",
                  f"  max_power: {kw:g} # Week 8 review transformer variant, kW (base 100)", text)
    if timescale != 15:  # Block D2: same day (05:00 to 05:00), finer step
        text = re.sub(r"(?m)^timescale: *\d+.*$", f"timescale: {timescale} # Week 8 review D2 (base 15)", text)
        text = re.sub(r"(?m)^simulation_length: *\d+.*$",
                      f"simulation_length: {24 * 60 // timescale} # Week 8 review D2: one day", text)
    text = re.sub(r"(?m)^spawn_multiplier: *[\d.]+.*$",
                  "spawn_multiplier: 30 # NOT READ: arrivals come from the station_arrivals sidecar "
                  "(<config>.arrivals.json)", text)
    header = ("# Week 8 advisor review (2026-11-01), Block B/C: DC regime with the station-level\n"
              "# arrival generator (ev2gym_thesis/demand/station_arrivals.py). Demand, dwell and\n"
              "# port-assignment parameters are in the sidecar " + name + ".arrivals.json.\n")
    write_if_changed(path, header + text)
    spec = sa.ArrivalSpec({"weekday": arrivals_per_day, "weekend": arrivals_per_day}, dwell,
                          dead_time_steps, extra_connected_steps,
                          level=float(level) if level is not None else float("nan"),
                          level_label=f"{level:.1f}x" if level is not None else "",
                          load_dependent_departure_cap_min=load_dependent_departure_cap_min,
                          energy_scale=energy_scale)
    sa.write_sidecar(path, spec, {"offered_kwh_target_1x": OFFERED_KWH_1X,
                                  "calibration": "experiments/phase4_review/calibration.csv"})
    return path


def offered_mean(arrivals_per_day, envs, seeds=CALIBRATION_SEEDS, spec_kwargs=None):
    """Mean (arrivals, kWh) offered over seeds x the given day envs."""
    spec = sa.ArrivalSpec({"weekday": arrivals_per_day, "weekend": arrivals_per_day}, **(spec_kwargs or {}))
    a, e = [], []
    for env in envs:
        for s in seeds:
            n, kwh = sa.offered_energy(env, spec, s)
            a.append(n)
            e.append(kwh)
    return float(np.mean(a)), float(np.mean(e))
