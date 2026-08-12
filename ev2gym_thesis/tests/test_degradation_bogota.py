"""
Unit tests for ev2gym_thesis.degradation_bogota, run with:
    PYTHONPATH=. python -m unittest ev2gym_thesis.tests.test_degradation_bogota -v
"""
import datetime
import unittest

from ev2gym_thesis.degradation_bogota import arrhenius_factor, recompute_calendar_degradation
from ev2gym_thesis.ambient_bogota import outdoor_ambient_c, underground_ambient_c


class TestArrheniusFactor(unittest.TestCase):
    """4 closed-form values, mandated and independently verified before writing
    this test (see chat log): exp(-E2/theta) relative to theta=298.15K,
    E2=6976. Tolerance 1e-3 as specified."""

    THETA_298 = arrhenius_factor(298.15)

    CASES = [
        (280.15, 0.2224),   # 7 C
        (286.45, 0.3846),   # 13.3 C (original, unverified assumption)
        (293.15, 0.6709),   # 20 C
        (300.15, 1.1687),   # 27 C
    ]

    def test_relative_arrhenius_factor(self):
        for theta, expected_ratio in self.CASES:
            with self.subTest(theta=theta):
                ratio = arrhenius_factor(theta) / self.THETA_298
                self.assertAlmostEqual(ratio, expected_ratio, delta=1e-3)


class FakeEV:
    """Minimal stand-in exposing exactly the attributes
    recompute_calendar_degradation reads from a real EV2Gym EV object."""

    def __init__(self, historic_soc, active_steps, time_of_arrival, time_of_departure):
        self.historic_soc = historic_soc
        self.active_steps = active_steps
        self.time_of_arrival = time_of_arrival
        self.time_of_departure = time_of_departure


class TestAmbientProfiles(unittest.TestCase):
    def test_outdoor_trough_and_peak(self):
        self.assertAlmostEqual(outdoor_ambient_c(6.0), 7.88, delta=1e-6)
        self.assertAlmostEqual(outdoor_ambient_c(14.5), 19.31, delta=1e-6)

    def test_underground_smaller_swing_than_outdoor(self):
        outdoor_swing = max(outdoor_ambient_c(h) for h in range(24)) - \
            min(outdoor_ambient_c(h) for h in range(24))
        underground_swing = max(underground_ambient_c(h) for h in range(24)) - \
            min(underground_ambient_c(h) for h in range(24))
        self.assertLess(underground_swing, outdoor_swing)


class TestRecomputeCalendarDegradation(unittest.TestCase):
    def test_none_when_no_session_data(self):
        ev = FakeEV(historic_soc=[], active_steps=[], time_of_arrival=0, time_of_departure=0)
        result = recompute_calendar_degradation(
            ev, datetime.datetime(2022, 1, 17, 5, 0), timescale_min=15,
            ambient_profile_fn=outdoor_ambient_c,
        )
        self.assertIsNone(result)

    def test_jensen_gap_is_positive_for_a_varying_profile(self):
        """exp(-E2/theta) is convex in theta over the relevant range, so
        integrating over a temperature that actually varies must give a
        result >= the point estimate at the mean temperature (Jensen's
        inequality) -- i.e. d_cal should be >= d_cal_point_estimate,
        never underestimate the properly-integrated value."""
        # A full day at the airport (sim starts 05:00, connected all 96 steps)
        # spans the whole outdoor diurnal swing.
        n_steps = 96
        ev = FakeEV(
            historic_soc=[0.5] * n_steps,
            active_steps=[1] * n_steps,
            time_of_arrival=0,
            time_of_departure=n_steps - 1,
        )
        result = recompute_calendar_degradation(
            ev, datetime.datetime(2022, 1, 17, 5, 0), timescale_min=15,
            ambient_profile_fn=outdoor_ambient_c, delta_t_charging_c=0.0,
        )
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["d_cal"], result["d_cal_point_estimate"])
        self.assertGreater(result["jensen_gap_pct"], 0)

    def test_delta_t_charging_increases_degradation(self):
        n_steps = 96
        ev = FakeEV(
            historic_soc=[0.5] * n_steps,
            active_steps=[1] * n_steps,
            time_of_arrival=0,
            time_of_departure=n_steps - 1,
        )
        base = recompute_calendar_degradation(
            ev, datetime.datetime(2022, 1, 17, 5, 0), timescale_min=15,
            ambient_profile_fn=outdoor_ambient_c, delta_t_charging_c=0.0,
        )
        bumped = recompute_calendar_degradation(
            ev, datetime.datetime(2022, 1, 17, 5, 0), timescale_min=15,
            ambient_profile_fn=outdoor_ambient_c, delta_t_charging_c=5.0,
        )
        self.assertGreater(bumped["d_cal"], base["d_cal"])


if __name__ == "__main__":
    unittest.main()
