"""Filling the cache from NASA (CacheFiller) and the ETD_FETCH setting – no network."""

import pytest

from conftest import make_series
from earth_trail_detective.application.cache_filler import CacheFiller, requested_variables
from earth_trail_detective.application.options import AnalysisRequest
from earth_trail_detective.config import FETCH_VARIABLE, FetchPolicy, Settings
from earth_trail_detective.domain.enums import Step
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.infrastructure.parquet_repository import ParquetSeriesRepository


class FakeGateway:
    """Serves every scripted product; can be told to fail for one product."""

    def __init__(self, failing: str | None = None) -> None:
        self.failing = failing
        self.calls: list[tuple[str, list[str], list[str]]] = []

    def supports(self, variable):
        return variable.access is not None and variable.access.provider != "csv"

    def fetch(self, variables, regions, period):
        short_name = variables[0].access.short_name
        self.calls.append((short_name, [v.id for v in variables], [r.id for r in regions]))
        if short_name == self.failing:
            raise LiveAccessError("NASA is down")
        return [make_series(years=3) for _ in variables for _ in regions]


@pytest.fixture
def store(tmp_path):
    return ParquetSeriesRepository(tmp_path)


def test_plan_groups_missing_series_by_product_and_skips_cached(catalog, store):
    alps, sahara = catalog.region("alps"), catalog.region("sahara")
    so4, soot = catalog.variable("so4_column_merra2"), catalog.variable("soot_column")
    store.save(so4, alps, make_series(years=3))  # already cached for one region
    filler = CacheFiller(catalog, store, FakeGateway())

    plan = filler.plan([so4, soot], [alps, sahara])

    assert len(plan.jobs) == 1  # both are MERRA-2 M2TMNXAER: one fetch
    job = plan.jobs[0]
    assert job.access.short_name == "M2TMNXAER"
    assert {v.id for v in job.variables} == {"so4_column_merra2", "soot_column"}
    assert {r.id for r in job.regions} == {"alps", "sahara"}  # soot is missing in both

    store.save(soot, alps, make_series(years=3))
    store.save(soot, sahara, make_series(years=3))
    store.save(so4, sahara, make_series(years=3))
    assert filler.plan([so4, soot], [alps, sahara]).is_empty
    assert not filler.plan([so4, soot], [alps, sahara], refresh=True).is_empty


def test_derived_variables_are_replaced_by_their_inputs(catalog, store):
    filler = CacheFiller(catalog, store, FakeGateway())
    plan = filler.plan([catalog.variable("sulfur_in_precipitation")], [catalog.region("alps")])
    fetched = {v.id for job in plan.jobs for v in job.variables}
    assert fetched == {"sulfur_wet_deposition", "precipitation_merra2"}


def test_hand_imported_products_are_listed_not_fetched(catalog, store):
    filler = CacheFiller(catalog, store, FakeGateway())
    plan = filler.plan([catalog.variable("snow_albedo_modis")], [catalog.region("alps")])
    assert plan.is_empty
    assert [v.id for v in plan.manual] == ["snow_albedo_modis"]


def test_skip_products(catalog, store):
    filler = CacheFiller(catalog, store, FakeGateway())
    variables = [catalog.variable("so2_column_omi"), catalog.variable("soot_column")]
    plan = filler.plan(variables, [catalog.region("alps")], skip_products={"OMSO2e"})
    assert [job.access.short_name for job in plan.jobs] == ["M2TMNXAER"]


def test_run_saves_each_product_and_goes_on_after_a_failure(catalog, store):
    alps = catalog.region("alps")
    variables = [catalog.variable("so2_column_omi"), catalog.variable("soot_column")]
    gateway = FakeGateway(failing="OMSO2e")
    filler = CacheFiller(catalog, store, gateway)
    announced = []

    outcomes = filler.run(
        filler.plan(variables, [alps]), on_job=lambda n, total, job: announced.append((n, total))
    )

    assert announced == [(1, 2), (2, 2)]
    by_product = {outcome.job.access.short_name: outcome for outcome in outcomes}
    assert by_product["OMSO2e"].error == "NASA is down" and not by_product["OMSO2e"].saved
    assert by_product["M2TMNXAER"].saved == (("soot_column", "alps", 36),)
    assert store.load(catalog.variable("soot_column"), alps) is not None
    assert store.load(catalog.variable("so2_column_omi"), alps) is None


def test_requested_variables_follow_the_trail_or_the_free_choice(catalog):
    alps = catalog.region("alps")
    trail = requested_variables(
        catalog, AnalysisRequest(regions=(alps,), substance_id="sulfur", steps=(Step.AIR,))
    )
    assert trail and all(v.step is Step.AIR and "sulfur" in v.substances for v in trail)
    free = requested_variables(
        catalog, AnalysisRequest(regions=(alps,), variable_ids=("soot_column",))
    )
    assert [v.id for v in free] == ["soot_column"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, FetchPolicy.OFF),
        ("", FetchPolicy.OFF),
        ("missing", FetchPolicy.MISSING),
        (" Refresh ", FetchPolicy.REFRESH),
        ("off", FetchPolicy.OFF),
    ],
)
def test_fetch_setting(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv(FETCH_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(FETCH_VARIABLE, value)
    assert Settings.from_environment().fetch is expected


def test_invalid_fetch_setting_is_rejected(monkeypatch):
    monkeypatch.setenv(FETCH_VARIABLE, "yes")
    with pytest.raises(ValueError, match="off, missing, refresh"):
        Settings.from_environment()


def test_missing_message_depends_on_how_a_product_is_obtained(catalog, store):
    assert "ETD_FETCH" in store.explain_missing(catalog.variable("soot_column"))
    manual = store.explain_missing(catalog.variable("snow_albedo_modis"))
    assert "import_csv.py" in manual and "ETD_FETCH" not in manual
