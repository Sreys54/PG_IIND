# f06_size_sensitivity

Transformer overload (kWh) vs. number of ports (2/8/16), one line per algorithm, two panels for the two transformer policies (Policy A: fixed at 100 kW; Policy B: scaled to hold the reference case's 4:1 oversubscription ratio constant). station_v0_bogota (n=8) is the shared middle point in both panels since it sits at both 100 kW and the 4:1 ratio simultaneously.

- Runs behind this figure: 500
- Configs: station_n02_tx025, station_n02_tx100, station_n16_tx100, station_n16_tx200, station_v0_bogota
- Algorithms: AFAP, Round Robin
- Git commit: 0b098f5e0b7ac8efe19a4369f476e58f917ff06a
- Generated: 2026-08-13T00:18:58.837867Z
