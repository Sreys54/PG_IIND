# Sources — final capacity brief (DC session duration)

Accessed 2026-10-06 (Bogotá). **None of these sources is Colombian
per-session data.** Enel publishes no session statistics. Every use in the
thesis is labelled as an external reference, never as Bogotá data.

## U.S. Department of Energy, Vehicle Technologies Office (2023). FOTW #1319

- **Local copy:** `doe_fotw_1319.html` (raw HTML, 120,911 bytes, HTTP 200).
- **URL:** https://www.energy.gov/cmei/vehicles/articles/fotw-1319-december-4-2023-ev-charging-paid-dc-fast-charging-stations-average
- **Verified in the saved page:**
  - It covers DC fast charging from June 30, 2020, to June 30, 2023.
  - Paid sessions: **1,412,050** sessions, **22.0 kWh** per session,
    **42 min** per session.
  - Free sessions: 957,265 sessions, 40.7 kWh, 78 min.
  - Totals: 2,369,315 sessions, 29.4 kWh, 54 min.
  - The page notes: "The statistics in this study are from a self-selected
    set of EV owners nationwide. They do not include charging sessions from
    Tesla's Supercharger network." The data source is the Energetics EVWATTS
    Dashboard.
- **Byline:** none, so the reference uses the office as author.

## Hardman (2026). Findings

- **Local copies:**
  - `findings_dcfc_driver_activities.html` (article, 318,272 bytes,
    HTTP 200);
  - `findings_dcfc_supplemental_information.pdf` (Supplemental
    Information, 5 pages).
- **URL:** https://findingspress.org/article/162484-exploring-electric-vehicle-driver-activities-and-expenditure-while-using-dc-fast-chargers
- **DOI:** https://doi.org/10.32866/001c.162484
- **Author and date:** Scott Hardman, PhD. Published 2026-06-08 according
  to the page metadata; the page shows June 09, 2026 AEST. The suggested
  citation is "Hardman, Scott. 2026."
- **Verified in the article text:** a California survey (June–July 2025),
  sent to 10,497 households, completed by 3,350. "The average duration of
  charging sessions was 32 minutes." The durations are self-reported, from
  recall of the last DCFC session (1,898 respondents).
- **Verified in the Supplemental Information, Table 3** (mean and SD of
  session time by reported activity, minutes):

  | Activity | n | Mean | SD |
  |---|---:|---:|---:|
  | Nowhere/stayed with car | 774 | 29.65 | 15.56 |
  | Restroom | 365 | 30.70 | 15.06 |
  | Café, restaurant or bar | 420 | 38.39 | 19.00 |
  | Other activities | — | 30.00 to 45.33 | 14.02 to 21.38 |

  - The text extraction offsets the mean and SD columns by one row. They
    were realigned using the single-respondent row ("Place of religion",
    n = 1, SD "."), and are consistent with the table title.
  - The brief's "29.7–38.4 min, SD about 14–19" matches the three
    most-reported activities. It is **not** in the article text, only in
    the supplement.
  - The CV of those three activities is 0.52, 0.49 and 0.49, which is the
    basis of the CV of 0.5.

## Blu Radio (2026)

- **Local copy:** `bluradio_enel_unicentro_2026.html` (544,766 bytes,
  HTTP 200).
- **URL:** https://www.bluradio.com/motor/conductores-en-boogta-podran-cargar-hasta-el-50-de-bateria-de-su-carro-electrico-en-menos-tiempo-so35
- **Author and date:** Coralina Durán, 13 May 2026.
- **Verified in the saved page** (Spanish, quoted):
  - "ocho mangueras de 30 kW y dos más de hasta 75 kW … podrá atender hasta
    10 vehículos de manera simultánea";
  - "recuperar cerca del 50 % de la batería en aproximadamente 25 a 30
    minutos … una carga completa podría tomar poco más de una hora";
  - "pagar únicamente por la cantidad de energía consumida durante el
    proceso" (users pay for the energy consumed).
- **Redaction (2026-10-07).** The saved page embedded Blu Radio's public
  Firebase web `apiKey` in its JavaScript. GitHub secret scanning flagged
  it, so it was replaced with a placeholder. This is a third party's
  client-side key, not a project credential. The article text quoted above
  is unchanged.
- **Two caveats:**
  - The article reports an announced upgrade ("ahora operará"). It is not a
    measured statistic.
  - The site's hardware is 8 × 30 kW + 2 × 75 kW, not 10 × 50 kW.

## Enel Colombia (2024)

- **Local copy: NOT SAVED.** The page answers curl and the WebFetch tool
  with an Imperva bot-check page ("Pardon Our Interruption"). The Internet
  Archive returned "Temporarily Offline" on 2026-10-06.
- **URL:** https://www.enel.com.co/es/historias/archive/2024/05/infraestructura-de-recarga-de-vehiculos-electricos.html
- **Not verified from a saved copy:** the value "about 1 h 30 min average to
  reach 100%" is taken from the brief as given. Its only use is as the
  plausibility ceiling in the Checkpoint A rule. The rule's outcome does not
  depend on it: the shortest simulated session is 225 min.

## References (APA 7)

- Blu Radio. (2026, May 13). *Conductores en Bogotá podrán cargar hasta el
  50 % de batería de su carro eléctrico en menos tiempo* (C. Durán, Author).
  https://www.bluradio.com/motor/conductores-en-boogta-podran-cargar-hasta-el-50-de-bateria-de-su-carro-electrico-en-menos-tiempo-so35
- Enel Colombia. (2024, May). *Avances en infraestructura de recarga de
  vehículos eléctricos.* https://www.enel.com.co/es/historias/archive/2024/05/infraestructura-de-recarga-de-vehiculos-electricos.html
- Hardman, S. (2026). Exploring electric vehicle driver activities and
  expenditure while using DC fast chargers. *Findings.*
  https://doi.org/10.32866/001c.162484
- U.S. Department of Energy, Vehicle Technologies Office. (2023, December 4).
  *FOTW #1319: EV charging at paid DC fast charging stations average 42
  minutes per session* [Fact of the Week]. https://www.energy.gov/cmei/vehicles/articles/fotw-1319-december-4-2023-ev-charging-paid-dc-fast-charging-stations-average
