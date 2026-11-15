"""Significance of a monotonic trend (requirement M7).

The tests themselves come from ``pymannkendall``. The registry below maps
each selectable variant to its implementation, so a further variant is one
new dictionary entry (open/closed principle).
"""

from collections.abc import Callable

import numpy as np
import pandas as pd
import pymannkendall as mk

from earth_trail_detective.domain.enums import MannKendallVariant

_TESTS: dict[MannKendallVariant, Callable] = {
    # Default: variance correction for autocorrelated data (Hamed & Rao 1998)
    MannKendallVariant.HAMED_RAO: mk.hamed_rao_modification_test,
    MannKendallVariant.YUE_WANG: mk.yue_wang_modification_test,
    MannKendallVariant.PRE_WHITENING: mk.pre_whitening_modification_test,
    # Classic test, assumes independent values; shown for comparison
    MannKendallVariant.ORIGINAL: mk.original_test,
}


def mann_kendall_p(values: pd.Series, variant: MannKendallVariant) -> float:
    """Two-sided p-value of the chosen Mann-Kendall test (missing values dropped).

    Safeguard: a corrected variant is never allowed to be *less* strict than
    the classic test. The corrections estimate the autocorrelation from the
    data; by chance that estimate can be negative, which shrinks the variance
    and doubles the false-alarm rate on pure noise (about 10 % instead of 5 %
    in our simulations). Taking the larger p-value keeps the rate at 5 % and
    still removes spurious significance in autocorrelated data.
    """
    data = values.dropna().to_numpy()
    classic_p = float(mk.original_test(data).p)
    if variant is MannKendallVariant.ORIGINAL:
        return classic_p
    with np.errstate(invalid="ignore"):  # a failed correction is handled below
        corrected_p = float(_TESTS[variant](data).p)
    # The correction can break down (negative variance estimate -> NaN).
    return max(corrected_p, classic_p) if np.isfinite(corrected_p) else classic_p
