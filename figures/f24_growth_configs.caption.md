# f24_growth_configs

Final capacity brief C2 at 1.3x and 1.6x, 42-minute DC sessions, ports scaled at constant station demand (spawn multiplier x 8/ports). Criteria: satisfaction counting rejected arrivals (CI low >= 90%), demand not served (CI high <= 15%), P95 peak (CI high <= the candidate's own rating in kW at pf 0.894). Transformer ratings are Enel ET-013 classes; 100 kW is the reference unit. AFAP is a labelled addition and the transformer-aware Round Robin is the recommended arm; the RL model is tied to 8 ports and excluded. Source: results/dwell_c2_growth_options.csv.

- Runs behind this figure: 15000
- Configs: station_v0_bogota_dc42_sp{39,48}[_p{10..16}_cd]_tx{100..357.8}
- Algorithms: Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-aware, AFAP
- Git commit: dad3f3ecb69b64e7a743809d0729e4b7058b0646
- Generated: 2026-10-07T22:29:23.040800Z
