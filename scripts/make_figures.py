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
from ev2gym_thesis.eval_protocol import REFERENCE_DAY, SEEDS, EVAL_DAYS

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
    "average_user_satisfaction", "gross_margin_cop",
]
METRIC_LABELS = {
    "total_ev_served": "EVs served",
    "total_energy_charged": "Energy charged (kWh)",
    "total_transformer_overload": "Transformer overload (kWh)",
    "average_user_satisfaction": "Avg. user satisfaction",
    # CORRECTED 2026-09-09 (Week 5 Gate review): this panel used to plot
    # EV2Gym's own `total_profits` labeled "Profits" -- that column is a
    # negated ENTSO-E-priced purchase cost, not a profit/revenue figure
    # (registry.py's total_profits_semantics doc comment). Replaced with
    # the Colombian-peso gross margin (results/economics_cop.csv). Per
    # 05_algorithm_comparison.md S5.1: gross margin is proportional to
    # energy delivered under this project's flat Colombian tariff and does
    # NOT discriminate between control strategies that respect the
    # transformer's rating and those that don't -- reported here for
    # Objective 1's revenue question, never used to rank algorithms.
    "gross_margin_cop": "Gross margin (COP/day)*",
}
HEADLINE_METRIC = "total_transformer_overload"  # the Week 1 headline finding

ALGO_ORDER = list(ALGORITHM_STYLE.keys())

# Week 4: the oracle is a bound, not a competitor
# (thesis_docs/chapters/04_oracle_and_pitd3.md S4.1) -- excluded from the
# comparative visuals below (bars/boxplot/pareto/heatmap), where mixing a
# perfect-information ceiling in as a peer row would invite exactly the
# misreading S4.1 warns against. It gets its own reference line/band in
# f10_optimality_gap instead, and still appears normally in f01 (a real
# power-dispatch curve, drawn dashed via ALGORITHM_STYLE's "linestyle").
ORACLE_ALGORITHMS = {"Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced"}


def _algos_present(rows, exclude_oracle: bool = False):
    present = {r["algorithm"] for r in rows}
    if exclude_oracle:
        present -= ORACLE_ALGORITHMS
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
        ax.plot(t_hours, power, color=sty["color"], marker=None, label=sty["label"], linewidth=1.5,
                linestyle=sty.get("linestyle", "-"))
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
    algos = _algos_present(grid, exclude_oracle=True)

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
        # Week 3: rotated (was horizontal) -- with 6 algorithms instead of 2,
        # horizontal labels overlapped into an illegible run-on string,
        # caught by this figure's own visual QA pass (Entregable 7).
        ax.set_xticklabels(labels, fontsize=7, rotation=35, ha="right")
        ax.set_title(METRIC_LABELS[metric], fontsize=9)
        if metric == "total_energy_charged":
            ax.axhline(energy_requested, color="black", linestyle="--", linewidth=1)
            ax.text(0.02, 0.98, "total energy\nrequested (bound)", transform=ax.transAxes,
                    fontsize=6, va="top")

    # Week 4 bug, caught by this figure's own visual QA pass (Entregable 9):
    # len(grid)//len(algos) divided ALL grid rows (including the 100 oracle
    # rows, excluded from `algos` but still counted in `grid`) by only the
    # plotted algorithm count, printing "n=61" instead of the true 50 -- a
    # silent regression the moment a figure started excluding some algorithms
    # from the plot while `grid` kept every row. Fixed by counting only rows
    # for algorithms actually plotted.
    n_per_algo = sum(1 for r in grid if r["algorithm"] in algos) // max(len(algos), 1)
    # CORRECTED 2026-09-09 (Week 5 Gate 4): was a hardcoded "5-seed x
    # 10-day" string, stale since the grid was rebuilt to
    # len(SEEDS) seeds x len(EVAL_DAYS) day types -- computed from the
    # actual eval_protocol constants so this can't drift again.
    fig.suptitle(f"{REFERENCE_CONFIG}: metrics across the {len(SEEDS)}-seed x "
                 f"{len(EVAL_DAYS)}-day-type evaluation grid, "
                 f"mean +/- 95% CI (n={n_per_algo} per algorithm)", fontsize=10)
    fig.text(0.5, 0.01, "* Gross margin does not discriminate control quality under this "
             "project's flat Colombian tariff -- reported for Objective 1's revenue "
             "question only, never used to rank algorithms (05_algorithm_comparison.md S5.1).",
             ha="center", fontsize=7, style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 0.93])
    _save(fig, "f02_metrics_bars")
    write_caption(
        "f02_metrics_bars",
        what_it_shows=(
            "Grouped bars with 95% CI error bars across algorithms for total_ev_served, "
            "total_energy_charged, total_transformer_overload, average_user_satisfaction, "
            "and gross_margin_cop (Colombian-peso economics, results/economics_cop.csv -- "
            "NOT EV2Gym's own total_profits column, which is a negated ENTSO-E-priced "
            "purchase cost, not a profit figure; see registry.py's total_profits_semantics "
            "doc comment). Gross margin does not discriminate control quality under this "
            "project's flat Colombian tariff (05_algorithm_comparison.md S5.1) -- reported "
            "for Objective 1's revenue question, never used to rank algorithms. The "
            "energy-charged panel additionally shows the total energy requested by "
            "arriving EVs as a dashed upper-bound reference line (computed from ONE live "
            "reference-day run, seed=0 -- a proxy, not an average over all runs)."
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
    algos = _algos_present(grid, exclude_oracle=True)

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
    algos = _algos_present(grid, exclude_oracle=True)

    # Week 3: figure width now scales with algorithm count (was a fixed 6in
    # -- fine for 2 algorithms, cramped and label-overlapping once RL added
    # 4 more; caught by this figure's own visual QA pass, Entregable 7).
    fig, ax = plt.subplots(figsize=(max(6, 1.3 * len(algos)), 4.5))
    data = [_values_for(grid, algo, HEADLINE_METRIC) for algo in algos]
    colors = [style_for(a)["color"] for a in algos]
    labels = [style_for(a)["label"] for a in algos]

    bp = ax.boxplot(data, patch_artist=True, tick_labels=labels, showmeans=True)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    ax.tick_params(axis="x", labelrotation=35)
    for label in ax.get_xticklabels():
        label.set_ha("right")

    # Same n-count fix as f02 (Week 4, Entregable 9 visual QA) -- count only
    # rows for algorithms actually plotted, not every row in `grid`.
    n_per_algo = sum(1 for r in grid if r["algorithm"] in algos) // max(len(algos), 1)
    ax.set_ylabel(METRIC_LABELS[HEADLINE_METRIC])
    ax.set_title(f"{REFERENCE_CONFIG}: {METRIC_LABELS[HEADLINE_METRIC]} distribution\n"
                 f"across all {n_per_algo} runs per algorithm "
                 f"({len(SEEDS)} seeds x {len(EVAL_DAYS)} day types)", fontsize=10)
    fig.tight_layout()
    _save(fig, "f04_distributions")
    write_caption(
        "f04_distributions",
        what_it_shows=(
            f"Box plot of {METRIC_LABELS[HEADLINE_METRIC]} per algorithm over every run "
            f"in the {len(SEEDS)}-seed x {len(EVAL_DAYS)}-day-type grid, showing "
            "run-to-run variance directly instead of hiding it behind a mean."
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
    # Oracle excluded: it isn't a "paired change vs. AFAP" competitor claim
    # this figure is designed to make (thesis_docs/chapters/04_oracle_and_pitd3.md
    # S4.1) -- its distance from every online algorithm is f10's job instead.
    algos = _algos_present(grid, exclude_oracle=True)
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

    fig_height = 0.7 * len(METRICS_FOR_BARS) * len(other_algos) + 1.5
    fig, ax = plt.subplots(figsize=(10, fig_height))
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
    # Week 3: title no longer enumerates every non-baseline algorithm by
    # name -- with 5 algorithms (was 1, Round Robin, in Week 2) that list
    # ran wider than the fixed-width figure and got clipped at the right
    # edge (caught by this figure's own visual QA, Entregable 7). The
    # per-row y-axis labels already carry "(algorithm)" whenever
    # show_algo_suffix is True, so the title doesn't need to repeat it.
    ax.set_title(f"{REFERENCE_CONFIG}: paired change vs. AFAP baseline\n"
                 f"(bootstrap 95% CI, algorithm shown per row)", fontsize=10)
    # Week 3: fixed INCH margins (not fractions) for title/xlabel space --
    # a fixed *fraction* (e.g. 0.15) of a figure that now grows much taller
    # with more algorithms leaves an ever-growing absolute blank margin;
    # also caught by visual QA.
    top_margin_in, bottom_margin_in = 0.7, 0.6
    # Week 4 bug, caught by this figure's own visual QA pass (Entregable 9):
    # `left` was ALSO a fixed fraction (0.42) of a fixed 10in-wide figure --
    # sized for Week 3's longest label ("... (TD3 (seed 100))"). Week 4's
    # "TD3-TrackingOnly (seed 10X)" labels are longer and no longer fit in
    # that same fixed margin, clipping the first few characters off the left
    # edge of the saved PNG. Fixed the same way the top/bottom margins were
    # fixed in Week 3: measure the actual rendered label width and convert
    # to a fraction of THIS figure's width, instead of assuming a constant.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    max_label_width_in = max(
        lbl.get_window_extent(renderer=renderer).width for lbl in ax.get_yticklabels()
    ) / fig.dpi
    left_margin_in = max_label_width_in + 0.15
    fig.subplots_adjust(left=left_margin_in / fig.get_figwidth(), right=0.95,
                         top=1 - top_margin_in / fig_height,
                         bottom=bottom_margin_in / fig_height)
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
    # Week 3: restricted to algorithms actually run across the port-count
    # sweep (checked via presence on a non-reference sweep config), not
    # every algorithm in the whole registry. TD3/RandomPolicy only ran on
    # the 8-port reference config (declared Week 3 scope limitation -- the
    # CPU budget didn't cover training across the size sweep too, see
    # thesis_docs/chapters/03_rl_baseline.md), so without this filter they
    # showed up as disconnected single dots at n=8 with no actual
    # sensitivity trend to show -- misleading in a figure whose whole point
    # is the trend across sizes. Caught by this figure's own visual QA
    # (Entregable 7).
    non_reference_sweep_config = POLICY_A_CONFIGS[0][0]  # station_n02_tx100
    swept_grid = main_grid_rows(rows, non_reference_sweep_config)
    algos = [a for a in _algos_present(main_grid_rows(rows)) if _values_for(swept_grid, a, HEADLINE_METRIC).size > 0]
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
    algos = _algos_present(grid, exclude_oracle=True)

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
    # Week 4 bug, caught by this figure's own visual QA pass (Entregable 9):
    # `left=0.15` was a fixed fraction sized for Week 3's longest row label
    # ("TD3 (seed 100)"). Week 4's "TD3-TrackingOnly (seed 10X)" labels are
    # longer and got clipped at the left edge ("...ckingOnly (seed 100)").
    # Same fix as f05_vs_baseline: measure the actual rendered label width.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    max_label_width_in = max(
        lbl.get_window_extent(renderer=renderer).width for lbl in ax.get_yticklabels()
    ) / fig.dpi
    left_margin_in = max_label_width_in + 0.15
    fig.subplots_adjust(left=left_margin_in / fig.get_figwidth(), right=0.88, bottom=0.32, top=0.82)
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
# f08_learning_curves (activated Week 3: reads each training run's own
# learning_curve.csv -- like f09 reads its own separate source file, this
# is NOT registry data; the registry has no reward-vs-timesteps time series
# column, only per-run final stats). Extended Week 4: TD3_TrackingOnly gets
# its own panel, not a shared axis with vanilla -- the two arms train under
# DIFFERENT reward functions (SquaredTrackingErrorReward vs.
# SqTrError_TrPenalty_UserIncentives), so their episode-reward magnitudes
# are not on a common scale. Plotting them on one shared axis would be the
# assert_total_reward_comparable mistake in figure form.
# ---------------------------------------------------------------------------
LEARNING_CURVE_ARMS = [
    ("TD3 vanilla", ["TD3_vanilla_ts100", "TD3_vanilla_ts101", "TD3_vanilla_ts102"]),
    ("TD3-TrackingOnly", ["TD3_TrackingOnly_ts100", "TD3_TrackingOnly_ts101", "TD3_TrackingOnly_ts102"]),
]
LEARNING_CURVE_PATH_TEMPLATE = "experiments/phase2_algorithms/models/{algo}/learning_curve.csv"


def _load_learning_curve(algo):
    path = LEARNING_CURVE_PATH_TEMPLATE.format(algo=algo)
    if not os.path.exists(path):
        return None
    with open(path, newline="") as f:
        curve_rows = list(csv.DictReader(f))
    return {
        "timesteps": np.array([float(r["timesteps"]) for r in curve_rows]),
        "mean_episode_reward": np.array([float(r["mean_episode_reward"]) for r in curve_rows]),
    }


def _load_extended_learning_curves():
    """{train_seed: {"timesteps", "mean_episode_reward"}} for the Week 6
    Part 0 extended run: rolling mean of the raw episode reward over the
    last <=100 completed episodes -- LearningCurveCallback's statistic."""
    import pandas as pd
    out = {}
    for s in (100, 101, 102):
        path = f"experiments/phase2_algorithms/results/week6_part0/TD3_vanilla_extended_ts{s}_episodes.csv"
        if os.path.exists(path):
            e = pd.read_csv(path)
            out[s] = {"timesteps": e.timesteps_at_end.to_numpy(),
                      "mean_episode_reward": e.episode_reward_raw.rolling(100, min_periods=1).mean().to_numpy()}
    return out


def make_f08_learning_curves(rows):
    rl_rows = [r for r in rows if r["algorithm_family"] == "rl"]
    if not rl_rows:
        print("f08_learning_curves: no algorithm_family=='rl' rows in the registry yet "
              "-- skipping cleanly (inert until Week 3+ RL rows exist). Not an error.")
        return

    arm_curves = {}
    for arm_label, algos in LEARNING_CURVE_ARMS:
        curves = {a: _load_learning_curve(a) for a in algos}
        curves = {a: c for a, c in curves.items() if c is not None}
        if curves:
            arm_curves[arm_label] = curves
        else:
            print(f"f08: no learning_curve.csv files found for arm {arm_label!r}, skipping that panel.")
    if not arm_curves:
        print("f08: no learning_curve.csv files found for any arm, skipping.")
        return

    # Week 6 Part 0: third panel for the extended TD3_vanilla run, same
    # statistic (mean raw episode reward over the last <=100 completed
    # episodes), computed from the run's per-episode log. It shares the
    # y-axis with the original vanilla panel (same reward function); the
    # TrackingOnly panel keeps its own scale (different reward function).
    extended = _load_extended_learning_curves()
    n_panels = len(arm_curves) + (1 if extended else 0)
    fig, axes = plt.subplots(1, n_panels, figsize=(6.5 * n_panels, 5.2), squeeze=False)
    axes = axes[0]
    for ax, (arm_label, curves) in zip(axes, arm_curves.items()):
        for algo, data in curves.items():
            sty = style_for(algo)
            ax.plot(data["timesteps"], data["mean_episode_reward"], color=sty["color"],
                    label=sty["label"], linewidth=1.3)
        ax.set_xlabel("Training timesteps")
        ax.set_title(f"{arm_label} (original runs, 60k steps)", fontsize=10)
        ax.legend(fontsize=8)
        _w6p0_kfmt(ax)
    if extended:
        ax = axes[-1]
        conv = _w6p0_convergence() if os.path.exists("results/week6_part0_convergence.csv") else {}
        for s, data in extended.items():
            sty = style_for(f"TD3_vanilla_extended_ts{s}")
            ax.plot(data["timesteps"], data["mean_episode_reward"], color=sty["color"], linewidth=1.3,
                    label=f"TD3 extended run (seed {s})")
            if s in conv and conv[s]["convergence_step"] != "not converged":
                ax.axvline(float(conv[s]["convergence_step"]), color=sty["color"], linestyle=":", linewidth=1.4)
        ax.axvline(W6P0_ORIGINAL_BUDGET, color="0.35", linestyle="--", linewidth=1, label="original 60k budget")
        from matplotlib.lines import Line2D
        h, l = ax.get_legend_handles_labels()
        h.append(Line2D([], [], color="0.3", linestyle=":", linewidth=1.4))
        l.append("convergence declared (seed colour)")
        ax.legend(h, l, fontsize=8)
        ax.set_xlabel("Training timesteps")
        ax.set_title("TD3 vanilla -- extended run (Week 6 Part 0, trained post-setpoint-fix)", fontsize=10)
        _w6p0_kfmt(ax)
        lo = min(axes[0].get_ylim()[0], ax.get_ylim()[0])
        hi = max(axes[0].get_ylim()[1], ax.get_ylim()[1])
        axes[0].set_ylim(lo, hi)
        ax.set_ylim(lo, hi)
    axes[0].set_ylabel("Mean episode reward\n(rolling window, last <=100 episodes)")
    fig.suptitle("Learning curves by arm -- TD3 vanilla panels share one y-axis (same reward); "
                 "TD3-TrackingOnly uses a different reward,\nNOT a common scale "
                 "(station_v0_bogota, TRAIN_DAYS round-robin)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    _save(fig, "f08_learning_curves")

    all_algos = [a for _, curves in arm_curves.items() for a in curves]
    all_algos += [f"TD3_vanilla_extended_ts{s}" for s in extended]
    write_caption(
        "f08_learning_curves",
        what_it_shows=(
            "Mean episode reward (SB3's own rolling window over the last <=100 "
            "completed episodes) vs. training timesteps, one line per training seed, "
            "in SEPARATE PANELS per arm -- vanilla TD3 (SqTrError_TrPenalty_UserIncentives) "
            "and TD3-TrackingOnly (SquaredTrackingErrorReward) train under different "
            "reward functions, so their episode-reward magnitudes are not comparable on "
            "one shared axis (the assert_total_reward_comparable rule, in figure form). "
            "Source: each run's own learning_curve.csv "
            "(ev2gym_thesis/rl/callbacks.py's LearningCurveCallback), NOT the main "
            "registry -- the registry has no reward-vs-timesteps time series column. "
            "Reward values use each arm's OWN training reward function, not any of "
            "metrics -- see thesis_docs/chapters/03_rl_baseline.md S3.4 for why those "
            "are not the same thing. Week 6 Part 0 adds a third panel: the extended "
            "TD3_vanilla run (480k/660k/910k steps), same statistic computed from its "
            "per-episode log (experiments/phase2_algorithms/results/week6_part0/*_episodes.csv), "
            "sharing the y-axis with the original vanilla panel because the reward "
            "function is identical. Dashed: original 60k budget; dotted: convergence "
            "declared by the validation rule. The extended run trained on the "
            "post-setpoint-fix environment, the original runs before it."
        ),
        n_runs=len(all_algos),
        configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in all_algos],
        extra=(
            "Seed-to-seed spread across each panel's 3 lines IS signal, not noise to "
            "average away -- see 00_lab_log.md's Week 3 Entregable 7 entry (vanilla) "
            "and Week 4's trackingonly_train_seed_dispersion.csv (TD3-TrackingOnly) "
            "for the cross-training-seed dispersion analysis this figure visualizes."
        ),
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


# ---------------------------------------------------------------------------
# f10_optimality_gap (Week 4): reads results/optimality_gap.csv and
# results/oracle_tiebreak_noise_floor.csv, both produced by
# scripts/analyze_week4_results.py -- NOT the main registry directly, same
# "figure reads its own analysis output" pattern as f09.
# ---------------------------------------------------------------------------
# CORRECTED 2026-09-09 (Week 5): was "results/optimality_gap.csv" /
# "results/oracle_tiebreak_noise_floor.csv" -- Week 4's own analysis
# output, computed on the pre-Gate-4 grid (11 algorithms, no MPC arms).
# f10 now reads the Week 5 grid's analysis (13 algorithms, including both
# MPC arms -- the arm this figure exists to show, per
# 05_algorithm_comparison.md S5.6). Week 4's own historical CSV/cited
# numbers in 04_oracle_and_pitd3.md are untouched -- this is a path
# change for the FIGURE only, not a rewrite of Week 4's own record.
OPTIMALITY_GAP_PATH = "results/week5_optimality_gap.csv"
NOISE_FLOOR_PATH = "results/week5_oracle_tiebreak_noise_floor.csv"
GAP_METRIC_LABELS = {
    "tracking_error": "Tracking error (gap vs. Optimal_Oracle_Tracking)",
    "average_user_satisfaction": "Avg. satisfaction (gap vs. Optimal_Oracle_Balanced)",
    "min_energy_user_satisfaction": "Min. energy satisfaction (gap vs. Optimal_Oracle_Balanced)",
}


def make_f10_optimality_gap():
    if not os.path.exists(OPTIMALITY_GAP_PATH) or not os.path.exists(NOISE_FLOOR_PATH):
        print(f"f10: {OPTIMALITY_GAP_PATH} or {NOISE_FLOOR_PATH} not found -- run "
              f"scripts/analyze_week4_results.py first. Skipping.")
        return

    # Both CSVs are written by analyze_week4_results.py with leading `#`
    # explanatory comment lines before the real header row -- csv.DictReader
    # would otherwise parse a comment line as the header (every field then
    # keyed under one bogus column name). Filter those out before parsing,
    # not after: filtering dict keys post-hoc can't fix a header that was
    # never correctly identified in the first place.
    with open(OPTIMALITY_GAP_PATH, newline="") as f:
        gap_rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    with open(NOISE_FLOOR_PATH, newline="") as f:
        floor_rows = {r["metric"]: r for r in csv.DictReader(line for line in f if not line.startswith("#"))}

    metrics = sorted({r["metric"] for r in gap_rows}, key=lambda m: list(GAP_METRIC_LABELS).index(m))
    fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 4.5))
    if len(metrics) == 1:
        axes = [axes]

    for ax, metric in zip(axes, metrics):
        rows_for_metric = [r for r in gap_rows if r["metric"] == metric]
        algos = sorted({r["algorithm"] for r in rows_for_metric}, key=lambda a: ALGO_ORDER.index(a) if a in ALGO_ORDER else 999)
        gaps = [float(next(r for r in rows_for_metric if r["algorithm"] == a)["mean_abs_gap"]) for a in algos]
        colors = [style_for(a)["color"] for a in algos]
        labels = [style_for(a)["label"] for a in algos]
        x = np.arange(len(algos))
        ax.bar(x, gaps, color=colors)
        floor = float(floor_rows[metric]["mean_abs_diff"]) if metric in floor_rows else 0.0
        ax.axhspan(0, floor, color="gray", alpha=0.25, label="tie-break noise floor")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7, rotation=35, ha="right")
        ax.set_title(GAP_METRIC_LABELS.get(metric, metric), fontsize=9)
        ax.set_ylabel("Mean absolute gap to oracle")
        ax.legend(fontsize=7)

    fig.suptitle(f"{REFERENCE_CONFIG}: online-algorithm gap to the oracle\n"
                 "(shaded band = tie-break noise floor -- a gap inside it is not a meaningful difference)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    _save(fig, "f10_optimality_gap")
    write_caption(
        "f10_optimality_gap",
        what_it_shows=(
            "Mean absolute gap between each online algorithm and the corresponding "
            "oracle variant, restricted to metrics that oracle actually optimizes "
            "(tracking_error vs. Optimal_Oracle_Tracking; satisfaction metrics vs. "
            "Optimal_Oracle_Balanced) -- no panel for total_transformer_overload, a "
            "hard constraint in both oracle variants and trivially zero. The shaded "
            "gray band is the tie-break noise floor (results/oracle_tiebreak_noise_floor.csv): "
            "the spread between the two oracle variants' own degenerate optima on the "
            "same metric -- any online-algorithm gap smaller than this band is within "
            "measurement resolution, not a meaningful difference."
        ),
        n_runs=len(gap_rows),
        configs=[REFERENCE_CONFIG],
        algorithms=[],
        extra="Source: results/optimality_gap.csv + results/oracle_tiebreak_noise_floor.csv (scripts/analyze_week4_results.py), not the main registry directly.",
    )


# ---------------------------------------------------------------------------
# f11_physics_term_falsification (Week 4): the negative-result evidence as
# a figure, not just a table (thesis_docs/chapters/04_oracle_and_pitd3.md
# S4.3). Regenerates its own data live from reward_pi.py's real functions
# (not hand-transcribed numbers) -- same "generated, never hand-written"
# discipline as write_caption.
# ---------------------------------------------------------------------------
def make_f11_physics_term_falsification():
    try:
        from scipy.stats import spearmanr
    except ImportError:
        print("f11: scipy not available, skipping.")
        return

    from ev2gym.rl_agent.reward import SqTrError_TrPenalty_UserIncentives
    from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin
    from ev2gym_thesis.rl.env_factory import make_env
    from ev2gym_thesis.rl.reward_pi import transformer_capacity_margin_term, headroom_penalty_term

    reference_config_path = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
    day, seed = REFERENCE_DAY, REFERENCE_SEED

    # --- Design 1: instantaneous margin, weight sweep (Pearson falls, Spearman pinned at 1.0) ---
    def run_episode_capture(agent_ctor, physics_term_fn):
        env = make_env(reference_config_path, day, seed)
        agent = agent_ctor(env)
        vanilla_s, physics_s = [], []

        def wrapper(env_, total_costs, user_satisfaction_list, *args):
            v = SqTrError_TrPenalty_UserIncentives(env_, total_costs, user_satisfaction_list, *args)
            p = physics_term_fn(env_)
            vanilla_s.append(v)
            physics_s.append(p)
            return v

        env.reward_function = wrapper
        for t in range(env.simulation_length):
            actions = agent.get_action(env)
            _, _, done, _, _ = env.step(actions)
            if done:
                break
        return np.array(vanilla_s), np.array(physics_s)

    vanilla, physics_raw_1 = run_episode_capture(lambda e: ChargeAsFastAsPossible(), transformer_capacity_margin_term)
    weights = [20, 100, 300, 1000, 2000]
    pearsons, spearmans = [], []
    for w in weights:
        pi = vanilla + w * physics_raw_1
        pearsons.append(np.corrcoef(vanilla, pi)[0, 1])
        rho, _ = spearmanr(vanilla, pi)
        spearmans.append(rho)

    # --- Design 2: headroom term, AFAP vs. Round Robin asymmetry + SoC correlation ---
    def run_episode_soc(agent_ctor):
        env = make_env(reference_config_path, day, seed)
        agent = agent_ctor(env)
        headroom_s, soc_s = [], []

        def wrapper(env_, total_costs, user_satisfaction_list, *args):
            h = headroom_penalty_term(env_)
            socs = [ev.get_soc() for cs in env_.charging_stations for ev in cs.evs_connected if ev is not None]
            headroom_s.append(h)
            soc_s.append(float(np.mean(socs)) if socs else np.nan)
            return SqTrError_TrPenalty_UserIncentives(env_, total_costs, user_satisfaction_list, *args)

        env.reward_function = wrapper
        for t in range(env.simulation_length):
            actions = agent.get_action(env)
            _, _, done, _, _ = env.step(actions)
            if done:
                break
        return np.array(headroom_s), np.array(soc_s)

    headroom_afap, soc_afap = run_episode_soc(lambda e: ChargeAsFastAsPossible())
    headroom_rr, soc_rr = run_episode_soc(lambda e: RoundRobin(e))
    valid_afap = ~np.isnan(soc_afap)
    valid_rr = ~np.isnan(soc_rr)
    corr_afap = np.corrcoef(headroom_afap[valid_afap], soc_afap[valid_afap])[0, 1]
    corr_rr = np.corrcoef(headroom_rr[valid_rr], soc_rr[valid_rr])[0, 1]

    # --- Plot: 3 panels ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

    ax = axes[0]
    ax.plot(weights, pearsons, "o-", color="#d62728", label="Pearson")
    ax.plot(weights, spearmans, "s-", color="#1f77b4", label="Spearman")
    ax.set_xscale("log")
    ax.set_ylim(0.9, 1.02)
    ax.set_xlabel("Physics-term weight (log scale)")
    ax.set_ylabel("Correlation with vanilla reward")
    ax.set_title("Design 1: instantaneous margin\n(Spearman pinned at 1.0 -- no weight escapes it)", fontsize=9)
    ax.legend(fontsize=8)

    ax = axes[1]
    counts = [int((headroom_afap < 0).sum()), int((headroom_rr < 0).sum())]
    ax.bar(["AFAP", "Round Robin"], counts, color=[style_for("ChargeAsFastAsPossible")["color"], style_for("RoundRobin")["color"]])
    ax.set_ylabel("Steps with headroom penalty active (/96)")
    ax.set_title("Design 2: Round Robin penalized far\nmore often than AFAP", fontsize=9)

    ax = axes[2]
    ax.scatter(soc_afap[valid_afap], headroom_afap[valid_afap], color=style_for("ChargeAsFastAsPossible")["color"],
               label=f"AFAP (r={corr_afap:.2f})", alpha=0.6, s=15)
    ax.scatter(soc_rr[valid_rr], headroom_rr[valid_rr], color=style_for("RoundRobin")["color"],
               label=f"Round Robin (r={corr_rr:.2f})", alpha=0.6, s=15)
    ax.set_xlabel("Mean connected-fleet SoC")
    ax.set_ylabel("Headroom penalty term")
    ax.set_title("Design 2: charging up REDUCES the\npenalty (positive correlation)", fontsize=9)
    ax.legend(fontsize=8)

    fig.suptitle("Falsification evidence: two physics-informed reward designs, two failure mechanisms\n"
                 "(station_v0_bogota, reference cell 2022-01-17 seed 0)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    _save(fig, "f11_physics_term_falsification")
    write_caption(
        "f11_physics_term_falsification",
        what_it_shows=(
            "Left: Design 1's weight sweep -- Pearson correlation with the vanilla "
            "reward falls as weight increases, but Spearman rank correlation stays "
            "pinned at 1.0 at every weight (both terms are monotonic functions of the "
            "same instantaneous scalar). Middle: Design 2's control-responsiveness "
            "asymmetry -- Round Robin (which nearly eliminates overload) triggers the "
            "headroom penalty far more often than AFAP (which overloads routinely). "
            "Right: Design 2's SoC-gradient problem -- the headroom penalty term "
            "correlates POSITIVELY with mean fleet SoC for both policies, meaning "
            "charging faster/more completely reduces the penalty, rewarding AFAP-like "
            "aggression. All data regenerated live from ev2gym_thesis/rl/reward_pi.py's "
            "actual functions on one real episode, not hand-transcribed."
        ),
        n_runs=1,
        configs=[REFERENCE_CONFIG],
        algorithms=["ChargeAsFastAsPossible", "RoundRobin"],
        extra="Full numeric account in thesis_docs/chapters/00_lab_log.md's 2026-08-19 falsification entry.",
    )


# ---------------------------------------------------------------------------
# f12/f13: Week 6 Part 0 extended training of TD3_vanilla. Like f08, these
# read the run's own logs (experiments/phase2_algorithms/results/week6_part0/,
# versioned) and results/week6_part0_convergence.csv, not the registry.
# ---------------------------------------------------------------------------
W6P0_LOG_DIR = "experiments/phase2_algorithms/results/week6_part0"
W6P0_SEEDS = [100, 101, 102]
W6P0_ORIGINAL_BUDGET = 60_000
W6P0_ROLLING = 100


def _w6p0_convergence():
    with open("results/week6_part0_convergence.csv", newline="") as f:
        return {int(r["train_seed"]): r for r in csv.DictReader(f)}


def _w6p0_kfmt(ax):
    # Visual QA fix: matplotlib's "1e3" offset label was easy to misread.
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))


def _w6p0_mark(ax, conv_row, color):
    ax.axvline(W6P0_ORIGINAL_BUDGET, color="0.35", linestyle="--", linewidth=1)
    if conv_row["convergence_step"] != "not converged":
        ax.axvline(float(conv_row["convergence_step"]), color=color, linestyle=":", linewidth=1.4)


def make_f12_extended_training_reward():
    import pandas as pd
    conv = _w6p0_convergence()
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    for ax, s in zip(axes, W6P0_SEEDS):
        e = pd.read_csv(f"{W6P0_LOG_DIR}/TD3_vanilla_extended_ts{s}_episodes.csv")
        sty = style_for(f"TD3_vanilla_extended_ts{s}")
        # Visual QA fix: raw values in neutral grey (the light seed-101 teal
        # at alpha 0.12 was invisible, and the legend already said grey).
        ax.plot(e.timesteps_at_end, e.episode_reward_raw, color="0.55", alpha=0.25, linewidth=0.5,
                label="raw episode reward")
        roll = e.episode_reward_raw.rolling(W6P0_ROLLING, min_periods=1).mean()
        ax.plot(e.timesteps_at_end, roll, color="black", linewidth=1.4, label=f"rolling mean ({W6P0_ROLLING} episodes)")
        _w6p0_mark(ax, conv[s], "black")
        ax.set_title(f"Training seed {s} (stopped at {int(conv[s]['total_steps']):,} steps)", fontsize=10)
        ax.set_xlabel("Training timesteps")
        _w6p0_kfmt(ax)
    axes[0].set_ylabel("Training-episode reward\n(SqTrError_TrPenalty_UserIncentives, with exploration noise)")
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color="0.5", alpha=0.5, label="raw episode reward (faint)"),
               Line2D([], [], color="black", label=f"rolling mean, {W6P0_ROLLING} episodes"),
               Line2D([], [], color="0.35", linestyle="--", label="original 60k budget"),
               Line2D([], [], color="0.2", linestyle=":", label="convergence declared (validation rule)")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9, frameon=False)
    fig.suptitle("Extended TD3_vanilla training: training-episode reward (noisy episodes over random scenarios --\n"
                 "NOT a convergence signal on its own; see f13 for the deterministic validation curve)", fontsize=10)
    fig.tight_layout(rect=[0, 0.07, 1, 0.9])
    _save(fig, "f12_extended_training_reward")
    write_caption(
        "f12_extended_training_reward",
        what_it_shows=(
            "Raw training-episode reward (faint) and its rolling mean over the last 100 episodes (black) "
            "for the three extended TD3_vanilla training seeds, one panel per seed; same reward function "
            "throughout, so a shared y-axis is valid. Dashed grey: the original 60,000-step budget. Dotted: "
            "the step at which the pre-registered validation rule declared convergence. Episodes use "
            "exploration noise and a different random scenario each, so this curve oscillates even for a "
            "stable policy. Source: experiments/phase2_algorithms/results/week6_part0/*_episodes.csv."
        ),
        n_runs=3, configs=[REFERENCE_CONFIG],
        algorithms=[style_for(f"TD3_vanilla_extended_ts{s}")["label"] for s in W6P0_SEEDS],
    )


def make_f13_extended_validation():
    import pandas as pd
    conv = _w6p0_convergence()
    val = {s: pd.read_csv(f"{W6P0_LOG_DIR}/TD3_vanilla_extended_ts{s}_validation.csv") for s in W6P0_SEEDS}
    panels = [("criterion_value", "Validation tracking error\n(selection criterion; lower is better)"),
              ("total_transformer_overload", "Validation transformer overload\n(kWh per simulated day)"),
              ("energy_user_satisfaction", "Validation energy user satisfaction\n(0-100 scale)")]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    common_max = min(v.timesteps.max() for v in val.values())
    for ax, (col, ylab) in zip(axes, panels):
        wide = pd.concat([v.set_index("timesteps")[col].rename(s) for s, v in val.items()], axis=1)
        both = wide[wide.index <= common_max]
        ax.fill_between(both.index, both.min(axis=1), both.max(axis=1), color="0.75", alpha=0.6,
                        label="min-max across 3 seeds")
        ax.plot(both.index, both.mean(axis=1), color="black", linewidth=1.6, label="mean across 3 seeds")
        for s, v in val.items():
            sty = style_for(f"TD3_vanilla_extended_ts{s}")
            tail = v[v.timesteps >= common_max]
            if len(tail) > 1:
                ax.plot(tail.timesteps, tail[col], color=sty["color"], linewidth=1.4,
                        label=f"seed {s} after {common_max:,} steps")
            c = conv[s]
            if c["convergence_step"] != "not converged":
                ax.axvline(float(c["convergence_step"]), color=sty["color"], linestyle=":", linewidth=1.4)
            if c["primary_step"]:
                p = v[v.timesteps == int(float(c["primary_step"]))]
                ax.plot(p.timesteps, p[col], marker=sty["marker"], color=sty["color"], markersize=8,
                        markeredgecolor="black", linestyle="none", label=f"primary checkpoint, seed {s}")
        ax.axvline(W6P0_ORIGINAL_BUDGET, color="0.35", linestyle="--", linewidth=1, label="original 60k budget")
        ax.set_xlabel("Training timesteps")
        ax.set_ylabel(ylab)
        _w6p0_kfmt(ax)
    h, l = axes[0].get_legend_handles_labels()
    from matplotlib.lines import Line2D
    h.append(Line2D([], [], color="0.3", linestyle=":", linewidth=1.4))
    l.append("convergence declared (seed colour)")
    fig.legend(h, l, loc="lower center", ncol=5, fontsize=8, frameon=False)
    fig.suptitle("Extended TD3_vanilla training: deterministic validation every 10,000 steps "
                 "(20 held-out cells: 10 seeds x weekday/weekend; dotted = convergence declared per seed)", fontsize=10)
    fig.tight_layout(rect=[0, 0.12, 1, 0.94])
    _save(fig, "f13_extended_validation")
    write_caption(
        "f13_extended_validation",
        what_it_shows=(
            "Deterministic (no exploration noise) validation of each saved checkpoint every 10,000 steps on "
            "20 fixed validation cells disjoint from the training draws and from the evaluation grid. Grey band "
            "and black line: min-max and mean across the three training seeds, over the range all three seeds "
            "reached; coloured lines continue the seeds that trained longer. Left: tracking error, the "
            "pre-registered selection criterion; middle/right: secondary metrics. Dashed grey: original 60k "
            "budget; dotted: convergence declared per seed; large markers: selected (primary) checkpoint. "
            "Source: experiments/phase2_algorithms/results/week6_part0/*_validation.csv and "
            "results/week6_part0_convergence.csv."
        ),
        n_runs=sum(len(v) for v in val.values()) * 20, configs=[REFERENCE_CONFIG],
        algorithms=[style_for(f"TD3_vanilla_extended_ts{s}")["label"] for s in W6P0_SEEDS],
        extra="n_runs counts validation episodes (validation evaluations x 20 cells).",
    )


# ---------------------------------------------------------------------------
# f14_all_models_comparison (Week 6 Part 0): every arm evaluated on the
# current 50-seed x 2-day grid, Week 1 through the extended TD3 run, one
# small-multiple panel per metric (never a shared/dual axis across metrics).
# ---------------------------------------------------------------------------
F14_GROUPS = [
    ("Heuristics and control", ["ChargeAsFastAsPossible", "RoundRobin", "RandomPolicy"]),
    ("Information-advantaged (non-causal)", ["MPC_TrackingG2V", "MPC_EnergyMaxG2V",
                                             "Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced"]),
    ("TD3 original, 60k (trained pre-setpoint-fix)", ["TD3_vanilla_ts100", "TD3_vanilla_ts101", "TD3_vanilla_ts102",
                                                     "TD3_TrackingOnly_ts100", "TD3_TrackingOnly_ts101",
                                                     "TD3_TrackingOnly_ts102"]),
    ("TD3 vanilla, new run @60k", ["TD3_vanilla_new60k_ts100", "TD3_vanilla_new60k_ts101", "TD3_vanilla_new60k_ts102"]),
    ("TD3 vanilla, extended (primary)", ["TD3_vanilla_extended_ts100", "TD3_vanilla_extended_ts101",
                                         "TD3_vanilla_extended_ts102"]),
    ("TD3 vanilla, extended (last)", ["TD3_vanilla_extended_last_ts100", "TD3_vanilla_extended_last_ts101",
                                      "TD3_vanilla_extended_last_ts102"]),
]


def _seed_level_mean_ci(df, algo, metric):
    """Mean over the 100 cells and a 95% normal CI over the 50 SEED-level
    means (both day types averaged within a seed first) -- the seed, not
    the row, is the independent unit (Week 5 Gate 3)."""
    per_seed = df[df.algorithm == algo].groupby("seed")[metric].mean()
    m = float(per_seed.mean())
    half = 1.96 * float(per_seed.std(ddof=1)) / np.sqrt(len(per_seed))
    return m, m - half, m + half, len(per_seed)


def make_f14_all_models_comparison():
    import pandas as pd
    from ev2gym_thesis.registry import REGISTRY_PATH
    reg = pd.read_csv(REGISTRY_PATH, low_memory=False)
    df = reg[(reg.config_name == REFERENCE_CONFIG) & (reg.analysis_row.astype(str) == "True")].copy()
    ens = pd.concat([pd.read_csv("results/week5_ens_compliance.csv"),
                     pd.read_csv("results/week6_part0_ens_compliance.csv")]).drop_duplicates("algorithm", keep="last")
    ens = ens.set_index("algorithm")

    order = [a for _, arms in F14_GROUPS for a in arms]
    missing = [a for a in order if (df.algorithm == a).sum() != 100 or a not in ens.index]
    assert not missing, f"f14: arms missing from the 100-cell grid or the ENS tables: {missing}"
    extra = sorted(set(df.algorithm) - set(order))
    assert not extra, f"f14: analysis arms not placed in any group (add them to F14_GROUPS): {extra}"

    # y positions with a gap between groups
    ypos, y, group_spans = {}, 0.0, []
    for label, arms in F14_GROUPS:
        start = y
        for a in arms:
            ypos[a] = y
            y += 1
        group_spans.append((label, start, y - 1))
        y += 1.5  # room for the next group's bold header row
    df["avg_sat_pct"] = df["average_user_satisfaction"].astype(float) * 100

    panels = [
        ("tracking_error", "Tracking error\n(sum of squared kW deviations; lower is better)", None),
        ("total_transformer_overload", "Transformer overload\n(kWh per simulated day; lower is better)", None),
        ("avg_sat_pct", "Average user satisfaction\n(%; higher is better; target > 90%)", None),
        ("ENS_rel", "Energy not served vs. AFAP, ENS_rel\n(%; target: 95% CI upper bound < 15%)", 15.0),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(19, 11), sharey=True)
    for ax, (metric, xlabel, target) in zip(axes, panels):
        for a in order:
            sty = style_for(a)
            if metric == "ENS_rel":
                m, lo, hi = (ens.loc[a, "ENS_rel_point_pct"], ens.loc[a, "ENS_rel_ci_low_pct"],
                             ens.loc[a, "ENS_rel_ci_high_pct"])
            else:
                m, lo, hi, _ = _seed_level_mean_ci(df, a, metric)
            ax.errorbar(m, ypos[a], xerr=[[m - lo], [hi - m]], fmt=sty["marker"], color=sty["color"],
                        markersize=8, markeredgecolor="black", markeredgewidth=0.6, ecolor=sty["color"],
                        elinewidth=2, capsize=3)
        if metric == "ENS_rel":
            rr = ens.loc["RoundRobin", "ENS_rel_point_pct"]
        else:
            rr = _seed_level_mean_ci(df, "RoundRobin", metric)[0]
        ax.axvline(rr, color=style_for("RoundRobin")["color"], linestyle="--", linewidth=1, alpha=0.8)
        if target is not None:
            ax.axvline(target, color="0.2", linestyle=":", linewidth=1.4)
            ax.text(target, -1.4, " 15% target", fontsize=8, color="0.2", va="center")
        for _, s0, s1 in group_spans[1::2]:
            ax.axhspan(s0 - 0.5, s1 + 0.5, color="0.94", zorder=0)
        ax.set_xlabel(xlabel, fontsize=9)
        if metric == "tracking_error":
            from matplotlib.ticker import FuncFormatter
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.grid(axis="x", color="0.88", linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_yticks([ypos[a] for a in order])
    axes[0].set_yticklabels([style_for(a)["label"] for a in order], fontsize=8.5)
    # (y inverted via set_ylim below)
    # Visual QA fix: group names as bold header rows directly above each
    # group, in the tick-label column (the first version placed them far to
    # the left and left a large empty margin).
    import matplotlib.transforms as mtransforms
    trans = mtransforms.blended_transform_factory(axes[0].transAxes, axes[0].transData)
    for label, s0, s1 in group_spans:
        axes[0].text(-0.02, s0 - 0.95, label, transform=trans, fontsize=9, fontweight="bold",
                     ha="right", va="center")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color=style_for("RoundRobin")["color"], linestyle="--",
                               label="Round Robin (recommended strategy, S5.8) -- reference line"),
                        Line2D([], [], color="0.2", linestyle=":", label="Declared target")],
               loc="lower center", ncol=2, fontsize=9, frameon=False)
    fig.suptitle("All models on the final evaluation grid (station_v0_bogota, 50 scenario seeds x weekday/weekend "
                 "= 100 cells per model)\nPoint = mean; bar = 95% CI over the 50 seed-level means "
                 "(ENS_rel: cluster-bootstrap CI, S5.7)", fontsize=10)
    axes[0].set_ylim(max(ypos.values()) + 0.8, -1.8)
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    _save(fig, "f14_all_models_comparison")
    write_caption(
        "f14_all_models_comparison",
        what_it_shows=(
            "Every arm evaluated on the current statistical grid (analysis_row=True, 50 scenario seeds x "
            "2 day types = 100 cells per arm), from the Week 1 heuristics through the Week 6 Part 0 extended "
            "TD3_vanilla run, in four small-multiple panels (one metric per panel, never a shared axis). "
            "Points are 100-cell means; bars are 95% normal CIs over the 50 seed-level means (the seed is "
            "the independent unit), except ENS_rel, which uses the S5.7 definition and its cluster-bootstrap "
            "CI from results/week5_ens_compliance.csv and results/week6_part0_ens_compliance.csv. Dashed blue: "
            "Round Robin, the recommended strategy (S5.8). Dotted: the 15% ENS_rel target. Groups are "
            "shaded alternately. MPC and oracle arms are non-causal (know departure times) and are "
            "value-of-information bounds, not deployable candidates. The original TD3 rows were trained "
            "before the Week 5 power-setpoint fix and evaluated after it; the new-run and extended rows "
            "were trained and evaluated on the fixed environment."
        ),
        n_runs=100 * len(order), configs=[REFERENCE_CONFIG],
        algorithms=[style_for(a)["label"] for a in order],
    )


# ---------------------------------------------------------------------------
# f15-f18 (Week 7, Objectives 4-5). Same presentation conventions as f13/f14:
# point = mean, bar = 95% cluster-bootstrap CI (scenario seed resampled),
# Round Robin as the dashed reference, declared targets drawn. Sources are
# the results/week7_*.csv tables written by scripts/analyze_week7_infra.py
# and scripts/analyze_week7_replicability.py.
# ---------------------------------------------------------------------------
W7_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "MPC_TrackingG2V", "TD3_vanilla_extended_ts102",
           "Optimal_Oracle_Tracking"]
W7_AXES = {"Axis 1 -- station demand (spawn multiplier x base)": [("base", 1.0), ("spawn1.3", 1.3), ("spawn1.6", 1.6)],
           "Axis 2 -- feeder background load (load multiplier)": [("base", 1.0), ("load1.3", 1.3), ("load1.6", 1.6)]}
W7_LABEL = {"TD3_vanilla_extended_ts102": "TD3 extended seed 102 (final RL)"}


def _w7_label(a):
    return W7_LABEL.get(a, style_for(a)["label"])


def _w7_errpoint(ax, x, m, lo, hi, arm, dashed=False):
    sty = style_for(arm)
    ax.errorbar(x, m, yerr=[[m - lo], [hi - m]], fmt=sty["marker"], color=sty["color"], markersize=7,
                markeredgecolor="black", markeredgewidth=0.6, elinewidth=1.8, capsize=3, zorder=3)


def make_f15_grid_growth():
    import pandas as pd
    mc = pd.read_csv("results/week7_grid_master_comparison.csv")
    en = pd.read_csv("results/week7_grid_ens_compliance.csv")
    mc = mc.merge(en[["setting", "algorithm", "ENS_rel_point_pct", "ENS_rel_ci_low_pct", "ENS_rel_ci_high_pct"]],
                  on=["setting", "algorithm"])
    panels = [("tracking_error", "Tracking error\n(lower is better)", None, 1),
              ("total_transformer_overload", "Transformer overload\n(kWh/day; lower is better)", None, 1),
              ("average_user_satisfaction", "Average user satisfaction (%)\n(target > 90%)", 90.0, 100),
              ("ENS_rel", "Energy not served vs. AFAP, ENS_rel (%)\n(target: CI upper < 15%)", 15.0, 1)]
    fig, axes = plt.subplots(2, 4, figsize=(19, 9.5))
    dodge = {a: (i - 2) * 0.035 for i, a in enumerate(W7_ARMS)}
    for r, (axis_label, levels) in enumerate(W7_AXES.items()):
        for c, (metric, ylabel, target, scale) in enumerate(panels):
            ax = axes[r, c]
            for arm in W7_ARMS:
                xs, ms = [], []
                for st, lvl in levels:
                    row = mc[(mc.setting == st) & (mc.algorithm == arm)]
                    if row.empty:
                        continue
                    row = row.iloc[0]
                    if metric == "ENS_rel":
                        m, lo, hi = row.ENS_rel_point_pct, row.ENS_rel_ci_low_pct, row.ENS_rel_ci_high_pct
                    else:
                        m, lo, hi = (row[f"{metric}_mean"] * scale, row[f"{metric}_ci_low"] * scale,
                                     row[f"{metric}_ci_high"] * scale)
                    _w7_errpoint(ax, lvl + dodge[arm], m, lo, hi, arm)
                    xs.append(lvl + dodge[arm])
                    ms.append(m)
                sty = style_for(arm)
                ax.plot(xs, ms, color=sty["color"], linewidth=1.6 if arm == "RoundRobin" else 0.9,
                        linestyle="--" if arm == "RoundRobin" else "-", alpha=0.9, zorder=2)
            if target is not None:
                ax.axhline(target, color="0.2", linestyle=":", linewidth=1.4)
            ax.set_xticks([1.0, 1.3, 1.6])
            ax.set_xticklabels(["1.0x", "1.3x", "1.6x"])
            ax.grid(axis="y", color="0.9", linewidth=0.6)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            if r == 0:
                ax.set_title(ylabel, fontsize=10)
            if c == 0:
                ax.set_ylabel(axis_label, fontsize=9, fontweight="bold")
            if metric == "tracking_error":
                from matplotlib.ticker import FuncFormatter
                ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker=style_for(a)["marker"], color=style_for(a)["color"], markeredgecolor="black",
                      linestyle="--" if a == "RoundRobin" else "-", label=_w7_label(a)) for a in W7_ARMS]
    handles.append(Line2D([], [], color="0.2", linestyle=":", label="Declared target"))
    fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=9, frameon=False)
    # Visual QA fix: the flat Axis 2 row is a result, not a plotting error -- say so on the figure.
    axes[1, 0].text(0.03, 0.52, "Feeder load does not feed back on the station:\nstation metrics are identical along Axis 2\n(its only effect is on voltage, see f17)",
                    transform=axes[1, 0].transAxes, fontsize=7.5, va="top", color="0.25")
    fig.suptitle("Grid-enabled station under growth (station on bus 27 of EV2Gym's 34-node feeder, 100 kW transformer)\n"
                 "Point = mean over 50 seeds x 2 day types; bar = 95% cluster-bootstrap CI; Round Robin dashed (reference)",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.05, 1, 0.93])
    _save(fig, "f15_grid_growth")
    write_caption(
        "f15_grid_growth",
        what_it_shows=(
            "The five fixed Objective 4 arms on the grid-enabled station, along two one-at-a-time growth axes "
            "(top: station demand, spawn_multiplier 30/39/48; bottom: feeder background load, load_multiplier "
            "1.0/1.3/1.6). Point = mean over 100 cells (50 scenario seeds x weekday/weekend); bar = 95% "
            "cluster-bootstrap CI resampling the seed (ENS_rel: S5.7 definition and its seed bootstrap). Round "
            "Robin is drawn dashed as the reference; dotted lines are the anteproyecto targets. Source: "
            "results/week7_grid_master_comparison.csv, results/week7_grid_ens_compliance.csv."),
        n_runs=int(mc.n_rows.sum()), configs=sorted({f"station_v0_bogota_grid[{s}]" for s in mc.setting}),
        algorithms=[_w7_label(a) for a in W7_ARMS],
        extra="MPC_TrackingG2V and the oracle are non-causal (know departure times); they bound, not compete.")


def make_f16_transformer_sizing():
    import pandas as pd
    ps = pd.read_csv("results/week7_transformer_per_seed.csv")
    sz = pd.read_csv("results/week7_transformer_sizing.csv")
    settings = [s for s in ["base", "spawn1.3", "spawn1.6", "load1.3", "load1.6"] if s in set(ps.setting)]
    fig, axes = plt.subplots(1, len(settings), figsize=(4.0 * len(settings), 5.6), sharey=True)
    axes = np.atleast_1d(axes)
    rng = np.random.default_rng(0)
    for ax, st in zip(axes, settings):
        for i, arm in enumerate(W7_ARMS):
            g = ps[(ps.setting == st) & (ps.algorithm == arm)]
            sty = style_for(arm)
            ax.scatter(i + rng.uniform(-0.18, 0.18, len(g)), g.peak_kw, s=10, color=sty["color"], alpha=0.35,
                       edgecolor="none", zorder=2)
            p95 = sz[(sz.setting == st) & (sz.algorithm == arm)].peak_kw_p95.iloc[0]
            ax.hlines(p95, i - 0.3, i + 0.3, color="black", linewidth=2.2, zorder=3)
        ax.axhline(100, color="0.2", linestyle=":", linewidth=1.4)
        ax.set_xticks(range(len(W7_ARMS)))
        ax.set_xticklabels([_w7_label(a) for a in W7_ARMS], rotation=40, ha="right", fontsize=8)
        ax.set_title(st, fontsize=10)
        ax.grid(axis="y", color="0.9", linewidth=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("Per-seed peak station power (kW)\n(max over weekday and weekend)")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], color="black", linewidth=2.2, label="95th percentile over 50 seeds"),
                        Line2D([], [], color="0.2", linestyle=":", label="Installed transformer rating (100 kW)")],
               loc="lower center", ncol=2, fontsize=9, frameon=False)
    fig.suptitle("Transformer sizing: per-seed peak station power by arm and growth setting (dots = one scenario seed)",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])
    _save(fig, "f16_transformer_sizing")
    write_caption(
        "f16_transformer_sizing",
        what_it_shows=(
            "Per scenario seed, the peak power drawn by the station (max over the two day types, from each run's "
            "saved timeseries); black bar = 95th percentile over the 50 seeds, i.e. the transformer rating at "
            "which the 95th-percentile seed would stop overloading. Dotted = the installed 100 kW. For AFAP the "
            "peak does not respond to the rating, so the bar is a valid sizing number; limit-aware arms stay at "
            "or below 100 kW by construction. With n = 50 the 95th percentile rests on ~2-3 tail seeds: "
            "directional, not a tail estimate. Source: results/week7_transformer_per_seed.csv, "
            "results/week7_transformer_sizing.csv."),
        n_runs=int(len(ps) * 2), configs=sorted({f"station_v0_bogota_grid[{s}]" for s in settings}),
        algorithms=[_w7_label(a) for a in W7_ARMS])


def make_f17_voltage_attribution():
    import pandas as pd
    va = pd.read_csv("results/week7_voltage_attribution.csv")
    settings = [s for s in ["base", "spawn1.3", "spawn1.6", "load1.3", "load1.6"] if s in set(va.setting)]
    panels = [("delta_bus_steps_outside", "Station-attributable out-of-band\n(bus, step) samples per day\n(arm minus idle station, same cell)"),
              ("delta_min_voltage_pu", "Station-attributable change in the\nfeeder's minimum voltage (p.u.)")]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.6))
    width = 0.15
    for ax, (col, ylabel) in zip(axes, panels):
        for i, arm in enumerate(W7_ARMS):
            for j, st in enumerate(settings):
                r = va[(va.setting == st) & (va.algorithm == arm)]
                if r.empty:
                    continue
                r = r.iloc[0]
                _w7_errpoint(ax, j + (i - 2) * width, r[f"{col}_mean"], r[f"{col}_ci_low"], r[f"{col}_ci_high"], arm)
        for j, st in enumerate(settings):
            r = va[(va.setting == st) & (va.algorithm == "RoundRobin")].iloc[0]
            ax.hlines(r[f"{col}_mean"], j - 0.4, j + 0.4, color=style_for("RoundRobin")["color"], linestyle="--",
                      linewidth=1.2, zorder=1)
        ax.axhline(0, color="0.2", linestyle=":", linewidth=1.4)
        labels = []
        for st in settings:
            idle = va[(va.setting == st) & (va.algorithm == "RoundRobin")].iloc[0]
            # Visual QA fix: shorter labels (the first version overlapped its neighbours).
            labels.append(f"{st}\n(idle: {int(idle.cells_idle_feeder_outside_band)}/{int(idle.n_runs)}\nout of band)")
        ax.set_xticks(range(len(settings)))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.grid(axis="y", color="0.9", linewidth=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker=style_for(a)["marker"], color=style_for(a)["color"], markeredgecolor="black",
                      linestyle="none", label=_w7_label(a)) for a in W7_ARMS]
    handles += [Line2D([], [], color=style_for("RoundRobin")["color"], linestyle="--", label="Round Robin (reference)"),
                Line2D([], [], color="0.2", linestyle=":", label="Target: station adds no out-of-band sample")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8.5, frameon=False)
    fig.suptitle("Voltage (+/-5% band, 0.95-1.05 p.u.): what the station adds to the feeder, by arm and setting\n"
                 "Point = mean over 100 cells; bar = 95% cluster-bootstrap CI", fontsize=10)
    fig.tight_layout(rect=[0, 0.1, 1, 0.92])
    _save(fig, "f17_voltage_attribution")
    write_caption(
        "f17_voltage_attribution",
        what_it_shows=(
            "Station-attributable voltage effect: each arm's run minus the idle-station (zero-charging) run of the "
            "same setting, seed and day (the feeder's background load and PV are identical between the two). Left: "
            "extra (bus, step) samples outside 0.95-1.05 p.u.; right: change in the minimum bus voltage. The x "
            "labels give how many of the 100 cells already leave the band with the station idle -- the feeder "
            "itself is out of band at bus 27, so no absolute compliance claim is made. Source: "
            "results/week7_voltage_attribution.csv."),
        n_runs=int(va.n_runs.sum()), configs=sorted({f"station_v0_bogota_grid[{s}]" for s in settings}),
        algorithms=[_w7_label(a) for a in W7_ARMS])


def make_f18_two_city_margin():
    import pandas as pd
    t = pd.read_csv("results/week7_replicability_margin.csv")
    t = t[(t.dataset == "nongrid") & t.price_scenario.isin(["bogota_base", "medellin_base"])]
    arms = ["RoundRobin", "MPC_TrackingG2V", "Optimal_Oracle_Tracking", "TD3_vanilla_extended_ts102", "RandomPolicy",
            "MPC_EnergyMaxG2V", "Optimal_Oracle_Balanced"]
    arms = [a for a in arms if a in set(t.algorithm)]
    fig, ax = plt.subplots(figsize=(11, 6))
    for k, (scen, city, off, mk) in enumerate([("bogota_base", "Bogota (Enel CU 865.76)", -0.17, "o"),
                                                ("medellin_base", "Medellin (EPM CU 923.92; retail 1,450 = sensitivity)", 0.17, "s")]):
        for i, arm in enumerate(arms):
            r = t[(t.price_scenario == scen) & (t.algorithm == arm)].iloc[0]
            sty = style_for(arm)
            ax.errorbar(r.margin_conceded_vs_afap_cop_per_day, i + off,
                        xerr=[[r.margin_conceded_vs_afap_cop_per_day - r.conceded_ci_low],
                              [r.conceded_ci_high - r.margin_conceded_vs_afap_cop_per_day]],
                        fmt=mk, color=sty["color"], markeredgecolor="black", markerfacecolor=sty["color"] if k == 0 else "white",
                        markersize=7, elinewidth=1.6, capsize=3, label=city if i == 0 else None)
    rr = t[(t.price_scenario == "bogota_base") & (t.algorithm == "RoundRobin")].iloc[0].margin_conceded_vs_afap_cop_per_day
    ax.axvline(rr, color=style_for("RoundRobin")["color"], linestyle="--", linewidth=1.2, label="Round Robin, Bogota (reference)")
    ax.axvline(0, color="0.2", linestyle=":", linewidth=1.2)
    ax.set_yticks(range(len(arms)))
    ax.set_yticklabels([_w7_label(a) for a in arms], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Gross margin conceded vs. AFAP (COP per simulated day; negative = earns more than AFAP)")
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="x", color="0.9", linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    from matplotlib.lines import Line2D
    # Visual QA fix: neutral legend markers (the first version showed the
    # Round Robin colour next to "Bogota").
    ax.legend(handles=[Line2D([], [], marker="o", color="0.4", markerfacecolor="0.4", markeredgecolor="black",
                              linestyle="none", label="Bogota (Enel CU 865.76; retail 1,450)"),
                       Line2D([], [], marker="s", color="0.4", markerfacecolor="white", markeredgecolor="black",
                              linestyle="none", label="Medellin (EPM CU 923.92; retail 1,450 = sensitivity)"),
                       Line2D([], [], color=style_for("RoundRobin")["color"], linestyle="--",
                              label="Round Robin, Bogota (reference)")],
              fontsize=8.5, loc="lower right", frameon=False)
    ax.set_title("Cost of each strategy against AFAP, Bogota vs. Medellin (non-grid evaluation set, 50 seeds x 2 day types)\n"
                 "filled = Bogota, open = Medellin; bar = 95% cluster-bootstrap CI; n_clusters = 50", fontsize=10)
    fig.tight_layout()
    _save(fig, "f18_two_city_margin")
    write_caption(
        "f18_two_city_margin",
        what_it_shows=(
            "Gross margin each arm concedes against AFAP (COP/day), recomputed from the registry's energy with "
            "Bogota's Week 5 constants (retail 1,450; CU 865.7615) and Medellin's EPM September 2026 Nivel II CU "
            "(923.92, Punta, with contribution) with Bogota's retail price as a labelled sensitivity (EPM publishes "
            "no EV charging price). Under a flat price the two cities differ by the constant factor 0.900; the "
            "ranking is identical (results/week7_ranking_invariance.csv). Source: results/week7_replicability_margin.csv."),
        n_runs=100 * len(arms), configs=["station_v0_bogota"], algorithms=[_w7_label(a) for a in arms])


# doc:begin closure_figures
CLOSURE_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "TD3_vanilla_extended_ts102"]


def make_f19_capacity_threshold():
    """Closure C1: demand not served (lower bound) and P95 peak vs demand
    level, per arm, with the two targets."""
    import pandas as pd
    d = pd.read_csv("results/closure_c1_capacity_by_level.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    offs = {"ChargeAsFastAsPossible": -0.012, "RoundRobin": 0.0, "TD3_vanilla_extended_ts102": 0.012}
    for arm in CLOSURE_ARMS:
        g = d[d.algorithm == arm].sort_values("level")
        x = g.level.replace({0.75: 0.7333}) + offs[arm]
        sty = style_for(arm)
        lab = _w7_label(arm)
        axes[0].errorbar(x, 100 * g.dns_lower_mean,
                         yerr=[100 * (g.dns_lower_mean - g.dns_lower_ci_low), 100 * (g.dns_lower_ci_high - g.dns_lower_mean)],
                         fmt=sty["marker"] + "-", color=sty["color"], markeredgecolor="black", capsize=3, label=lab)
        axes[1].errorbar(x, g.peak_kw_p95, yerr=[g.peak_kw_p95 - g.peak_kw_p95_ci_low, g.peak_kw_p95_ci_high - g.peak_kw_p95],
                         fmt=sty["marker"] + "-", color=sty["color"], markeredgecolor="black", capsize=3, label=lab)
    axes[0].axhline(15, color="0.2", linestyle=":", linewidth=1.3, label="Target: demand not served < 15%")
    axes[1].axhline(100, color="0.2", linestyle=":", linewidth=1.3, label="Transformer limit, 100 kW")
    axes[0].set_ylabel("Demand not served, lower bound (% of requested energy)")
    axes[1].set_ylabel("95th-percentile per-seed peak station power (kW)")
    for ax in axes:
        ax.set_xlabel("Demand level (multiple of the Week 1 demand; 0.733x = spawn 22)")
        ax.set_xticks([0.5, 0.7333, 1.0, 1.3, 1.6, 2.0, 2.5])
        ax.set_xticklabels(["0.5", "0.733", "1.0", "1.3", "1.6", "2.0", "2.5"])
        ax.grid(color="0.9", linewidth=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    # Visual QA fix (closure): the in-axes legend covered AFAP's 1.0-1.3x error
    # bars on the right panel, so one shared legend sits below both panels.
    h, l = axes[0].get_legend_handles_labels()
    h2, l2 = axes[1].get_legend_handles_labels()
    fig.legend(h + [h2[0]], l + [l2[0]], loc="lower center", ncol=5, fontsize=8.5, frameon=False)
    axes[0].set_ylim(0, 100)
    axes[1].set_ylim(0, 260)
    fig.suptitle("Where the 8-port, 100 kW station breaks: demand not served (left) and peak power (right), by arm\n"
                 "Point = mean (left) or P95 over 50 seeds (right); bar = 95% CI, cluster bootstrap over 50 scenario seeds",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0.07, 1, 0.92])
    _save(fig, "f19_capacity_threshold")
    write_caption(
        "f19_capacity_threshold",
        what_it_shows=(
            "Closure brief C1. Left: demand not served, lower bound (rejected arrivals' energy plus shortfall on served "
            "EVs, over total requested; ev2gym_thesis/demand/censoring.py). Right: 95th percentile over 50 seeds of the "
            "per-seed peak station power. Round Robin breaks the 15% target at 0.733x and never exceeds 100 kW; AFAP and "
            "the final RL model exceed 100 kW from 0.5x. Demand not served is nearly identical across arms: the 8 ports "
            "set it. 1.0/1.3/1.6x are the Week 7 Step 2 rows (identical to non-grid); the rest are closure rows. Source: "
            "results/closure_c1_capacity_by_level.csv."),
        n_runs=int(d.n_runs.sum()), configs=["station_v0_bogota_sp15/22/60/75", "station_v0_bogota_grid[base/spawn1.3/1.6]"],
        algorithms=[_w7_label(a) for a in CLOSURE_ARMS])


def make_f20_port_options():
    """Closure C2: Round Robin's demand not served for each port option,
    as run and at constant station demand, at 0.733x and 1.0x."""
    import pandas as pd
    c = pd.read_csv("results/closure_c2_options.csv")
    c = c[(c.algorithm == "RoundRobin") & (c.transformer_kw == 100.0)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, lvl in zip(axes, [0.75, 1.0]):
        g = c[c.level == lvl]
        for k, (treat, col, mk) in enumerate([("as run", "0.65", "o"), ("constant", style_for("RoundRobin")["color"], "s")]):
            for ports in [8, 10, 12]:
                if ports == 8:
                    r = g[g.ports == 8].iloc[0]
                else:
                    sub = g[(g.ports == ports) & g.station_demand.str.startswith(treat)]
                    if not len(sub):
                        continue
                    r = sub.iloc[0]
                x = ports + (-0.18 if k == 0 else 0.18)
                ax.errorbar(x, 100 * r.dns_lower_mean,
                            yerr=[[100 * (r.dns_lower_mean - r.dns_lower_ci_low)], [100 * (r.dns_lower_ci_high - r.dns_lower_mean)]],
                            fmt=mk, color=col, markeredgecolor="black", capsize=3, markersize=7,
                            label=(("Spawn unchanged (more ports also add arrivals)" if k == 0 else
                                    "Constant station demand (spawn x 8/ports)") if ports == 10 else None))
        ax.axhline(15, color="0.2", linestyle=":", linewidth=1.3, label="Target: demand not served < 15%")
        ax.set_xticks([8, 10, 12])
        ax.set_xlabel("Charging ports (transformer 100 kW; Round Robin)")
        ax.set_title(f"Demand level {'0.733x (spawn 22)' if lvl == 0.75 else '1.0x (Week 1 sizing)'}", fontsize=10)
        ax.grid(axis="y", color="0.9", linewidth=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("Demand not served, lower bound (% of requested energy)")
    axes[0].legend(fontsize=8.5, frameon=False, loc="upper right")
    fig.suptitle("What closes the demand gap: more ports (a larger transformer changes nothing for Round Robin)\n"
                 "Point = mean over 100 cells; bar = 95% CI, cluster bootstrap over 50 scenario seeds", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    _save(fig, "f20_port_options")
    write_caption(
        "f20_port_options",
        what_it_shows=(
            "Closure brief C2, Round Robin on the 100 kW transformer. EV2Gym draws arrivals per port, so adding ports at "
            "an unchanged spawn multiplier also adds demand (grey); the constant-demand variants scale the spawn "
            "multiplier by 8/ports so only the port count changes (blue, the primary reading). 10 ports meet the 15% "
            "target at 0.733x and 12 ports at 1.0x. The 112.5 and 150 kVA variants (not plotted) leave Round Robin's "
            "values identical. Censoring recomputed for each port count. Source: results/closure_c2_options.csv."),
        n_runs=int(c.n_runs.sum()), configs=["station_v0_bogota_sp22/sp30[_p10|_p12]_tx100[_cd]"],
        algorithms=["Round Robin"])


def make_f21_city_cost():
    """Closure D2: Round Robin's cost of the 100 kW limit in the six
    categoria especial cities, flat cost vs the operator's two-band option."""
    import pandas as pd
    c = pd.read_csv("results/closure_multicity_rr_cost.csv")
    c = c[c.retail_price_label == "1450_reference"].reset_index(drop=True)
    t = pd.read_csv("results/closure_multicity_tariffs.csv").set_index("city")
    fig, ax = plt.subplots(figsize=(11, 5.5))
    y = range(len(c))
    for i, r in c.iterrows():
        ax.errorbar(r.conceded_flat_cop_day, i - 0.15,
                    xerr=[[r.conceded_flat_cop_day - r.conceded_flat_ci_low], [r.conceded_flat_ci_high - r.conceded_flat_cop_day]],
                    fmt="o", color="0.35", markeredgecolor="black", capsize=3, label="Flat (monomial) cost" if i == 0 else None)
        if not pd.isna(r.conceded_tou_cop_day):
            ax.errorbar(r.conceded_tou_cop_day, i + 0.15,
                        xerr=[[r.conceded_tou_cop_day - r.conceded_tou_ci_low], [r.conceded_tou_ci_high - r.conceded_tou_cop_day]],
                        fmt="s", color=style_for("RoundRobin")["color"], markeredgecolor="black", capsize=3,
                        label="Operator's two-band option" if i == 0 else None)
    labels = []
    for city in c.city:
        sp = t.loc[city, "intraday_spread"]
        labels.append(f"{city}\n({t.loc[city, 'operator'].split(' (')[0]}, {t.loc[city, 'sheet_month']}; "
                      f"spread {'n/a' if pd.isna(sp) else f'{100 * sp:.2f}%'})")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.invert_yaxis()
    from matplotlib.ticker import FuncFormatter
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlabel("Round Robin's margin conceded vs. AFAP (COP per simulated day; retail 1,450 COP/kWh in every city)")
    ax.grid(axis="x", color="0.9", linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
    ax.set_title("Cost of keeping the 100 kW transformer with Round Robin, in the six categoria especial cities\n"
                 "Point = mean over 100 paired runs; bar = 95% CI, cluster bootstrap over 50 scenario seeds", fontsize=10)
    fig.tight_layout()
    _save(fig, "f21_city_cost")
    write_caption(
        "f21_city_cost",
        what_it_shows=(
            "Closure brief D2. Each city's Nivel 2 commercial energy cost with contribution (ev2gym_thesis/prices/cities.py, "
            "sources saved in thesis_docs/sources/) applied to the non-grid statistical rows. Flat: margin = energy x "
            "(1,450 - cost), so the relative cost is 0.47% everywhere (Proposition 7.1). Two-band: each run's 15-minute "
            "station power profile priced at the operator's peak and off-peak rates. Barranquilla (Air-e, 10.03% spread, "
            "17-22 h) is the only city where the two-band cost departs materially from the flat one. Cali uses EMCALI's "
            "January 2026 sheet, the latest retrievable. Source: results/closure_multicity_rr_cost.csv."),
        n_runs=200, configs=["station_v0_bogota"], algorithms=["AFAP", "Round Robin"])
# doc:end closure_figures


def _save(fig, name):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig.savefig(f"{FIGURES_DIR}/{name}.png", dpi=300)
    fig.savefig(f"{FIGURES_DIR}/{name}.pdf")
    plt.close(fig)
    print(f"Wrote {FIGURES_DIR}/{name}.png, .pdf")


def _merge_economics(rows):
    """Week 5: joins results/economics_cop.csv's gross_margin_cop onto each
    registry row (dedup key: config_name, algorithm, seed, eval_day) -- a
    plain dict-merge, not a recompute, so figures read the exact same
    Colombian-peso values 05_algorithm_comparison.md quotes."""
    import csv as _csv
    econ_by_key = {}
    with open("results/economics_cop.csv", newline="") as f:
        for r in _csv.DictReader(f):
            key = (r["config_name"], r["algorithm"], r["seed"], r["eval_day"])
            econ_by_key[key] = float(r["gross_margin_cop"])
    for r in rows:
        key = (r["config_name"], r["algorithm"], str(int(r["seed"])), r["eval_day"])
        r["gross_margin_cop"] = econ_by_key.get(key)
    return rows


if __name__ == "__main__":
    import argparse
    _p = argparse.ArgumentParser()
    _p.add_argument("--only", default=None,
                    help="comma-separated figure ids to regenerate (e.g. f12,f13); default: all")
    _only = _p.parse_args().only
    if _only:
        # Week 6 Part 0: regenerate only the named figures, leaving the rest
        # (and their captions' git commit/timestamp) untouched.
        _fns = {"f08": lambda: make_f08_learning_curves(load_registry()),
                "f12": make_f12_extended_training_reward, "f13": make_f13_extended_validation,
                "f14": make_f14_all_models_comparison, "f15": make_f15_grid_growth,
                "f16": make_f16_transformer_sizing, "f17": make_f17_voltage_attribution,
                "f18": make_f18_two_city_margin, "f19": make_f19_capacity_threshold,
                "f20": make_f20_port_options, "f21": make_f21_city_cost}
        for _fid in _only.split(","):
            _fns[_fid.strip()]()
        raise SystemExit(0)
    rows = load_registry()
    rows = _merge_economics(rows)
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
    make_f10_optimality_gap()
    make_f11_physics_term_falsification()
    make_f12_extended_training_reward()
    make_f13_extended_validation()
    make_f14_all_models_comparison()
    make_f15_grid_growth()
    make_f16_transformer_sizing()
    make_f17_voltage_attribution()
    make_f18_two_city_margin()
    make_f19_capacity_threshold()
    make_f20_port_options()
    make_f21_city_cost()

    print("\nAll figures regenerated.")
