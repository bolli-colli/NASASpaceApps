"""The common data format (spec 10.4) and its in-memory representation.

On disk a series is a table with the columns listed in ``COLUMNS``.
In memory it is a ``MonthlySeries``: the values on a regular monthly index
plus one ``SeriesMeta`` object, so the constant columns are stored only once.
"""

from dataclasses import asdict, dataclass, fields

import pandas as pd

from earth_trail_detective.domain.errors import SeriesFormatError
from earth_trail_detective.domain.models import Period, Region, VariableSpec

DATE_COLUMN = "date"
VALUE_COLUMN = "value"

# Product name that marks artificial development data (never NASA data).
SYNTHETIC_PRODUCT = "SYNTHETIC"


@dataclass(frozen=True)
class SeriesMeta:
    """The descriptive columns of the common data format."""

    unit: str
    variable: str
    product: str
    version: str
    region: str
    substance: str
    step: str
    kind: str
    source_url: str

    @classmethod
    def describe(
        cls, variable: VariableSpec, region: Region, source_url: str | None = None
    ) -> "SeriesMeta":
        """Build the metadata of a series from its catalog entry and region."""
        return cls(
            unit=variable.unit,
            variable=variable.variable_label,
            product=variable.product,
            version=variable.version,
            region=region.name,
            substance=", ".join(variable.substances),
            step=variable.step.value,
            kind=variable.kind.value,
            source_url=source_url or variable.source_url,
        )


META_COLUMNS = tuple(field.name for field in fields(SeriesMeta))
# Column order of the common data format: date, value, unit, variable, ...
COLUMNS = (DATE_COLUMN, VALUE_COLUMN, *META_COLUMNS)


def to_month_start(index: pd.Index) -> pd.DatetimeIndex:
    """Snap arbitrary timestamps to the first day of their month."""
    return pd.DatetimeIndex(index).to_period("M").to_timestamp()


@dataclass(frozen=True, eq=False)
class MonthlySeries:
    """Monthly values of one variable in one region.

    The index is always a gap-free range of month starts; months without data
    hold ``NaN`` (missing values are marked, never interpolated – spec 9).
    """

    values: pd.Series
    meta: SeriesMeta

    def __post_init__(self) -> None:
        values = self.values.astype(float)
        values.index = to_month_start(values.index)
        if values.index.has_duplicates:
            raise SeriesFormatError("A monthly series must have one value per month.")
        values = values.sort_index().asfreq("MS").rename(VALUE_COLUMN)
        values.index.name = DATE_COLUMN
        # The dataclass is frozen, so the normalised copy is set explicitly.
        object.__setattr__(self, "values", values)

    @property
    def is_synthetic(self) -> bool:
        """True for artificial development data."""
        return self.meta.product == SYNTHETIC_PRODUCT

    def cropped(self, period: Period) -> "MonthlySeries":
        """Return the same series limited to a period."""
        return MonthlySeries(period.crop(self.values), self.meta)

    def to_frame(self) -> pd.DataFrame:
        """Convert to a table in the common data format."""
        frame = self.values.reset_index()
        return frame.assign(**asdict(self.meta))[list(COLUMNS)]

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "MonthlySeries":
        """Read a table in the common data format."""
        missing = set(COLUMNS) - set(frame.columns)
        if missing:
            raise SeriesFormatError(f"Missing columns: {sorted(missing)}")
        if frame.empty:
            raise SeriesFormatError("The table contains no rows.")
        # Metadata columns are constant, so the first row describes the series.
        meta = SeriesMeta(**{column: str(frame[column].iloc[0]) for column in META_COLUMNS})
        values = pd.Series(frame[VALUE_COLUMN].to_numpy(), index=frame[DATE_COLUMN])
        return cls(values, meta)
