"""Data handling: common format, units, Parquet cache, CSV import, grid reduction."""

import numpy as np
import pandas as pd
import pytest

from conftest import make_series
from earth_trail_detective.application.ingest import build_series
from earth_trail_detective.domain.errors import (
    LiveAccessError,
    SeriesFormatError,
    UnitConversionError,
)
from earth_trail_detective.domain.models import BoundingBox
from earth_trail_detective.domain.series import COLUMNS, MonthlySeries
from earth_trail_detective.domain.units import convert
from earth_trail_detective.infrastructure.csv_import import read_time_series_csv
from earth_trail_detective.infrastructure.grid_reduction import area_mean
from earth_trail_detective.infrastructure.parquet_repository import ParquetSeriesRepository

# Hand-written sample in the layout of a Giovanni area-averaged CSV download.
GIOVANNI_SAMPLE = """Title:,"Time Series, Area-Averaged of SO2 Column Amount"
User Start Date:,2005-01-01T00:00:00Z
Fill Value (mean_OMSO2e_003_ColumnAmountSO2):,-9999

time,mean_OMSO2e_003_ColumnAmountSO2
2005-01-01,0.5
2005-01-02,1.5
2005-02-01,-9999
2005-03-01,2.0
"""


def test_common_format_round_trip():
    series = make_series(years=3)
    frame = series.to_frame()
    assert tuple(frame.columns) == COLUMNS  # spec 10.4
    restored = MonthlySeries.from_frame(frame)
    assert restored.meta == series.meta
    pd.testing.assert_series_equal(restored.values, series.values)


def test_series_marks_missing_months_and_rejects_bad_tables():
    values = pd.Series([1.0, 2.0], index=pd.to_datetime(["2020-01-15", "2020-04-15"]))
    series = MonthlySeries(values, make_series().meta)
    assert list(series.values.index.strftime("%Y-%m-%d")) == [
        "2020-01-01",
        "2020-02-01",
        "2020-03-01",
        "2020-04-01",
    ]
    assert series.values.isna().sum() == 2
    with pytest.raises(SeriesFormatError):
        MonthlySeries.from_frame(pd.DataFrame({"date": [], "value": []}))


def test_unit_conversions():
    index = pd.to_datetime(["2021-01-01", "2021-02-01"])  # 31 and 28 days
    flux = pd.Series([1e-12, 1e-12], index=index)
    monthly = convert(flux, "kg m-2 s-1", "mg m-2 month-1")
    assert monthly.iloc[0] == pytest.approx(1e-12 * 1e6 * 86_400 * 31)
    assert monthly.iloc[1] == pytest.approx(1e-12 * 1e6 * 86_400 * 28)
    assert convert(flux, "mm h-1", "mm month-1").iloc[0] == pytest.approx(1e-12 * 24 * 31)
    assert convert(flux, "kg m-2", "kg m-2") is flux
    with pytest.raises(UnitConversionError):
        convert(flux, "kg", "parsec")


def test_every_catalog_variable_has_a_unit_conversion(catalog):
    index = pd.to_datetime(["2021-01-01"])
    for variable in catalog.variables():
        convert(pd.Series([1.0], index=index), variable.source_unit, variable.unit)


def test_parquet_repository_round_trip(tmp_path, catalog):
    repository = ParquetSeriesRepository(tmp_path)
    variable, region = catalog.variable("so2_column_omi"), catalog.region("alps")
    assert repository.load(variable, region) is None
    series = make_series(years=2)
    repository.save(variable, region, series)
    pd.testing.assert_series_equal(repository.load(variable, region).values, series.values)


def test_csv_import_giovanni_layout(tmp_path, catalog):
    path = tmp_path / "giovanni.csv"
    path.write_text(GIOVANNI_SAMPLE, encoding="utf-8")
    raw = read_time_series_csv(path)
    assert len(raw) == 4 and np.isnan(raw.iloc[2])  # fill value became a gap
    series = build_series(catalog.variable("so2_column_omi"), catalog.region("alps"), raw)
    assert series.values.iloc[0] == pytest.approx(1.0)  # daily values -> monthly mean
    assert np.isnan(series.values.iloc[1])
    assert series.meta.unit == "DU" and series.meta.kind == "measured"


def test_csv_import_plain_table(tmp_path):
    path = tmp_path / "stats.csv"
    path.write_text("Date,Count,Mean\n2020-01-01,5,40.5\n2020-02-01,7,41.5\n", encoding="utf-8")
    raw = read_time_series_csv(path, value_column="Mean")
    assert list(raw) == [40.5, 41.5]
    with pytest.raises(SeriesFormatError):
        read_time_series_csv(path, value_column="Median")


def test_grid_reduction_sums_bins_and_weights_by_latitude():
    xr = pytest.importorskip("xarray")  # optional dependency (extra "live")
    dataset = xr.Dataset(
        {
            "BIN1": (("time", "lat", "lon"), np.array([[[1.0, 1.0], [3.0, 3.0], [9.0, 9.0]]])),
            "BIN2": (("time", "lat", "lon"), np.array([[[0.0, 0.0], [1.0, 1.0], [9.0, 9.0]]])),
        },
        coords={"time": [0], "lat": [0.0, 60.0, 80.0], "lon": [10.0, 11.0]},
    )
    box = BoundingBox(south=-5, north=65, west=9, east=12)  # excludes latitude 80
    # rows: 1 (weight 1) and 3 + 1 = 4 (weight 0.5)  ->  (1 + 2) / 1.5
    assert area_mean(dataset, ("BIN1", "BIN2"), box) == pytest.approx(2.0)
    with pytest.raises(LiveAccessError):
        area_mean(dataset, ("MISSING",), box)
    with pytest.raises(LiveAccessError):
        area_mean(dataset, ("BIN1",), BoundingBox(south=20, north=30, west=9, east=12))
