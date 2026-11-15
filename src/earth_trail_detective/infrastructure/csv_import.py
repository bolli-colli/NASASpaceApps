"""Reader for time-series CSV files exported by hand.

Two layouts are understood:

* **Giovanni** "Time Series, Area-Averaged" downloads: some ``Key:,Value``
  metadata lines, then a table whose first column is ``time``.
* **Plain tables** with a date column and a value column (for example the
  statistics file of an AppEEARS area request).

The header row is found by looking for the date column name, so any number of
metadata lines in front of the table is fine.
"""

import io
from pathlib import Path

import numpy as np
import pandas as pd

from earth_trail_detective.domain.errors import SeriesFormatError

DEFAULT_DATE_COLUMNS = ("time", "date")
_FILL_VALUE_KEY = "fill value"


def _first_cell(line: str) -> str:
    """Return the first CSV cell of a line, lower-cased and without quotes."""
    return line.split(",", 1)[0].strip().strip('"').lower()


def _split_header(lines: list[str], date_columns: tuple[str, ...]) -> tuple[dict[str, str], int]:
    """Collect the metadata lines and return them with the header row index."""
    metadata: dict[str, str] = {}
    for number, line in enumerate(lines):
        if _first_cell(line) in date_columns:
            return metadata, number
        key, _, value = line.partition(",")
        if key.strip():
            metadata[key.strip().rstrip(":").lower()] = value.strip()
    raise SeriesFormatError(f"No header row starting with one of {date_columns} was found.")


def read_time_series_csv(
    path: Path,
    date_column: str | None = None,
    value_column: str | None = None,
    fill_value: float | None = None,
) -> pd.Series:
    """Read a CSV export and return its values indexed by date.

    ``date_column`` defaults to ``time`` or ``date``; ``value_column`` defaults
    to the first column after the date. Fill values (from the Giovanni header
    or ``fill_value``) become missing values.
    """
    date_columns = (date_column.lower(),) if date_column else DEFAULT_DATE_COLUMNS
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    metadata, header_row = _split_header(lines, date_columns)

    table = pd.read_csv(io.StringIO("\n".join(lines[header_row:])))
    table.columns = [str(column).strip() for column in table.columns]
    # Long Giovanni series mix "2004-10-06 00:00:00" and "2020-01-01T00:00:00" in one
    # column, so the format must be inferred row by row.
    dates = pd.to_datetime(table.iloc[:, 0], format="mixed")
    if value_column is None:
        value_column = table.columns[1]
    if value_column not in table.columns:
        raise SeriesFormatError(
            f"Column '{value_column}' not found; available: {list(table.columns)}"
        )
    values = pd.Series(
        pd.to_numeric(table[value_column], errors="coerce").to_numpy(),
        index=pd.DatetimeIndex(dates).tz_localize(None),
    )

    # Fill values: explicit argument plus any "Fill Value ..." header line.
    fills = [fill_value] if fill_value is not None else []
    for key, text in metadata.items():
        if key.startswith(_FILL_VALUE_KEY):
            try:
                fills.append(float(text))
            except ValueError:
                continue  # not a number: nothing to mask
    return values.replace(fills, np.nan) if fills else values
