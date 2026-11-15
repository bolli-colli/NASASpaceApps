"""Access to NASA Earthdata with the ``earthaccess`` library (requirement S5).

Granules are found through NASA's Common Metadata Repository (CMR), opened
over HTTPS and reduced file by file to area means – nothing is downloaded to
disk. Used for live mode and by ``scripts/build_cache.py``.

Supported are products whose files are netCDF-4/HDF5 lat/lon grids with one
file per month. Reading whole files takes about a minute per file, so the
catalog uses this gateway only where Harmony offers no service (OCO-2 GEOS,
MODIS CLDPROP cloud properties); everything else goes through ``HarmonyGateway``.

Variables given as ``group/variable`` (CLDPROP: ``Cloud_Optical_Thickness_Liquid/Mean``)
are read with ``hoss_reader.load_grouped_grid``, which fetches only those arrays and
the root coordinates – about 15 s for three variables of a 600 MB file.

Reading is bound by network latency (many small byte-range requests), not by
bandwidth. With a token, several files are therefore read at the same time in
separate processes (``ETD_WORKERS``, default 6; ``1`` = one after the other).
Processes, not threads: h5py runs every HDF5 call under one global lock.

The optional dependencies (``pip install -e ".[live]"``) are imported lazily,
so the app starts and runs offline without them.
"""

import logging
import os
import time as clock
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from datetime import date
from multiprocessing import get_context

import pandas as pd

from earth_trail_detective.config import TOKEN_VARIABLE, WORKERS_VARIABLE
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import AccessSpec, BoundingBox, Region, VariableSpec
from earth_trail_detective.infrastructure.grid_reduction import area_mean
from earth_trail_detective.infrastructure.gridded_gateway import (
    AreaMeanCollector,
    GriddedGateway,
    RawValues,
)
from earth_trail_detective.infrastructure.hoss_reader import load_grouped_grid

_HDF5_ENGINE = "h5netcdf"
_DEFAULT_WORKERS = 6
_ATTEMPTS = 3  # per file; NASA archives answer 429/5xx when busy
_CACHE = {"cache_type": "blockcache", "block_size": 2**20}
_LOG = logging.getLogger(__name__)

# One area mean to compute per file: (source variable names, region box)
Job = tuple[tuple[str, ...], BoundingBox]


def _workers() -> int:
    """Number of files read at the same time (``ETD_WORKERS``)."""
    value = os.environ.get(WORKERS_VARIABLE, "").strip()
    try:
        return max(1, int(value)) if value else _DEFAULT_WORKERS
    except ValueError as error:
        raise LiveAccessError(f"{WORKERS_VARIABLE}={value!r} is not a whole number.") from error


def _granule_url(granule) -> str:
    """HTTPS address of the data file of a granule."""
    links = granule.data_links(access="external")
    if not links:
        raise LiveAccessError(f"Granule {granule['umm'].get('GranuleUR')} has no data link.")
    return next((link for link in links if link.endswith((".nc", ".nc4", ".h5"))), links[0])


def area_means_of_file(
    url: str, token: str, names: tuple[str, ...], group: str | None, jobs: Sequence[Job]
) -> list[float]:
    """Open one file over HTTPS and return one area mean per job (runs in a worker)."""
    import fsspec
    import xarray as xr

    grouped = any("/" in name for name in names)
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            filesystem = fsspec.filesystem("https", client_kwargs={"headers": headers})
            # HDF5 reads many small pieces; a 1 MB block cache is ~3x faster than
            # fsspec's default 5 MB read-ahead (11 s instead of 33 s per CLDPROP file).
            with filesystem.open(url, "rb", **_CACHE) as handle:
                if grouped:
                    dataset = load_grouped_grid(handle, names)
                else:
                    dataset = xr.open_dataset(
                        handle, engine=_HDF5_ENGINE, group=group, decode_times=False
                    ).load()
            with dataset:
                return [area_mean(dataset, sources, bbox) for sources, bbox in jobs]
        except LiveAccessError:
            raise  # wrong layout: retrying does not help
        except Exception as error:  # network errors come in many types (aiohttp, OSError)
            if attempt == _ATTEMPTS:
                raise LiveAccessError(f"Cannot read {url}: {error}") from error
            clock.sleep(10 * attempt)
    return []  # not reached


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
        except Exception as error:
            raise LiveAccessError(f"Search for {access.short_name} failed: {error}") from error
        if not granules:
            raise LiveAccessError(f"No files found for {access.short_name} from {start} to {end}.")

        names = tuple(dict.fromkeys(n for v in variables for n in v.source_variables))
        token = os.environ.get(TOKEN_VARIABLE, "").strip()
        workers = _workers()
        if token and workers > 1 and len(granules) > 1:
            try:
                return self._fetch_parallel(
                    access, variables, regions, granules, names, token, workers
                )
            except BrokenProcessPool as error:  # e.g. a host that cannot start processes
                _LOG.warning("Parallel reading failed (%s); reading one file at a time.", error)

        try:
            handles = earthaccess.open(granules)
        except Exception as error:
            raise LiveAccessError(f"Cannot open {access.short_name}: {error}") from error
        grouped = any("/" in name for name in names)
        collector = AreaMeanCollector()
        for granule, handle in zip(granules, handles, strict=True):
            time = _granule_start(granule)
            try:
                if grouped:  # read only the wanted arrays of a large file
                    dataset = load_grouped_grid(handle, names)
                else:
                    # The time comes from the CMR metadata, so the file's own time axis
                    # (sometimes in an undecodable calendar) is left as plain numbers.
                    dataset = xr.open_dataset(
                        handle, engine=_HDF5_ENGINE, group=access.group, decode_times=False
                    )
                with dataset:
                    for variable in variables:
                        for region in regions:
                            value = area_mean(dataset, variable.source_variables, region.bbox)
                            collector.add(variable, region, time, value)
            except OSError as error:
                raise LiveAccessError(
                    f"Cannot read a file of {access.short_name}: {error}"
                ) from error
        return collector.series()

    @staticmethod
    def _fetch_parallel(
        access: AccessSpec,
        variables: Sequence[VariableSpec],
        regions: Sequence[Region],
        granules: list,
        names: tuple[str, ...],
        token: str,
        workers: int,
    ) -> RawValues:
        """Read ``workers`` files at the same time, each in its own process."""
        pairs = [(variable, region) for variable in variables for region in regions]
        jobs = [(variable.source_variables, region.bbox) for variable, region in pairs]
        collector = AreaMeanCollector()
        total, started = len(granules), clock.monotonic()
        # "spawn": a clean interpreter per worker (fork is unsafe on macOS with threads).
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as pool:
            futures = {
                pool.submit(
                    area_means_of_file, _granule_url(granule), token, names, access.group, jobs
                ): _granule_start(granule)
                for granule in granules
            }
            for done, future in enumerate(as_completed(futures), start=1):
                try:
                    values = future.result()
                except LiveAccessError:
                    for other in futures:
                        other.cancel()
                    raise
                for (variable, region), value in zip(pairs, values, strict=True):
                    collector.add(variable, region, futures[future], value)
                if done % 10 == 0 or done == total:
                    minutes = (clock.monotonic() - started) / 60
                    _LOG.info("%s: %d/%d files, %.1f min", access.short_name, done, total, minutes)
        return collector.series()
