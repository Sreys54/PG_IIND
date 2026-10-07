"""
Closure brief: formatted .xlsx versions of every closure results table,
through ev2gym_thesis/xlsx_export.py::export_formatted_xlsx (CLAUDE.md rule 7).

Most closure tables share a column grammar, <metric>_mean / _ci_low / _ci_high
(cluster bootstrap over the scenario seed). Labels are therefore built from
one explicit per-metric dictionary (BASE) plus fixed suffix wording. Every
column still receives an explicit label, and export_formatted_xlsx's
missing-label check stays active: an unlisted metric raises.

Usage: PYTHONPATH=. python scripts/export_closure_results_xlsx.py
"""
import re

import pandas as pd

from ev2gym_thesis.xlsx_export import (COP_FORMAT, COP_PER_KWH_FORMAT, COUNT_FORMAT, KWH_FORMAT,
                                       PCT_FRACTION_FORMAT, PER_UNIT_VOLTAGE_FORMAT, export_formatted_xlsx)

R = "results"
CI = "95% CI, cluster bootstrap over 50 scenario seeds"

# metric -> (label stem with unit, number format)
BASE = {
    "average_user_satisfaction": ("Average User Satisfaction of Served EVs (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
    "dns_lower": ("Demand Not Served, Lower Bound (fraction of requested energy, 0 to 1)", PCT_FRACTION_FORMAT),
    "dns_upper": ("Demand Not Served, Upper Bound (fraction of requested energy, 0 to 1)", PCT_FRACTION_FORMAT),
    "total_transformer_overload": ("Transformer Overload (kWh per simulated day)", KWH_FORMAT),
    "total_energy_charged": ("Energy Delivered (kWh per simulated day)", KWH_FORMAT),
    "gross_margin_cop": ("Gross Margin at Bogota Prices (COP per simulated day)", COP_FORMAT),
    "total_ev_served": ("EVs Served (count per simulated day)", KWH_FORMAT),
    "peak_kw_p95": ("95th-Percentile Per-Seed Peak Station Power (kW)", KWH_FORMAT),
    "rejected_lower": ("Rejected Arrivals, Lower Bound (count per simulated day)", KWH_FORMAT),
    "rejected_upper": ("Rejected Arrivals, Upper Bound (count per simulated day)", KWH_FORMAT),
    "n_spawned": ("Spawned (Served) EVs (count per simulated day)", KWH_FORMAT),
    "energy_rejected_lower_kwh": ("Energy Requested by Rejected Arrivals, Lower Bound (kWh per day)", KWH_FORMAT),
    "shortfall_served_kwh": ("Shortfall on Served EVs, Requested minus Delivered (kWh per day)", KWH_FORMAT),
    "delta_dns_lower": ("Change in Demand Not Served vs. 8 Ports / 100 kW (fraction points, 0 to 1)", PCT_FRACTION_FORMAT),
    "delta_average_user_satisfaction": ("Change in Served-EV Satisfaction vs. 8 Ports / 100 kW (fraction points)", PCT_FRACTION_FORMAT),
    "delta_total_transformer_overload": ("Change in Transformer Overload vs. 8 Ports / 100 kW (kWh per day)", KWH_FORMAT),
    "delta_gross_margin_cop": ("Change in Gross Margin vs. 8 Ports / 100 kW (COP per day)", COP_FORMAT),
}
PLAIN = {
    "level": ("Demand Level (multiple of the Week 1 spawn multiplier 30; 0.75 means spawn 22 = 0.733x)", "0.000"),
    "level_label": ("Demand Level, Display Label", None),
    "algorithm": ("Algorithm", None),
    "n_runs": ("Runs (count)", COUNT_FORMAT),
    "n_clusters": ("Independent Scenario Seeds in the Bootstrap (n_clusters)", COUNT_FORMAT),
    "seeds_with_overload": ("Scenario Seeds with Any Overload (count of 50)", COUNT_FORMAT),
    "broken_satisfaction": ("Satisfaction Criterion Broken (CI lower bound < 0.90)", None),
    "broken_dns": ("Demand-Not-Served Criterion Broken (CI upper bound > 0.15)", None),
    "broken_peak": ("Peak Criterion Broken (CI upper bound of P95 peak > 100 kW)", None),
    "ports": ("Charging Ports (count)", COUNT_FORMAT),
    "station_demand": ("Station Demand Treatment (as run, or spawn scaled by 8/ports)", None),
    "transformer_kw": ("Transformer Limit (kW)", KWH_FORMAT),
    "transformer_kva_at_pf_0894": ("Transformer Rating (kVA at power factor 0.894)", KWH_FORMAT),
    "peak_kw_p95": ("95th-Percentile Per-Seed Peak Station Power (kW)", KWH_FORMAT),
    "peak_kw_p95_ci_low": (f"95th-Percentile Peak, {CI} Lower Bound (kW)", KWH_FORMAT),
    "peak_kw_p95_ci_high": (f"95th-Percentile Peak, {CI} Upper Bound (kW)", KWH_FORMAT),
}


def labels_for(columns):
    lab, fmt = {}, {}
    for c in columns:
        if c in PLAIN:
            lab[c], f = PLAIN[c]
        else:
            m = re.match(r"^(.*?)(_mean|_ci_low|_ci_high)?$", c)
            stem, suf = m.group(1), m.group(2)
            if stem not in BASE:
                raise KeyError(f"no label for column {c!r}")
            text, f = BASE[stem]
            lab[c] = {None: text, "_mean": f"{text}, Mean", "_ci_low": f"{text}, {CI} Lower Bound",
                      "_ci_high": f"{text}, {CI} Upper Bound"}[suf]
        if f:
            fmt[lab[c]] = f
    return lab, fmt


def export_grammar(name, sheet):
    cols = pd.read_csv(f"{R}/{name}.csv", nrows=0).columns
    lab, fmt = labels_for(cols)
    export_formatted_xlsx(f"{R}/{name}.csv", f"{R}/{name}.xlsx", lab, fmt, sheet_name=sheet)


def export_explicit(name, sheet, spec):
    lab = {k: v[0] for k, v in spec.items()}
    fmt = {v[0]: v[1] for v in spec.values() if v[1]}
    export_formatted_xlsx(f"{R}/{name}.csv", f"{R}/{name}.xlsx", lab, fmt, sheet_name=sheet)


def main():
    export_grammar("closure_c1_capacity_by_level", "c1_by_level")
    export_grammar("closure_c2_options", "c2_options")
    export_grammar("closure_demand_not_served", "dns_by_level_arm")
    export_explicit("closure_c1_breaking_levels", "breaking_levels", {
        "algorithm": ("Algorithm", None),
        "breaking_level": ("First Demand Level Where a Criterion Breaks (multiple of Week 1; 0.75 = 0.733x)", "0.000"),
        "breaking_level_label": ("Breaking Level, Display Label", None),
        "highest_level_not_broken": ("Highest Tested Level Below It With No Criterion Broken (multiple)", "0.000"),
        "first_criterion_broken": ("First Criterion Broken (satisfaction, dns, peak)", None),
        "all_criteria_broken_at_level": ("All Criteria Broken at That Level", None),
        "value": ("Value of the First Broken Criterion (fraction for dns/satisfaction; kW for peak)", "#,##0.0000"),
        "ci_low": (f"Value, {CI} Lower Bound", "#,##0.0000"),
        "ci_high": (f"Value, {CI} Upper Bound", "#,##0.0000"),
        "n_clusters": ("Independent Scenario Seeds in the Bootstrap (n_clusters)", COUNT_FORMAT),
        "levels_tested": ("Demand Levels Tested (multiples)", None)})
    cens = {
        "level": PLAIN["level"], "seed": ("Scenario Seed", COUNT_FORMAT), "eval_day": ("Evaluation Day", None),
        "spawn_multiplier": ("EV2Gym spawn_multiplier Used", "0.0000"),
        "n_spawned": ("EVs Spawned (count)", COUNT_FORMAT),
        "dropped_late_horizon": ("Arrivals Dropped by the Horizon-End Rule (count, not a rejection)", COUNT_FORMAT),
        "rejected_upper": ("Rejected Arrivals, Upper Bound (count)", COUNT_FORMAT),
        "rejected_lower": ("Rejected Arrivals, Lower Bound (count)", COUNT_FORMAT),
        "energy_rejected_upper_kwh": ("Energy Requested by Rejected Arrivals, Upper Bound (kWh)", KWH_FORMAT),
        "energy_rejected_lower_kwh": ("Energy Requested by Rejected Arrivals, Lower Bound (kWh)", KWH_FORMAT),
        "requested_served_kwh": ("Energy Requested by Spawned EVs (kWh)", KWH_FORMAT)}
    export_explicit("closure_censoring_by_cell", "censoring_8_ports", cens)
    export_explicit("closure_censoring_port_variants_by_cell", "censoring_port_variants",
                    {**cens, "ports": PLAIN["ports"],
                     "constant_demand": ("Constant Station Demand (spawn scaled by 8/ports)", None)})
    export_explicit("closure_margin_vs_overload_ci", "margin_vs_overload_ci", {
        "algorithm": ("Algorithm", None),
        "margin_foregone_vs_afap_cop": ("Margin Foregone vs. AFAP (COP per simulated day)", COP_FORMAT),
        "foregone_ci_low": (f"Margin Foregone, {CI} Lower Bound (COP per day)", COP_FORMAT),
        "foregone_ci_high": (f"Margin Foregone, {CI} Upper Bound (COP per day)", COP_FORMAT),
        "overload_avoided_vs_afap_kwh": ("Transformer Overload Avoided vs. AFAP (kWh per day)", KWH_FORMAT),
        "avoided_ci_low": (f"Overload Avoided, {CI} Lower Bound (kWh per day)", KWH_FORMAT),
        "avoided_ci_high": (f"Overload Avoided, {CI} Upper Bound (kWh per day)", KWH_FORMAT),
        "n_clusters": PLAIN["n_clusters"]})
    export_explicit("closure_lower_demand_monotonicity", "lower_demand", {
        "from_level": ("Lower Demand Level (multiple; 0.75 = 0.733x)", "0.000"),
        "to_level": ("Higher Demand Level (multiple)", "0.000"),
        "metric": ("Metric (Round Robin)", None),
        "mean_low_demand": ("Mean at the Lower Level (metric units: fraction or kWh/day)", "#,##0.0000"),
        "mean_high_demand": ("Mean at the Higher Level (metric units)", "#,##0.0000"),
        "diff_high_minus_low": ("Paired Difference, Higher minus Lower Level (metric units)", "#,##0.0000"),
        "ci_low": (f"Paired Difference, {CI} Lower Bound", "#,##0.0000"),
        "ci_high": (f"Paired Difference, {CI} Upper Bound", "#,##0.0000"),
        "cells_where_lower_demand_is_worse": ("Cells Where the Lower Level Is Worse (count of 100)", COUNT_FORMAT),
        "n_clusters": PLAIN["n_clusters"]})
    export_explicit("closure_multicity_tariffs", "city_tariffs", {
        "city": ("City (categoria especial, CGN vigencia 2026)", None), "operator": ("Network Operator", None),
        "sheet_month": ("Tariff Sheet Month", None), "source": ("Saved Source File", None),
        "cu_nivel2_sin_contribucion": ("Nivel 2 CU without Contribution (COP/kWh)", COP_PER_KWH_FORMAT),
        "flat_cost_con_contribucion": ("Flat Nivel 2 Commercial Cost with 20% Contribution (COP/kWh)", COP_PER_KWH_FORMAT),
        "flat_cost_status": ("Flat Cost: Published or Derived", None),
        "tou_option": ("Two-Band Tariff Option", None), "tou_peak_hours": ("Peak Band Hours (24 h clock)", None),
        "tou_peak_con": ("Peak-Band Cost with Contribution (COP/kWh)", COP_PER_KWH_FORMAT),
        "tou_offpeak_con": ("Off-Peak Cost with Contribution (COP/kWh)", COP_PER_KWH_FORMAT),
        "intraday_spread": ("Intraday Spread, (Peak - Off-Peak) / Off-Peak (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "generation_share": ("Generation Component Share of the CU (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "component_sum": ("Sum of the Six CU Components (COP/kWh)", COP_PER_KWH_FORMAT),
        "component_sum_abs_diff": ("Component Sum minus Stated CU, Absolute (COP/kWh)", COP_PER_KWH_FORMAT),
        "component_sum_ok": ("Invariant 1 Holds (sum within 0.01 COP/kWh)", None),
        "contribution_max_rel_diff": ("Largest Relative Deviation from the 1.20 Contribution Factor (fraction)", "0.000000"),
        "contribution_ok": ("Invariant 2 Holds (within 0.1%)", None),
        "unit_margin_at_1450": ("Unit Margin at 1,450 COP/kWh Retail (COP/kWh)", COP_PER_KWH_FORMAT),
        "operator_charging_price": ("Operator's Published Charging Price (COP/kWh)", COP_PER_KWH_FORMAT),
        "unit_margin_at_operator_price": ("Unit Margin at the Operator's Price (COP/kWh)", COP_PER_KWH_FORMAT),
        "charging_price_source": ("Charging Price Source", None),
        "unavailable": ("Data Not Published or Not Retrievable (listed, not filled in)", None)})
    export_explicit("closure_multicity_rr_cost", "rr_cost_by_city", {
        "city": ("City", None), "retail_price_label": ("Retail Price Case", None),
        "retail_price": ("Retail Price (COP/kWh)", COP_PER_KWH_FORMAT),
        "conceded_flat_cop_day": ("Round Robin Margin Conceded vs. AFAP, Flat Cost (COP per day)", COP_FORMAT),
        "conceded_flat_ci_low": (f"Conceded, Flat Cost, {CI} Lower Bound (COP per day)", COP_FORMAT),
        "conceded_flat_ci_high": (f"Conceded, Flat Cost, {CI} Upper Bound (COP per day)", COP_FORMAT),
        "conceded_flat_share_of_afap": ("Conceded as a Share of AFAP Margin, Flat Cost (fraction)", PCT_FRACTION_FORMAT),
        "n_clusters": PLAIN["n_clusters"],
        "conceded_tou_cop_day": ("Round Robin Margin Conceded vs. AFAP, Two-Band Cost (COP per day)", COP_FORMAT),
        "conceded_tou_ci_low": (f"Conceded, Two-Band Cost, {CI} Lower Bound (COP per day)", COP_FORMAT),
        "conceded_tou_ci_high": (f"Conceded, Two-Band Cost, {CI} Upper Bound (COP per day)", COP_FORMAT),
        "conceded_tou_share_of_afap": ("Conceded as a Share of AFAP Margin, Two-Band Cost (fraction)", PCT_FRACTION_FORMAT),
        "afap_peak_share": ("AFAP Energy in the Peak Band (fraction of daily energy)", PCT_FRACTION_FORMAT),
        "rr_peak_share": ("Round Robin Energy in the Peak Band (fraction of daily energy)", PCT_FRACTION_FORMAT)})
    export_explicit("closure_voltage_contribution", "voltage_contribution", {
        "setting": ("Week 7 Grid Setting", None), "n_pairs": ("Paired Runs (count)", COUNT_FORMAT),
        "n_clusters": PLAIN["n_clusters"],
        "afap_delta_min_v_mean": ("AFAP Drop in Feeder Minimum Voltage vs. Idle Station, Mean (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "rr_delta_min_v_mean": ("Round Robin Drop in Feeder Minimum Voltage vs. Idle Station, Mean (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "diff_rr_minus_afap": ("Paired Difference, Round Robin minus AFAP (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "diff_ci_low": (f"Paired Difference, {CI} Lower Bound (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "diff_ci_high": (f"Paired Difference, {CI} Upper Bound (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "rr_reduction_vs_afap": ("Round Robin Reduction of the Drop vs. AFAP, Ratio of Means (fraction)", PCT_FRACTION_FORMAT),
        "reduction_ci_low": (f"Reduction, {CI} Lower Bound (fraction)", PCT_FRACTION_FORMAT),
        "reduction_ci_high": (f"Reduction, {CI} Upper Bound (fraction)", PCT_FRACTION_FORMAT),
        "afap_runs_worst_bus_is_station_bus": ("AFAP Runs Whose Lowest-Voltage Bus Is the Station Bus 27 (count)", COUNT_FORMAT)})
    export_explicit("closure_feeder_probe_summary", "feeder_probe", {
        "feeder": ("EV2Gym Shipped Feeder", None), "n_buses": ("Buses (count)", COUNT_FORMAT),
        "station_bus": ("Station Bus (electrically farthest)", COUNT_FORMAT),
        "cells_screened": ("Idle-Station Cells Screened (count; stops at the first out-of-band cell)", COUNT_FORMAT),
        "cells_out_of_band": ("Cells with Any Bus Outside 0.95-1.05 p.u. (count)", COUNT_FORMAT),
        "min_v": ("Lowest Bus Voltage Seen (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "max_v": ("Highest Bus Voltage Seen (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "qualifies_in_band_idle": ("Qualifies: In Band in Every Idle Cell", None),
        "runnable_as_shipped": ("Runnable as Shipped (bus file has nominal loads)", None),
        "reason": ("Reason Not Runnable", None)})
    export_explicit("closure_ieee123_voltage", "ieee123_voltage", {
        "level": ("Station Demand Level (multiple of Week 1)", "0.0"), "algorithm": ("Algorithm", None),
        "n_runs": ("Runs (count)", COUNT_FORMAT), "n_clusters": PLAIN["n_clusters"],
        "idle_cells_out_of_band": ("Idle-Station Cells with Any Bus Out of Band (count of 100)", COUNT_FORMAT),
        "cells_out_of_band": ("Cells with Any Bus Outside 0.95-1.05 p.u. (count of 100)", COUNT_FORMAT),
        "bus_steps_out_of_band_total": ("(Bus, Step) Samples Out of Band, Total over 100 Cells (count)", COUNT_FORMAT),
        "band_compliance_all_cells": ("+/-5% Band Met in Every Cell", None),
        "min_voltage_pu_worst": ("Lowest Bus Voltage over All Cells (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "min_voltage_pu_mean": ("Daily Minimum Bus Voltage, Mean over Cells (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "station_bus_min_voltage_pu_worst": ("Lowest Station-Bus (115) Voltage over All Cells (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "delta_min_v_mean": ("Drop in Feeder Minimum Voltage vs. Idle Station, Mean (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "delta_min_v_ci_low": (f"Drop vs. Idle, {CI} Lower Bound (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "delta_min_v_ci_high": (f"Drop vs. Idle, {CI} Upper Bound (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "margin_to_band_pu_worst": ("Worst-Case Margin Above 0.95 p.u. (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "rr_reduction_vs_afap": ("Round Robin Reduction of the Drop vs. AFAP, Ratio of Means (fraction)", PCT_FRACTION_FORMAT),
        "reduction_ci_low": (f"Reduction, {CI} Lower Bound (fraction)", PCT_FRACTION_FORMAT),
        "reduction_ci_high": (f"Reduction, {CI} Upper Bound (fraction)", PCT_FRACTION_FORMAT)})
    export_explicit("closure_target_compliance", "target_compliance", {
        "algorithm": ("Algorithm", None), "n_runs": ("Runs at the Reference Demand (count)", COUNT_FORMAT),
        "n_clusters": PLAIN["n_clusters"],
        "sat_served_mean": ("Satisfaction of Served EVs, Mean (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "sat_served_ci_low": (f"Satisfaction of Served EVs, {CI} Lower Bound (fraction)", PCT_FRACTION_FORMAT),
        "sat_served_met": ("Target > 90% Met, Served EVs (as before)", None),
        "sat_all_arrivals_mean": ("Satisfaction Counting Rejected Arrivals as 0, Mean (fraction)", PCT_FRACTION_FORMAT),
        "sat_all_arrivals_ci_low": (f"Satisfaction Counting Rejected Arrivals, {CI} Lower Bound (fraction)", PCT_FRACTION_FORMAT),
        "sat_all_arrivals_met": ("Target > 90% Met, Counting Rejected Arrivals", None),
        "ens_rel_pct": ("ENS_rel vs. AFAP, Served EVs (already in %, 0 to 100)", '#,##0.00"%"'),
        "ens_rel_ci_high_pct": (f"ENS_rel, {CI} Upper Bound (already in %)", '#,##0.00"%"'),
        "ens_rel_met": ("Target < 15% Met, ENS_rel (as before)", None),
        "dns_lower_mean": ("Demand Not Served, Lower Bound, Mean (fraction)", PCT_FRACTION_FORMAT),
        "dns_lower_ci_high": (f"Demand Not Served, {CI} Upper Bound (fraction)", PCT_FRACTION_FORMAT),
        "dns_met": ("Target < 15% Met, Demand Not Served", None),
        "cells_with_overload": ("Cells with Transformer Overload (count of 100)", COUNT_FORMAT),
        "transformer_met": ("Transformer Within Rating in Every Cell", None),
        "voltage_status": ("Voltage +/-5% Status", None), "voltage_reason": ("Voltage Status Reason", None),
        "voltage_station_adds_outside_cells": ("34-Node Feeder: Cells Where the Station Adds Out-of-Band Samples (count of 100)", COUNT_FORMAT)})
    volt = {
        "n_steps": ("Simulated Steps (count)", COUNT_FORMAT),
        "n_bus_steps_outside": ("(Bus, Step) Samples Outside 0.95-1.05 p.u. (count)", COUNT_FORMAT),
        "n_steps_any_bus_outside": ("Steps with Any Bus Out of Band (count)", COUNT_FORMAT),
        "min_voltage_pu": ("Lowest Bus Voltage of the Run (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "max_voltage_pu": ("Highest Bus Voltage of the Run (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "worst_bus": ("Bus with the Lowest Voltage", COUNT_FORMAT),
        "excursion_pu_steps": ("Excursion Beyond the Band, Summed over Steps (p.u. x steps)", PER_UNIT_VOLTAGE_FORMAT),
        "station_bus_min_voltage_pu": ("Lowest Station-Bus Voltage (p.u.)", PER_UNIT_VOLTAGE_FORMAT),
        "station_bus_steps_outside": ("Station-Bus Steps Out of Band (count)", COUNT_FORMAT),
        "seed": ("Scenario Seed", COUNT_FORMAT), "eval_day": ("Evaluation Day", None)}
    export_explicit("closure_feeder_probe", "feeder_probe_cells", {
        "feeder": ("EV2Gym Shipped Feeder", None), "n_buses": ("Buses (count)", COUNT_FORMAT),
        "station_bus": ("Station Bus", COUNT_FORMAT), **volt})
    export_explicit("closure_ieee123_voltage_by_run", "ieee123_runs", {
        "level": ("Station Demand Level (multiple of Week 1)", "0.0"),
        "algorithm": ("Algorithm ('idle' = zero-action baseline)", None),
        "total_energy_charged": ("Energy Delivered (kWh per simulated day)", KWH_FORMAT),
        "total_transformer_overload": ("Transformer Overload (kWh per simulated day)", KWH_FORMAT),
        "average_user_satisfaction": ("Average User Satisfaction of Served EVs (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        **volt})
    export_explicit("closure_demand_not_served_by_run", "dns_by_run", {
        "run_id": ("Registry run_id", None), "config_name": ("Config Name", None), "level": PLAIN["level"],
        "algorithm": ("Algorithm", None), "seed": ("Scenario Seed", COUNT_FORMAT), "eval_day": ("Evaluation Day", None),
        "total_energy_charged": ("Energy Delivered (kWh per simulated day)", KWH_FORMAT),
        "n_spawned": ("EVs Spawned (count)", COUNT_FORMAT),
        "rejected_lower": ("Rejected Arrivals, Lower Bound (count)", COUNT_FORMAT),
        "rejected_upper": ("Rejected Arrivals, Upper Bound (count)", COUNT_FORMAT),
        "dropped_late_horizon": ("Arrivals Dropped by the Horizon-End Rule (count, not a rejection)", COUNT_FORMAT),
        "energy_rejected_lower_kwh": ("Energy Requested by Rejected Arrivals, Lower Bound (kWh)", KWH_FORMAT),
        "energy_rejected_upper_kwh": ("Energy Requested by Rejected Arrivals, Upper Bound (kWh)", KWH_FORMAT),
        "requested_served_kwh": ("Energy Requested by Spawned EVs (kWh)", KWH_FORMAT),
        "shortfall_served_kwh": ("Shortfall on Spawned EVs, Requested minus Delivered (kWh)", KWH_FORMAT),
        "dns_lower": ("Demand Not Served, Lower Bound (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "dns_upper": ("Demand Not Served, Upper Bound (fraction, 0 to 1)", PCT_FRACTION_FORMAT)})
    export_explicit("closure_multicity_tou_ranking", "tou_ranking", {
        "city": ("City", None), "n_arms": ("Arms Ranked (count)", COUNT_FORMAT),
        "ranking_by_energy": ("Ranking by Mean Energy Delivered (highest first)", None),
        "ranking_by_tou_margin": ("Ranking by Mean Margin under the Two-Band Cost (highest first)", None),
        "same_ranking": ("Rankings Identical", None),
        "n_positions_differing": ("Positions Where the Rankings Differ (count)", COUNT_FORMAT)})
    export_explicit("closure_audit_table", "audit", {
        "file": ("Document", None), "line": ("Line", COUNT_FORMAT), "check": ("Audit Check", None),
        "stated_value": ("Value Stated in the Document", None), "source_value": ("Value in the Current Source File", None),
        "action": ("Action Taken / Status", None), "context": ("Line Context (truncated)", None)})


if __name__ == "__main__":
    main()
