"""Area-averaged time series computed on NASA's servers (Giovanni in the cloud).

NASA Harmony runs Giovanni's "Area-Averaged Time Series" as a service: one job
per variable and region returns a small CSV with one area mean per time step
of the product. Nothing has to be downloaded file by file, so this is the
fastest route for the **daily** OMI grids (20 years in about 20 seconds,
compared with hours when every daily file is subset and averaged locally).

The CSV has the same layout as a Giovanni website download and is read with
the CSV importer; ``build_series`` then averages to months as for every
other source. Checked on 2026-11-14: identical monthly means to the Harmony
subsetting route (OMI aerosol index, Ohio Valley, Jan-Mar 2020).

Which variables the service accepts is listed at ``CONFIGURED_VARIABLES_URL``;
the catalog names them in ``access.giovanni_id``
(``<ShortName>_<Version>_<Variable>``, e.g. ``OMSO2e_003_ColumnAmountSO2``).
Giovanni has a monthly compute quota per user, checked before each product.

Needs the "live" extra and the environment variable ``EARTHDATA_TOKEN``.
"""

import os
import tempfile
import time
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

import pandas as pd

from earth_trail_detective.config import TOKEN_VARIABLE
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import AccessSpec, BoundingBox, Region, VariableSpec
from earth_trail_detective.infrastructure.csv_import import read_time_series_csv
from earth_trail_detective.infrastructure.gridded_gateway import GriddedGateway, RawValues
from earth_trail_detective.infrastructure.harmony_gateway import find_collection_id

HARMONY_URL = "https://harmony.earthdata.nasa.gov"
QUOTA_URL = "https://api.giovanni.earthdata.nasa.gov/quota"
CONFIGURED_VARIABLES_URL = "https://api.giovanni.earthdata.nasa.gov/configured-variables/"
JOB_LABEL = "earth-trail-detective"
QUOTA_LIMIT = 0.95  # stop before the monthly Giovanni quota is used up
_REQUEST_TIMEOUT_SECONDS = 60
_JOB_TIMEOUT_SECONDS = 30 * 60
_FIRST_POLL_SECONDS = 2.0
_MAX_POLL_SECONDS = 15.0
_FINISHED = {"successful", "complete_with_errors", "failed", "canceled"}
_DATA_LINK = "data"


def coverage_url(collection_id: str) -> str:
    """OGC coverage endpoint of a collection; variables are given as parameters."""
    return (
        f"{HARMONY_URL}/{collection_id}/ogc-api-coverages/1.0.0/collections/"
        "parameter_vars/coverage/rangeset"
    )


def averaging_parameters(
    giovanni_id: str, bbox: BoundingBox, start: date, end: date
) -> list[tuple[str, str]]:
    """Query parameters of one area-average job (repeated keys, so a list)."""
    return [
        ("variable", giovanni_id),
        ("subset", f"lat({bbox.south}:{bbox.north})"),
        ("subset", f"lon({bbox.west}:{bbox.east})"),
        ("subset", f'time("{start.isoformat()}T00:00:00Z":"{end.isoformat()}T23:59:59Z")'),
        ("average", "area"),
        ("format", "text/csv"),
        ("skipPreview", "true"),
        ("forceAsync", "true"),
        ("label", JOB_LABEL),
    ]


def _error_text(response) -> str:
    """Harmony's own error description, or the start of the response body."""
    try:
        return response.json().get("description", response.text[:300])
    except ValueError:
        return response.text[:300]


class GiovanniGateway(GriddedGateway):
    """Lets Giovanni (via Harmony) compute the area means on NASA's servers."""

    provider = "giovanni"

    def __init__(self, session=None, sleep: Callable[[float], None] = time.sleep) -> None:
        # Both can be replaced in tests; the real session is created on first use.
        self._session = session
        self._sleep = sleep

    def _http(self):
        if self._session is None:
            import requests

            token = os.environ.get(TOKEN_VARIABLE)
            if not token:
                raise LiveAccessError(f"Set the environment variable {TOKEN_VARIABLE}.")
            self._session = requests.Session()
            self._session.headers["Authorization"] = f"Bearer {token}"
        return self._session

    def _fetch_collection(
        self,
        access: AccessSpec,
        variables: Sequence[VariableSpec],
        regions: Sequence[Region],
        start: date,
        end: date,
    ) -> RawValues:
        if not access.giovanni_id:
            raise LiveAccessError(f"{access.short_name}: the catalog entry has no giovanni_id.")
        self._check_quota()
        try:
            collection_id = find_collection_id(access.short_name, access.version)
            # Submit every region first: NASA processes the jobs in parallel.
            jobs = {
                region.id: self._submit(collection_id, access.giovanni_id, region.bbox, start, end)
                for region in regions
            }
            series = {region_id: self._result(job) for region_id, job in jobs.items()}
        except LiveAccessError:
            raise
        except Exception as error:  # requests and pandas raise several error types
            raise LiveAccessError(
                f"Giovanni request for {access.giovanni_id} failed: {error}"
            ) from error
        # One Giovanni variable per collection entry: all catalog variables that
        # share this access block get the same series.
        return {
            (variable.id, region_id): values
            for variable in variables
            for region_id, values in series.items()
        }

    def _check_quota(self) -> None:
        """Stop before Giovanni's monthly compute quota runs out."""
        response = self._http().get(QUOTA_URL, timeout=_REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 401:
            raise LiveAccessError("Earthdata token rejected (401) - is it expired?")
        if not response.ok:
            return  # the quota service being down must not block the data request
        used = float(response.json().get("quota", 0.0))
        if used >= QUOTA_LIMIT:
            raise LiveAccessError(
                f"{used:.0%} of this month's Giovanni quota is used - stopping to keep a reserve."
            )

    def _submit(
        self, collection_id: str, giovanni_id: str, bbox: BoundingBox, start: date, end: date
    ) -> str:
        """Start one job; Harmony answers with a redirect to the job's status page."""
        response = self._http().get(
            coverage_url(collection_id),
            params=averaging_parameters(giovanni_id, bbox, start, end),
            allow_redirects=False,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code in (301, 302, 303):
            return HARMONY_URL + response.headers["Location"]
        if response.ok and "jobID" in response.json():
            return f"{HARMONY_URL}/jobs/{response.json()['jobID']}"
        raise LiveAccessError(
            f"Giovanni rejected {giovanni_id} ({response.status_code}): {_error_text(response)}"
        )

    def _result(self, job_url: str) -> pd.Series:
        """Wait for a job, download its CSV and return the area means by time."""
        delay, waited = _FIRST_POLL_SECONDS, 0.0
        while True:
            response = self._http().get(job_url, timeout=_REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            job = response.json()
            if job["status"] in _FINISHED:
                break
            if waited > _JOB_TIMEOUT_SECONDS:
                raise LiveAccessError(f"Giovanni job did not finish in time: {job_url}")
            self._sleep(delay)
            waited += delay
            delay = min(delay * 1.5, _MAX_POLL_SECONDS)
        if job["status"] != "successful":
            errors = job.get("errors") or [{}]
            message = errors[0].get("message") or job.get("message", "")
            raise LiveAccessError(f"Giovanni job {job['status']}: {message}")
        links = [link["href"] for link in job.get("links", []) if link.get("rel") == _DATA_LINK]
        if not links:
            raise LiveAccessError(f"Giovanni job returned no data: {job_url}")
        parts = [self._download_csv(link) for link in links]
        return pd.concat(parts).sort_index()

    def _download_csv(self, url: str) -> pd.Series:
        response = self._http().get(url, timeout=_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "giovanni.csv"
            path.write_bytes(response.content)
            # The header holds the fill value; the reader turns it into gaps.
            return read_time_series_csv(path)
