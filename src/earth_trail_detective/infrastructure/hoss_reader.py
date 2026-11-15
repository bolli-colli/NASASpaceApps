"""Readers that turn netCDF-4/HDF5 grid files into plain ``lat``/``lon`` datasets.

``load_grid`` reads the subset files that NASA Harmony returns (HOSS service).
Harmony cuts a bounding box out of an HDF-EOS grid file and returns it as
netCDF-4. Where exactly the variable and its coordinates sit inside that file
(root or nested groups, ``lat`` or ``Latitude``) depends on the product, so
this reader searches the whole file instead of assuming one layout.

``load_grouped_grid`` reads large whole files over the network (earthaccess)
whose variables live in groups, e.g. ``Cloud_Optical_Thickness_Liquid/Mean`` in
the MODIS ``CLDPROP_M3`` files (about 600 MB, about 1100 variables). It opens
only the root coordinates and the requested arrays, so a few MB are read
instead of the whole file.

Both return a dataset with ``lat``/``lon`` coordinates that
``grid_reduction.area_mean`` understands.
"""

from pathlib import Path
from typing import IO, TYPE_CHECKING

import numpy as np

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
        grids = {
            name: _as_grid(
                field.squeeze(drop=True).to_numpy(), latitudes, longitudes, name, path.name
            )
            for name, field in fields.items()
        }
        return xr.Dataset(grids, coords={LAT: latitudes, LON: longitudes})


def _as_grid(
    values: np.ndarray, latitudes: np.ndarray, longitudes: np.ndarray, name: str, file: object
) -> tuple[tuple[str, str], np.ndarray]:
    """Return ``values`` as a ``(lat, lon)`` grid; turn it if it is stored ``(lon, lat)``."""
    expected_shape = (latitudes.size, longitudes.size)
    if values.shape != expected_shape and values.shape == expected_shape[::-1]:
        values = values.T
    if values.shape != expected_shape:
        raise LiveAccessError(
            f"{file}: {name} has shape {values.shape}, expected {expected_shape}."
        )
    return (LAT, LON), values


def _decoded(variable) -> np.ndarray:
    """Values of an h5netcdf variable with fill values masked and scale/offset applied."""
    import xarray as xr

    raw = xr.Variable(variable.dimensions, variable[...], dict(variable.attrs))
    return xr.conventions.decode_cf_variable(variable.name, raw).to_numpy().astype(float)


def _find_variable(group, names: set[str]):
    """Variable of ``group`` whose (case-insensitive) name is in ``names``."""
    return next((v for key, v in group.variables.items() if key.lower() in names), None)


def load_grouped_grid(source: "Path | IO[bytes]", variable_paths: tuple[str, ...]) -> "xr.Dataset":
    """Load ``group/variable`` arrays plus the root ``lat``/``lon`` of one file."""
    import h5netcdf
    import xarray as xr

    file = str(getattr(source, "path", source)).rsplit("/", 1)[-1]
    with h5netcdf.File(source, "r") as root:
        latitude = _find_variable(root, _LATITUDE_NAMES)
        longitude = _find_variable(root, _LONGITUDE_NAMES)
        if latitude is None or longitude is None:
            raise LiveAccessError(f"{file}: no latitude/longitude in the root group.")
        latitudes = _decoded(latitude).ravel()
        longitudes = _decoded(longitude).ravel()
        grids = {}
        for path in variable_paths:
            group_name, _, name = path.rpartition("/")
            try:
                variable = root[group_name][name] if group_name else root[name]
            except KeyError as error:
                raise LiveAccessError(f"{file}: variable {path} not found.") from error
            values = np.squeeze(_decoded(variable))
            grids[path] = _as_grid(values, latitudes, longitudes, path, file)
    return xr.Dataset(grids, coords={LAT: latitudes, LON: longitudes})
