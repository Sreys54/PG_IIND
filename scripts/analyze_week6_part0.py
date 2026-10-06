"""
Week 6, Part 0, Part B: analysis of the extended TD3_vanilla training run.

Reads only (i) the raw per-seed logs in
experiments/phase2_algorithms/results/week6_part0/ (versioned), (ii) the
registry's analysis_row=True rows, (iii) each run's state.json (gitignored,
used only to cross-check the rule recomputed here from the versioned logs),
and (iv) the original 60k runs' learning_curve.csv (gitignored, used only
for the first-60k reproduction comparison).

Reuses, never re-implements:
  - ev2gym_thesis.rl.extended_training.convergence_index / select_primary_index
  - scripts.analyze_week5_results.master_comparison_table / optimality_gap /
    ens_and_compliance (parametrized in Week 6 Part 0; defaults unchanged)
  - ev2gym_thesis.stats_utils.paired_cluster_bootstrap_ci (cluster = scenario seed)

Writes results/week6_part0_*.csv (xlsx exports: scripts/export_week6_part0_results_xlsx.py).

Usage: PYTHONPATH=. python scripts/analyze_week6_part0.py
"""
import json
import os

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import TRAIN_SEEDS
from ev2gym_thesis.rl import extended_training as et
from ev2gym_thesis.rl import price_data_cache
from ev2gym_thesis.stats_utils import paired_cluster_bootstrap_ci

from scripts import analyze_week5_results as w5

LOG_DIR = "experiments/phase2_algorithms/results/week6_part0"
MODELS_DIR = "experiments/phase2_algorithms/models"
OUT = "results/week6_part0_{}.csv"
N_BOOTSTRAP = 10_000
ROLLING_EPISODES = 100          # SB3's ep_info_buffer window, as in the original learning curves
REPRO_WINDOW = (30_000, 60_000)  # plateau segment compared against the original run

PRIMARY = {s: f"TD3_vanilla_extended_ts{s}" for s in TRAIN_SEEDS}
LAST = {s: f"TD3_vanilla_extended_last_ts{s}" for s in TRAIN_SEEDS}
NEW60K = {s: f"TD3_vanilla_new60k_ts{s}" for s in TRAIN_SEEDS}
ORIGINAL = {s: f"TD3_vanilla_ts{s}" for s in TRAIN_SEEDS}
FAMILIES = {"TD3_vanilla (original 60k, trained pre-setpoint-fix)": ORIGINAL,
            "TD3_vanilla_new60k (new run @60k, post-fix)": NEW60K,
            "TD3_vanilla_extended (primary checkpoint)": PRIMARY,
            "TD3_vanilla_extended_last (last checkpoint)": LAST}
REFERENCE_ARMS = ["ChargeAsFastAsPossible", "RoundRobin", "MPC_TrackingG2V",
                  "Optimal_Oracle_Tracking", "Optimal_Oracle_Balanced"]
COMPARE_METRICS = w5.HEADLINE_METRICS + ["total_energy_charged", "energy_user_satisfaction"]
ALL_ARMS = (REFERENCE_ARMS + [ORIGINAL[s] for s in TRAIN_SEEDS] + [NEW60K[s] for s in TRAIN_SEEDS]
            + [PRIMARY[s] for s in TRAIN_SEEDS] + [LAST[s] for s in TRAIN_SEEDS])


def load_logs():
    val = {s: pd.read_csv(f"{LOG_DIR}/TD3_vanilla_extended_ts{s}_validation.csv") for s in TRAIN_SEEDS}
    eps = {s: pd.read_csv(f"{LOG_DIR}/TD3_vanilla_extended_ts{s}_episodes.csv") for s in TRAIN_SEEDS}
    return val, eps


def rolling_reward_at(eps, timesteps):
    """Mean raw episode reward over the last <=100 episodes completed by
    each timestep -- the same statistic LearningCurveCallback logged for the
    original runs (SB3 ep_info_buffer), so the two curves are comparable."""
    ends = eps["timesteps_at_end"].to_numpy()
    r = eps["episode_reward_raw"].to_numpy()
    out = []
    for t in timesteps:
        k = np.searchsorted(ends, t, side="right")
        out.append(r[max(0, k - ROLLING_EPISODES):k].mean() if k else np.nan)
    return np.array(out)


# doc:begin convergence_table
def convergence_table(val, eps):
    rows = []
    orig_means = {}
    for s in TRAIN_SEEDS:
        lc = pd.read_csv(f"{MODELS_DIR}/TD3_vanilla_ts{s}/learning_curve.csv")
        seg = lc[(lc.timesteps >= REPRO_WINDOW[0]) & (lc.timesteps <= REPRO_WINDOW[1])]
        orig_means[s] = (seg.mean_episode_reward.mean(), seg.mean_episode_reward.std(ddof=1))
    orig_between_seed_range = (min(m for m, _ in orig_means.values()), max(m for m, _ in orig_means.values()))
    for s in TRAIN_SEEDS:
        v, e = val[s], eps[s]
        m = v.criterion_value.tolist()
        ci = et.convergence_index(m)
        pi = et.select_primary_index(m, ci)
        state = json.load(open(f"{MODELS_DIR}/TD3_vanilla_extended_ts{s}/state.json"))
        assert ci == state["conv_eval_index"] and pi == state["primary_eval_index"], \
            f"ts{s}: rule recomputed from the versioned log disagrees with the live run's state.json"
        last_w = np.array(m[-et.CONVERGENCE_WINDOW:])
        best = int(np.argmin(m))
        ts_grid = np.arange(REPRO_WINDOW[0], REPRO_WINDOW[1] + 1, 500)
        new_seg = rolling_reward_at(e, ts_grid)
        o_mean, o_std = orig_means[s]
        n_mean = float(np.nanmean(new_seg))
        # Labelled reproduction rule: the new run's 30k-60k mean training
        # reward is "within run-to-run noise" if it falls inside the range
        # spanned by the three ORIGINAL seeds' 30k-60k means, widened by the
        # largest original within-segment std. Environment caveat: the
        # original runs used the pre-fix power-setpoint generator.
        tol = max(sd for _, sd in orig_means.values())
        within = orig_between_seed_range[0] - tol <= n_mean <= orig_between_seed_range[1] + tol
        rows.append({
            "train_seed": s,
            "convergence_step": v.timesteps.iloc[ci] if ci is not None else "not converged",
            "total_steps": int(v.timesteps.iloc[-1]),
            "wall_clock_h": v.wall_clock_s.iloc[-1] / 3600,
            "n_validations": len(v),
            "n_training_episodes": len(e),
            "median_train_steps_per_s": v.train_steps_per_s_since_last_eval.median(),
            "min_train_steps_per_s": v.train_steps_per_s_since_last_eval.min(),
            "val_te_mean_last_w": last_w.mean(),
            "val_te_std_last_w": last_w.std(ddof=1),
            "val_te_at_60k": v.loc[v.timesteps == 60_000, "criterion_value"].iloc[0],
            "primary_step": int(v.timesteps.iloc[pi]) if pi is not None else None,
            "val_te_primary": m[pi] if pi is not None else None,
            "val_overload_primary": v.total_transformer_overload.iloc[pi] if pi is not None else None,
            "val_energy_user_sat_primary": v.energy_user_satisfaction.iloc[pi] if pi is not None else None,
            "last_step": int(v.timesteps.iloc[-1]),
            "val_te_last": m[-1],
            "val_overload_last": v.total_transformer_overload.iloc[-1],
            "val_energy_user_sat_last": v.energy_user_satisfaction.iloc[-1],
            "best_ever_step": int(v.timesteps.iloc[best]),
            "val_te_best_ever": m[best],
            "train_reward_30k_60k_new": n_mean,
            "train_reward_30k_60k_original_same_seed": o_mean,
            "first_60k_within_original_noise": bool(within),
            "eval_seed_draws_rejected": int(e.rejected_eval_seed_draws.notna().sum()),
            "contaminated_training_episodes": int(e.scenario_seed_in_eval_seeds.sum()),
            "resumes": len(state.get("resumes", [])),
            "stop_reason": state["stop_reason"],
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT.format("convergence"), index=False)
    print(out.T.to_string())
    return out
# doc:end convergence_table


def validation_log(val):
    frames = []
    for s in TRAIN_SEEDS:
        v = val[s].drop(columns=["checkpoint_path", "criterion_name"]).copy()
        v.insert(0, "train_seed", s)
        frames.append(v)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(OUT.format("validation_log"), index=False)
    return out


def paired(df, a, b, metric):
    A = df[df.algorithm == a][["seed", "day_type", metric]]
    B = df[df.algorithm == b][["seed", "day_type", metric]]
    m = A.merge(B, on=["seed", "day_type"], suffixes=("_a", "_b"))
    return m[f"{metric}_a"].astype(float).to_numpy(), m[f"{metric}_b"].astype(float).to_numpy(), m.seed.to_numpy()


def _arm_mean(df, arms, name):
    """Per-cell mean across the three training seeds of one checkpoint
    family -- the METHOD-level comparison (the thesis claim is about the
    training procedure, not one seed)."""
    sub = df[df.algorithm.isin(arms)].copy()
    agg = sub.groupby(["seed", "day_type"])[COMPARE_METRICS].apply(lambda g: g.astype(float).mean()).reset_index()
    assert (sub.groupby(["seed", "day_type"]).size() == len(arms)).all()
    agg["algorithm"] = name
    return agg


# doc:begin bootstrap_comparisons
def bootstrap_comparisons(df):
    """B minus A, cluster bootstrap (cluster = scenario seed), per metric.
    Primary comparison: extended vs. the new run's own 60k checkpoint
    (same seed, same post-fix environment). Secondary: vs. the original
    60k rows (trained pre-fix), Round Robin, AFAP, MPC_TrackingG2V, oracle."""
    fam = pd.concat([_arm_mean(df, list(arms.values()), f"MEAN3[{label}]") for label, arms in FAMILIES.items()])
    dfx = pd.concat([df, fam], ignore_index=True)
    pairs = []
    for s in TRAIN_SEEDS:
        pairs += [("primary", NEW60K[s], PRIMARY[s]), ("primary", NEW60K[s], LAST[s]),
                  ("secondary (pre-fix reference)", ORIGINAL[s], PRIMARY[s]),
                  ("secondary (pre-fix reference)", ORIGINAL[s], NEW60K[s])]
        pairs += [("vs reference arm", ref, PRIMARY[s]) for ref in REFERENCE_ARMS]
    M = {k: f"MEAN3[{k}]" for k in FAMILIES}
    ext, last, n60, orig = (M["TD3_vanilla_extended (primary checkpoint)"], M["TD3_vanilla_extended_last (last checkpoint)"],
                            M["TD3_vanilla_new60k (new run @60k, post-fix)"], M["TD3_vanilla (original 60k, trained pre-setpoint-fix)"])
    pairs += [("primary, 3-seed mean", n60, ext), ("primary, 3-seed mean", n60, last),
              ("secondary (pre-fix reference), 3-seed mean", orig, ext),
              ("secondary (pre-fix reference), 3-seed mean", orig, n60)]
    pairs += [("vs reference arm, 3-seed mean", ref, ext) for ref in REFERENCE_ARMS]
    rows = []
    for kind, a, b in pairs:
        for metric in COMPARE_METRICS:
            va, vb, cl = paired(dfx, a, b, metric)
            r = paired_cluster_bootstrap_ci(va, vb, cl, n_bootstrap=N_BOOTSTRAP, seed=0)
            rows.append({"comparison": kind, "baseline_A": a, "candidate_B": b, "metric": metric,
                         "mean_A": va.mean(), "mean_B": vb.mean(), "diff_B_minus_A": r["point_estimate"],
                         "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                         "ci_excludes_zero": bool(r["ci_low"] > 0 or r["ci_high"] < 0),
                         "n_pairs": r["n_pairs"], "n_clusters": r["n_clusters"]})
    out = pd.DataFrame(rows)
    out.to_csv(OUT.format("bootstrap_comparisons"), index=False)
    key = out[(out.metric.isin(["tracking_error", "total_transformer_overload", "average_user_satisfaction"]))
              & out.comparison.str.contains("3-seed")]
    print(key[["comparison", "baseline_A", "candidate_B", "metric", "diff_B_minus_A", "ci_low", "ci_high",
               "n_clusters"]].to_string(index=False))
    return out
# doc:end bootstrap_comparisons


def train_seed_dispersion(df):
    """Across-training-seed spread of per-seed means, per checkpoint family."""
    rows = []
    for label, arms in FAMILIES.items():
        for metric in COMPARE_METRICS:
            means = np.array([df[df.algorithm == arms[s]][metric].astype(float).mean() for s in TRAIN_SEEDS])
            rows.append({"family": label, "metric": metric,
                         **{f"mean_ts{s}": v for s, v in zip(TRAIN_SEEDS, means)},
                         "across_seed_mean": means.mean(), "across_seed_std": means.std(ddof=1),
                         "across_seed_range": means.max() - means.min(),
                         "relative_range_pct": (means.max() - means.min()) / abs(means.mean()) * 100 if means.mean() else np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(OUT.format("train_seed_dispersion"), index=False)
    print(out[out.metric.isin(["tracking_error", "total_transformer_overload"])][
        ["family", "metric", "across_seed_mean", "across_seed_range", "relative_range_pct"]].to_string(index=False))
    return out


def final_model_selection(conv):
    """Pre-registered rule: the single final model is the primary checkpoint
    of the seed with the best (lowest) validation criterion."""
    c = conv.dropna(subset=["val_te_primary"])
    best = c.loc[c.val_te_primary.idxmin()]
    s, step = int(best.train_seed), int(best.primary_step)
    sel = {"rule": "primary checkpoint of the seed with the best validation tracking_error",
           "algorithm_name": PRIMARY[s], "train_seed": s, "checkpoint_step": step,
           "checkpoint_path": f"{MODELS_DIR}/TD3_vanilla_extended_ts{s}/checkpoints/td3_vanilla_extended_ts{s}_{step}_steps.zip",
           "val_te": float(best.val_te_primary), "status": "rule output -- adoption is the user's decision (Part B verdict)"}
    with open(OUT.format("final_model_selection").replace(".csv", ".json"), "w") as f:
        json.dump(sel, f, indent=2)
    print(sel)
    return sel


if __name__ == "__main__":
    price_data_cache.enable()  # requested_energy_by_cell builds 100 envs; output-identical by a pinned test
    val, eps = load_logs()
    conv = convergence_table(val, eps)
    validation_log(val)
    df = w5.load_grid_df()
    missing = [a for a in ALL_ARMS if (df.algorithm == a).sum() != 100]
    assert not missing, f"arms without exactly 100 analysis rows: {missing}"
    w5.master_comparison_table(df, algos=ALL_ARMS, out_path=OUT.format("master_comparison"))
    w5.optimality_gap(df, algos=[a for a in ALL_ARMS if not a.startswith("Optimal_Oracle")],
                      out_path=OUT.format("optimality_gap"))
    bootstrap_comparisons(df)
    train_seed_dispersion(df)
    w5.ens_and_compliance(df, algos=ALL_ARMS, out_path=OUT.format("ens_compliance"),
                          requested_energy_out_path=OUT.format("requested_energy_by_cell"))
    final_model_selection(conv)
    print("Week 6 Part 0 analysis complete.")
