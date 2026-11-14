"""Create ARTIFICIAL data so the app can be developed without NASA data.

The numbers are random (seasonal cycle + noise + a random trend). They say
nothing about the real world. Every series is stored with the product name
"SYNTHETIC", and the app shows a warning banner whenever such data is used.

    python scripts/make_synthetic_cache.py
    ETD_DATA_DIR=data/synthetic streamlit run app.py
    # PowerShell: $env:ETD_DATA_DIR="data/synthetic"; streamlit run app.py

The files go to ``data/synthetic/`` (ignored by git) – never into ``data/``.
"""

import zlib
from dataclasses import replace

import numpy as np
import pandas as pd

from earth_trail_detective.bootstrap import build_container
from earth_trail_detective.config import PROJECT_ROOT
from earth_trail_detective.domain.models import Region, VariableSpec
from earth_trail_detective.domain.series import SYNTHETIC_PRODUCT, MonthlySeries, SeriesMeta
from earth_trail_detective.infrastructure.parquet_repository import ParquetSeriesRepository

SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
LAST_MONTH = "2025-12"
BASE_LEVEL = 10.0
MAX_TREND_PER_YEAR = 0.15
SEASONAL_AMPLITUDE = 2.0
NOISE = 1.0


def synthetic_series(variable: VariableSpec, region: Region) -> MonthlySeries:
    """Random but reproducible series for one variable and region."""
    # The seed depends only on the ids, so every run produces the same files.
    seed = zlib.crc32(f"{variable.id}/{region.id}".encode())
    random = np.random.default_rng(seed)
    months = pd.date_range(variable.period_start, variable.period_end or LAST_MONTH, freq="MS")
    years = np.arange(len(months)) / 12
    values = (
        BASE_LEVEL
        + random.uniform(-MAX_TREND_PER_YEAR, MAX_TREND_PER_YEAR) * years
        + SEASONAL_AMPLITUDE * np.sin(2 * np.pi * years)
        + random.normal(0, NOISE, len(months))
    )
    meta = replace(SeriesMeta.describe(variable, region), product=SYNTHETIC_PRODUCT)
    return MonthlySeries(pd.Series(values, index=months), meta)


def main() -> None:
    container = build_container()
    repository = ParquetSeriesRepository(SYNTHETIC_DIR)
    count = 0
    for variable in container.catalog.variables():
        if variable.derivation is not None:
            continue  # derived variables are computed from their inputs
        for region in container.catalog.regions():
            repository.save(variable, region, synthetic_series(variable, region))
            count += 1
    print(f"Wrote {count} ARTIFICIAL series to {SYNTHETIC_DIR}")


if __name__ == "__main__":
    main()
