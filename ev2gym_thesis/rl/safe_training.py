"""
Week 8 (redesigned RL): the training environment of the projected TD3 agent.

SafeTrainingEnv is extended_training.SeedLoggingTrainingEnv (TRAIN_DAYS
round-robin, a fresh EV2Gym per episode, the evaluation-seed leakage guard
and the per-episode scenario log) with one change: every action is passed
through safety.project_actions before EV2Gym steps. SB3 stores the policy's
own action in the replay buffer and the environment enforces the projection,
the usual way to impose a hard action constraint in an off-policy learner:
the critic learns Q(s, a) of the projected outcome of a.

The share of steps on which the projection actually cut the action is
attached to the terminal step's info dict (projection_active_share).

Never touches ev2gym/models/*.py or ev2gym/rl_agent/*.py.
"""
from ev2gym_thesis.rl.extended_training import SeedLoggingTrainingEnv
from ev2gym_thesis.rl.safety import project_actions


# doc:begin safe_training_env
class SafeTrainingEnv(SeedLoggingTrainingEnv):

    def reset(self, seed=None, options=None):
        self._proj_steps = self._proj_active = 0
        return super().reset(seed=seed, options=options)

    def step(self, action):
        projected, pinfo = project_actions(self._env, action)
        self._proj_steps += 1
        self._proj_active += int(pinfo["active"])
        obs, reward, terminated, truncated, info = super().step(projected)
        if terminated or truncated:
            info = dict(info)
            info["projection_active_share"] = self._proj_active / max(self._proj_steps, 1)
        return obs, reward, terminated, truncated, info
# doc:end safe_training_env
