"""Entry point of the Streamlit app: page layout and control flow."""

import os

import streamlit as st

from earth_trail_detective import APP_NAME
from earth_trail_detective.application.options import AnalysisRequest
from earth_trail_detective.application.ports import Catalog
from earth_trail_detective.bootstrap import Container, build_container
from earth_trail_detective.config import TOKEN_VARIABLE
from earth_trail_detective.domain.errors import EarthTrailError
from earth_trail_detective.presentation.researcher_form import render_researcher_form
from earth_trail_detective.presentation.result_view import render_results
from earth_trail_detective.presentation.student_form import render_student_form

MODE_STUDENT = "🎒 Student"
MODE_RESEARCHER = "🔬 Researcher"
OUTCOME_KEY = "outcome"  # session entry: (request, trails) of the last run


@st.cache_resource
def _container() -> Container:
    """Wire the application once per server process.

    Token precedence: shell environment, then ``.env``, then ``st.secrets``.
    """
    container = build_container()
    _export_token_from_secrets()
    return container


def _export_token_from_secrets() -> None:
    """Copy the Earthdata token from ``st.secrets`` to the environment.

    The token is read on the server only (environment variable, ``.env`` or
    secrets file) and is never asked for or shown in the browser (spec 14).
    """
    if os.environ.get(TOKEN_VARIABLE):
        return
    try:
        token = st.secrets.get(TOKEN_VARIABLE)
    except FileNotFoundError:  # no secrets file: stay offline
        return
    if token:
        os.environ[TOKEN_VARIABLE] = token


def _render_demo_picker(catalog: Catalog) -> AnalysisRequest | None:
    """Sidebar: start a prepared demo with two clicks."""
    st.sidebar.subheader("Prepared demos")
    demo = st.sidebar.selectbox(
        "Demo", catalog.demos(), format_func=lambda d: f"{d.id} · {d.title}"
    )
    st.sidebar.caption(demo.purpose)
    substance_id = st.sidebar.selectbox(
        "Substance", demo.substances, format_func=lambda s: catalog.substance(s).name
    )
    region_set = st.sidebar.selectbox(
        "Regions",
        demo.region_sets,
        format_func=lambda ids: "  ↔  ".join(catalog.region(i).name for i in ids),
    )
    if not st.sidebar.button("▶ Run demo"):
        return None
    return AnalysisRequest(
        regions=tuple(catalog.region(region_id) for region_id in region_set),
        substance_id=substance_id,
        demo_id=demo.id,
    )


def _run(container: Container, request: AnalysisRequest) -> None:
    """Execute a request and remember its result for the following reruns."""
    builder = (
        container.live_builder(request.options.period)
        if request.live
        else container.cache_builder()
    )
    try:
        with st.spinner("Following the trail ..."):
            st.session_state[OUTCOME_KEY] = (request, builder.run(request))
    except EarthTrailError as error:
        st.session_state.pop(OUTCOME_KEY, None)
        st.error(f"The analysis could not be completed: {error}")


def main() -> None:
    """Draw the page. Streamlit calls this on every interaction."""
    st.set_page_config(page_title=APP_NAME, page_icon="🔎", layout="wide")
    container = _container()
    catalog = container.catalog

    st.title(f"🔎 {APP_NAME}")
    st.caption(
        "Follow a pollutant through the water cycle and test every step for a trend. "
        "A screening and learning tool – not for health warnings, forecasts or official decisions."
    )

    mode = st.sidebar.radio("Mode", [MODE_STUDENT, MODE_RESEARCHER])
    demo_request = _render_demo_picker(catalog)

    with st.expander("Start a new analysis", expanded=OUTCOME_KEY not in st.session_state):
        if mode == MODE_STUDENT:
            form_request = render_student_form(catalog)
        else:
            form_request = render_researcher_form(catalog, container.has_token)

    request = demo_request or form_request
    if request is not None:
        _run(container, request)
    if OUTCOME_KEY in st.session_state:
        render_results(catalog, *st.session_state[OUTCOME_KEY])
