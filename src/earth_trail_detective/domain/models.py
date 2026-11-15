"""Immutable entities and value objects described by the catalog.

Everything here is plain data: no file access, no statistics, no UI.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd

from earth_trail_detective.domain.enums import DataKind, GapStatus, Step


def _degrees(value: float, positive: str, negative: str) -> str:
    """Format a coordinate such as ``-88`` as ``88°W``."""
    return f"{abs(value):g}°{positive if value >= 0 else negative}"


@dataclass(frozen=True)
class BoundingBox:
    """A latitude/longitude box in degrees (west/east negative = western hemisphere)."""

    south: float
    north: float
    west: float
    east: float

    def __post_init__(self) -> None:
        # Boxes crossing the antimeridian are not supported, hence west < east.
        if not -90 <= self.south < self.north <= 90:
            raise ValueError(f"Invalid latitudes: south={self.south}, north={self.north}")
        if not -180 <= self.west < self.east <= 180:
            raise ValueError(f"Invalid longitudes: west={self.west}, east={self.east}")

    @property
    def label(self) -> str:
        """Human readable extent, e.g. ``37°N–42°N, 88°W–80°W``."""
        return (
            f"{_degrees(self.south, 'N', 'S')}–{_degrees(self.north, 'N', 'S')}, "
            f"{_degrees(self.west, 'E', 'W')}–{_degrees(self.east, 'E', 'W')}"
        )


@dataclass(frozen=True)
class Period:
    """A closed time span; ``None`` on either side means "as far as the data goes"."""

    start: date | None = None
    end: date | None = None

    def crop(self, values: pd.Series) -> pd.Series:
        """Return the part of a date-indexed series that lies inside the period."""
        start = pd.Timestamp(self.start) if self.start else None
        end = pd.Timestamp(self.end) if self.end else None
        return values.loc[start:end]

    @property
    def label(self) -> str:
        """Text for reports, e.g. ``2004-10 to end of record``."""
        start = f"{self.start:%Y-%m}" if self.start else "start of record"
        end = f"{self.end:%Y-%m}" if self.end else "end of record"
        return f"{start} to {end}"


@dataclass(frozen=True)
class Region:
    """A named bounding box the user can analyse."""

    id: str
    name: str
    category: str
    bbox: BoundingBox


@dataclass(frozen=True)
class Substance:
    """Something that can be followed along the trail (sulfur, soot, ...)."""

    id: str
    name: str
    icon: str
    description: str
    student_visible: bool = True


@dataclass(frozen=True)
class StepInfo:
    """Display texts of a trail step (editable in ``catalog/trail.yaml``)."""

    step: Step
    label: str
    icon: str
    description: str


@dataclass(frozen=True)
class AccessSpec:
    """How the raw data of a variable can be obtained."""

    provider: str  # "giovanni", "harmony", "earthaccess" (scripted / live), "csv" (manual)
    short_name: str | None = None  # NASA CMR collection short name
    version: str | None = None  # NASA CMR collection version
    group: str | None = None  # HDF5/netCDF group that holds the grid, if any
    hint: str | None = None  # where to export a CSV by hand
    giovanni_id: str | None = None  # Giovanni variable id, e.g. "OMSO2e_003_ColumnAmountSO2"


@dataclass(frozen=True)
class Derivation:
    """Recipe for a variable that is computed from other catalog variables."""

    operation: str  # "sum" or "ratio" (first input divided by second)
    inputs: tuple[str, ...]


@dataclass(frozen=True)
class VariableSpec:
    """One entry of the variable catalog (requirement M1)."""

    id: str
    name: str
    definition: str
    unit: str  # unified unit used everywhere inside the app
    source_unit: str  # unit found in the original file
    product: str
    version: str
    source_variables: tuple[str, ...]  # NASA variable names; several are summed
    substances: tuple[str, ...]
    step: Step
    kind: DataKind
    period_start: str  # "YYYY-MM"
    period_end: str | None  # "YYYY-MM" or None for ongoing records
    coverage: str
    source_url: str
    caveats: tuple[str, ...] = ()
    access: AccessSpec | None = None
    derivation: Derivation | None = None

    @property
    def variable_label(self) -> str:
        """NASA variable name(s) as one string for cards and data files."""
        return ", ".join(self.source_variables)

    @property
    def period_label(self) -> str:
        """Record length as text, e.g. ``1980-01 to present``."""
        return f"{self.period_start} to {self.period_end or 'present'}"


@dataclass(frozen=True)
class TrailGap:
    """A matrix cell without time series: reason and further reading (M9)."""

    substance: str
    step: Step
    status: GapStatus
    reason: str
    reference_label: str
    reference_url: str


@dataclass(frozen=True)
class ReferenceTrend:
    """Published trend range used by the validation case (spec 13.2)."""

    low_per_year: float
    high_per_year: float
    unit: str
    source: str
    confirmed: bool  # False while the team has not verified the numbers


@dataclass(frozen=True)
class DemoCase:
    """A prepared case: substances + regions + explanatory text (spec 11)."""

    id: str
    title: str
    purpose: str
    explanation: str
    substances: tuple[str, ...]
    region_sets: tuple[tuple[str, ...], ...]  # each set holds one or two region ids
    reference: ReferenceTrend | None = None
