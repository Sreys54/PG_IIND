# Sources added by the closure brief (2026-10-06)

Every external fact the closure brief introduces is listed here, with the
local copy, the original URL and the access date. Each entry also records
what the source supports and what it does not.

## Regulatory

### CREG Resolution 015 of 2018 (distribution remuneration methodology)

- Local copy: `regulatory/creg_015_2018.htm` (CREG Gestor Normativo compiled
  text, with the modification notes inline).
- URL: https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_creg_0015_2018.htm
- Accessed: 2026-10-06.
- Used for: the power factor that converts kW to kVA (closure brief A.4).
  Chapter 12 (cost of reactive energy transport), condition (b): an end user
  pays for reactive energy transport when the inductive reactive energy
  (kVArh) recorded at its commercial boundary exceeds **fifty percent (50 %)
  of the active energy (kWh)** delivered in each hourly period.
- Derived value: the lowest power factor an end user can hold without
  paying the reactive charge is pf = cos(arctan 0.5) = **0.894**. That
  number is a calculation from the 50 % threshold. The resolution does not
  state it as a power factor.
- Verification caveat (declared, not resolved): the compiled text prints
  conditions (a) to (c) immediately after a "Notas de Vigencia / Legislación
  Anterior" marker, which follows the amended definition of the variable M.
  From the HTML alone, it cannot be settled whether the 50 % condition is
  current text or the superseded wording. For that reason every kVA figure
  in the closure documents is given both at pf 0.894 and at unity power
  factor (kVA = kW, the lower bound). The recommended rating is the same
  under both (see below).

## Standards

### Enel Colombia (CODENSA) technical specification ET-013

- Title: "Transformador trifásico de distribución tipo seco abierto".
- Local copy: `standards/enel_ET-013.pdf`.
- URL: https://www.enel.com.co/content/dam/enel-co/español/2-1-6-normas-tecnicas/especificaciones-tecnicas-para-materiales-y-equipos-de-media-tension/ET-013.pdf
- Accessed: 2026-10-06.
- Used for: the list of standard three-phase distribution transformer
  ratings bought by Bogotá's network operator. Table 1 ("Rangos de capacidad
  nominal") lists 15, 30, 45, 75, 112.5, 150, 225, 300, 400, 500, 630, 800
  and 1000 kVA.
- Scope limit: this is the operator's purchasing specification for dry-type
  transformers, not the national standard. The national standard (NTC 819,
  ICONTEC) is paywalled and was not consulted. "Standard rating" in the
  closure documents means "a rating in ET-013 Table 1".

### Enel Colombia ET-009 and ET-012 (context only)

- `standards/enel_ET-009.pdf`: submersible three-phase transformer, 500 kVA
  only.
- `standards/enel_ET-012.pdf`: pad-mounted transformer for public lighting,
  30, 45 and 75 kVA.
- Same URL directory as ET-013, accessed 2026-10-06. Neither is used for a
  rating mapping. They were saved because they were consulted, and they show
  that the operator's ratings are the same discrete steps as ET-013.

## Mapping applied (closure brief A.4)

| Quantity (from the registry) | kW | kVA at pf 0.894 | kVA at pf 1.0 | ET-013 rating, rounded up |
|---|---:|---:|---:|---:|
| Current transformer limit (EV2Gym `transformer.max_power`) | 100.0 | 111.9 | 100.0 | 112.5 kVA (the limit fits, with 0.6 kVA to spare at pf 0.894) |
| AFAP 95th-percentile peak, base (Week 7 Step 2) | 172.7 | 193.2 | 172.7 | 225 kVA |
| AFAP 95th-percentile peak, spawn 1.3x | 191.9 | 214.6 | 191.9 | 225 kVA |
| AFAP 95th-percentile peak, spawn 1.6x | 189.1 | 211.5 | 189.1 | 225 kVA |
| C2 transformer variant 1 (112.5 kVA x 0.894) | 100.6 | 112.5 | — | 112.5 kVA |
| C2 transformer variant 2 (150 kVA x 0.894) | 134.2 | 150.0 | — | 150 kVA |

EV2Gym models the transformer limit in kW (active power) only. It has no
reactive-power or kVA model. The kVA columns are therefore a
post-processing conversion, not a simulated quantity.
