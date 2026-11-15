"""Result page: trail cards per region, side by side for two regions (M8, M9, M11)."""

from collections.abc import Sequence

import streamlit as st

from earth_trail_detective.application.comparison import check_reference, compare_trends
from earth_trail_detective.application.formatting import format_number, format_p, format_percent
from earth_trail_detective.application.narrative import CAUSATION_NOTE, describe_trend
from earth_trail_detective.application.options import AnalysisRequest
from earth_trail_detective.application.ports import Catalog
from earth_trail_detective.domain.enums import ComparisonOutcome, Step
from earth_trail_detective.domain.models import DemoCase, ReferenceTrend, Region
from earth_trail_detective.domain.results import (
    Card,
    Trail,
    TrailEndCard,
    TrendCard,
    UnavailableCard,
)
from earth_trail_detective.presentation import theme
from earth_trail_detective.presentation.charts import trend_figure
from earth_trail_detective.presentation.exports import render_exports

SYNTHETIC_WARNING = (
    "⚠️ ARTIFICIAL DATA: these series are random development data (product 'SYNTHETIC'), "
    "not NASA data. The results say nothing about the real world."
)
PNG_SCALE = 2  # export charts at double resolution


def _render_trend_card(card: TrendCard, region: Region, reference: ReferenceTrend | None) -> None:
    """Trend card: labels, key numbers, chart, plain text and source."""
    variable, result, meta = card.variable, card.result, card.series.meta
    st.markdown(f"**{variable.name}**")
    st.markdown(
        f"{theme.direction_label(result.direction)} &nbsp; {theme.evidence_badge(result.evidence)}"
        f" &nbsp; {theme.kind_label(meta.kind)}"
    )
    low, high = result.ci_per_decade
    numbers = st.columns(3)
    numbers[0].metric(
        f"Change per decade ({variable.unit})",
        format_number(result.slope_per_decade, signed=True),
        format_percent(result.percent_of_mean_per_decade) + " of mean",
        delta_color="off",
    )
    numbers[1].metric("p-value", format_p(result.effective_p))
    numbers[2].metric(
        f"{1 - result.alpha:.0%} interval",
        f"{format_number(low, signed=True)} … {format_number(high, signed=True)}",
    )
    st.plotly_chart(
        trend_figure(card),
        key=f"chart-{region.id}-{variable.id}",
        config={
            "displaylogo": False,
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"{variable.id}_{region.id}",
                "scale": PNG_SCALE,
            },
        },
    )
    st.markdown(describe_trend(card, region.name))
    for warning in (*result.warnings, *variable.caveats):
        st.caption(f"⚠️ {warning}")
    if reference is not None:
        _render_reference_check(card, reference)
    with st.expander("What is this?"):
        st.write(variable.definition)
    st.caption(
        f"{meta.product} · version {meta.version} · {meta.variable} · {meta.unit} · "
        f"{theme.kind_label(meta.kind)} · [source]({meta.source_url})"
    )


def _render_reference_check(card: TrendCard, reference: ReferenceTrend) -> None:
    """Validation case: compare the result with the published trend (M12)."""
    status = "" if reference.confirmed else " (placeholder, not yet confirmed)"
    st.markdown(
        f"**Check against the known trend:** {reference.low_per_year} to "
        f"{reference.high_per_year} {reference.unit} per year{status}"
    )
    for criterion, passed in check_reference(card.result, reference).items():
        st.markdown(f"{'✔️ passed' if passed else '✖️ failed'} – {criterion}")
    st.caption(f"Reference: {reference.source}")


def _render_trail_end(card: TrailEndCard) -> None:
    """Honest card for a step without any time series (M9)."""
    st.markdown(f"**{theme.GAP_TITLE[card.gap.status]}**")
    st.write(card.gap.reason)
    if card.gap.reference_url:
        st.caption(f"Read more: [{card.gap.reference_label}]({card.gap.reference_url})")


def _render_unavailable(card: UnavailableCard) -> None:
    """Compact note for a catalog variable that could not be analysed."""
    st.markdown(f"**{card.variable.name}**")
    st.caption(f"➖ No result: {card.reason}")


def _render_card(card: Card, region: Region, reference: ReferenceTrend | None) -> None:
    """Draw one card inside a bordered box."""
    with st.container(border=True):
        if isinstance(card, TrendCard):
            _render_trend_card(card, region, reference)
        elif isinstance(card, TrailEndCard):
            _render_trail_end(card)
        else:
            _render_unavailable(card)


def _render_comparison(cards: Sequence[Card], trails: Sequence[Trail]) -> None:
    """Plain-language verdict below a pair of trend cards (M8)."""
    if len(cards) != 2 or not all(isinstance(card, TrendCard) for card in cards):
        return
    comparison = compare_trends(
        cards[0].result, cards[1].result, trails[0].region.name, trails[1].region.name
    )
    show = st.success if comparison.outcome is ComparisonOutcome.OPPOSITE else st.info
    show(f"⚖️ {comparison.text}")


def _demo(catalog: Catalog, request: AnalysisRequest) -> DemoCase | None:
    """The demo case a request was started from, if any."""
    return next((demo for demo in catalog.demos() if demo.id == request.demo_id), None)


def render_results(catalog: Catalog, request: AnalysisRequest, trails: Sequence[Trail]) -> None:
    """Render the complete result of one analysis run."""
    if any(card.series.is_synthetic for trail in trails for card in trail.trend_cards):
        st.error(SYNTHETIC_WARNING)

    demo = _demo(catalog, request)
    substance = trails[0].substance
    st.header(f"{substance.icon} {substance.name}" if substance else "Selected variables")
    if demo is not None:
        st.subheader(demo.title)
        st.write(demo.explanation)
    st.caption(
        "Each step is tested on its own. Steps are shown next to each other, "
        "but the tool does not prove that one causes the next."
    )

    if not any(trail.cards for trail in trails):
        st.info("This step is not part of the trail of this substance.")
        return

    # Region names as column headers
    for column, trail in zip(st.columns(len(trails)), trails, strict=True):
        column.subheader(f"📍 {trail.region.name}")
        column.caption(trail.region.bbox.label)

    step_labels = {info.step: f"{info.icon} {info.label}" for info in catalog.steps()}
    reference = demo.reference if demo else None
    current_step: Step | None = None
    # All trails are built from the same catalog entries, so their cards line up.
    for row in zip(*(trail.cards for trail in trails), strict=True):
        if row[0].step is not current_step:
            current_step = row[0].step
            st.markdown(f"### {step_labels[current_step]}")
        for column, card, trail in zip(st.columns(len(trails)), row, trails, strict=True):
            with column:
                _render_card(card, trail.region, reference)
        _render_comparison(row, trails)

    st.info(f"💡 {CAUSATION_NOTE}")
    render_exports(trails, request.options)
