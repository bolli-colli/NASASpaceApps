"""Reader for the subset files that NASA Harmony returns (HOSS service).

Harmony cuts a bounding box out of an HDF-EOS grid file and returns it as
netCDF-4. Where exactly the variable and its coordinates sit inside that file
(root or nested groups, ``lat`` or ``Latitude``) depends on the product, so
this reader searches the whole file instead of assuming one layout and
returns a plain dataset with ``lat``/``lon`` coordinates that
``grid_reduction.area_mean`` understands.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.infrastructure.grid_reduction import LAT, LON

if TYPE_CHECKING:  # xarray is an optional dependency (extra "live")
    import xarray as xr

_HDF5_ENGINE = "h5netcdf"
_LATITUDE_NAMES = {"lat", "latitude", "ydim"}
_LONGITUDE_NAMES = {"lon", "longitude", "xdim"}


def _find(tree: "xr.DataTree", names: set[str]) -> "xr.DataArray | None":
    """First array in any group whose (case-insensitive) name is in ``names``."""
    for node in tree.subtree:
        dataset = node.to_dataset(inherit=False)
        for name in (*dataset.data_vars, *dataset.coords):
            if str(name).lower() in names:
                return dataset[name]
    return None


def load_grid(path: Path, variable_names: tuple[str, ...]) -> "xr.Dataset":
    """Load the named variables of a subset file as ``(lat, lon)`` grids."""
    import xarray as xr

    # The time of a file comes from the job result; some products (IMERG) use a
    # calendar that xarray cannot decode without extra packages.
    with xr.open_datatree(path, engine=_HDF5_ENGINE, decode_times=False) as tree:
        latitude = _find(tree, _LATITUDE_NAMES)
        longitude = _find(tree, _LONGITUDE_NAMES)
        fields = {name: _find(tree, {name.lower()}) for name in variable_names}
        missing = [name for name, field in fields.items() if field is None]
        if latitude is None or longitude is None or missing:
            raise LiveAccessError(
                f"Unexpected layout of {path.name}: missing {missing or 'lat/lon coordinates'}. "
                f"File content:\n{tree}"
            )
        latitudes = latitude.to_numpy().ravel()
        longitudes = longitude.to_numpy().ravel()
        expected_shape = (latitudes.size, longitudes.size)
        grids = {}
        for name, field in fields.items():
            values = field.squeeze(drop=True).to_numpy()
            # HDF-EOS grids are stored (lat, lon); turn them if the file says otherwise.
            if values.shape != expected_shape and values.shape == expected_shape[::-1]:
                values = values.T
            if values.shape != expected_shape:
                raise LiveAccessError(
                    f"{path.name}: {name} has shape {values.shape}, expected {expected_shape}."
                )
            grids[name] = ((LAT, LON), values)
        return xr.Dataset(grids, coords={LAT: latitudes, LON: longitudes})
