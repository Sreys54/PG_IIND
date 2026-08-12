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
    # Append new algorithms here as they're added (MPC, RL, ...) -- never
    # reassign an existing entry's color/marker once a figure has used it.
}
# doc:end algorithm_style


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
