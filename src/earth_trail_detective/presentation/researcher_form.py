"""Researcher mode: the expert form (requirement M3, spec 7)."""

import streamlit as st

from earth_trail_detective.application.options import (
    DEFAULT_ALPHA,
    AnalysisOptions,
    AnalysisRequest,
)
from earth_trail_detective.application.ports import Catalog
from earth_trail_detective.domain.enums import MannKendallVariant
from earth_trail_detective.domain.models import BoundingBox, Region
from earth_trail_detective.presentation.form_widgets import period_picker

ALPHA_CHOICES = (0.01, DEFAULT_ALPHA, 0.10)
CUSTOM_CATEGORY = "Custom"  # category of regions typed in by the user
CUSTOM_BOX = "custom"  # sentinel for "use the numbers typed below"
SOURCE_CACHE = "Offline cache"
SOURCE_LIVE = "Live from NASA Earthdata (own token)"

_VARIANT_LABEL = {
    MannKendallVariant.HAMED_RAO: "Hamed-Rao (autocorrelation corrected, default)",
    MannKendallVariant.YUE_WANG: "Yue-Wang (autocorrelation corrected)",
    MannKendallVariant.PRE_WHITENING: "Pre-whitening",
    MannKendallVariant.ORIGINAL: "Classic (assumes independent values)",
}


def _region_picker(catalog: Catalog, title: str, key: str, optional: bool) -> Region | None:
    """Pick a catalog region or type a custom bounding box (live mode only)."""
    choices = [*catalog.regions(), CUSTOM_BOX]
    if optional:
        choices.insert(0, None)
    choice = st.selectbox(
        title,
        choices,
        key=f"{key}-region",
        format_func=lambda c: (
            "– none –"
            if c is None
            else "Custom bounding box (live only)"
            if c == CUSTOM_BOX
            else f"{c.name} ({c.bbox.label})"
        ),
    )
    with st.expander(f"Custom bounding box for {title.lower()}"):
        columns = st.columns(4)
        south = columns[0].number_input("South", -90.0, 90.0, 37.0, key=f"{key}-south")
        north = columns[1].number_input("North", -90.0, 90.0, 42.0, key=f"{key}-north")
        west = columns[2].number_input("West", -180.0, 180.0, -88.0, key=f"{key}-west")
        east = columns[3].number_input("East", -180.0, 180.0, -80.0, key=f"{key}-east")
    if choice != CUSTOM_BOX:
        return choice
    try:
        box = BoundingBox(south, north, west, east)
    except ValueError as error:
        st.error(f"{title}: {error}")
        return None
    return Region(
        id=f"custom_{key}", name=f"Custom box {box.label}", category=CUSTOM_CATEGORY, bbox=box
    )


def render_researcher_form(catalog: Catalog, has_token: bool) -> AnalysisRequest | None:
    """Show the form; returns a request when the user submits valid input."""
    with st.form("researcher-form"):
        variables = st.multiselect(
            "Variables",
            catalog.variables(),
            format_func=lambda v: f"{v.name} · {v.product} · {v.step.value}",
        )
        source = st.radio(
            "Data source",
            [SOURCE_CACHE, SOURCE_LIVE],
            disabled=not has_token,
            help="Live access needs the environment variable EARTHDATA_TOKEN (see README). "
            "It reads one file per month and can take minutes - choose a short period.",
        )
        left, right = st.columns(2)
        with left:
            region_a = _region_picker(catalog, "Region A", "a", optional=False)
        with right:
            region_b = _region_picker(catalog, "Region B", "b", optional=True)

        st.selectbox("Aggregation", ["monthly"], disabled=True)
        period = period_picker("Years", "researcher-period", "Whole record")
        climatology = period_picker(
            "Climatology years", "researcher-climatology", "Climatology over the whole record"
        )

        st.markdown("**Statistics**")
        variant = st.selectbox(
            "Mann-Kendall variant", list(MannKendallVariant), format_func=_VARIANT_LABEL.get
        )
        alpha = st.selectbox(
            "Significance level", ALPHA_CHOICES, index=ALPHA_CHOICES.index(DEFAULT_ALPHA)
        )
        use_anomalies = st.checkbox("Remove the seasonal cycle (anomalies)", value=True)
        benjamini_hochberg = st.checkbox("Benjamini-Hochberg correction across all cards")
        submitted = st.form_submit_button("🔬 Analyse", type="primary")

    if not submitted:
        return None
    live = source == SOURCE_LIVE
    regions = tuple(region for region in (region_a, region_b) if region is not None)
    if not variables or region_a is None:
        st.error("Choose at least one variable and a valid region A.")
        return None
    if not live and any(region.category == CUSTOM_CATEGORY for region in regions):
        st.error("Custom bounding boxes need live access; the cache holds fixed regions only.")
        return None
    return AnalysisRequest(
        regions=regions,
        options=AnalysisOptions(
            period=period,
            climatology=climatology,
            mk_variant=variant,
            alpha=alpha,
            use_anomalies=use_anomalies,
            benjamini_hochberg=benjamini_hochberg,
        ),
        variable_ids=tuple(variable.id for variable in variables),
        live=live,
    )
