"""
Week 8 (redesigned RL): the observation for the projected TD3 agent.

Why PublicPST is replaced (review of 2026-10-14, chapter 08 item 48).
PublicPST tells the agent, per port, only whether the EV is full (1 or 0.5),
the energy exchanged so far and the steps since arrival. The agent cannot
tell an EV that still needs 40 kWh from one that needs 2 kWh, which is the
information a service-maximising allocation needs.

ServiceState adds each connected EV's state of charge. The SoC is
information a real DC station has: CCS / ISO 15118 and DIN SPEC 70121
charging sessions report it from the vehicle to the charger. Because every
EV in this project wants a full battery (ev.desired_capacity = 1), the
remaining requested energy is battery x (1 - SoC); the SoC therefore gives
the agent its remaining need without any information a station lacks.

Still withheld, as in PublicPST and for the same reason (EV2Gym paper,
Sec. III-A; chapter 04 S4.3): the departure time and anything derived from
it. env.charge_power_potential is not read either, because EV2Gym computes
it with each EV's departure time (utils.py, calculate_charge_power_potential,
line 786).

Layout (n_ports = 8 -> 4 + 4 x 8 = 36 values):
  global: [step / T, last-step station power / rating,
           next-step power setpoint / rating, connected EVs / n_ports]
  per port, in EV2Gym's action order (stations in order, ports in order):
           [connected (1/0), SoC (0 if empty),
            steps connected so far / T (0 if empty),
            energy delivered so far / battery capacity (0 if empty)]
The setpoint is EV2Gym's published operational signal (PublicPST already
exposes it); it is kept so the same state serves both rewards in
reward_service.py. Observations are standardised by VecNormalize at
training time (config_safe.py).

Never touches ev2gym/rl_agent/*.py.
"""
import numpy as np

N_GLOBAL = 4
N_PER_PORT = 4


def _rating_kw(env, step) -> float:
    step = min(step, env.simulation_length - 1)
    return float(sum(tr.max_power[step] for tr in env.transformers))


# doc:begin service_state
def ServiceState(env, *args):
    T = env.simulation_length
    t = env.current_step
    rating = _rating_kw(env, t)
    setpoint = env.power_setpoints[t] if t < T else 0.0
    last_power = env.current_power_usage[t - 1] if t > 0 else 0.0
    per_port, n_connected = [], 0
    for cs in env.charging_stations:
        for port in range(cs.n_ports):
            ev = cs.evs_connected[port]
            if ev is None:
                per_port += [0.0, 0.0, 0.0, 0.0]
            else:
                n_connected += 1
                per_port += [1.0, float(ev.get_soc()), (t - ev.time_of_arrival) / T,
                             float(ev.total_energy_exchanged) / float(ev.battery_capacity)]
    n_ports = len(per_port) // N_PER_PORT
    glob = [t / T, float(last_power) / rating, float(setpoint) / rating, n_connected / n_ports]
    return np.asarray(glob + per_port, dtype=np.float64)
# doc:end service_state


def service_state_dim(n_ports: int) -> int:
    return N_GLOBAL + N_PER_PORT * n_ports


# doc:begin service_state_causal
def ServiceStateCausal(env, *args):
    """Week 8 advisor review (A6/C1): ServiceState without the power
    setpoint. EV2Gym builds the setpoint from every EV of the day
    (utils.generate_power_setpoints: each EV's requested energy spread over
    [arrival + 1, departure), then median-smoothed over steps t-2..t+2), so
    setpoint[t] carries the departure times and energy of the connected EVs
    and the arrivals of the next two steps -- information a real station does
    not have. Dropping it makes the observation causal: occupancy, SoC (CCS
    reports it), time connected, energy delivered, last-step power and the
    time of day. Layout: 3 global + 4 per port (35 values for 8 ports)."""
    s = ServiceState(env)
    return np.delete(s, 2)  # index 2 = next-step power setpoint / rating
# doc:end service_state_causal
