"""Shared test helpers: synthetic series with known properties (spec 13.2)."""

import numpy as np
import pandas as pd
import pytest

from earth_trail_detective.config import PROJECT_ROOT
from earth_trail_detective.domain.series import MonthlySeries, SeriesMeta
from earth_trail_detective.infrastructure.yaml_catalog import YamlCatalog

TEST_META = SeriesMeta(
    unit="unit",
    variable="TEST",
    product="TEST",
    version="1",
    region="Test region",
    substance="test",
    step="air",
    kind="model",
    source_url="https://example.org",
)


def make_series(
    years: int = 20,
    slope_per_year: float = 0.0,
    noise: float = 1.0,
    seasonal_amplitude: float = 0.0,
    ar1: float = 0.0,
    seed: int = 0,
    start: str = "2000-01",
) -> MonthlySeries:
    """Monthly series = trend + seasonal cycle + (optionally autocorrelated) noise."""
    random = np.random.default_rng(seed)
    count = years * 12
    time = np.arange(count) / 12
    innovations = random.normal(0, noise, count)
    errors = np.empty(count)
    errors[0] = innovations[0]
    for i in range(1, count):  # AR(1) process; ar1 = 0 gives white noise
        errors[i] = ar1 * errors[i - 1] + innovations[i]
    values = slope_per_year * time + seasonal_amplitude * np.sin(2 * np.pi * time) + errors
    index = pd.date_range(start, periods=count, freq="MS")
    return MonthlySeries(pd.Series(values, index=index), TEST_META)


@pytest.fixture(scope="session")
def catalog() -> YamlCatalog:
    """The real catalog of the repository."""
    return YamlCatalog(PROJECT_ROOT / "catalog")
