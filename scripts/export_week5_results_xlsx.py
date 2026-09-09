"""
Week 5: human-readable Excel exports for every results/week5_*.csv file
(economics_cop.csv has its own script, export_economics_cop_xlsx.py).
Uses the shared ev2gym_thesis.xlsx_export utility -- see that module's
docstring for the formatting convention.

A note on satisfaction columns, resolved once here rather than guessed at
per file: this project's own registry mixes two scales --
average_user_satisfaction is a 0-1 FRACTION, min_energy_user_satisfaction
is already on a 0-100 SCALE (both inherited from EV2Gym's own stats dict,
not something this project introduced). Every column derived from one or
the other is labeled and formatted accordingly below, never assumed.

Usage: PYTHONPATH=. python scripts/export_week5_results_xlsx.py
"""
from ev2gym_thesis.xlsx_export import (
    export_formatted_xlsx, COP_FORMAT, KWH_FORMAT, COP_PER_KWH_FORMAT,
    COUNT_FORMAT, PCT_FRACTION_FORMAT, PCT_ALREADY_SCALED_FORMAT,
    SECONDS_FORMAT, DIMENSIONLESS_4DP_FORMAT,
)

RESULTS_DIR = "results"


def export_ens_compliance():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_ens_compliance.csv",
        f"{RESULTS_DIR}/week5_ens_compliance.xlsx",
        column_labels={
            "algorithm": "Algorithm",
            "ENS_rel_point_pct": "Energy Not Served vs. AFAP, Point Estimate (%)",
            "ENS_rel_ci_low_pct": "Energy Not Served vs. AFAP, 95% CI Lower Bound (%)",
            "ENS_rel_ci_high_pct": "Energy Not Served vs. AFAP, 95% CI Upper Bound (%)",
            "ENS_rel_pass_15pct_ci_upper_bound": "Passes <15% Target (CI Upper Bound Test)",
            "ENS_abs_diagnostic_pct": "Energy Not Served vs. Requested Energy, Diagnostic Only (%)",
            "avg_satisfaction_pct": "Average User Satisfaction (fraction, 0 to 1)",
            "min_satisfaction_pct": "Minimum Energy User Satisfaction (already 0-100 scale, %)",
            "satisfaction_gt_90pct": "Average Satisfaction Exceeds 90% Target",
            "n_seeds": "Number of Scenario Seeds Behind This Row",
        },
        number_formats={
            "Energy Not Served vs. AFAP, Point Estimate (%)": PCT_ALREADY_SCALED_FORMAT,
            "Energy Not Served vs. AFAP, 95% CI Lower Bound (%)": PCT_ALREADY_SCALED_FORMAT,
            "Energy Not Served vs. AFAP, 95% CI Upper Bound (%)": PCT_ALREADY_SCALED_FORMAT,
            "Energy Not Served vs. Requested Energy, Diagnostic Only (%)": PCT_ALREADY_SCALED_FORMAT,
            "Average User Satisfaction (fraction, 0 to 1)": PCT_FRACTION_FORMAT,
            "Minimum Energy User Satisfaction (already 0-100 scale, %)": PCT_ALREADY_SCALED_FORMAT,
            "Number of Scenario Seeds Behind This Row": COUNT_FORMAT,
        },
        sheet_name="ens_compliance",
    )


def export_horizon_sensitivity():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_horizon_sensitivity.csv",
        f"{RESULTS_DIR}/week5_horizon_sensitivity.xlsx",
        column_labels={
            "horizon": "MPC Control Horizon (steps, 15 min/step)",
            "seed": "Scenario Seed",
            "eval_day": "Evaluation Day",
            "tracking_error": "Tracking Error (dimensionless, sum of squared kW deviations)",
            "total_energy_charged": "Energy Charged (kWh, one simulated day)",
            "total_transformer_overload": "Transformer Overload (kWh, one simulated day)",
            "average_user_satisfaction": "Average User Satisfaction (fraction, 0 to 1)",
            "runtime_s": "Episode Runtime (seconds)",
        },
        number_formats={
            "MPC Control Horizon (steps, 15 min/step)": COUNT_FORMAT,
            "Tracking Error (dimensionless, sum of squared kW deviations)": COP_FORMAT,
            "Energy Charged (kWh, one simulated day)": KWH_FORMAT,
            "Transformer Overload (kWh, one simulated day)": KWH_FORMAT,
            "Average User Satisfaction (fraction, 0 to 1)": PCT_FRACTION_FORMAT,
            "Episode Runtime (seconds)": SECONDS_FORMAT,
        },
        sheet_name="horizon_sensitivity",
    )
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_horizon_sensitivity_summary.csv",
        f"{RESULTS_DIR}/week5_horizon_sensitivity_summary.xlsx",
        column_labels={
            "horizon": "MPC Control Horizon (steps, 15 min/step)",
            "tracking_error_mean": "Mean Tracking Error (dimensionless, across the 10-seed subset)",
            "tracking_error_std": "Std. Dev. of Tracking Error (across the 10-seed subset)",
            "energy_charged_mean": "Mean Energy Charged (kWh, one simulated day)",
            "overload_mean": "Mean Transformer Overload (kWh, one simulated day)",
            "runtime_mean_s": "Mean Episode Runtime (seconds)",
        },
        number_formats={
            "MPC Control Horizon (steps, 15 min/step)": COUNT_FORMAT,
            "Mean Tracking Error (dimensionless, across the 10-seed subset)": COP_FORMAT,
            "Std. Dev. of Tracking Error (across the 10-seed subset)": COP_FORMAT,
            "Mean Energy Charged (kWh, one simulated day)": KWH_FORMAT,
            "Mean Transformer Overload (kWh, one simulated day)": KWH_FORMAT,
            "Mean Episode Runtime (seconds)": SECONDS_FORMAT,
        },
        sheet_name="horizon_sensitivity_summary",
    )


def export_margin_vs_overload():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_margin_vs_overload.csv",
        f"{RESULTS_DIR}/week5_margin_vs_overload.xlsx",
        column_labels={
            "algorithm": "Algorithm",
            "mean_margin": "Mean Gross Margin (COP per simulated day, across the 50-seed grid)",
            "mean_overload": "Mean Transformer Overload (kWh per simulated day)",
            "mean_satisfaction": "Mean Average User Satisfaction (fraction, 0 to 1)",
            "margin_foregone_vs_afap_cop": "Margin Foregone vs. AFAP (COP per simulated day)",
            "overload_avoided_vs_afap_kwh": "Transformer Overload Avoided vs. AFAP (kWh per simulated day)",
            "cop_per_kwh_overload_avoided": "Cost per kWh of Overload Avoided (COP/kWh)",
        },
        number_formats={
            "Mean Gross Margin (COP per simulated day, across the 50-seed grid)": COP_FORMAT,
            "Mean Transformer Overload (kWh per simulated day)": KWH_FORMAT,
            "Mean Average User Satisfaction (fraction, 0 to 1)": PCT_FRACTION_FORMAT,
            "Margin Foregone vs. AFAP (COP per simulated day)": COP_FORMAT,
            "Transformer Overload Avoided vs. AFAP (kWh per simulated day)": KWH_FORMAT,
            "Cost per kWh of Overload Avoided (COP/kWh)": COP_PER_KWH_FORMAT,
        },
        sheet_name="margin_vs_overload",
    )


def export_master_comparison():
    labels = {"algorithm": "Algorithm", "n_rows": "Number of Rows", "n_seeds": "Number of Scenario Seeds"}
    formats = {"Number of Rows": COUNT_FORMAT, "Number of Scenario Seeds": COUNT_FORMAT}

    # (csv_prefix, detailed metric name, unit label, number format)
    metric_specs = [
        ("total_ev_served", "EVs Served", "count, mean per day", COUNT_FORMAT),
        ("total_transformer_overload", "Transformer Overload", "kWh per simulated day", KWH_FORMAT),
        ("average_user_satisfaction", "Average User Satisfaction", "fraction, 0 to 1", PCT_FRACTION_FORMAT),
        ("min_energy_user_satisfaction", "Minimum Energy User Satisfaction", "already 0-100 scale, %", PCT_ALREADY_SCALED_FORMAT),
        ("tracking_error", "Tracking Error", "dimensionless, sum of squared kW deviations", COP_FORMAT),
        ("energy_tracking_error", "Energy Tracking Error", "dimensionless", DIMENSIONLESS_4DP_FORMAT),
        ("battery_degradation", "Battery Degradation", "dimensionless capacity-loss fraction", DIMENSIONLESS_4DP_FORMAT),
    ]
    for prefix, name, unit, fmt in metric_specs:
        for suffix, stat in [("_mean", "Mean"), ("_ci_low", "95% CI Lower Bound"), ("_ci_high", "95% CI Upper Bound")]:
            label = f"{name} -- {stat} ({unit})"
            labels[f"{prefix}{suffix}"] = label
            formats[label] = fmt

    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_master_comparison.csv",
        f"{RESULTS_DIR}/week5_master_comparison.xlsx",
        column_labels=labels, number_formats=formats, sheet_name="master_comparison",
    )


def export_old_vs_new_ci():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_old_vs_new_ci.csv",
        f"{RESULTS_DIR}/week5_old_vs_new_ci.xlsx",
        column_labels={
            "version": "Bootstrap Version (old naive vs. new cluster-corrected)",
            "point_estimate": "Point Estimate, Round Robin minus AFAP (kWh, absolute difference)",
            "ci_low": "95% CI Lower Bound (kWh)",
            "ci_high": "95% CI Upper Bound (kWh)",
            "n_pairs": "Number of Paired Rows",
            "n_clusters": "Number of Independent Clusters (Scenario Seeds)",
            "ci_width": "95% CI Width (kWh, ci_high minus ci_low)",
        },
        number_formats={
            "Point Estimate, Round Robin minus AFAP (kWh, absolute difference)": KWH_FORMAT,
            "95% CI Lower Bound (kWh)": KWH_FORMAT,
            "95% CI Upper Bound (kWh)": KWH_FORMAT,
            "Number of Paired Rows": COUNT_FORMAT,
            "Number of Independent Clusters (Scenario Seeds)": COUNT_FORMAT,
            "95% CI Width (kWh, ci_high minus ci_low)": KWH_FORMAT,
        },
        sheet_name="old_vs_new_ci",
    )


def export_optimality_gap():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_optimality_gap.csv",
        f"{RESULTS_DIR}/week5_optimality_gap.xlsx",
        column_labels={
            "algorithm": "Algorithm",
            "metric": "Metric Being Compared to the Oracle",
            "oracle_variant": "Oracle Variant Used as the Bound",
            "mean_abs_gap": "Mean Absolute Gap to Oracle (unit matches Metric column: dimensionless for tracking_error, percentage points for satisfaction metrics)",
            "pct_of_oracle_value": "Gap as a Percentage of the Oracle's Own Value (%)",
            "n_cells": "Number of Matched Evaluation Cells",
        },
        number_formats={
            "Mean Absolute Gap to Oracle (unit matches Metric column: dimensionless for tracking_error, percentage points for satisfaction metrics)": DIMENSIONLESS_4DP_FORMAT,
            "Gap as a Percentage of the Oracle's Own Value (%)": PCT_ALREADY_SCALED_FORMAT,
            "Number of Matched Evaluation Cells": COUNT_FORMAT,
        },
        sheet_name="optimality_gap",
    )


def export_oracle_tiebreak_noise_floor():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_oracle_tiebreak_noise_floor.csv",
        f"{RESULTS_DIR}/week5_oracle_tiebreak_noise_floor.xlsx",
        column_labels={
            "metric": "Metric",
            "mean_abs_diff": "Mean Absolute Difference Between Oracle Variants (tie-break noise floor)",
            "median_abs_diff": "Median Absolute Difference Between Oracle Variants",
            "max_abs_diff": "Max Absolute Difference Between Oracle Variants",
            "std_abs_diff": "Std. Dev. of the Absolute Difference",
            "n_cells": "Number of Matched Evaluation Cells",
        },
        number_formats={
            "Mean Absolute Difference Between Oracle Variants (tie-break noise floor)": DIMENSIONLESS_4DP_FORMAT,
            "Median Absolute Difference Between Oracle Variants": DIMENSIONLESS_4DP_FORMAT,
            "Max Absolute Difference Between Oracle Variants": DIMENSIONLESS_4DP_FORMAT,
            "Std. Dev. of the Absolute Difference": DIMENSIONLESS_4DP_FORMAT,
            "Number of Matched Evaluation Cells": COUNT_FORMAT,
        },
        sheet_name="oracle_tiebreak_noise_floor",
    )


def export_requested_energy_by_cell():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_requested_energy_by_cell.csv",
        f"{RESULTS_DIR}/week5_requested_energy_by_cell.xlsx",
        column_labels={
            "seed": "Scenario Seed",
            "eval_day": "Evaluation Day",
            "R": "Requested Energy, EVs Departing Within Horizon (kWh, the ENS_abs denominator)",
            "n_departing": "Number of EVs Departing Within the Simulation Horizon",
            "n_still_connected": "Number of EVs Still Connected at Horizon End (excluded from R)",
            "still_connected_energy": "Requested Energy of Still-Connected EVs, Diagnostic Only (kWh)",
        },
        number_formats={
            "Requested Energy, EVs Departing Within Horizon (kWh, the ENS_abs denominator)": KWH_FORMAT,
            "Number of EVs Departing Within the Simulation Horizon": COUNT_FORMAT,
            "Number of EVs Still Connected at Horizon End (excluded from R)": COUNT_FORMAT,
            "Requested Energy of Still-Connected EVs, Diagnostic Only (kWh)": KWH_FORMAT,
        },
        sheet_name="requested_energy_by_cell",
    )


def export_seed_overload_distribution():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_seed_overload_distribution.csv",
        f"{RESULTS_DIR}/week5_seed_overload_distribution.xlsx",
        column_labels={
            "seed": "Scenario Seed",
            "mean_overload_kwh": "AFAP Mean Transformer Overload Across Both Day Types (kWh)",
            "max_overload_kwh": "AFAP Max Transformer Overload Across Both Day Types (kWh)",
        },
        number_formats={
            "AFAP Mean Transformer Overload Across Both Day Types (kWh)": KWH_FORMAT,
            "AFAP Max Transformer Overload Across Both Day Types (kWh)": KWH_FORMAT,
        },
        sheet_name="seed_overload_distribution",
    )


def export_td3_budget_curve():
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_td3_budget_curve.csv",
        f"{RESULTS_DIR}/week5_td3_budget_curve.xlsx",
        column_labels={
            "checkpoint_steps": "TD3 Training Checkpoint (timesteps)",
            "seed": "Scenario Seed",
            "eval_day": "Evaluation Day",
            "tracking_error": "Tracking Error (dimensionless, sum of squared kW deviations)",
            "total_transformer_overload": "Transformer Overload (kWh, one simulated day)",
            "average_user_satisfaction": "Average User Satisfaction (fraction, 0 to 1)",
            "total_energy_charged": "Energy Charged (kWh, one simulated day)",
        },
        number_formats={
            "TD3 Training Checkpoint (timesteps)": COUNT_FORMAT,
            "Tracking Error (dimensionless, sum of squared kW deviations)": COP_FORMAT,
            "Transformer Overload (kWh, one simulated day)": KWH_FORMAT,
            "Average User Satisfaction (fraction, 0 to 1)": PCT_FRACTION_FORMAT,
            "Energy Charged (kWh, one simulated day)": KWH_FORMAT,
        },
        sheet_name="td3_budget_curve",
    )
    export_formatted_xlsx(
        f"{RESULTS_DIR}/week5_td3_budget_curve_summary.csv",
        f"{RESULTS_DIR}/week5_td3_budget_curve_summary.xlsx",
        column_labels={
            "checkpoint_steps": "TD3 Training Checkpoint (timesteps)",
            "tracking_error_mean": "Mean Tracking Error (across the 10-seed subset)",
            "overload_mean": "Mean Transformer Overload (kWh)",
            "satisfaction_mean": "Mean Average User Satisfaction (fraction, 0 to 1)",
            "energy_charged_mean": "Mean Energy Charged (kWh)",
        },
        number_formats={
            "TD3 Training Checkpoint (timesteps)": COUNT_FORMAT,
            "Mean Tracking Error (across the 10-seed subset)": COP_FORMAT,
            "Mean Transformer Overload (kWh)": KWH_FORMAT,
            "Mean Average User Satisfaction (fraction, 0 to 1)": PCT_FRACTION_FORMAT,
            "Mean Energy Charged (kWh)": KWH_FORMAT,
        },
        sheet_name="td3_budget_curve_summary",
    )


if __name__ == "__main__":
    export_ens_compliance()
    export_horizon_sensitivity()
    export_margin_vs_overload()
    export_master_comparison()
    export_old_vs_new_ci()
    export_optimality_gap()
    export_oracle_tiebreak_noise_floor()
    export_requested_energy_by_cell()
    export_seed_overload_distribution()
    export_td3_budget_curve()
    print("\nAll Week 5 result CSVs exported to formatted .xlsx.")
