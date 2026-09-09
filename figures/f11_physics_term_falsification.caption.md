# f11_physics_term_falsification

Left: Design 1's weight sweep -- Pearson correlation with the vanilla reward falls as weight increases, but Spearman rank correlation stays pinned at 1.0 at every weight (both terms are monotonic functions of the same instantaneous scalar). Middle: Design 2's control-responsiveness asymmetry -- Round Robin (which nearly eliminates overload) triggers the headroom penalty far more often than AFAP (which overloads routinely). Right: Design 2's SoC-gradient problem -- the headroom penalty term correlates POSITIVELY with mean fleet SoC for both policies, meaning charging faster/more completely reduces the penalty, rewarding AFAP-like aggression. All data regenerated live from ev2gym_thesis/rl/reward_pi.py's actual functions on one real episode, not hand-transcribed.

- Runs behind this figure: 1
- Configs: station_v0_bogota
- Algorithms: ChargeAsFastAsPossible, RoundRobin
- Git commit: 07eb8a4fecac3a57be1571389199f4917c39ca03
- Generated: 2026-09-09T16:12:12.365577Z

Full numeric account in thesis_docs/chapters/00_lab_log.md's 2026-08-19 falsification entry.
