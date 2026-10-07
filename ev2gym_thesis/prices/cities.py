"""
Closure brief, Part D2: Nivel 2 commercial energy cost for every
municipality of categoria especial, from each network operator's own
regulated tariff sheet.

City list (official source, saved): Contaduria General de la Nacion,
"Historicos hasta vigencia 2025" categorisation workbook, column "Vigencia
2026" (self-categorisation decrees of 2025), accessed 2026-10-06,
thesis_docs/sources/municipal_categories/cgn_categorizacion_historicos_hasta_2025.xlsx.
The six municipalities with category ESP for 2026 are: Bogota D.C.,
Medellin, Cali, Barranquilla, Cartagena and Bucaramanga. The criterion is Ley
617 de 2000, Art. 6: population >= 500,001 and ICLD > 400,000 SMMLV
(thesis_docs/sources/municipal_categories/ley_617_2000.pdf).

Every value below is transcribed from the saved sheet named in SOURCE. Each
city records:
  - cu_sin: the Nivel 2 CU without contribution;
  - components: the six published components (G, T, D, C, PR, R), when
    published;
  - flat_con: the flat (monomial) Nivel 2 commercial rate WITH the 20%
    contribution, flagged "published" or "derived = 1.20 x cu_sin" when the
    sheet does not print it;
  - tou: the operator's two-band Nivel 2 option (with contribution), its
    band hours, and whether the values are published or derived;
  - unavailable: what the sheet does not publish (listed, never filled in).

Invariants (same as Week 5/7, ev2gym_thesis/prices/medellin.check_invariants):
the components sum to the CU within 0.01 COP/kWh; with-contribution =
1.20 x without within 0.1%.
"""
from ev2gym_thesis.prices import medellin as _med

SUM_TOLERANCE = _med.SUM_TOLERANCE
CONTRIBUTION_FACTOR = _med.CONTRIBUTION_FACTOR
CONTRIBUTION_TOLERANCE = _med.CONTRIBUTION_TOLERANCE
SIM_START_HOUR = 5        # station_v0_bogota.yaml: hour 5, minute 0
STEP_HOURS = 0.25         # timescale 15 min

# doc:begin city_tariffs
CITIES = {
    "Bogota": {
        "operator": "Enel Colombia", "sheet_month": "2026-08",
        "source": "thesis_docs/sources/enel_tariffs/2026-agosto.pdf",
        "cu_sin": 721.4679,
        "components": {"G": 374.9931, "T": 49.3138, "D": 183.7335, "C": 83.3438, "PR": 23.9960, "R": 6.0877},
        "flat_con": 865.7615, "flat_con_status": "published",
        "tou": {"name": "Opciones horarias", "peak_hours": [(9, 12), (18, 21)],
                "peak_con": 877.5709, "offpeak_con": 864.0163,
                "peak_sin": 731.3091, "offpeak_sin": 720.0136, "status": "published"},
        "charging_price": 1450.0,
        "charging_price_source": "Enel Colombia, Aug 2025 (Week 5, ev2gym_thesis/prices/colombia.py)",
        "unavailable": [],
    },
    "Medellin": {
        "operator": "EPM", "sheet_month": "2026-09",
        "source": "thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf",
        "cu_sin": _med.EPM_NIVEL2_CU_MONOMIO_SIN_CONTRIBUCION,   # 767.30, no components published
        "components": None,
        # Punta line components (G 401.37 of 769.94), used for the generation share
        "generation_component": 401.37, "generation_reference_cu": 769.94,
        "flat_con": round(CONTRIBUTION_FACTOR * _med.EPM_NIVEL2_CU_MONOMIO_SIN_CONTRIBUCION, 4),
        "flat_con_status": "derived = 1.20 x CU monomio (not published)",
        "tou": {"name": "Tarifa horaria", "peak_hours": [(9, 12), (18, 21)],
                "peak_con": _med.EPM_NIVEL2_PUNTA_CON_CONTRIBUCION, "offpeak_con": _med.EPM_NIVEL2_FUERA_PUNTA_CON_CONTRIBUCION,
                "peak_sin": _med.EPM_NIVEL2_PUNTA_SIN_CONTRIBUCION, "offpeak_sin": _med.EPM_NIVEL2_FUERA_PUNTA_SIN_CONTRIBUCION,
                "status": "published"},
        "charging_price": None,
        "charging_price_source": "not published by EPM (Week 7 search, SOURCES_week7.md)",
        "unavailable": ["components of the monomial CU", "per-kWh public charging price"],
    },
    "Cali": {
        "operator": "EMCALI", "sheet_month": "2026-01",
        "source": "thesis_docs/sources/tariffs_d2/emcali_2026-enero.pdf",
        "cu_sin": 625.7458,
        "components": {"G": 308.8267, "T": 52.2138, "D": 152.3953, "C": 67.9090, "PR": 25.0050, "R": 19.3960},
        "flat_con": round(CONTRIBUTION_FACTOR * 625.7458, 4),
        "flat_con_status": "derived = 1.20 x CU (Nivel 2 commercial with contribution not printed; "
                           "factor verified on the printed Nivel 1 commercial line 910.7360 = 1.20 x 758.9467)",
        "contribution_check": {"sin_contribucion": 758.9467, "con_contribucion": 910.7360},
        "tou": {"name": "Doble horaria", "peak_hours": [(9, 12), (18, 21)],
                "peak_sin": 629.8683, "offpeak_sin": 624.0957,
                "peak_con": round(CONTRIBUTION_FACTOR * 629.8683, 4), "offpeak_con": round(CONTRIBUTION_FACTOR * 624.0957, 4),
                "status": "published without contribution; with-contribution derived x 1.20"},
        "charging_price": 2500.0,
        "charging_price_source": "secondary (press): El Pais Cali, 2025-04-30, "
                                 "tariffs_d2/press_elpais_emcali_carga_2025-04-30.html; no EMCALI page located",
        "unavailable": ["any 2026 sheet after January (latest retrievable on 2026-10-06; Sep 2026 not located)"],
    },
    "Barranquilla": {
        "operator": "Air-e (intervened by Superservicios)", "sheet_month": "2026-09",
        "source": "thesis_docs/sources/tariffs_d2/aire_2026-septiembre.pdf",
        "cu_sin": 746.5458,
        "components": {"G": 449.0545, "T": 43.8332, "D": 75.8592, "C": 135.6644, "PR": 32.9191, "R": 9.2154},
        "flat_con": 895.8549,
        "flat_con_status": "published (Nivel 2 estratos 5 y 6 line, same 20% contribution as commercial)",
        "contribution_check": {"sin_contribucion": 746.5458, "con_contribucion": 895.8549},
        "tou": {"name": "Monomia doble tipo 1", "peak_hours": [(17, 22)],
                "peak_con": 956.74, "offpeak_con": 869.52, "peak_sin": 797.28, "offpeak_sin": 724.60,
                "status": "published"},
        "other_tou_options": {"Monomia doble tipo 2 (altas 9-13, 18-22)": (886.38, 889.20),
                              "Monomia triple (max 9-12, 18-21 / min 0-4, 23-24)": (892.67, 909.38)},
        "charging_price": None,
        "charging_price_source": "no Air-e public EV charging price located",
        "unavailable": ["per-kWh public charging price"],
    },
    "Cartagena": {
        "operator": "Afinia (Grupo EPM)", "sheet_month": "2026-09",
        "source": "thesis_docs/sources/tariffs_d2/afinia_2026-septiembre.pdf",
        # The six components sum to the 'CU mes con COT' (859.76), not the
        # 'sin COT' line (805.46); the CU with COT is what a Nivel 2 user pays.
        "cu_sin": 859.76, "cu_sin_without_cot": 805.46,
        "components": {"G": 435.32, "T": 43.83, "D": 123.50, "C": 199.25, "PR": 50.30, "R": 7.55},
        "flat_con": round(CONTRIBUTION_FACTOR * 859.76, 4),
        "flat_con_status": "derived = 1.20 x CU with COT (monomial commercial line not printed)",
        "tou": {"name": "Monomia doble tipo 1", "peak_hours": [(17, 22)],
                "peak_con": 1031.46, "offpeak_con": 1031.22, "peak_sin": 859.55, "offpeak_sin": 859.35,
                "status": "published (Nivel 2 row identified through the residential >173 kWh line, which "
                          "pays the full CU)"},
        "other_tou_options": {"Monomia doble tipo 2 (altas 9-13, 18-22)": (1013.44, 1039.61),
                              "Monomia triple (max 9-12, 18-21 / min 0-4, 23-24)": (1017.90, 1036.07)},
        "charging_price": None,
        "charging_price_source": "no Afinia public EV charging price located",
        "unavailable": ["per-kWh public charging price"],
    },
    "Bucaramanga": {
        "operator": "ESSA (Grupo EPM)", "sheet_month": "2026-09",
        "source": "thesis_docs/sources/tariffs_d2/essa_2026-septiembre.pdf",
        "cu_sin": 855.67,
        "components": {"G": 479.62, "T": 43.83, "D": 197.10, "C": 92.98, "PR": 34.85, "R": 7.28},
        "flat_con": 1026.80, "flat_con_status": "published",
        "contribution_check": {"sin_contribucion": 855.67, "con_contribucion": 1026.80},
        "tou": None,
        "charging_price": None,
        "charging_price_source": "ESSA prices public charging per 'Unidad de Recarga Vehicular' (~1,500 fast / "
                                 "~1,200 normal COP per URV, Vanguardia 2026-06-01); the URV is not defined in kWh, "
                                 "so no per-kWh price is stated",
        "unavailable": ["time-of-use Nivel 2 option (sheet is monomial only)", "per-kWh public charging price"],
    },
}
# doc:end city_tariffs


def invariants(city: str) -> dict:
    c = CITIES[city]
    out = {"city": city}
    if c["components"]:
        s = round(sum(c["components"].values()), 6)
        out.update(component_sum=s, sum_abs_diff=round(abs(s - c["cu_sin"]), 6),
                   sum_ok=abs(s - c["cu_sin"]) <= SUM_TOLERANCE + 1e-9)
    else:
        out.update(component_sum=None, sum_abs_diff=None, sum_ok=None)
    pairs = []
    if c.get("contribution_check"):
        pairs.append((c["contribution_check"]["sin_contribucion"], c["contribution_check"]["con_contribucion"]))
    t = c["tou"]
    if t and "published" == t["status"][:9] and "derived" not in t["status"]:
        pairs += [(t["peak_sin"], t["peak_con"]), (t["offpeak_sin"], t["offpeak_con"])]
    if c["flat_con_status"] == "published" and not c.get("contribution_check"):
        pairs.append((c["cu_sin"], c["flat_con"]))
    rel = [abs(con - CONTRIBUTION_FACTOR * sin) / sin for sin, con in pairs]
    out.update(n_contribution_pairs=len(pairs), contribution_max_rel_diff=max(rel) if rel else None,
               contribution_ok=(max(rel) <= CONTRIBUTION_TOLERANCE) if rel else None)
    return out


def spread(city: str):
    """(peak - off-peak) / off-peak of the city's two-band Nivel 2 option, the
    Week 5/7 definition; None when no time-of-use option is published."""
    t = CITIES[city]["tou"]
    return None if t is None else (t["peak_con"] - t["offpeak_con"]) / t["offpeak_con"]


def generation_share(city: str) -> float:
    c = CITIES[city]
    if c["components"]:
        return c["components"]["G"] / c["cu_sin"]
    return c["generation_component"] / c["generation_reference_cu"]


def step_in_peak(step: int, peak_hours) -> bool:
    h = (SIM_START_HOUR + step * STEP_HOURS) % 24
    return any(a <= h < b for a, b in peak_hours)


def energy_by_band(station_power_kw, peak_hours):
    """kWh delivered in the peak band and outside it, from the per-step
    station power (kW, 15-min steps starting at 05:00)."""
    peak = off = 0.0
    for k, p in enumerate(station_power_kw):
        e = max(float(p), 0.0) * STEP_HOURS
        if step_in_peak(k, peak_hours):
            peak += e
        else:
            off += e
    return peak, off
