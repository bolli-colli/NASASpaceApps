"""Access to gridded products through NASA Harmony (spec 10.5: "OPeNDAP/Harmony").

Harmony cuts the region box out of every file **on NASA's servers** (service
HOSS) and returns small netCDF files. They are downloaded to a temporary
folder, averaged with cos(latitude) weights and deleted again. Used for the
daily OMI grids and the monthly MERRA-2, GLDAS and IMERG products - far faster
than reading whole files.

One Harmony job is submitted per region and calendar year, so a single job
never has to process more than about 366 files.

Needs the "live" extra and the environment variable ``EARTHDATA_TOKEN``.
"""

import os
import tempfile
from collections.abc import Iterator, Sequence
from datetime import date, datetime
from pathlib import Path

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
from earth_trail_detective.infrastructure.hoss_reader import load_grid

CMR_COLLECTIONS_URL = "https://cmr.earthdata.nasa.gov/search/collections.json"
_REQUEST_TIMEOUT_SECONDS = 60
_DATA_LINK = "data"
# harmony-py reads its number of parallel downloads from this variable (default 3).
_WORKERS_VARIABLE = "NUM_REQUESTS_WORKERS"
_PARALLEL_DOWNLOADS = "8"


def yearly_chunks(start: date, end: date) -> Iterator[tuple[datetime, datetime]]:
    """Split a period into pieces that each stay within one calendar year."""
    for year in range(start.year, end.year + 1):
        first = max(start, date(year, 1, 1))
        last = min(end, date(year, 12, 31))
        yield (
            datetime(first.year, first.month, first.day),
            datetime(last.year, last.month, last.day, 23, 59, 59),
        )


def find_collection_id(short_name: str, version: str) -> str:
    """Look up the CMR concept id of a collection (public, no login needed).

    Harmony addresses collections by this id; asking for short name *and*
    version avoids silently getting a different product version.
    """
    import requests

    response = requests.get(
        CMR_COLLECTIONS_URL,
        params={"short_name": short_name, "version": version},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    entries = response.json()["feed"]["entry"]
    if not entries:
        raise LiveAccessError(f"NASA's catalog has no collection {short_name} version {version}.")
    return entries[0]["id"]


class HarmonyGateway(GriddedGateway):
    """Lets Harmony subset the files and averages the small results locally."""

    provider = "harmony"

    def _fetch_collection(
        self,
        access: AccessSpec,
        variables: Sequence[VariableSpec],
        regions: Sequence[Region],
        start: date,
        end: date,
    ) -> RawValues:
        from harmony import BBox, Client, Collection, Request

        token = os.environ.get(TOKEN_VARIABLE)
        if not token:
            raise LiveAccessError(f"Set the environment variable {TOKEN_VARIABLE}.")
        os.environ.setdefault(_WORKERS_VARIABLE, _PARALLEL_DOWNLOADS)
        try:
            client = Client(token=token)
            collection = Collection(id=find_collection_id(access.short_name, access.version))
            # Harmony names a variable by its full path inside the file.
            prefix = f"{access.group}/" if access.group else ""
            paths = [
                f"{prefix}{name}" for variable in variables for name in variable.source_variables
            ]
            collector = AreaMeanCollector()
            with tempfile.TemporaryDirectory() as directory:
                for region in regions:
                    box = region.bbox
                    jobs = [
                        client.submit(
                            Request(
                                collection=collection,
                                spatial=BBox(box.west, box.south, box.east, box.north),
                                temporal={"start": chunk_start, "stop": chunk_end},
                                variables=paths,
                            )
                        )
                        for chunk_start, chunk_end in yearly_chunks(start, end)
                    ]
                    for job in jobs:
                        self._collect_job(client, job, directory, variables, region, collector)
        except LiveAccessError:
            raise
        except Exception as error:  # harmony-py and requests raise several error types
            raise LiveAccessError(
                f"Harmony request for {access.short_name} failed: {error}"
            ) from error
        return collector.series()

    @staticmethod
    def _collect_job(
        client,
        job_id: str,
        directory: str,
        variables: Sequence[VariableSpec],
        region: Region,
        collector: AreaMeanCollector,
    ) -> None:
        """Wait for one job, then download, average and delete each result file."""
        client.wait_for_processing(job_id)
        # Start all downloads first (harmony-py loads them in parallel), then read them.
        downloads = [
            # The time of a file comes from the job result, not from the file name.
            (
                pd.Timestamp(link["temporal"]["start"]).tz_localize(None),
                client.download(link["href"], directory, overwrite=True),
            )
            for link in client.result_json(job_id)["links"]
            if link.get("rel") == _DATA_LINK
        ]
        names = tuple(name for variable in variables for name in variable.source_variables)
        for time, download in downloads:
            path = Path(download.result())
            grid = load_grid(path, names)  # every file is opened only once
            for variable in variables:
                value = area_mean(grid, variable.source_variables, region.bbox)
                collector.add(variable, region, time, value)
            path.unlink()
