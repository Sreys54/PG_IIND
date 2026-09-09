"""
Week 5, Part A, section 4.2: download Enel Colombia's 2026 monthly tariff
sheets (pliegos tarifarios), extract Nivel de Tension 2's regulated CU
(Costo Unitario de Prestacion del Servicio) six-component breakdown, and
validate it against two structural invariants before writing anything to
the annex CSV.

Why this exists as a script, not a one-off notebook cell: the brief's own
instruction is that these local PDF copies -- not the live Enel URLs, which
rotate content -- are the citable artifact for every CU number quoted in
this thesis. A script makes the download + extraction + validation
reproducible from source, the same discipline CLAUDE.md requires for every
experiment config in this project.

Nivel 2 (11.4 y 13.2 kV) is used throughout this project because
station_v0_bogota models a station with its own local transformer fed at
medium voltage (see Week 5 Gate 0 report, 2026-09-08). "SENCILLA Monomia"
under "INDUSTRIAL Y COMERCIAL CON CONTRIBUCION" is the with-contribution
commercial rate -- the row this project's ENERGY_PURCHASE_COST_COP_PER_KWH
constant (ev2gym_thesis/prices/colombia.py) is read from for the August
2026 base case.

Two invariants validated per month, per the brief's explicit instruction
(these are the checks that catch a mis-parsed row, not decorative
assertions):
  1. The six CU components (Generacion + Transmision + Distribucion +
     Comercializacion + Perdidas + Restricciones) sum to the sheet's own
     stated Nivel 2 CU (without contribution), within rounding tolerance.
  2. The with-contribution Nivel 2 CU equals 1.20x the without-contribution
     Nivel 2 CU (the regulatory contribucion de solidaridad for
     non-residential, non-exempt users) -- extracted independently from a
     DIFFERENT table on the same sheet (SECTOR NO RESIDENCIAL), not merely
     computed, so this is a genuine cross-check between two extractions,
     not a tautology.

If either invariant fails for a month, that month's row is not written and
the script exits non-zero -- per the brief, a failed invariant means the
parser grabbed the wrong row and the number must not be used anywhere.

One month (February 2026) has no extractable text layer for its CU table
(confirmed: pdfplumber finds 0 characters in that region of the page,
despite the page having other, unrelated extractable text lower down --
the table appears to be rendered as vector paths / outlined fonts rather
than as text). Handled via FEBRUARY_MANUAL_READING below: values were read
directly from a high-resolution crop of the rendered page (see
thesis_docs/sources/enel_tariffs/2026-febrero_cu_table_crop.png, saved by
this script for audit) and are still subject to both invariants above --
they are not exempted from validation just because they were transcribed
rather than regex-extracted.
"""
import csv
import datetime
import os
import re
import sys
import urllib.parse

import pdfplumber
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "thesis_docs", "sources", "enel_tariffs")
LISTING_URL = "https://www.enel.com.co/es/personas/tarifas-energia-enel-distribucion.html"
BASE_URL = "https://www.enel.com.co/content/dam/enel-co/español/personas/1-17-1/2026/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# doc:begin month_files
# Filenames confirmed by fetching LISTING_URL directly (2026-09-08) and
# reading the actual <a href> attributes -- NOT constructed from a naming
# pattern, since the convention changed mid-year (see the module docstring
# and the brief: enero/febrero use "tarifario-enel-<mes>-2026.pdf", marzo
# through junio use "pliego-tarifario-digital-<mes>-2026.pdf", julio and
# agosto each use a one-off name).
MONTH_FILES = {
    "enero": "tarifario-enel-enero-2026.pdf",
    "febrero": "tarifario-enel-febrero-2026.pdf",
    "marzo": "pliego-tarifario-digital-marzo-2026.pdf",
    "abril": "pliego-tarifario-digital-abril-2026.pdf",
    "mayo": "pliego-tarifario-digital-mayo-2026.pdf",
    "junio": "pliego-tarifario-digital-junio-2026.pdf",
    "julio": "Consulta el tarifario de energía Enel - Julio 2026.pdf",
    "agosto": "pliego tarifario digital _agosto_2026.pdf",
}
MONTH_ORDER = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto"]
# doc:end month_files

CONTRIBUTION_FACTOR = 1.20  # regulatory contribucion de solidaridad, non-residential non-exempt
SUM_TOLERANCE = 0.01
CONTRIBUTION_TOLERANCE = 0.001  # relative tolerance on the 1.20x check

# doc:begin february_manual_reading
# 2026-02 CU table has no extractable text layer (confirmed: page.chars
# covering that table region is empty, though the page's lower
# "TARIFAS Y COSTOS EFICIENTES..." section extracts fine -- i.e. this is
# not a wholesale extraction failure, just this one table). Values below
# were read directly off a 600dpi crop of the rendered page
# (2026-febrero_cu_table_crop.png, saved by render_february_crop() into
# OUT_DIR for audit) rather than regex-extracted. Cross-checked against
# both invariants below like every other month -- confirmed: components
# sum to 685.9857 (matches), and the independently-read with-contribution
# figure (823.1828, from the SECTOR NO RESIDENCIAL table on the same
# rendered crop) equals 685.9857 x 1.20 = 823.18284 (matches to rounding).
FEBRUARY_MANUAL_READING = {
    "generacion": 332.9887,
    "transmision": 50.6152,
    "distribucion": 185.2724,
    "comercializacion": 75.0193,
    "perdidas": 23.8141,
    "restricciones": 18.2760,
    "cu_sin_contribucion": 685.9857,
    "cu_con_contribucion": 823.1828,
    "extraction_method": "manual_visual_read_600dpi_crop",
}
# doc:end february_manual_reading

NUM = r"([\d.,]+)"


def _to_float(s: str) -> float:
    return float(s.replace(",", ""))


def check_listing_for_new_month():
    """Fetch the live listing page and warn if a 2026 PDF link exists that
    isn't one of the 8 already known -- e.g. September becoming available.
    Does not fail the run; this is a heads-up, not a validation gate."""
    try:
        resp = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"WARNING: could not fetch {LISTING_URL} to check for a new month: {exc}")
        return
    hrefs = set(re.findall(r'1-17-1/2026/([^"\']*\.pdf)', resp.text))
    decoded = {urllib.parse.unquote(h) for h in hrefs}
    known = set(MONTH_FILES.values())
    unknown = decoded - known
    if unknown:
        print("NOTICE: listing page has 2026 PDF link(s) not in MONTH_FILES -- "
              "a new month may be published:")
        for u in sorted(unknown):
            print(f"  {u}")
    else:
        print(f"Confirmed: no 2026 tariff sheet beyond {MONTH_ORDER[-1]} is published "
              f"yet (checked {LISTING_URL} on {datetime.date.today().isoformat()}).")


def download_month(month: str, filename: str) -> str:
    out_path = os.path.join(OUT_DIR, f"2026-{month}.pdf")
    if os.path.exists(out_path):
        print(f"  {month}: already downloaded, skipping fetch ({out_path})")
        return out_path
    url = BASE_URL + urllib.parse.quote(filename, safe="")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200 or resp.content[:4] != b"%PDF":
        raise RuntimeError(f"Download failed for {month}: status={resp.status_code}, url={url}")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(resp.content)
    print(f"  {month}: downloaded {len(resp.content)} bytes -> {out_path}")
    return out_path


def extract_month(pdf_path: str, month: str) -> dict:
    if month == "febrero":
        row = dict(FEBRUARY_MANUAL_READING)
        render_february_crop(pdf_path)
        return row

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += (page.extract_text() or "") + "\n"

    breakdown_pattern = (
        r"NIVEL\s*2\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM +
        r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM
    )
    m = re.search(breakdown_pattern, full_text)
    if m is None:
        raise RuntimeError(
            f"{month}: could not find the Nivel 2 CU breakdown row via regex. "
            f"This PDF may need a FEBRUARY_MANUAL_READING-style manual fallback."
        )
    gen, trans, dist, com, perd, restr, cu_sin = (_to_float(g) for g in m.groups())

    contrib_pattern = (
        r"INDUSTRIAL Y\s+SENCILLA\s+Monom[ií]a\s+" + NUM + r"\s+" + NUM +
        r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM + r"\s+" + NUM
    )
    m2 = re.search(contrib_pattern, full_text)
    if m2 is None:
        raise RuntimeError(
            f"{month}: could not find the with-contribution Nivel 2 row via regex."
        )
    cu_con = _to_float(m2.groups()[3])  # 4th captured number = Nivel 2 column

    return {
        "generacion": gen,
        "transmision": trans,
        "distribucion": dist,
        "comercializacion": com,
        "perdidas": perd,
        "restricciones": restr,
        "cu_sin_contribucion": cu_sin,
        "cu_con_contribucion": cu_con,
        "extraction_method": "regex_text_extraction",
    }


def render_february_crop(pdf_path: str):
    """Save a high-resolution crop of February's CU table region for audit,
    since its value came from a manual visual read, not regex extraction."""
    crop_path = os.path.join(OUT_DIR, "2026-febrero_cu_table_crop.png")
    if os.path.exists(crop_path):
        return
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        crop = page.crop((55, 255, 480, 325))
        im = crop.to_image(resolution=600)
        im.save(crop_path)
    print(f"  febrero: saved manual-read audit crop -> {crop_path}")


def validate_invariants(month: str, row: dict):
    component_sum = (
        row["generacion"] + row["transmision"] + row["distribucion"] +
        row["comercializacion"] + row["perdidas"] + row["restricciones"]
    )
    cu_sin = row["cu_sin_contribucion"]
    if abs(component_sum - cu_sin) > SUM_TOLERANCE:
        raise RuntimeError(
            f"{month}: FAILED invariant 1 (components sum to CU). "
            f"sum={component_sum:.4f}, stated CU={cu_sin:.4f}, "
            f"diff={abs(component_sum - cu_sin):.4f}"
        )

    cu_con = row["cu_con_contribucion"]
    expected_con = cu_sin * CONTRIBUTION_FACTOR
    rel_diff = abs(cu_con - expected_con) / cu_sin
    if rel_diff > CONTRIBUTION_TOLERANCE:
        raise RuntimeError(
            f"{month}: FAILED invariant 2 (with-contribution = 1.20x without). "
            f"with-contribution={cu_con:.4f}, 1.20x without={expected_con:.4f}, "
            f"relative diff={rel_diff:.5f}"
        )

    print(f"  {month}: both invariants OK "
          f"(sum={component_sum:.4f}~=CU={cu_sin:.4f}; "
          f"con-contribucion={cu_con:.4f}~=1.20x{cu_sin:.4f}={expected_con:.4f})")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Checking Enel's live listing page for a month beyond the known 8...")
    check_listing_for_new_month()

    rows = []
    today = datetime.date.today().isoformat()
    print("\nDownloading and extracting monthly tariff sheets...")
    for month in MONTH_ORDER:
        filename = MONTH_FILES[month]
        pdf_path = download_month(month, filename)
        row = extract_month(pdf_path, month)
        validate_invariants(month, row)
        row["month"] = month
        row["year"] = 2026
        row["source_pdf"] = os.path.relpath(pdf_path, REPO_ROOT).replace("\\", "/")
        row["retrieval_date"] = today
        rows.append(row)

    out_csv = os.path.join(OUT_DIR, "nivel2_cu_2026_monthly.csv")
    fieldnames = [
        "year", "month", "generacion", "transmision", "distribucion",
        "comercializacion", "perdidas", "restricciones",
        "cu_sin_contribucion", "cu_con_contribucion", "extraction_method",
        "source_pdf", "retrieval_date",
    ]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fieldnames})
    print(f"\nWrote {len(rows)} rows -> {out_csv}")

    return rows


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"\nFATAL: {exc}", file=sys.stderr)
        sys.exit(1)
