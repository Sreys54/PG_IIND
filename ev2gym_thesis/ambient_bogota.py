"""
Bogota diurnal ambient temperature profiles, for the Week 2 battery
degradation calibration (see thesis_docs/chapters/00_lab_log.md for the
full derivation and CLAUDE.md's Gate 2 finding that theta is hard-coded to
298.15K in ev2gym/models/ev.py, not an input).

Data source and a correction to the original plan:
IDEAM, "Normales climatologicas estandar 1981-2010" (downloaded directly
from https://www.ideam.gov.co/sala-de-prensa/informes/Normales-clim%C3%A1ticas-est%C3%A1ndar,
file normales_climatologicas_periodo_1981-2010.xlsx), station 21205791
"Aeropuerto El Dorado Catam - AUT", Bogota, Cundinamarca, elevation 2547 m:
  - Annual mean temperature (sheet TEMPERATURA MEDIA, column ANUAL): 13.68 C
    -- NOT 13.3 C as originally assumed. The 13.3 C figure does not match
    this primary IDEAM source and has been replaced everywhere.
  - Annual mean of daily maximum (sheet TEMPERATURA MAXIMA): 19.31 C
  - Annual mean of daily minimum (sheet TEMPERATURA MINIMA): 7.88 C
  - Monthly mean temperature ranges only ENE=13.29 C to MAY=14.16 C across
    the year (spread ~0.87 C) -- confirms the "negligible seasonal
    variation" premise.

What is NOT verified against this source: the specific clock hours at
which the daily minimum (~06:00) and maximum (~14:00-15:00) occur. IDEAM's
normals file reports monthly/annual daily min-mean and max-mean values
only, not an hourly diurnal curve. The 06:00 / 14:30 anchor hours below are
a general assumption about tropical-highland diurnal timing (sunrise-driven
minimum, mid-afternoon peak after several hours of solar heating), not an
IDEAM-sourced figure -- flagged pending verification against an hourly
IDEAM dataset if one becomes available.
"""
import math

# doc:begin outdoor_anchors
# Verified against IDEAM (see module docstring): annual mean-of-daily-min
# and mean-of-daily-max for station 21205791. Hour-of-day anchors (06:00
# trough, 14:30 peak) are an assumption, not IDEAM-sourced -- see docstring.
OUTDOOR_MIN_C = 7.88
OUTDOOR_MAX_C = 19.31
OUTDOOR_TROUGH_HOUR = 6.0
OUTDOOR_PEAK_HOUR = 14.5
# doc:end outdoor_anchors

# doc:begin underground_anchors
# NOT IDEAM-sourced: no published normals exist for covered/basement sites.
# Modeled as a damped version of the outdoor cycle, centered on the same
# verified IDEAM annual mean (13.68 C), with an assumed +/-0.75 C swing
# (Deliverable 6.3's "13-14 C, much smaller swing" description). This is a
# declared modeling assumption, not a measured or cited figure.
UNDERGROUND_MEAN_C = 13.68
UNDERGROUND_MIN_C = UNDERGROUND_MEAN_C - 0.75
UNDERGROUND_MAX_C = UNDERGROUND_MEAN_C + 0.75
UNDERGROUND_TROUGH_HOUR = OUTDOOR_TROUGH_HOUR
UNDERGROUND_PEAK_HOUR = OUTDOOR_PEAK_HOUR
# doc:end underground_anchors


def _piecewise_linear_diurnal(hour_of_day, trough_hour, peak_hour, t_min, t_max):
    """Single-trough, single-peak diurnal cycle, linearly interpolated
    between the two anchor points (asymmetric: faster morning rise,
    slower overnight fall, consistent with a solar-driven cycle). This is
    an explicit simplification, not a validated thermal/solar model --
    see module docstring.
    """
    h = hour_of_day % 24.0
    if trough_hour <= h <= peak_hour:
        frac = (h - trough_hour) / (peak_hour - trough_hour)
        return t_min + frac * (t_max - t_min)
    else:
        # wrap through midnight from peak back down to the next trough
        if h > peak_hour:
            h_from_peak = h - peak_hour
        else:
            h_from_peak = (24.0 - peak_hour) + h
        span = 24.0 - (peak_hour - trough_hour)
        frac = h_from_peak / span
        return t_max - frac * (t_max - t_min)


def outdoor_ambient_c(hour_of_day: float) -> float:
    """Surface/outdoor site diurnal ambient temperature in Celsius (e.g. Salitre,
    Plaza de las Americas -- surface Enel X sites)."""
    return _piecewise_linear_diurnal(
        hour_of_day, OUTDOOR_TROUGH_HOUR, OUTDOOR_PEAK_HOUR, OUTDOOR_MIN_C, OUTDOOR_MAX_C
    )


def underground_ambient_c(hour_of_day: float) -> float:
    """Covered/basement site diurnal ambient temperature in Celsius (e.g. Tercer
    Milenio subterraneo, Hotel Tequendama sotano -- covered Enel X sites)."""
    return _piecewise_linear_diurnal(
        hour_of_day, UNDERGROUND_TROUGH_HOUR, UNDERGROUND_PEAK_HOUR,
        UNDERGROUND_MIN_C, UNDERGROUND_MAX_C
    )


AMBIENT_PROFILES = {
    "bogota_outdoor": outdoor_ambient_c,
    "bogota_underground": underground_ambient_c,
    "default": lambda hour_of_day: 298.15 - 273.15,  # ev.py's fixed 25 C constant, for comparison
}
