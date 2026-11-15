"""Removal of the seasonal cycle (requirement M5)."""

import pandas as pd

from earth_trail_detective.domain.models import Period

_NO_LIMIT = Period()


def monthly_climatology(values: pd.Series, period: Period = _NO_LIMIT) -> pd.Series:
    """Mean value of each calendar month (index 1..12) within ``period``."""
    reference = period.crop(values)
    return reference.groupby(reference.index.month).mean()


def deseasonalize(values: pd.Series, climatology_period: Period = _NO_LIMIT) -> pd.Series:
    """Return anomalies: each value minus the climatology of its calendar month.

    Calendar months without any data in the climatology period yield ``NaN``.
    """
    climatology = monthly_climatology(values, climatology_period)
    seasonal_cycle = climatology.reindex(values.index.month).to_numpy()
    return values - seasonal_cycle
