"""
Week 8 advisor review, C4 analysis: the infrastructure answers under the
station-level arrival generator (DC, 42-min sessions).

Outputs:
  results/review_C4_summary.csv       one row per question (threshold, ports at
                                      1.6x, AFAP transformer, RR ports/transformer)
  results/review_C4_comparisons.csv   RR-TA vs FIX12.5 and vs AFAP with the 300 kVA
                                      unit, per level: energy, DNS, mean f, margin,
                                      paired differences with CIs; cost of keeping
                                      the transformer limit (COP/day and share of
                                      margin) against AFAP and against FIX12.5
Criteria (labelled, Week 8 brief C4): a configuration "meets" when the exact
DNS 95% upper bound <= 15% and the mean energy satisfaction f (rejected
drivers at f = 0) 95% lower bound >= 90%; a transformer is "sufficient" for
an arm when the arm's maximum station peak over the 100 days does not exceed
its rating (P95 reported beside it; the advisor's note that a P95 rule allows
about five days in a hundred above the rating). ET-013 standard sizes at the
project's power factor 0.894: 112.5, 150, 225, 300, 400 kVA = 100, 134.2,
201.2, 268.3, 357.8 kW.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ev2gym_thesis.stats_utils import cluster_bootstrap_ratio as rci
from scripts.review_C6_tables import level_of

ET013 = [(112.5, 100.0), (150, 134.2), (225, 201.2), (300, 268.3), (400, 357.8)]
C1 = "experiments/phase4_review/C/c1_cases.csv"
C4 = "experiments/phase4_review/C4/C4_cases.csv"


def judge(g):
    cl = g.seed.values
    d = rci(g.energy_offered_kwh - g.energy_delivered_kwh, g.energy_offered_kwh, cl)
    f = rci(g.sum_f, g.n_served + g.n_rejected, cl)
    return {"dns": d["point_estimate"], "dns_ci_high": d["ci_high"], "mean_f": f["point_estimate"],
            "mean_f_ci_low": f["ci_low"], "meets": bool(d["ci_high"] <= 0.15 and f["ci_low"] >= 0.90),
            "peak_kw_max": float(g.peak_station_kw.max()), "peak_kw_p95": float(np.quantile(g.peak_station_kw, 0.95)),
            "offered_kwh_per_day": float(g.energy_offered_kwh.mean()),
            "offered_arrivals_per_day": float(g.arrivals_offered.mean()), "n_clusters": d["n_clusters"]}


def smallest_unit(peak_kw):
    for kva, kw in ET013:
        if peak_kw <= kw + 1e-6:
            return f"{kva:g} kVA ({kw:g} kW)"
    return "above 400 kVA"


def main():
    c1 = pd.read_csv(C1)
    c1["level"] = c1.config_name.map(level_of)
    c4 = pd.read_csv(C4) if os.path.exists(C4) else pd.DataFrame()
    rows = []
    for f in sorted(glob.glob("experiments/phase4_review/C4/threshold_*.json")):
        d = json.load(open(f))
        best = d["threshold_arrivals_per_day"]
        lvl = [x for x in d["log"] if best is not None and abs(x["arrivals_per_day"] - best) < 1e-9]
        q = "capacity threshold (largest arrivals/day meeting both targets)"
        if "_d3" in f:
            q += f", D3 22 kWh per session (energy x {d['energy_scale']:.4f}); bisection floor 0.5x = 19.15 arrivals/day"
        rows.append({"question": q, "arm": d["arm"],
                     "ports": d["ports"], "transformer": "112.5 kVA (100 kW)",
                     "answer": "none in range" if best is None else f"{best:.2f} arrivals/day",
                     "offered_kwh_per_day": lvl[0]["offered_kwh"] if lvl else np.nan,
                     "offered_arrivals_per_day": lvl[0]["offered_arrivals"] if lvl else np.nan,
                     "dns": lvl[0]["dns"] if lvl else np.nan, "mean_f": lvl[0]["mean_f_all"] if lvl else np.nan,
                     "levels_evaluated": len(d["log"])})
    g16 = c1[np.isclose(c1.level, 1.6)]
    for arm in ("RR-TA", "PS", "RR"):
        cand = [(8, g16[g16.algorithm == arm])]
        if len(c4):
            for p in (10, 12, 14, 16):
                x = c4[(c4.algorithm == arm) & (c4.ports == p) & np.isclose(c4.transformer_kw, 100.0)
                       & c4.config_name.str.contains("grid_|_1.60x|a60")]
                if len(x) >= 100:
                    cand.append((p, x))
        for p, x in cand:
            j = judge(x)
            rows.append({"question": "ports at 1.6x with the 112.5 kVA unit", "arm": arm, "ports": p,
                         "transformer": "112.5 kVA (100 kW)" if arm != "RR" else f"needs {smallest_unit(j['peak_kw_max'])} "
                         f"(peak max {j['peak_kw_max']:.1f} kW, P95 {j['peak_kw_p95']:.1f} kW)",
                         "answer": "meets" if j["meets"] else "does not meet", "offered_kwh_per_day": j["offered_kwh_per_day"],
                         "offered_arrivals_per_day": j["offered_arrivals_per_day"], "dns": j["dns"], "mean_f": j["mean_f"],
                         "dns_ci_high": j["dns_ci_high"], "mean_f_ci_low": j["mean_f_ci_low"]})
    if len(c4):
        for arm in ("RR-TA", "PS"):
            for kva, kw in ET013[1:4]:
                x = c4[(c4.algorithm == arm) & (c4.ports == 8) & np.isclose(c4.transformer_kw, kw)
                       & c4.config_name.str.contains("grid_")]
                if len(x) >= 100:
                    j = judge(x)
                    rows.append({"question": "transformer at 1.6x with 8 ports", "arm": arm, "ports": 8,
                                 "transformer": f"{kva:g} kVA ({kw:g} kW)",
                                 "answer": "meets" if j["meets"] else "does not meet",
                                 "offered_kwh_per_day": j["offered_kwh_per_day"], "dns": j["dns"], "mean_f": j["mean_f"],
                                 "dns_ci_high": j["dns_ci_high"], "mean_f_ci_low": j["mean_f_ci_low"]})
    for lv in sorted(c1.level.unique()):
        a = c1[np.isclose(c1.level, lv) & (c1.algorithm == "AFAP")]
        j = judge(a)
        rows.append({"question": f"AFAP minimum transformer at 8 ports, {lv:.1f}x", "arm": "AFAP", "ports": 8,
                     "transformer": f"max peak {j['peak_kw_max']:.1f} kW -> {smallest_unit(j['peak_kw_max'])}; "
                                    f"P95 {j['peak_kw_p95']:.1f} kW -> {smallest_unit(j['peak_kw_p95'])}",
                     "answer": "meets service targets" if j["meets"] else "does not meet service targets",
                     "offered_kwh_per_day": j["offered_kwh_per_day"], "dns": j["dns"], "mean_f": j["mean_f"]})
    pd.DataFrame(rows).to_csv("results/review_C4_summary.csv", index=False)

    comp = []
    for lv in sorted(c1.level.unique()):
        g = c1[np.isclose(c1.level, lv)]
        piv = {m: g.pivot_table(index=["seed", "eval_day"], columns="algorithm", values=m)
               for m in ["energy_delivered_kwh", "energy_offered_kwh", "sum_f", "n_served", "n_rejected", "gross_margin_cop"]}
        afap300 = c4[(c4.algorithm == "AFAP") & np.isclose(c4.transformer_kw, 268.3) & c4.config_name.str.contains(
            f"{lv}x")] if len(c4) else pd.DataFrame()
        cl = piv["energy_delivered_kwh"].index.get_level_values("seed").values
        one = np.ones(len(cl))
        for other in ("FIX12.5", "AFAP"):
            o = {"level": lv, "reference": "RR-TA", "other": other if other != "AFAP" else "AFAP with 300 kVA (268.3 kW)"}
            if other == "AFAP" and len(afap300):
                o["afap_300kva_days_with_overload"] = int(afap300.overload_day.sum())
                o["afap_300kva_overload_kwh_per_day"] = float(afap300.overload_kwh.mean())
            for m, num, den in [("energy_kwh_per_day", "energy_delivered_kwh", None),
                                ("gross_margin_cop_per_day", "gross_margin_cop", None)]:
                r = rci(piv[num][other].values, one, cl, piv[num]["RR-TA"].values, one)
                o.update({f"{m}_rrta_minus_other": r["point_estimate"], f"{m}_ci_low": r["ci_low"], f"{m}_ci_high": r["ci_high"]})
            off = piv["energy_offered_kwh"]["RR-TA"].values
            r = rci(off - piv["energy_delivered_kwh"][other].values, off, cl, off - piv["energy_delivered_kwh"]["RR-TA"].values, off)
            o.update({"dns_rrta_minus_other": r["point_estimate"], "dns_ci_low": r["ci_low"], "dns_ci_high": r["ci_high"]})
            nr, no = piv["n_served"]["RR-TA"] + piv["n_rejected"]["RR-TA"], piv["n_served"][other] + piv["n_rejected"][other]
            r = rci(piv["sum_f"][other].values, no.values, cl, piv["sum_f"]["RR-TA"].values, nr.values)
            o.update({"mean_f_rrta_minus_other": r["point_estimate"], "mean_f_ci_low": r["ci_low"], "mean_f_ci_high": r["ci_high"]})
            # cost of respecting the transformer: margin(other) - margin(RR-TA), and as a share of other's margin
            r = rci(piv["gross_margin_cop"][other].values - piv["gross_margin_cop"]["RR-TA"].values,
                    piv["gross_margin_cop"][other].values, cl)
            o.update({"cost_of_limit_share_of_other_margin": r["point_estimate"], "cost_share_ci_low": r["ci_low"],
                      "cost_share_ci_high": r["ci_high"], "n_clusters": r["n_clusters"]})
            comp.append(o)
    pd.DataFrame(comp).to_csv("results/review_C4_comparisons.csv", index=False)
    print(pd.DataFrame(rows).to_string())
    print(pd.DataFrame(comp).round(4).to_string())


if __name__ == "__main__":
    main()
