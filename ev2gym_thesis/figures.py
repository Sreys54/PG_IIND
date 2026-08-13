"""
Shared figure infrastructure for Week 2+ (Deliverable 4). matplotlib only
-- no seaborn, no styling that depends on a network fetch.

ALGORITHM_STYLE: one fixed colour/marker per algorithm, defined once here.
An algorithm keeps the same colour in every figure of every week; new
algorithms get appended to this dict, never reassigned.
"""
import datetime
import os

from ev2gym_thesis.registry import get_git_commit

FIGURES_DIR = "figures"

# doc:begin algorithm_style
ALGORITHM_STYLE = {
    "ChargeAsFastAsPossible": {"color": "#d62728", "marker": "o", "label": "AFAP"},
    "RoundRobin": {"color": "#1f77b4", "marker": "s", "label": "Round Robin"},
    # Week 3 additions (append only, per project convention -- AFAP/Round
    # Robin's color/marker above are untouched). Three distinct shades of
    # green for the three TD3 training seeds (same algorithm, different
    # training runs -- visually grouped by hue, distinguished by marker),
    # and a neutral gray for the random-policy negative control so it never
    # visually competes with the algorithms actually being compared.
    "TD3_vanilla_ts100": {"color": "#2ca02c", "marker": "^", "label": "TD3 (seed 100)"},
    "TD3_vanilla_ts101": {"color": "#5fd35f", "marker": "v", "label": "TD3 (seed 101)"},
    "TD3_vanilla_ts102": {"color": "#1b6b1b", "marker": "D", "label": "TD3 (seed 102)"},
    "RandomPolicy": {"color": "#7f7f7f", "marker": "x", "label": "Random (control)"},
    # Append new algorithms here as they're added (PI-TD3, optimal
    # reference, ...) -- never reassign an existing entry's color/marker
    # once a figure has used it.
}
# doc:end algorithm_style


# doc:begin total_reward_guardrail
# Week 3, Entregable 3 (thesis_docs/chapters/03_rl_baseline.md S3.5):
# total_reward is computed under whichever reward_function an EV2Gym run was
# built with. Weeks 1-2's heuristic rows and Week 3+'s RL rows do NOT share
# a reward function (see that chapter section), so total_reward is not a
# comparable quantity across rows that used different ones -- comparing it
# anyway would silently plot apples against oranges under a shared axis
# label. New registry rows record their reward function by name in the
# `notes` column (e.g. "reward=SqTrError_TrPenalty_UserIncentives,..."); rows
# with no such marker (Weeks 1-2) used the environment's own default.
_DEFAULT_REWARD_FN_NAME = "SquaredTrackingErrorReward"  # EV2Gym.__init__'s own default, implicit for rows whose notes don't declare a reward function


def _reward_fn_name(row: dict) -> str:
    for part in (row.get("notes") or "").split(","):
        if part.startswith("reward="):
            return part.split("=", 1)[1]
    return _DEFAULT_REWARD_FN_NAME


def assert_total_reward_comparable(rows: list, metric: str = "total_reward") -> None:
    """No-op for any metric other than total_reward. For total_reward,
    raises if `rows` mixes runs built with different reward functions.
    Call this at the top of any per-metric loop in a figure-generating
    function, before computing/plotting values for that metric, so a future
    figure that adds total_reward to a comparison fails loudly instead of
    silently comparing incompatible values."""
    if metric != "total_reward":
        return
    reward_fns = {_reward_fn_name(r) for r in rows}
    if len(reward_fns) > 1:
        raise ValueError(
            f"Cannot compare/plot total_reward across rows built with "
            f"different reward functions: {sorted(reward_fns)}. See "
            f"thesis_docs/chapters/03_rl_baseline.md S3.5 -- total_reward is "
            f"only a comparable quantity within a single reward function."
        )
# doc:end total_reward_guardrail


def style_for(algorithm: str) -> dict:
    if algorithm not in ALGORITHM_STYLE:
        raise KeyError(
            f"No ALGORITHM_STYLE entry for {algorithm!r}. Add one to "
            f"ev2gym_thesis/figures.py's ALGORITHM_STYLE dict -- don't "
            f"reassign an existing algorithm's color/marker to make room."
        )
    return ALGORITHM_STYLE[algorithm]


# doc:begin write_caption
def write_caption(name: str, what_it_shows: str, n_runs: int, configs: list,
                   algorithms: list, extra: str = "") -> str:
    """Every figure gets a generated (never hand-written) sidecar caption
    stating what it shows, how many runs are behind it, which
    configs/algorithms are included, the git commit, and the generation
    timestamp -- so a figure can never silently go stale relative to the
    data that produced it.
    """
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = f"{FIGURES_DIR}/{name}.caption.md"
    lines = [
        f"# {name}",
        "",
        what_it_shows,
        "",
        f"- Runs behind this figure: {n_runs}",
        f"- Configs: {', '.join(configs)}",
        f"- Algorithms: {', '.join(algorithms)}",
        f"- Git commit: {get_git_commit()}",
        f"- Generated: {datetime.datetime.utcnow().isoformat()}Z",
    ]
    if extra:
        lines += ["", extra]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path
# doc:end write_caption
