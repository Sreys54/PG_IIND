"""
Week 7, Objective 5 (replicability): Medellin tariff constants and their
invariant-checked extraction from EPM's regulated tariff sheet.

City (labelled assumption): Medellin, categoria especial; network operator
and regulated retailer: Empresas Publicas de Medellin (EPM).

Source: EPM, "Tarifas y Costo de Energia Electrica - Mercado Regulado -
septiembre de 2026" (the most recent sheet listed on
https://www.epm.com.co/clientesyusuarios/energia/tarifas-energia/ on
2026-10-05), saved as
thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf.

What EPM publishes for non-residential Nivel II (unlike Enel's Bogota sheet,
which publishes a with-contribution MONOMIAL Nivel 2 line):
  - hourly ("Tarifa Horaria") Nivel II rates, Punta and Fuera de Punta, for
    "Industrial y Comercial" (WITH contribution) and "Oficial y Exentos"
    (WITHOUT contribution = the CU), each with its six CU components;
  - a monomial "CU Monomio" for Nivel II WITHOUT contribution and WITHOUT a
    component breakdown.

Invariants (the Week 5 ones, same tolerances as scripts/fetch_enel_tariffs.py):
  1. the six CU components sum to the stated CU (abs tolerance 0.01 COP/kWh,
     applied inclusively after rounding -- six two-decimal published
     components can legitimately miss the two-decimal total by 0.01);
  2. the with-contribution line equals 1.20x the without-contribution line
     (relative tolerance 0.001).
Both are checked on the Punta and on the Fuera de Punta lines; the
monomial CU has no published components, so invariant 1 cannot be applied
to it and it is not used as the base value.
"""
import re

SUM_TOLERANCE = 0.01
CONTRIBUTION_FACTOR = 1.20
CONTRIBUTION_TOLERANCE = 0.001
COMPONENTS = ["G", "T", "D", "CV", "PR", "R"]
_COMPONENT_LABELS = {
    "G": r"Costo compra: Gm,i", "T": r"Cargo transporte STN: Tm", "D": r"Cargo transporte SDL: Dn,m",
    "CV": r"Margen comercializaci.n: CVm,i,j", "PR": r"Costo G, T, p.rdidas: PRn,m", "R": r"Restricciones: Rm",
}
_NUM = r"(\d+\.\d{2})"


# doc:begin parse_epm_nivel2
def parse_epm_nivel2(text: str) -> dict:
    """Parse the Nivel II/III/IV hourly block of an EPM tariff sheet's page 1
    text (pdfplumber). Returns Nivel II values only:
    {"punta": {...}, "fuera_punta": {...}, "cu_monomio_sin_contribucion": float},
    each period dict holding con_contribucion, sin_contribucion and the six
    components. Raises ValueError if the block cannot be located."""
    start = text.find("Nivel II Nivel III Nivel IV")
    if start < 0:
        raise ValueError("Nivel II/III/IV block not found")
    block = text[start:]
    six = lambda label: [float(x) for x in re.search(label + r"\s+" + r"\s+".join([_NUM] * 6), block).groups()]
    con = six(r"Industrial y Comercial")
    sin = six(r"Total CU")
    out = {}
    for i, period in enumerate(["punta", "fuera_punta"]):
        out[period] = {"con_contribucion": con[i], "sin_contribucion": sin[i],
                       **{c: six(_COMPONENT_LABELS[c])[i] for c in COMPONENTS}}
    out["cu_monomio_sin_contribucion"] = float(re.search(r"CU Monomio\s+" + _NUM, block).group(1))
    return out
# doc:end parse_epm_nivel2


# doc:begin check_invariants
def check_invariants(period: dict) -> dict:
    comp_sum = round(sum(period[c] for c in COMPONENTS), 6)
    sum_diff = round(abs(comp_sum - period["sin_contribucion"]), 6)
    rel = abs(period["con_contribucion"] - CONTRIBUTION_FACTOR * period["sin_contribucion"]) / period["sin_contribucion"]
    return {"component_sum": comp_sum, "sum_abs_diff": sum_diff, "sum_ok": sum_diff <= SUM_TOLERANCE,
            "contribution_ratio": period["con_contribucion"] / period["sin_contribucion"],
            "contribution_rel_diff": rel, "contribution_ok": rel <= CONTRIBUTION_TOLERANCE}
# doc:end check_invariants


# doc:begin medellin_constants
# Values extracted from the September 2026 sheet by parse_epm_nivel2 and
# validated by check_invariants (pinned in ev2gym_thesis/tests/test_replicability.py).
EPM_SHEET_MONTH = "2026-09"
EPM_NIVEL2_PUNTA_CON_CONTRIBUCION = 923.92
EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION = 917.58
EPM_NIVEL2_PUNTA_SIN_CONTRIBUCION = 769.94
EPM_NIVEL2_FUERA_PUNTA_SIN_CONTRIBUCION = 764.65
EPM_NIVEL2_CU_MONOMIO_SIN_CONTRIBUCION = 767.30

# Base energy purchase cost for the flat-tariff economics (labelled
# assumption, conservative): the HIGHER of the two invariant-validated
# with-contribution Nivel II commercial rates (Punta). Using the higher rate
# makes every Medellin margin a LOWER bound, the same direction as Bogota's
# Week 5 framing. Fuera de Punta (917.58) and the monomial CU x 1.20
# (= 920.76, derived, not published) are reported as sensitivities.
ENERGY_PURCHASE_COST_COP_PER_KWH_MEDELLIN = EPM_NIVEL2_PUNTA_CON_CONTRIBUCION

# Retail EV charging price: NO EPM EV-charging price per kWh is published
# (searched 2026-10-05: epm.com.co tariff and mobility pages, press coverage
# of EPM's 20 public charging stations; negative result logged in
# 00_lab_log.md and thesis_docs/sources/SOURCES_week7.md). Per the brief's
# pairing rule, no competitor's price is substituted: Bogota's Enel
# 1,450 COP/kWh is used as a LABELLED SENSITIVITY, not as a Medellin price.
RETAIL_TARIFF_COP_PER_KWH_MEDELLIN_SENSITIVITY = 1450.0
RETAIL_TARIFF_MEDELLIN_IS_PUBLISHED = False

# Intraday spread of the validated with-contribution Nivel II rates:
# (Punta - Fuera de Punta) / Fuera de Punta.
INTRADAY_SPREAD_MEDELLIN = (EPM_NIVEL2_PUNTA_CON_CONTRIBUCION - EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION) \
    / EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION
# doc:end medellin_constants
