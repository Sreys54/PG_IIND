"""
Week 8 advisor review, Block B (station-level arrival generator) and A1
(energy satisfaction). Brief B5: the stream is identical across arms; the
calibration reproduces the target energy within 1%; a port is reusable in
the step after a departure; rejections happen only when every port is
occupied; a no-control run conserves energy per EV.

Run: python -m unittest ev2gym_thesis.tests.test_station_arrivals
"""
import os
import unittest
from types import SimpleNamespace

import numpy as np

from ev2gym.baselines.heuristics import ChargeAsFastAsPossible

from ev2gym_thesis.demand import review_configs as rc
from ev2gym_thesis.demand import station_arrivals as sa
from ev2gym_thesis.metrics import service
from ev2gym_thesis.rl.env_factory import make_env, reset_for_evaluation

TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "w8_test_sa_cfg")
DAY = (2022, 1, 17)


def _episode(config_path, seed, policy, day=DAY):
    """Run one episode with the generator and the recorder; return env, record."""
    sa.enable(sa.spec_for_config(config_path))
    service.enable_recording()
    try:
        env = make_env(config_path, day, seed, day_config_dir=TMP)
        reset_for_evaluation(env, seed)
        rng = np.random.default_rng(seed)
        for _ in range(env.simulation_length):
            a = ChargeAsFastAsPossible().get_action(env) if policy == "afap" else (
                np.zeros(env.number_of_ports) if policy == "idle" else rng.random(env.number_of_ports))
            env.step(a)
        return env, service.LAST.pop("episode")
    finally:
        service.disable_recording()
        sa.disable()


class TestStationArrivals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg10 = rc.write_config(1.0, out_dir=TMP)
        cls.cfg16 = rc.write_config(1.6, out_dir=TMP)

    def test_stream_and_assignment_identical_across_arms(self):
        runs = {p: _episode(self.cfg16, 4, p)[0] for p in ("afap", "random", "idle")}
        sig = {p: ([(e._sa_key, e.time_of_arrival, e.time_of_departure, e.battery_capacity_at_arrival)
                    for e in env._sa["stream"]], env._sa["online"], [e._sa_key for e in env._sa["rejected"]])
               for p, env in runs.items()}
        self.assertEqual(sig["afap"], sig["random"])
        self.assertEqual(sig["afap"], sig["idle"])

    def test_calibration_within_one_percent(self):
        envs = [make_env(rc.BASE_CONFIG, d, 0, day_config_dir=TMP) for d in rc.CALIBRATION_DAYS]
        for level in rc.LEVELS:
            _, e = rc.offered_mean(rc.calibrated_arrivals_per_day(level), envs)
            self.assertLess(abs(e - rc.OFFERED_KWH_1X * level) / (rc.OFFERED_KWH_1X * level), 0.01, level)

    def test_port_reusable_in_step_after_departure(self):
        ev = lambda a, d: SimpleNamespace(time_of_arrival=a, time_of_departure=d)
        acc, rej = sa.plan_assignment([ev(5, 7), ev(8, 9)], [(0, 0)], dead_time_steps=0)
        self.assertEqual((len(acc), len(rej)), (2, 0))
        acc, rej = sa.plan_assignment([ev(5, 7), ev(8, 9)], [(0, 0)], dead_time_steps=2)
        self.assertEqual((len(acc), len(rej)), (1, 1))
        # In a simulated episode: some port takes a new EV the step after a departure.
        env, rec = _episode(self.cfg16, 1, "afap")
        by_port = {}
        for e in rec["evs"]:
            by_port.setdefault((e["station"], e["port"]), []).append((e["arrival"], e["departure"]))
        gaps = [b[0] - a[1] for v in by_port.values() for a, b in zip(sorted(v), sorted(v)[1:])]
        self.assertIn(1, gaps)
        self.assertGreaterEqual(min(gaps), 1)

    def test_rejection_only_when_all_ports_occupied(self):
        probe = make_env(self.cfg16, DAY, 0, day_config_dir=TMP)
        spec = sa.spec_for_config(self.cfg16)
        ports = [(i, 0) for i in range(8)]
        seed = next(s for s in range(200)  # first scenario with a rejection (plan only, no simulation)
                    if sa.plan_assignment(sa.draw_stream(probe, spec, s)["stream"], ports)[1])
        env, rec = _episode(self.cfg16, seed, "afap")
        self.assertGreater(len(env._sa["rejected"]), 0)
        sessions = [(e["arrival"], e["departure"]) for e in rec["evs"]]
        for r in env._sa["rejected"]:
            a = r.time_of_arrival
            busy = sum(1 for (s, d) in sessions if s <= a <= d)
            self.assertEqual(busy, env.number_of_ports, f"rejected at {a} with a free port")

    def test_no_control_run_conserves_energy(self):
        env, rec = _episode(self.cfg10, 0, "afap")
        stats_e = sum(e["delivered_kwh"] for e in rec["evs"] + rec["connected_at_end"])
        self.assertAlmostEqual(stats_e, service.episode_totals(rec)["energy_kwh"], places=6)
        for e in rec["evs"]:
            self.assertLessEqual(e["delivered_kwh"], e["requested_kwh"] + 0.05)  # EV2Gym's 0.01 kWh capacity rounding
        self.assertEqual(rec["connected_at_end"], [])

    def test_connection_window_equals_sampled_steps(self):
        env, rec = _episode(self.cfg10, 5, "idle")
        dwell = {e._sa_key: e._sa_dwell_steps for e in env._sa["stream"]}
        for e in env._sa["stream"]:
            if e._sa_key in env._sa["online"]:
                self.assertEqual(e.time_of_departure - e.time_of_arrival + 1, dwell[e._sa_key])


class TestEnergySatisfaction(unittest.TestCase):
    def test_definitions(self):
        self.assertEqual(service.energy_satisfaction(5.0, 10.0), 0.5)
        self.assertEqual(service.energy_satisfaction(12.0, 10.0), 1.0)
        self.assertEqual(service.energy_satisfaction(0.0, 0.0), 1.0)
        # EV2Gym's battery-level satisfaction of an EV that got nothing, R/C = 0.23
        self.assertAlmostEqual(service.ev2gym_battery_level_satisfaction(16.1, 70.0, 0.0), 1 - 16.1 / 70.0)

    def test_summary_counts_rejected_as_zero(self):
        s = service.service_summary([1.0, 0.95, 0.5], n_rejected=1)
        self.assertAlmostEqual(s["mean_f_served"], 2.45 / 3)
        self.assertAlmostEqual(s["mean_f_all"], 2.45 / 4)
        self.assertAlmostEqual(s["service_level_served"], 2 / 3)
        self.assertAlmostEqual(s["service_level_all"], 2 / 4)

    def test_identity_with_ev2gym_metric_in_simulation(self):
        env, rec = _episode(rc.write_config(1.6, out_dir=TMP), 3, "random")
        for e in rec["evs"]:
            self.assertAlmostEqual(e["s_ev2gym"], service.ev2gym_battery_level_satisfaction(
                e["requested_kwh"], e["battery_kwh"], e["f"]), places=2)


if __name__ == "__main__":
    unittest.main()
