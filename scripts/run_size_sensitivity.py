"""
Week 2 station-size sensitivity sweep.

Runs ChargeAsFastAsPossible (AFAP) and RoundRobin over 4 new configs in
experiments/phase1_baseline/configs/station_sensitivity/ (n=2 and n=16
ports, at a fixed 100 kW transformer and at a transformer scaled to hold
the reference case's 4:1 oversubscription ratio). The n=8/100kW reference
case (station_v0_bogota.yaml) is NOT re-run -- its already-obtained,
committed results are read from
experiments/phase1_baseline/results/baseline_afap.csv and
baseline_roundrobin.csv and merged into the same output table.

Output: experiments/phase1_baseline/results/size_sensitivity.csv, one row
per (config, algorithm).
"""
import csv
import yaml
from ev2gym.models.ev2gym_env import EV2Gym
from ev2gym.baselines.heuristics import ChargeAsFastAsPossible, RoundRobin

SEED = 42
CONFIG_DIR = "experiments/phase1_baseline/configs/station_sensitivity"
RESULTS_DIR = "experiments/phase1_baseline/results"

SENSITIVITY_CONFIGS = [
    "station_n02_tx100",
    "station_n16_tx100",
    "station_n02_tx025",
    "station_n16_tx200",
]

REFERENCE_CONFIG = {
    "name": "station_v0_bogota",
    "n_ports": 8,
    "transformer_kw": 100,
    "csv_by_algo": {
        "ChargeAsFastAsPossible": f"{RESULTS_DIR}/baseline_afap.csv",
        "RoundRobin": f"{RESULTS_DIR}/baseline_roundrobin.csv",
    },
}

STATS_COLUMNS = [
    "total_ev_served",
    "total_energy_charged",
    "total_transformer_overload",
    "average_user_satisfaction",
    "energy_user_satisfaction",
    "min_energy_user_satisfaction",
    "total_profits",
    "tracking_error",
    "energy_tracking_error",
]

OUTPUT_COLUMNS = (
    ["config", "algorithm", "seed", "sim_date", "n_ports", "transformer_kw",
     "oversubscription_ratio"]
    + STATS_COLUMNS
)


def run_config(config_name, algo_cls, algo_name):
    config_path = f"{CONFIG_DIR}/{config_name}.yaml"
    with open(config_path) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    n_ports = cfg["number_of_charging_stations"]
    transformer_kw = cfg["transformer"]["max_power"]

    env = EV2Gym(config_file=config_path, seed=SEED, save_replay=False, save_plots=False)
    state, _ = env.reset(seed=SEED)
    try:
        agent = algo_cls(env)
    except TypeError:
        agent = algo_cls()

    stats = None
    for t in range(env.simulation_length):
        actions = agent.get_action(env)
        state, reward, done, truncated, stats = env.step(actions)
        if done:
            break

    installed_kw = n_ports * cfg["ev"]["max_ac_charge_power"]
    row = {
        "config": config_name,
        "algorithm": algo_name,
        "seed": SEED,
        "sim_date": str(env.sim_starting_date),
        "n_ports": n_ports,
        "transformer_kw": transformer_kw,
        "oversubscription_ratio": round(installed_kw / transformer_kw, 3),
    }
    for col in STATS_COLUMNS:
        row[col] = stats.get(col)
    return row


def load_reference_row(algo_name):
    csv_path = REFERENCE_CONFIG["csv_by_algo"][algo_name]
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        ref = next(reader)

    n_ports = REFERENCE_CONFIG["n_ports"]
    transformer_kw = REFERENCE_CONFIG["transformer_kw"]
    row = {
        "config": REFERENCE_CONFIG["name"],
        "algorithm": algo_name,
        "seed": ref["seed"],
        "sim_date": ref["sim_date"],
        "n_ports": n_ports,
        "transformer_kw": transformer_kw,
        "oversubscription_ratio": round(n_ports * 50 / transformer_kw, 3),
        "total_ev_served": ref["total_ev_served"],
        "total_energy_charged": ref["total_energy_charged"],
        "total_transformer_overload": ref["total_transformer_overload"],
        "average_user_satisfaction": ref["average_user_satisfaction"],
        "total_profits": ref["total_profits"],
        # not present in the Week 1 baseline CSVs (only saved a metric subset);
        # left blank rather than guessed, per project convention of never
        # interpolating unreported numbers.
        "energy_user_satisfaction": "",
        "min_energy_user_satisfaction": "",
        "tracking_error": "",
        "energy_tracking_error": "",
    }
    return row


if __name__ == "__main__":
    rows = []

    for algo_name in ["ChargeAsFastAsPossible", "RoundRobin"]:
        rows.append(load_reference_row(algo_name))

    algos = [
        (ChargeAsFastAsPossible, "ChargeAsFastAsPossible"),
        (RoundRobin, "RoundRobin"),
    ]
    for config_name in SENSITIVITY_CONFIGS:
        for algo_cls, algo_name in algos:
            print(f"Running {config_name} / {algo_name} ...")
            row = run_config(config_name, algo_cls, algo_name)
            rows.append(row)
            print(f"  -> total_ev_served={row['total_ev_served']}, "
                  f"total_transformer_overload={row['total_transformer_overload']}")

    out_path = f"{RESULTS_DIR}/size_sensitivity.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"\nWrote {len(rows)} rows to {out_path}")
