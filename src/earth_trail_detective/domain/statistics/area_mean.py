"""Area average of a latitude/longitude grid (requirement M4)."""

import numpy as np


def cos_lat_weighted_mean(grid: np.ndarray, latitudes: np.ndarray) -> float:
    """Average a ``(lat, lon)`` grid with weights proportional to cos(latitude).

    Grid cells shrink towards the poles; cos(latitude) corrects for that.
    Missing cells (``NaN``) are ignored. Returns ``NaN`` if no cell has data.
    """
    weights = np.cos(np.deg2rad(latitudes))[:, np.newaxis] * np.ones_like(grid, dtype=float)
    valid = np.isfinite(grid)
    total_weight = weights[valid].sum()
    if total_weight == 0:
        return float("nan")
    return float((grid[valid] * weights[valid]).sum() / total_weight)
