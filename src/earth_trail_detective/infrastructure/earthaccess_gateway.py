"""Live access to NASA Earthdata (requirement S5) with the user's own token.

Implements the ``LiveDataGateway`` port with the ``earthaccess`` library:
granules are found through NASA's Common Metadata Repository (CMR), opened
over HTTPS and reduced file by file to area means – nothing is downloaded to
disk. The same code fills the offline cache (``scripts/build_cache.py``).

Supported are products whose files are netCDF-4/HDF5 lat/lon grids
(MERRA-2, GLDAS, IMERG, OCO-2 GEOS). Everything else is imported from CSV.

The optional dependencies (``pip install -e ".[live]"``) are imported lazily,
so the app starts and runs offline without them.
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date

import pandas as pd

from earth_trail_detective.application.ingest import build_series
from earth_trail_detective.config import TOKEN_VARIABLE
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import AccessSpec, Period, Region, VariableSpec
from earth_trail_detective.domain.series import MonthlySeries
from earth_trail_detective.infrastructure.grid_reduction import area_mean

PROVIDER = "earthaccess"
_HDF5_ENGINE = "h5netcdf"


def _granule_start(granule) -> pd.Timestamp:
    """Start time of a granule from its CMR metadata (independent of file calendars)."""
    start = granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
    return pd.Timestamp(start).tz_localize(None)


class EarthaccessGateway:
    """Retrieves monthly area means from NASA Earthdata."""

    def supports(self, variable: VariableSpec) -> bool:
        return variable.access is not None and variable.access.provider == PROVIDER

    def fetch(
        self, variables: Sequence[VariableSpec], regions: Sequence[Region], period: Period
    ) -> list[MonthlySeries]:
        """Fetch all variables for all regions; every file is opened only once."""
        unsupported = [variable.id for variable in variables if not self.supports(variable)]
        if unsupported:
            raise LiveAccessError(f"No scripted access for: {unsupported}")
        self._login()

        # Variables of the same collection share their files.
        by_collection: dict[AccessSpec, list[VariableSpec]] = defaultdict(list)
        for variable in variables:
            by_collection[variable.access].append(variable)

        raw: dict[tuple[str, str], pd.Series] = {}
        for access, members in by_collection.items():
            raw.update(self._fetch_collection(access, members, regions, period))
        return [
            build_series(variable, region, raw[(variable.id, region.id)])
            for variable in variables
            for region in regions
        ]

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

    @staticmethod
    def _fetch_collection(
        access: AccessSpec,
        variables: Sequence[VariableSpec],
        regions: Sequence[Region],
        period: Period,
    ) -> dict[tuple[str, str], pd.Series]:
        """Reduce every granule of one collection to area means."""
        import earthaccess
        import xarray as xr

        start = period.start or date.fromisoformat(f"{variables[0].period_start}-01")
        end = period.end or date.today()
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
            raise LiveAccessError(f"No files found for {access.short_name} in {period.label}.")

        values: dict[tuple[str, str], dict[pd.Timestamp, float]] = defaultdict(dict)
        for granule, handle in zip(granules, handles, strict=True):
            timestamp = _granule_start(granule)
            try:
                with xr.open_dataset(handle, engine=_HDF5_ENGINE, group=access.group) as dataset:
                    for variable in variables:
                        for region in regions:
                            values[(variable.id, region.id)][timestamp] = area_mean(
                                dataset, variable.source_variables, region.bbox
                            )
            except OSError as error:
                raise LiveAccessError(
                    f"Cannot read a file of {access.short_name}: {error}"
                ) from error
        return {key: pd.Series(series).sort_index() for key, series in values.items()}
