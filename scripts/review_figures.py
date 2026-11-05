"""
Week 8 advisor review: Block C figures (PNG + PDF + caption .txt each),
experiments/phase4_review/results/figures/.

  w8_f1_load_profiles      station power on one typical day (seed 0, weekday,
                           1.0x) for AFAP, PS, RR-TA and TD3_safe, with the
                           100 kW rating (re-simulated here with the recorder);
  w8_f2_dns_satisfaction   exact DNS and mean energy satisfaction f (incl.
                           rejected) by level for every C1 arm, 95% CIs (C6);
  w8_f3_capacity_threshold DNS and mean f vs arrivals/day for RR-TA and PS at
                           8 and 10 ports (C4 bisection logs), with targets;
  w8_f4_td3_safe_validation validation energy per checkpoint for each
                           TD3_safe seed, convergence and final checkpoint.
Colours: the dataviz reference categorical palette, one fixed slot per arm
(validated: worst adjacent CVD Delta E 9.1 on the light surface); markers
and direct labels carry identity as well (two slots are below 3:1 contrast).
A panel whose inputs do not exist yet is skipped.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = "experiments/phase4_review/results/figures"
SLOT = {"AFAP": ("#2a78d6", "o"), "PS": ("#eb6834", "s"), "RR-TA": ("#1baf7a", "D"), "TD3_safe": ("#eda100", "^"),
        "FIX12.5": ("#e87ba4", "v"), "RR": ("#008300", "P"), "MPC-soft": ("#6250d6", "X"), "Oracle-E": ("#e34948", "*"),
        "RR+S": ("#7a7a75", "p"), "Random+S": ("#a3a29b", "h"), "MPC-soft-est": ("#4b4a45", "<")}
INK, MUTED = "#26251f", "#6b6a63"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.grid": True, "grid.color": "#e5e4df", "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2})


def style(arm):
    for k, v in SLOT.items():
        if arm == k or arm.startswith(k + "_"):
            return v
    return ("#7a7a75", ".")


def save(fig, name, caption):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}/{name}.{ext}", dpi=200, bbox_inches="tight")
    open(f"{OUT}/{name}_caption.txt", "w", encoding="utf-8").write(caption.strip() + "\n")
    plt.close(fig)
    print("wrote", name)


def f1_load_profiles(td3=None):
    from ev2gym_thesis.demand import review_configs as rc
    from ev2gym_thesis.metrics import service
    from scripts import review_dc
    review_dc.process_hooks()
    if td3:
        from ev2gym_thesis.rl import config_safe as cfg
        review_dc.register_td3_safe("TD3_safe", td3, cfg.STATE_FNS["service_causal"])
    cfgp = rc.write_config(1.0)
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    hours = None
    for arm in ["AFAP", "PS", "RR-TA"] + (["TD3_safe"] if td3 else []):
        review_dc.run_case(arm, cfgp, 0, (2022, 1, 17), "station")
        rec = review_dc.LAST_RECORD["episode"]
        p = np.array([s["power_kw"] for s in rec["steps"]])
        hours = 5 + np.arange(len(p)) * 0.25
        c, m = style(arm)
        ax.step(hours, p, where="post", color=c, label=arm, linewidth=1.6 if arm != "AFAP" else 2)
    ax.axhline(100, color=INK, linewidth=1, linestyle="--")
    ax.text(5.1, 103, "100 kW rating", color=INK, fontsize=8)
    ticks = np.arange(5, 30, 3)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(t) % 24:02d}:00" for t in ticks])
    ax.set_xlabel("Clock time (the simulated day runs 05:00 to 05:00)")
    ax.set_ylabel("Station power (kW)")
    ax.legend(frameon=False, ncol=4, loc="upper left", bbox_to_anchor=(0, 1.15))
    save(fig, "w8_f1_load_profiles", """Station power on one day (scenario seed 0, weekday 2022-01-17, 1.0x =
627 kWh/day offered, station-level arrivals, 42-min DC sessions), 8 ports and the 100 kW
transformer. AFAP ignores the rating; PS (AFAP + proportional safety layer), RR-TA and TD3_safe
stay at or below 0.999 x 100 kW. One illustrative day, not a statistic.""")


def f2_dns_satisfaction():
    p = "experiments/phase4_review/C/C6_master_all_levels.csv"
    if not os.path.exists(p):
        return
    t = pd.read_csv(p)
    t = t[~t.algorithm.str.startswith("TD3_safe_ts")]  # non-carried seeds: dispersion, in the C6 tables only
    arms = [a for a in SLOT if a in set(t.algorithm)] + sorted(set(t.algorithm) - set(SLOT))
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharex=True)
    for ax, (m, lab, target) in zip(axes, [("dns_exact", "Demand not served, exact (%)", 15),
                                           ("mean_f_incl_rejected", "Mean energy satisfaction f incl. rejected (%)", 90)]):
        for i, a in enumerate(arms):
            g = t[t.algorithm == a].sort_values("level")
            c, mk = style(a)
            x = g.level.values + (i - len(arms) / 2) * 0.012
            ax.errorbar(x, 100 * g[m], yerr=[100 * (g[m] - g[f"{m}_ci_low"]), 100 * (g[f"{m}_ci_high"] - g[m])],
                        color=c, marker=mk, markersize=6, linewidth=1, capsize=0, label=a)
        ax.axhline(target, color=INK, linewidth=1, linestyle="--")
        ax.set_ylabel(lab)
        ax.set_xticks(sorted(t.level.unique()))
        ax.set_xlabel("Demand level (x 627 kWh/day offered)")
    axes[1].legend(frameon=False, fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
    save(fig, "w8_f2_dns_satisfaction", """Exact demand not served (left) and mean energy satisfaction f including
rejected drivers at f = 0 (right) for every C1 arm at 1.0x, 1.3x and 1.6x (627 / 814 / 1,002 kWh/day
offered), 8 ports, 100 kW. Points: ratio of totals over 100 days; bars: 95% cluster-bootstrap
intervals over the scenario seed (n_clusters = 50, 10,000 resamples, per comparison). Dashed:
targets (DNS <= 15%, f >= 90%). Arms are offset horizontally for legibility; MPC-soft and Oracle-E
coincide to within 0.1 kWh per day.""")


def f3_capacity():
    files = sorted(f for f in glob.glob("experiments/phase4_review/C4/threshold_*.json") if "_d3" not in f)
    if not files:
        return
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharex=True)
    for f in files:
        d = json.load(open(f))
        log = pd.DataFrame(d["log"]).sort_values("arrivals_per_day")
        c, mk = style(d["arm"])
        ls = "-" if d["ports"] == 8 else ":"
        lab = f"{d['arm']}, {d['ports']} ports"
        axes[0].plot(log.arrivals_per_day, 100 * log.dns, color=c, marker=mk, linestyle=ls, label=lab)
        axes[1].plot(log.arrivals_per_day, 100 * log.mean_f_all, color=c, marker=mk, linestyle=ls, label=lab)
        if d["threshold_arrivals_per_day"]:
            for ax in axes:
                ax.axvline(d["threshold_arrivals_per_day"], color=c, linewidth=0.8, linestyle=ls)
    axes[0].axhline(15, color=INK, linestyle="--", linewidth=1)
    axes[1].axhline(90, color=INK, linestyle="--", linewidth=1)
    axes[0].set_ylabel("Demand not served, exact (%)")
    axes[1].set_ylabel("Mean f incl. rejected (%)")
    for ax in axes:
        ax.set_xlabel("Offered arrivals per day")
    axes[1].legend(frameon=False, fontsize=7)
    save(fig, "w8_f3_capacity_threshold", """Capacity threshold of RR-TA and PS with the 100 kW transformer at 8 and 10
ports (station-level arrivals, 42-min DC sessions): every level evaluated by the bisection, 100 days each
(point estimates, ratio of totals). A level passes when the DNS 95% upper bound is <= 15% and the mean-f
95% lower bound is >= 90%; vertical lines mark the largest passing arrivals/day.""")


def f4_td3(root="C:/ev2gym_runs/w8_td3_safe"):
    files = sorted(glob.glob(f"{root}/logs/TD3_safe_dc42_ts*_validation.csv"))
    if not files:
        return
    sel = json.load(open("results/review_td3_safe_selection.json")) if os.path.exists(
        "results/review_td3_safe_selection.json") else {"seeds": {}}
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    greys = ["#eda100", "#b37a00", "#7a5300"]
    carried = str(sel.get("carried_model", {}).get("train_seed", ""))
    for f, c, ls in zip(files, greys, ["-", "--", "-."]):
        v = pd.read_csv(f)
        seed = f.split("_ts")[1].split("_")[0]
        ax.plot(v.timesteps / 1000, v.criterion_value, color=c, linewidth=1.4, linestyle=ls,
                label=f"seed {seed}" + (" (carried model)" if seed == carried else ""))
        info = sel["seeds"].get(seed) or sel["seeds"].get(int(seed)) if sel["seeds"] else None
        if info and info.get("final_step"):
            y = float(v.loc[v.timesteps == info["final_step"], "criterion_value"].iloc[0])
            ax.plot(info["final_step"] / 1000, y, marker="*", markersize=11, color=c, markeredgecolor=INK)
        if info and info.get("convergence_step"):
            ax.axvline(info["convergence_step"] / 1000, color=c, linestyle=":", linewidth=1)
    ax.set_xlabel("Training steps (thousands)")
    ax.set_ylabel("Validation energy delivered (kWh/day)")
    ax.legend(frameon=False)
    save(fig, "w8_f4_td3_safe_validation", """TD3_safe validation curves (DC regime, station-level arrivals, 1.0x):
mean energy delivered on the 20 validation cells (seeds 1,000,000-1,000,009 x one weekday and one weekend
day) at every 10,000-step checkpoint, deterministic policy with the safety layer. Dotted: convergence
declaration (2%/5% rule on 50,000-step windows; seeds 100 and 101 both converge at 130,000 steps, so their
lines coincide); star: each seed's final checkpoint (best validation value at or after convergence,
config_safe.py). Each run stops 100,000 steps after convergence. The carried model is the seed whose final
checkpoint has the best validation value (seed 100, 150,000 steps); selection uses validation only.""")


def f5_td3_long(root="C:/ev2gym_runs/w8_td3_safe_long"):
    files = sorted(glob.glob(f"{root}/logs/TD3_safe_dc42_ts*_validation.csv"))
    if not files or not os.path.exists("results/review_td3_safe_long_selection.json"):
        return
    sel = json.load(open("results/review_td3_safe_long_selection.json"))["seeds"]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for f, c, ls in zip(files, ["#eda100", "#b37a00", "#7a5300"], ["-", "--", "-."]):
        v = pd.read_csv(f)
        seed = f.split("_ts")[1].split("_")[0]
        ax.plot(v.timesteps / 1e6, v.criterion_value, color=c, linewidth=1.2, linestyle=ls, label=f"seed {seed}")
        b = sel.get(seed)
        if b:
            ax.plot(b["bestval_step"] / 1e6, b["bestval_validation_energy_kwh"], marker="*", markersize=11, color=c,
                    markeredgecolor=INK)
    ax.axvline(0.15, color=INK, linewidth=0.8, linestyle=":")
    ax.text(0.16, ax.get_ylim()[0] + 2, "carried TD3_safe" + chr(10) + "(seed 100, 150k)", color=INK, fontsize=7)
    ax.set_xlabel("Training steps (millions)")
    ax.set_ylabel("Validation energy delivered (kWh/day)")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "w8_f5_td3_safe_long_validation", """TD3_safe long-budget sensitivity (pre-registered; seeds retrained from
scratch to 2,000,000 steps with no stopping rule): mean energy delivered on the 20 validation cells at every
10,000-step checkpoint. Stars: best validation value per seed (tested on the C3 test grid together with the
2,000,000-step checkpoint). Dotted: the carried TD3_safe checkpoint (seed 100, 150,000 steps, C3 rule), which
does not change. Validation peaks between 310,000 and 580,000 steps and drifts back to the C3 plateau.""")


if __name__ == "__main__":
    which = sys.argv[1:] or ["f1", "f2", "f3", "f4", "f5"]
    td3 = None
    if os.path.exists("results/review_td3_safe_selection.json"):
        td3 = json.load(open("results/review_td3_safe_selection.json")).get("carried_model", {}).get("checkpoint")
    if "f1" in which:
        f1_load_profiles(td3)
    if "f2" in which:
        f2_dns_satisfaction()
    if "f3" in which:
        f3_capacity()
    if "f4" in which:
        f4_td3()
    if "f5" in which:
        f5_td3_long()
