"""Entry point of the Streamlit app: page layout and control flow."""

import os

import streamlit as st

from earth_trail_detective import APP_NAME
from earth_trail_detective.application.cache_filler import FetchJob, requested_variables
from earth_trail_detective.application.options import AnalysisRequest
from earth_trail_detective.application.ports import Catalog
from earth_trail_detective.bootstrap import Container, build_container
from earth_trail_detective.config import FETCH_VARIABLE, TOKEN_VARIABLE, FetchPolicy
from earth_trail_detective.domain.errors import EarthTrailError
from earth_trail_detective.presentation.researcher_form import (
    CUSTOM_CATEGORY,
    render_researcher_form,
)
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


def _fill_cache(container: Container, request: AnalysisRequest, refresh: bool = False) -> None:
    """Fetch what the analysis needs from NASA and save it to the cache (ETD_FETCH).

    Custom bounding boxes are skipped: the cache holds catalog regions only.
    """
    filler = container.cache_filler()
    regions = [region for region in request.regions if region.category != CUSTOM_CATEGORY]
    plan = filler.plan(requested_variables(container.catalog, request), regions, refresh=refresh)
    if plan.is_empty:
        if refresh:
            st.info("Nothing to update: these series can only be imported by hand (CSV).")
        return
    label = f"Fetching {len(plan.jobs)} NASA product(s) for the cache"
    with st.status(f"{label} ...", expanded=True) as status:
        status.write(
            "The whole record is fetched once and saved. Daily OMI products take seconds; "
            "MERRA-2 (since 1980) about 10-15 minutes per region."
        )

        def announce(number: int, total: int, job: FetchJob) -> None:
            status.write(f"[{number}/{total}] {job.label} ...")

        outcomes = filler.run(plan, on_job=announce)
        failures = [outcome for outcome in outcomes if outcome.error]
        for outcome in failures:
            status.write(f"⚠️ {outcome.job.access.short_name} failed: {outcome.error}")
        saved = sum(len(outcome.saved) for outcome in outcomes)
        summary = f"Saved {saved} series to the cache"
        if failures:
            summary += f" – {len(failures)} product(s) failed"
        status.update(
            label=summary, state="error" if failures else "complete", expanded=bool(failures)
        )


def _run(container: Container, request: AnalysisRequest) -> None:
    """Execute a request and remember its result for the following reruns."""
    if not request.live and container.can_fetch:
        _fill_cache(container, request)
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


def _render_data_status(container: Container) -> None:
    """Sidebar note on where the data comes from (ETD_FETCH, token)."""
    policy = container.settings.fetch
    if policy is FetchPolicy.OFF:
        return
    if not container.has_token:
        st.sidebar.warning(
            f"{FETCH_VARIABLE}={policy.value} is set, but {TOKEN_VARIABLE} is missing – "
            "the app reads the offline cache only."
        )
        return
    note = "Missing series are fetched from NASA and saved to the cache."
    if policy is FetchPolicy.REFRESH:
        note += " Results can be updated from NASA."
    st.sidebar.caption(f"📡 {note}")


def _render_refresh_button(container: Container, request: AnalysisRequest) -> None:
    """ETD_FETCH=refresh: reload the series of the shown analysis from NASA."""
    if request.live or not container.can_fetch:
        return
    if container.settings.fetch is not FetchPolicy.REFRESH:
        return
    if st.button(
        "🔄 Update this analysis from NASA",
        help="Fetches the whole record of every product shown here again and replaces the "
        "cached series. MERRA-2 products take about 10-15 minutes per region.",
    ):
        _fill_cache(container, request, refresh=True)
        _run(container, request)
        st.rerun()


def main() -> None:
    """Draw the page. Streamlit calls this on every interaction."""
    st.set_page_config(page_title=APP_NAME, page_icon="🔎", layout="wide")
    try:
        container = _container()
    except ValueError as error:  # e.g. an invalid ETD_FETCH value
        st.error(f"Configuration error: {error}")
        st.stop()
    catalog = container.catalog

    st.title(f"🔎 {APP_NAME}")
    st.caption(
        "Follow a pollutant through the water cycle and test every step for a trend. "
        "A screening and learning tool – not for health warnings, forecasts or official decisions."
    )

    mode = st.sidebar.radio("Mode", [MODE_STUDENT, MODE_RESEARCHER])
    _render_data_status(container)
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
        shown_request, trails = st.session_state[OUTCOME_KEY]
        render_results(catalog, shown_request, trails)
        _render_refresh_button(container, shown_request)
