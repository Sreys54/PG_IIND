"""
Week 3, Entregable 2: EV2Gym environment construction for RL training and
evaluation. Never touches ev2gym/models/ev2gym_env.py or
ev2gym/rl_agent/*.py -- only imports their published, documented interfaces
(reward_function/state_function constructor kwargs, confirmed in the Week 3
preflight, see thesis_docs/chapters/00_lab_log.md's 2026-08-12 Week 3 entry).

No Gymnasium/SB3 compatibility shim is needed: the preflight confirmed
EV2Gym already satisfies the full Gymnasium API (reset() -> (obs, info),
step() -> (obs, reward, terminated, truncated, info), gymnasium.Env
subclass) -- see the same lab-log entry.
"""
import random

import gymnasium as gym

from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.rl_agent.reward import SqTrError_TrPenalty_UserIncentives
from ev2gym.rl_agent.state import PublicPST

from ev2gym_thesis.config_utils import make_day_config
from ev2gym_thesis.eval_protocol import TRAIN_DAYS, EVAL_DAYS

EVAL_DAY_CONFIG_DIR = "experiments/phase2_algorithms/configs/_tmp_eval_day_configs"
TRAIN_DAY_CONFIG_DIR = "experiments/phase2_algorithms/configs/_tmp_train_day_configs"

# doc:begin default_reward_state
# Chosen in thesis_docs/chapters/03_rl_baseline.md (Entregable 3) -- see that
# chapter for the full justification against this thesis's Public/PST
# problem variant and the rejected alternatives (SquaredTrackingErrorReward
# alone; the V2G/Business reward and state families).
DEFAULT_REWARD_FN = SqTrError_TrPenalty_UserIncentives
DEFAULT_STATE_FN = PublicPST
# doc:end default_reward_state


# doc:begin make_env
def make_env(config_path: str, day: tuple, scenario_seed: int,
             reward_fn=DEFAULT_REWARD_FN, state_fn=DEFAULT_STATE_FN,
             day_config_dir: str = EVAL_DAY_CONFIG_DIR) -> EV2Gym:
    """Build one EV2Gym instance for a single (config, day, scenario_seed)
    cell.

    Uses config_utils.make_day_config -- the exact same mechanism
    scripts/backfill_registry.py uses for AFAP/Round Robin -- so an RL agent
    evaluated on (config_path, day, scenario_seed) sees the literal same
    scenario a heuristic evaluated on that cell saw, not just a "similar"
    one. This is what makes the Entregable 6 comparison a paired comparison
    rather than an independent-sample one.
    """
    year, month, day_of_month = day
    day_config_path = make_day_config(config_path, year, month, day_of_month, day_config_dir)
    return EV2Gym(
        config_file=day_config_path,
        seed=scenario_seed,
        save_replay=False,
        save_plots=False,
        reward_function=reward_fn,
        state_function=state_fn,
    )
# doc:end make_env


# doc:begin training_day_cycling_env
class TrainingDayCyclingEnv(gym.Env):
    """A gym.Env that samples a new calendar day from TRAIN_DAYS every
    reset() -- never from EVAL_DAYS -- so a TD3 agent trained against this
    env sees variety across days instead of overfitting to a single one.

    Design decision: EV2Gym itself cannot vary its simulated day across
    resets of the SAME instance unless config['random_day']=True, and that
    flag samples uniformly across ~1.5 years with no way to restrict it to
    the TRAIN_DAYS pool (verified by reading ev2gym_env.py's reset(), see
    the Week 3 preflight entry in 00_lab_log.md) -- so day-cycling requires
    constructing a fresh EV2Gym instance per episode. Rejected alternative:
    directly mutating a single long-lived EV2Gym instance's internal
    sim_starting_date attribute between resets. This would be cheaper
    (skips re-reading the day config YAML and the Netherlands price CSV
    every episode) but relies on internal EV2Gym state that isn't a
    published interface and isn't verified safe for every loader
    (load_transformers, load_ev_charger_profiles, etc.) -- a correctness
    risk not worth taking for the sake of the day-construction overhead,
    which the Entregable 4 timing calibration measures directly.

    Sampling: round-robin (deterministic cycling through TRAIN_DAYS in
    order), not random-with-seed. Rejected alternative: random.choice with a
    fixed RNG seed. Round-robin was chosen because the Week 3 CPU budget
    (Entregable 4) caps total training to at most a few hundred episodes per
    training seed against a 20-day pool -- random sampling at that scale can
    by chance under-represent or skip some days entirely, while round-robin
    guarantees every TRAIN_DAYS date is seen an equal (+/-1) number of times
    regardless of how many episodes the budget allows. sample_mode="random"
    is still available (rng_seed required) for a future ablation if desired,
    but is not the default.
    """

    metadata = {"render_modes": []}

    def __init__(self, config_path: str, reward_fn=DEFAULT_REWARD_FN,
                 state_fn=DEFAULT_STATE_FN, sample_mode: str = "round_robin",
                 rng_seed: int = None, day_config_dir: str = TRAIN_DAY_CONFIG_DIR):
        super().__init__()
        if sample_mode not in ("round_robin", "random"):
            raise ValueError(f"Unknown sample_mode {sample_mode!r}; expected 'round_robin' or 'random'")
        if sample_mode == "random" and rng_seed is None:
            raise ValueError("sample_mode='random' requires an explicit rng_seed for reproducibility")

        self.config_path = config_path
        self.reward_fn = reward_fn
        self.state_fn = state_fn
        self.sample_mode = sample_mode
        self.day_config_dir = day_config_dir
        self._rng = random.Random(rng_seed)
        self._rr_index = 0
        self.days_seen = []  # every day sampled so far, for the anti-leakage test

        # Build one probe instance purely to publish action_space/
        # observation_space before the first reset() -- SB3 needs these at
        # construction time. Neither space depends on which day is loaded
        # (both are fixed by port count / v2g_enabled and observation
        # feature layout), so any TRAIN_DAYS day is representative.
        probe_env = self._build_env_for_day(TRAIN_DAYS[0], seed=0)
        self.action_space = probe_env.action_space
        self.observation_space = probe_env.observation_space
        self._env = probe_env

    def _next_day(self) -> tuple:
        if self.sample_mode == "round_robin":
            day = TRAIN_DAYS[self._rr_index % len(TRAIN_DAYS)]
            self._rr_index += 1
        else:
            day = self._rng.choice(TRAIN_DAYS)
        assert day not in EVAL_DAYS, (
            f"Sampled day {day} is in EVAL_DAYS -- this must never happen "
            f"(train/eval leakage). TRAIN_DAYS/EVAL_DAYS disjointness is "
            f"already asserted at eval_protocol import time; reaching this "
            f"means TRAIN_DAYS itself was mutated after import."
        )
        self.days_seen.append(day)
        return day

    def _build_env_for_day(self, day: tuple, seed: int) -> EV2Gym:
        year, month, day_of_month = day
        day_config_path = make_day_config(self.config_path, year, month, day_of_month, self.day_config_dir)
        return EV2Gym(
            config_file=day_config_path,
            seed=seed,
            save_replay=False,
            save_plots=False,
            reward_function=self.reward_fn,
            state_function=self.state_fn,
        )

    def reset(self, seed=None, options=None):
        day = self._next_day()
        self._env = self._build_env_for_day(day, seed=seed)
        return self._env.reset(seed=seed)

    def step(self, action):
        return self._env.step(action)

    def render(self):
        return self._env.render()

    def close(self):
        pass
# doc:end training_day_cycling_env


def make_training_env(config_path: str, reward_fn=DEFAULT_REWARD_FN,
                       state_fn=DEFAULT_STATE_FN, sample_mode: str = "round_robin",
                       rng_seed: int = None,
                       day_config_dir: str = TRAIN_DAY_CONFIG_DIR) -> TrainingDayCyclingEnv:
    """Factory returning a single TrainingDayCyclingEnv instance, ready to be
    wrapped in a DummyVecEnv (+ optionally VecNormalize) by the training
    script -- see ev2gym_thesis/rl/config_rl.py for the VecNormalize design
    decision."""
    return TrainingDayCyclingEnv(
        config_path=config_path,
        reward_fn=reward_fn,
        state_fn=state_fn,
        sample_mode=sample_mode,
        rng_seed=rng_seed,
        day_config_dir=day_config_dir,
    )
