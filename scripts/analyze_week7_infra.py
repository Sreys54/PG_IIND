"""
Week 7, Objective 4 (Step 2 analysis): grid-enabled infrastructure study.

Inputs: the registry's grid rows (analysis_row=True, simulate_grid=True, the
5 Week 7 setting configs), results/week7_voltage_by_run.csv,
results/week7_voltage_zero_charging_baseline.csv, and each run's saved
timeseries (results/timeseries/<run_id>.npz) for peak station power.

Every comparison uses ev2gym_thesis.stats_utils.paired_cluster_bootstrap_ci,
resampling the scenario seed, with n_clusters written to every table. The
CI of a single arm's mean is the same function applied to (0, x): the paired
difference against zero, resampled by seed.

Writes results/week7_*.csv (xlsx: scripts/export_week7_results_xlsx.py).

Usage:
  PYTHONPATH=. python scripts/analyze_week7_infra.py               # registry rows
  PYTHONPATH=. python scripts/analyze_week7_infra.py --from-shards # development only
"""
import argparse
import glob

import numpy as np
import pandas as pd

from ev2gym_thesis.grid import placement
from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

from scripts import analyze_week5_results as w5
from scripts import run_week7_grid as w7

N_BOOT = 10_000
ARMS = w7.ARMS
REFERENCE = "RoundRobin"
# doc:begin week7_axes
AXES = {
    "axis1_station_demand": [("base", 1.0), ("spawn1.3", 1.3), ("spawn1.6", 1.6)],
    "axis2_feeder_background": [("base", 1.0), ("load1.3", 1.3), ("load1.6", 1.6)],
}
# doc:end week7_axes
METRICS = w5.HEADLINE_METRICS + ["total_energy_charged", "energy_user_satisfaction"]
SATISFACTION_TARGET = 0.90
ENS_TARGET_PCT = 15.0
STANDARD_TRANSFORMER_KVA = [75, 112.5, 150, 225, 300, 400, 500, 630]  # common Colombian distribution sizes (declared, unity power factor)


def boot(a, b, clusters):
    r = paired_cluster_bootstrap_ci(np.asarray(a, float), np.asarray(b, float), np.asarray(clusters),
                                    n_bootstrap=N_BOOT, seed=0)
    return r


def mean_ci(x, clusters):
    r = boot(np.zeros(len(x)), x, clusters)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def load_grid_df(from_shards=False):
    if from_shards:
        df = pd.concat([pd.read_csv(p) for p in glob.glob(f"{w7.SHARD_DIR}/registry_rows_w*.csv")], ignore_index=True)
    else:
        df = pd.read_csv("results/master_results.csv", low_memory=False)
        df = df[(df.analysis_row.astype(str) == "True") & (df.simulate_grid.astype(str) == "True")]
    names = {w7.config_name_for(s): s for s in w7.SETTINGS}
    df = df[df.config_name.isin(names)].copy()
    df["setting"] = df.config_name.map(names)
    df["seed"] = df.seed.astype(int)
    for m in METRICS + ["total_energy_discharged", "voltage_violation", "voltage_violation_counter"]:
        df[m] = df[m].astype(float)
    return df


def present(df):
    return [s for s in w7.SETTINGS if s in set(df.setting)]


def complete_cells(df, require_all_settings=True):
    """Keep, per setting, only the seeds with all 5 arms x 2 days present.
    For the final analysis every setting must hold the same complete seed
    set (asserted); --from-shards (development) relaxes this."""
    keep = []
    seed_sets = {}
    for st, g in df.groupby("setting"):
        c = g.groupby("seed").size()
        seeds = set(c[c == len(ARMS) * 2].index)
        seed_sets[st] = seeds
        keep.append(g[g.seed.isin(seeds)])
    if require_all_settings:
        same_seeds = len({frozenset(v) for v in seed_sets.values()}) == 1
        assert set(seed_sets) == set(w7.SETTINGS) and same_seeds, {k: len(v) for k, v in seed_sets.items()}
    out = pd.concat(keep, ignore_index=True)
    return out[out.setting.isin([s for s, v in seed_sets.items() if v])]


# ---------------------------------------------------------------------------
# doc:begin base_equivalence_all_arms
def base_equivalence_all_arms(df):
    """Full-scale version of Step 1b: every base-setting grid row must equal
    the non-grid registry row of the same arm, seed and day on every station
    metric (the station model is identical; only voltage is new). Also
    guards the shard data against the Week 7 day-config race (a corrupted
    read would show up here as a mismatch)."""
    reg = pd.read_csv("results/master_results.csv", low_memory=False)
    ng = reg[(reg.analysis_row.astype(str) == "True") & (reg.config_name == "station_v0_bogota")].copy()
    ng["seed"] = ng.seed.astype(int)
    g = df[df.setting == "base"]
    m = g.merge(ng, on=["algorithm", "seed", "eval_day"], suffixes=("_grid", "_nongrid"))
    rows = []
    for metric in METRICS:
        d = (m[f"{metric}_grid"].astype(float) - m[f"{metric}_nongrid"].astype(float)).abs()
        rows.append({"metric": metric, "n_cells": len(m), "n_arms": m.algorithm.nunique(),
                     "max_abs_diff": float(d.max()), "identical": bool(d.max() <= 1e-6)})
    out = pd.DataFrame(rows)
    out.to_csv("results/week7_grid_base_equivalence_all_arms.csv", index=False)
    assert out.identical.all(), out
    return out
# doc:end base_equivalence_all_arms


def master(df):
    rows = []
    for st in present(df):
        for arm in ARMS:
            sub = df[(df.setting == st) & (df.algorithm == arm)]
            row = {"setting": st, "algorithm": arm, "n_rows": len(sub)}
            for m in METRICS:
                pt, lo, hi, nc = mean_ci(sub[m], sub.seed)
                row.update({f"{m}_mean": pt, f"{m}_ci_low": lo, f"{m}_ci_high": hi})
            row["n_clusters"] = nc
            rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv("results/week7_grid_master_comparison.csv", index=False)
    return out


def paired_table(df, pairs, out):
    rows = []
    for st, a, b in pairs:
        A = df[(df.setting == st[0]) & (df.algorithm == a)]
        B = df[(df.setting == st[1]) & (df.algorithm == b)]
        m_ = A.merge(B, on=["seed", "day_type"], suffixes=("_a", "_b"))
        for m in METRICS:
            r = boot(m_[f"{m}_a"], m_[f"{m}_b"], m_.seed)
            rows.append({"setting_A": st[0], "setting_B": st[1], "algorithm_A": a, "algorithm_B": b, "metric": m,
                         "mean_A": m_[f"{m}_a"].mean(), "mean_B": m_[f"{m}_b"].mean(),
                         "diff_B_minus_A": r["point_estimate"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                         "ci_excludes_zero": bool(r["ci_low"] > 0 or r["ci_high"] < 0),
                         "n_pairs": r["n_pairs"], "n_clusters": r["n_clusters"]})
    t = pd.DataFrame(rows)
    t.to_csv(out, index=False)
    return t


def ens(df):
    frames = []
    for st in present(df):
        _, path = w7.setting_config(st)
        sub = df[df.setting == st].copy()
        sub["eval_day"] = sub["eval_day"].astype(str)
        tmp = f"results/week7_tmp_ens_{st}.csv"
        e = w5.ens_and_compliance(sub, algos=ARMS, out_path=tmp,
                                  requested_energy_out_path=f"results/week7_tmp_req_{st}.csv", config_path=path)
        e.insert(0, "setting", st)
        frames.append(e)
        import os
        os.remove(tmp)
        os.remove(f"results/week7_tmp_req_{st}.csv")
    out = pd.concat(frames, ignore_index=True)
    out.to_csv("results/week7_grid_ens_compliance.csv", index=False)
    return out


# doc:begin transformer_sizing
def transformer_sizing(df):
    """Per run: peak station power (kW) from the saved timeseries. Per seed:
    mean overload over the two day types (kWh/day) and the max peak over the
    two days. Per arm x setting: empirical quantiles over the 50 seeds, and
    the rating (kW) at which the 95th-percentile seed would stop overloading
    = the 95th percentile of the per-seed peak. Valid as a sizing number for
    arms whose power does not respond to the 100 kW limit (AFAP); for
    limit-aware arms it is the peak they actually drew under the 100 kW
    limit, so a bigger transformer would not change it downward."""
    peaks = []
    for _, r in df.iterrows():
        d = np.load(f"results/timeseries/{r.run_id}.npz")
        peaks.append(float(np.max(d["station_power"])))
    df = df.assign(peak_station_kw=peaks)
    per_seed = df.groupby(["setting", "algorithm", "seed"]).agg(
        overload_kwh_per_day=("total_transformer_overload", "mean"), peak_kw=("peak_station_kw", "max")).reset_index()
    per_seed.to_csv("results/week7_transformer_per_seed.csv", index=False)
    rows = []
    for (st, arm), g in per_seed.groupby(["setting", "algorithm"]):
        q = lambda s, p: float(np.quantile(s, p))
        p95 = q(g.peak_kw, 0.95)
        rows.append({"setting": st, "algorithm": arm, "n_seeds": len(g),
                     "seeds_with_overload": int((g.overload_kwh_per_day > 0).sum()),
                     "overload_p50": q(g.overload_kwh_per_day, .5), "overload_p90": q(g.overload_kwh_per_day, .9),
                     "overload_p95": q(g.overload_kwh_per_day, .95), "overload_max": g.overload_kwh_per_day.max(),
                     "peak_kw_p50": q(g.peak_kw, .5), "peak_kw_p90": q(g.peak_kw, .9), "peak_kw_p95": p95,
                     "peak_kw_max": g.peak_kw.max(),
                     "rating_kw_for_p95_seed_no_overload": p95,
                     "next_standard_kva_unity_pf": next((s for s in STANDARD_TRANSFORMER_KVA if s >= p95), None),
                     "seeds_above_p95": int((g.peak_kw > p95).sum())})
    out = pd.DataFrame(rows)
    out.to_csv("results/week7_transformer_sizing.csv", index=False)
    return out, df
# doc:end transformer_sizing


# doc:begin voltage_attribution
def voltage_attribution(df):
    """Station-attributable voltage effect: each arm's run minus the
    idle-station (zero-charging) baseline of the SAME (setting, seed, day)."""
    import os
    if os.path.exists("results/week7_voltage_by_run.csv"):
        v = pd.read_csv("results/week7_voltage_by_run.csv")
    else:  # development (--from-shards) before the merge
        v = pd.concat([pd.read_csv(p) for p in glob.glob(f"{w7.SHARD_DIR}/voltage_w*.csv")], ignore_index=True)
    z = pd.read_csv("results/week7_voltage_zero_charging_baseline.csv")
    v = v[v.run_id.isin(df.run_id)]
    m = v.merge(z, on=["setting", "seed", "eval_day"], suffixes=("", "_idle"))
    m["delta_bus_steps_outside"] = m.n_bus_steps_outside - m.n_bus_steps_outside_idle
    m["delta_min_voltage_pu"] = m.min_voltage_pu - m.min_voltage_pu_idle
    m["delta_excursion_pu_steps"] = m.excursion_pu_steps - m.excursion_pu_steps_idle
    m["delta_station_bus_steps_outside"] = m.station_bus_steps_outside - m.station_bus_steps_outside_idle
    m.to_csv("results/week7_voltage_attribution_by_run.csv", index=False)
    rows = []
    for (st, arm), g in m.groupby(["setting", "algorithm"]):
        row = {"setting": st, "algorithm": arm, "n_runs": len(g),
               "cells_idle_feeder_outside_band": int((g.n_bus_steps_outside_idle > 0).sum()),
               "cells_with_arm_outside_band": int((g.n_bus_steps_outside > 0).sum()),
               "cells_station_adds_outside_samples": int((g.delta_bus_steps_outside > 0).sum()),
               "min_voltage_pu_worst": g.min_voltage_pu.min(), "min_voltage_pu_idle_worst": g.min_voltage_pu_idle.min()}
        for col in ["delta_bus_steps_outside", "delta_min_voltage_pu", "delta_excursion_pu_steps",
                    "delta_station_bus_steps_outside", "n_bus_steps_outside"]:
            pt, lo, hi, nc = mean_ci(g[col], g.seed)
            row.update({f"{col}_mean": pt, f"{col}_ci_low": lo, f"{col}_ci_high": hi})
        row["n_clusters"] = nc
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv("results/week7_voltage_attribution.csv", index=False)
    return out
# doc:end voltage_attribution


def margin(df):
    """Bogota flat-tariff economics (Week 5 constants), margin conceded vs.
    AFAP in COP per simulated day, paired by cell."""
    unit = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
    rows = []
    for st in present(df):
        afap = df[(df.setting == st) & (df.algorithm == "ChargeAsFastAsPossible")]
        for arm in ARMS:
            b = df[(df.setting == st) & (df.algorithm == arm)]
            m_ = afap.merge(b, on=["seed", "day_type"], suffixes=("_a", "_b"))
            r = boot(m_.total_energy_charged_a * unit, m_.total_energy_charged_b * unit, m_.seed)
            pt, lo, hi, nc = mean_ci(b.total_energy_charged * unit, b.seed)
            rows.append({"setting": st, "algorithm": arm, "gross_margin_cop_per_day_mean": pt,
                         "gross_margin_ci_low": lo, "gross_margin_ci_high": hi,
                         "margin_conceded_vs_afap_cop_per_day": -r["point_estimate"],
                         "conceded_ci_low": -r["ci_high"], "conceded_ci_high": -r["ci_low"],
                         "unit_margin_cop_per_kwh": unit, "n_clusters": r["n_clusters"]})
    out = pd.DataFrame(rows)
    out.to_csv("results/week7_grid_margin_bogota.csv", index=False)
    return out


def compliance(master_df, ens_df, volt_df):
    rows = []
    for st in [s for s in w7.SETTINGS if s in set(master_df.setting)]:
        for arm in ARMS:
            mrow = master_df[(master_df.setting == st) & (master_df.algorithm == arm)].iloc[0]
            erow = ens_df[(ens_df.setting == st) & (ens_df.algorithm == arm)].iloc[0]
            vrow = volt_df[(volt_df.setting == st) & (volt_df.algorithm == arm)].iloc[0]
            rows.append({
                "setting": st, "algorithm": arm,
                "avg_satisfaction_mean": mrow.average_user_satisfaction_mean,
                "avg_satisfaction_ci_low": mrow.average_user_satisfaction_ci_low,
                "satisfaction_target_met_ci_lower_gt_90pct": bool(mrow.average_user_satisfaction_ci_low > SATISFACTION_TARGET),
                "ens_rel_point_pct": erow.ENS_rel_point_pct, "ens_rel_ci_high_pct": erow.ENS_rel_ci_high_pct,
                "ens_target_met_ci_upper_lt_15pct": bool(erow.ENS_rel_ci_high_pct < ENS_TARGET_PCT),
                "voltage_cells_station_adds_outside_samples": int(vrow.cells_station_adds_outside_samples),
                "voltage_cells_total": int(vrow.n_runs),
                "voltage_station_increment_ci_high": vrow.delta_bus_steps_outside_ci_high,
                "voltage_station_adds_no_excursion_all_cells": bool(vrow.cells_station_adds_outside_samples == 0),
                "voltage_cells_idle_feeder_outside_band": int(vrow.cells_idle_feeder_outside_band),
                "n_clusters": int(mrow.n_clusters)})
    out = pd.DataFrame(rows)
    out.to_csv("results/week7_target_compliance.csv", index=False)
    return out


def main(from_shards=False):
    price_data_cache.enable()
    placement.enable()
    df = complete_cells(load_grid_df(from_shards), require_all_settings=not from_shards)
    print(f"grid rows used: {len(df)}; seeds per setting: {df.groupby('setting').seed.nunique().to_dict()}")
    print(base_equivalence_all_arms(df).to_string(index=False))
    m = master(df)
    paired_table(df, [((st, st), REFERENCE, arm) for st in present(df) for arm in ARMS if arm != REFERENCE],
                 "results/week7_grid_vs_roundrobin.csv")
    growth_pairs = [(("base", lvl_st), arm, arm) for axis in AXES.values() for lvl_st, _ in axis[1:] for arm in ARMS
                    if lvl_st in present(df) and "base" in present(df)]
    paired_table(df, growth_pairs, "results/week7_grid_growth_effect.csv")
    e = ens(df)
    sizing, df = transformer_sizing(df)
    v = voltage_attribution(df)
    margin(df)
    c = compliance(m, e, v)
    print(c.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-shards", action="store_true")
    main(ap.parse_args().from_shards)
