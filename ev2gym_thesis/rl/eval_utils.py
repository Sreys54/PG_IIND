"""
Week 3, Entregable 5/9: loading a trained TD3 checkpoint for evaluation, and
running one deterministic evaluation episode.

The classic VecNormalize bug this guards against: training with
VecNormalize computes running observation/reward statistics; if those
statistics aren't reloaded at evaluation time (training=False,
norm_reward=False), the agent sees observations on a completely different
scale than it was trained on and looks like it "worked in training,
collapsed in evaluation." load_trained_agent refuses to proceed silently if
the sidecar stats file is missing -- see
ev2gym_thesis/tests/test_rl_infrastructure.py for the test that pins this
behavior.
"""
import os

from stable_baselines3 import TD3
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


def vecnormalize_path_for(model_path: str) -> str:
    """Convention: {model_path_without_extension}_vecnormalize.pkl, saved
    next to the model checkpoint by
    ev2gym_thesis/rl/callbacks.py's CheckpointCallback(save_vecnormalize=True)."""
    base, _ = os.path.splitext(model_path)
    return f"{base}_vecnormalize.pkl"


# doc:begin load_trained_agent
def load_trained_agent(model_path: str, env, vecnormalize_path: str = None):
    """Load a TD3 model plus its VecNormalize statistics for evaluation.

    Raises FileNotFoundError loudly if the VecNormalize stats file doesn't
    exist next to the model checkpoint -- silently evaluating with
    mismatched (or default-initialized) normalization statistics is exactly
    the bug this function exists to make impossible.

    `env` must be a single, un-normalized environment (e.g. straight from
    env_factory.make_env); this function wraps it in DummyVecEnv +
    VecNormalize.load(...) and forces training=False, norm_reward=False --
    reward normalization is a training-time convenience only and must never
    affect evaluated/reported metrics.
    """
    if vecnormalize_path is None:
        vecnormalize_path = vecnormalize_path_for(model_path)
    if not os.path.exists(vecnormalize_path):
        raise FileNotFoundError(
            f"VecNormalize statistics file not found at {vecnormalize_path!r} "
            f"for checkpoint {model_path!r}. Evaluating a VecNormalize-trained "
            f"model without its saved statistics silently uses wrong-scale "
            f"observations -- refusing to proceed. Statistics are saved "
            f"automatically by ev2gym_thesis/rl/callbacks.py's "
            f"CheckpointCallback(save_vecnormalize=True)."
        )
    venv = DummyVecEnv([lambda: env])
    venv = VecNormalize.load(vecnormalize_path, venv)
    venv.training = False
    venv.norm_reward = False
    model = TD3.load(model_path, env=venv)
    return model, venv
# doc:end load_trained_agent
