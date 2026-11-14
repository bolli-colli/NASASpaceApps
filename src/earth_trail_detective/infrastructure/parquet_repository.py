"""Offline cache: one Parquet file per variable and region (spec 10.5).

File name: ``<variable id>__<region id>.parquet`` inside the data directory.
The content follows the common data format (spec 10.4).
"""

from pathlib import Path

import pandas as pd

from earth_trail_detective.domain.models import Region, VariableSpec
from earth_trail_detective.domain.series import MonthlySeries

_SEPARATOR = "__"
_SUFFIX = ".parquet"


class ParquetSeriesRepository:
    """Implements the ``SeriesStore`` port on the local file system."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, variable: VariableSpec, region: Region) -> Path:
        return self._directory / f"{variable.id}{_SEPARATOR}{region.id}{_SUFFIX}"

    def load(self, variable: VariableSpec, region: Region) -> MonthlySeries | None:
        path = self._path(variable, region)
        if not path.exists():
            return None
        return MonthlySeries.from_frame(pd.read_parquet(path))

    def save(self, variable: VariableSpec, region: Region, series: MonthlySeries) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        series.to_frame().to_parquet(self._path(variable, region), index=False)

    def explain_missing(self, variable: VariableSpec) -> str:
        return "Not in the offline cache for this region (see README, 'Filling the data cache')."
