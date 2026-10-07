"""
Closure brief, Part C analysis: the capacity threshold per arm (C1) and the
gap-closing options at the breaking level (C2).

Inputs (all post-processing; nothing is written to the registry):
  - registry analysis rows: Part C rows (notes "closure_part=C1/C2",
    simulate_grid=False) and the Week 7 Step 2 grid rows for 1.0/1.3/1.6x
    (station metrics identical to non-grid, 0.0 difference, Week 7 S6.1);
  - results/closure_censoring_by_cell.csv (8 ports) and
    results/closure_censoring_port_variants_by_cell.csv (10/12 ports);
  - results/timeseries/<run_id>.npz for the peak station power.

Breaking criteria (closure brief C1), each evaluated on 100 runs per (level,
arm), 50 scenario seeds x 2 day types, with the scenario seed as the
bootstrap cluster (n_clusters = 50):
  - satisfaction: broken when the 95% CI lower bound of the mean
    average_user_satisfaction is below 0.90;
  - demand not served (lower bound, ev2gym_thesis/demand/censoring.py):
    broken when the 95% CI upper bound is above 0.15;
  - peak: broken when the 95% CI upper bound of the 95th-percentile per-seed
    peak station power is above 100 kW (per-seed peak = max over the two
    day types, as in Week 7's transformer_sizing).
Using the CI side that makes compliance hardest to claim is the conservative
reading (labelled assumption). Point estimates are reported alongside.
Means use paired_cluster_bootstrap_ci; the P95 quantile is not a mean, so
its CI resamples the 50 per-seed peaks with replacement (same cluster unit,
10,000 draws, seed 0) -- declared.

Usage: PYTHONPATH=. python scripts/analyze_closure_capacity.py
"""
import numpy as np
import pandas as pd

from ev2gym_thesis.demand.censoring import demand_not_served
from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

STEP2 = {"station_v0_bogota_grid": 1.0, "station_v0_bogota_grid_spawn1.3": 1.3,
         "station_v0_bogota_grid_spawn1.6": 1.6}
ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "TD3_vanilla_extended_ts102"]
SAT_MIN, DNS_MAX, PEAK_MAX_KW = 0.90, 0.15, 100.0
UNIT_MARGIN = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
LEVEL_LABEL = {0.75: "0.733x (spawn 22)"}
N_BOOT = 10_000


def _level_label(lvl):
    return LEVEL_LABEL.get(lvl, f"{lvl:g}x")


def load_rows():
    reg = pd.read_csv("results/master_results.csv", low_memory=False)
    reg = reg[reg.analysis_row.astype(str) == "True"].copy()
    notes = reg.notes.fillna("")
    step2 = reg[reg.config_name.isin(STEP2) & reg.algorithm.isin(ARMS)].copy()
    step2["level"] = step2.config_name.map(STEP2)
    step2["ports"], step2["kw"], step2["part"], step2["cd"] = 8, 100.0, "week7_step2", False
    clo = reg[notes.str.contains("closure_part=")].copy()
    n = clo.notes
    clo["level"] = n.str.extract(r"demand_level=([0-9.]+)")[0].astype(float)
    clo["ports"] = n.str.extract(r"ports=(\d+)")[0].astype(int)
    clo["kw"] = n.str.extract(r"transformer_kw=([0-9.]+)")[0].astype(float)
    clo["part"] = n.str.extract(r"closure_part=(C\dcd|C\d)")[0]
    clo["cd"] = n.str.contains("constant_station_demand=True")
    out = pd.concat([step2, clo], ignore_index=True)
    out["seed"] = out.seed.astype(float).astype(int)
    for c in ["total_energy_charged", "average_user_satisfaction", "total_transformer_overload", "total_ev_served"]:
        out[c] = out[c].astype(float)
    return out


def attach_censoring(rows):
    base = pd.read_csv("results/closure_censoring_by_cell.csv").assign(ports=8, constant_demand=False)
    var = pd.read_csv("results/closure_censoring_port_variants_by_cell.csv")
    var["constant_demand"] = var.constant_demand.astype(str) == "True" if "constant_demand" in var else False
    cens = pd.concat([base, var], ignore_index=True).rename(columns={"constant_demand": "cd"})
    cens["ports"] = cens.ports.astype(int)
    cens["cd"] = cens.cd.astype(bool)
    m = rows.merge(cens, on=["level", "ports", "cd", "seed", "eval_day"], how="left", validate="many_to_one")
    if m.n_spawned.isna().any():
        raise ValueError("censoring missing for some cells")
    # the censoring replay must describe the same EV population as the run
    if not np.allclose(m.n_spawned, m.total_ev_served):
        bad = m[~np.isclose(m.n_spawned, m.total_ev_served)]
        raise AssertionError(f"{len(bad)} runs: censoring n_spawned != total_ev_served")
    for b in ("lower", "upper"):
        m[f"dns_{b}"] = [demand_not_served(e, r, b) for e, (_, r) in zip(m.total_energy_charged, m.iterrows())]
    m["gross_margin_cop"] = m.total_energy_charged * UNIT_MARGIN
    return m


def attach_peaks(rows):
    peaks = []
    for rid in rows.run_id:
        d = np.load(f"results/timeseries/{rid}.npz")
        peaks.append(float(np.max(d["station_power"])))
    return rows.assign(peak_station_kw=peaks)


def mean_ci(x, clusters):
    r = paired_cluster_bootstrap_ci(np.zeros(len(x)), np.asarray(x, float), np.asarray(clusters),
                                    n_bootstrap=N_BOOT, seed=0)
    return r["point_estimate"], r["ci_low"], r["ci_high"], r["n_clusters"]


def p95_ci(per_seed_peaks):
    v = np.asarray(per_seed_peaks, float)
    rng = np.random.default_rng(0)
    boots = np.quantile(v[rng.integers(0, len(v), size=(N_BOOT, len(v)))], 0.95, axis=1)
    return float(np.quantile(v, 0.95)), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)), len(v)


def summarize(g):
    row = {"n_runs": len(g)}
    for col in ["average_user_satisfaction", "dns_lower", "dns_upper", "total_transformer_overload",
                "total_energy_charged", "gross_margin_cop", "total_ev_served"]:
        pt, lo, hi, nc = mean_ci(g[col], g.seed)
        row.update({f"{col}_mean": pt, f"{col}_ci_low": lo, f"{col}_ci_high": hi})
    per_seed = g.groupby("seed").agg(peak=("peak_station_kw", "max"), ov=("total_transformer_overload", "mean"))
    pt, lo, hi, _ = p95_ci(per_seed.peak)
    row.update({"peak_kw_p95": pt, "peak_kw_p95_ci_low": lo, "peak_kw_p95_ci_high": hi,
                "seeds_with_overload": int((per_seed.ov > 0).sum()), "n_clusters": nc})
    row["broken_satisfaction"] = row["average_user_satisfaction_ci_low"] < SAT_MIN
    row["broken_dns"] = row["dns_lower_ci_high"] > DNS_MAX
    row["broken_peak"] = row["peak_kw_p95_ci_high"] > PEAK_MAX_KW
    return row


# doc:begin c1_thresholds
def c1_tables(m):
    c1 = m[(m.ports == 8) & (m.kw == 100.0) & m.algorithm.isin(ARMS)]
    rows = []
    for (lvl, arm), g in c1.groupby(["level", "algorithm"]):
        rows.append({"level": lvl, "level_label": _level_label(lvl), "algorithm": arm, **summarize(g)})
    by_level = pd.DataFrame(rows).sort_values(["algorithm", "level"])
    by_level.to_csv("results/closure_c1_capacity_by_level.csv", index=False)
    crit = [("satisfaction", "average_user_satisfaction", "ci_low"), ("dns", "dns_lower", "ci_high"),
            ("peak", "peak_kw_p95", "ci_high")]
    brk = []
    for arm, g in by_level.groupby("algorithm"):
        g = g.sort_values("level")
        hit = g[g.broken_satisfaction | g.broken_dns | g.broken_peak]
        if not len(hit):
            brk.append({"algorithm": arm, "breaking_level": None, "levels_tested": ",".join(f"{x:g}" for x in g.level)})
            continue
        r = hit.iloc[0]
        broken = [name for name, _, _ in crit if r[f"broken_{name}"]]
        first = broken[0]
        col = dict((n, c) for n, c, _ in crit)[first]
        lo_key = "peak_kw_p95_ci_low" if first == "peak" else f"{col}_ci_low"
        hi_key = "peak_kw_p95_ci_high" if first == "peak" else f"{col}_ci_high"
        val_key = "peak_kw_p95" if first == "peak" else f"{col}_mean"
        lower_tested = g[g.level < r.level]
        brk.append({"algorithm": arm, "breaking_level": r.level, "breaking_level_label": r.level_label,
                    "highest_level_not_broken": lower_tested.level.max() if len(lower_tested) else None,
                    "first_criterion_broken": first, "all_criteria_broken_at_level": ";".join(broken),
                    "value": r[val_key], "ci_low": r[lo_key], "ci_high": r[hi_key], "n_clusters": r.n_clusters,
                    "levels_tested": ",".join(f"{x:g}" for x in g.level)})
    brk = pd.DataFrame(brk)
    brk.to_csv("results/closure_c1_breaking_levels.csv", index=False)
    return by_level, brk
# doc:end c1_thresholds


# doc:begin c2_options
def c2_table(m):
    """At each C2 level, every (ports, rating[, constant demand]) option
    against the reference 8 ports / 100 kW at the same level, paired by
    (seed, day). as_run variants keep spawn_multiplier, so in EV2Gym's
    per-port arrival model they also face more arrivals; constant-demand
    (cd) variants scale it by 8/ports, so only the port count changes."""
    rows = []
    c2 = m[m.part.isin(["C2", "C2cd"])]
    for lvl in sorted(c2.level.unique()):
        ref_all = m[(m.level == lvl) & (m.ports == 8) & (m.kw == 100.0)]
        if lvl == 1.0:  # the 1.0x reference = Step 2 base rows (same population, 0.0 difference)
            ref_all = ref_all[ref_all.part == "week7_step2"]
        opts = c2[c2.level == lvl][["ports", "kw", "cd"]].drop_duplicates().values.tolist()
        for arm in ["ChargeAsFastAsPossible", "RoundRobin"]:
            ref = ref_all[ref_all.algorithm == arm]
            for ports, kw, cd in [(8, 100.0, False)] + sorted(opts):
                g = ref if (ports, kw) == (8, 100.0) else c2[(c2.level == lvl) & (c2.ports == ports) & (c2.kw == kw)
                                                             & (c2.cd == cd) & (c2.algorithm == arm)]
                row = {"level": lvl, "level_label": _level_label(lvl), "algorithm": arm, "ports": ports,
                       "station_demand": "constant (spawn x 8/ports)" if cd else "as run (per-port arrivals)",
                       "transformer_kw": kw, "transformer_kva_at_pf_0894": round(kw / 0.894, 1)
                       if kw != 100.0 else 111.9, **summarize(g)}
                p = ref.merge(g, on=["seed", "eval_day"], suffixes=("_ref", ""))
                assert len(p) == 100, (lvl, arm, ports, kw, len(p))
                for col in ["dns_lower", "average_user_satisfaction", "total_transformer_overload", "gross_margin_cop"]:
                    r = paired_cluster_bootstrap_ci(p[col + "_ref"], p[col], p.seed, n_bootstrap=N_BOOT, seed=0)
                    row.update({f"delta_{col}": r["point_estimate"], f"delta_{col}_ci_low": r["ci_low"],
                                f"delta_{col}_ci_high": r["ci_high"]})
                rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv("results/closure_c2_options.csv", index=False)
    return out
# doc:end c2_options


def main():
    m = attach_peaks(attach_censoring(load_rows()))
    by_level, brk = c1_tables(m)
    c2 = c2_table(m)
    pd.set_option("display.width", 250)
    print(by_level[["level_label", "algorithm", "average_user_satisfaction_mean", "average_user_satisfaction_ci_low",
                    "dns_lower_mean", "dns_lower_ci_high", "peak_kw_p95", "peak_kw_p95_ci_high",
                    "total_transformer_overload_mean", "seeds_with_overload", "broken_satisfaction", "broken_dns",
                    "broken_peak", "n_clusters"]].round(4).to_string(index=False))
    print(brk.to_string(index=False))
    print(c2[["level_label", "algorithm", "ports", "station_demand", "transformer_kw", "average_user_satisfaction_mean", "dns_lower_mean",
              "dns_lower_ci_low", "dns_lower_ci_high", "total_transformer_overload_mean", "seeds_with_overload",
              "gross_margin_cop_mean", "delta_dns_lower", "delta_gross_margin_cop", "peak_kw_p95"]
             ].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
