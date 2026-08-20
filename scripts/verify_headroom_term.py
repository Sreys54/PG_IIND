"""
Week 4 verification (user-directed, 2026-08-19): validate
reward_pi.headroom_penalty_term (design iteration 2) before it is trusted
for PI-TD3/TD3_HeadroomPenalty training. Five checks, each capable of
stopping the design, none skipped:

1. H (lookahead horizon) sensitivity: how the disagreement rate against
   get_how_overloaded() moves as H varies.
2. Predictability from the observation the policy actually sees
   (PublicPST) -- a term the policy cannot predict from its own
   observation is shaping noise, not signal.
3. Control-responsiveness: AFAP vs. Round Robin on the same cell -- is the
   term sensitive to control, or purely to exogenous demand?
4. SoC-gradient check: correlation against mean fleet SoC, to catch a
   perverse gradient (a term that drops simply because EVs were charged up
   fast would reward AFAP-like aggression, the opposite of the intent).
5. Spearman rank correlation against get_how_overloaded(), across multiple
   EVAL_DAYS x seeds, not a single episode.

Usage: PYTHONPATH=. python scripts/verify_headroom_term.py
"""
import numpy as np
from scipy.stats import spearmanr

from ev2gym.rl_agent.reward import SqTrError_TrPenalty_UserIncentives
from ev2gym.rl_agent.state import PublicPST
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

from ev2gym_thesis.rl.env_factory import make_env
from ev2gym_thesis.rl.reward_pi import headroom_penalty_term, PI_TD3_PHYSICS_WEIGHT
from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS

REFERENCE_CONFIG_PATH = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"


def run_episode(day, seed, agent_ctor, horizon=4, collect_state=False):
    """Steps one episode, returns per-step: vanilla reward, raw headroom
    term (at `horizon`), get_how_overloaded() sum, mean connected-fleet
    SoC, and (optionally) the PublicPST observation vector."""
    env = make_env(REFERENCE_CONFIG_PATH, day, seed)
    agent = agent_ctor(env)

    vanilla_s, headroom_s, overload_s, soc_s, obs_s = [], [], [], [], []

    def wrapper(env_, total_costs, user_satisfaction_list, *args):
        v = SqTrError_TrPenalty_UserIncentives(env_, total_costs, user_satisfaction_list, *args)
        h = headroom_penalty_term(env_, horizon=horizon)
        overload = sum(tr.get_how_overloaded() for tr in env_.transformers)
        socs = [ev.get_soc() for cs in env_.charging_stations for ev in cs.evs_connected if ev is not None]
        mean_soc = float(np.mean(socs)) if socs else np.nan
        vanilla_s.append(v)
        headroom_s.append(h)
        overload_s.append(overload)
        soc_s.append(mean_soc)
        if collect_state:
            obs_s.append(PublicPST(env_))
        return v

    env.reward_function = wrapper
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        _, _, done, _, _ = env.step(actions)
        if done:
            break

    result = (np.array(vanilla_s), np.array(headroom_s), np.array(overload_s), np.array(soc_s))
    if collect_state:
        return result + (obs_s,)
    return result


def check_1_horizon_sensitivity():
    print("=== Check 1: horizon H sensitivity ===")
    day, seed = EVAL_DAYS[0], SEEDS[0]
    for H in [1, 2, 4, 8]:
        vanilla, headroom, overload, soc = run_episode(day, seed, lambda e: ChargeAsFastAsPossible(), horizon=H)
        n_active = int((headroom < 0).sum())
        n_disagree = int(((headroom < 0) & (overload == 0)).sum())
        print(f"  H={H}: active steps={n_active}/{len(headroom)}, "
              f"disagree-with-overload (latent-only) steps={n_disagree}/{len(headroom)}")


def check_2_predictability():
    print("\n=== Check 2: predictability of headroom term from PublicPST observation ===")
    all_obs, all_target = [], []
    for day in EVAL_DAYS[:3]:
        for seed in SEEDS[:2]:
            vanilla, headroom, overload, soc, obs = run_episode(day, seed, lambda e: RoundRobin(e), collect_state=True)
            all_obs.extend(obs)
            all_target.extend(headroom)
    X = np.array(all_obs)
    y = np.array(all_target)
    # Simple closed-form OLS via lstsq (no sklearn dependency needed).
    X_design = np.hstack([X, np.ones((X.shape[0], 1))])
    coef, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
    y_pred = X_design @ coef
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    print(f"  n_samples={len(y)}, observation_dim={X.shape[1]}")
    print(f"  R^2 (linear regression, PublicPST observation -> headroom_penalty_term): {r2:.4f}")
    return r2


def check_3_control_responsiveness():
    print("\n=== Check 3: control-responsiveness (AFAP vs. Round Robin, same cell) ===")
    day, seed = EVAL_DAYS[0], SEEDS[0]
    _, headroom_afap, _, _ = run_episode(day, seed, lambda e: ChargeAsFastAsPossible())
    _, headroom_rr, _, _ = run_episode(day, seed, lambda e: RoundRobin(e))
    identical = np.allclose(headroom_afap, headroom_rr)
    diff = np.abs(headroom_afap - headroom_rr)
    print(f"  AFAP headroom term: sum={headroom_afap.sum():.3f}, nonzero steps={(headroom_afap<0).sum()}")
    print(f"  RR headroom term:   sum={headroom_rr.sum():.3f}, nonzero steps={(headroom_rr<0).sum()}")
    print(f"  Identical across both policies? {identical} (max abs diff={diff.max():.4f})")
    if identical:
        print("  WARNING: term is purely demand-determined on this cell, not control-sensitive.")
    else:
        print("  Term responds to control choice, not just exogenous demand -- as intended.")


def check_4_soc_gradient():
    print("\n=== Check 4: SoC-gradient check (correlation vs. mean fleet SoC) ===")
    for agent_name, ctor in [("AFAP", lambda e: ChargeAsFastAsPossible()), ("RoundRobin", lambda e: RoundRobin(e))]:
        day, seed = EVAL_DAYS[0], SEEDS[0]
        _, headroom, _, soc = run_episode(day, seed, ctor)
        valid = ~np.isnan(soc)
        if valid.sum() > 1:
            corr = np.corrcoef(headroom[valid], soc[valid])[0, 1]
            print(f"  {agent_name}: corr(headroom_term, mean_fleet_SoC) = {corr:.4f} (n={valid.sum()})")
            if corr < -0.3:
                print(f"    WARNING: notably negative -- charging up fast reduces the penalty; "
                      f"could reward AFAP-like aggression.")
        else:
            print(f"  {agent_name}: insufficient valid steps for correlation.")


def check_5_multiday_spearman():
    print("\n=== Check 5: Spearman rank correlation vs. get_how_overloaded(), multi-day/seed ===")
    rhos = []
    for day in EVAL_DAYS[:3]:
        for seed in SEEDS[:2]:
            vanilla, headroom, overload, soc = run_episode(day, seed, lambda e: ChargeAsFastAsPossible())
            pi = vanilla + PI_TD3_PHYSICS_WEIGHT * headroom
            rho, _ = spearmanr(vanilla, pi)
            rhos.append(rho)
            n_disagree = int(((headroom < 0) & (overload == 0)).sum()) + int(((headroom == 0) & (overload > 0)).sum())
            print(f"  day={day}, seed={seed}: Spearman(vanilla, PI)={rho:.4f}, "
                  f"disagreement steps={n_disagree}/{len(headroom)}")
    rhos = np.array(rhos)
    print(f"\n  Spearman across {len(rhos)} (day,seed) cells: mean={rhos.mean():.4f}, "
          f"min={rhos.min():.4f}, max={rhos.max():.4f}")
    if rhos.max() >= 0.9999:
        print("  WARNING: at least one cell still shows Spearman ~1.0 -- check that cell individually.")


if __name__ == "__main__":
    check_1_horizon_sensitivity()
    check_2_predictability()
    check_3_control_responsiveness()
    check_4_soc_gradient()
    check_5_multiday_spearman()
