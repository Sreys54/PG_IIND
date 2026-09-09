"""
Week 5, Part A: Colombian peso (COP) economics constants, replacing the
ENTSO-E-derived EUR `total_profits` registry column for all reporting
purposes (Weeks 1-4 used Netherlands day-ahead prices inherited from
EV2Gym's default dataset -- see the Week 5 Gate 0 report, 2026-09-08, for
the full audit of why that column cannot be reinterpreted as Colombian
economics and must be recomputed instead).

Origins used, exactly one per constant below, following the same
declared-origin convention as ev2gym_thesis/rl/config_rl.py:
  "validated external, single point, no time series" -- a real published
      figure from a named source and retrieval date, not a time series and
      not derived from this project's own modelling.
  "validated external, regulated tariff sheet"       -- read from a
      downloaded, invariant-checked Enel Colombia regulatory PDF (see
      scripts/fetch_enel_tariffs.py), not modelled or estimated.
  "declared assumption"                              -- a labelled
      simplification this project adopts and states as such, per
      CLAUDE.md rule 5.

Neither constant is a price *series*: EV2Gym's price pipeline
(ev2gym/utilities/loaders.py:load_electricity_prices) produces an
hourly-varying array; this module deliberately does not. Both Colombian
inputs are flat (see Week 5 Gate 0 §5.2's price-independence finding and
the Week 5 brief's section 7 "no intraday price signal" result) -- there is
no EV2Gym-native price array to replace, because no arm's control decision
in this project has ever depended on the price series (verified, not
assumed: see the Gate 0 report's price-independence table). This module is
consumed by a post-hoc economics recompute
(ev2gym_thesis/economics_recompute.py), never by anything inside
ev2gym/ itself.
"""

# doc:begin retail_tariff
# Source: Enel Colombia, "Estas son las estaciones de carga para vehiculos
# electricos en Bogota", published August 2025.
# https://www.enel.com.co/es/historias/a202508-primera-red-de-cargadores-electricos-publica.html
# Exact quoted sentence: "La recarga tendra un valor de 1.450 pesos por
# kilovatio, que puede variar segun el costo de la energia."
#
# Origin: validated external, single point, no time series.
#
# Declared assumption, stated in these terms per the Week 5 brief: a
# recency search restricted to Enel X (enelx.com) and Enel Colombia
# (enel.com.co) on 2026-09-08 found no more recent published EV public
# charging retail price from either source -- a negative result, logged in
# thesis_docs/chapters/00_lab_log.md's 2026-09-08 entry, not silently
# substituted with a competitor's (Terpel Voltex/Celsia/Primax) price. The
# August 2025 figure is therefore carried forward and paired with a 2026
# energy purchase cost (ENERGY_PURCHASE_COST_COP_PER_KWH below). This
# mismatch is deliberate and its direction is known: pairing a 2025 revenue
# figure with a 2026 cost figure UNDERSTATES the operator's margin (retail
# prices trend upward, not downward, over this period in Colombia -- see
# the CU series in thesis_docs/sources/enel_tariffs/nivel2_cu_2026_monthly.csv,
# which rose 19.2% Jan-Aug 2026 alone). Every profitability result computed
# from this constant is therefore a LOWER BOUND on the operator's margin,
# not a central estimate -- report it that way, not as a point estimate.
RETAIL_TARIFF_COP_PER_KWH = 1450.0
RETAIL_TARIFF_SOURCE = (
    "Enel Colombia, 'Estas son las estaciones de carga para vehiculos "
    "electricos en Bogota', August 2025, "
    "https://www.enel.com.co/es/historias/a202508-primera-red-de-cargadores-electricos-publica.html"
)
RETAIL_TARIFF_RETRIEVAL_DATE = "2025-08"  # article publication month, as dated in its own URL slug
# doc:end retail_tariff

# doc:begin retail_tariff_sensitivity
# +/-20% sensitivity band, per the Week 5 brief's explicit instruction that
# 1,450 COP/kWh is "indicative and a year old" -- not a literature value or
# a measured uncertainty, a declared assumption sized to test whether the
# operator-economics RANKING across algorithms is robust to the retail
# price being wrong by a reasonable margin in either direction.
RETAIL_TARIFF_SENSITIVITY_FRACTION = 0.20
# doc:end retail_tariff_sensitivity

# doc:begin energy_purchase_cost
# Source: Enel Colombia's regulated monthly tariff sheet ("pliego
# tarifario"), SECTOR NO RESIDENCIAL, Nivel de Tension 2 (11.4 y 13.2 kV),
# row "INDUSTRIAL Y COMERCIAL CON CONTRIBUCION, SENCILLA Monomia" --
# extracted and invariant-validated by scripts/fetch_enel_tariffs.py from
# the locally stored PDF (thesis_docs/sources/enel_tariffs/2026-agosto.pdf),
# not the live URL (Enel rotates this content -- see that script's
# docstring). August 2026 is the base case per the Week 5 brief: the most
# recently published sheet at the time of writing (confirmed 2026-09-08 --
# September 2026 is not yet published, see
# scripts/fetch_enel_tariffs.py's check_listing_for_new_month()), and NOT
# an average across months, since the CU is on a clear upward trend through
# 2026 (+19.2% Jan-Aug), not fluctuating around a mean -- an average would
# understate today's cost, not estimate it.
#
# Nivel 2 is the correct row because station_v0_bogota models a station
# with its own local transformer fed at medium voltage. The WITH-
# CONTRIBUTION value is used (not the base CUv) because a commercial EV
# charging operator is not documented anywhere in CREG/Ley 1964 de 2019 as
# exempt from the contribucion de solidaridad -- no such exemption was
# found when checked (Week 5 Gate 0 audit), so the exemption is not applied
# without evidence, per the brief's explicit instruction.
#
# Origin: validated external, regulated tariff sheet.
#
# Six-component breakdown (COP/kWh, August 2026, Nivel 2,
# sin contribucion -- see thesis_docs/sources/enel_tariffs/nivel2_cu_2026_monthly.csv):
#   Generacion (Gm,i,j)        374.9931
#   Transmision (Tm)            49.3138
#   Distribucion (Dn,m)        183.7335
#   Comercializacion (Cvm,i,j)  83.3438
#   Perdidas (PRn,m,i,j)        23.9960
#   Restricciones (Rm,j)         6.0877
#   CUv, sin contribucion      721.4679
#   Con contribucion (x1.20)   865.7615  <- this constant
ENERGY_PURCHASE_COST_COP_PER_KWH = 865.7615
ENERGY_PURCHASE_COST_SOURCE = (
    "Enel Colombia, pliego tarifario agosto 2026, SECTOR NO RESIDENCIAL, "
    "Nivel de Tension 2, INDUSTRIAL Y COMERCIAL CON CONTRIBUCION / SENCILLA "
    "Monomia -- thesis_docs/sources/enel_tariffs/2026-agosto.pdf"
)
ENERGY_PURCHASE_COST_TARIFF_MONTH = "2026-08"
ENERGY_PURCHASE_COST_RETRIEVAL_DATE = "2026-09-08"
ENERGY_PURCHASE_COST_WITH_CONTRIBUTION = True
ENERGY_PURCHASE_COST_CONTRIBUTION_FACTOR = 1.20
# doc:end energy_purchase_cost


def compute_row_economics(total_energy_charged_kwh: float,
                           retail_tariff_cop_per_kwh: float = RETAIL_TARIFF_COP_PER_KWH,
                           purchase_cost_cop_per_kwh: float = ENERGY_PURCHASE_COST_COP_PER_KWH) -> dict:
    """Pure function: energy delivered (kWh) -> Colombian-peso economics for
    one registry row. Never re-simulates -- see the Week 5 Gate 0 report's
    price-independence finding (every arm's control decision in this
    project is price-independent, verified by reading every reward/state/
    oracle-objective function, not assumed) for why a post-hoc recompute
    from total_energy_charged alone is valid instead of re-running EV2Gym.

    Deliberately named without the word "profit" anywhere -- see the Week 5
    Gate 0 report's correction: EV2Gym's own `total_profits` column was
    read as a profit/revenue figure in Weeks 1-4 when it is actually a
    negated purchase cost. Explicit names only, so this mistake cannot
    repeat with the Colombian columns.
    """
    revenue = total_energy_charged_kwh * retail_tariff_cop_per_kwh
    cost = total_energy_charged_kwh * purchase_cost_cop_per_kwh
    return {
        "retail_revenue_cop": revenue,
        "energy_purchase_cost_cop": cost,
        "gross_margin_cop": revenue - cost,
    }
