"""
Week 7, Objective 4 (Step 1d): what EV2Gym's voltage metrics measure, and an
independent post-processing check against the +/-5% band.

EV2Gym's own definitions (ev2gym/utilities/utils.py::get_statistics, read
from source, simulate_grid=True only), on env.node_voltage, an array of
shape (node_num, simulation_length) in per unit, row 0 = slack bus fixed at
1.0 p.u.:
  - voltage_violation: sum over ALL buses and ALL steps of
    min(0, 0.05 - |1 - v|) -- an aggregate, cumulative, NON-POSITIVE number
    in p.u.*step (total per-unit excursion beyond the band); 0 means no
    excursion anywhere. Returned as a 1-tuple (trailing comma in the
    library), which registry._coerce_scalar sums to a float.
  - voltage_violation_counter: number of (bus, step) samples with v < 0.95
    or v > 1.05 -- aggregate count over buses and steps.
  - voltage_violation_counter_per_step: number of STEPS in which at least
    one bus is outside [0.95, 1.05].
The band is hard-coded as 0.95-1.05 p.u., i.e. +/-5% around 1.0 p.u.

The +/-5% band is the band this thesis adopts for RETIE compliance (see
CLAUDE.md and chapter 06). The library's band is numerically the same band,
but it is computed by library code we do not own; band_check() below
recomputes compliance independently from the raw per-bus voltage series so
the compliance statement does not rest on the library's aggregation alone,
and also reports the station bus separately.
"""
import numpy as np

RETIE_BAND_LOW = 0.95
RETIE_BAND_HIGH = 1.05


# doc:begin band_check
def band_check(node_voltage: np.ndarray, station_bus: int = None,
               low: float = RETIE_BAND_LOW, high: float = RETIE_BAND_HIGH) -> dict:
    """Independent +/-5% compliance check on an (node_num x steps) per-unit
    voltage array (row 0 = bus 1, the slack). Steps never simulated (all
    zeros, e.g. the final step) are excluded."""
    v = np.asarray(node_voltage, dtype=float)
    simulated = np.any(v != 0, axis=0)
    v = v[:, simulated]
    outside = (v < low) | (v > high)
    out = {
        "n_steps": int(v.shape[1]),
        "n_bus_steps_outside": int(outside.sum()),
        "n_steps_any_bus_outside": int(np.any(outside, axis=0).sum()),
        "min_voltage_pu": float(v.min()) if v.size else float("nan"),
        "max_voltage_pu": float(v.max()) if v.size else float("nan"),
        "worst_bus": int(np.unravel_index(np.argmin(v), v.shape)[0] + 1) if v.size else -1,
        "excursion_pu_steps": float(np.maximum(0, np.abs(1 - v) - (high - 1)).sum()),
    }
    if station_bus is not None:
        sv = v[station_bus - 1]
        out["station_bus_min_voltage_pu"] = float(sv.min())
        out["station_bus_steps_outside"] = int(((sv < low) | (sv > high)).sum())
    return out
# doc:end band_check
