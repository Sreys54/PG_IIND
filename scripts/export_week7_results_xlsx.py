"""
Week 7 (Objectives 4 and 5): one formatted workbook per results/week7_*.csv
table, same convention as the Week 5 and Week 6 Part 0 exporters, all
through ev2gym_thesis.xlsx_export.export_formatted_xlsx (CLAUDE.md rule 7).

Scales, as in Weeks 5-6: average_user_satisfaction is a 0-1 FRACTION;
energy_user_satisfaction / min_energy_user_satisfaction and every *_pct
column are already on a 0-100 SCALE.

Usage: PYTHONPATH=. python scripts/export_week7_results_xlsx.py
"""
import os

from ev2gym_thesis.xlsx_export import (
    export_formatted_xlsx, COP_FORMAT, KWH_FORMAT, COP_PER_KWH_FORMAT, COUNT_FORMAT, PCT_FRACTION_FORMAT,
    PCT_ALREADY_SCALED_FORMAT, SECONDS_FORMAT, DIMENSIONLESS_4DP_FORMAT, MIXED_UNIT_4DP_FORMAT,
    PER_UNIT_VOLTAGE_FORMAT,
)

TE = "dimensionless, sum of squared kW deviations"
METRIC_SPECS = {  # prefix -> (name, unit, format)
    "total_ev_served": ("EVs Served", "count per simulated day", COUNT_FORMAT),
    "total_transformer_overload": ("Transformer Overload", "kWh per simulated day", KWH_FORMAT),
    "average_user_satisfaction": ("Average User Satisfaction", "fraction, 0 to 1", PCT_FRACTION_FORMAT),
    "min_energy_user_satisfaction": ("Minimum Energy User Satisfaction", "already 0-100 scale, %", PCT_ALREADY_SCALED_FORMAT),
    "tracking_error": ("Tracking Error", TE, COP_FORMAT),
    "energy_tracking_error": ("Energy Tracking Error", "dimensionless", DIMENSIONLESS_4DP_FORMAT),
    "battery_degradation": ("Battery Degradation", "dimensionless capacity-loss fraction", DIMENSIONLESS_4DP_FORMAT),
    "total_energy_charged": ("Energy Charged", "kWh per simulated day", KWH_FORMAT),
    "energy_user_satisfaction": ("Energy User Satisfaction", "already 0-100 scale, %", PCT_ALREADY_SCALED_FORMAT),
}
SETTING = ("setting", "Growth Setting (base; spawn1.3/1.6 = station demand axis; load1.3/1.6 = feeder load axis)", None)
ALGO = ("algorithm", "Algorithm", None)
NCL = ("n_clusters", "Number of Clusters Resampled (independent scenario seeds)", COUNT_FORMAT)


def _export(csv_path, spec, sheet):
    if not os.path.exists(csv_path):
        print(f"skip (missing): {csv_path}")
        return
    export_formatted_xlsx(csv_path, csv_path.replace(".csv", ".xlsx"),
                          column_labels={c: l for c, l, _ in spec},
                          number_formats={l: f for _, l, f in spec if f}, sheet_name=sheet)


def _mean_ci_spec(prefixes):
    spec = []
    for p in prefixes:
        name, unit, fmt = METRIC_SPECS[p]
        for suf, stat in [("_mean", "Mean"), ("_ci_low", "95% Cluster-Bootstrap CI Lower Bound"),
                          ("_ci_high", "95% Cluster-Bootstrap CI Upper Bound")]:
            spec.append((f"{p}{suf}", f"{name} -- {stat} ({unit})", fmt))
    return spec


def _paired_spec():
    return [("setting_A", "Setting of A", None), ("setting_B", "Setting of B", None),
            ("algorithm_A", "Algorithm A", None), ("algorithm_B", "Algorithm B", None),
            ("metric", "Metric (units as in the grid master comparison workbook)", None),
            ("mean_A", "Mean of A over Paired Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
            ("mean_B", "Mean of B over Paired Cells (metric units)", MIXED_UNIT_4DP_FORMAT),
            ("diff_B_minus_A", "Difference B minus A, Point Estimate (metric units)", MIXED_UNIT_4DP_FORMAT),
            ("ci_low", "Difference B minus A, 95% Cluster-Bootstrap CI Lower Bound (metric units)", MIXED_UNIT_4DP_FORMAT),
            ("ci_high", "Difference B minus A, 95% Cluster-Bootstrap CI Upper Bound (metric units)", MIXED_UNIT_4DP_FORMAT),
            ("ci_excludes_zero", "95% CI Excludes Zero", None),
            ("n_pairs", "Number of Paired Cells (seed x day type)", COUNT_FORMAT), NCL]


def export_all():
    R = "results/"
    _export(R + "week7_grid_equivalence_summary.csv", [
        ("metric", "Station Metric", None),
        ("mean_nongrid", "Mean, Non-Grid Config (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("mean_grid", "Mean, Grid-Enabled Config (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("max_abs_diff", "Maximum Absolute Per-Cell Difference (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("within_tolerance", "Within the Pre-Stated Tolerance", None),
        ("n_cells", "Paired Cells (AFAP and Round Robin x seeds 0-9 x 2 days)", COUNT_FORMAT),
        ("tolerance_abs", "Pre-Stated Absolute Tolerance (metric units)", "0.000000")], "grid_equivalence")
    _export(R + "week7_grid_base_equivalence_all_arms.csv", [
        ("metric", "Station Metric", None),
        ("n_cells", "Paired Cells (base setting: 50 seeds x 2 days x 5 arms)", COUNT_FORMAT),
        ("n_arms", "Arms Compared", COUNT_FORMAT),
        ("max_abs_diff", "Maximum Absolute Grid minus Non-Grid Difference (metric units)", MIXED_UNIT_4DP_FORMAT),
        ("identical", "Identical Within 1e-6", None)], "base_equivalence_all_arms")
    _export(R + "week7_grid_master_comparison.csv",
            [SETTING, ALGO, ("n_rows", "Number of Rows (cells)", COUNT_FORMAT)] + _mean_ci_spec(list(METRIC_SPECS)) + [NCL],
            "grid_master_comparison")
    _export(R + "week7_grid_vs_roundrobin.csv", _paired_spec(), "vs_round_robin")
    _export(R + "week7_grid_growth_effect.csv", _paired_spec(), "growth_effect")
    _export(R + "week7_grid_ens_compliance.csv", [
        SETTING, ALGO,
        ("ENS_rel_point_pct", "Energy Not Served vs. AFAP, Point Estimate (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ENS_rel_ci_low_pct", "Energy Not Served vs. AFAP, 95% CI Lower Bound (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ENS_rel_ci_high_pct", "Energy Not Served vs. AFAP, 95% CI Upper Bound (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ENS_rel_pass_15pct_ci_upper_bound", "Passes <15% Target (CI Upper Bound Test)", None),
        ("ENS_abs_diagnostic_pct", "Energy Not Served vs. Requested Energy, Diagnostic Only (%)", PCT_ALREADY_SCALED_FORMAT),
        ("avg_satisfaction_pct", "Average User Satisfaction (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        ("min_satisfaction_pct", "Minimum Energy User Satisfaction (already 0-100 scale, %)", PCT_ALREADY_SCALED_FORMAT),
        ("satisfaction_gt_90pct", "Average Satisfaction Exceeds 90% Target", None),
        ("n_seeds", "Number of Scenario Seeds Behind This Row", COUNT_FORMAT)], "ens_compliance")
    _export(R + "week7_transformer_sizing.csv", [
        SETTING, ALGO, ("n_seeds", "Scenario Seeds", COUNT_FORMAT),
        ("seeds_with_overload", "Seeds with Any Overload (count)", COUNT_FORMAT),
        ("overload_p50", "Per-Seed Overload, 50th Percentile (kWh per day)", KWH_FORMAT),
        ("overload_p90", "Per-Seed Overload, 90th Percentile (kWh per day)", KWH_FORMAT),
        ("overload_p95", "Per-Seed Overload, 95th Percentile (kWh per day)", KWH_FORMAT),
        ("overload_max", "Per-Seed Overload, Maximum (kWh per day)", KWH_FORMAT),
        ("peak_kw_p50", "Per-Seed Peak Station Power, 50th Percentile (kW)", KWH_FORMAT),
        ("peak_kw_p90", "Per-Seed Peak Station Power, 90th Percentile (kW)", KWH_FORMAT),
        ("peak_kw_p95", "Per-Seed Peak Station Power, 95th Percentile (kW)", KWH_FORMAT),
        ("peak_kw_max", "Per-Seed Peak Station Power, Maximum (kW)", KWH_FORMAT),
        ("rating_kw_for_p95_seed_no_overload", "Transformer Rating at Which the 95th-Percentile Seed Stops Overloading (kW)", KWH_FORMAT),
        ("next_standard_kva_unity_pf", "Next Standard Distribution Transformer Size (kVA, unity power factor assumed)", KWH_FORMAT),
        ("seeds_above_p95", "Seeds Above the 95th Percentile (count; tail support)", COUNT_FORMAT)], "transformer_sizing")
    _export(R + "week7_transformer_per_seed.csv", [
        SETTING, ALGO, ("seed", "Scenario Seed", COUNT_FORMAT),
        ("overload_kwh_per_day", "Transformer Overload, Mean of Weekday and Weekend (kWh per day)", KWH_FORMAT),
        ("peak_kw", "Peak Station Power, Max of Weekday and Weekend (kW)", KWH_FORMAT)], "transformer_per_seed")
    vol = [SETTING, ALGO, ("n_runs", "Cells (seed x day type)", COUNT_FORMAT),
           ("cells_idle_feeder_outside_band", "Cells Where the Feeder Leaves 0.95-1.05 p.u. with the Station Idle", COUNT_FORMAT),
           ("cells_with_arm_outside_band", "Cells Where the Feeder Leaves the Band with This Arm Charging", COUNT_FORMAT),
           ("cells_station_adds_outside_samples", "Cells Where the Station Adds Out-of-Band (Bus, Step) Samples", COUNT_FORMAT),
           ("min_voltage_pu_worst", "Worst Minimum Bus Voltage with This Arm (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
           ("min_voltage_pu_idle_worst", "Worst Minimum Bus Voltage with the Station Idle (p.u.)", PER_UNIT_VOLTAGE_FORMAT)]
    for p, name, fmt in [("delta_bus_steps_outside", "Station-Attributable Out-of-Band (Bus, Step) Samples per Day (count)", MIXED_UNIT_4DP_FORMAT),
                         ("delta_min_voltage_pu", "Station-Attributable Change in Minimum Bus Voltage (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
                         ("delta_excursion_pu_steps", "Station-Attributable Excursion Beyond the Band (p.u. x step)", PER_UNIT_VOLTAGE_FORMAT),
                         ("delta_station_bus_steps_outside", "Station-Attributable Out-of-Band Steps at the Station Bus (count)", MIXED_UNIT_4DP_FORMAT),
                         ("n_bus_steps_outside", "Out-of-Band (Bus, Step) Samples with This Arm (count)", MIXED_UNIT_4DP_FORMAT)]:
        for suf, stat in [("_mean", "Mean"), ("_ci_low", "95% CI Lower Bound"), ("_ci_high", "95% CI Upper Bound")]:
            vol.append((p + suf, f"{name} -- {stat}", fmt))
    _export(R + "week7_voltage_attribution.csv", vol + [NCL], "voltage_attribution")
    _export(R + "week7_voltage_probe.csv", [
        ("run_id", "Run Identifier", None), ("config_name", "Config Name", None), ("setting", "Probe Setting", None),
        ALGO, ("seed", "Scenario Seed", COUNT_FORMAT), ("eval_day", "Evaluation Day", None), ("day_type", "Day Type", None),
        ("lib_voltage_violation", "EV2Gym voltage_violation (p.u. x step, <= 0)", PER_UNIT_VOLTAGE_FORMAT),
        ("lib_voltage_violation_counter", "EV2Gym voltage_violation_counter (bus-step samples outside band)", COUNT_FORMAT),
        ("n_steps", "Simulated Steps", COUNT_FORMAT),
        ("n_bus_steps_outside", "Independent Check: (Bus, Step) Samples Outside 0.95-1.05 p.u.", COUNT_FORMAT),
        ("n_steps_any_bus_outside", "Independent Check: Steps with Any Bus Outside the Band", COUNT_FORMAT),
        ("min_voltage_pu", "Minimum Bus Voltage (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        ("max_voltage_pu", "Maximum Bus Voltage (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        ("worst_bus", "Bus with the Minimum Voltage (1-based)", COUNT_FORMAT),
        ("excursion_pu_steps", "Total Excursion Beyond the Band (p.u. x step)", PER_UNIT_VOLTAGE_FORMAT),
        ("station_bus_min_voltage_pu", "Station Bus (27) Minimum Voltage (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        ("station_bus_steps_outside", "Station Bus (27) Steps Outside the Band", COUNT_FORMAT),
        ("load_multiplier", "Feeder Load Multiplier", DIMENSIONLESS_4DP_FORMAT)], "voltage_probe")
    _export(R + "week7_grid_margin_bogota.csv", [
        SETTING, ALGO,
        ("gross_margin_cop_per_day_mean", "Gross Margin, Revenue minus Cost -- Mean (COP per simulated day)", COP_FORMAT),
        ("gross_margin_ci_low", "Gross Margin -- 95% CI Lower Bound (COP per simulated day)", COP_FORMAT),
        ("gross_margin_ci_high", "Gross Margin -- 95% CI Upper Bound (COP per simulated day)", COP_FORMAT),
        ("margin_conceded_vs_afap_cop_per_day", "Margin Conceded vs. AFAP -- Point Estimate (COP per simulated day)", COP_FORMAT),
        ("conceded_ci_low", "Margin Conceded vs. AFAP -- 95% CI Lower Bound (COP per simulated day)", COP_FORMAT),
        ("conceded_ci_high", "Margin Conceded vs. AFAP -- 95% CI Upper Bound (COP per simulated day)", COP_FORMAT),
        ("unit_margin_cop_per_kwh", "Unit Margin, Retail minus Purchase Cost (COP per kWh)", COP_PER_KWH_FORMAT), NCL],
        "grid_margin_bogota")
    _export(R + "week7_target_compliance.csv", [
        SETTING, ALGO,
        ("avg_satisfaction_mean", "Average User Satisfaction -- Mean (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        ("avg_satisfaction_ci_low", "Average User Satisfaction -- 95% CI Lower Bound (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        ("satisfaction_target_met_ci_lower_gt_90pct", "Satisfaction Target Met (CI Lower Bound > 90%)", None),
        ("ens_rel_point_pct", "Energy Not Served vs. AFAP, Point Estimate (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ens_rel_ci_high_pct", "Energy Not Served vs. AFAP, 95% CI Upper Bound (%)", PCT_ALREADY_SCALED_FORMAT),
        ("ens_target_met_ci_upper_lt_15pct", "Energy-Not-Served Target Met (CI Upper Bound < 15%)", None),
        ("voltage_cells_station_adds_outside_samples", "Voltage: Cells Where the Station Adds Out-of-Band Samples", COUNT_FORMAT),
        ("voltage_cells_total", "Voltage: Cells Evaluated", COUNT_FORMAT),
        ("voltage_station_increment_ci_high", "Voltage: Station-Attributable Out-of-Band Samples, 95% CI Upper Bound", MIXED_UNIT_4DP_FORMAT),
        ("voltage_station_adds_no_excursion_all_cells", "Voltage Target Met (Station Adds No Out-of-Band Sample in Any Cell)", None),
        ("voltage_cells_idle_feeder_outside_band", "Voltage: Cells Where the Feeder Is Out of Band with the Station Idle", COUNT_FORMAT),
        NCL], "target_compliance")
    _export(R + "week7_replicability_margin.csv", [
        ("dataset", "Dataset (nongrid = Week 5 statistical rows; grid_<setting> = Week 7 grid rows)", None),
        ("price_scenario", "Price Scenario", None),
        ("retail_cop_per_kwh", "Retail EV Charging Price (COP per kWh)", COP_PER_KWH_FORMAT),
        ("purchase_cost_cop_per_kwh", "Energy Purchase Cost, CU with Contribution (COP per kWh)", COP_PER_KWH_FORMAT), ALGO,
        ("mean_energy_kwh_per_day", "Energy Charged, Mean (kWh per simulated day)", KWH_FORMAT),
        ("gross_margin_cop_per_day", "Gross Margin -- Mean (COP per simulated day)", COP_FORMAT),
        ("margin_ci_low", "Gross Margin -- 95% CI Lower Bound (COP per simulated day)", COP_FORMAT),
        ("margin_ci_high", "Gross Margin -- 95% CI Upper Bound (COP per simulated day)", COP_FORMAT),
        ("margin_conceded_vs_afap_cop_per_day", "Margin Conceded vs. AFAP -- Point Estimate (COP per simulated day)", COP_FORMAT),
        ("conceded_ci_low", "Margin Conceded vs. AFAP -- 95% CI Lower Bound (COP per simulated day)", COP_FORMAT),
        ("conceded_ci_high", "Margin Conceded vs. AFAP -- 95% CI Upper Bound (COP per simulated day)", COP_FORMAT), NCL],
        "two_city_margin")
    _export(R + "week7_cost_of_transformer_limit_two_cities.csv", [
        ("dataset", "Dataset", None), ALGO,
        ("conceded_ci_high_bogota_base", "Bogota: Margin Conceded vs. AFAP, 95% CI Upper Bound (COP per day)", COP_FORMAT),
        ("conceded_ci_high_medellin_base", "Medellin: Margin Conceded vs. AFAP, 95% CI Upper Bound (COP per day)", COP_FORMAT),
        ("conceded_ci_low_bogota_base", "Bogota: Margin Conceded vs. AFAP, 95% CI Lower Bound (COP per day)", COP_FORMAT),
        ("conceded_ci_low_medellin_base", "Medellin: Margin Conceded vs. AFAP, 95% CI Lower Bound (COP per day)", COP_FORMAT),
        ("margin_conceded_vs_afap_cop_per_day_bogota_base", "Bogota: Margin Conceded vs. AFAP, Point Estimate (COP per day)", COP_FORMAT),
        ("margin_conceded_vs_afap_cop_per_day_medellin_base", "Medellin: Margin Conceded vs. AFAP, Point Estimate (COP per day)", COP_FORMAT),
        NCL], "cost_of_limit_two_cities")
    _export(R + "week7_ranking_invariance.csv", [
        ("dataset", "Dataset", None), ("price_scenario", "Price Scenario", None),
        ("unit_margin_cop_per_kwh", "Unit Margin, Retail minus Cost (COP per kWh)", COP_PER_KWH_FORMAT),
        ("ranking_by_margin", "Arms Ranked by Mean Gross Margin (highest first)", None),
        ("same_as_energy_ranking", "Margin Ranking Equals Energy Ranking", None),
        ("ranking_identical_across_all_price_scenarios", "Ranking Identical Across All Price Scenarios of This Dataset", None)],
        "ranking_invariance")
    _export(R + "week7_transfer_classification.csv", [
        ("model_input", "Model Input", None), ("classification", "Transferability Class", None),
        ("bogota_value", "Bogota Value / Source", None), ("medellin_value", "Medellin Value / Source", None),
        ("note", "Note", None)], "transfer_classification")
    _export(R + "week7_demand_mapping.csv", [
        ("quantity", "Quantity (source: Andi-Fenalco via El Colombiano, 2025-09-10; Bogota chargers: Week 1)", None),
        ("medellin", "Medellin (count)", COUNT_FORMAT), ("bogota", "Bogota (count)", COUNT_FORMAT),
        ("ratio_medellin_over_bogota", "Ratio Medellin / Bogota (dimensionless)", DIMENSIONLESS_4DP_FORMAT),
        ("supports_per_station_demand_mapping", "Supports a Per-Station Demand Mapping", None)], "demand_mapping")
    _export("experiments/phase3_infra_replicability/results/week7_timing_one_cell.csv", [
        ("arm", "Arm", None), ("seconds", "End-to-End Wall Clock for One Grid Cell (seconds)", SECONDS_FORMAT),
        ("tracking_error", f"Tracking Error of That Cell ({TE})", COP_FORMAT),
        ("total_transformer_overload", "Transformer Overload of That Cell (kWh)", KWH_FORMAT),
        ("notes_status", "Oracle Reached Gurobi OPTIMAL (blank for non-oracle arms)", None)], "timing_one_cell")


if __name__ == "__main__":
    export_all()
    print("Week 7 workbooks written.")
