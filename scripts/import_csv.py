"""Import a hand-exported time-series CSV into the offline data cache.

Works for Giovanni "Time Series, Area-Averaged" downloads and for plain
tables with a date and a value column (e.g. AppEEARS area statistics).

    python scripts/import_csv.py --variable so2_column_omi --region ohio_valley giovanni.csv
    python scripts/import_csv.py --variable snow_albedo_modis --region alps stats.csv \
        --date-column Date --value-column Mean

Daily values are averaged to months. The values are assumed to be in the
catalog's ``source_unit``; use ``--unit`` if the export uses the app unit already.
"""

import argparse
from pathlib import Path

from earth_trail_detective.application.ingest import build_series
from earth_trail_detective.bootstrap import build_container
from earth_trail_detective.infrastructure.csv_import import read_time_series_csv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--variable", required=True, help="variable id from catalog/variables.yaml")
    parser.add_argument("--region", required=True, help="region id from catalog/regions.yaml")
    parser.add_argument("--date-column", help="name of the date column (default: time or date)")
    parser.add_argument("--value-column", help="name of the value column (default: second column)")
    parser.add_argument("--fill-value", type=float, help="number that marks missing values")
    parser.add_argument("--unit", help="unit of the CSV values (default: catalog source_unit)")
    parser.add_argument(
        "--source-url", help="URL that reproduces the export (stored with the data)"
    )
    arguments = parser.parse_args()

    container = build_container()
    variable = container.catalog.variable(arguments.variable)
    region = container.catalog.region(arguments.region)

    raw = read_time_series_csv(
        arguments.csv_file, arguments.date_column, arguments.value_column, arguments.fill_value
    )
    series = build_series(variable, region, raw, arguments.unit, arguments.source_url)
    container.repository.save(variable, region, series)

    values = series.values
    print(
        f"Saved {variable.id} / {region.id}: {values.index[0]:%Y-%m} to {values.index[-1]:%Y-%m}, "
        f"{values.count()} months with data, {values.isna().mean():.0%} missing, "
        f"range {values.min():.4g} to {values.max():.4g} {variable.unit}"
    )
    print("Check: unit, period, share of missing values and plausible range (spec 13.2).")


if __name__ == "__main__":
    main()
