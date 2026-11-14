"""Access to NASA Earthdata with the ``earthaccess`` library (requirement S5).

Granules are found through NASA's Common Metadata Repository (CMR), opened
over HTTPS and reduced file by file to area means – nothing is downloaded to
disk. Used for live mode and by ``scripts/build_cache.py``.

Supported are products whose files are netCDF-4/HDF5 lat/lon grids with one
file per month. Reading whole files takes about a minute per file, so the
catalog uses this gateway only where Harmony offers no service (OCO-2 GEOS);
everything else goes through ``HarmonyGateway``.

The optional dependencies (``pip install -e ".[live]"``) are imported lazily,
so the app starts and runs offline without them.
"""

from collections.abc import Sequence
from datetime import date

import pandas as pd

from earth_trail_detective.config import TOKEN_VARIABLE
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import AccessSpec, Region, VariableSpec
from earth_trail_detective.infrastructure.grid_reduction import area_mean
from earth_trail_detective.infrastructure.gridded_gateway import (
    AreaMeanCollector,
    GriddedGateway,
    RawValues,
)

_HDF5_ENGINE = "h5netcdf"


def _granule_start(granule) -> pd.Timestamp:
    """Start time of a granule from its CMR metadata (independent of file calendars)."""
    start = granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
    return pd.Timestamp(start).tz_localize(None)


class EarthaccessGateway(GriddedGateway):
    """Reads whole files remotely and averages the region boxes locally."""

    provider = "earthaccess"

    @staticmethod
    def _login() -> None:
        """Authenticate with the token from the environment (never from the browser)."""
        import earthaccess

        try:
            auth = earthaccess.login(strategy="environment")
        except Exception as error:  # earthaccess raises several error types
            raise LiveAccessError(f"Earthdata login failed: {error}") from error
        if not auth.authenticated:
            raise LiveAccessError(
                f"Earthdata login failed. Set the environment variable {TOKEN_VARIABLE}."
            )

    def _fetch_collection(
        self,
        access: AccessSpec,
        variables: Sequence[VariableSpec],
        regions: Sequence[Region],
        start: date,
        end: date,
    ) -> RawValues:
        import earthaccess
        import xarray as xr

        self._login()
        try:
            granules = earthaccess.search_data(
                short_name=access.short_name,
                version=access.version,
                temporal=(start.isoformat(), end.isoformat()),
            )
            handles = earthaccess.open(granules)
        except Exception as error:
            raise LiveAccessError(f"Search for {access.short_name} failed: {error}") from error
        if not granules:
            raise LiveAccessError(f"No files found for {access.short_name} from {start} to {end}.")

        collector = AreaMeanCollector()
        for granule, handle in zip(granules, handles, strict=True):
            time = _granule_start(granule)
            try:
                # The time comes from the CMR metadata, so the file's own time axis
                # (sometimes in an undecodable calendar) is left as plain numbers.
                with xr.open_dataset(
                    handle, engine=_HDF5_ENGINE, group=access.group, decode_times=False
                ) as dataset:
                    for variable in variables:
                        for region in regions:
                            value = area_mean(dataset, variable.source_variables, region.bbox)
                            collector.add(variable, region, time, value)
            except OSError as error:
                raise LiveAccessError(
                    f"Cannot read a file of {access.short_name}: {error}"
                ) from error
        return collector.series()
