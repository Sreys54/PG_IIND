"""
Week 3, Entregable 2: training callbacks -- periodic checkpointing (so an
interrupted training run is resumable, not lost) and a CSV learning-curve
log (timesteps, mean episode reward, mean episode length, wall-clock
elapsed), independent of stdout.

Checkpointing itself is NOT reimplemented: stable_baselines3's own
CheckpointCallback already does this correctly, including
save_vecnormalize=True, which saves the VecNormalize running statistics
alongside each model checkpoint -- exactly the artifact Entregable 5's
"normalization stats must be saved next to the model" requirement needs.
Only the learning-curve CSV logger is custom, since SB3 has no built-in
timesteps-indexed CSV of this shape.
"""
import csv
import os
import time

from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback


# doc:begin make_checkpoint_callback
def make_checkpoint_callback(save_dir: str, save_freq_steps: int, name_prefix: str) -> CheckpointCallback:
    """Periodic checkpoint, including VecNormalize stats when the training
    env is VecNormalize-wrapped. save_freq_steps is in environment steps, as
    SB3's own CheckpointCallback expects (n_envs=1 in this project, so no
    save_freq // n_envs adjustment is needed -- see SB3's own docstring
    note about that adjustment, which only applies to n_envs > 1)."""
    os.makedirs(save_dir, exist_ok=True)
    return CheckpointCallback(
        save_freq=save_freq_steps,
        save_path=save_dir,
        name_prefix=name_prefix,
        save_replay_buffer=False,  # not needed for reproducing reported metrics; would bloat committed/regenerable artifacts for no evaluation benefit
        save_vecnormalize=True,
    )
# doc:end make_checkpoint_callback


# doc:begin learning_curve_callback
class LearningCurveCallback(BaseCallback):
    """Appends one row per log_freq_steps to a CSV: timesteps, the mean
    episode reward and mean episode length over SB3's own rolling
    ep_info_buffer (last <=100 completed episodes, SB3's standard window),
    and wall-clock seconds elapsed since training start. Written
    incrementally (flushed every row), not buffered in memory and written
    once at the end, so a crash or interruption doesn't lose the curve."""

    def __init__(self, csv_path: str, log_freq_steps: int, verbose: int = 0):
        super().__init__(verbose)
        self.csv_path = csv_path
        self.log_freq_steps = log_freq_steps
        self._start_time = None
        self._file = None
        self._writer = None

    def _on_training_start(self) -> None:
        self._start_time = time.time()
        os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
        self._file = open(self.csv_path, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["timesteps", "mean_episode_reward", "mean_episode_length", "elapsed_wall_clock_s"])

    def _on_step(self) -> bool:
        if self.num_timesteps % self.log_freq_steps == 0 and len(self.model.ep_info_buffer) > 0:
            mean_reward = sum(ep["r"] for ep in self.model.ep_info_buffer) / len(self.model.ep_info_buffer)
            mean_length = sum(ep["l"] for ep in self.model.ep_info_buffer) / len(self.model.ep_info_buffer)
            elapsed = time.time() - self._start_time
            self._writer.writerow([self.num_timesteps, mean_reward, mean_length, round(elapsed, 2)])
            self._file.flush()
        return True

    def _on_training_end(self) -> None:
        if self._file is not None:
            self._file.close()
# doc:end learning_curve_callback


def make_callbacks(checkpoint_dir: str, checkpoint_freq_steps: int, name_prefix: str,
                    learning_curve_csv_path: str, learning_curve_log_freq_steps: int):
    """Combines both callbacks into the list SB3's model.learn(callback=...) expects."""
    return [
        make_checkpoint_callback(checkpoint_dir, checkpoint_freq_steps, name_prefix),
        LearningCurveCallback(learning_curve_csv_path, learning_curve_log_freq_steps),
    ]
