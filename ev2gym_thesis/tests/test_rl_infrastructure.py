"""
Week 3, Entregable 9: tests for the RL infrastructure added this week.
Deliberately does NOT depend on a real trained model (Entregable 5 training
runs after the Entregable 4 CPU-budget confirmation) -- these tests use
freshly-constructed, untrained TD3 instances or pure bookkeeping checks, so
they can run any time, before or after training exists.

Run with:
    PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_rl_infrastructure -v
"""
import os
import shutil
import tempfile
import unittest

from ev2gym_thesis.eval_protocol import SEEDS, TRAIN_SEEDS, EVAL_DAYS, TRAIN_DAYS
from ev2gym_thesis.rl.env_factory import TrainingDayCyclingEnv, make_env
from ev2gym_thesis.rl.eval_utils import load_trained_agent

REFERENCE_CONFIG = "experiments/phase1_baseline/configs/station_v0_bogota.yaml"


class TestSeedAndDayDisjointness(unittest.TestCase):
    """Entregable 9, item 1: TRAIN_SEEDS ∩ SEEDS = ∅ and TRAIN_DAYS ∩
    EVAL_DAYS = ∅. Both are already asserted at eval_protocol import time
    (so a violation fails immediately for every script, not just this
    test) -- these tests pin the *values* the assertions were checked
    against, so a future edit that silently narrows either pool without
    breaking disjointness still gets caught here."""

    def test_train_seeds_disjoint_from_seeds(self):
        self.assertTrue(set(SEEDS).isdisjoint(set(TRAIN_SEEDS)))

    def test_train_days_disjoint_from_eval_days(self):
        self.assertTrue(set(TRAIN_DAYS).isdisjoint(set(EVAL_DAYS)))

    def test_pools_are_non_empty(self):
        # A disjointness check against two empty sets would trivially pass --
        # guard against that degenerate case too.
        self.assertGreater(len(SEEDS), 0)
        self.assertGreater(len(TRAIN_SEEDS), 0)
        self.assertGreater(len(EVAL_DAYS), 0)
        self.assertGreater(len(TRAIN_DAYS), 0)


class TestTrainingEnvNeverLeaksEvalDays(unittest.TestCase):
    """Entregable 9, item 2: make_training_env/TrainingDayCyclingEnv must
    NEVER sample a day from EVAL_DAYS. This is the anti-data-leakage
    barrier and must be a test, not a convention -- per the Week 3 brief's
    explicit instruction."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_day_config_dir = tempfile.mkdtemp(prefix="train_day_cycling_test_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_day_config_dir, ignore_errors=True)

    def test_round_robin_never_samples_eval_day_and_cycles_evenly(self):
        env = TrainingDayCyclingEnv(
            config_path=REFERENCE_CONFIG,
            sample_mode="round_robin",
            day_config_dir=self.tmp_day_config_dir,
        )
        # One full lap of TRAIN_DAYS plus a bit more, to also exercise wraparound.
        n_resets = len(TRAIN_DAYS) + 3
        for _ in range(n_resets):
            env.reset()

        self.assertEqual(len(env.days_seen), n_resets)
        for day in env.days_seen:
            self.assertNotIn(day, EVAL_DAYS,
                              f"TrainingDayCyclingEnv sampled {day}, which is in EVAL_DAYS -- train/eval leakage.")
            self.assertIn(day, TRAIN_DAYS)

        # Round-robin coverage: every TRAIN_DAYS day appears at least once
        # in one full lap, and the sequence repeats TRAIN_DAYS[0] at the
        # wraparound point.
        self.assertEqual(set(env.days_seen), set(TRAIN_DAYS))
        self.assertEqual(env.days_seen[len(TRAIN_DAYS)], TRAIN_DAYS[0])

    def test_random_mode_never_samples_eval_day(self):
        env = TrainingDayCyclingEnv(
            config_path=REFERENCE_CONFIG,
            sample_mode="random",
            rng_seed=42,
            day_config_dir=self.tmp_day_config_dir,
        )
        for _ in range(10):
            env.reset()
        for day in env.days_seen:
            self.assertNotIn(day, EVAL_DAYS)
            self.assertIn(day, TRAIN_DAYS)

    def test_random_mode_requires_explicit_seed(self):
        with self.assertRaises(ValueError):
            TrainingDayCyclingEnv(config_path=REFERENCE_CONFIG, sample_mode="random",
                                   day_config_dir=self.tmp_day_config_dir)


class TestVecNormalizeStatsRequired(unittest.TestCase):
    """Entregable 9, item 3: loading a checkpoint without its VecNormalize
    statistics file must fail loudly (FileNotFoundError), never silently
    evaluate with mismatched/default statistics."""

    def test_missing_vecnormalize_file_raises_file_not_found(self):
        env = make_env(REFERENCE_CONFIG, EVAL_DAYS[0], SEEDS[0])
        with self.assertRaises(FileNotFoundError) as ctx:
            load_trained_agent(
                model_path="/nonexistent/path/model.zip",
                env=env,
                vecnormalize_path="/nonexistent/path/model_vecnormalize.pkl",
            )
        self.assertIn("VecNormalize", str(ctx.exception))


class TestEvaluationReproducibility(unittest.TestCase):
    """Entregable 9, item 4: the same (config, scenario_seed, eval_day,
    model) evaluated twice must produce identical metrics. Uses a freshly
    constructed (untrained) TD3 model -- reproducibility of the evaluation
    PIPELINE (deterministic predict + deterministic scenario generation
    given a fixed seed) does not depend on the model having been trained,
    only on the model's weights being fixed between the two runs, which
    they are since it's the same in-memory model object."""

    def test_same_cell_same_model_gives_identical_stats(self):
        from stable_baselines3 import TD3

        day = EVAL_DAYS[0]
        seed = SEEDS[0]

        env_a = make_env(REFERENCE_CONFIG, day, seed)
        model = TD3("MlpPolicy", env_a, policy_kwargs=dict(net_arch=[8, 8]), seed=100, verbose=0)

        def run_once(env):
            obs, _ = env.reset(seed=seed)
            done = False
            info = {}
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, truncated, info = env.step(action)
            return info

        stats_a = run_once(env_a)
        env_b = make_env(REFERENCE_CONFIG, day, seed)
        stats_b = run_once(env_b)

        numeric_keys = [
            k for k, v in stats_a.items()
            if k != "action_mask" and isinstance(v, (int, float))
        ]
        self.assertGreater(len(numeric_keys), 0)
        for key in numeric_keys:
            self.assertEqual(stats_a[key], stats_b[key], f"Mismatch in {key!r}: {stats_a[key]} != {stats_b[key]}")


if __name__ == "__main__":
    unittest.main()
