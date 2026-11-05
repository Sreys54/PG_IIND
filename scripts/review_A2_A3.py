"""
Week 8 advisor review, A2 (one aggregation rule) and A3 (Table IV root
cause), from the stored registries and censoring files (no simulation).

A2.
  1. Inventory: every percentage in chapters 03-08, the three latest
     handbacks and the figure captions (scripts/make_figures.py), with its
     line, the metric family it belongs to (keyword classification) and how
     that family is computed by the code that produced it today.
  2. Recomputation of every energy percentage by both rules, with cluster
     bootstrap CIs (scenario seed, n_clusters = 50, 10,000 resamples,
     percentile): ENS_rel = 1 - E_arm/E_AFAP, DNS (lower and upper bound),
     tracking-error reduction vs AFAP, overload share of energy. The adopted
     rule is the ratio of totals (pooled kWh), recomputed inside each
     resample; "changes" lists the numbers whose rounded value moves.
A3. Offered demand of every Final-capacity-brief DC variant at 1.6x (8-16
    ports, "constant station demand" scaling spawn x 8/P), and the
    margin/DNS consistency of each Table IV row: margin = E (p - c) and
    DNS = 1 - E / E_offered.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH, RETAIL_TARIFF_COP_PER_KWH
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci

D = "experiments/phase4_review/A"
UNIT = RETAIL_TARIFF_COP_PER_KWH - ENERGY_PURCHASE_COST_COP_PER_KWH
DOCS = sorted(glob.glob("thesis_docs/chapters/0[3-8]*.md")) + [
    "thesis_docs/Final_Parameter_Method_and_Implementation_Justification.md",
    "thesis_docs/Dwell_Capacity_Parameter_Method_and_Implementation_Justification.md",
    "thesis_docs/Closure_Parameter_Method_and_Implementation_Justification.md",
    "scripts/make_figures.py"]

# doc:begin A2_rules
FAMILIES = [  # (family, regex on the line, rule today, code)
    ("DNS", r"\bDNS\b|demand not served", "mean of per-case ratios",
     "scripts/analyze_dwell_capacity.py summarize (mean_ci over per-run dns_lower); "
     "ev2gym_thesis/demand/censoring.py demand_not_served per run"),
    ("ENS_rel", r"ENS_?rel|ENS\$?_", "mean of per-seed ratios (two days pooled within a seed)",
     "scripts/analyze_week5_results.py ens_and_compliance (ens_rel_per_seed, then np.mean)"),
    ("satisfaction", r"satisf", "mean of per-case means of per-EV values (EV2Gym battery level)",
     "registry average_user_satisfaction (ev2gym/utilities/utils.py get_statistics), averaged over cases"),
    ("overload", r"overload", "mean of per-case kWh; shares: count of cases",
     "registry total_transformer_overload"),
    ("tracking", r"tracking", "mean of per-case values; reductions: ratio of means or of per-case values (mixed)",
     "registry tracking_error; scripts/analyze_week5_results.py"),
    ("cost/margin share", r"margin|COP|cost of", "ratio of means (Delta E / E_AFAP, Proposition 7.1)",
     "scripts/closure_*.py, scripts/analyze_dwell_capacity.py"),
    ("optimality gap", r"gap|oracle", "ratio of means", "scripts/analyze_week5_results.py optimality gap"),
    ("infeasibility/occupancy/other", r".", "not an energy percentage", "-"),
]
# doc:end A2_rules


def inventory():
    rows = []
    pct = re.compile(r"(\d[\d,]*\.?\d*)\s*%")
    for f in DOCS:
        for i, line in enumerate(open(f, encoding="utf-8"), start=1):
            if f.endswith(".py") and "caption" not in line.lower() and "title" not in line.lower():
                continue
            for m in pct.finditer(line):
                fam = next(fa for fa in FAMILIES if re.search(fa[1], line, re.I))
                rows.append({"file": f, "line": i, "value_pct": m.group(1), "metric_family": fam[0],
                             "rule_today": fam[2], "code": fam[3], "context": line.strip()[:220]})
    return pd.DataFrame(rows)


def _pivot(df, col):
    return df.pivot_table(index=["seed", "eval_day"], columns="algorithm", values=col)


# doc:begin A2_recompute
def recompute():
    out = []
    m = pd.read_csv("results/master_results.csv", low_memory=False)
    long = m[(m.analysis_row == True) & (m.config_name == "station_v0_bogota")]
    cens_l = pd.read_csv("results/closure_censoring_by_cell.csv")
    cens_l = cens_l[np.isclose(cens_l.level, 1.0)].set_index(["seed", "eval_day"])
    d = pd.read_csv("results/dwell_registry.csv", low_memory=False)
    cens_d = pd.read_csv("results/dwell_censoring_by_cell.csv")
    grids = [("long-dwell", 1.0, long, cens_l)]
    for lv, sp in ((1.0, 30), (1.3, 39), (1.6, 48)):
        g = d[d.config_name == f"station_v0_bogota_dc42_sp{sp}"].drop_duplicates(["algorithm", "seed", "eval_day"])
        c = cens_d[(cens_d.config_name == f"station_v0_bogota_dc42_sp{sp}")].drop_duplicates(
            ["seed", "eval_day"]).set_index(["seed", "eval_day"])
        grids.append(("DC 42 min", lv, g, c))
    for regime, lv, g, cens in grids:
        E = _pivot(g, "total_energy_charged")
        TE = _pivot(g, "tracking_error")
        OV = _pivot(g, "total_transformer_overload")
        idx = E.index
        cl = idx.get_level_values("seed").values
        cz = cens.loc[idx]
        for arm in E.columns:
            if E[arm].isna().any():
                continue
            e, a = E[arm].values, E["ChargeAsFastAsPossible"].values
            rows = [("ENS_rel", a - e, a, (a - e) / a)]
            for b in ("lower", "upper"):
                off = cz[f"energy_rejected_{b}_kwh"].values + cz["requested_served_kwh"].values
                rows.append((f"DNS_{b}", off - e, off, (off - e) / off))
            if arm != "ChargeAsFastAsPossible":
                t, ta = TE[arm].values, TE["ChargeAsFastAsPossible"].values
                rows.append(("tracking_error_reduction_vs_AFAP", ta - t, ta, (ta - t) / ta))
            ov = OV[arm].values * 0.25  # EV2Gym's kW x steps -> kWh (15-min steps; see review_A_analyze.py)
            rows.append(("overload_share_of_energy", ov, e, ov / e))
            for name, num, den, per_case in rows:
                r = rci(num, den, cl)
                mr = rci(per_case, np.ones(len(per_case)), cl)
                out.append({"regime": regime, "level": lv, "algorithm": arm, "metric": name,
                            "mean_of_ratios": mr["point_estimate"], "mean_of_ratios_ci_low": mr["ci_low"],
                            "mean_of_ratios_ci_high": mr["ci_high"], "ratio_of_totals": r["point_estimate"],
                            "ratio_of_totals_ci_low": r["ci_low"], "ratio_of_totals_ci_high": r["ci_high"],
                            "difference_points": 100 * (r["point_estimate"] - mr["point_estimate"]),
                            "changes_at_one_decimal": round(100 * r["point_estimate"], 1) != round(
                                100 * mr["point_estimate"], 1),
                            "n_clusters": r["n_clusters"], "n_bootstrap": r["n_bootstrap"]})
    return pd.DataFrame(out)
# doc:end A2_recompute


# doc:begin A3
def table_iv():
    """Offered demand per DC variant at 1.6x, and Table IV consistency."""
    cens = pd.read_csv("results/dwell_censoring_by_cell.csv")
    c = cens[(cens.dwell_mean_min == 42) & np.isclose(cens.level, 1.6)]
    off = c.assign(offered_lower=c.energy_rejected_lower_kwh + c.requested_served_kwh,
                   offered_upper=c.energy_rejected_upper_kwh + c.requested_served_kwh)
    demand = off.groupby(["ports", "transformer_kw", "constant_demand", "config_name"]).agg(
        n_cases=("seed", "size"), offered_kwh_lower=("offered_lower", "mean"),
        offered_kwh_upper=("offered_upper", "mean"), requested_served_kwh=("requested_served_kwh", "mean"),
        arrivals_served=("n_spawned", "mean")).reset_index()
    opts = pd.read_csv("results/dwell_c2_growth_options.csv")
    opts = opts[np.isclose(opts.level, 1.6) | np.isclose(opts.level, 1.3)]
    rows = []
    for _, r in opts.iterrows():
        e, mg, dns = r.total_energy_charged_mean, r.gross_margin_cop_mean, r.dns_lower_mean
        rows.append({"level": r.level, "algorithm": r.algorithm, "ports": r.ports, "transformer_kw": r.transformer_kw,
                     "station_demand": r.station_demand, "energy_kwh": e, "margin_cop": mg, "dns_lower": dns,
                     "margin_over_unit_margin_kwh": mg / UNIT, "margin_check_rel_error": abs(mg - e * UNIT) / (e * UNIT),
                     "offered_implied_by_dns_kwh": e / (1 - dns) if dns < 1 else np.nan,
                     "dns_if_offered_911_kwh": 1 - e / 910.708, "advisor_reading_dns_gap_points":
                     100 * (dns - (1 - e / 910.708))})
    return demand, pd.DataFrame(rows)
# doc:end A3


def main():
    os.makedirs(D, exist_ok=True)
    inv = inventory()
    inv.to_csv(os.path.join(D, "A2_percentage_inventory.csv"), index=False)
    rec = recompute()
    rec.to_csv(os.path.join(D, "A2_recomputed.csv"), index=False)
    demand, t4 = table_iv()
    demand.to_csv(os.path.join(D, "A3_offered_demand_1_6x.csv"), index=False)
    t4.to_csv(os.path.join(D, "A3_table_iv_consistency.csv"), index=False)
    print(len(inv), "percentages;", inv.metric_family.value_counts().to_dict())
    print(rec[rec.changes_at_one_decimal][["regime", "level", "algorithm", "metric", "mean_of_ratios",
                                            "ratio_of_totals"]].round(4).to_string())
    print(demand.round(1).to_string())


if __name__ == "__main__":
    main()
