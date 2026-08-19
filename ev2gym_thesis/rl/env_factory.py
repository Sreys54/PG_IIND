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
from stable_baselines3.common.monitor import Monitor

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


# doc:begin reset_for_evaluation
def _ev_population_signature(env) -> list:
    """A comparable summary of the EV arrival scenario an env instance
    currently holds. Used only to verify reset_for_evaluation's determinism
    guarantee, not a general-purpose utility."""
    return [
        (ev.time_of_arrival, ev.time_of_departure, ev.battery_capacity, ev.desired_capacity)
        for ev in env.EVs_profiles
    ]


def reset_for_evaluation(env, scenario_seed: int):
    """The only sanctioned way to start an evaluation episode on an env built
    by make_env(). Every evaluation stepper (TD3, RandomPolicy, and the
    Week 4 oracle's) must call this instead of env.reset() directly.

    Week 3 correction (see thesis_docs/chapters/00_lab_log.md): plain
    gymnasium Env.reset(seed=None) -- which is what env.reset() and
    env.reset(seed=None) both do -- makes EV2Gym draw a FRESH
    np.random.randint(0, 1_000_000) and regenerate self.EVs_profiles from
    scratch; it does NOT fall back to reusing the seed the env was
    constructed with. scripts/evaluate_rl.py's _TD3Stepper and
    _RandomPolicyStepper both called reset this way, so all 200 of Week 3's
    TD3/RandomPolicy evaluation episodes silently ran against a
    re-randomized scenario instead of the (config, day, scenario_seed) cell
    their registry row claims -- confirmed empirically (14 EVs at
    construction vs. 16 EVs with completely different arrival/departure
    times, after one bare env.reset()).

    The population check below is a real, always-on assertion, not a
    comment -- the entire point of this bug is that "the code looks right"
    was already tried once and was wrong. scripts/backfill_registry.py's
    AFAP/Round Robin runs were unaffected (they already pass seed=seed
    explicitly), confirmed with the same population-diff method.
    """
    construction_population = _ev_population_signature(env)
    obs, info = env.reset(seed=scenario_seed)
    post_reset_population = _ev_population_signature(env)
    assert post_reset_population == construction_population, (
        f"reset_for_evaluation: EV population after reset(seed={scenario_seed}) "
        f"does not match the population env was constructed with -- the "
        f"evaluated scenario would silently diverge from the (config, day, "
        f"scenario_seed) cell this run is registered under. This is exactly "
        f"the Week 3 bug documented in 00_lab_log.md; do not bypass this check."
    )
    return obs, info
# doc:end reset_for_evaluation


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

    # doc:begin training_day_cycling_env_init
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

        # Probe instance purely to publish action_space/observation_space
        # before the first reset() (SB3 needs these at construction time) --
        # neither space depends on which day is loaded, so any TRAIN_DAYS
        # day is representative.
        probe_env = self._build_env_for_day(TRAIN_DAYS[0], seed=0)
        self.action_space = probe_env.action_space
        self.observation_space = probe_env.observation_space
        self._env = probe_env
    # doc:end training_day_cycling_env_init

    # doc:begin training_day_cycling_env_sampling
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

    def reset(self, seed=None, options=None):
        day = self._next_day()
        self._env = self._build_env_for_day(day, seed=seed)
        return self._env.reset(seed=seed)
    # doc:end training_day_cycling_env_sampling

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

    def step(self, action):
        return self._env.step(action)

    def render(self):
        return self._env.render()

    def close(self):
        pass


def make_training_env(config_path: str, reward_fn=DEFAULT_REWARD_FN,
                       state_fn=DEFAULT_STATE_FN, sample_mode: str = "round_robin",
                       rng_seed: int = None,
                       day_config_dir: str = TRAIN_DAY_CONFIG_DIR) -> Monitor:
    """Factory returning a Monitor-wrapped TrainingDayCyclingEnv, ready to
    be wrapped in a DummyVecEnv (+ optionally VecNormalize) by the training
    script -- see ev2gym_thesis/rl/config_rl.py for the VecNormalize design
    decision.

    The Monitor wrap (stable_baselines3.common.monitor.Monitor) is required,
    not cosmetic: SB3's off-policy algorithms only populate
    model.ep_info_buffer -- the mean-episode-reward source
    ev2gym_thesis/rl/callbacks.py's LearningCurveCallback reads -- from an
    "episode" key that Monitor adds to each step's info dict on episode
    end. A bare (unwrapped) VecEnv never gets this key, so
    ep_info_buffer silently stays empty and the learning-curve CSV would
    silently log nothing -- discovered exactly this way while smoke-testing
    scripts/train_td3.py before the Entregable 5 training run, not assumed.
    TrainingDayCyclingEnv-specific attributes (e.g. days_seen, used by
    scripts/calibrate_td3_timing.py) are still reachable through the wrapper
    via env.unwrapped.days_seen -- gymnasium's Wrapper does NOT transparently
    forward arbitrary custom attributes by plain dot-access in this
    gymnasium version (confirmed empirically), so callers must use
    .unwrapped for TrainingDayCyclingEnv-specific state.
    """
    env = TrainingDayCyclingEnv(
        config_path=config_path,
        reward_fn=reward_fn,
        state_fn=state_fn,
        sample_mode=sample_mode,
        rng_seed=rng_seed,
        day_config_dir=day_config_dir,
    )
    return Monitor(env)
