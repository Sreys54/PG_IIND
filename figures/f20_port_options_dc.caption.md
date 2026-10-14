# f20_port_options_dc

Last run: f20 in the DC fast-charging regime, 42-minute sessions (the long-dwell regime is f20_port_options; two-regime framing, 06 S6.8). On the 100 kW unit, with the spawn multiplier scaled by 8/ports (constant station demand), the transformer-aware Round Robin meets the 15% target with 8 ports at 1.3x and needs 10 ports at 1.6x (where 8 ports also fail the satisfaction criterion); EV2Gym's setpoint-following Round Robin stays above 15% at every port count on 100 kW. Source: results/dwell_c2_growth_options.csv.

- Runs behind this figure: 2000
- Configs: station_v0_bogota_dc42_sp{39,48}[_p{10..16}_cd]_tx100
- Algorithms: Round Robin (EV2Gym, follows the setpoint), Round Robin, transformer-aware
- Git commit: 34dc0e0d006bf1a6ba010ba73e477eadb400fae6
- Generated: 2026-10-14T05:43:52.205792Z
