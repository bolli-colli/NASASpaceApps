"""Giovanni area-average gateway, tested with a fake HTTP session (no login, no network)."""

from datetime import date

import numpy as np
import pytest

from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import Period
from earth_trail_detective.infrastructure import giovanni_gateway
from earth_trail_detective.infrastructure.giovanni_gateway import (
    GiovanniGateway,
    averaging_parameters,
)

# Same layout as a real result (research/variable-automation, OMAERUVd, Ohio Valley).
# Real long series mix two date styles (with and without "T"), so this one does too.
CSV = """User Start Date:,2020-01-01T00:00:00.000Z
User End Date:,2020-02-29T23:59:59.000Z
User Bounding Box:,"-88, 37, -80, 42"
Fill Value:,-1.2676506002282294e+30
,
time,mean_OMAERUVd_003_UVAerosolIndex
2020-01-01 00:00:00,1.0
2020-01-02T00:00:00,3.0
2020-01-03T00:00:00,-1.2676506002282294e+30
2020-02-01T00:00:00,0.5
"""
JOB = "/jobs/abc"
DATA = "https://harmony.example/results/out.csv"


class FakeResponse:
    def __init__(self, status=200, json=None, text="", headers=None):
        self.status_code = status
        self._json = json
        self.text = text
        self.content = text.encode()
        self.headers = headers or {}

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        if self._json is None:
            raise ValueError("no JSON")
        return self._json

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Answers the quota, submit, job and download calls in that order."""

    def __init__(self, quota=0.1, submit=None, statuses=("running", "successful")):
        self.quota = quota
        self.submit = submit or FakeResponse(303, headers={"Location": JOB})
        self.statuses = list(statuses)
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, dict(params or [])))
        if url == giovanni_gateway.QUOTA_URL:
            return FakeResponse(json={"quota": self.quota})
        if "ogc-api-coverages" in url:
            return self.submit
        if url.endswith(JOB):
            status = self.statuses.pop(0)
            links = [{"rel": "data", "href": DATA}] if status == "successful" else []
            return FakeResponse(json={"status": status, "links": links, "errors": []})
        if url == DATA:
            return FakeResponse(text=CSV)
        raise AssertionError(f"unexpected URL {url}")


@pytest.fixture(autouse=True)
def _no_cmr(monkeypatch):
    """The collection id lookup is a public CMR call - replace it."""
    monkeypatch.setattr(giovanni_gateway, "find_collection_id", lambda *_: "C1-TEST")


def _fetch(catalog, session):
    gateway = GiovanniGateway(session=session, sleep=lambda _: None)
    variable, region = catalog.variable("aerosol_index_omi"), catalog.region("ohio_valley")
    return gateway.fetch([variable], [region], Period(date(2020, 1, 1), date(2020, 2, 29)))[0]


def test_request_asks_for_an_area_average_csv(catalog):
    bbox = catalog.region("ohio_valley").bbox
    params = averaging_parameters(
        "OMAERUVd_003_UVAerosolIndex", bbox, date(2020, 1, 1), date(2020, 2, 29)
    )
    assert ("average", "area") in params and ("format", "text/csv") in params
    assert ("variable", "OMAERUVd_003_UVAerosolIndex") in params
    subsets = [value for key, value in params if key == "subset"]
    assert subsets == [
        f"lat({bbox.south}:{bbox.north})",
        f"lon({bbox.west}:{bbox.east})",
        'time("2020-01-01T00:00:00Z":"2020-02-29T23:59:59Z")',
    ]


def test_daily_csv_becomes_monthly_means_without_fill_values(catalog):
    session = FakeSession()
    series = _fetch(catalog, session).values.dropna()
    # January: mean of 1 and 3 (the fill value is a gap, not a number); February: 0.5
    assert series.iloc[0] == pytest.approx(2.0)
    assert series.iloc[1] == pytest.approx(0.5)
    assert np.isfinite(series).all()
    assert any("C1-TEST/ogc-api-coverages" in url for url, _ in session.calls)


def test_quota_near_the_limit_stops_before_submitting(catalog):
    session = FakeSession(quota=0.97)
    with pytest.raises(LiveAccessError, match="quota"):
        _fetch(catalog, session)
    assert not any("ogc-api-coverages" in url for url, _ in session.calls)


def test_rejected_variable_reports_harmonys_reason(catalog):
    rejected = FakeResponse(400, json={"description": "Bad or missing variable input"})
    with pytest.raises(LiveAccessError, match="Bad or missing variable"):
        _fetch(catalog, FakeSession(submit=rejected))


def test_failed_job_is_reported(catalog):
    with pytest.raises(LiveAccessError, match="failed"):
        _fetch(catalog, FakeSession(statuses=("running", "failed")))
