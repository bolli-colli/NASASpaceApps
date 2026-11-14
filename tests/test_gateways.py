"""Gateways to NASA services: everything that can be tested without a login."""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from conftest import make_series
from earth_trail_detective.application.sources import RoutingGateway
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import Period
from earth_trail_detective.infrastructure.earthaccess_gateway import EarthaccessGateway
from earth_trail_detective.infrastructure.gridded_gateway import AreaMeanCollector
from earth_trail_detective.infrastructure.harmony_gateway import HarmonyGateway, yearly_chunks
from earth_trail_detective.infrastructure.hoss_reader import load_grid


class FakeGateway:
    """Gateway double that serves one provider and records what it was asked for."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self.calls: list[list[str]] = []

    def supports(self, variable):
        return variable.access is not None and variable.access.provider == self.provider

    def fetch(self, variables, regions, period):
        self.calls.append([variable.id for variable in variables])
        return [make_series(years=2) for _ in variables for _ in regions]


def test_catalog_products_are_assigned_to_the_right_gateway(catalog):
    harmony, earthaccess = HarmonyGateway(), EarthaccessGateway()
    for variable_id in ("so2_column_omi", "aerosol_index_omi", "no2_column_omi"):
        variable = catalog.variable(variable_id)
        assert harmony.supports(variable) and not earthaccess.supports(variable)
        assert variable.access.group.startswith("HDFEOS/GRIDS/")
    # The monthly model products are subset by Harmony as well.
    for variable_id in ("so4_column_merra2", "snow_water_gldas", "precipitation_imerg"):
        assert harmony.supports(catalog.variable(variable_id))
    assert earthaccess.supports(catalog.variable("co2_column"))  # no Harmony service
    assert not harmony.supports(catalog.variable("snow_albedo_modis"))  # CSV import only


def test_routing_gateway_splits_by_provider_and_keeps_the_order(catalog):
    first, second = FakeGateway("earthaccess"), FakeGateway("harmony")
    router = RoutingGateway([first, second])
    variables = [catalog.variable(i) for i in ("so2_column_omi", "co2_column", "no2_column_omi")]
    regions = [catalog.region("alps"), catalog.region("sahara")]
    result = router.fetch(variables, regions, Period())
    assert len(result) == len(variables) * len(regions)
    assert first.calls == [["co2_column"]]  # one call per gateway
    assert second.calls == [["so2_column_omi", "no2_column_omi"]]
    assert not router.supports(catalog.variable("snow_albedo_modis"))
    with pytest.raises(LiveAccessError):
        router.fetch([catalog.variable("snow_albedo_modis")], regions, Period())


def test_yearly_chunks_cover_the_period_without_gaps():
    chunks = list(yearly_chunks(date(2004, 10, 1), date(2006, 3, 15)))
    assert chunks == [
        (datetime(2004, 10, 1), datetime(2004, 12, 31, 23, 59, 59)),
        (datetime(2005, 1, 1), datetime(2005, 12, 31, 23, 59, 59)),
        (datetime(2006, 1, 1), datetime(2006, 3, 15, 23, 59, 59)),
    ]


def test_area_mean_collector_sorts_by_time(catalog):
    collector = AreaMeanCollector()
    variable, region = catalog.variable("soot_column"), catalog.region("alps")
    collector.add(variable, region, pd.Timestamp("2020-02-01"), 2.0)
    collector.add(variable, region, pd.Timestamp("2020-01-01"), 1.0)
    assert list(collector.series()[("soot_column", "alps")]) == [1.0, 2.0]


def test_hoss_reader_finds_variables_in_nested_groups(tmp_path):
    """A hand-built file with an HDF-EOS-like layout (not a real Harmony result)."""
    xr = pytest.importorskip("xarray")
    grid = xr.Dataset(
        {"ColumnAmountSO2": (("YDim", "XDim"), np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]))}
    )
    coordinates = xr.Dataset(
        {"Latitude": ("YDim", [10.0, 11.0]), "Longitude": ("XDim", [1.0, 2.0, 3.0])}
    )
    tree = xr.DataTree.from_dict(
        {"/": coordinates, "/HDFEOS/GRIDS/OMI_Total_Column_Amount_SO2/Data_Fields": grid}
    )
    path = tmp_path / "subset.nc4"
    tree.to_netcdf(path, engine="h5netcdf")

    loaded = load_grid(path, ("ColumnAmountSO2",))
    assert loaded["ColumnAmountSO2"].dims == ("lat", "lon")
    assert list(loaded["lat"]) == [10.0, 11.0] and loaded["ColumnAmountSO2"].shape == (2, 3)
    with pytest.raises(LiveAccessError, match="Unexpected layout"):
        load_grid(path, ("NotThere",))
