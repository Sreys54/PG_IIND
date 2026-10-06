"""
Week 6, Part 0: human-readable Excel exports for every results/week6_part0_*.csv
table (plus the Gate 1 timing calibration), one workbook per CSV, same
convention as scripts/export_week5_results_xlsx.py -- all through
ev2gym_thesis.xlsx_export.export_formatted_xlsx (CLAUDE.md rule 7).

Satisfaction scales, as in Week 5: average_user_satisfaction is a 0-1
FRACTION; energy_user_satisfaction and min_energy_user_satisfaction are
already on a 0-100 SCALE. Labelled and formatted accordingly.

Usage: PYTHONPATH=. python scripts/export_week6_part0_results_xlsx.py
"""
from ev2gym_thesis.xlsx_export import (
    export_formatted_xlsx, COP_FORMAT, KWH_FORMAT, COUNT_FORMAT, PCT_FRACTION_FORMAT,
    PCT_ALREADY_SCALED_FORMAT, SECONDS_FORMAT, DIMENSIONLESS_4DP_FORMAT, MIXED_UNIT_4DP_FORMAT,
)

R = "results/week6_part0_{}"
TE = "dimensionless, sum of squared kW deviations"


def _export(name, labels, formats, sheet, src=None):
    export_formatted_xlsx(src or R.format(name) + ".csv", (src or R.format(name) + ".csv").replace(".csv", ".xlsx"),
                          column_labels=labels, number_formats=formats, sheet_name=sheet)


def export_convergence():
    spec = [
        ("train_seed", "Training Seed", COUNT_FORMAT),
        ("convergence_step", "Convergence Declared at Step (validation rule; or 'not converged')", None),
        ("total_steps", "Total Training Steps Reached", COUNT_FORMAT),
        ("wall_clock_h", "Training Wall Clock (hours)", KWH_FORMAT),
        ("n_validations", "Number of Validation Evaluations (every 10,000 steps)", COUNT_FORMAT),
        ("n_training_episodes", "Number of Training Episodes (96 steps each)", COUNT_FORMAT),
        ("median_train_steps_per_s", "Median Training Throughput (steps per second)", KWH_FORMAT),
        ("min_train_steps_per_s", "Minimum Training Throughput (steps per second)", KWH_FORMAT),
        ("val_te_mean_last_w", f"Validation Tracking Error, Mean over Last 5 Evaluations ({TE})", COP_FORMAT),
        ("val_te_std_last_w", f"Validation Tracking Error, Sample Std over Last 5 Evaluations ({TE})", COP_FORMAT),
        ("val_te_at_60k", f"Validation Tracking Error at 60,000 Steps ({TE})", COP_FORMAT),
        ("primary_step", "Selected (Primary) Checkpoint Step", COUNT_FORMAT),
        ("val_te_primary", f"Validation Tracking Error, Primary Checkpoint ({TE})", COP_FORMAT),
        ("val_overload_primary", "Validation Transformer Overload, Primary Checkpoint (kWh per simulated day)", KWH_FORMAT),
        ("val_energy_user_sat_primary", "Validation Energy User Satisfaction, Primary Checkpoint (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
        ("last_step", "Last Checkpoint Step", COUNT_FORMAT),
        ("val_te_last", f"Validation Tracking Error, Last Checkpoint ({TE})", COP_FORMAT),
        ("val_overload_last", "Validation Transformer Overload, Last Checkpoint (kWh per simulated day)", KWH_FORMAT),
        ("val_energy_user_sat_last", "Validation Energy User Satisfaction, Last Checkpoint (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
        ("best_ever_step", "Step of Best Validation Tracking Error Anywhere in the Run", COUNT_FORMAT),
        ("val_te_best_ever", f"Best Validation Tracking Error Anywhere in the Run ({TE})", COP_FORMAT),
        ("train_reward_30k_60k_new", "Training Reward, 100-Episode Rolling Mean over 30k-60k Steps, New Run (reward units)", COP_FORMAT),
        ("train_reward_30k_60k_original_same_seed", "Training Reward, Rolling Mean over 30k-60k Steps, Original Run Same Seed (reward units, pre-setpoint-fix)", COP_FORMAT),
        ("first_60k_within_original_noise", "First 60k Steps Within Original Run-to-Run Noise (labelled rule)", None),
        ("eval_seed_draws_rejected", "Training Draws Rejected by the Evaluation-Seed Guard (count)", COUNT_FORMAT),
        ("contaminated_training_episodes", "Training Episodes Run on an Evaluation Seed (count)", COUNT_FORMAT),
        ("resumes", "Number of Resumes After Interruption", COUNT_FORMAT),
        ("stop_reason", "Stop Reason", None),
    ]
    _export("convergence", {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "convergence")


def export_validation_log():
    spec = [
        ("train_seed", "Training Seed", COUNT_FORMAT),
        ("eval_index", "Validation Evaluation Index (0-based)", COUNT_FORMAT),
        ("timesteps", "Training Step at Evaluation", COUNT_FORMAT),
        ("wall_clock_s", "Training Wall Clock at Evaluation (seconds)", SECONDS_FORMAT),
        ("validation_wall_clock_s", "Validation Duration (seconds)", SECONDS_FORMAT),
        ("criterion_value", f"Selection Criterion: Validation Mean Tracking Error ({TE})", COP_FORMAT),
        ("total_reward", "Validation Mean Total Reward (SqTrError_TrPenalty_UserIncentives units)", COP_FORMAT),
        ("energy_user_satisfaction", "Validation Mean Energy User Satisfaction (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
        ("average_user_satisfaction", "Validation Mean Average User Satisfaction (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        ("total_transformer_overload", "Validation Mean Transformer Overload (kWh per simulated day)", KWH_FORMAT),
        ("tracking_error", f"Validation Mean Tracking Error ({TE})", COP_FORMAT),
        ("total_energy_charged", "Validation Mean Energy Charged (kWh per simulated day)", KWH_FORMAT),
        ("n_cells", "Validation Cells Averaged (count)", COUNT_FORMAT),
        ("train_steps_per_s_since_last_eval", "Training Throughput Since Previous Evaluation (steps per second)", KWH_FORMAT),
        ("conditions_hold", "Both Convergence Window Conditions Hold at This Evaluation", None),
        ("converged", "Convergence Declared at or Before This Evaluation", None),
    ]
    _export("validation_log", {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "validation_log")


def export_master_comparison():
    labels = {"algorithm": "Algorithm", "n_rows": "Number of Rows", "n_seeds": "Number of Scenario Seeds"}
    formats = {"Number of Rows": COUNT_FORMAT, "Number of Scenario Seeds": COUNT_FORMAT}
    metric_specs = [
        ("total_ev_served", "EVs Served", "count, mean per day", COUNT_FORMAT),
        ("total_transformer_overload", "Transformer Overload", "kWh per simulated day", KWH_FORMAT),
        ("average_user_satisfaction", "Average User Satisfaction", "fraction, 0 to 1", PCT_FRACTION_FORMAT),
        ("min_energy_user_satisfaction", "Minimum Energy User Satisfaction", "already 0-100 scale, %", PCT_ALREADY_SCALED_FORMAT),
        ("tracking_error", "Tracking Error", TE, COP_FORMAT),
        ("energy_tracking_error", "Energy Tracking Error", "dimensionless", DIMENSIONLESS_4DP_FORMAT),
        ("battery_degradation", "Battery Degradation", "dimensionless capacity-loss fraction", DIMENSIONLESS_4DP_FORMAT),
    ]
    for prefix, name, unit, fmt in metric_specs:
        for suffix, stat in [("_mean", "Mean"), ("_ci_low", "95% CI Lower Bound"), ("_ci_high", "95% CI Upper Bound")]:
            label = f"{name} -- {stat} ({unit})"
            labels[f"{prefix}{suffix}"] = label
            formats[label] = fmt
    _export("master_comparison", labels, formats, "test_grid_results")


def export_bootstrap_comparisons():
    spec = [
        ("comparison", "Comparison Kind (primary = extended vs. the new run's own 60k checkpoint)", None),
        ("baseline_A", "Baseline A (MEAN3[...] = per-cell mean across the 3 training seeds)", None),
        ("candidate_B", "Candidate B", None),
        ("metric", "Metric (units as in the master comparison workbook)", None),
        ("mean_A", "Mean of A over Paired Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("mean_B", "Mean of B over Paired Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("diff_B_minus_A", "Difference B minus A, Point Estimate (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("ci_low", "Difference B minus A, 95% Cluster-Bootstrap CI Lower Bound (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("ci_high", "Difference B minus A, 95% Cluster-Bootstrap CI Upper Bound (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("ci_excludes_zero", "95% CI Excludes Zero", None),
        ("n_pairs", "Number of Paired Cells (seed x day type)", COUNT_FORMAT),
        ("n_clusters", "Number of Clusters Resampled (independent scenario seeds)", COUNT_FORMAT),
    ]
    _export("bootstrap_comparisons", {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "cluster_bootstrap")


def export_ens_compliance():
    spec = [
        ("algorithm", "Algorithm", None),
        ("ENS_rel_point_pct", "Energy Not Served vs. AFAP, Point Estimate (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ENS_rel_ci_low_pct", "Energy Not Served vs. AFAP, 95% CI Lower Bound (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ENS_rel_ci_high_pct", "Energy Not Served vs. AFAP, 95% CI Upper Bound (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ENS_rel_pass_15pct_ci_upper_bound", "Passes <15% Target (CI Upper Bound Test)", None),
        ("ENS_abs_diagnostic_pct", "Energy Not Served vs. Requested Energy, Diagnostic Only (%)", PCT_ALREADY_SCALED_FORMAT),
        ("avg_satisfaction_pct", "Average User Satisfaction (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        ("min_satisfaction_pct", "Minimum Energy User Satisfaction (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
        ("satisfaction_gt_90pct", "Average Satisfaction Exceeds 90% Target", None),
        ("n_seeds", "Number of Scenario Seeds Behind This Row", COUNT_FORMAT),
    ]
    _export("ens_compliance", {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "target_compliance")


def export_optimality_gap():
    spec = [
        ("algorithm", "Algorithm", None),
        ("metric", "Metric", None),
        ("oracle_variant", "Oracle Variant Used as Reference", None),
        ("mean_abs_gap", "Mean Absolute Gap to Oracle (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("pct_of_oracle_value", "Gap as Percentage of the Oracle's Mean Value (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
        ("n_cells", "Number of Paired Cells", COUNT_FORMAT),
    ]
    _export("optimality_gap", {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "optimality_gap")


def export_train_seed_dispersion():
    spec = [
        ("family", "Checkpoint Family", None),
        ("metric", "Metric (units as in the master comparison workbook)", None),
        ("mean_ts100", "Training Seed 100, Mean over 100 Test Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("mean_ts101", "Training Seed 101, Mean over 100 Test Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("mean_ts102", "Training Seed 102, Mean over 100 Test Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("across_seed_mean", "Mean of the 3 Per-Seed Means (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("across_seed_std", "Sample Std of the 3 Per-Seed Means (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("across_seed_range", "Range (Max minus Min) of the 3 Per-Seed Means (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("relative_range_pct", "Range as Percentage of the Across-Seed Mean (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
    ]
    _export("train_seed_dispersion", {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "train_seed_dispersion")


def export_timing_calibration():
    spec = [
        ("label", "Calibration Configuration Label", None),
        ("utc", "Timestamp (UTC)", None),
        ("n_concurrent", "Concurrent Training Processes (count)", COUNT_FORMAT),
        ("seed", "Training Seed", COUNT_FORMAT),
        ("price_cache", "Price-Table Cache Enabled", None),
        ("torch_threads", "Torch Intra-Op Threads per Process", None),
        ("exit_code", "Process Exit Code", COUNT_FORMAT),
        ("steps", "Training Steps in the Calibration Run", COUNT_FORMAT),
        ("train_wall_s", "Training Wall Clock Excluding Validation (seconds)", SECONDS_FORMAT),
        ("train_steps_per_s", "Training Throughput (steps per second)", KWH_FORMAT),
        ("validation_wall_s", "One 20-Cell Validation Evaluation (seconds)", SECONDS_FORMAT),
        ("process_total_wall_s", "Whole Calibration Batch Wall Clock (seconds)", SECONDS_FORMAT),
        ("peak_rss_mb", "Peak Resident Memory per Process (MB)", COUNT_FORMAT),
        ("replay_buffer_mb_at_steps", "Replay Buffer File Size (MB)", KWH_FORMAT),
        ("checkpoint_kb", "Model Checkpoint File Size (KB)", COUNT_FORMAT),
        ("criterion_at_steps", f"Validation Tracking Error at the Final Calibration Step ({TE})", COP_FORMAT),
    ]
    _export(None, {c: l for c, l, _ in spec}, {l: f for _, l, f in spec if f}, "timing_calibration",
            src="experiments/phase2_algorithms/results/week6_part0/timing_calibration.csv")


if __name__ == "__main__":
    export_convergence()
    export_validation_log()
    export_master_comparison()
    export_bootstrap_comparisons()
    export_ens_compliance()
    export_optimality_gap()
    export_train_seed_dispersion()
    export_timing_calibration()
    print("Week 6 Part 0 workbooks written.")
