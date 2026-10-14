# f06_size_sensitivity

Transformer overload (kWh) vs. number of ports (2/8/16), one line per algorithm, two panels for the two transformer policies (Policy A: fixed at 100 kW; Policy B: scaled to hold the reference case's 4:1 oversubscription ratio constant). station_v0_bogota (n=8) is the shared middle point in both panels since it sits at both 100 kW and the 4:1 ratio simultaneously. HISTORICAL DATA (regenerated 2026-10-14): every point, including n=8, comes from the superseded Week 2 grid (5 seeds x 10 EVAL_DAYS, superseded=True), because the size sweep was not part of the Week 5 Gate 4 regeneration. Two caveats follow. (1) The 10 days collapse to 2 day types in EV2Gym, so the interval is a Student t interval over the 5 seed means, not over 50 rows; its lower bound is clipped at 0, since overload cannot be negative. (2) Round Robin's power budget is the pre-fix setpoint generator (ENTSO-E price-weighted); AFAP ignores the setpoint and is unaffected. The n=8 AFAP value (5.33 kWh) is the superseded-grid value; the current grid gives 14.22 kWh (05 S5.6). EV2Gym's native session durations (long-dwell regime). From 2026-09-09 to 2026-10-14 this figure rendered empty (it filtered on analysis_row=True, which no sweep row has).

- Runs behind this figure: 500
- Configs: station_n02_tx025, station_n02_tx100, station_n16_tx100, station_n16_tx200, station_v0_bogota
- Algorithms: AFAP, Round Robin
- Git commit: e11160e6530ea77a535c93ecc68a23b4013d14e8
- Generated: 2026-10-14T06:22:42.525043Z
