"""Student mode: the guided form with four questions (requirement M2, spec 7)."""

from dataclasses import dataclass

import streamlit as st

from earth_trail_detective.application.options import AnalysisOptions, AnalysisRequest
from earth_trail_detective.application.ports import Catalog
from earth_trail_detective.domain.models import Region
from earth_trail_detective.presentation.form_widgets import period_picker


@dataclass(frozen=True)
class _Place:
    """One answer to "Where?": a demo pair or a single region."""

    label: str
    regions: tuple[Region, ...]


def _places(catalog: Catalog) -> list[_Place]:
    """Demo region pairs first, then every single region with its category."""
    places: dict[tuple[str, ...], _Place] = {}
    for demo in catalog.demos():
        for region_set in demo.region_sets:
            if len(region_set) > 1:
                regions = tuple(catalog.region(region_id) for region_id in region_set)
                label = "Compare: " + "  ↔  ".join(region.name for region in regions)
                places.setdefault(region_set, _Place(label, regions))
    singles = [
        _Place(f"{region.category}: {region.name}", (region,)) for region in catalog.regions()
    ]
    return [*places.values(), *singles]


def render_student_form(catalog: Catalog) -> AnalysisRequest | None:
    """Show the form; returns a request when the user submits it."""
    substances = [s for s in catalog.substances() if s.student_visible]
    steps = catalog.steps()
    with st.form("student-form"):
        substance = st.radio(
            "1 · What do you want to follow?",
            substances,
            format_func=lambda s: f"{s.icon} {s.name}",
            captions=[s.description for s in substances],
        )
        place = st.selectbox("2 · Where?", _places(catalog), format_func=lambda p: p.label)
        # ``None`` stands for the whole trail.
        step = st.selectbox(
            "3 · Which part of the water's journey?",
            [None, *steps],
            format_func=lambda info: (
                "🧭 The whole trail" if info is None else f"{info.icon} {info.label}"
            ),
        )
        st.markdown("4 · Which period?")
        period = period_picker("Years", "student-period", "The longest period available")
        submitted = st.form_submit_button("🔎 Follow the trail", type="primary")
    if not submitted:
        return None
    return AnalysisRequest(
        regions=place.regions,
        options=AnalysisOptions(period=period),
        substance_id=substance.id,
        steps=None if step is None else (step.step,),
    )
