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
    fig.suptitle(f"{REFERENCE_CONFIG}: metrics across the 5-seed x 10-day evaluation grid, "
                 f"mean +/- 95% CI (n={n_per_algo} per algorithm)", fontsize=10)
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
                 f"across all {n_per_algo} runs per algorithm (5 seeds x 10 days)", fontsize=10)
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

    fig, axes = plt.subplots(1, len(arm_curves), figsize=(6.5 * len(arm_curves), 5), squeeze=False)
    axes = axes[0]
    for ax, (arm_label, curves) in zip(axes, arm_curves.items()):
        for algo, data in curves.items():
            sty = style_for(algo)
            ax.plot(data["timesteps"], data["mean_episode_reward"], color=sty["color"],
                    label=sty["label"], linewidth=1.3)
        ax.set_xlabel("Training timesteps")
        ax.set_title(arm_label, fontsize=10)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Mean episode reward\n(SB3 rolling window, last <=100 episodes)")
    fig.suptitle("Learning curves by arm -- separate panels: different reward\n"
                 "functions, NOT a common scale (station_v0_bogota, TRAIN_DAYS round-robin)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    _save(fig, "f08_learning_curves")

    all_algos = [a for _, curves in arm_curves.items() for a in curves]
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
            "are not the same thing."
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
OPTIMALITY_GAP_PATH = "results/optimality_gap.csv"
NOISE_FLOOR_PATH = "results/oracle_tiebreak_noise_floor.csv"
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
    make_f10_optimality_gap()
    make_f11_physics_term_falsification()

    print("\nAll figures regenerated.")