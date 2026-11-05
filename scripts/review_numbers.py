"""
Week 8 advisor review: write thesis_docs/review_2026-11-01_numbers.md, every
number of the review with the file it comes from, generated from the result
files (never typed by hand). Sections whose inputs do not exist are listed
as not yet available.

Usage: PYTHONPATH=. python scripts/review_numbers.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

OUT = "thesis_docs/review_2026-11-01_numbers.md"
A = "experiments/phase4_review/A"
STATS = ("Statistics everywhere: cluster bootstrap over the scenario seed, n_clusters = 50 (100 cases = "
         "50 seeds x {weekday 2022-01-17, weekend 2022-03-05}), 10,000 resamples, percentile 95% intervals, "
         "per comparison; energy percentages and per-driver means are ratios of totals recomputed in every "
         "resample. Overload is in kWh (EV2Gym's total_transformer_overload x 0.25 h).")


def pct(x, d=1):
    return f"{100 * x:.{d}f}%"


def ci(r, k, d=1, scale=100, unit="%"):
    return f"{scale * r[k]:,.{d}f}{unit} [{scale * r[k + '_ci_low']:,.{d}f}, {scale * r[k + '_ci_high']:,.{d}f}]"


def md(df, cols, fmt=None):
    fmt = fmt or {}
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(fmt[c](r) if c in fmt else str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def section_calibration():
    c = pd.read_csv("experiments/phase4_review/calibration.csv")
    return ["## B4. Demand levels by offered energy", "Source: `experiments/phase4_review/calibration.csv`.", "",
            md(c, ["level", "arrivals_per_day", "mean_offered_arrivals_per_day", "mean_offered_kwh_per_day",
                   "offered_kwh_per_port_per_day_8_ports", "rel_error"],
               {"mean_offered_kwh_per_day": lambda r: f"{r.mean_offered_kwh_per_day:,.1f}",
                "offered_kwh_per_port_per_day_8_ports": lambda r: f"{r.offered_kwh_per_port_per_day_8_ports:.1f}",
                "rel_error": lambda r: pct(r.rel_error, 2)})]


def section_gate1():
    p = "experiments/phase4_review/gate1/gate1_capacity.csv"
    if not os.path.exists(p):
        return []
    g = pd.read_csv(p)
    s = g[(g.level == 1.0) & (g.ports == 8)].sort_values(["algorithm", "variant"])
    return ["## Gate 1. Old spawner vs station-level arrivals (1.0x, 8 ports)", f"Source: `{p}`.", "",
            md(s, ["variant", "algorithm", "arrivals_rejected_per_day_lower", "port_occupancy", "dns_lower",
                   "mean_f_all_lower", "overload_kwh_per_day", "gross_margin_cop_per_day"],
               {"dns_lower": lambda r: ci(r, "dns_lower"), "mean_f_all_lower": lambda r: ci(r, "mean_f_all_lower"),
                "port_occupancy": lambda r: pct(r.port_occupancy),
                "overload_kwh_per_day": lambda r: f"{r.overload_kwh_per_day:.2f}",
                "gross_margin_cop_per_day": lambda r: f"{r.gross_margin_cop_per_day:,.0f}",
                "arrivals_rejected_per_day_lower": lambda r: f"{r.arrivals_rejected_per_day_lower:.2f}"}), "",
            "RR-TA capacity, old vs new criteria:", "",
            md(g[g.algorithm == "RR-TA"], ["variant", "level", "ports", "dns_lower_ci_high", "mean_f_all_lower_ci_low",
                                            "old_meets_all", "new_meets_all"],
               {"dns_lower_ci_high": lambda r: pct(r.dns_lower_ci_high),
                "mean_f_all_lower_ci_low": lambda r: pct(r.mean_f_all_lower_ci_low)})]


def section_a():
    out = []
    a = pd.read_csv(f"{A}/A1_A7_service_and_dns.csv")
    out += ["## A1 / A7. Energy satisfaction and DNS bounds", f"Source: `{A}/A1_A7_service_and_dns.csv`.", "",
            md(a, ["regime", "level", "algorithm", "mean_f_served", "mean_f_all_lower", "service_level_all_lower",
                   "ev2gym_satisfaction_served", "dns_lower", "dns_upper", "overload_kwh_per_day",
                   "target_satisfaction_met", "target_dns_met", "target_overload_met"],
               {k: (lambda kk: (lambda r: ci(r, kk)))(k) for k in
                ["mean_f_served", "mean_f_all_lower", "service_level_all_lower", "ev2gym_satisfaction_served",
                 "dns_lower", "dns_upper"]} | {"overload_kwh_per_day": lambda r: f"{r.overload_kwh_per_day:.3f}"})]
    r = pd.read_csv(f"{A}/A2_recomputed.csv")
    r = r[r.changes_at_one_decimal]
    out += ["", "## A2. Numbers that change under the ratio-of-totals rule", f"Source: `{A}/A2_recomputed.csv`.", "",
            md(r, ["regime", "level", "algorithm", "metric", "mean_of_ratios", "ratio_of_totals"],
               {"mean_of_ratios": lambda x: pct(x.mean_of_ratios, 2), "ratio_of_totals": lambda x: pct(x.ratio_of_totals, 2)})]
    d = pd.read_csv(f"{A}/A4_reward_terms_850k_minus_60k.csv")
    out += ["", "## A4. Reward terms, later checkpoint minus 60k (per day)", f"Source: `{A}/A4_reward_terms_850k_minus_60k.csv`.", "",
            md(d, ["train_seed", "to_label", "diff_r_tracking", "diff_r_overload", "diff_r_user", "diff_tracking_error",
                   "diff_reward_total"],
               {k: (lambda kk: (lambda x: f"{x[kk]:,.0f} [{x[kk + '_ci_low']:,.0f}, {x[kk + '_ci_high']:,.0f}]"))(k)
                for k in ["diff_r_tracking", "diff_r_overload", "diff_r_user", "diff_tracking_error", "diff_reward_total"]})]
    v = pd.read_csv(f"{A}/A4_posthoc_reward_vs_td3.csv")
    out += ["", f"Post-hoc reward, arm minus TD3 final (per day; source `{A}/A4_posthoc_reward_vs_td3.csv`):", "",
            md(v, ["baseline", "reward_baseline_minus_td3", "baseline_beats_td3_on_its_own_reward"],
               {"reward_baseline_minus_td3": lambda x: f"{x.reward_baseline_minus_td3:,.0f} [{x.reward_baseline_minus_td3_ci_low:,.0f}, {x.reward_baseline_minus_td3_ci_high:,.0f}]"})]
    t = pd.read_csv(f"{A}/A4_td3_vs_random.csv")
    out += ["", f"TD3 final vs Random, Table II metrics (source `{A}/A4_td3_vs_random.csv`):", "",
            md(t, ["metric", "random", "td3_final", "diff_td3_minus_random", "ci_low", "ci_high", "significant"],
               {k: (lambda kk: (lambda x: f"{x[kk]:,.4g}"))(k) for k in ["random", "td3_final", "diff_td3_minus_random", "ci_low", "ci_high"]})]
    s = pd.read_csv(f"{A}/A8_week1_transformer_sweep.csv")
    out += ["", "## A8. Week 1 transformer sweep (re-run; no stored rows existed)", f"Source: `{A}/A8_week1_transformer_sweep.csv`.", "",
            md(s, ["set", "transformer_kw", "n", "overload_kwh_mean", "overload_ev2gym_kw_steps_mean", "days_with_overload"],
               {"overload_kwh_mean": lambda x: f"{x.overload_kwh_mean:.3f}",
                "overload_ev2gym_kw_steps_mean": lambda x: f"{x.overload_ev2gym_kw_steps_mean:.3f}"})]
    pk = pd.read_csv(f"{A}/A8_dc_peaks.csv")
    out += ["", f"DC peaks, old spawner (source `{A}/A8_dc_peaks.csv`):", "",
            md(pk, ["level", "algorithm", "peak_kw_p95_over_cases", "peak_kw_max_over_cases", "days_above_rating"],
               {"peak_kw_p95_over_cases": lambda x: f"{x.peak_kw_p95_over_cases:.1f}",
                "peak_kw_max_over_cases": lambda x: f"{x.peak_kw_max_over_cases:.1f}"})]
    return out


def section_c():
    out = []
    for lv in ("1.0", "1.3", "1.6"):
        p = f"results/review_C_master_{lv}x.csv"
        if not os.path.exists(p):
            continue
        t = pd.read_csv(p)
        out += ["", f"## C6. DC master table, {lv}x (station-level arrivals, 8 ports, 100 kW)", f"Source: `{p}`.", "",
                md(t, ["algorithm", "causal", "energy_kwh_per_day", "ens_rel", "dns_exact", "mean_f_incl_rejected",
                       "service_level_incl_rejected", "overload_kwh_per_day", "days_with_overload", "peak_kw_p95",
                       "peak_kw_max", "gross_margin_cop_per_day", "gross_margin_cop_per_day_diff_vs_RR-TA"],
                   {"energy_kwh_per_day": lambda x: f"{x.energy_kwh_per_day:,.1f} ± {x.energy_kwh_per_day_ci_halfwidth:.1f}",
                    "ens_rel": lambda x: ci(x, "ens_rel"), "dns_exact": lambda x: ci(x, "dns_exact"),
                    "mean_f_incl_rejected": lambda x: ci(x, "mean_f_incl_rejected"),
                    "service_level_incl_rejected": lambda x: ci(x, "service_level_incl_rejected"),
                    "overload_kwh_per_day": lambda x: f"{x.overload_kwh_per_day:.2f}",
                    "peak_kw_p95": lambda x: f"{x.peak_kw_p95:.1f}", "peak_kw_max": lambda x: f"{x.peak_kw_max:.1f}",
                    "gross_margin_cop_per_day": lambda x: f"{x.gross_margin_cop_per_day:,.0f}",
                    "gross_margin_cop_per_day_diff_vs_RR-TA": lambda x: f"{x['gross_margin_cop_per_day_diff_vs_RR-TA']:,.0f} [{x['gross_margin_cop_per_day_diff_ci_low']:,.0f}, {x['gross_margin_cop_per_day_diff_ci_high']:,.0f}]"})]
    for name, p in [("C4 summary", "results/review_C4_summary.csv"), ("C5 voltage", "results/review_C5_voltage_summary.csv"),
                    ("D sensitivities", "results/review_D_summary.csv")]:
        if os.path.exists(p):
            t = pd.read_csv(p)
            out += ["", f"## {name}", f"Source: `{p}`.", "", md(t, list(t.columns),
                    {c: (lambda cc: (lambda x: f"{x[cc]:,.4g}" if isinstance(x[cc], float) else str(x[cc])))(c) for c in t.columns})]
    if os.path.exists("results/review_td3_safe_selection.json"):
        out += ["", "## C3. TD3_safe selection", "```json", open("results/review_td3_safe_selection.json").read(), "```"]
    p = "results/review_C3_td3_safe_comparisons.csv"
    if os.path.exists(p):
        t = pd.read_csv(p)
        f = {m: (lambda mm, sc, d: (lambda x: f"{sc * x[mm + '_td3_minus_other']:,.{d}f} [{sc * x[mm + '_diff_ci_low']:,.{d}f}, "
                                                 f"{sc * x[mm + '_diff_ci_high']:,.{d}f}]"))(m, sc, d)
             for m, sc, d in [("energy_kwh_per_day", 1, 1), ("dns_exact", 100, 2), ("mean_f_incl_rejected", 100, 2)]}
        out += ["", "## C3. TD3_safe (carried model) minus each causal arm, test grid",
                f"Source: `{p}`. Energy in kWh/day; DNS and mean f in percentage points.", "",
                md(t, ["level", "other", "energy_kwh_per_day", "dns_exact", "mean_f_incl_rejected", "n_clusters"],
                   {"energy_kwh_per_day": f["energy_kwh_per_day"], "dns_exact": f["dns_exact"],
                    "mean_f_incl_rejected": f["mean_f_incl_rejected"]})]
    p = "results/review_C3_td3_safe_seeds.csv"
    if os.path.exists(p):
        t = pd.read_csv(p)
        out += ["", "## C3. TD3_safe, every training seed, test grid", f"Source: `{p}`.", "",
                md(t, ["level", "train_seed", "carried_model", "final_step", "validation_energy_kwh", "energy_kwh_per_day",
                       "dns_exact", "mean_f_incl_rejected", "days_with_overload", "peak_kw_max"],
                   {"validation_energy_kwh": lambda x: f"{x.validation_energy_kwh:.1f}",
                    "energy_kwh_per_day": lambda x: f"{x.energy_kwh_per_day:,.1f} [{x.energy_kwh_per_day_ci_low:,.1f}, {x.energy_kwh_per_day_ci_high:,.1f}]",
                    "dns_exact": lambda x: ci(x, "dns_exact"), "mean_f_incl_rejected": lambda x: ci(x, "mean_f_incl_rejected"),
                    "peak_kw_max": lambda x: f"{x.peak_kw_max:.1f}"})]
    p = "results/review_C3_long_budget.csv"
    if os.path.exists(p):
        t = pd.read_csv(p)
        d = lambda m, ref, sc, k: (lambda x: f"{sc * x[f'{m}_minus_{ref}']:+,.{k}f} [{sc * x[f'{m}_minus_{ref}_ci_low']:,.{k}f}, "
                                              f"{sc * x[f'{m}_minus_{ref}_ci_high']:,.{k}f}]")
        out += ["", "## C3 long-budget sensitivity (2,000,000 steps; carried model unchanged)",
                f"Source: `{p}`; selection `results/review_td3_safe_long_selection.json`. Energy in kWh/day.", "",
                md(t, ["level", "algorithm", "energy_kwh_per_day", "energy_kwh_per_day_minus_TD3_safe",
                       "energy_kwh_per_day_minus_RR-TA", "energy_kwh_per_day_minus_PS", "dns_exact",
                       "mean_f_incl_rejected", "days_with_overload"],
                   {"energy_kwh_per_day": lambda x: f"{x.energy_kwh_per_day:,.1f}",
                    "energy_kwh_per_day_minus_TD3_safe": d("energy_kwh_per_day", "TD3_safe", 1, 1),
                    "energy_kwh_per_day_minus_RR-TA": d("energy_kwh_per_day", "RR-TA", 1, 1),
                    "energy_kwh_per_day_minus_PS": d("energy_kwh_per_day", "PS", 1, 1),
                    "dns_exact": lambda x: ci(x, "dns_exact"),
                    "mean_f_incl_rejected": lambda x: ci(x, "mean_f_incl_rejected")})]
    return out


def main():
    lines = ["# Week 8 advisor review (2026-11-01): every number, with its source",
             "", "Generated by `scripts/review_numbers.py` from the result files; do not edit by hand.", "", STATS, ""]
    lines += section_calibration() + [""] + section_gate1() + [""] + section_a() + section_c()
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote", OUT, len(lines), "lines")


if __name__ == "__main__":
    main()
