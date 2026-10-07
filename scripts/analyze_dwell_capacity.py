"""
Final capacity brief, Parts C-E analysis, under the DC session-duration model
(primary, Checkpoint A) -- post-processing only, nothing written to any
registry.

Inputs:
  results/dwell_registry.csv          runs (scripts/run_dwell_capacity.py --merge)
  results/dwell_censoring_by_cell.csv policy-independent rejected-arrival replay
  results/timeseries/<run_id>.npz     station power, for the peak

Per run:
  DNS (lower bound)  = (E_rej_lower + R_served - E_delivered) / (E_rej_lower + R_served)
                       (ev2gym_thesis/demand/censoring.py::demand_not_served)
  satisfaction counting rejected arrivals
                     = average_user_satisfaction x n_spawned / (n_spawned + rejected_lower)
                       (a rejected arrival counts with satisfaction 0; closure definition)
  peak               = max station power over the day (kW)
  margin             = total_energy_charged x (1,450 - 865.7615) COP/kWh (Bogota)

Breaking criteria (brief C1), each on 100 runs (50 seeds x 2 days), judged on
the CI side that is hardest to claim (closure convention, conservative,
labelled); means with paired_cluster_bootstrap_ci over the scenario seed
(n_clusters = 50), 10,000 draws, seed 0:
  - satisfaction counting rejected arrivals: CI lower bound < 0.90;
  - DNS (lower bound): CI upper bound > 0.15;
  - P95 station peak: CI upper bound > the transformer rating in kW (100 kW in
    C1; the candidate's own rating in C2 -- labelled reading: the brief's
    "100 kW" is the reference unit's rating). P95 over the 50 per-seed peaks
    (max over the two days), CI by resampling seeds.

Outputs:
  results/dwell_c1_capacity_by_level.csv   per (variant, level, arm)
  results/dwell_c1_breaking_levels.csv     per (variant, arm): threshold, first
                                           criterion, per-criterion first break
  results/dwell_c2_growth_options.csv      per (level, arm, ports, kW)
  results/dwell_c2_minimal_configs.csv     Pareto-minimal (ports, kVA) meeting all
  results/dwell_d_physical_units.csv       per (model, level[, ports]): arrivals/day,
                                           kWh requested/day, per port, occupancy
  results/dwell_e_target_compliance.csv    1.0/1.3/1.6x, AFAP/RR/final RL

Usage: PYTHONPATH=. python scripts/analyze_dwell_capacity.py
"""
import numpy as np
import pandas as pd

from ev2gym_thesis.demand.censoring import demand_not_served
from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

REG = "results/dwell_registry.csv"
CENS = "results/dwell_censoring_by_cell.csv"
RL = "TD3_vanilla_extended_ts102"
RR_CAPPED = "RoundRobin_TransformerCapped"  # diagnostic arm, ev2gym_thesis/heuristics.py
ARMS = ["ChargeAsFastAsPossible", "RoundRobin", RL, RR_CAPPED]
SAT_MIN, DNS_MAX = 0.90, 0.15
PF = 0.894
UNIT_MARGIN = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
N_BOOT = 10_000
LEVEL_LABEL = {0.25: "0.267x (spawn 8)", 0.75: "0.733x (spawn 22)"}
KVA = {100.0: "reference 100 kW unit (111.9 kVA at pf 0.894; 112.5 kVA class)", 134.2: "150 kVA",
       201.2: "225 kVA", 268.3: "300 kVA", 357.8: "400 kVA"}


def level_label(lvl):
    return LEVEL_LABEL.get(lvl, f"{lvl:g}x")


def load():
    reg = pd.read_csv(REG, low_memory=False)
    n = reg.notes.fillna("")
    reg["part"] = n.str.extract(r"dwell_part=(\w+)")[0]
    reg["dwell_mean"] = n.str.extract(r"dwell_mean_min=([0-9.]+)")[0].astype(float)
    reg["level"] = n.str.extract(r"demand_level=([0-9.]+)")[0].astype(float)
    reg["ports"] = n.str.extract(r"ports=(\d+)")[0].astype(int)
    reg["kw"] = n.str.extract(r"transformer_kw=([0-9.]+)")[0].astype(float)
    reg["seed"] = reg.seed.astype(float).astype(int)
    cens = pd.read_csv(CENS)
    cens["seed"] = cens.seed.astype(int)
    m = reg.merge(cens.drop(columns=["dwell_mean_min", "level", "ports", "transformer_kw", "constant_demand"]),
                  on=["config_name", "seed", "eval_day"], how="left", validate="many_to_one")
    if m.n_spawned.isna().any():
        raise ValueError("censoring missing for some runs")
    if not np.allclose(m.n_spawned, m.total_ev_served):
        raise AssertionError("censoring population != run population")
    m["dns_lower"] = [demand_not_served(e, r, "lower") for e, (_, r) in zip(m.total_energy_charged, m.iterrows())]
    m["dns_upper"] = [demand_not_served(e, r, "upper") for e, (_, r) in zip(m.total_energy_charged, m.iterrows())]
    m["sat_all_arrivals"] = m.average_user_satisfaction * m.n_spawned / (m.n_spawned + m.rejected_lower)
    m["gross_margin_cop"] = m.total_energy_charged * UNIT_MARGIN
    m["peak_station_kw"] = [float(np.max(np.load(f"results/timeseries/{rid}.npz")["station_power"]))
                            for rid in m.run_id]
    return m


def mean_ci(x, clusters):
    r = paired_cluster_bootstrap_ci(np.zeros(len(x)), np.asarray(x, float), np.asarray(clusters),
                                    n_bootstrap=N_BOOT, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def p95_ci(v):
    v = np.asarray(v, float)
    rng = np.random.default_rng(0)
    boots = np.quantile(v[rng.integers(0, len(v), size=(N_BOOT, len(v)))], 0.95, axis=1)
    return float(np.quantile(v, 0.95)), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


# doc:begin dwell_summarize
def summarize(g, rating_kw):
    row = {"n_runs": len(g)}
    for col in ["sat_all_arrivals", "average_user_satisfaction", "dns_lower", "dns_upper",
                "total_transformer_overload", "total_energy_charged", "gross_margin_cop", "total_ev_served"]:
        pt, lo, hi, nc = mean_ci(g[col], g.seed)
        row.update({f"{col}_mean": pt, f"{col}_ci_low": lo, f"{col}_ci_high": hi})
    per_seed = g.groupby("seed").agg(peak=("peak_station_kw", "max"), ov=("total_transformer_overload", "sum"))
    pt, lo, hi = p95_ci(per_seed.peak)
    row.update({"peak_kw_p95": pt, "peak_kw_p95_ci_low": lo, "peak_kw_p95_ci_high": hi,
                "peak_kva_p95_at_pf_0894": pt / PF, "rating_kw": rating_kw,
                "cells_with_overload": int((g.total_transformer_overload > 0).sum()),
                "seeds_with_overload": int((per_seed.ov > 0).sum()), "n_clusters": nc})
    row["broken_satisfaction"] = row["sat_all_arrivals_ci_low"] < SAT_MIN
    row["broken_dns"] = row["dns_lower_ci_high"] > DNS_MAX
    row["broken_peak"] = row["peak_kw_p95_ci_high"] > rating_kw
    row["meets_all"] = not (row["broken_satisfaction"] or row["broken_dns"] or row["broken_peak"])
    return row
# doc:end dwell_summarize


CRIT = [("satisfaction", "sat_all_arrivals"), ("dns", "dns_lower"), ("peak", "peak_kw_p95")]


def _value_keys(name, col):
    if name == "peak":
        return "peak_kw_p95", "peak_kw_p95_ci_low", "peak_kw_p95_ci_high"
    return f"{col}_mean", f"{col}_ci_low", f"{col}_ci_high"


# doc:begin dwell_c1
def c1_tables(m):
    c1 = m[(m.ports == 8) & (m.kw == 100.0)]
    rows = []
    for (dm, lvl, arm), g in c1.groupby(["dwell_mean", "level", "algorithm"]):
        rows.append({"dwell_mean_min": dm, "level": lvl, "level_label": level_label(lvl),
                     "spawn_multiplier": int(round(30 * lvl)), "algorithm": arm, **summarize(g, 100.0)})
    by_level = pd.DataFrame(rows).sort_values(["dwell_mean_min", "algorithm", "level"])
    by_level.to_csv("results/dwell_c1_capacity_by_level.csv", index=False)
    brk = []
    for (dm, arm), g in by_level.groupby(["dwell_mean_min", "algorithm"]):
        g = g.sort_values("level")
        rec = {"dwell_mean_min": dm, "algorithm": arm, "levels_tested": ",".join(f"{x:g}" for x in g.level),
               "lowest_level_tested": g.level.min()}
        for name, _ in CRIT:
            hit = g[g[f"broken_{name}"]]
            rec[f"first_level_broken_{name}"] = hit.level.min() if len(hit) else None
        hit = g[~g.meets_all]
        if not len(hit):
            rec.update({"breaking_level": None, "highest_level_not_broken": g.level.max()})
        else:
            r = hit.iloc[0]
            broken = [n for n, _ in CRIT if r[f"broken_{n}"]]
            col = dict(CRIT)[broken[0]]
            v, lo, hi = _value_keys(broken[0], col)
            below = g[g.level < r.level]
            ok_below = below[below.meets_all]
            rec.update({"breaking_level": r.level, "breaking_level_label": r.level_label,
                        "highest_level_not_broken": ok_below.level.max() if len(ok_below) else None,
                        "breaks_at_lowest_level_tested": r.level == g.level.min(),
                        "criteria_broken_at_breaking_level": ";".join(broken),
                        "first_criterion": broken[0], "value": r[v], "ci_low": r[lo], "ci_high": r[hi],
                        "confirmed_one_level_beyond": bool(len(g[g.level > r.level]) and
                                                           (~g[g.level > r.level].iloc[0:1].meets_all).all()),
                        "n_clusters": r.n_clusters})
        brk.append(rec)
    brk = pd.DataFrame(brk)
    brk.to_csv("results/dwell_c1_breaking_levels.csv", index=False)
    return by_level, brk
# doc:end dwell_c1


# doc:begin dwell_c2
def c2_tables(m):
    rows = []
    for lvl in (1.3, 1.6):
        sub = m[(m.level == lvl) & (m.dwell_mean == 42.0) & m.algorithm.isin(["RoundRobin", "ChargeAsFastAsPossible", RR_CAPPED])]
        ref = sub[(sub.ports == 8) & (sub.kw == 100.0)]
        for (arm, ports, kw), g in sub.groupby(["algorithm", "ports", "kw"]):
            r = {"level": lvl, "level_label": level_label(lvl), "algorithm": arm, "ports": ports,
                 "transformer_kw": kw, "transformer_rating": KVA.get(kw, f"{kw:g} kW"),
                 "station_demand": "constant (spawn x 8/ports)" if ports != 8 else "reference (8 ports)",
                 **summarize(g, kw)}
            p = ref[ref.algorithm == arm].merge(g, on=["seed", "eval_day"], suffixes=("_ref", ""))
            assert len(p) == 100, (lvl, arm, ports, kw, len(p))
            for col in ["dns_lower", "gross_margin_cop"]:
                d = paired_cluster_bootstrap_ci(p[col + "_ref"], p[col], p.seed, n_bootstrap=N_BOOT, seed=0)
                r.update({f"delta_{col}_vs_8p100kw": d["point_estimate"], f"delta_{col}_ci_low": d["ci_low"],
                          f"delta_{col}_ci_high": d["ci_high"]})
            rows.append(r)
    out = pd.DataFrame(rows).sort_values(["level", "algorithm", "ports", "transformer_kw"])
    out.to_csv("results/dwell_c2_growth_options.csv", index=False)
    mins = []
    for (lvl, arm), g in out.groupby(["level", "algorithm"]):
        ok = g[g.meets_all]
        pareto = [r for _, r in ok.iterrows()
                  if not ((ok.ports <= r.ports) & (ok.transformer_kw <= r.transformer_kw)
                          & ((ok.ports < r.ports) | (ok.transformer_kw < r.transformer_kw))).any()]
        if not pareto:
            mins.append({"level": lvl, "algorithm": arm, "minimal_config": "none in the searched grid",
                         "searched_ports": ",".join(map(str, sorted(g.ports.unique()))),
                         "searched_kw": ",".join(f"{k:g}" for k in sorted(g.transformer_kw.unique()))})
        for r in pareto:
            mins.append({"level": lvl, "algorithm": arm, "minimal_config": f"{r.ports} ports, {r.transformer_rating}",
                         "ports": r.ports, "transformer_kw": r.transformer_kw,
                         **{k: r[k] for k in ["dns_lower_mean", "dns_lower_ci_low", "dns_lower_ci_high",
                                              "sat_all_arrivals_mean", "sat_all_arrivals_ci_low",
                                              "total_transformer_overload_mean", "cells_with_overload",
                                              "peak_kw_p95", "peak_kw_p95_ci_high", "gross_margin_cop_mean",
                                              "gross_margin_cop_ci_low", "gross_margin_cop_ci_high", "n_clusters"]}})
    mins = pd.DataFrame(mins)
    mins.to_csv("results/dwell_c2_minimal_configs.csv", index=False)
    return out, mins
# doc:end dwell_c2


# doc:begin dwell_physical_units
def physical_units():
    """Policy-independent demand in physical units, per (model, level[, ports]).
    Offered arrivals = spawned + rejected (lower bound); kWh requested = the
    spawned EVs' requested energy + the rejected arrivals' (mean) energy."""
    rows = []
    c = pd.read_csv(CENS)
    c["model"] = "DC " + c.dwell_mean_min.map(lambda x: f"{x:g}") + " min"
    d = pd.read_csv("results/closure_censoring_by_cell.csv").assign(model="Dutch (EV2Gym as configured)", ports=8,
                                                                      constant_demand=False)
    d["requested_kwh_spawned"] = d.requested_served_kwh
    for src in (c, d):
        for keys, g in src.groupby(["model", "level", "ports", "constant_demand"]):
            model, lvl, ports, cd = keys
            g = g.assign(offered=g.n_spawned + g.rejected_lower,
                         kwh_offered=g.requested_kwh_spawned + g.energy_rejected_lower_kwh)
            r = {"model": model, "level": lvl, "level_label": level_label(lvl), "spawn_multiplier_base": int(round(30 * lvl)),
                 "ports": int(ports), "constant_station_demand": bool(cd), "n_cells": len(g)}
            for col, name in [("offered", "arrivals_offered_per_day"), ("n_spawned", "arrivals_served_per_day"),
                              ("kwh_offered", "kwh_requested_per_day")]:
                pt, lo, hi, nc = mean_ci(g[col], g.seed)
                r.update({name: pt, f"{name}_ci_low": lo, f"{name}_ci_high": hi})
            r["kwh_requested_per_port_per_day"] = r["kwh_requested_per_day"] / ports
            if "mean_port_occupancy" in g:
                pt, lo, hi, _ = mean_ci(g.mean_port_occupancy, g.seed)
                r.update({"mean_port_occupancy": pt, "mean_port_occupancy_ci_low": lo, "mean_port_occupancy_ci_high": hi})
            r["n_clusters"] = nc
            rows.append(r)
    out = pd.DataFrame(rows).sort_values(["model", "ports", "level"])
    out.to_csv("results/dwell_d_physical_units.csv", index=False)
    return out
# doc:end dwell_physical_units


# doc:begin dwell_compliance
def compliance(m):
    """Brief E3: 1.0x, 1.3x, 1.6x, DC 42 min, 8 ports, 100 kW; AFAP, RR and
    the final RL model (out of its training distribution)."""
    rows = []
    for lvl in (1.0, 1.3, 1.6):
        sub = m[(m.level == lvl) & (m.dwell_mean == 42.0) & (m.ports == 8) & (m.kw == 100.0)]
        afap = sub[sub.algorithm == "ChargeAsFastAsPossible"].groupby("seed").total_energy_charged.sum()
        for arm in ARMS:
            g = sub[sub.algorithm == arm]
            assert len(g) == 100, (lvl, arm, len(g))
            s = summarize(g, 100.0)
            e = g.groupby("seed").total_energy_charged.sum()
            ens = ((afap - e) / afap).loc[afap.index]
            ens_pt, ens_lo, ens_hi, _ = mean_ci(ens.values, ens.index.values)
            st = lambda ok: "met" if ok else "not met"
            rows.append({
                "level": lvl, "algorithm": arm, "n_runs": 100, "n_clusters": s["n_clusters"],
                "sat_served_mean": s["average_user_satisfaction_mean"],
                "sat_served_ci_low": s["average_user_satisfaction_ci_low"],
                "sat_served_status": st(s["average_user_satisfaction_ci_low"] > SAT_MIN),
                "sat_all_arrivals_mean": s["sat_all_arrivals_mean"], "sat_all_arrivals_ci_low": s["sat_all_arrivals_ci_low"],
                "sat_all_arrivals_status": st(s["sat_all_arrivals_ci_low"] > SAT_MIN),
                "ens_rel_served_pct": 100 * ens_pt, "ens_rel_served_ci_high_pct": 100 * ens_hi,
                "ens_rel_served_status": st(ens_hi < 0.15),
                "dns_lower_mean": s["dns_lower_mean"], "dns_lower_ci_high": s["dns_lower_ci_high"],
                "dns_status": st(s["dns_lower_ci_high"] < DNS_MAX),
                "cells_with_overload": s["cells_with_overload"], "overload_kwh_mean": s["total_transformer_overload_mean"],
                "transformer_status": st(s["cells_with_overload"] == 0),
                "peak_kw_p95": s["peak_kw_p95"], "peak_kw_p95_ci_high": s["peak_kw_p95_ci_high"],
                "voltage_status": "not evaluable",
                "voltage_reason": ("not rerun under DC sessions; the 34-node feeder is out of band with the station idle, "
                                   "and the node_123 result (closure E2) used Dutch durations"),
                "note": ("out of its training distribution (trained on Dutch durations)" if arm == RL else
                         "diagnostic arm added by this brief (budget = transformer rating)" if arm == RR_CAPPED else ""),
            })
    out = pd.DataFrame(rows)
    out.to_csv("results/dwell_e_target_compliance.csv", index=False)
    return out
# doc:end dwell_compliance


def main():
    m = load()
    by_level, brk = c1_tables(m)
    c2, mins = c2_tables(m)
    pu = physical_units()
    comp = compliance(m)
    pd.set_option("display.width", 260)
    pd.set_option("display.max_columns", 40)
    print(by_level[["dwell_mean_min", "level_label", "algorithm", "sat_all_arrivals_mean", "sat_all_arrivals_ci_low",
                    "dns_lower_mean", "dns_lower_ci_high", "peak_kw_p95", "peak_kw_p95_ci_high",
                    "total_transformer_overload_mean", "cells_with_overload", "meets_all"]].round(4).to_string(index=False))
    print(brk.to_string(index=False))
    print(c2[["level", "algorithm", "ports", "transformer_kw", "dns_lower_mean", "dns_lower_ci_high",
              "sat_all_arrivals_ci_low", "peak_kw_p95", "peak_kw_p95_ci_high", "cells_with_overload",
              "gross_margin_cop_mean", "meets_all"]].round(3).to_string(index=False))
    print(mins.to_string(index=False))
    print(pu.round(2).to_string(index=False))
    print(comp.drop(columns=["voltage_reason"]).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
