"""Unit harmonisation applied when data is loaded (spec 9, "Vorverarbeitung").

Each conversion is a constant factor, optionally multiplied by the length of
the month (rates per second/hour become totals per month). New conversions
are added to ``_CONVERSIONS`` only – no other code has to change.
"""

from dataclasses import dataclass

import pandas as pd

from earth_trail_detective.domain.errors import UnitConversionError

SECONDS_PER_DAY = 86_400
HOURS_PER_DAY = 24
THREE_HOUR_STEPS_PER_DAY = 8


@dataclass(frozen=True)
class _Conversion:
    """``target = source * factor * (steps_per_day * days in month)``."""

    factor: float
    steps_per_day: int | None = None  # None: no dependence on month length


_CONVERSIONS: dict[tuple[str, str], _Conversion] = {
    # Column and surface masses
    ("kg m-2", "mg m-2"): _Conversion(1e6),
    ("kg m-3", "µg m-3"): _Conversion(1e9),
    # Deposition and scavenging fluxes -> monthly totals (spec 9 example)
    ("kg m-2 s-1", "mg m-2 month-1"): _Conversion(1e6, SECONDS_PER_DAY),
    # Water fluxes: 1 kg of water per m² is a 1 mm layer
    ("kg m-2 s-1", "mm month-1"): _Conversion(1.0, SECONDS_PER_DAY),
    ("mm h-1", "mm month-1"): _Conversion(1.0, HOURS_PER_DAY),
    # GLDAS "*_acc" monthly files hold the mean 3-hourly accumulation
    ("kg m-2 (3h)-1", "mm month-1"): _Conversion(1.0, THREE_HOUR_STEPS_PER_DAY),
    # Mixing ratios
    ("mol mol-1", "ppm"): _Conversion(1e6),
}


def convert(values: pd.Series, source_unit: str, target_unit: str) -> pd.Series:
    """Convert a date-indexed monthly series from one unit to another."""
    if source_unit == target_unit:
        return values
    try:
        conversion = _CONVERSIONS[(source_unit, target_unit)]
    except KeyError:
        raise UnitConversionError(
            f"No conversion from '{source_unit}' to '{target_unit}' is defined."
        ) from None
    converted = values * conversion.factor
    if conversion.steps_per_day is not None:
        converted = converted * conversion.steps_per_day * values.index.days_in_month
    return converted
