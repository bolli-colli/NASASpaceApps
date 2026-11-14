"""Reduce one gridded file to the area mean of a bounding box (requirement M4).

Kept separate from the network code so it can be tested with small in-memory
datasets. Expects a regular grid with coordinates named ``lat`` and ``lon``.
"""

from typing import TYPE_CHECKING

from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import BoundingBox
from earth_trail_detective.domain.statistics.area_mean import cos_lat_weighted_mean

if TYPE_CHECKING:  # xarray is an optional dependency (extra "live")
    import xarray as xr

LAT = "lat"
LON = "lon"


def area_mean(dataset: "xr.Dataset", variable_names: tuple[str, ...], bbox: BoundingBox) -> float:
    """Sum the given variables (e.g. size bins) and average them over the box."""
    missing = [name for name in variable_names if name not in dataset]
    if missing:
        raise LiveAccessError(f"Variables {missing} are not in the file.")
    # One file holds one time step: drop the time axis (and other length-1 axes).
    field = sum(dataset[name] for name in variable_names).squeeze(drop=True)
    if set(field.dims) != {LAT, LON}:
        raise LiveAccessError(
            f"Expected a lat/lon grid but found the dimensions {field.dims}; "
            "products with extra dimensions (e.g. pressure levels) are not supported."
        )
    inside = (
        (field[LAT] >= bbox.south)
        & (field[LAT] <= bbox.north)
        & (field[LON] >= bbox.west)
        & (field[LON] <= bbox.east)
    )
    box = field.where(inside, drop=True).transpose(LAT, LON)
    if box.size == 0:
        raise LiveAccessError("The bounding box contains no grid cell centre; enlarge the box.")
    return cos_lat_weighted_mean(box.to_numpy(), box[LAT].to_numpy())
