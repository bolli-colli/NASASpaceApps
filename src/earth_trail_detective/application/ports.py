"""Ports: the interfaces the application layer expects from the outside world.

The infrastructure layer provides the implementations (dependency inversion):
use cases depend on these protocols only, never on YAML, Parquet or NASA APIs.
"""

from collections.abc import Sequence
from typing import Protocol

from earth_trail_detective.domain.enums import Step
from earth_trail_detective.domain.models import (
    DemoCase,
    Period,
    Region,
    StepInfo,
    Substance,
    TrailGap,
    VariableSpec,
)
from earth_trail_detective.domain.series import MonthlySeries


class Catalog(Protocol):
    """Read-only access to the curated catalog."""

    def substances(self) -> tuple[Substance, ...]: ...

    def substance(self, substance_id: str) -> Substance: ...

    def variables(self) -> tuple[VariableSpec, ...]: ...

    def variable(self, variable_id: str) -> VariableSpec: ...

    def variables_for(self, substance_id: str, step: Step) -> tuple[VariableSpec, ...]: ...

    def regions(self) -> tuple[Region, ...]: ...

    def region(self, region_id: str) -> Region: ...

    def steps(self) -> tuple[StepInfo, ...]: ...

    def gap(self, substance_id: str, step: Step) -> TrailGap | None: ...

    def demos(self) -> tuple[DemoCase, ...]: ...


class SeriesSource(Protocol):
    """Anything that can deliver the monthly series of a variable in a region."""

    def load(self, variable: VariableSpec, region: Region) -> MonthlySeries | None:
        """Return the series, or ``None`` if this source does not have it."""
        ...

    def explain_missing(self, variable: VariableSpec) -> str:
        """Tell the user why ``load`` returned ``None`` for this variable."""
        ...


class SeriesStore(SeriesSource, Protocol):
    """A source that can also persist series (the offline cache)."""

    def save(self, variable: VariableSpec, region: Region, series: MonthlySeries) -> None: ...


class LiveDataGateway(Protocol):
    """Retrieval of gridded NASA data, reduced to monthly area means."""

    def supports(self, variable: VariableSpec) -> bool:
        """True if the gateway can retrieve this variable."""
        ...

    def fetch(
        self, variables: Sequence[VariableSpec], regions: Sequence[Region], period: Period
    ) -> list[MonthlySeries]:
        """Return one series per (variable, region), variables in the outer loop."""
        ...
