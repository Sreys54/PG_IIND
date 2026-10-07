# f22_session_duration

Final capacity brief, Parts A-B. EV2Gym draws each stay from the ElaadNL 'public' mean session length for the arrival time (2.8-12.5 h), floors it at min_time_of_stay (200 min) and adds two steps, so no session is shorter than 225 min; the mean is 300.6 min [296.5, 304.7]. The DC transform (ev2gym_thesis/demand/dc_sessions.py) redraws durations from a lognormal (CV 0.5) with mean 32, 42 or 78 min (external references, not Colombian: U.S. DOE 2023; Hardman 2026), rounded to the 15-minute step. Steps in the curves are the timestep. Source: results/dwell_sessions_ev_level.csv, results/dwell_a_session_summary.csv.

- Runs behind this figure: 400
- Configs: station_v0_bogota (1.0x), 4 session models
- Algorithms: none (policy-independent)
- Git commit: 942122a9ef92ffece960e3d7270f98c5307131be
- Generated: 2026-10-07T03:33:47.527829Z
