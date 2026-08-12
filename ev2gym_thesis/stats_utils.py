"""
Aggregation and paired-bootstrap statistics for the Week 2+ figure module
(Deliverable 4). Verified against synthetic fixtures with analytically
known results in ev2gym_thesis/tests/test_stats_utils.py -- NOT against
the registry, which is still being backfilled. Do not call these against
real registry data until the backfill is complete and the evaluation grid
is balanced (see 00_lab_log.md, 2026-08-12).
"""
import numpy as np


# doc:begin mean_ci
def mean_ci(values, ci: float = 0.95):
    """Mean and a normal-approximation confidence interval (mean +/- z*SEM).
    Used for f02_metrics_bars-style grouped bars with error bars.

    Returns (mean, lower, upper). With fewer than 2 samples, lower/upper
    equal the mean (a zero-width interval, not a crash).
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    m = float(np.mean(values))
    if n < 2:
        return m, m, m
    sem = float(np.std(values, ddof=1)) / np.sqrt(n)
    z = _normal_z(ci)
    return m, m - z * sem, m + z * sem


def _normal_z(ci: float) -> float:
    """z-score for a two-sided normal CI, for the handful of confidence
    levels this project uses -- avoids a scipy.stats dependency for one
    lookup."""
    table = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    if ci not in table:
        raise ValueError(f"Unsupported CI level {ci}; supported: {sorted(table)}")
    return table[ci]
# doc:end mean_ci


def paired_bootstrap_ci(values_a, values_b, n_bootstrap: int = 10000,
                         ci: float = 0.95, seed: int = None, statistic="diff"):
    """Paired bootstrap confidence interval for the difference between two
    equal-length, index-aligned samples (e.g. algorithm X vs. AFAP, matched
    cell-by-cell on the same (seed, eval_day) grid -- NOT independent-sample
    means, since both were evaluated on identical scenarios).

    statistic: "diff" for (b - a) per pair, or "pct" for (b - a) / a * 100.

    Returns a dict: {"point_estimate", "ci_low", "ci_high", "n_pairs"}.
    Resamples PAIRS (indices), not values_a/values_b independently, which
    is what makes this "paired" rather than an independent-sample bootstrap.
    """
    # doc:begin paired_bootstrap
    values_a = np.asarray(values_a, dtype=float)
    values_b = np.asarray(values_b, dtype=float)
    if len(values_a) != len(values_b):
        raise ValueError("values_a and values_b must be the same length (paired)")
    n = len(values_a)
    if n == 0:
        raise ValueError("No pairs to bootstrap")

    rng = np.random.default_rng(seed)

    def _stat(a, b):
        if statistic == "diff":
            return np.mean(b - a)
        elif statistic == "pct":
            return np.mean((b - a) / a) * 100
        else:
            raise ValueError(f"Unknown statistic {statistic!r}")

    point_estimate = float(_stat(values_a, values_b))

    boot_stats = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot_stats[i] = _stat(values_a[idx], values_b[idx])

    alpha = 1 - ci
    lo, hi = np.percentile(boot_stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])

    return {
        "point_estimate": point_estimate,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "n_pairs": n,
    }
# doc:end paired_bootstrap
