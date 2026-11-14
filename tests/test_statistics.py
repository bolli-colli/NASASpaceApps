"""Statistics core: the four synthetic acceptance tests of spec 13.2 (a–d) and helpers."""

import numpy as np
import pandas as pd
import pytest

from conftest import make_series
from earth_trail_detective.application.options import AnalysisOptions
from earth_trail_detective.application.trend_analysis import TrendAnalyzer
from earth_trail_detective.domain.enums import EvidenceLabel, MannKendallVariant, TrendDirection
from earth_trail_detective.domain.errors import InsufficientDataError
from earth_trail_detective.domain.models import Period
from earth_trail_detective.domain.statistics.anomalies import deseasonalize, monthly_climatology
from earth_trail_detective.domain.statistics.area_mean import cos_lat_weighted_mean
from earth_trail_detective.domain.statistics.evidence import classify_evidence
from earth_trail_detective.domain.statistics.mann_kendall import mann_kendall_p
from earth_trail_detective.domain.statistics.multiple_testing import benjamini_hochberg

ALPHA = 0.05
analyzer = TrendAnalyzer()


def test_a_known_trend_is_recovered():
    """(a) Series with known trend + noise: the slope is hit."""
    result = analyzer.analyze(
        make_series(years=30, slope_per_year=0.5, noise=1.0), AnalysisOptions()
    )
    assert result.sen_slope_per_year == pytest.approx(0.5, abs=0.05)
    assert result.ols_slope_per_year == pytest.approx(0.5, abs=0.05)
    assert result.ci_low_per_year < 0.5 < result.ci_high_per_year
    assert result.direction is TrendDirection.INCREASING
    assert result.evidence is EvidenceLabel.STRONG
    assert result.slope_per_decade == pytest.approx(10 * result.sen_slope_per_year)


def test_b_pure_noise_is_not_significant_in_about_95_percent():
    """(b) Pure noise: about 95 % of 1000 runs are "not significant"."""
    runs = 1000
    not_significant = sum(
        mann_kendall_p(make_series(years=10, seed=seed).values, MannKendallVariant.HAMED_RAO)
        >= ALPHA
        for seed in range(runs)
    )
    assert 0.93 <= not_significant / runs <= 0.97


def test_c_hamed_rao_prevents_spurious_significance():
    """(c) Autocorrelated noise: Hamed-Rao removes a large part of the false alarms.

    Measured with these settings: classic about 35 %, Hamed-Rao about 18 %.
    The correction reduces spurious significance; it does not remove it fully.
    """
    runs = 200
    series = [make_series(years=20, ar1=0.7, seed=seed).values for seed in range(runs)]
    classic = sum(mann_kendall_p(s, MannKendallVariant.ORIGINAL) < ALPHA for s in series)
    corrected = sum(mann_kendall_p(s, MannKendallVariant.HAMED_RAO) < ALPHA for s in series)
    assert classic / runs > 0.25  # the classic test is fooled often
    assert corrected < 0.6 * classic


def test_d_deseasonalising_narrows_the_confidence_interval():
    """(d) Removing the seasonal cycle shrinks the confidence interval."""
    series = make_series(years=20, slope_per_year=0.1, noise=0.5, seasonal_amplitude=5.0)
    raw = analyzer.analyze(series, AnalysisOptions(use_anomalies=False))
    anomalies = analyzer.analyze(series, AnalysisOptions(use_anomalies=True))
    width = lambda r: r.ci_high_per_year - r.ci_low_per_year  # noqa: E731
    assert width(anomalies) < width(raw) / 2


def test_climatology_and_anomalies():
    series = make_series(years=10, noise=0.0, seasonal_amplitude=3.0).values
    climatology = monthly_climatology(series)
    assert list(climatology.index) == list(range(1, 13))
    assert np.allclose(deseasonalize(series), 0.0)
    # A climatology period without data for a month yields gaps, not zeros.
    partial = deseasonalize(series, Period(pd.Timestamp("2000-01-01"), pd.Timestamp("2000-06-30")))
    assert partial.isna().sum() == len(series) / 2


def test_gaps_are_reported_not_interpolated():
    series = make_series(years=20, slope_per_year=0.3)
    values = series.values.copy()
    values.iloc[24:72] = np.nan  # four years missing = 20 %
    result = analyzer.analyze(type(series)(values, series.meta), AnalysisOptions())
    assert result.missing_fraction == pytest.approx(0.2)
    assert any("missing" in warning for warning in result.warnings)
    assert result.sen_slope_per_year == pytest.approx(0.3, abs=0.05)  # real time axis is used


def test_short_records_warn_and_too_short_records_fail():
    result = analyzer.analyze(make_series(years=6, slope_per_year=1.0), AnalysisOptions())
    assert any("Short record" in warning for warning in result.warnings)
    assert result.evidence is EvidenceLabel.WEAK  # never "Strong" below 15 years
    with pytest.raises(InsufficientDataError):
        analyzer.analyze(make_series(years=1), AnalysisOptions())


def test_period_option_crops_the_record():
    options = AnalysisOptions(period=Period(pd.Timestamp("2005-01-01"), pd.Timestamp("2014-12-31")))
    result = analyzer.analyze(make_series(years=20), options)
    assert (result.start, result.end) == (pd.Timestamp("2005-01-01"), pd.Timestamp("2014-12-01"))
    assert result.years == pytest.approx(10)


@pytest.mark.parametrize(
    ("mk_p", "ci", "years", "expected"),
    [
        (0.01, (0.1, 0.3), 20, EvidenceLabel.STRONG),
        (0.01, (0.1, 0.3), 12, EvidenceLabel.WEAK),  # both criteria, 10–15 years
        (0.01, (-0.1, 0.3), 20, EvidenceLabel.WEAK),  # only Mann-Kendall
        (0.20, (0.1, 0.3), 20, EvidenceLabel.WEAK),  # only confidence interval
        (0.20, (-0.1, 0.3), 20, EvidenceLabel.NONE),
        (float("nan"), (-0.1, 0.3), 20, EvidenceLabel.NONE),
    ],
)
def test_evidence_label_table(mk_p, ci, years, expected):
    assert classify_evidence(mk_p, ci[0], ci[1], years, ALPHA) is expected


def test_benjamini_hochberg():
    assert benjamini_hochberg([]) == []
    assert benjamini_hochberg([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.04, 0.04])


def test_cos_lat_weighted_mean():
    latitudes = np.array([0.0, 60.0])  # weights 1 and 0.5
    grid = np.array([[1.0, 1.0], [4.0, 4.0]])
    assert cos_lat_weighted_mean(grid, latitudes) == pytest.approx(2.0)
    grid[1, 1] = np.nan  # missing cells are ignored
    assert cos_lat_weighted_mean(grid, latitudes) == pytest.approx((1 + 1 + 0.5 * 4) / 2.5)
    assert np.isnan(cos_lat_weighted_mean(np.full((2, 2), np.nan), latitudes))
