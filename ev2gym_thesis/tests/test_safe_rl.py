"""
Week 8 (redesigned RL, TD3_safe): tests for the hard transformer constraint,
the served-energy reward, the service state and the new configuration.

Every test drives the real production objects (env_factory.make_env with the
regime's real config, safety.safe_step, SafeTrainingEnv), per the standing
rule from the Week 3 evaluation bug: a test must exercise the call path used
in production, not a lookalike.

Run: PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_safe_rl -v
"""
import shutil
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from ev2gym_thesis.demand import dc_sessions
from ev2gym_thesis.eval_protocol import EVAL_DAYS
from ev2gym_thesis.rl import config_rl, config_safe as cfg
from ev2gym_thesis.rl import extended_training as et
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation
from ev2gym_thesis.rl.reward_service import ServedEnergyReward, served_energy_scale_kwh
from ev2gym_thesis.rl.safe_training import SafeTrainingEnv
from ev2gym_thesis.rl.safety import project_actions, safe_step, port_rated_kw
from ev2gym_thesis.rl.state_service import ServiceState, service_state_dim

BUDGET = 0.999 * 100.0
TOL_KW = 1e-4  # float32 representation of transformer power (99.9 is stored as 99.9000015); 3 orders below the 0.1 kW margin to 100 kW


class _RegimeCase(unittest.TestCase):
    regime = "dc42"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg_path = cfg.REGIME_CONFIGS[self.regime]
        if self.regime == "dc42":
            dc_sessions.enable(dc_sessions.model_for_config(self.cfg_path))

    def tearDown(self):
        dc_sessions.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def env(self, seed, day=EVAL_DAYS[0], reward_fn=ServedEnergyReward):
        env = make_env(self.cfg_path, day, seed, reward_fn=reward_fn, state_fn=cfg.STATE_FN,
                       day_config_dir=self.tmp)
        reset_for_evaluation(env, seed)
        return env

    def run_episode(self, env, policy):
        """policy(env, obs) -> raw action. Returns (stats, rewards, per-step
        transformer power, projection-active count)."""
        obs = env._get_observation()
        rewards, powers, active, done, stats = [], [], 0, False, None
        while not done:
            obs, r, term, trunc, stats, pinfo = safe_step(env, policy(env, obs))
            rewards.append(r)
            powers.append(max(tr.current_power for tr in env.transformers))
            active += int(pinfo["active"])
            done = term or trunc
        return stats, np.array(rewards), np.array(powers), active


def _random_policy(rng):
    return lambda env, obs: rng.uniform(0.0, 1.0, size=env.number_of_ports)


def _all_on(env, obs):
    return np.ones(env.number_of_ports)


class TestProjectionDC(_RegimeCase):
    regime = "dc42"

    def test_never_exceeds_rating_random_and_all_on(self):
        rng = np.random.default_rng(0)
        for seed in (0, 1, 2):
            for policy in (_random_policy(rng), _all_on):
                stats, _, powers, _ = self.run_episode(self.env(seed), policy)
                self.assertLessEqual(powers.max(), BUDGET + TOL_KW)
                self.assertEqual(float(stats["total_transformer_overload"]), 0.0)

    def test_all_on_actually_binds(self):
        # At 1.0x DC demand, unmanaged charging exceeds 100 kW (06 S6.6.4), so
        # the projection must cut at least one step of an all-on policy.
        _, _, _, active = self.run_episode(self.env(0), _all_on)
        self.assertGreater(active, 0)

    def test_projection_properties(self):
        env = self.env(0)
        for _ in range(40):  # walk into the day until EVs are connected
            safe_step(env, np.ones(env.number_of_ports))
        raw = np.full(env.number_of_ports, 0.9)
        proj, info = project_actions(env, raw)
        self.assertTrue(np.all(raw == 0.9), "input must not be modified")
        self.assertTrue(np.all(proj <= raw + 1e-7), "projection may only lower actions")
        idx = 0
        for cs in env.charging_stations:
            for port in range(cs.n_ports):
                if cs.evs_connected[port] is None:
                    self.assertEqual(proj[idx], 0.0, "empty ports get action 0")
                idx += 1
        bound_after = sum(proj[i] * port_rated_kw(env.charging_stations[i]) for i in range(len(proj)))
        self.assertLessEqual(bound_after, BUDGET + TOL_KW)
        # Below the budget the projection is the identity on connected ports.
        small = np.zeros(env.number_of_ports)
        connected = [i for i, cs in enumerate(env.charging_stations) if cs.evs_connected[0] is not None]
        if connected:
            small[connected[0]] = 0.5
            proj2, info2 = project_actions(env, small)
            self.assertFalse(info2["active"])
            self.assertAlmostEqual(float(proj2[connected[0]]), 0.5, places=6)


class TestProjectionLong(TestProjectionDC):
    regime = "long"

    def test_all_on_actually_binds(self):
        # Long-dwell regime: AFAP overloads in 35 of 100 cells; seed 0
        # weekday is one of them (closure_c1 / week5 seed distribution).
        _, _, _, active = self.run_episode(self.env(0), _all_on)
        self.assertGreater(active, 0)


class TestServedEnergyReward(_RegimeCase):
    regime = "dc42"

    def test_return_equals_energy_delivered(self):
        rng = np.random.default_rng(1)
        for seed in (0, 3):
            for day in EVAL_DAYS:
                env = self.env(seed, day)
                scale = served_energy_scale_kwh(env)
                stats, rewards, _, _ = self.run_episode(env, _random_policy(rng))
                # EV2Gym stores per-step power in a float32 array while
                # total_energy_charged accumulates in float64, so the two
                # agree to float32 precision (~1e-6 kWh on ~500 kWh), not to
                # float64 precision.
                self.assertAlmostEqual(rewards.sum() * scale, float(stats["total_energy_charged"]), delta=1e-4)
                self.assertTrue(np.all(rewards >= 0) and np.all(rewards <= 1.0 + 1e-9))

    def test_refuses_when_desired_capacity_is_not_full(self):
        fake = SimpleNamespace(config={"ev": {"desired_capacity": 0.8}})
        with self.assertRaises(ValueError):
            ServedEnergyReward(fake, 0, [])

    def test_every_ev_wants_a_full_battery(self):
        env = self.env(0)
        self.assertTrue(all(ev.desired_capacity == ev.battery_capacity for ev in env.EVs_profiles))


class TestServedEnergyRewardLong(TestServedEnergyReward):
    regime = "long"


class TestServiceState(_RegimeCase):
    regime = "dc42"

    def test_dimension_and_finiteness(self):
        env = self.env(0)
        self.assertEqual(env.observation_space.shape, (service_state_dim(env.number_of_ports),))
        self.assertEqual(service_state_dim(8), 36)
        stats, _, _, _ = self.run_episode(env, _all_on)
        self.assertTrue(np.all(np.isfinite(ServiceState(env))))

    def test_does_not_use_departure_times(self):
        env = self.env(0)
        while sum(cs.n_evs_connected for cs in env.charging_stations) == 0:
            safe_step(env, np.ones(env.number_of_ports))
        before = ServiceState(env)
        for cs in env.charging_stations:
            for ev in cs.evs_connected:
                if ev is not None:
                    ev.time_of_departure += 37
        np.testing.assert_array_equal(before, ServiceState(env))

    def test_soc_is_exposed(self):
        env = self.env(0)
        while sum(cs.n_evs_connected for cs in env.charging_stations) == 0:
            safe_step(env, np.ones(env.number_of_ports))
        s = ServiceState(env)
        idx = 0
        for cs in env.charging_stations:
            for port in range(cs.n_ports):
                ev = cs.evs_connected[port]
                block = s[4 + 4 * idx: 8 + 4 * idx]
                if ev is not None:
                    self.assertEqual(block[0], 1.0)
                    self.assertAlmostEqual(block[1], ev.get_soc())
                else:
                    np.testing.assert_array_equal(block, np.zeros(4))
                idx += 1


class TestSafeTrainingEnv(_RegimeCase):
    regime = "dc42"

    def test_training_env_projects_and_never_overloads(self):
        env = SafeTrainingEnv(config_path=self.cfg_path, reward_fn=ServedEnergyReward, state_fn=cfg.STATE_FN,
                              day_config_dir=self.tmp)
        env.reset(seed=100)
        done, info = False, {}
        while not done:
            _, _, term, trunc, info = env.step(np.ones(env.action_space.shape[0]))
            done = term or trunc
        self.assertEqual(float(info["total_transformer_overload"]), 0.0)
        self.assertIn("projection_active_share", info)
        self.assertGreater(info["projection_active_share"], 0.0)
        self.assertEqual(env.observation_space.shape, (36,))


class TestConfig(unittest.TestCase):

    def test_safe_hyperparameters_pinned(self):
        self.assertEqual(cfg.NET_ARCH, [256, 256])
        self.assertEqual((cfg.LEARNING_RATE, cfg.BATCH_SIZE, cfg.GAMMA, cfg.TAU), (3e-4, 256, 0.99, 0.005))
        self.assertEqual((cfg.POLICY_DELAY, cfg.TARGET_POLICY_NOISE, cfg.TARGET_NOISE_CLIP), (2, 0.2, 0.5))
        self.assertEqual((cfg.ACTION_NOISE_SIGMA, cfg.LEARNING_STARTS, cfg.BUFFER_SIZE), (0.1, 10_000, 300_000))
        self.assertEqual((cfg.VECNORMALIZE_NORM_OBS, cfg.VECNORMALIZE_NORM_REWARD), (True, False))
        self.assertIs(cfg.STATE_FN, ServiceState)
        self.assertEqual(cfg.SELECTION["served_energy"], ("total_energy_charged", False))
        self.assertEqual(cfg.arm_name("dc42", "served_energy"), "TD3_safe_dc42")

    def test_weeks_3_to_7_config_unchanged(self):
        # The old design stays reproducible: config_rl.py must not drift.
        self.assertEqual(config_rl.NET_ARCH, [64, 64])
        self.assertEqual((config_rl.LEARNING_RATE, config_rl.BUFFER_SIZE, config_rl.LEARNING_STARTS),
                         (1e-3, 50_000, 500))
        self.assertEqual(config_rl.TOTAL_TIMESTEPS, 60_000)
        self.assertTrue(config_rl.VECNORMALIZE_NORM_REWARD)

    def test_callback_defaults_reproduce_week6_logging(self):
        cb = et.ExtendedTrainingCallback(run_name="x", model_dir=tempfile.mkdtemp(), log_dir=tempfile.mkdtemp(),
                                         reward_fn=ServedEnergyReward, deadline_epoch_s=0)
        self.assertEqual(cb.validation_csv_fields, et.VALIDATION_CSV_FIELDS)
        self.assertEqual((cb.criterion, cb.lower_is_better), ("tracking_error", True))


if __name__ == "__main__":
    unittest.main()
