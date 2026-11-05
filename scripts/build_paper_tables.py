"""
Week 8 advisor review, A3: build every article table directly from the
registries and the Week 8 result files, as .xlsx (CLAUDE.md rule 7 labels)
and as Markdown, so no number is typed by hand again.

Tables (statistics stated under each: cluster bootstrap over the scenario
seed, n_clusters = 50, 10,000 resamples, percentile 95%, per comparison;
ratios of totals for energy percentages and per-driver means):
  I    parameters of the reference station and economics;
  II   long-dwell regime (EV2Gym native sessions), every arm: energy, mean f
       (served / incl. rejected, lower bound), EV2Gym battery-level
       satisfaction, ENS_rel, DNS (lower / upper bound), overload, tracking
       error, gross energy margin (needs experiments/phase4_review/A/A_cases.csv);
  III  DC regime, station-level arrivals, 1.0x: the C6 master table;
  IV   infrastructure under DC (C4);
  V    cost of keeping the transformer limit by city (C1 AFAP vs RR-TA energy
       difference x (retail price - each city's flat Nivel 2 cost));
  A6   information table.
A table whose inputs do not exist yet is skipped and listed as such.

Every row carries the energy, offered energy, margin, p and c it was built
from, so ev2gym_thesis/tests/test_paper_tables.py can check margin =
E (p - c) within 0.5% and DNS = 1 - E / E_offered within 0.5 points.

Usage: PYTHONPATH=. python scripts/build_paper_tables.py
Output: results/review_paper_tables.xlsx, thesis_docs/review_paper_tables.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.prices.cities import CITIES
from ev2gym_thesis.prices.colombia import ENERGY_PURCHASE_COST_COP_PER_KWH as C_BOG, RETAIL_TARIFF_COP_PER_KWH as P
from ev2gym_thesis.review_information import COLUMNS as INFO_COLUMNS, INFORMATION_TABLE
from ev2gym_thesis.review_labels import sheet
from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
from ev2gym_thesis.xlsx_export import export_formatted_xlsx_sheets

OUT_XLSX = "results/review_paper_tables.xlsx"
OUT_MD = "thesis_docs/review_paper_tables.md"
STATS = ("cluster bootstrap over scenario seed, n_clusters = 50, 10,000 resamples, percentile 95%, per comparison; "
         "energy percentages and per-driver means are ratios of totals per resample")
LONG_ARMS = {"ChargeAsFastAsPossible": "AFAP", "RoundRobin": "RR", "RoundRobin_TransformerCapped": "RR-TA",
             "MPC_TrackingG2V": "MPC-T", "MPC_EnergyMaxG2V": "MPC-E", "Optimal_Oracle_Tracking": "Oracle-T",
             "Optimal_Oracle_Balanced": "Oracle-B", "TD3_vanilla_extended_ts102": "TD3 final (850k)",
             "RandomPolicy": "Random"}


def table_i():
    rows = [("Ports", "8 (one 50 kW port per charger, 72 A, 400 V, 3 phases: 49.88 kW)"),
            ("Transformer", "100 kW (112.5 kVA class at PF 0.894)"),
            ("Battery", "70 kWh, desired capacity 100%"),
            ("Step / horizon", "15 min / 96 steps (05:00 to 05:00)"),
            ("Retail price p", f"{P:,.2f} COP/kWh (Enel Colombia, Aug 2025)"),
            ("Energy purchase cost c", f"{C_BOG:,.4f} COP/kWh (Enel Nivel 2 with contribution, Aug 2026)"),
            ("Unit margin p - c", f"{P - C_BOG:,.4f} COP/kWh"),
            ("Long-dwell sessions", "EV2Gym native (ElaadNL 'public'), floor 200 min"),
            ("DC sessions", "lognormal, mean 42 min, CV 0.5, connected exactly the sampled duration (Week 8)"),
            ("DC arrivals", "station-level Poisson, 38.31 / 49.32 / 60.70 arrivals/day = 627 / 814 / 1,002 kWh/day")]
    return pd.DataFrame(rows, columns=["parameter", "value"])


def table_ii():
    c = pd.read_csv("experiments/phase4_review/A/A_cases.csv")
    c = c[c.regime == "long"]
    cens = pd.read_csv("results/closure_censoring_by_cell.csv")
    cens = cens[np.isclose(cens.level, 1.0)].set_index(["seed", "eval_day"])
    afap = c[c.algorithm == "ChargeAsFastAsPossible"].set_index(["seed", "eval_day"]).sort_index()
    rows = []
    for arm, name in LONG_ARMS.items():
        g = c[c.algorithm == arm].set_index(["seed", "eval_day"]).sort_index()
        if len(g) != 100:
            continue
        z = cens.loc[g.index]
        cl = g.index.get_level_values("seed").values
        one = np.ones(len(g))
        o = {"arm": name, "n_clusters": 50}

        def put(k, num, den):
            r = rci(np.asarray(num, float), np.asarray(den, float), cl)
            o[k] = r["point_estimate"]
            o[f"{k}_ci_halfwidth"] = (r["ci_high"] - r["ci_low"]) / 2
        put("energy_kwh_per_day", g.total_energy_charged, one)
        put("mean_f_served", g.sum_f, g.n_served_rec)
        put("mean_f_all_lower", g.sum_f, g.n_served_rec + z.rejected_lower)
        put("ev2gym_satisfaction_served", g.sum_s_ev2gym, g.n_served_rec)
        put("ens_rel", afap.total_energy_charged - g.total_energy_charged, afap.total_energy_charged)
        off_lo = z.energy_rejected_lower_kwh + z.requested_served_kwh
        off_hi = z.energy_rejected_upper_kwh + z.requested_served_kwh
        put("dns_lower", off_lo - g.total_energy_charged, off_lo)
        put("dns_upper", off_hi - g.total_energy_charged, off_hi)
        put("overload_kwh_per_day", g.total_transformer_overload * 0.25, one)  # EV2Gym kW x steps -> kWh
        put("tracking_error", g.tracking_error, one)
        put("gross_margin_cop_per_day", g.total_energy_charged * (P - C_BOG), one)
        o.update({"offered_kwh_lower_mean": float(off_lo.mean()), "retail_price": P, "purchase_cost": C_BOG,
                  "statistics": STATS})
        rows.append(o)
    return pd.DataFrame(rows)


def table_iii():
    p = "results/review_C_master_1.0x.csv"
    return pd.read_csv(p) if os.path.exists(p) else None


def table_iv():
    """Infrastructure under DC (C4): the summary (threshold, ports and
    transformer at 1.6x, AFAP's minimum transformer) and the RR-TA
    comparisons against FIX12.5 and against AFAP on a 300 kVA unit."""
    ps, pc = "results/review_C4_summary.csv", "results/review_C4_comparisons.csv"
    if not (os.path.exists(ps) and os.path.exists(pc)):
        return None, None
    s, c = pd.read_csv(ps), pd.read_csv(pc)
    s["statistics"] = STATS + ("; 'meets' = DNS CI upper bound <= 15% and mean-f CI lower bound >= 90%; a "
                               "transformer suffices when the maximum station peak over 100 days <= its rating")
    c["statistics"] = STATS
    return s, c


def table_v():
    p = "experiments/phase4_review/C/c1_cases.csv"
    if not os.path.exists(p):
        return None
    c = pd.read_csv(p)
    c = c[c.config_name.str.contains("_1.00x_p8_tr100$")]
    piv = c.pivot_table(index=["seed", "eval_day"], columns="algorithm", values="energy_delivered_kwh")
    cl = piv.index.get_level_values("seed").values
    d = piv["AFAP"] - piv["RR-TA"]
    rows = []
    for city, t in CITIES.items():
        cost = t["flat_con"]
        r = rci((d * (P - cost)).values, np.ones(len(d)), cl)
        share = rci(d.values, piv["AFAP"].values, cl)
        rows.append({"city": city, "purchase_cost": cost, "retail_price": P,
                     "cost_of_limit_cop_per_day": r["point_estimate"], "cost_ci_low": r["ci_low"],
                     "cost_ci_high": r["ci_high"], "share_of_afap_margin": share["point_estimate"],
                     "n_clusters": r["n_clusters"], "statistics": STATS})
    return pd.DataFrame(rows)


def _fmt(v):
    if isinstance(v, (float, np.floating)):
        a = abs(v)
        return f"{v:,.0f}" if a >= 1000 else (f"{v:,.2f}" if a >= 1 else f"{v:.4f}")
    return str(v)


def md_table(df, title, note):
    cols = [c for c in df.columns if c != "statistics"]
    df = df[cols]
    out = [f"## {title}", "", note, "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(_fmt(v) for v in r.values) + " |")
    return "\n".join(out) + "\n"


def main():
    T = {"Table I parameters": (table_i(), {"parameter": ("Parameter", None), "value": ("Value", None)})}
    if os.path.exists("experiments/phase4_review/A/A_cases.csv"):
        T["Table II long-dwell"] = (table_ii(), {"offered_kwh_lower_mean": ("Offered Energy, Lower Bound, Mean (kWh per day)", "#,##0.00"),
                                                  "retail_price": ("Retail Price p (COP per kWh)", "#,##0.0000"),
                                                  "purchase_cost": ("Energy Purchase Cost c (COP per kWh)", "#,##0.0000")})
    t3 = table_iii()
    if t3 is not None:
        T["Table III DC 1.0x"] = (t3, {})
    t4s, t4c = table_iv()
    if t4s is not None:
        from scripts.review_C_workbook import C4_COMP_LABELS, C4_LABELS
        T["Table IV infrastructure"] = (t4s, C4_LABELS)
        T["Table IV comparisons"] = (t4c, C4_COMP_LABELS)
    t5 = table_v()
    if t5 is not None:
        T["Table V cities"] = (t5, {"city": ("City (categoria especial)", None),
                                    "purchase_cost": ("Flat Nivel 2 Energy Cost c (COP per kWh)", "#,##0.0000"),
                                    "retail_price": ("Retail Price p (COP per kWh)", "#,##0.0000"),
                                    "cost_of_limit_cop_per_day": ("Cost of Keeping the 100 kW Limit, AFAP minus RR-TA Margin (COP per day)", "#,##0.00"),
                                    "cost_ci_low": ("95% CI Lower Bound (COP per day)", "#,##0.00"),
                                    "cost_ci_high": ("95% CI Upper Bound (COP per day)", "#,##0.00"),
                                    "share_of_afap_margin": ("Share of AFAP Margin (0-1 fraction)", "0.00%")})
    T["A6 information"] = (pd.DataFrame(INFORMATION_TABLE)[INFO_COLUMNS], {
        "arm": ("Arm", None), "regimes": ("Regimes", None), "connected_evs": ("Connected EVs", None),
        "transformer_rating": ("Transformer Rating", None), "requested_energy": ("Requested Energy", None),
        "departure_times": ("Departure Times", None), "future_arrivals": ("Future Arrivals", None),
        "power_setpoint": ("EV2Gym Setpoint", None), "code": ("Code", None)})
    export_formatted_xlsx_sheets(OUT_XLSX, [sheet(k, df, extra) for k, (df, extra) in T.items()])
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# Article tables (generated by scripts/build_paper_tables.py; do not edit by hand)\n\n")
        for k, (df, _) in T.items():
            note = df["statistics"].iloc[0] if "statistics" in df.columns and len(df) else STATS
            if k.startswith(("A6", "Table I ")):
                note = "none (descriptive table, not an estimate)"
            f.write(md_table(df, k, f"Statistics: {note}.") + "\n")
    print("tables:", list(T))


if __name__ == "__main__":
    main()
