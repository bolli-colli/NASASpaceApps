"""Rate of change (requirement M6): Sen's slope and OLS with confidence interval.

Both estimators use the real time axis in decimal years, so gaps in a series
do not distort the slope. Missing values are dropped, never interpolated.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

MONTHS_PER_YEAR = 12


def decimal_years(index: pd.DatetimeIndex) -> np.ndarray:
    """Convert month starts to decimal years, e.g. July 2004 -> 2004.5."""
    return np.asarray(index.year + (index.month - 1) / MONTHS_PER_YEAR, dtype=float)


@dataclass(frozen=True, eq=False)
class SenSlope:
    """Robust trend: median of all pairwise slopes."""

    slope_per_year: float
    line: pd.Series  # fitted line at the dates that hold data


@dataclass(frozen=True, eq=False)
class OlsFit:
    """Ordinary least squares trend with its confidence interval."""

    slope_per_year: float
    ci_low_per_year: float
    ci_high_per_year: float
    band: pd.DataFrame  # columns: fit, lower, upper (confidence band of the line)


def sen_slope(values: pd.Series) -> SenSlope:
    """Estimate Sen's slope (Theil-Sen estimator) per year."""
    valid = values.dropna()
    years = decimal_years(valid.index)
    slope, intercept, _, _ = stats.theilslopes(valid.to_numpy(), years)
    line = pd.Series(intercept + slope * years, index=valid.index)
    return SenSlope(float(slope), line)


def ols_trend(values: pd.Series, alpha: float) -> OlsFit:
    """Fit a straight line by OLS; the interval has confidence ``1 - alpha``."""
    valid = values.dropna()
    # Years are centred to keep the regression numerically well conditioned.
    years = decimal_years(valid.index)
    design = sm.add_constant(years - years.mean())
    fit = sm.OLS(valid.to_numpy(), design).fit()
    ci_low, ci_high = fit.conf_int(alpha=alpha)[1]
    prediction = fit.get_prediction(design).summary_frame(alpha=alpha)
    band = pd.DataFrame(
        {
            "fit": prediction["mean"].to_numpy(),
            "lower": prediction["mean_ci_lower"].to_numpy(),
            "upper": prediction["mean_ci_upper"].to_numpy(),
        },
        index=valid.index,
    )
    return OlsFit(float(fit.params[1]), float(ci_low), float(ci_high), band)
