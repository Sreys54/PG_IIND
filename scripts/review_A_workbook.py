"""
Week 8 advisor review: assemble results/review_A_post_processing.xlsx (one
sheet per Block A item) from the CSVs written by review_A_analyze.py,
review_A2_A3.py and review_A8_week1_sweep.py, plus the code-fact tables of
A4/A5/A6 (ev2gym_thesis/review_information.py and the facts below).
Every header is a unit-bearing label (CLAUDE.md rule 7).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from ev2gym_thesis.review_information import COLUMNS as INFO_COLUMNS, INFORMATION_TABLE
from ev2gym_thesis.review_labels import KW_FORMAT, sheet
from ev2gym_thesis.xlsx_export import COUNT_FORMAT, KWH_FORMAT, PCT_FRACTION_FORMAT, export_formatted_xlsx_sheets

D = "experiments/phase4_review/A"
OUT = "results/review_A_post_processing.xlsx"

TXT = None
FACT_LABELS = {"item": ("Item", TXT), "fact": ("Fact", TXT), "value": ("Value", TXT),
               "source": ("Source (file and line)", TXT)}

# doc:begin A4_facts
A4_FACTS = [
    ("checkpoint selection rule (Week 6 extended run)", "convergence over windows of 5 validations (50,000 steps): "
     "|mean(last 5) - mean(previous 5)| / |mean(previous 5)| < 2% and std(last 5)/|mean(last 5)| < 5% on 3 "
     "consecutive validations; primary checkpoint = best validation tracking_error at or after convergence",
     "ev2gym_thesis/rl/extended_training.py lines 92-97 (constants), 154-192 (convergence_index), 195-208 "
     "(select_primary_index)"),
    ("carried-model rule (Week 6)", "primary checkpoint of the seed with the best validation tracking_error -> "
     "TD3_vanilla_extended_ts102, 850,000 steps (validation tracking_error 40,377.9); adopted by the author "
     "2026-10-05", "results/week6_part0_final_model_selection.json"),
    ("training seeds (agent)", "100, 101, 102 (SB3 weight init, exploration noise); disjoint from SEEDS",
     "ev2gym_thesis/eval_protocol.py line 84; test_rl_infrastructure.test_train_seeds_disjoint_from_seeds"),
    ("test scenario seeds", "0-49 x {2022-01-17 weekday, 2022-03-05 weekend} = 100 cases",
     "ev2gym_thesis/eval_protocol.py lines 72, 105"),
    ("validation scenario seeds", "1,000,000-1,000,009 x {2022-01-31, 2022-03-12} = 20 cells",
     "ev2gym_thesis/rl/extended_training.py lines 73-86"),
    ("training scenarios", "a fresh unseeded EV2Gym scenario seed per episode, uniform in [0, 999,999] "
     "(np.random.randint at reset), with the 50 test seeds rejected by a guard; days cycle round-robin over 20 "
     "TRAIN_DAYS. EV2Gym's EV population depends only on (seed, weekday/weekend), so the date separates nothing; "
     "the seeds do: validation seeds >= 1,000,000 are unreachable, test seeds are rejected",
     "ev2gym_thesis/rl/extended_training.py lines 60-66, 211-243 (eval_seed_guard)"),
    ("disjointness proof (existing test)", "validation vs test seeds, validation vs training draws, validation days "
     "vs EVAL/TRAIN days: all empty intersections, asserted",
     "ev2gym_thesis/rl/extended_training.py disjointness_proof; "
     "ev2gym_thesis/tests/test_final_rl_model.py test_validation_training_evaluation_sets_disjoint"),
    ("budget in episodes", "60,000 steps = 625 simulated days; 850,000 = 8,854.2; 400,000 = 4,166.7; "
     "630,000 = 6,562.5 (96 steps per day)", "arithmetic"),
    ("checkpoints that exist", "every 10,000 steps; ts100 to 480k, ts101 to 660k, ts102 to 910k; 850k exists "
     "only for ts102 (rule-selected checkpoints: 400k, 630k, 850k)",
     "experiments/phase2_algorithms/models/TD3_vanilla_extended_ts*/checkpoints"),
    ("the 'fifteen TD3 checkpoints' (IV-C)", "TD3_vanilla_ts100-102 (Week 3, 60k), TD3_TrackingOnly_ts100-102 "
     "(Week 4 reward ablation, 60k), TD3_vanilla_extended_ts100-102 (rule-selected), "
     "TD3_vanilla_extended_last_ts100-102 (last), TD3_vanilla_new60k_ts100-102 (new run's 60k) = 5 x 3 = 15; "
     "all evaluated on the 100-case grid (master_results.csv)", "results/master_results.csv"),
    ("MDP: action", "8 continuous values in [0, 1], fraction of each port's pilot current (72 A at 400 V, "
     "3 phases = 49.88 kW); EV2Gym normalises a charger's actions to sum <= 1 per charger "
     "(one port per charger here)", "ev2gym/models/ev_charger.py lines 134-176"),
    ("MDP: episode", "96 steps of 15 min (05:00 to 05:00), gamma = 0.99", "station_v0_bogota.yaml; "
     "ev2gym_thesis/rl/config_rl.py line 67"),
    ("MDP: network and noise (Weeks 3-6)", "actor and critics [64, 64], lr 1e-3, tau 0.005, batch 256, buffer "
     "50,000, learning starts 500, exploration N(0, 0.1) in SB3's [-1, 1] policy space",
     "ev2gym_thesis/rl/config_rl.py lines 65-81"),
    ("MDP: reward", "SqTrError_TrPenalty_UserIncentives: -(min(setpoint, potential, rating) - power)^2 "
     "- 100 x overload kW - 1000 x sum over departing EVs (1 - s)", "ev2gym/rl_agent/reward.py lines 16-32"),
]

PUBLICPST = [  # (index, element, meaning, normalisation)
    (1, "t / T", "time of day (step over episode length)", "divided by T = 96"),
    (2, "power_setpoints[t]", "EV2Gym power setpoint for this step (kW)", "none (raw kW; VecNormalize standardises)"),
    (3, "current_power_usage[t-1]", "station power in the previous step (kW)", "none (raw kW)"),
] + [(4 + 3 * p + k, f"port {p + 1}: " + n, m, z) for p in range(8) for k, (n, m, z) in enumerate([
    ("full flag", "1 if the EV's SoC is 1, 0.5 if connected and not full, 0 if empty", "categorical"),
    ("energy exchanged", "kWh delivered to the connected EV so far (0 if empty)", "none (raw kWh)"),
    ("steps connected", "current step - arrival step (0 if empty)", "none (raw steps)")])]
# doc:end A4_facts

A5_FACTS = [
    ("MPC_TrackingG2V origin", "this project's code (not the library, not the companion repo); subclasses the "
     "abstract ev2gym/baselines/mpc/mpc.py MPC for its state reconstruction", "ev2gym_thesis/mpc/tracking_mpc.py lines 62-150"),
    ("MPC_TrackingG2V objective", "min sum_{i=0}^{H-1} (sum_ports u_i - setpoint_{t+i})^2, kW^2; no min() clamp", "tracking_mpc.py lines 129-134"),
    ("MPC_TrackingG2V constraints", "AU u <= bU (EV battery capacity and HARD departure-energy bounds from "
     "calculate_InequalityConstraints), 0 <= u <= UB (kW), transformer: sum u_i + loads + pv <= limit (kW); "
     "H = 10 steps", "tracking_mpc.py lines 106-124"),
    ("MPC_TrackingG2V infeasible", "returns zeros (prints INFEASIBLE)", "tracking_mpc.py lines 141-143"),
    ("MPC_EnergyMaxG2V", "ev2gym eMPC_G2V unmodified, with ch_prices overwritten by a flat 1.0: it MINIMISES "
     "sum price x energy = energy subject to the hard departure-energy constraints, i.e. it delivers the least "
     "energy that meets every departure, not the most", "ev2gym_thesis/mpc/energy_max_mpc.py; ev2gym/baselines/mpc/eMPC.py line 259 (f @ u, minimised)"),
    ("prices in control decisions", "none: MPC-E's prices are a flat constant (no Dutch ENTSO-E price), and "
     "generate_power_setpoints uses prices = np.ones since 2026-09-08", "ev2gym/utilities/utils.py line 694 (commit b06c4af)"),
    ("'+3.1 COP/day' of MPC-E over AFAP", "mean +0.0053 kWh/day (x 584.24 COP/kWh = 3.11 COP/day); per case "
     "between -0.020 and +0.024 kWh; higher in 67 of 100 cases, lower in 33: solver tolerance, not a difference",
     "results/master_results.csv (computed 2026-11-03)"),
    ("oracles", "Optimal_Oracle_Tracking = ev2gym PowerTrackingErrorrMin on the replay of the whole day (one solve, "
     "full knowledge); Optimal_Oracle_Balanced = the same plus (desired - energy at departure)^2 penalty, weight 1",
     "ev2gym/baselines/gurobi_models/tracking_error.py; ev2gym_thesis/oracle/balanced_model.py"),
]


def facts_df(rows, cols=("item", "fact", "source")):
    return pd.DataFrame(rows, columns=list(cols))


def main():
    sheets = []
    a1 = pd.read_csv(f"{D}/A1_A7_service_and_dns.csv")
    sheets.append(sheet("A1_A7 service and DNS", a1))
    inv = pd.read_csv(f"{D}/A2_percentage_inventory.csv")
    sheets.append(sheet("A2 inventory", inv, {
        "file": ("Document", TXT), "line": ("Line", COUNT_FORMAT), "value_pct": ("Percentage as Written (%)", TXT),
        "metric_family": ("Metric Family (keyword classification)", TXT),
        "rule_today": ("How the Family Is Aggregated Today", TXT), "code": ("Code that Produced It", TXT),
        "context": ("Line Text (first 220 characters)", TXT)}))
    rec = pd.read_csv(f"{D}/A2_recomputed.csv")
    sheets.append(sheet("A2 recomputed", rec, {
        "metric": ("Energy Percentage", TXT),
        "mean_of_ratios": ("Mean of Per-Case Ratios (0-1 fraction)", PCT_FRACTION_FORMAT),
        "ratio_of_totals": ("Ratio of Totals, Adopted Rule (0-1 fraction)", PCT_FRACTION_FORMAT),
        "difference_points": ("Ratio of Totals minus Mean of Ratios (percentage points)", "0.000"),
        "changes_at_one_decimal": ("Rounded Value (one decimal, %) Changes", TXT)}))
    a3d = pd.read_csv(f"{D}/A3_offered_demand_1_6x.csv")
    sheets.append(sheet("A3 offered demand 1.6x", a3d, {
        "ports": ("Ports", COUNT_FORMAT), "transformer_kw": ("Transformer Rating (kW)", KW_FORMAT),
        "constant_demand": ("Labelled 'Constant Station Demand' (spawn x 8/ports)", TXT),
        "config_name": ("Config Name", TXT), "offered_kwh_lower": ("Offered Energy, Lower Bound (kWh per day)", KWH_FORMAT),
        "offered_kwh_upper": ("Offered Energy, Upper Bound (kWh per day)", KWH_FORMAT),
        "requested_served_kwh": ("Energy Requested by Served EVs (kWh per day)", KWH_FORMAT),
        "arrivals_served": ("EVs Served per Day (count)", KWH_FORMAT)}))
    a3t = pd.read_csv(f"{D}/A3_table_iv_consistency.csv")
    sheets.append(sheet("A3 table IV check", a3t, {
        "ports": ("Ports", COUNT_FORMAT), "transformer_kw": ("Transformer Rating (kW)", KW_FORMAT),
        "station_demand": ("Station Demand Label", TXT), "energy_kwh": ("Energy Delivered (kWh per day)", KWH_FORMAT),
        "margin_cop": ("Gross Energy Margin (COP per day)", "#,##0.00"),
        "margin_over_unit_margin_kwh": ("Margin / 584.24 COP per kWh (kWh per day)", KWH_FORMAT),
        "margin_check_rel_error": ("Relative Error, Margin vs Energy x (p - c) (0-1 fraction)", PCT_FRACTION_FORMAT),
        "offered_implied_by_dns_kwh": ("Offered Energy Implied by the Row's DNS, E / (1 - DNS) (kWh per day)", KWH_FORMAT),
        "dns_if_offered_911_kwh": ("DNS if Offered Energy Were 910.7 kWh (0-1 fraction)", PCT_FRACTION_FORMAT),
        "advisor_reading_dns_gap_points": ("Row DNS minus DNS at 910.7 kWh (percentage points)", "0.00")}))
    for name, f in [("A4 terms by arm", "A4_reward_terms_by_arm.csv"),
                    ("A4 later minus 60k", "A4_reward_terms_850k_minus_60k.csv"),
                    ("A4 posthoc vs TD3", "A4_posthoc_reward_vs_td3.csv")]:
        sheets.append(sheet(name, pd.read_csv(f"{D}/{f}"), {
            "train_seed": ("Training Seed", COUNT_FORMAT), "from": ("From Checkpoint (60k arm)", TXT),
            "to": ("To Checkpoint (arm)", TXT), "to_label": ("To Checkpoint (step)", TXT),
            "baseline": ("Arm Scored with TD3's Reward", TXT), "vs": ("Compared with", TXT),
            "reward_baseline_minus_td3": ("Reward per Day, Arm minus TD3 Final (positive = arm scores better)", KWH_FORMAT),
            "baseline_beats_td3_on_its_own_reward": ("Arm Beats TD3 Final on TD3's Own Reward (CI excludes 0)", TXT)}))
    tv = pd.read_csv(f"{D}/A4_td3_vs_random.csv")
    sheets.append(sheet("A4 TD3 vs Random", tv, {
        "metric": ("Table II Metric", TXT), "random": ("Random Policy (metric units)", "#,##0.0000"),
        "td3_final": ("TD3 Final, 850k (metric units)", "#,##0.0000"),
        "diff_td3_minus_random": ("Paired Difference, TD3 minus Random (metric units)", "#,##0.0000"),
        "ci_low": ("95% CI Lower Bound", "#,##0.0000"), "ci_high": ("95% CI Upper Bound", "#,##0.0000"),
        "significant": ("CI Excludes Zero", TXT)}))
    sheets.append(sheet("A4 facts", facts_df(A4_FACTS), FACT_LABELS))
    sheets.append(sheet("A4 PublicPST state", pd.DataFrame(PUBLICPST, columns=["index", "element", "meaning",
                                                                                 "normalisation"]),
                        {"index": ("State Index (1-27)", COUNT_FORMAT), "element": ("Element", TXT),
                         "meaning": ("Meaning", TXT), "normalisation": ("Normalisation in the State Function", TXT)}))
    sheets.append(sheet("A5 MPC facts", facts_df(A5_FACTS), FACT_LABELS))
    info = pd.DataFrame(INFORMATION_TABLE)[INFO_COLUMNS]
    sheets.append(sheet("A6 information", info, {
        "arm": ("Arm", TXT), "regimes": ("Regimes Where It Is Run", TXT),
        "connected_evs": ("Uses Connected EVs (occupancy)", TXT), "transformer_rating": ("Uses Transformer Rating", TXT),
        "requested_energy": ("Uses Requested / Remaining Energy", TXT), "departure_times": ("Uses Departure Times", TXT),
        "future_arrivals": ("Uses Future Arrivals (horizon)", TXT), "power_setpoint": ("Uses EV2Gym Power Setpoint", TXT),
        "code": ("Code (file and line)", TXT)}))
    a8 = pd.read_csv(f"{D}/A8_week1_transformer_sweep.csv")
    sheets.append(sheet("A8 week1 sweep", a8, {
        "set": ("Case Set (week1_seed42 = Week 1 single case; grid = 100-case grid)", TXT),
        "transformer_kw": ("Transformer Rating (kW)", KW_FORMAT), "n": ("Cases", COUNT_FORMAT),
        "overload_kwh_mean": ("AFAP Transformer Overload, Mean (kWh per day; EV2Gym value x 0.25 h)", KWH_FORMAT),
        "overload_ev2gym_kw_steps_mean": ("AFAP Overload as EV2Gym Reports It, Mean (kW summed over 15-min steps)", KWH_FORMAT),
        "days_with_overload": ("Days with Overload (count)", COUNT_FORMAT),
        "peak_kw_mean": ("AFAP Station Peak, Mean (kW)", KW_FORMAT), "peak_kw_max": ("AFAP Station Peak, Max (kW)", KW_FORMAT)}))
    if os.path.exists(f"{D}/A8_dc_peaks.csv"):
        sheets.append(sheet("A8 DC peaks", pd.read_csv(f"{D}/A8_dc_peaks.csv"), {
            "peak_kw_p95_over_cases": ("Station Peak, 95th Percentile over the 100 Days (kW)", KW_FORMAT),
            "peak_kw_max_over_cases": ("Station Peak, Maximum over the 100 Days (kW)", KW_FORMAT),
            "peak_kw_mean": ("Station Peak, Mean over Days (kW)", KW_FORMAT),
            "days_above_rating": ("Days with Any Step above the 100 kW Rating (count)", COUNT_FORMAT),
            "days_peak_above_100kw": ("Days with Peak above 100 kW (count)", COUNT_FORMAT)}))
    for extra_csv, name in [(f"{D}/A8_week2_outputs.csv", "A8 week2 outputs"), (f"{D}/A8_60kwh.csv", "A8 60 kWh")]:
        if os.path.exists(extra_csv):
            sheets.append(sheet(name, pd.read_csv(extra_csv), {
                "file": ("File", TXT), "line": ("Line", COUNT_FORMAT), "text": ("Text", TXT),
                "status": ("Status", TXT), "what": ("What It Holds", TXT), "number": ("Key Number", TXT)}))
    export_formatted_xlsx_sheets(OUT, sheets)


if __name__ == "__main__":
    main()
