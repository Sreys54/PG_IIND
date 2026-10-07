# f21_city_cost

Closure brief D2. Each city's Nivel 2 commercial energy cost with contribution (ev2gym_thesis/prices/cities.py, sources saved in thesis_docs/sources/) applied to the non-grid statistical rows. Flat: margin = energy x (1,450 - cost), so the relative cost is 0.47% everywhere (Proposition 7.1). Two-band: each run's 15-minute station power profile priced at the operator's peak and off-peak rates. Barranquilla (Air-e, 10.03% spread, 17-22 h) is the only city where the two-band cost departs materially from the flat one. Cali uses EMCALI's January 2026 sheet, the latest retrievable. Source: results/closure_multicity_rr_cost.csv.

- Runs behind this figure: 200
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin
- Git commit: 6f42b02fd5e17cca0db3f2e9b52ce01865c1da10
- Generated: 2026-10-06T23:36:11.892379Z
