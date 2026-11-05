"""
Week 8 advisor review: column labels and number formats for every review_*
workbook (CLAUDE.md rule 7). A column is labelled from its base name plus a
known suffix; a base name with no entry raises in export_formatted_xlsx_sheets
(the hard check is kept, never worked around).
"""
from ev2gym_thesis.xlsx_export import (COP_FORMAT, COUNT_FORMAT, KWH_FORMAT, PCT_FRACTION_FORMAT)

GENERAL = None
KW_FORMAT = "#,##0.00"
RATIO_FORMAT = "0.0000"

# base -> (label, format)
BASE = {
    # identifiers
    "regime": ("Regime (long-dwell = EV2Gym native sessions; DC = 42-min fast-charging sessions)", GENERAL),
    "level": ("Demand Level (multiple of the 1.0x offered energy)", RATIO_FORMAT),
    "algorithm": ("Arm (article name or registry algorithm name)", GENERAL),
    "arm": ("Arm (article name)", GENERAL),
    "n_cases": ("Cases (days) in the Statistic", COUNT_FORMAT),
    "n_clusters": ("Independent Clusters Resampled (scenario seeds)", COUNT_FORMAT),
    "n_bootstrap": ("Bootstrap Resamples", COUNT_FORMAT),
    "n_rows": ("Rows (cases) in the Statistic", COUNT_FORMAT),
    "statistics": ("Interval Method and Resampling Unit", GENERAL),
    "causal": ("Causal (uses only information a real station has at step t)", GENERAL),
    # service (A1, C6)
    "mean_f_served": ("Mean Energy Satisfaction f, Served Drivers Only (0-1 fraction, ratio of totals)", PCT_FRACTION_FORMAT),
    "mean_f_all_lower": ("Mean Energy Satisfaction f incl. Rejected Drivers at f = 0, Rejected = Lower Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "mean_f_all_upper": ("Mean Energy Satisfaction f incl. Rejected Drivers at f = 0, Rejected = Upper Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "mean_f_incl_rejected": ("Mean Energy Satisfaction f incl. Rejected Drivers at f = 0 (0-1 fraction, exact)", PCT_FRACTION_FORMAT),
    "service_level_served": ("Service Level, Share of Served Drivers with f >= 0.9 (0-1 fraction)", PCT_FRACTION_FORMAT),
    "service_level_all_lower": ("Service Level incl. Rejected Drivers, Rejected = Lower Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "service_level_all_upper": ("Service Level incl. Rejected Drivers, Rejected = Upper Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "service_level_incl_rejected": ("Service Level incl. Rejected Drivers, f >= 0.9 (0-1 fraction, exact)", PCT_FRACTION_FORMAT),
    "ev2gym_satisfaction_served": ("EV2Gym Battery-Level Satisfaction s, Served Drivers (0-1 fraction)", PCT_FRACTION_FORMAT),
    "ev2gym_satisfaction_all_lower": ("EV2Gym Battery-Level Satisfaction s incl. Rejected at 0, Lower Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "ev2gym_satisfaction_all_upper": ("EV2Gym Battery-Level Satisfaction s incl. Rejected at 0, Upper Bound (0-1 fraction)", PCT_FRACTION_FORMAT),
    "ev2gym_battery_level_satisfaction_served": ("EV2Gym Battery-Level Satisfaction s, Served Drivers (0-1 fraction)", PCT_FRACTION_FORMAT),
    "advisor_check_s_predicted": ("Advisor Check: 1 - (sum R / sum C)(1 - sum e / sum R) (0-1 fraction)", PCT_FRACTION_FORMAT),
    "advisor_check_s_observed": ("Advisor Check: Observed Mean EV2Gym s, Served Drivers (0-1 fraction)", PCT_FRACTION_FORMAT),
    "dns_lower": ("Demand Not Served, Lower Bound (0-1 fraction of offered energy, ratio of totals)", PCT_FRACTION_FORMAT),
    "dns_upper": ("Demand Not Served, Upper Bound (0-1 fraction of offered energy, ratio of totals)", PCT_FRACTION_FORMAT),
    "dns_exact": ("Demand Not Served, Exact (0-1 fraction of offered energy, ratio of totals)", PCT_FRACTION_FORMAT),
    "rejected_per_day_lower": ("Rejected Drivers per Day, Lower Bound (count)", KWH_FORMAT),
    "rejected_per_day_upper": ("Rejected Drivers per Day, Upper Bound (count)", KWH_FORMAT),
    "energy_kwh_per_day": ("Energy Delivered (kWh per day)", KWH_FORMAT),
    "overload_kwh_per_day": ("Transformer Overload (kWh per day)", KWH_FORMAT),
    "days_with_overload": ("Days with Any Transformer Overload (count of 100)", COUNT_FORMAT),
    "days_with_overload_share": ("Share of Days with Any Transformer Overload (0-1 fraction)", PCT_FRACTION_FORMAT),
    "gross_margin_cop_per_day": ("Gross Energy Margin, Revenue minus Energy Cost (COP per day, Bogota tariff)", COP_FORMAT),
    "ens_rel": ("ENS_rel, 1 - Energy / AFAP Energy (0-1 fraction, ratio of totals)", PCT_FRACTION_FORMAT),
    "peak_kw_p95": ("Station Peak Power, 95th Percentile over Days (kW)", KW_FORMAT),
    "peak_kw_max": ("Station Peak Power, Maximum over Days (kW)", KW_FORMAT),
    "target_satisfaction_met": ("Target Met: Mean f incl. Rejected, CI Lower Bound >= 0.90", GENERAL),
    "target_dns_met": ("Target Met: DNS, CI Upper Bound <= 0.15", GENERAL),
    "target_overload_met": ("Target Met: Zero Days with Overload", GENERAL),
    # reward decomposition (A4)
    "r_tracking": ("Reward Term 1: -(min(setpoint, potential, rating) - power)^2, Summed per Day (kW^2 x steps)", KWH_FORMAT),
    "r_overload": ("Reward Term 2: -100 x Overload kW, Summed per Day (kW x steps x 100)", KWH_FORMAT),
    "r_user": ("Reward Term 3: -1000 x (1 - s) per Departing EV, Summed per Day (dimensionless x 1000)", KWH_FORMAT),
    "reward_total": ("Total SqTrError_TrPenalty_UserIncentives Reward per Day (sum of the three terms)", KWH_FORMAT),
    "sq_dev_min_target": ("Squared Deviation from min(setpoint, potential, rating), Summed per Day (kW^2 x steps)", KWH_FORMAT),
    "tracking_error": ("EV2Gym tracking_error, Squared Deviation from the Setpoint Alone, Summed (kW^2 x steps)", KWH_FORMAT),
}

SUFFIXES = [  # (suffix, label suffix) -- longest first
    ("_diff_vs_RR-TA", " -- Paired Difference, Arm minus RR-TA"),
    ("_diff_ci_low", " -- Paired Difference vs RR-TA, 95% CI Lower Bound"),
    ("_diff_ci_high", " -- Paired Difference vs RR-TA, 95% CI Upper Bound"),
    ("_ci_halfwidth", " -- 95% CI Half-Width"),
    ("_ci_low", " -- 95% CI Lower Bound"),
    ("_ci_high", " -- 95% CI Upper Bound"),
]


def label_for(col: str, extra: dict = None):
    table = {**BASE, **(extra or {})}
    if col in table:
        return table[col]
    for suf, lab in SUFFIXES:
        if col.endswith(suf):
            base = col[: -len(suf)]
            if base in table:
                l, f = table[base]
                return l + lab, f
            if base.startswith("diff_") and base[5:] in table:
                l, f = table[base[5:]]
                return "Change, Later Checkpoint minus 60k: " + l + lab, f
    if col.startswith("diff_") and col[5:] in table:
        l, f = table[col[5:]]
        return "Change, Later Checkpoint minus 60k: " + l, f
    return None


def sheet(name, df, extra=None):
    """(sheet_name, df, labels, formats) for export_formatted_xlsx_sheets.
    Columns with no label stay unmapped, so the exporter's hard check raises."""
    labels, formats = {}, {}
    for c in df.columns:
        lf = label_for(c, extra)
        if lf is None:
            continue
        labels[c] = lf[0]
        if lf[1]:
            formats[lf[0]] = lf[1]
    return (name, df, labels, formats)
