# Chapter 3 — Algorithm Documentation

Fixed per-algorithm template. Sections: Rationale, Implementation,
Hyperparameters, Results, Conclusions, Limitations. Weeks 3-5 (MPC, vanilla
RL, PI-TD3) fill in the same template as they're added — never a different
structure per algorithm, so the eventual cross-algorithm comparison stays
apples-to-apples.

Results below are computed directly from `results/master_results.csv`
(`station_v0_bogota`, 50 evaluation runs per algorithm: 5 seeds x 10 days),
not estimated or taken from any paper. The 313 kWh / 57 kWh figures
reported by Orfanoudakis et al. (2025) for AFAP / Round Robin appear only
as an attributed external reference point in the Conclusions discussion
below — never in the results tables, since that paper's network,
scenario, and dataset are not ours (see `thesis_docs/chapters/02_model_validation.md`
for the full list of what differs).

---

## ChargeAsFastAsPossible (AFAP)

### Rationale

AFAP represents the "unmanaged charging" baseline: every connected EV
charges at its maximum rate with no coordination, no awareness of the
transformer's capacity, and no response to a power setpoint. It is in the
comparison because it answers a specific question none of the other
algorithms can: *what happens at this station if charging is not managed
at all?* Every other algorithm in this thesis is evaluated relative to
this baseline (see `figures/f05_vs_baseline.png`), because "does managed
charging help, and by how much" is only a meaningful question once you
know what "unmanaged" costs.

### Implementation

- **Location:** `ev2gym.baselines.heuristics.ChargeAsFastAsPossible`
  (ships with EV2Gym; nothing written for this thesis — used as-is, per
  the project's convention of extending rather than modifying the
  library).
- **Observation/action space:** does not use the environment's
  observation vector at all. `get_action(env)` ignores its state input and
  returns a constant action of `1.0` (maximum charge command) for every
  port, every step (`ev2gym/baselines/heuristics.py:161-166`).
- **Deviation from the reference implementation:** none. Called with no
  arguments (`ChargeAsFastAsPossible()`), library default behavior.

### Hyperparameters

| Parameter | Value | Justification |
|---|---|---|
| — | — | AFAP has no tunable parameters — it is a constant policy by construction. |

### Results

`station_v0_bogota.yaml`, 50 evaluation runs (5 seeds x 10 eval days), mean
± 95% CI:

| Metric | Value |
|---|---|
| EVs served | 13.44 [13.21, 13.67] |
| Energy charged (kWh) | 196.7 [190.9, 202.5] |
| Transformer overload (kWh) | 5.33 [1.93, 8.73] |
| Average user satisfaction | 1.0 [1.0, 1.0] |
| Profits | -45.73 [-53.8, -37.66] |

Supporting figures: `figures/f01_power_profile.png` (reference-day power
trace, shows two clear excursions above the 100 kW transformer limit),
`figures/f02_metrics_bars.png`, `figures/f04_distributions.png` (shows the
overload distribution is right-skewed — most days show ~0 kWh overload,
with a small number of high-overload outlier days driving the mean),
`figures/f06_size_sensitivity.png` (AFAP's overload grows sharply with
port count under a fixed transformer).

### Conclusions

At this station's 4:1 oversubscription ratio, unmanaged charging produces
a measurable transformer overload (mean 5.33 kWh/day, 95% CI excluding
zero) without any corresponding benefit in EVs served, energy delivered,
or user satisfaction relative to Round Robin (see the paired comparison
below) — i.e., the naive strategy buys nothing except the emergency
capacity risk. `figures/f04_distributions.png` shows this is not a uniform
daily cost: overload is concentrated in a minority of high-arrival days,
which is itself a claim worth stating carefully — a jury could reasonably
ask whether a 50-run, single-season sample captures the true tail
frequency, which it does not fully (see Limitations).

### Limitations

- Single station configuration (`station_v0_bogota`, 8 ports, 100 kW
  transformer) for these specific numbers; the port-count/transformer-ratio
  sensitivity is covered separately in `figures/f06_size_sensitivity.png`,
  not repeated here per-algorithm.
- No grid/voltage constraints modeled (`simulate_grid: False` — see
  `02_model_validation.md`); "overload" here means exceeding the local
  transformer's rated power, not a verified RETIE voltage violation.
- Evaluation grid is 10 fixed days across 2022, not a full year — the tail
  frequency of high-overload days is not fully characterized by 50 runs.
- `total_profits` reflects Dutch ENTSO-E day-ahead prices (see
  `02_model_validation.md`), not Colombian tariffs — usable only as a
  relative comparison against Round Robin under identical prices.

---

## RoundRobin

### Rationale

Round Robin represents the cheapest possible *managed* charging strategy:
it tracks a power setpoint by rotating which connected EVs charge at full
power each step, using no forecasting, no optimization, and negligible
compute. It answers a different question than AFAP: *can a trivial,
non-predictive heuristic already fix the transformer-overload problem, or
does solving it require something more sophisticated (MPC, RL)?* If Round
Robin already eliminates the overload, that sets the bar every later,
more complex algorithm (Weeks 3-5) has to clear to justify its added
complexity.

### Implementation

- **Location:** `ev2gym.baselines.heuristics.RoundRobin` (ships with
  EV2Gym; nothing written for this thesis).
- **Mechanism (not a plain "reduce everyone's power" heuristic — worth
  being precise about):** each step, it reads the environment's power
  setpoint (`env.power_setpoints[env.current_step]`, generated from
  `power_setpoint_enabled`/`power_setpoint_flexiblity` in the config) and
  computes `number_of_EVs_to_charge = setpoint / average_port_power`. It
  maintains a FIFO buffer of currently-connected EVs and charges only that
  many per step at full power (action = 1.0), rotating the buffer so every
  connected EV eventually gets its turn — this is why it's called "Round
  Robin," not a fair-share power reduction (`ev2gym/baselines/heuristics.py:54-95`).
- **Observation/action space:** like AFAP, does not use the environment's
  observation vector; it reads `env.power_setpoints` and
  `env.charging_stations` directly rather than through the state function.
- **Deviation from the reference implementation:** none. Constructed with
  `RoundRobin(env)` (needs `env` at construction to compute
  `self.average_power` from the station's charger specs — the one
  mechanical difference from AFAP's no-argument constructor, not an
  algorithmic choice).

### Hyperparameters

| Parameter | Value | Justification |
|---|---|---|
| `power_setpoint_enabled` | `True` | Library default, unchanged — Round Robin requires a setpoint to track; without it there is nothing for this algorithm to do. |
| `power_setpoint_flexiblity` | `80` (%) | Inherited unchanged from the `V2Ggrid.yaml` template this project's config derives from — not tuned for this thesis. Controls how far the generated setpoint can deviate from nominal power; not independently justified here. |
| — | — | Round Robin itself has no additional tunable parameters (`self.average_power` is computed automatically from the station config, not user-set). |

### Results

`station_v0_bogota.yaml`, 50 evaluation runs (5 seeds x 10 eval days), mean
± 95% CI:

| Metric | Value |
|---|---|
| EVs served | 13.44 [13.21, 13.67] |
| Energy charged (kWh) | 196.5 [190.7, 202.4] |
| Transformer overload (kWh) | 0.0 [0.0, 0.0] |
| Average user satisfaction | ~1.0 [0.9999, 1.0] |
| Profits | -44.51 [-52.32, -36.71] |

**Paired comparison vs. AFAP** (bootstrap 95% CI, matched by identical
seed+day cell — not independent-sample means, since both algorithms are
evaluated on the exact same 50 scenarios):

| Metric | Paired change vs. AFAP |
|---|---|
| EVs served | +0.00% [+0.00%, +0.00%] (no measurable difference) |
| Energy charged | -0.08% [-0.13%, -0.06%] (negligible) |
| Transformer overload | -5.33 kWh [-8.96, -2.13] (absolute; AFAP's baseline is 0 for the % form) |
| Average user satisfaction | ~0.00% (no measurable difference) |
| Profits | -2.52% [-4.23%, -0.82%] |
| `tracking_error` | -76.18% [-77.41%, -74.77%] |
| `power_tracker_violation` | -100% [-100%, -100%] (essentially eliminated) |

Supporting figures: `figures/f01_power_profile.png`, `figures/f02_metrics_bars.png`,
`figures/f03_tradeoff_pareto.png` (satisfaction-vs-overload trade-off —
both algorithms are non-dominated in this sample, since neither one beats
the other on both satisfaction and overload simultaneously: AFAP wins
marginally on satisfaction, Round Robin wins decisively on overload),
`figures/f05_vs_baseline.png`,
`figures/f06_size_sensitivity.png` (Round Robin's overload stays near zero
across every tested port count and both transformer policies).

### Conclusions

Round Robin **eliminates all measured transformer overload** at this
station (0.0 kWh across all 50 evaluation runs, vs. AFAP's 5.33 kWh mean
with a 95% CI that excludes zero) and cuts power-setpoint tracking error
by 76%, at a statistically real but modest cost in profit (-2.52%,
95% CI excluding zero) and with no measurable change in how many EVs are
served, how much energy is delivered, or user satisfaction. This directly
answers this algorithm's rationale question: at this station's 4:1
oversubscription ratio, a zero-forecasting, negligible-compute heuristic
is already sufficient to solve the overload problem in this evaluation
grid. Whether that headroom disappears at a higher oversubscription ratio
or under grid voltage constraints is exactly what `f06_size_sensitivity`
and the Week 2+ grid-enabled work (Objectives 4-5, not this week) are for
— this result should not be read as "the problem is solved," only as "this
particular unmanaged-vs-simple-heuristic gap, at this station size, is
this large."

For external context only (not a numerical comparison, since the network,
scenario, and dataset all differ — see `02_model_validation.md`):
Orfanoudakis et al. (2025) report AFAP and Round Robin daily energy figures
on the order of 313 kWh and 57 kWh respectively in their own evaluation
setup. Our station's much smaller port count and different arrival
intensity make our ~196 kWh/day figures for both algorithms not directly
comparable to theirs, and the relative AFAP/RR gap in their paper is not
reproduced here as a target or a check — it is cited only to be transparent
about where this thesis's numbers came from and where they didn't.

### Limitations

- Round Robin is a **tracking** heuristic, not an optimizer — it has no
  mechanism to prioritize which EVs charge based on urgency, price, or
  remaining time, and no guarantee of fairness beyond FIFO rotation. Its
  zero-overload result here reflects that the setpoint itself is
  achievable at this oversubscription ratio, not that Round Robin is
  provably the best way to achieve it.
- Same station-scope, grid-modeling, evaluation-window, and price-source
  limitations as AFAP's Limitations section above — not repeated in full.
- `power_setpoint_flexiblity: 80%` was inherited, not tuned; a different
  setpoint flexibility could change how much headroom Round Robin has to
  work with, and this was not swept.