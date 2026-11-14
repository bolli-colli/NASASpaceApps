"""The single place where raw values become a series in the common format.

Used by every loader (CSV import, Earthdata gateway, synthetic generator), so
monthly aggregation and unit harmonisation are implemented exactly once.
"""

import pandas as pd

from earth_trail_detective.domain.models import Region, VariableSpec
from earth_trail_detective.domain.series import MonthlySeries, SeriesMeta, to_month_start
from earth_trail_detective.domain.units import convert


def build_series(
    variable: VariableSpec,
    region: Region,
    raw: pd.Series,
    source_unit: str | None = None,
    source_url: str | None = None,
) -> MonthlySeries:
    """Aggregate date-indexed raw values to months and unify their unit.

    ``source_unit`` defaults to the unit the catalog lists for the original
    file; pass it only if an export already uses a different unit.
    """
    # Daily (or finer) values become monthly means; monthly values stay as is.
    monthly = raw.astype(float).groupby(to_month_start(raw.index)).mean()
    converted = convert(monthly, source_unit or variable.source_unit, variable.unit)
    return MonthlySeries(converted, SeriesMeta.describe(variable, region, source_url))
