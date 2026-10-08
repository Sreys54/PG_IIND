# f25_voltage_dc

Last run, Part 3: the closure E2 protocol under 42-minute DC sessions. node_123 as shipped, 8 ports on bus 115, idle baseline matched per (level, seed), weekday only (EV2Gym's background-load generator stalls on the weekend day for 123 buses), 50 seeds. The station energy equals the non-grid dwell rows exactly (no feeder feedback). node_123 is a test network, not a Colombian feeder. Source: results/dwell_last_voltage_node123.csv.

- Runs behind this figure: 300
- Configs: grid123_dc42_sp{30,39,48}
- Algorithms: AFAP, Round Robin, transformer-aware
- Git commit: dad3f3ecb69b64e7a743809d0729e4b7058b0646
- Generated: 2026-10-07T22:30:18.771046Z
