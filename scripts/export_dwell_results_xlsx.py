"""
Final capacity (dwell) brief: formatted .xlsx versions of every dwell results
table, through ev2gym_thesis/xlsx_export.py::export_formatted_xlsx (CLAUDE.md
rule 7). Same label grammar as scripts/export_closure_results_xlsx.py
(<metric>_mean / _ci_low / _ci_high, cluster bootstrap over the scenario
seed); every column gets an explicit, unit-bearing label, and an unlisted
column raises.

Usage: PYTHONPATH=. python scripts/export_dwell_results_xlsx.py
"""
import re

import pandas as pd

from ev2gym_thesis.xlsx_export import (COP_FORMAT, COUNT_FORMAT, KWH_FORMAT, PCT_FRACTION_FORMAT,
                                       export_formatted_xlsx)
from scripts.export_closure_results_xlsx import BASE as CLOSURE_BASE, CI, PLAIN as CLOSURE_PLAIN

R = "results"
MIN_FORMAT = "#,##0.0"  # minutes
FRAC4 = "#,##0.0000"

BASE = {**CLOSURE_BASE,
        "sat_all_arrivals": ("Satisfaction Counting Rejected Arrivals as 0 (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "duration_mean": ("Connection Duration per Session (minutes)", MIN_FORMAT),
        "energy_requested": ("Energy Requested per Session (kWh)", KWH_FORMAT),
        "arrivals_spawned": ("Arrivals That Got a Port (count per day)", KWH_FORMAT),
        "arrivals_offered_lower": ("Arrivals Offered, Spawned plus Rejected Lower Bound (count per day)", KWH_FORMAT),
        "mean_port_occupancy": ("Mean Port Occupancy over the Day (fraction of port-steps, 0 to 1)", PCT_FRACTION_FORMAT),
        "arrivals_offered_per_day": ("Arrivals Offered per Day, Spawned plus Rejected Lower Bound (count)", KWH_FORMAT),
        "arrivals_served_per_day": ("Arrivals Served per Day (count)", KWH_FORMAT),
        "kwh_requested_per_day": ("Energy Requested per Day, Served plus Rejected Lower Bound (kWh)", KWH_FORMAT),
        "delta_dns_lower_vs_8p100kw": ("Change in Demand Not Served vs. 8 Ports / 100 kW (fraction points)", PCT_FRACTION_FORMAT),
        "delta_dns_lower": ("Change in Demand Not Served vs. 8 Ports / 100 kW (fraction points)", PCT_FRACTION_FORMAT),
        "delta_gross_margin_cop_vs_8p100kw": ("Change in Gross Margin vs. 8 Ports / 100 kW (COP per day)", COP_FORMAT),
        "delta_gross_margin_cop": ("Change in Gross Margin vs. 8 Ports / 100 kW (COP per day)", COP_FORMAT),
        }
PLAIN = {**CLOSURE_PLAIN,
         "level": ("Demand Level (multiple of the Week 1 spawn multiplier 30; 0.25 = spawn 8 = 0.267x, 0.75 = spawn 22 = 0.733x)", "0.000"),
         "dwell_mean_min": ("DC Session Model, Target Mean Connection Duration (minutes)", MIN_FORMAT),
         "spawn_multiplier": ("EV2Gym spawn_multiplier at 8 Ports", COUNT_FORMAT),
         "spawn_multiplier_base": ("EV2Gym spawn_multiplier at 8 Ports", COUNT_FORMAT),
         "peak_kva_p95_at_pf_0894": ("95th-Percentile Peak Station Power (kVA at power factor 0.894)", KWH_FORMAT),
         "rating_kw": ("Transformer Rating Used for the Peak Criterion (kW)", KWH_FORMAT),
         "cells_with_overload": ("Runs with Any Transformer Overload (count of 100)", COUNT_FORMAT),
         "broken_satisfaction": ("Satisfaction Criterion Broken (CI lower bound of satisfaction counting rejected arrivals < 0.90)", None),
         "broken_peak": ("Peak Criterion Broken (CI upper bound of P95 peak > the transformer rating in kW)", None),
         "meets_all": ("Meets All Three Criteria", None),
         "transformer_rating": ("Transformer Rating (Enel ET-013 class)", None),
         "delta_dns_lower_vs_8p100kw": ("Change in Demand Not Served vs. 8 Ports / 100 kW, Mean (fraction points)", PCT_FRACTION_FORMAT),
         "delta_gross_margin_cop_vs_8p100kw": ("Change in Gross Margin vs. 8 Ports / 100 kW, Mean (COP per day)", COP_FORMAT),
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


def export_grammar(name, sheet, extra=None):
    cols = pd.read_csv(f"{R}/{name}.csv", nrows=0).columns
    global PLAIN
    saved = dict(PLAIN)
    PLAIN.update(extra or {})
    try:
        lab, fmt = labels_for(cols)
    finally:
        PLAIN = saved
    export_formatted_xlsx(f"{R}/{name}.csv", f"{R}/{name}.xlsx", lab, fmt, sheet_name=sheet)


def export_explicit(name, sheet, spec):
    lab = {k: v[0] for k, v in spec.items()}
    fmt = {v[0]: v[1] for v in spec.values() if v[1]}
    export_formatted_xlsx(f"{R}/{name}.csv", f"{R}/{name}.xlsx", lab, fmt, sheet_name=sheet)


def main():
    export_grammar("dwell_a_session_summary", "session_summary", {
        "variant": ("Session Model (dutch = EV2Gym as configured; 32/42/78 = DC transform target mean, minutes)", None),
        "target_mean_min": ("Target Mean Connection Duration (minutes)", MIN_FORMAT),
        "cv": ("Coefficient of Variation of the Lognormal (assumption)", "0.00"),
        "n_evs": ("Spawned EVs Pooled (count)", COUNT_FORMAT), "n_cells": ("Cells (count)", COUNT_FORMAT),
        "duration_mean_min": ("Connection Duration per Session, Mean (minutes)", MIN_FORMAT),
        "duration_median_min": ("Connection Duration, Median (minutes)", MIN_FORMAT),
        "duration_p10_min": ("Connection Duration, 10th Percentile (minutes)", MIN_FORMAT),
        "duration_p90_min": ("Connection Duration, 90th Percentile (minutes)", MIN_FORMAT),
        "duration_min_min": ("Connection Duration, Minimum (minutes)", MIN_FORMAT),
        "duration_max_min": ("Connection Duration, Maximum (minutes)", MIN_FORMAT),
        "share_one_step_sessions": ("Sessions Lasting One 15-Minute Step (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "energy_requested_mean_kwh": ("Energy Requested per Session, Mean (kWh)", KWH_FORMAT),
        "energy_requested_median_kwh": ("Energy Requested per Session, Median (kWh)", KWH_FORMAT),
        "arrivals_spawned_per_day": ("Arrivals That Got a Port, Mean (count per day)", KWH_FORMAT),
        "arrivals_offered_lower_per_day": ("Arrivals Offered (spawned + rejected, lower bound), Mean (count per day)", KWH_FORMAT),
        "rejected_lower_per_day": ("Rejected Arrivals, Lower Bound (count per day)", KWH_FORMAT),
        "rejected_upper_per_day": ("Rejected Arrivals, Upper Bound (count per day)", KWH_FORMAT),
        "dropped_late_horizon_per_day": ("Late Arrivals Dropped by the Horizon Rule (count per day)", KWH_FORMAT),
        "realised_vs_target_mean_pct": ("Realised Mean minus Target, Relative (% of target, already scaled)", '#,##0.00"%"'),
        "duration_mean_ci_low": (f"Connection Duration Mean, {CI} Lower Bound (minutes)", MIN_FORMAT),
        "duration_mean_ci_high": (f"Connection Duration Mean, {CI} Upper Bound (minutes)", MIN_FORMAT),
        "energy_requested_ci_low": (f"Energy Requested Mean, {CI} Lower Bound (kWh)", KWH_FORMAT),
        "energy_requested_ci_high": (f"Energy Requested Mean, {CI} Upper Bound (kWh)", KWH_FORMAT),
    })
    export_explicit("dwell_a_reference_comparison", "reference_comparison", {
        "quantity": ("Quantity", None), "kind": ("Kind (simulated, or external reference)", None),
        "mean_session_min": ("Mean Session Duration (minutes)", MIN_FORMAT),
        "mean_session_ci": ("Mean Session, 95% CI (minutes; cluster bootstrap over 50 seeds)", None),
        "median_session_min": ("Median Session (minutes)", MIN_FORMAT), "p10_min": ("10th Percentile (minutes)", MIN_FORMAT),
        "p90_min": ("90th Percentile (minutes)", MIN_FORMAT),
        "energy_per_session_kwh": ("Energy per Session (kWh)", KWH_FORMAT),
        "ratio_sim_mean_to_reference": ("Simulated Mean Divided by This Reference (ratio)", "0.00"),
        "source": ("Source", None), "n_clusters": ("Independent Scenario Seeds (n_clusters)", COUNT_FORMAT)})
    export_grammar("dwell_c1_capacity_by_level", "c1_by_level")
    export_explicit("dwell_c1_breaking_levels", "breaking_levels", {
        "dwell_mean_min": PLAIN["dwell_mean_min"], "algorithm": ("Algorithm", None),
        "levels_tested": ("Demand Levels Tested (multiples)", None),
        "lowest_level_tested": ("Lowest Demand Level Tested (multiple)", "0.000"),
        "first_level_broken_satisfaction": ("First Level Where Satisfaction Breaks (multiple; blank = never)", "0.000"),
        "first_level_broken_dns": ("First Level Where Demand Not Served Breaks (multiple; blank = never)", "0.000"),
        "first_level_broken_peak": ("First Level Where the Peak Criterion Breaks (multiple; blank = never)", "0.000"),
        "breaking_level": ("First Level Where Any Criterion Breaks (multiple; blank = never)", "0.000"),
        "breaking_level_label": ("Breaking Level, Display Label", None),
        "highest_level_not_broken": ("Highest Tested Level Meeting All Criteria (multiple; blank = none)", "0.000"),
        "breaks_at_lowest_level_tested": ("Breaks Already at the Lowest Level Tested", None),
        "criteria_broken_at_breaking_level": ("Criteria Broken at the Breaking Level", None),
        "first_criterion": ("First Criterion Listed (satisfaction, dns, peak)", None),
        "value": ("Value of That Criterion (fraction for dns/satisfaction; kW for peak)", FRAC4),
        "ci_low": (f"Value, {CI} Lower Bound", FRAC4), "ci_high": (f"Value, {CI} Upper Bound", FRAC4),
        "confirmed_one_level_beyond": ("Next Level Also Fails (confirmation)", None),
        "n_clusters": PLAIN["n_clusters"]})
    export_grammar("dwell_c2_growth_options", "c2_growth_options")
    export_grammar("dwell_c2_minimal_configs", "c2_minimal_configs", {
        "minimal_config": ("Pareto-Minimal Configuration Meeting All Three Criteria", None),
        "searched_ports": ("Ports Searched (count list)", None), "searched_kw": ("Transformer Limits Searched (kW list)", None)})
    export_grammar("dwell_d_physical_units", "physical_units", {
        "model": ("Session Model", None), "constant_station_demand": ("Constant Station Demand (spawn scaled by 8/ports)", None),
        "n_cells": ("Cells (count)", COUNT_FORMAT),
        "kwh_requested_per_port_per_day": ("Energy Requested per Port per Day (kWh)", KWH_FORMAT)})
    export_explicit("dwell_e_target_compliance", "target_compliance", {
        "level": PLAIN["level"], "algorithm": ("Algorithm", None), "n_runs": ("Runs (count)", COUNT_FORMAT),
        "n_clusters": PLAIN["n_clusters"],
        "sat_served_mean": ("Satisfaction of Served EVs, Mean (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "sat_served_ci_low": (f"Satisfaction of Served EVs, {CI} Lower Bound", PCT_FRACTION_FORMAT),
        "sat_served_status": ("Satisfaction > 90%, Served EVs: Status", None),
        "sat_all_arrivals_mean": ("Satisfaction Counting Rejected Arrivals, Mean (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "sat_all_arrivals_ci_low": (f"Satisfaction Counting Rejected Arrivals, {CI} Lower Bound", PCT_FRACTION_FORMAT),
        "sat_all_arrivals_status": ("Satisfaction > 90%, Counting Rejected Arrivals: Status", None),
        "ens_rel_served_pct": ("Energy Not Served vs. AFAP, Served EVs, Mean (% already scaled)", '#,##0.00"%"'),
        "ens_rel_served_ci_high_pct": (f"Energy Not Served vs. AFAP, {CI} Upper Bound (% already scaled)", '#,##0.00"%"'),
        "ens_rel_served_status": ("Energy Target < 15%, ENS_rel on Served EVs: Status", None),
        "dns_lower_mean": ("Demand Not Served, Lower Bound, Mean (fraction, 0 to 1)", PCT_FRACTION_FORMAT),
        "dns_lower_ci_high": (f"Demand Not Served, {CI} Upper Bound", PCT_FRACTION_FORMAT),
        "dns_status": ("Energy Target < 15%, on Demand Not Served: Status", None),
        "cells_with_overload": ("Runs with Any Transformer Overload (count of 100)", COUNT_FORMAT),
        "overload_kwh_mean": ("Transformer Overload, Mean (kWh per day)", KWH_FORMAT),
        "transformer_status": ("Transformer Within Rating in Every Run: Status", None),
        "peak_kw_p95": ("95th-Percentile Per-Seed Peak Station Power (kW)", KWH_FORMAT),
        "peak_kw_p95_ci_high": (f"95th-Percentile Peak, {CI} Upper Bound (kW)", KWH_FORMAT),
        "voltage_status": ("Voltage +/-5% (RETIE): Status", None), "voltage_reason": ("Voltage: Reason", None),
        "note": ("Note", None)})


if __name__ == "__main__":
    main()
