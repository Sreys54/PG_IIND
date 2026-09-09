"""
Shared human-readable Excel export utility (Week 5). Every
scripts/export_*_xlsx.py script uses this instead of duplicating the
same openpyxl formatting logic -- one place to fix if the formatting
convention ever needs to change.

The source CSV is always left untouched -- this produces a SEPARATE
.xlsx for reading by eye (thousand-separated numbers, unit-labeled
headers), never a file any script reads back in.

Three format families used across every export, per the project's
convention going forward:
  - COP amounts and kWh amounts: thousand separator, 2 decimals
    (e.g. 349,343.97).
  - Flat-rate COP/kWh constants: thousand separator, 4 decimals -- these
    are exact verified reference values (1,450.0000 / 865.7615), not
    simulation output, and rounding to 2 would silently drop verified
    digits.
  - Percentages: this project's own registry mixes two conventions
    (average_user_satisfaction is a 0-1 fraction; min_energy_user_satisfaction
    is already on a 0-100 scale) -- PCT_FRACTION_FORMAT applies Excel's
    native "x100 and add %" percentage format to a 0-1 fraction;
    PCT_ALREADY_SCALED_FORMAT appends a literal "%" to a value that is
    already on a 0-100 (or similar) scale, WITHOUT multiplying it again.
    Every column mapping below states which one applies and why, so this
    ambiguity is resolved once per column, not guessed at when reading.
"""
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

COP_FORMAT = "#,##0.00"
KWH_FORMAT = "#,##0.00"
COP_PER_KWH_FORMAT = "#,##0.0000"
COUNT_FORMAT = "#,##0"
PCT_FRACTION_FORMAT = "0.00%"          # underlying value is 0-1; Excel multiplies by 100 for display
PCT_ALREADY_SCALED_FORMAT = '#,##0.00"%"'  # underlying value is already on a 0-100 (or similar) scale
SECONDS_FORMAT = "#,##0.000"
DIMENSIONLESS_4DP_FORMAT = "#,##0.000000"  # for very small values (e.g. battery_degradation)


def export_formatted_xlsx(csv_path: str, xlsx_path: str, column_labels: dict,
                           number_formats: dict, sheet_name: str = "data",
                           comment_prefix: str = "#"):
    """column_labels: {original_csv_column: detailed label with unit}.
    Every original column not present in column_labels is kept as-is,
    which is itself a signal that a label was missed -- callers should
    map every column, not leave gaps.

    number_formats: {DISPLAY label (post-rename) -> openpyxl number_format
    string}. Columns absent from this dict get Excel's "General" format
    (used for text/categorical/boolean columns, where no numeric format
    applies).
    """
    with open(csv_path, encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith(comment_prefix)]
    from io import StringIO
    df = pd.read_csv(StringIO("".join(lines)))
    df = df.rename(columns=column_labels)

    missing = set(df.columns) - set(column_labels.values())
    if missing:
        raise ValueError(
            f"{csv_path}: columns with no detailed label mapped: {missing} -- "
            f"every column must get an explicit, unit-bearing label."
        )

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]

        for cell in ws[1]:
            cell.font = Font(bold=True)
        ws.freeze_panes = "A2"

        for col_idx, col_name in enumerate(df.columns, start=1):
            letter = get_column_letter(col_idx)
            fmt = number_formats.get(col_name)
            if fmt:
                for row in range(2, len(df) + 2):
                    ws[f"{letter}{row}"].number_format = fmt
            ws.column_dimensions[letter].width = min(max(len(col_name), 14) + 2, 46)

    print(f"Wrote {xlsx_path} ({len(df)} rows, {len(df.columns)} columns, every header unit-labeled).")
    return xlsx_path
