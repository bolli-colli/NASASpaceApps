"""Shared skeleton of the gateways that turn gridded NASA files into series.

Template method pattern: ``fetch`` does everything that is the same for every
service (check support, group variables by collection, resolve the period,
build the series). A subclass only says which catalog ``provider`` it serves
and how the files of one collection are read.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from datetime import date

import pandas as pd

from earth_trail_detective.application.ingest import build_series
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import AccessSpec, Period, Region, VariableSpec
from earth_trail_detective.domain.series import MonthlySeries

# Area means per (variable id, region id), indexed by the time of each file
RawValues = dict[tuple[str, str], pd.Series]


class GriddedGateway(ABC):
    """Base class implementing the ``LiveDataGateway`` port."""

    provider: str  # value of ``access.provider`` in the catalog

    def supports(self, variable: VariableSpec) -> bool:
        return variable.access is not None and variable.access.provider == self.provider

    def fetch(
        self, variables: Sequence[VariableSpec], regions: Sequence[Region], period: Period
    ) -> list[MonthlySeries]:
        """Fetch all variables for all regions; files of a collection are shared."""
        unsupported = [variable.id for variable in variables if not self.supports(variable)]
        if unsupported:
            raise LiveAccessError(f"No '{self.provider}' access for: {unsupported}")

        by_collection: dict[AccessSpec, list[VariableSpec]] = defaultdict(list)
        for variable in variables:
            by_collection[variable.access].append(variable)

        raw: RawValues = {}
        for access, members in by_collection.items():
            start = period.start or date.fromisoformat(f"{members[0].period_start}-01")
            end = period.end or date.today()
            raw.update(self._fetch_collection(access, members, regions, start, end))
        # Monthly aggregation and unit harmonisation happen in one shared place.
        return [
            build_series(variable, region, raw[(variable.id, region.id)])
            for variable in variables
            for region in regions
        ]

    @abstractmethod
    def _fetch_collection(
        self,
        access: AccessSpec,
        variables: Sequence[VariableSpec],
        regions: Sequence[Region],
        start: date,
        end: date,
    ) -> RawValues:
        """Return the area means of one collection for every variable and region."""


class AreaMeanCollector:
    """Gathers area means file by file and returns them as time-sorted series."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], dict[pd.Timestamp, float]] = defaultdict(dict)

    def add(self, variable: VariableSpec, region: Region, time: pd.Timestamp, value: float) -> None:
        self._values[(variable.id, region.id)][time] = value

    def series(self) -> RawValues:
        return {key: pd.Series(values).sort_index() for key, values in self._values.items()}
