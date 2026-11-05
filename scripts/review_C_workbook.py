"""
Week 8 advisor review: results/review_C_dc_comparison.xlsx (Block C), one
sheet per item, every header a unit-bearing label (CLAUDE.md rule 7):
C6 master tables (1.0x, 1.3x, 1.6x), C4 summary and comparisons, C5 voltage
summary, the A6 information table, and the TD3_safe selection and
validation log when they exist.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from ev2gym_thesis.review_information import COLUMNS as INFO_COLUMNS, INFORMATION_TABLE
from ev2gym_thesis.review_labels import KW_FORMAT, sheet
from ev2gym_thesis.xlsx_export import COP_FORMAT, COUNT_FORMAT, KWH_FORMAT, PCT_FRACTION_FORMAT, export_formatted_xlsx_sheets

OUT = "results/review_C_dc_comparison.xlsx"
PU = "0.00000"
T = None
C4_LABELS = {
    "question": ("Question", T), "arm": ("Arm", T), "ports": ("Ports", COUNT_FORMAT), "transformer": ("Transformer", T),
    "answer": ("Answer", T), "offered_kwh_per_day": ("Offered Energy (kWh per day)", KWH_FORMAT),
    "offered_arrivals_per_day": ("Offered Arrivals per Day (count)", KWH_FORMAT),
    "dns": ("Demand Not Served, Exact (0-1 fraction, ratio of totals)", PCT_FRACTION_FORMAT),
    "mean_f": ("Mean Energy Satisfaction f incl. Rejected (0-1 fraction)", PCT_FRACTION_FORMAT),
    "dns_ci_high": ("DNS 95% CI Upper Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "mean_f_ci_low": ("Mean f 95% CI Lower Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "levels_evaluated": ("Demand Levels Evaluated by the Bisection (count)", COUNT_FORMAT),
    "reference": ("Reference Arm", T), "other": ("Compared Arm", T),
    "afap_300kva_days_with_overload": ("AFAP with 300 kVA: Days with Overload (count of 100)", COUNT_FORMAT),
    "afap_300kva_overload_kwh_per_day": ("AFAP with 300 kVA: Overload (kWh per day)", KWH_FORMAT),
    "energy_kwh_per_day_rrta_minus_other": ("Energy, RR-TA minus Compared Arm (kWh per day)", KWH_FORMAT),
    "energy_kwh_per_day_ci_low": ("Energy Difference 95% CI Lower Bound (kWh per day)", KWH_FORMAT),
    "energy_kwh_per_day_ci_high": ("Energy Difference 95% CI Upper Bound (kWh per day)", KWH_FORMAT),
    "gross_margin_cop_per_day_rrta_minus_other": ("Gross Margin, RR-TA minus Compared Arm (COP per day)", COP_FORMAT),
    "gross_margin_cop_per_day_ci_low": ("Margin Difference 95% CI Lower Bound (COP per day)", COP_FORMAT),
    "gross_margin_cop_per_day_ci_high": ("Margin Difference 95% CI Upper Bound (COP per day)", COP_FORMAT),
    "dns_rrta_minus_other": ("DNS, RR-TA minus Compared Arm (0-1 fraction)", PCT_FRACTION_FORMAT),
    "dns_ci_low": ("DNS Difference 95% CI Lower Bound", PCT_FRACTION_FORMAT),
    "mean_f_rrta_minus_other": ("Mean f incl. Rejected, RR-TA minus Compared Arm (0-1 fraction)", PCT_FRACTION_FORMAT),
    "mean_f_ci_high": ("Mean f Difference 95% CI Upper Bound", PCT_FRACTION_FORMAT),
    "cost_of_limit_share_of_other_margin": ("Cost of Respecting the Transformer, Share of Compared Arm's Margin (0-1 fraction)", PCT_FRACTION_FORMAT),
    "cost_share_ci_low": ("Cost Share 95% CI Lower Bound", PCT_FRACTION_FORMAT),
    "cost_share_ci_high": ("Cost Share 95% CI Upper Bound", PCT_FRACTION_FORMAT),
}
# In the comparisons file dns_ci_high / mean_f_ci_low bound the paired DIFFERENCE, not a level.
C4_COMP_LABELS = {**C4_LABELS,
                  "dns_ci_high": ("DNS Difference 95% CI Upper Bound", PCT_FRACTION_FORMAT),
                  "mean_f_ci_low": ("Mean f Difference 95% CI Lower Bound", PCT_FRACTION_FORMAT)}
C5_LABELS = {"feeder_min_pu": ("Feeder Minimum Voltage, Mean over Cases (p.u.)", PU),
             "station_bus_min_pu": ("Station Bus (115) Minimum Voltage, Mean over Cases (p.u.)", PU),
             "energy_kwh_per_day": ("Energy Delivered (kWh per day)", KWH_FORMAT)}
for base in ("feeder_min_pu", "station_bus_min_pu"):
    for ref in ("idle", "AFAP"):
        k = f"{base}_diff_vs_{ref}"
        lab = C5_LABELS[base][0].split(",")[0] + f", Arm minus {ref} (p.u.)"
        C5_LABELS[k] = (lab, PU)
        C5_LABELS[k + "_ci_low"] = (lab + " -- 95% CI Lower Bound", PU)
        C5_LABELS[k + "_ci_high"] = (lab + " -- 95% CI Upper Bound", PU)
for band, txt in (("ev2gym_095_105", "0.95-1.05 p.u. (EV2Gym)"), ("creg024_090_110", "0.90-1.10 p.u. (CREG 024/2005)")):
    C5_LABELS[f"cases_any_bus_outside_{band}"] = (f"Cases with Any Bus Outside {txt} (count of 50)", COUNT_FORMAT)
    C5_LABELS[f"cases_station_bus_outside_{band}"] = (f"Cases with the Station Bus Outside {txt} (count of 50)", COUNT_FORMAT)


def main():
    sheets = []
    for lv in ("1.0", "1.3", "1.6"):
        p = f"results/review_C_master_{lv}x.csv"
        if os.path.exists(p):
            sheets.append(sheet(f"C6 master {lv}x", pd.read_csv(p)))
    for name, p, lab in [("C4 summary", "results/review_C4_summary.csv", C4_LABELS),
                         ("C4 comparisons", "results/review_C4_comparisons.csv", C4_COMP_LABELS),
                         ("C5 voltage", "results/review_C5_voltage_summary.csv", C5_LABELS)]:
        if os.path.exists(p):
            sheets.append(sheet(name, pd.read_csv(p), lab))
    sheets.append(sheet("A6 information", pd.DataFrame(INFORMATION_TABLE)[INFO_COLUMNS], {
        "arm": ("Arm", T), "regimes": ("Regimes", T), "connected_evs": ("Uses Connected EVs", T),
        "transformer_rating": ("Uses Transformer Rating", T), "requested_energy": ("Uses Requested Energy", T),
        "departure_times": ("Uses Departure Times", T), "future_arrivals": ("Uses Future Arrivals", T),
        "power_setpoint": ("Uses EV2Gym Setpoint", T), "code": ("Code (file and line)", T)}))
    if os.path.exists("results/review_td3_safe_selection.json"):
        sel = json.load(open("results/review_td3_safe_selection.json"))
        rows = [{"train_seed": s, **{k: v for k, v in d.items()}} for s, d in sel["seeds"].items()]
        sheets.append(sheet("C3 TD3_safe selection", pd.DataFrame(rows), {
            "train_seed": ("Training Seed", T), "status": ("Status", T), "converged": ("Converged (2%/5% rule)", T),
            "convergence_step": ("Convergence Declared at Step", COUNT_FORMAT), "final_step": ("Final Checkpoint Step", COUNT_FORMAT),
            "last_step": ("Last Step Trained", COUNT_FORMAT), "stop_reason": ("Stop Reason", T),
            "validation_energy_kwh": ("Validation Energy at the Final Checkpoint (kWh per day)", KWH_FORMAT),
            "checkpoint": ("Checkpoint Path", T)}))
    c3 = {"reference": ("Reference Arm", T), "other": ("Compared Arm", T), "train_seed": ("Training Seed", T),
          "carried_model": ("Carried Model (best validation among the seeds' final checkpoints)", T),
          "final_step": ("Final Checkpoint Step", COUNT_FORMAT),
          "validation_energy_kwh": ("Validation Energy at the Final Checkpoint (kWh per day)", KWH_FORMAT),
          "days_with_overload": ("Days with Any Transformer Overload (count of 100)", COUNT_FORMAT),
          "peak_kw_max": ("Station Peak Power, Maximum over Days (kW)", KW_FORMAT)}
    for m, lab, fmt in [("energy_kwh_per_day", "Energy Delivered (kWh per day)", KWH_FORMAT),
                        ("dns_exact", "Demand Not Served, Exact (0-1 fraction)", PCT_FRACTION_FORMAT),
                        ("mean_f_incl_rejected", "Mean Energy Satisfaction f incl. Rejected (0-1 fraction)",
                         PCT_FRACTION_FORMAT)]:
        c3[f"{m}_td3_minus_other"] = (f"{lab}, TD3_safe minus Compared Arm", fmt)
        c3[f"{m}_diff_ci_low"] = (f"{lab}, Difference 95% CI Lower Bound", fmt)
        c3[f"{m}_diff_ci_high"] = (f"{lab}, Difference 95% CI Upper Bound", fmt)
    for name, p in [("C3 TD3_safe comparisons", "results/review_C3_td3_safe_comparisons.csv"),
                    ("C3 TD3_safe seeds", "results/review_C3_td3_safe_seeds.csv")]:
        if os.path.exists(p):
            sheets.append(sheet(name, pd.read_csv(p), c3))
    # C3 long-budget sensitivity (config_safe doc long_budget_sensitivity; scripts/review_C3_long.py)
    lb = {"algorithm": ("Arm (TD3_safe_long_<last|bestval>_ts<training seed>)", T),
          "days_with_overload": ("Days with Any Transformer Overload (count of 100)", COUNT_FORMAT),
          "peak_kw_max": ("Station Peak Power, Maximum over Days (kW)", KW_FORMAT)}
    for m, lab, fmt in [("energy_kwh_per_day", "Energy Delivered (kWh per day)", KWH_FORMAT),
                        ("dns_exact", "Demand Not Served, Exact (0-1 fraction)", PCT_FRACTION_FORMAT),
                        ("mean_f_incl_rejected", "Mean Energy Satisfaction f incl. Rejected (0-1 fraction)",
                         PCT_FRACTION_FORMAT)]:
        lb[m] = (lab, fmt)
        lb[f"{m}_ci_low"] = (f"{lab}, 95% CI Lower Bound", fmt)
        lb[f"{m}_ci_high"] = (f"{lab}, 95% CI Upper Bound", fmt)
        for ref, txt in [("TD3_safe", "the Carried TD3_safe Model"), ("RR-TA", "RR-TA"), ("PS", "PS")]:
            lb[f"{m}_minus_{ref}"] = (f"{lab}, Arm minus {txt}", fmt)
            lb[f"{m}_minus_{ref}_ci_low"] = (f"{lab}, Arm minus {txt}, 95% CI Lower Bound", fmt)
            lb[f"{m}_minus_{ref}_ci_high"] = (f"{lab}, Arm minus {txt}, 95% CI Upper Bound", fmt)
    if os.path.exists("results/review_C3_long_budget.csv"):
        sheets.append(sheet("C3 long-budget sensitivity", pd.read_csv("results/review_C3_long_budget.csv"), lb))
    export_formatted_xlsx_sheets(OUT, sheets)


if __name__ == "__main__":
    main()
