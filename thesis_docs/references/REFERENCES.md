# References

Tracks every source this thesis cites: full citation, DOI, which
objective/chapter it supports, and acquisition status. For regulatory
documents, the retrieval date and source URL are recorded too, since a
normative page can change and a thesis citing regulation needs the
consulted version pinned. Updated as sources are acquired -- entries are
corrected in place with a dated note when status changes, not silently
rewritten (same discipline as `thesis_docs/chapters/00_lab_log.md`).

## In repo, acquired 2026-08-19

### EV2Gym paper [Primary -- simulator models, baselines, metrics]

Orfanoudakis, S., Diaz-Londono, C., Yılmaz, Y. E., Palensky, P., & Vergara,
P. P. (2024). *EV2Gym: A Flexible V2G Simulator for EV Smart Charging
Research and Benchmarking*. arXiv:2404.01849. Published in IEEE
Transactions on Intelligent Transportation Systems.

- **File:** `thesis_docs/references/ev2gym_paper.pdf`
- **Version read:** arXiv:2404.01849v1 (the only version posted as of
  retrieval; the PDF's own header confirms `arXiv:2404.01849v1 [cs.SE] 2
  Apr 2024`). If a table/equation number in this thesis differs from the
  published IEEE T-ITS version, that will be stated explicitly at the
  point of citation, not silently assumed identical.
- **Supports:** Objectives 1-3 (baseline characterization, model
  validation, RL baseline) -- the simulator itself, its PST/V2G-ProfitMax
  mathematical formulations (Eq. 8-24), its evaluation metrics (Table V),
  and its baseline algorithm descriptions.
- **Confirmed by reading the actual PDF, not recalled:** Table V's `ϵ^usr`
  (user satisfaction) formula is `(1/|E|) · Σ_{k∈E} SoC_k/SoC*_k`; Eq. 24
  states the profit-maximization problem's departure constraint as
  `E_{j,i,t} >= E*_{j,i,t}` -- a direct same-unit (kWh) comparison, with no
  multiplication by any other energy term. This is relevant to Week 4's
  `ev2gym_thesis/oracle/balanced_model.py`: the installed
  `ev2gym/baselines/gurobi_models/profit_max.py`'s own `user_satisfaction`
  term multiplies `ev_des_energy` by `ev_max_energy` before comparing to
  `energy`, which does not match this formal definition either (a second,
  independent piece of evidence -- beyond the units-dimensional argument
  already recorded in `04_oracle_and_pitd3.md` -- that the installed
  Gurobi class's satisfaction term is not a faithful implementation of the
  paper's own formulation).

### PI-TD3 paper [Primary -- §4.1's physics-informed design basis]

*Physics-Informed Reinforcement Learning for Large-Scale EV Smart Charging
Considering Distribution Network Voltage Constraints*. arXiv:2510.12335v2.

- **File:** `thesis_docs/references/pi_td3_paper.pdf`
- **Supports:** Week 4 Part B (PI-TD3) -- Algorithm 1 and Eq. 14 are read
  and cited by number before any adaptation is written into
  `ev2gym_thesis/rl/reward_pi.py`, per the task brief's explicit
  requirement and `CLAUDE.md` rule 3 (never reconstruct a paper's
  equations from memory).
- **Status note:** fetched 2026-08-19; not yet read in full at the time of
  this REFERENCES.md entry -- Entregable 5 work reads it before writing
  any PI-TD3 code, not before.

## In repo, regulatory -- retrieved 2026-08-19, Weeks 6-7 material (placed, not read into Week 4)

| Document | File | Source URL | Format |
|---|---|---|---|
| Ley 1964 de 2019 | `regulatory/ley_1964_2019.pdf` | https://www.minambiente.gov.co/wp-content/uploads/2021/06/ley-1964-2019.pdf | PDF (confirmed genuine, `%PDF-1.6` header) |
| Res. 40117 de 2024 (RETIE) | `regulatory/res_40117_2024_retie.pdf` | https://www.minenergia.gov.co/documents/11563/Resoluci%C3%B3n_40117_de_2024.pdf | PDF (confirmed genuine, `%PDF-1.7` header) |
| RETIE Libro 3 -- Instalaciones | `regulatory/retie_libro3_instalaciones.pdf` | https://www.minenergia.gov.co/documents/11566/4._Libro_3_-_Instalaciones.pdf | PDF (confirmed genuine, `%PDF-1.7` header) |
| Res. 40223 de 2021 (CREG) | `regulatory/res_40223_2021.html` | https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_minminas_40223_2021.htm | **HTML, not PDF -- see limitation below** |
| Res. 40123 de 2024 (CREG) | `regulatory/res_40123_2024.html` | https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_minminas_40123_2024.htm | **HTML, not PDF -- see limitation below** |

**Declared limitation, not silently worked around:** the two CREG
resolutions are published as HTML by CREG's gestor normativo, with no PDF
alternative found. No HTML-to-PDF rendering tool was available in this
environment (`wkhtmltopdf`, `pandoc`, `weasyprint`, `pdfkit` all absent,
confirmed by attempting each). Rather than fabricate a PDF or silently
substitute a different source, the raw HTML was saved as-is
(`res_40223_2021.html` / `res_40123_2024.html`, both confirmed to contain
real resolution text, not an error page, at retrieval time). If a true PDF
copy is needed later, either install a renderer or use the browser's own
"print to PDF" on the two URLs above and replace these files, updating this
row's Format column and retrieval date.

All five: **retrieved 2026-08-19**, all confirmed to contain real document
content (checked file headers/text, not just a successful HTTP status) --
per the standing project rule that `curl` will save an HTML error page as
a `.pdf` without complaining. **Placed for Weeks 6-7 (Objective 4,
infrastructure guidelines) -- not read into any Week 4 deliverable.**

## Pending from advisor -- Weeks 6-7, not a Week 4 dependency

### Zandrazavi et al. (2022) [Primary once acquired -- methodological precedent]

Zandrazavi, S. F., Guzman, C. P., **Tabares Pozos, A.** (thesis advisor),
Quiros-Tortos, J., & Franco, J. F. (2022). *Stochastic multi-objective
optimal energy management of grid-connected unbalanced microgrids with
renewable energy generation and plug-in electric vehicles.* Energy, 241,
122884. https://doi.org/10.1016/j.energy.2021.122884

- **Status:** pending from advisor -- she is the third author, so the copy
  comes directly from her, not a proxy or interlibrary loan.
- **Supports:** Objective 4 (infrastructure guidelines) and the Week 6
  IEEE 34-bus phase specifically -- its unbalanced-network treatment is
  directly relevant to that feeder, which is itself unbalanced. Read
  before Week 6 starts, not just before writing about it.
- **Required, not optional, once acquired:** a positioning paragraph in
  the literature review stating what this paper solves, what this thesis
  does differently, and why the difference is justified -- because the
  advisor's own prior work invites exactly that comparison from a jury.
  Draft only after reading the paper in full, not from the abstract.

### Mahmoud (2017), Ch. 1 [Background -- control hierarchy theory]

Mahmoud, M. S. (2017). *Microgrid Control Problems and Related Issues*
(Ch. 1). In *Microgrid: Advanced Control Methods and Renewable Energy
System Integration*. Butterworth-Heinemann.
https://doi.org/10.1016/B978-0-08-101753-1.00001-2

- **Status:** pending institutional access (paywalled) -- route is
  Uniandes library access or document delivery.
- **Supports:** the primary/secondary/tertiary control hierarchy
  background in the Objective 4 chapter. Not a Week 4 dependency.
- **Explicit exclusion, stated so it isn't quietly forgotten:** `gym4ReaL`
  documentation is NOT a substitute for this chapter -- it documents a
  different RL benchmark suite (software), not peer-reviewed, and not
  about control-hierarchy theory. It must not be cited as support for any
  claim that needs Mahmoud. If a claim needs this chapter, the claim stays
  unwritten until the chapter is in hand.
