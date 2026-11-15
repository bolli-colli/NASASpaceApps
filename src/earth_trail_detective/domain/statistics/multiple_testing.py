"""Correction for testing many cards at once (requirement C6)."""

from collections.abc import Sequence

from statsmodels.stats.multitest import multipletests


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Return Benjamini-Hochberg adjusted p-values (false discovery rate)."""
    if not p_values:
        return []
    return [float(p) for p in multipletests(p_values, method="fdr_bh")[1]]
