"""
Paper Fig. 3: demand not served (a) and mean energy satisfaction counting
rejected drivers (b) by demand level, DC regime, 8 ports, 100 kW, every C1 arm.

Same data, arms, colours and style as the figure in the submitted paper
(results/review_C_master_{1.0,1.3,1.6}x.csv; serif 8 pt, 3.5 in column width).
Regenerated after the advisor's final comments (2026-11-17, task 7) with a
shorter canvas (3.5 x 4.4 in instead of 3.5 x 4.9 in) so the figure takes less
of the column; nothing in the data or the encoding changed.

Usage (from the repository root):
  python scripts/paper_fig3.py
Output: experiments/phase4_review/results/figures/paper_fig3_dns_f_levels.{png,pdf}
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
                     "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "legend.fontsize": 6.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.linewidth": 0.6, "lines.linewidth": 1.1, "savefig.dpi": 300,
                     "grid.linewidth": 0.4, "grid.color": "#d9d9d9"})

OUT = "experiments/phase4_review/results/figures"
ARMS = [("AFAP", "AFAP", "#000000", "o", "-"), ("PS", "PS", "#d95f02", "s", "-"),
        ("RR-TA", "RR-TA", "#1b9e77", "D", "-"), ("TD3_safe", "TD3_safe", "#e6ab02", "^", "-"),
        ("MPC-soft-est", "MPC-soft-est", "#666666", "<", "-"), ("Random+S", "Random+S", "#a6761d", "h", "-"),
        ("FIX12.5", "FIX12.5", "#e7298a", "v", "-"), ("RR", "RR*", "#2c7fb8", "P", ":"),
        ("RR+S", "RR+S*", "#7570b3", "X", ":"), ("MPC-soft", "MPC-soft*", "#66a61e", "*", ":"),
        ("Oracle-E", "Oracle-E*", "#c51b7d", "8", ":")]
LEVELS = [1.0, 1.3, 1.6]


def main():
    m = pd.concat([pd.read_csv(f"results/review_C_master_{lv}x.csv") for lv in ("1.0", "1.3", "1.6")])
    fig, axs = plt.subplots(2, 1, figsize=(3.5, 4.4), sharex=True)
    offs = np.linspace(-0.07, 0.07, len(ARMS))
    for k, (arm, lab, c, mk, ls) in enumerate(ARMS):
        r = m[m.algorithm == arm].sort_values("level")
        xx = r.level.values + offs[k]
        for ax, col in [(axs[0], "dns_exact"), (axs[1], "mean_f_incl_rejected")]:
            y = 100 * r[col].values
            lo, hi = 100 * r[col + "_ci_low"].values, 100 * r[col + "_ci_high"].values
            ax.errorbar(xx, y, yerr=[y - lo, hi - y], color=c, marker=mk, ms=3.6, ls=ls, lw=0.9,
                        capsize=0, elinewidth=0.7, label=lab)
    axs[0].axhline(15, color="k", lw=0.6, ls="--")
    axs[1].axhline(90, color="k", lw=0.6, ls="--")
    axs[0].set_ylabel("Demand not served, DNS (%)")
    axs[1].set_ylabel("Mean energy satisfaction $f$ (%)")
    axs[1].set_xlabel("Demand level (1.0$\\times$ = 627 kWh/day offered)")
    axs[1].set_xticks(LEVELS)
    axs[1].set_xticklabels(["1.0$\\times$\n627 kWh/d", "1.3$\\times$\n814 kWh/d", "1.6$\\times$\n1,002 kWh/d"])
    for ax in axs:
        ax.grid(True, axis="y")
    axs[0].text(0.01, 0.97, "(a)", transform=axs[0].transAxes, va="top")
    axs[1].text(0.01, 0.03, "(b)", transform=axs[1].transAxes, va="bottom")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, columnspacing=0.8, handletextpad=0.3,
               borderaxespad=0.2)
    fig.tight_layout(rect=(0, 0.095, 1, 1), h_pad=0.4)
    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}/paper_fig3_dns_f_levels.{ext}")
    plt.close(fig)
    print("wrote", f"{OUT}/paper_fig3_dns_f_levels.png")


if __name__ == "__main__":
    main()
