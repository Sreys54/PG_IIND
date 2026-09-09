"""
Week 5: human-readable Excel export of results/economics_cop.csv. Uses
the shared ev2gym_thesis.xlsx_export utility -- see that module's
docstring for the formatting convention every export in this project
follows from here on.

Usage: PYTHONPATH=. python scripts/export_economics_cop_xlsx.py
"""
from ev2gym_thesis.xlsx_export import (
    export_formatted_xlsx, COP_FORMAT, KWH_FORMAT, COP_PER_KWH_FORMAT,
)

SRC_CSV = "results/economics_cop.csv"
OUT_XLSX = "results/economics_cop.xlsx"

# Every row is ONE simulated day (96 steps x 15 min) for one
# (algorithm, scenario seed, evaluation day) cell -- "/day" on every
# peso and kWh column states that explicitly, so it can't be misread as
# a monthly or annual figure.
COLUMN_LABELS = {
    "config_name": "Config Name",
    "algorithm": "Algorithm",
    "seed": "Scenario Seed",
    "eval_day": "Evaluation Day",
    "algorithm_family": "Algorithm Family",
    "total_energy_charged_kwh": "Energy Charged (kWh per simulated day)",
    "retail_revenue_cop": "Retail Revenue (COP per simulated day)",
    "energy_purchase_cost_cop": "Energy Purchase Cost (COP per simulated day)",
    "gross_margin_cop": "Gross Margin, Revenue minus Cost (COP per simulated day)",
    "retail_tariff_cop_per_kwh": "Retail Tariff, Flat Rate (COP per kWh)",
    "retail_tariff_month": "Retail Tariff Source Month",
    "energy_purchase_cost_cop_per_kwh": "Energy Purchase Cost, Flat Rate (COP per kWh)",
    "cu_tariff_month": "Enel CU Tariff Sheet Month",
    "cu_with_contribution": "CU Includes 20% Contribucion de Solidaridad (True/False)",
}

NUMBER_FORMATS = {
    "Energy Charged (kWh per simulated day)": KWH_FORMAT,
    "Retail Revenue (COP per simulated day)": COP_FORMAT,
    "Energy Purchase Cost (COP per simulated day)": COP_FORMAT,
    "Gross Margin, Revenue minus Cost (COP per simulated day)": COP_FORMAT,
    "Retail Tariff, Flat Rate (COP per kWh)": COP_PER_KWH_FORMAT,
    "Energy Purchase Cost, Flat Rate (COP per kWh)": COP_PER_KWH_FORMAT,
}

if __name__ == "__main__":
    export_formatted_xlsx(SRC_CSV, OUT_XLSX, COLUMN_LABELS, NUMBER_FORMATS, sheet_name="economics_cop")
