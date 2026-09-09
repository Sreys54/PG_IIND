"""
Week 5, Gate 4 (found while building the grid runner, not anticipated at
Gate 1/Gate 2): `eMPC_G2V`'s objective reads `env.charge_prices` directly
(`ev2gym/baselines/mpc/mpc.py:200-207`, `self.ch_prices = abs(env.charge_prices[0,:])`)
-- the same live ENTSO-E day-ahead price dependency Gate 4 just removed
from `generate_power_setpoints`. Verified empirically before assuming it:
`eMPC_G2V.ch_prices` differs between two weekday dates for the same seed
(0.2019 vs a different value), exactly the pattern that made the day axis
non-redundant for the setpoint. Left unfixed, `MPC_EnergyMaxG2V` would
still schedule around genuine Dutch day-ahead price shape -- reintroducing
the exact problem Gate 4 was created to close, and undermining its own
premise (this arm exists to represent a flat-Colombian-tariff
energy-delivery objective, not Dutch price arbitrage).

Why this doesn't change the underlying G2V model's behavior in a way that
invalidates the arm: `eMPC_G2V`'s battery-capacity constraints
(`calculate_XF_G2V`) already force every EV to reach its desired capacity
by departure as a HARD constraint (mirroring AFAP's 100% satisfaction --
confirmed at Gate 2's calibration: `average_user_satisfaction=1.0` for
this arm). The price term only ever decided WHEN, within the feasible
window, to deliver that already-guaranteed energy -- so a flat price does
not change whether energy is delivered, only that the model no longer has
any preference for WHEN, subject to the transformer-capacity constraint it
already respects. This is closer to "meet AFAP's own charging requirement
without ever exceeding the transformer, tie-broken arbitrarily by the
solver" than "maximize energy delivered" -- a more precise description
than the Gate 1 shorthand, recorded here and propagated to
`05_algorithm_comparison.md`.

Fix, following the exact wrapper discipline `ev2gym_thesis/oracle/replay_utils.force_g2v`
already established: subclass the unmodified `eMPC_G2V` (`ev2gym/baselines/mpc/eMPC.py`
is never edited), call its real `__init__`, then overwrite the two
price arrays with a flat constant AFTER construction -- the model is built
fresh every `get_action()` call from `self.ch_prices`/`self.disch_prices`,
so this is sufficient; no deeper patch is needed.
"""
import numpy as np

from ev2gym.baselines.mpc.eMPC import eMPC_G2V

# doc:begin flat_price_constant
# Origin: declared assumption. The absolute value is immaterial to this
# arm's behavior under the "reach desired capacity" hard constraint (see
# module docstring) -- any positive constant makes the LP objective a
# scalar multiple of total energy delivered, which is itself fixed by the
# capacity constraint, so the schedule becomes price-indifferent
# regardless of which positive constant is chosen. 1.0 is used for
# simplicity, not calibrated against any real tariff.
FLAT_PRICE_CONSTANT = 1.0
# doc:end flat_price_constant


class MPCEnergyMaxG2V(eMPC_G2V):
    """`eMPC_G2V`, unmodified, with a flat (price-neutral) objective input
    -- registered under the honest name `MPC_EnergyMaxG2V` at evaluation
    time so no reader mistakes the (inert, under Colombian flat pricing)
    price objective for doing real arbitrage work."""

    def __init__(self, env, control_horizon=10, verbose=False, **kwargs):
        super().__init__(env, control_horizon=control_horizon, verbose=verbose, **kwargs)
        # Overwrite the ENTSO-E-derived arrays set by the parent __init__
        # (mpc.py:200-207) with flat constants -- same horizon-padded
        # length as the original, so nothing downstream needs to change.
        self.ch_prices = np.full_like(self.ch_prices, FLAT_PRICE_CONSTANT)
        self.disch_prices = np.zeros_like(self.disch_prices)  # unused in G2V, neutralized for completeness
