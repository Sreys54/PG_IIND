# f09_degradation_by_ambient

Mean battery degradation (total, calendar-only, cycling-only) per algorithm and ambient scenario, with 95% confidence intervals across 5 seeds x 10 evaluation days. Cycling aging has no temperature dependence in the implemented model (verified by inspection) and is included as a visual confirmation that it does not shift across ambient scenarios.

- Runs behind this figure: 100
- Configs: station_v0_bogota
- Algorithms: AFAP, Round Robin
- Git commit: 2190ce39ddafeac3a25b4c59437e94459f2a2c57
- Generated: 2026-08-13T04:42:50.223499Z

Source data: results/degradation_by_ambient.csv (scope=reference: station_v0_bogota only, not the full 502-row registry). See thesis_docs/chapters/02_model_validation.md for the paired-bootstrap percentage-change measurement this figure's absolute values correspond to.
