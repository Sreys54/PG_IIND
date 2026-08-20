"""
Week 4 verification (user-directed, 2026-08-19): before launching PI-TD3
training, prove reward_pi.SqTrError_TrPenalty_UserIncentives_PI is not a
near-duplicate of the vanilla arm's SqTrError_TrPenalty_UserIncentives --
both already penalize transformer overload (the vanilla reward's own
`-100 * tr.get_how_overloaded()` term), so the concern is real: if the two
series are near-perfectly correlated, the two arms are the same experiment
wearing different names.

Method: step through ONE real episode (ChargeAsFastAsPossible on
station_v0_bogota, seed 0, 2022-01-17 -- known to overload this station,
so the regime where the two reward functions could differ is actually
exercised, not trivially zero throughout). At each step, computes BOTH
reward functions on the exact same (env, total_costs, user_satisfaction_list,
invalid_action_punishment) tuple EV2Gym's own _calculate_reward passes to
env.reward_function -- captured via a wrapper substituted for
env.reward_function, not a reimplementation of env.step()'s internals.

Usage: PYTHONPATH=. python scripts/verify_pi_reward_differs.py
"""
import numpy as np

from ev2gym.rl_agent.reward import SqTrError_TrPenalty_UserIncentives
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

from ev2gym_thesis.rl.env_factory import make_env
from ev2gym_thesis.rl.reward_pi import SqTrError_TrPenalty_UserIncentives_PI, anticipated_overload_term, PI_TD3_PHYSICS_WEIGHT

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"
REFERENCE_DAY = (2022, 1, 17)
REFERENCE_SEED = 0


def run_and_capture():
    env = make_env(REFERENCE_CONFIG_PATH, REFERENCE_DAY, REFERENCE_SEED)

    vanilla_series, pi_series, physics_only_series, overload_series = [], [], [], []

    def capturing_wrapper(env_, total_costs, user_satisfaction_list, *args):
        v = SqTrError_TrPenalty_UserIncentives(env_, total_costs, user_satisfaction_list, *args)
        p = SqTrError_TrPenalty_UserIncentives_PI(env_, total_costs, user_satisfaction_list, *args)
        physics_only = PI_TD3_PHYSICS_WEIGHT * anticipated_overload_term(env_)
        overload = sum(tr.get_how_overloaded() for tr in env_.transformers)
        vanilla_series.append(v)
        pi_series.append(p)
        physics_only_series.append(physics_only)
        overload_series.append(overload)
        return v  # episode dynamics/termination follow the vanilla reward, same as the reference AFAP run

    env.reward_function = capturing_wrapper

    agent = ChargeAsFastAsPossible()
    done = False
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        _, _, done, _, _ = env.step(actions)
        if done:
            break

    return (np.array(vanilla_series), np.array(pi_series),
            np.array(physics_only_series), np.array(overload_series))


if __name__ == "__main__":
    vanilla, pi, physics_only, overload = run_and_capture()

    n_steps = len(vanilla)
    n_overload_steps = int((overload > 0).sum())
    n_physics_active_steps = int((physics_only < 0).sum())

    print(f"Episode: {n_steps} steps, ChargeAsFastAsPossible, station_v0_bogota, seed=0, 2022-01-17")
    print(f"Steps with actual overload (get_how_overloaded() > 0): {n_overload_steps}/{n_steps}")
    print(f"Steps with physics term active (connected-fleet potential > capacity): {n_physics_active_steps}/{n_steps}")
    print(f"Physics term active but NOT yet overloaded (latent demand exceeds capacity, "
          f"but the agent's chosen action avoided realized overload this step): "
          f"{int(((physics_only < 0) & (overload == 0)).sum())}/{n_steps}")

    diff = pi - vanilla
    print(f"\nvanilla reward:      sum={vanilla.sum():.2f}, min={vanilla.min():.2f}, max={vanilla.max():.2f}")
    print(f"PI reward:           sum={pi.sum():.2f}, min={pi.min():.2f}, max={pi.max():.2f}")
    print(f"PI - vanilla (the physics contribution): sum={diff.sum():.2f}, "
          f"nonzero steps={int((diff != 0).sum())}/{n_steps}")
    print(f"Matches PI_TD3_PHYSICS_WEIGHT * anticipated_overload_term exactly? "
          f"{np.allclose(diff, physics_only)}")

    corr = np.corrcoef(vanilla, pi)[0, 1]
    print(f"\nPearson correlation, vanilla vs. PI, full episode: {corr:.6f}")

    # Ranking agreement (Spearman-style): does the step ordering by reward value agree?
    from scipy.stats import spearmanr
    rho, _ = spearmanr(vanilla, pi)
    print(f"Spearman rank correlation, vanilla vs. PI: {rho:.6f}")

    # Restrict to the steps where the two functions could plausibly diverge --
    # near/at capacity -- since across a whole day dominated by non-overload
    # steps (where both are byte-identical, tracking+satisfaction terms
    # equal and physics term=0), any correlation would trivially be ~1.0
    # regardless of whether the physics term does anything. The informative
    # comparison is restricted to steps where at least one of the two
    # overload-related signals (get_how_overloaded or the physics margin)
    # is active.
    relevant = (overload > 0) | (physics_only < 0)
    n_relevant = int(relevant.sum())
    print(f"\nRestricted to the {n_relevant} steps where EITHER signal is active "
          f"(the only steps where the two functions COULD differ):")
    if n_relevant > 1:
        corr_relevant = np.corrcoef(vanilla[relevant], pi[relevant])[0, 1]
        rho_relevant, _ = spearmanr(vanilla[relevant], pi[relevant])
        print(f"  Pearson correlation (relevant steps only): {corr_relevant:.6f}")
        print(f"  Spearman rank correlation (relevant steps only): {rho_relevant:.6f}")
        ratio = np.abs(diff[relevant]) / (np.abs(vanilla[relevant]) + 1e-9)
        print(f"  |physics contribution| / |vanilla reward| on these steps: "
              f"mean={ratio.mean():.4f}, max={ratio.max():.4f}")
    else:
        print("  Fewer than 2 relevant steps -- cannot compute correlation on this episode; "
              "re-run with a heavier-overload scenario.")
