# Week 7 (Objective 5) — Sources and Access Dates

## Medellín network operator tariff (EPM)

- **Document:** Empresas Públicas de Medellín E.S.P., "Tarifas y Costo de
  Energía Eléctrica - Mercado Regulado - septiembre de 2026", 2 pages.
- **URL:**
  https://www.epm.com.co/content/dam/epm/clientes-y-usuarios/energia/tarifas-energia/Tarifas%202026/9.PublicacionTarifasSeptiembre162026_ANT_OM.pdf
- **Listing page:** https://www.epm.com.co/clientesyusuarios/energia/tarifas-energia/
  (January–September 2026 sheets listed; September is the most recent).
- **Accessed:** 2026-10-05, 23:21 (UTC−5), i.e. 2026-10-06T04:21Z.
- **Local copy:** `thesis_docs/sources/epm_tariffs/2026-septiembre_epm_tarifas.pdf`
  (341,135 bytes).
- **Values used** (non-residential Nivel II, "Tarifa Horaria", COP/kWh):

| Period | Industrial y Comercial (with contribution) | Oficial y Exentos (without contribution, = CU) |
|---|---:|---:|
| Punta | 923.92 | 769.94 |
| Fuera de Punta | 917.58 | 764.65 |

  CU Monomio Nivel II (without contribution, no component breakdown
  published): 767.30.
- **Peak hours:** 9 a.m.–12 m and 6 p.m.–9 p.m.; all other hours are off-peak
  (as printed on the sheet).
- **Invariants** (`ev2gym_thesis/prices/medellin.py::check_invariants`):

| Period | Six components | Stated CU | Abs diff | Tolerance 0.01 | With / without contribution | Rel diff | Tolerance 0.001 |
|---|---:|---:|---:|---|---:|---:|---|
| Punta | 769.94 | 769.94 | 0.00 | pass | 1.19999 | 1.0e-5 | pass |
| Fuera de Punta | 764.66 | 764.65 | 0.01 | pass, at the inclusive bound | 1.20000 | ~0 | pass |

## Medellín retail EV charging price — negative result

No EPM EV-charging price per kWh was found. Searched on 2026-10-05:
- epm.com.co: the tariff pages, and the mobility URL, which returned 404;
- press coverage of EPM's 20 public "ecoestaciones": Portafolio,
  El Colombiano, El Carro Colombiano;
- EPM's own advertorial, "EPM, promotor de movilidad eléctrica en
  Colombia", El Colombiano, 2021-10-02.

None states a per-kWh price. The sources say only that charging is billed
through the utility invoice or the EPM app. Per the pairing rule, no
competitor's price (for example Tesla's 1,300 COP/kWh in Medellín) is
substituted. Bogotá's Enel 1,450 COP/kWh (August 2025) is used **only as a
labelled sensitivity**.

## Medellín as the replicability city — justification sources

- Medellín is a district of categoría especial and has its own network
  operator and regulated retailer (EPM). Its tariff sheet is published
  monthly in the same CREG CU format as Enel's (G, T, D, Cv, PR, R), which
  is what makes the Week 5 invariants applicable unchanged.
- The EPM sheet's page 2 also publishes EPM-as-retailer CUs in the Enel,
  CELSIA and EMCALI operator markets, which confirms the common regulatory
  format across Colombian operators.
