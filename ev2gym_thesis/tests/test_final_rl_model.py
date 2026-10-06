"""
Week 6, Part 0: tests for the extended training of the selected RL policy.

Every test calls the real production code (ev2gym_thesis/rl/
extended_training.py, ev2gym_thesis/rl/price_data_cache.py,
scripts/train_td3_extended.py) -- no re-implementations of the rule or the
training loop inside the test.

Run: PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_final_rl_model -v
"""
import json
import os
import re
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd

from ev2gym_thesis.eval_protocol import EVAL_DAYS, SEEDS, TRAIN_DAYS, TRAIN_SEEDS
from ev2gym_thesis.rl import extended_training as et
from ev2gym_thesis.rl import price_data_cache

W = et.CONVERGENCE_WINDOW
EARLIEST = 2 * W - 1 + et.CONVERGENCE_CONSECUTIVE - 1  # 11 with the brief's constants


# ---------------------------------------------------------------------------
# Convergence rule on synthetic curves with known answers
# ---------------------------------------------------------------------------
class TestConvergenceRule(unittest.TestCase):
    def test_constants_match_brief(self):
        assert (W, et.CONVERGENCE_REL_MEAN_TOL, et.CONVERGENCE_REL_STD_TOL, et.CONVERGENCE_CONSECUTIVE) == (5, 0.02, 0.05, 3)
        assert et.EVAL_FREQ_STEPS == 10_000 and et.CONFIRMATION_MARGIN_STEPS == 100_000
        assert EARLIEST == 11

    def test_flat_curve_converges_at_earliest_possible_evaluation(self):
        assert et.convergence_index([30_000.0] * 20) == EARLIEST

    def test_too_short_never_converges(self):
        assert et.convergence_index([30_000.0] * EARLIEST) is None

    def test_steady_drift_never_converges(self):
        # 3% decline per evaluation: window means differ by ~15%.
        assert et.convergence_index([30_000.0 * 0.97 ** k for k in range(40)]) is None

    def test_oscillation_above_std_threshold_never_converges(self):
        # +/-10% alternation: std/mean ~ 0.11 > 5%, means stay equal.
        assert et.convergence_index([30_000.0 * (1.1 if k % 2 else 0.9) for k in range(40)]) is None

    def test_oscillation_below_std_threshold_converges(self):
        assert et.convergence_index([30_000.0 * (1.02 if k % 2 else 0.98) for k in range(20)]) == EARLIEST

    def test_step_change_converges_only_after_both_windows_on_new_plateau(self):
        # 10 evaluations at 100, then 85. At k=18 the previous window still
        # holds one 100: mean 88 vs 85 = 3.4% > 2% -> fails. k=19,20,21 hold.
        m = [100.0] * 10 + [85.0] * 15
        assert not et.convergence_conditions_at(m, 18)
        assert all(et.convergence_conditions_at(m, k) for k in (19, 20, 21))
        assert et.convergence_index(m) == 21

    def test_consecutive_run_resets_on_a_failure(self):
        m = [100.0] * 11 + [140.0] + [100.0] * 20
        # k=9,10 hold (2 in a row), k=11 fails (spike), the spike then sits
        # in "last W" for k=11..15 and in "previous W" for k=16..20.
        assert et.convergence_conditions_at(m, 9) and et.convergence_conditions_at(m, 10)
        assert not et.convergence_conditions_at(m, 11)
        idx = et.convergence_index(m)
        assert idx is not None and idx >= 21
        assert all(et.convergence_conditions_at(m, k) for k in range(idx - 2, idx + 1))

    def test_zero_mean_window_raises(self):
        with self.assertRaises(ValueError):
            et.convergence_conditions_at([0.0] * 10, 9)

    def test_primary_selection_is_best_at_or_after_convergence(self):
        m = [50.0] + [100.0] * 11 + [99.0, 98.5, 101.0]
        assert et.select_primary_index(m, 11, lower_is_better=True) == 13     # 50.0 before convergence is ignored
        assert et.select_primary_index(m, 11, lower_is_better=False) == 14
        assert et.select_primary_index(m, None) is None


# ---------------------------------------------------------------------------
# Seed / day disjointness
# ---------------------------------------------------------------------------
class TestDisjointness(unittest.TestCase):
    def test_proof_passes(self):
        proof = et.disjointness_proof()
        assert proof["validation intersect eval seeds"] == []
        assert proof["n validation cells"] == 20

    def test_validation_training_evaluation_sets_disjoint(self):
        v = set(et.VALIDATION_SEEDS)
        assert v.isdisjoint(SEEDS) and v.isdisjoint(TRAIN_SEEDS)
        assert set(et.VALIDATION_DAYS).isdisjoint(EVAL_DAYS)
        assert set(et.VALIDATION_DAYS).isdisjoint(TRAIN_DAYS)
        assert min(v) >= et.TRAIN_SCENARIO_SEED_HIGH_EXCLUSIVE

    def test_training_draw_range_matches_ev2gym_source(self):
        # Pins the premise of the by-construction argument: if EV2Gym's
        # unseeded draw ever changes, this fails instead of the proof
        # silently going stale.
        src = open("ev2gym/models/ev2gym_env.py").read()
        reset_body = src[src.index("def reset(self, seed=None"):]
        reset_body = reset_body[:reset_body.index("np.random.seed(self.seed)")]
        assert re.search(r"self\.seed = np\.random\.randint\(0, 1000000\)", reset_body)
        assert et.TRAIN_SCENARIO_SEED_HIGH_EXCLUSIVE == 1_000_000


# ---------------------------------------------------------------------------
# Price-table cache: identical outputs, no RNG side effects
# ---------------------------------------------------------------------------
def _rollout(seed, day, cfg_dir):
    from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
    env = make_env(et.REFERENCE_CONFIG_PATH, day, seed, day_config_dir=cfg_dir)
    reset_for_evaluation(env, seed)
    rng = np.random.default_rng(0)
    done, info = False, None
    while not done:
        _, _, te, tr, info = env.step(rng.random(env.action_space.shape))
        done = te or tr
    return (env.charge_prices.copy(), env.power_setpoints.copy(), env.current_power_usage.copy(),
            {k: info[k] for k in et.VALIDATION_LOG_METRICS}, np.random.get_state()[1].copy())


class _TmpDirCase(unittest.TestCase):
    def setUp(self):
        # %TEMP% is short; the session scratchpad path exceeds Windows MAX_PATH.
        self.tmp = tempfile.mkdtemp(prefix="w6p0_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestPriceCache(_TmpDirCase):
  def test_price_cache_is_output_identical(self):
    tmp_path = self.tmp
    cells = [(et.VALIDATION_SEEDS[0], et.VALIDATION_DAYS[0]), (7, EVAL_DAYS[1])]
    price_data_cache.disable()
    ref = [_rollout(s, d, str(tmp_path)) for s, d in cells]
    price_data_cache.enable()
    try:
        _rollout(3, TRAIN_DAYS[7], str(tmp_path))  # warm the cache on another date
        got = [_rollout(s, d, str(tmp_path)) for s, d in cells]
    finally:
        price_data_cache.disable()
    for a, b in zip(ref, got):
        for x, y in zip(a[:3], b[:3]):
            np.testing.assert_array_equal(x, y)
        assert a[3] == b[3]
        np.testing.assert_array_equal(a[4], b[4])


# ---------------------------------------------------------------------------
# Training script: monitor does not perturb training; resume path
# ---------------------------------------------------------------------------
def _train(root, *extra):
    from scripts import train_td3_extended
    train_td3_extended.main(["--seed", "100", "--deadline", "2099-01-01T00:00:00-05:00",
                             "--output-root", str(root), "--n-validation-cells", "1", "--price-cache", *extra])
    price_data_cache.disable()
    return os.path.join(str(root), "logs", "TD3_vanilla_extended_ts100")


class TestTrainingScript(_TmpDirCase):
  def test_validation_monitor_does_not_change_training_trajectory(self):
    tmp_path = self.tmp
    with_val = _train(os.path.join(tmp_path, "a"), "--max-steps", "500", "--eval-freq", "150", "--buffer-freq", "1000")
    without = _train(os.path.join(tmp_path, "b"), "--max-steps", "500", "--eval-freq", "1000", "--buffer-freq", "1000")
    ea, eb = pd.read_csv(with_val + "_episodes.csv"), pd.read_csv(without + "_episodes.csv")
    assert len(ea) == len(eb) >= 4
    assert ea.train_scenario_seed.tolist() == eb.train_scenario_seed.tolist()
    assert ea.train_day.tolist() == eb.train_day.tolist()
    assert ea.train_scenario_seed.iloc[0] == 100  # SB3 seeds the first episode with the training seed
    assert len(pd.read_csv(with_val + "_validation.csv")) == 4  # 150, 300, 450, final 500


  def test_resume_path(self):
    tmp_path = self.tmp
    from scripts import train_td3_extended
    logs = _train(tmp_path, "--max-steps", "400", "--eval-freq", "100", "--buffer-freq", "300")
    model_dir = os.path.join(str(tmp_path), "models", "TD3_vanilla_extended_ts100")
    step, *_ = train_td3_extended.latest_resume_point(model_dir)
    assert step == 400  # finalize() also saves a resumable buffer
    # Simulate an interruption after the 300-step buffer save: drop the 400 one.
    for f in os.listdir(os.path.join(model_dir, "replay_buffers")):
        if "_400_" in f:
            os.remove(os.path.join(model_dir, "replay_buffers", f))
    assert train_td3_extended.latest_resume_point(model_dir)[0] == 300
    _train(tmp_path, "--resume", "--max-steps", "600", "--eval-freq", "100", "--buffer-freq", "300")
    val = pd.read_csv(logs + "_validation.csv")
    assert val.timesteps.tolist() == [100, 200, 300, 400, 500, 600]  # 400 re-trained, not duplicated
    eps = pd.read_csv(logs + "_episodes.csv")
    assert eps.timesteps_at_end.is_monotonic_increasing
    post = eps[eps.timesteps_at_end > 300]
    assert len(post) >= 2 and 100 not in post.train_scenario_seed.tolist()  # no silent re-seed after load
    state = json.load(open(os.path.join(model_dir, "state.json")))
    assert state["resumes"][0]["from_step"] == 300 and state["last_step"] == 600

  def test_vecnormalize_saved_with_every_checkpoint_and_frozen_in_validation(self):
    from stable_baselines3.common.vec_env import VecNormalize
    from ev2gym_thesis.rl.eval_utils import vecnormalize_path_for
    _train(self.tmp, "--max-steps", "400", "--eval-freq", "100", "--buffer-freq", "100")
    model_dir = os.path.join(self.tmp, "models", "TD3_vanilla_extended_ts100")
    ckpts = sorted(f for f in os.listdir(os.path.join(model_dir, "checkpoints")) if f.endswith("_steps.zip"))
    self.assertEqual(len(ckpts), 4)
    for c in ckpts:
        self.assertTrue(os.path.exists(vecnormalize_path_for(os.path.join(model_dir, "checkpoints", c))))
    # The training normaliser saw exactly 1 initial reset + 400 steps; 4
    # validations x 96 steps never reached it.
    final_vn = VecNormalize.load(os.path.join(model_dir, "final_model_vecnormalize.pkl"),
                                 _spaces_only_venv())
    self.assertAlmostEqual(final_vn.obs_rms.count, 1e-4 + 1 + 400, places=6)
    # Frozen load: flags set, statistics unchanged by a validation episode.
    ckpt = os.path.join(model_dir, "checkpoints", ckpts[-1])
    model, vn = et.load_frozen_checkpoint(ckpt, _spaces_only_venv())
    self.assertFalse(vn.training)
    self.assertFalse(vn.norm_reward)
    mean, var, count = vn.obs_rms.mean.copy(), vn.obs_rms.var.copy(), vn.obs_rms.count
    from ev2gym_thesis.rl.env_factory import DEFAULT_REWARD_FN
    et.run_validation(model, vn, DEFAULT_REWARD_FN, cells=et.VALIDATION_CELLS[:1],
                      day_config_dir=os.path.join(self.tmp, "cfg"))
    np.testing.assert_array_equal(mean, vn.obs_rms.mean)
    np.testing.assert_array_equal(var, vn.obs_rms.var)
    self.assertEqual(count, vn.obs_rms.count)
    # Rotation: only the last 2 replay buffers (and their aux files) remain.
    bufs = sorted(os.listdir(os.path.join(model_dir, "replay_buffers")))
    self.assertEqual(bufs, ["replay_buffer_300_steps.pkl", "replay_buffer_400_steps.pkl",
                            "resume_aux_300_steps.pkl", "resume_aux_400_steps.pkl"])

  def test_eval_seed_guard_rejects_and_redraws_same_day(self):
    env = et.SeedLoggingTrainingEnv(config_path=et.REFERENCE_CONFIG_PATH, day_config_dir=self.tmp)
    self.assertEqual(env.forbidden_scenario_seeds, frozenset(SEEDS))
    env.forbidden_scenario_seeds = frozenset(SEEDS) | {100}  # force a hit on the first episode's seed
    env.reset(seed=100)
    self.assertEqual(env.current_rejected_seeds, [100])
    self.assertNotIn(env.current_scenario_seed, env.forbidden_scenario_seeds)
    self.assertEqual(env.days_seen, [TRAIN_DAYS[0]])  # same day, round-robin not advanced
    self.assertEqual(int(env._env.seed), env.current_scenario_seed)


def _spaces_only_venv():
    from stable_baselines3.common.vec_env import DummyVecEnv
    from ev2gym_thesis.rl.env_factory import make_env
    env = make_env(et.REFERENCE_CONFIG_PATH, et.VALIDATION_DAYS[0], et.VALIDATION_SEEDS[0],
                   day_config_dir=tempfile.gettempdir() + "/w6p0_spaces")
    return DummyVecEnv([lambda: env])


# ---------------------------------------------------------------------------
# Pins on the completed run (Part B): selected checkpoint and registry rows
# ---------------------------------------------------------------------------
LOG_DIR = "experiments/phase2_algorithms/results/week6_part0"
EXPECTED_CONVERGENCE = {100: 380_000, 101: 560_000, 102: 810_000}
EXPECTED_PRIMARY = {100: 400_000, 101: 630_000, 102: 850_000}
EXPECTED_LAST = {100: 480_000, 101: 660_000, 102: 910_000}
NEW_ARMS = ([f"TD3_vanilla_extended_ts{s}" for s in TRAIN_SEEDS]
            + [f"TD3_vanilla_extended_last_ts{s}" for s in TRAIN_SEEDS]
            + [f"TD3_vanilla_new60k_ts{s}" for s in TRAIN_SEEDS])


class TestFinalModelPins(unittest.TestCase):
    def test_rule_recomputed_from_versioned_logs(self):
        """convergence_index/select_primary_index re-run on the committed
        validation logs reproduce the live run's decisions."""
        for s in TRAIN_SEEDS:
            v = pd.read_csv(f"{LOG_DIR}/TD3_vanilla_extended_ts{s}_validation.csv")
            m = v.criterion_value.tolist()
            ci = et.convergence_index(m)
            self.assertEqual(int(v.timesteps.iloc[ci]), EXPECTED_CONVERGENCE[s])
            self.assertEqual(int(v.timesteps.iloc[et.select_primary_index(m, ci)]), EXPECTED_PRIMARY[s])
            self.assertEqual(int(v.timesteps.iloc[-1]), EXPECTED_LAST[s])
            self.assertEqual(v.timesteps.tolist(), list(range(10_000, EXPECTED_LAST[s] + 1, 10_000)))

    def test_selected_final_model_pinned(self):
        sel = json.load(open("results/week6_part0_final_model_selection.json"))
        self.assertEqual(sel["algorithm_name"], "TD3_vanilla_extended_ts102")
        self.assertEqual(sel["train_seed"], 102)
        self.assertEqual(sel["checkpoint_step"], 850_000)
        self.assertTrue(sel["checkpoint_path"].endswith("td3_vanilla_extended_ts102_850000_steps.zip"))
        # The rule's own definition: best validation criterion among the 3 primaries.
        prim = {}
        for s in TRAIN_SEEDS:
            v = pd.read_csv(f"{LOG_DIR}/TD3_vanilla_extended_ts{s}_validation.csv")
            prim[s] = v.loc[v.timesteps == EXPECTED_PRIMARY[s], "criterion_value"].iloc[0]
        self.assertEqual(min(prim, key=prim.get), 102)

    def test_no_training_episode_on_an_evaluation_seed(self):
        for s in TRAIN_SEEDS:
            e = pd.read_csv(f"{LOG_DIR}/TD3_vanilla_extended_ts{s}_episodes.csv")
            self.assertFalse(e.scenario_seed_in_eval_seeds.any())
            self.assertFalse(e.train_scenario_seed.isin(SEEDS).any())

    def test_registry_row_count_pin(self):
        df = pd.read_csv("results/master_results.csv", low_memory=False)
        new = df[df.algorithm.isin(NEW_ARMS)]
        self.assertEqual(len(new), 900)
        self.assertTrue((new.groupby("algorithm").size() == 100).all())
        self.assertEqual(set(new.algorithm), set(NEW_ARMS))
        self.assertTrue(new.analysis_row.astype(str).eq("True").all())
        self.assertTrue(new.superseded.astype(str).eq("False").all())
        for arm in NEW_ARMS:
            cells = new[new.algorithm == arm]
            self.assertEqual(cells.seed.nunique(), 50)
            self.assertEqual(sorted(cells.day_type.unique()), ["weekday", "weekend"])
        self.assertTrue(new.notes.str.contains("env=post_setpoint_fix").all())
        # Week 5's 1,300 analysis rows are untouched: 1,300 + 900.
        self.assertEqual(int(df.analysis_row.astype(str).eq("True").sum()), 2200)


if __name__ == "__main__":
    unittest.main()
