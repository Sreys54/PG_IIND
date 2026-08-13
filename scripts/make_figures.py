"""
Week 2+ figure module (Deliverable 4). Reads results/master_results.csv
fresh and regenerates every figure from scratch on each invocation -- no
manual step, no possibility of a stale figure. Matplotlib only, no seaborn.

Run: PYTHONPATH=. python scripts/make_figures.py
"""
import csv
import datetime
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

from ev2gym_thesis.figures import (
    FIGURES_DIR, ALGORITHM_STYLE, style_for, write_caption, assert_total_reward_comparable,
)
from ev2gym_thesis.stats_utils import mean_ci, paired_bootstrap_ci
from ev2gym_thesis.registry_analysis import load_registry, main_grid_rows
from ev2gym_thesis.config_utils import make_day_config
from ev2gym_thesis.eval_protocol import REFERENCE_DAY

REFERENCE_CONFIG = "station_v0_bogota"
REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
REFERENCE_SEED = 0  # documented choice: EVAL_DAYS/REFERENCE_DAY exists precisely so
                     # single-day figures don't try to overlay 50 runs; seed=0 is
                     # simply the first of the 5 seeds, not a cherry-pick.
TIMESERIES_DIR = "results/timeseries"
_ref_year, _ref_month, _ref_day = REFERENCE_DAY
REFERENCE_DAY_STR = f"{_ref_year:04d}-{_ref_month:02d}-{_ref_day:02d}"

METRICS_FOR_BARS = [
    "total_ev_served", "total_energy_charged", "total_transformer_overload",
    "average_user_satisfaction", "total_profits",
]
METRIC_LABELS = {
    "total_ev_served": "EVs served",
    "total_energy_charged": "Energy charged (kWh)",
    "total_transformer_overload": "Transformer overload (kWh)",
    "average_user_satisfaction": "Avg. user satisfaction",
    "total_profits": "Profits",
}
HEADLINE_METRIC = "total_transformer_overload"  # the Week 1 headline finding

ALGO_ORDER = list(ALGORITHM_STYLE.keys())


def _algos_present(rows):
    present = {r["algorithm"] for r in rows}
    return [a for a in ALGO_ORDER if a in present]


def _values_for(rows, algorithm, metric):
    return np.array([r[metric] for r in rows if r["algorithm"] == algorithm and r[metric] is not None])


# ---------------------------------------------------------------------------
# f01_power_profile
# ---------------------------------------------------------------------------
def make_f01_power_profile(rows):
    grid = [r for r in main_grid_rows(rows, REFERENCE_CONFIG)
            if r["eval_day"] == REFERENCE_DAY_STR and int(r["seed"]) == REFERENCE_SEED]
    algos = _algos_present(grid)
    transformer_kw = grid[0]["transformer_kw"] if grid else 100.0

    fig, ax = plt.subplots(figsize=(9, 4.5))
    n_steps = None
    for algo in algos:
        run_id = f"{REFERENCE_CONFIG}__{algo}__seed{REFERENCE_SEED}__{REFERENCE_DAY_STR}"
        npz_path = f"{TIMESERIES_DIR}/{run_id}.npz"
        if not os.path.exists(npz_path):
            print(f"f01: missing timeseries {npz_path}, skipping {algo}")
            continue
        data = np.load(npz_path)
        power = data["station_power"]
        n_steps = len(power)
        t_hours = 5 + np.arange(n_steps) * 15 / 60.0  # config: hour=5, timescale=15min
        sty = style_for(algo)
        ax.plot(t_hours, power, color=sty["color"], marker=None, label=sty["label"], linewidth=1.5)
        ax.fill_between(t_hours, power, transformer_kw, where=(power > transformer_kw),
                         color=sty["color"], alpha=0.25, interpolate=True)

    ax.axhline(transformer_kw, color="black", linestyle="--", linewidth=1,
                label=f"Transformer limit ({transformer_kw:.0f} kW)")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Station power (kW)")
    ax.set_title(f"Aggregate station power, reference day {REFERENCE_DAY_STR}\n"
                 f"({REFERENCE_CONFIG}, seed={REFERENCE_SEED})", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()

    _save(fig, "f01_power_profile")
    write_caption(
        "f01_power_profile",
        what_it_shows=(
            "Aggregate station power (kW) over the reference evaluation day, one line "
            "per algorithm, with the transformer power limit as a dashed horizontal "
            "line and shaded fill where the limit is exceeded."
        ),
        n_runs=len(algos),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in algos],
        extra=(
            f"Single-day profile: seed={REFERENCE_SEED} only (not averaged across the "
            f"5-seed grid), per eval_protocol.REFERENCE_DAY={REFERENCE_DAY_STR} -- "
            f"this is the figure REFERENCE_DAY exists for, per its own docstring."
        ),
    )


# ---------------------------------------------------------------------------
# f02_metrics_bars
# ---------------------------------------------------------------------------
def _reference_day_energy_requested(algo_cls=ChargeAsFastAsPossible, seed=REFERENCE_SEED):
    """Total energy requested by all arriving EVs (kWh) on the reference day,
    one live run. Used as the 'energy requested' upper-bound reference line
    on f02, per the Gurobi-policy free-bounds rule. Computed via a live run
    (not stored in the registry) since it isn't one of env.step()'s stats."""
    year, month, day = REFERENCE_DAY
    day_config_path = make_day_config(REFERENCE_CONFIG_PATH, year, month, day,
                                       "experiments/phase1_baseline/configs/_tmp_day_configs")
    env = EV2Gym(config_file=day_config_path, seed=seed, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=seed)
    agent = algo_cls()
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break
    total_requested = sum(ev.desired_capacity - ev.battery_capacity_at_arrival for ev in env.EVs)
    return total_requested


def make_f02_metrics_bars(rows):
    grid = main_grid_rows(rows, REFERENCE_CONFIG)
    algos = _algos_present(grid)

    fig, axes = plt.subplots(1, len(METRICS_FOR_BARS), figsize=(4 * len(METRICS_FOR_BARS), 4.2))
    energy_requested = _reference_day_energy_requested()

    for ax, metric in zip(axes, METRICS_FOR_BARS):
        assert_total_reward_comparable(grid, metric)
        means, los, his, colors, labels = [], [], [], [], []
        for algo in algos:
            values = _values_for(grid, algo, metric)
            m, lo, hi = mean_ci(values)
            means.append(m)
            los.append(m - lo)
            his.append(hi - m)
            colors.append(style_for(algo)["color"])
            labels.append(style_for(algo)["label"])
        x = np.arange(len(algos))
        ax.bar(x, means, color=colors, yerr=[los, his], capsize=4)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(METRIC_LABELS[metric], fontsize=9)
        if metric == "total_energy_charged":
            ax.axhline(energy_requested, color="black", linestyle="--", linewidth=1)
            ax.text(0.02, 0.98, "total energy\nrequested (bound)", transform=ax.transAxes,
                    fontsize=6, va="top")

    fig.suptitle(f"{REFERENCE_CONFIG}: metrics across the 5-seed x 10-day evaluation grid, "
                 f"mean +/- 95% CI (n={len(grid)//max(len(algos),1)} per algorithm)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, "f02_metrics_bars")
    write_caption(
        "f02_metrics_bars",
        what_it_shows=(
            "Grouped bars with 95% CI error bars across algorithms for total_ev_served, "
            "total_energy_charged, total_transformer_overload, average_user_satisfaction, "
            "and total_profits. The energy-charged panel additionally shows the total "
            "energy requested by arriving EVs as a dashed upper-bound reference line "
            "(computed from ONE live reference-day run, seed=0 -- a proxy, not an "
            "average over all 100 runs)."
        ),
        n_runs=len(grid),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in algos],
    )


# ---------------------------------------------------------------------------
# f03_tradeoff_pareto
# ---------------------------------------------------------------------------
def make_f03_tradeoff_pareto(rows):
    grid = main_grid_rows(rows, REFERENCE_CONFIG)
    algos = _algos_present(grid)

    points = {}
    for algo in algos:
        sat = _values_for(grid, algo, "average_user_satisfaction")
        overload = _values_for(grid, algo, "total_transformer_overload")
        sm, slo, shi = mean_ci(sat)
        om, olo, ohi = mean_ci(overload)
        points[algo] = {"sat": sm, "sat_err": (sm - slo, shi - sm),
                         "overload": om, "overload_err": (om - olo, ohi - om)}

    # non-dominated: maximize sat, minimize overload
    non_dominated = []
    for a in algos:
        dominated = False
        for b in algos:
            if b == a:
                continue
            if points[b]["sat"] >= points[a]["sat"] and points[b]["overload"] <= points[a]["overload"] and \
               (points[b]["sat"] > points[a]["sat"] or points[b]["overload"] < points[a]["overload"]):
                dominated = True
                break
        if not dominated:
            non_dominated.append(a)

    fig, ax = plt.subplots(figsize=(6, 5))
    for algo in algos:
        p = points[algo]
        sty = style_for(algo)
        edge = "black" if algo in non_dominated else "none"
        ax.errorbar(p["sat"], p["overload"],
                    xerr=[[p["sat_err"][0]], [p["sat_err"][1]]],
                    yerr=[[p["overload_err"][0]], [p["overload_err"][1]]],
                    fmt=sty["marker"], color=sty["color"], markersize=10,
                    markeredgecolor=edge, markeredgewidth=2, capsize=4, label=sty["label"])

    if len(non_dominated) > 1:
        nd_sorted = sorted(non_dominated, key=lambda a: points[a]["sat"])
        ax.plot([points[a]["sat"] for a in nd_sorted], [points[a]["overload"] for a in nd_sorted],
                color="gray", linestyle=":", linewidth=1, zorder=0)

    ax.set_xlabel("Average user satisfaction")
    ax.set_ylabel("Transformer overload (kWh)")
    ax.set_title(f"{REFERENCE_CONFIG}: satisfaction vs. overload trade-off\n"
                 "(black edge = non-dominated, mean +/- 95% CI both axes)", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    _save(fig, "f03_tradeoff_pareto")
    write_caption(
        "f03_tradeoff_pareto",
        what_it_shows=(
            "Scatter of mean user satisfaction (x) vs. mean transformer overload (y), "
            "one point per algorithm with 95% CI error bars on both axes. Non-dominated "
            "points (black edge) are connected."
        ),
        n_runs=len(grid),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in algos],
    )


# ---------------------------------------------------------------------------
# f04_distributions
# ---------------------------------------------------------------------------
def make_f04_distributions(rows):
    grid = main_grid_rows(rows, REFERENCE_CONFIG)
    algos = _algos_present(grid)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    data = [_values_for(grid, algo, HEADLINE_METRIC) for algo in algos]
    colors = [style_for(a)["color"] for a in algos]
    labels = [style_for(a)["label"] for a in algos]

    bp = ax.boxplot(data, patch_artist=True, tick_labels=labels, showmeans=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)

    ax.set_ylabel(METRIC_LABELS[HEADLINE_METRIC])
    ax.set_title(f"{REFERENCE_CONFIG}: {METRIC_LABELS[HEADLINE_METRIC]} distribution\n"
                 f"across all {len(grid)//max(len(algos),1)} runs per algorithm (5 seeds x 10 days)", fontsize=10)
    fig.tight_layout()
    _save(fig, "f04_distributions")
    write_caption(
        "f04_distributions",
        what_it_shows=(
            f"Box plot of {METRIC_LABELS[HEADLINE_METRIC]} per algorithm over every run "
            "in the 5-seed x 10-day grid, showing run-to-run variance directly instead "
            "of hiding it behind a mean."
        ),
        n_runs=len(grid),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in algos],
    )


# ---------------------------------------------------------------------------
# f05_vs_baseline
# ---------------------------------------------------------------------------
def make_f05_vs_baseline(rows):
    grid = main_grid_rows(rows, REFERENCE_CONFIG)
    algos = _algos_present(grid)
    if "ChargeAsFastAsPossible" not in algos:
        print("f05: no AFAP rows found, skipping (AFAP is the baseline).")
        return
    other_algos = [a for a in algos if a != "ChargeAsFastAsPossible"]
    if not other_algos:
        print("f05: no non-baseline algorithm rows found, skipping.")
        return

    # Pair by (seed, eval_day) cell.
    def cell_key(r):
        return (r["seed"], r["eval_day"])

    afap_by_cell = {cell_key(r): r for r in grid if r["algorithm"] == "ChargeAsFastAsPossible"}
    show_algo_suffix = len(other_algos) > 1  # redundant with color when there's only one

    fig, ax = plt.subplots(figsize=(10, 0.7 * len(METRICS_FOR_BARS) * len(other_algos) + 1.5))
    y_labels = []
    y_pos = []
    y = 0
    for algo in other_algos:
        other_by_cell = {cell_key(r): r for r in grid if r["algorithm"] == algo}
        common_cells = sorted(set(afap_by_cell) & set(other_by_cell))
        for metric in METRICS_FOR_BARS:
            assert_total_reward_comparable(
                [afap_by_cell[c] for c in common_cells] + [other_by_cell[c] for c in common_cells], metric)
            afap_vals = np.array([afap_by_cell[c][metric] for c in common_cells])
            other_vals = np.array([other_by_cell[c][metric] for c in common_cells])
            # skip pct statistic where AFAP value could be 0 (division by zero)
            if np.any(afap_vals == 0):
                result = paired_bootstrap_ci(afap_vals, other_vals, n_bootstrap=5000, seed=0, statistic="diff")
                unit = " (abs. diff)"
            else:
                result = paired_bootstrap_ci(afap_vals, other_vals, n_bootstrap=5000, seed=0, statistic="pct")
                unit = " (%)"
            sty = style_for(algo)
            ax.errorbar(result["point_estimate"], y,
                        xerr=[[result["point_estimate"] - result["ci_low"]],
                              [result["ci_high"] - result["point_estimate"]]],
                        fmt=sty["marker"], color=sty["color"], capsize=4, markersize=8)
            label = f"{METRIC_LABELS[metric]}{unit}"
            if show_algo_suffix:
                label += f" ({sty['label']})"
            y_labels.append(label)
            y_pos.append(y)
            y += 1

    ax.axvline(0, color="black", linestyle="-", linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(y_labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Paired change vs. AFAP baseline")
    ax.set_title(f"{REFERENCE_CONFIG}: paired change vs. AFAP baseline\n"
                 f"({', '.join(style_for(a)['label'] for a in other_algos)}, bootstrap 95% CI)", fontsize=10)
    fig.subplots_adjust(left=0.42, right=0.95, top=0.85, bottom=0.15)
    _save(fig, "f05_vs_baseline")
    write_caption(
        "f05_vs_baseline",
        what_it_shows=(
            "Paired percentage (or absolute, where the AFAP baseline is exactly 0) "
            "change relative to the AFAP baseline for each metric, computed with a "
            "paired bootstrap matched by (seed, eval_day) cell -- not independent-sample "
            "means, since every algorithm is evaluated on the identical scenario grid. "
            "A vertical zero line marks 'no change'."
        ),
        n_runs=len(grid),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in algos],
    )


# ---------------------------------------------------------------------------
# f06_size_sensitivity
# ---------------------------------------------------------------------------
POLICY_A_CONFIGS = [("station_n02_tx100", 2), (REFERENCE_CONFIG, 8), ("station_n16_tx100", 16)]
POLICY_B_CONFIGS = [("station_n02_tx025", 2), (REFERENCE_CONFIG, 8), ("station_n16_tx200", 16)]


def make_f06_size_sensitivity(rows):
    algos = _algos_present(main_grid_rows(rows))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)

    for ax, (policy_name, policy_configs) in zip(
            axes, [("Policy A: fixed 100 kW transformer", POLICY_A_CONFIGS),
                   ("Policy B: transformer scaled to hold 4:1", POLICY_B_CONFIGS)]):
        for algo in algos:
            n_ports_list, means, los, his = [], [], [], []
            for config_name, n_ports in policy_configs:
                grid = main_grid_rows(rows, config_name)
                values = _values_for(grid, algo, HEADLINE_METRIC)
                if len(values) == 0:
                    continue
                m, lo, hi = mean_ci(values)
                n_ports_list.append(n_ports)
                means.append(m)
                los.append(m - lo)
                his.append(hi - m)
            sty = style_for(algo)
            ax.errorbar(n_ports_list, means, yerr=[los, his], fmt=sty["marker"] + "-",
                        color=sty["color"], label=sty["label"], capsize=4)
        ax.set_xlabel("Number of ports")
        ax.set_xticks([2, 8, 16])
        ax.set_title(policy_name, fontsize=9)

    axes[0].set_ylabel(METRIC_LABELS[HEADLINE_METRIC])
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Station-size sensitivity: {METRIC_LABELS[HEADLINE_METRIC]} vs. port count", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, "f06_size_sensitivity")

    configs_used = sorted({c for c, _ in POLICY_A_CONFIGS + POLICY_B_CONFIGS})
    write_caption(
        "f06_size_sensitivity",
        what_it_shows=(
            f"{METRIC_LABELS[HEADLINE_METRIC]} vs. number of ports (2/8/16), one line per "
            "algorithm, two panels for the two transformer policies (Policy A: fixed at "
            "100 kW; Policy B: scaled to hold the reference case's 4:1 oversubscription "
            "ratio constant). station_v0_bogota (n=8) is the shared middle point in both "
            "panels since it sits at both 100 kW and the 4:1 ratio simultaneously."
        ),
        n_runs=sum(len(main_grid_rows(rows, c)) for c in configs_used),
        configs=configs_used,
        algorithms=[style_for(a)["label"] for a in algos],
    )


# ---------------------------------------------------------------------------
# f07_metric_heatmap
# ---------------------------------------------------------------------------
# Metrics where a LOWER raw value is the better outcome. Every other metric
# in METRICS_FOR_BARS is "higher is better". Getting this backwards would
# color the worse algorithm green, which is worse than not coloring at all.
LOWER_IS_BETTER = {"total_transformer_overload"}


def make_f07_metric_heatmap(rows):
    grid = main_grid_rows(rows, REFERENCE_CONFIG)
    algos = _algos_present(grid)

    for metric in METRICS_FOR_BARS:
        assert_total_reward_comparable(grid, metric)

    raw = np.zeros((len(algos), len(METRICS_FOR_BARS)))
    for i, algo in enumerate(algos):
        for j, metric in enumerate(METRICS_FOR_BARS):
            raw[i, j] = np.mean(_values_for(grid, algo, metric))

    normalized = np.zeros_like(raw)
    for j, metric in enumerate(METRICS_FOR_BARS):
        col = raw[:, j]
        span = col.max() - col.min()
        norm_col = (col - col.min()) / span if span > 0 else np.full_like(col, 0.5)
        if metric in LOWER_IS_BETTER:
            norm_col = 1 - norm_col  # so green (1.0) always means "better", not just "higher raw number"
        normalized[:, j] = norm_col

    fig, ax = plt.subplots(figsize=(9.5, 2.2 + 0.6 * len(algos)))
    im = ax.imshow(normalized, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(METRICS_FOR_BARS)))
    xlabels = [METRIC_LABELS[m] + (" (lower better)" if m in LOWER_IS_BETTER else "")
               for m in METRICS_FOR_BARS]
    ax.set_xticklabels(xlabels, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(algos)))
    ax.set_yticklabels([style_for(a)["label"] for a in algos], fontsize=9)
    for i in range(len(algos)):
        for j in range(len(METRICS_FOR_BARS)):
            ax.text(j, i, f"{raw[i, j]:.2g}", ha="center", va="center", fontsize=8)
    ax.set_title(f"{REFERENCE_CONFIG}: algorithm x metric summary\n"
                 "(green = better within column, accounting for metric direction)", fontsize=10)
    cbar = fig.colorbar(im, ax=ax, fraction=0.06, pad=0.03)
    cbar.set_label("green = better\n(column-normalized, not absolute)", fontsize=8)
    fig.subplots_adjust(left=0.15, right=0.88, bottom=0.32, top=0.82)
    _save(fig, "f07_metric_heatmap")
    write_caption(
        "f07_metric_heatmap",
        what_it_shows=(
            "Algorithms (rows) x metrics (columns), color-normalized per column (min-max "
            "across algorithms) with direction corrected so green always means 'better "
            "performance', not just 'higher raw number' -- total_transformer_overload is "
            "inverted since lower is better there. Raw mean value annotated in each cell. "
            "A single-glance summary of the cumulative experiment history -- with only 2 "
            "algorithms so far, each column is necessarily 0/1; this becomes more "
            "informative as more algorithms are added in later weeks."
        ),
        n_runs=len(grid),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in algos],
    )


# ---------------------------------------------------------------------------
# f08_learning_curves (inert until RL rows exist)
# ---------------------------------------------------------------------------
def make_f08_learning_curves(rows):
    rl_rows = [r for r in rows if r["algorithm_family"] == "rl"]
    if not rl_rows:
        print("f08_learning_curves: no algorithm_family=='rl' rows in the registry yet "
              "-- skipping cleanly (inert until Week 3+ RL rows exist). Not an error.")
        return
    raise NotImplementedError(
        "RL rows now exist in the registry but f08_learning_curves plotting logic "
        "has not been implemented yet -- this needs reward-vs-steps time series data "
        "that isn't part of the current registry schema."
    )


# ---------------------------------------------------------------------------
# f09_degradation_by_ambient (built in the previous session; reads its own
# separate source file, results/degradation_by_ambient.csv, not the main
# registry -- see thesis_docs/chapters/00_lab_log.md for why they're separate)
# ---------------------------------------------------------------------------
DEGRADATION_PATH = "results/degradation_by_ambient.csv"
SCENARIO_ORDER = ["default", "bogota_outdoor", "bogota_outdoor_plus5", "bogota_underground"]
SCENARIO_LABELS = {
    "default": "Default\n(25C fixed)",
    "bogota_outdoor": "Bogota\noutdoor",
    "bogota_outdoor_plus5": "Bogota outdoor\n+5C charging",
    "bogota_underground": "Bogota\nunderground",
}


def make_f09_degradation_by_ambient():
    if not os.path.exists(DEGRADATION_PATH):
        print(f"f09: {DEGRADATION_PATH} not found -- run "
              f"scripts/measure_degradation_by_ambient.py --execute first. Skipping.")
        return

    with open(DEGRADATION_PATH, newline="") as f:
        deg_rows = list(csv.DictReader(f))

    algorithms = sorted({r["algorithm"] for r in deg_rows}, key=lambda a: ALGO_ORDER.index(a))
    configs = sorted({r["config_name"] for r in deg_rows})

    metrics = {
        "battery_degradation": defaultdict(list),
        "battery_degradation_calendar": defaultdict(list),
        "battery_degradation_cycling": defaultdict(list),
    }
    for r in deg_rows:
        key = (r["algorithm"], r["ambient_scenario"])
        cal = float(r["sum_d_cal"])
        cyc = float(r["sum_d_cyc_unchanged"])
        metrics["battery_degradation"][key].append(cal + cyc)
        metrics["battery_degradation_calendar"][key].append(cal)
        metrics["battery_degradation_cycling"][key].append(cyc)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    metric_titles = {
        "battery_degradation": "Total (calendar + cycling)",
        "battery_degradation_calendar": "Calendar aging",
        "battery_degradation_cycling": "Cycling aging (temperature-independent)",
    }
    n_scenarios = len(SCENARIO_ORDER)
    n_algos = len(algorithms)
    bar_width = 0.8 / n_algos
    x = np.arange(n_scenarios)

    for ax, (metric_key, title) in zip(axes, metric_titles.items()):
        for i, algo in enumerate(algorithms):
            sty = style_for(algo)
            means, los, his = [], [], []
            for scenario in SCENARIO_ORDER:
                values = metrics[metric_key].get((algo, scenario), [])
                m, lo, hi = mean_ci(values) if values else (0, 0, 0)
                means.append(m)
                los.append(m - lo)
                his.append(hi - m)
            offset = (i - (n_algos - 1) / 2) * bar_width
            ax.bar(x + offset, means, width=bar_width, color=sty["color"],
                   label=sty["label"], yerr=[los, his], capsize=3, error_kw={"linewidth": 1})
        ax.set_title(title, fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels([SCENARIO_LABELS[s] for s in SCENARIO_ORDER], fontsize=8)
        ax.set_ylabel("Capacity loss (dimensionless)", fontsize=9)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))

    axes[0].legend(fontsize=9, loc="upper right")
    fig.suptitle("Battery degradation by ambient scenario and algorithm\n"
                  "(station_v0_bogota, 5 seeds x 10 days, mean +/- 95% CI)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    _save(fig, "f09_degradation_by_ambient")

    n_runs = len(deg_rows) // len(SCENARIO_ORDER)
    write_caption(
        "f09_degradation_by_ambient",
        what_it_shows=(
            "Mean battery degradation (total, calendar-only, cycling-only) per algorithm "
            "and ambient scenario, with 95% confidence intervals across 5 seeds x 10 "
            "evaluation days. Cycling aging has no temperature dependence in the "
            "implemented model (verified by inspection) and is included as a visual "
            "confirmation that it does not shift across ambient scenarios."
        ),
        n_runs=n_runs,
        configs=configs,
        algorithms=[style_for(a)["label"] for a in algorithms],
        extra=(
            "Source data: results/degradation_by_ambient.csv (scope=reference: "
            "station_v0_bogota only, not the full 502-row registry). See "
            "thesis_docs/chapters/02_model_validation.md for the paired-bootstrap "
            "percentage-change measurement this figure's absolute values correspond to."
        ),
    )


def _save(fig, name):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig.savefig(f"{FIGURES_DIR}/{name}.png", dpi=300)
    fig.savefig(f"{FIGURES_DIR}/{name}.pdf")
    plt.close(fig)
    print(f"Wrote {FIGURES_DIR}/{name}.png, .pdf")


if __name__ == "__main__":
    rows = load_registry()
    print(f"Loaded {len(rows)} registry rows (smoke test excluded).")

    make_f01_power_profile(rows)
    make_f02_metrics_bars(rows)
    make_f03_tradeoff_pareto(rows)
    make_f04_distributions(rows)
    make_f05_vs_baseline(rows)
    make_f06_size_sensitivity(rows)
    make_f07_metric_heatmap(rows)
    make_f08_learning_curves(rows)
    make_f09_degradation_by_ambient()

    print("\nAll figures regenerated.")