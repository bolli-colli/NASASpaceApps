"""Use cases: catalog rules, trail building, comparison, validation, texts."""

from datetime import datetime

import pytest

from conftest import make_series
from earth_trail_detective.application.comparison import check_reference, compare_trends
from earth_trail_detective.application.methods_report import build_methods_report
from earth_trail_detective.application.narrative import LONGER_RECORD_NOTE, describe_trend
from earth_trail_detective.application.options import AnalysisOptions, AnalysisRequest
from earth_trail_detective.application.sources import DerivedSeriesSource
from earth_trail_detective.application.trail import TrailBuilder
from earth_trail_detective.application.trend_analysis import TrendAnalyzer
from earth_trail_detective.domain.enums import ComparisonOutcome, GapStatus, Step
from earth_trail_detective.domain.models import ReferenceTrend
from earth_trail_detective.domain.results import TrailEndCard, TrendCard, UnavailableCard
from earth_trail_detective.domain.series import MonthlySeries, SeriesMeta

analyzer = TrendAnalyzer()


class FakeSource:
    """In-memory series source: a rising series for every non-excluded variable."""

    def __init__(self, missing: set[str] = frozenset(), slope: float = 0.5) -> None:
        self._missing = missing
        self._slope = slope

    def load(self, variable, region):
        if variable.id in self._missing:
            return None
        values = make_series(years=25, slope_per_year=self._slope).values + 100
        return MonthlySeries(values, SeriesMeta.describe(variable, region))

    def explain_missing(self, variable):
        return "not available in the test"


def _builder(catalog, **source_options) -> TrailBuilder:
    return TrailBuilder(
        catalog, DerivedSeriesSource(FakeSource(**source_options), catalog), analyzer
    )


# --- catalog -------------------------------------------------------------------------


def test_catalog_contains_the_must_variables_of_spec_10_3(catalog):
    names = {name for variable in catalog.variables() for name in variable.source_variables}
    must = {"ColumnAmountSO2", "SO4CMASS", "SO4SMASS", "SO2CMASS", "SUPSO4AQ", "SUWT001",
            "SUDP004", "BCCMASS", "BCSMASS", "BCWT002", "BCDP001", "DUCMASS", "DUSMASS",
            "DUWT005", "DUDP001", "Snow_Albedo_Daily_Tile", "RUNOFF", "SNOMAS_GL",
            "PRECTOTCORR", "PRECSNO", "precipitation", "SWE_inst", "Snowf_tavg", "Qsm_acc",
            "SoilMoi0_10cm_inst", "SoilMoi100_200cm_inst", "Qs_acc", "Qsb_acc"}  # fmt: skip
    assert must <= names


def test_every_matrix_cell_is_a_variable_or_a_documented_gap(catalog):
    """Honesty rule (spec 13.2): no substance x step cell may silently vanish."""
    for substance in catalog.substances():
        for step in Step:
            gap = catalog.gap(substance.id, step)
            assert catalog.variables_for(substance.id, step) or gap is not None
            if gap is not None and gap.status is not GapStatus.NOT_APPLICABLE:
                assert gap.reason and gap.reference_url.startswith("https://")


@pytest.mark.parametrize("substance_id", ["sulfur", "soot", "dust"])
def test_trail_has_four_trend_steps_and_trail_end_cards(catalog, substance_id):
    """Success criterion 3: at least 4 steps as trend cards, the rest "Trail ends here"."""
    trail = _builder(catalog).build_trail(substance_id, catalog.region("alps"), AnalysisOptions())
    assert len({card.step for card in trail.trend_cards}) >= 4
    end_steps = {card.step for card in trail.cards if isinstance(card, TrailEndCard)}
    assert end_steps == {Step.SOIL, Step.RIVER}
    assert [card.step for card in trail.cards] == sorted(
        (card.step for card in trail.cards), key=list(Step).index
    )


def test_single_step_missing_data_and_derived_variables(catalog):
    region = catalog.region("alps")
    builder = _builder(catalog, missing={"sulfur_dry_deposition"})
    trail = builder.build_trail("sulfur", region, AnalysisOptions(), steps=(Step.PRECIPITATION,))
    cards = {card.variable.id: card for card in trail.cards}
    assert {card.step for card in trail.cards} == {Step.PRECIPITATION}
    assert isinstance(cards["sulfur_dry_deposition"], UnavailableCard)
    # Derived estimate (S7): wet deposition / precipitation keeps its catalog metadata.
    derived = cards["sulfur_in_precipitation"]
    assert isinstance(derived, TrendCard)
    assert (derived.series.meta.kind, derived.series.meta.unit) == ("estimate", "mg L-1")
    assert derived.series.values.iloc[0] == pytest.approx(1.0, abs=0.1)
    # A derived value is unavailable as soon as one input is missing.
    glacier = builder.build_trail("sulfur", region, AnalysisOptions(), steps=(Step.GLACIER,))
    assert isinstance(glacier.cards[0], UnavailableCard)


def test_request_runs_per_region_and_benjamini_hochberg_adjusts(catalog):
    request = AnalysisRequest(
        regions=(catalog.region("alps"), catalog.region("central_himalaya")),
        options=AnalysisOptions(benjamini_hochberg=True),
        variable_ids=("soot_column", "dust_column"),
    )
    trails = _builder(catalog).run(request)
    assert [trail.region.id for trail in trails] == ["alps", "central_himalaya"]
    assert all(trail.substance is None and len(trail.trend_cards) == 2 for trail in trails)
    for card in trails[0].trend_cards:
        assert card.result.mk_p_adjusted is not None
        assert card.result.effective_p >= card.result.mk_p


# --- comparison, validation, texts ---------------------------------------------------


def _result(slope: float, noise: float = 1.0):
    return analyzer.analyze(
        make_series(years=25, slope_per_year=slope, noise=noise), AnalysisOptions()
    )


def test_opposite_trends_only_with_evidence_on_both_sides():
    up, down, flat = _result(0.5), _result(-0.5), _result(0.0)
    assert compare_trends(up, down, "A", "B").outcome is ComparisonOutcome.OPPOSITE
    assert compare_trends(up, up, "A", "B").outcome is ComparisonOutcome.SAME
    assert compare_trends(up, flat, "A", "B").outcome is ComparisonOutcome.INCONCLUSIVE


def test_validation_acceptance_logic_on_a_co2_like_series():
    """Logic of spec 13.2 on synthetic data (the real CO₂ check needs the cached series)."""
    series = make_series(years=20, slope_per_year=2.2, noise=0.3, seasonal_amplitude=3.0)
    result = analyzer.analyze(series, AnalysisOptions())
    reference = ReferenceTrend(1.8, 2.7, "ppm", "test", confirmed=False)
    assert all(check_reference(result, reference).values())
    wrong = ReferenceTrend(5.0, 6.0, "ppm", "test", confirmed=False)
    assert not check_reference(result, wrong)["Confidence interval overlaps the reference value"]


def test_plain_text_and_methods_report(catalog):
    region = catalog.region("alps")
    trail = _builder(catalog, slope=0.0).build_trail("soot", region, AnalysisOptions())
    card = trail.trend_cards[0]
    text = describe_trend(card, region.name)
    for part in ("**What?**", "**Where?**", "**How strong?**", "**Significant?**"):
        assert part in text
    assert "model" in text  # the data kind is always named (M11)
    assert LONGER_RECORD_NOTE in text  # shown for "No evidence"
    report = build_methods_report([trail], AnalysisOptions(), datetime(2026, 11, 14))
    assert card.variable.product in report and card.series.meta.source_url in report
    assert "no time series" in report  # trail-end cards are part of the report
