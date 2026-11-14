"""Input widgets shared by the student and the researcher form."""

from datetime import date

import streamlit as st

from earth_trail_detective.domain.models import Period

FIRST_YEAR = 1980  # start of MERRA-2, the longest record in the catalog


def period_picker(label: str, key: str, whole_label: str) -> Period:
    """A "use everything" checkbox plus a year range slider.

    Inside ``st.form`` widgets cannot react to each other, so the slider is
    always visible and only used when the checkbox is unticked.
    """
    this_year = date.today().year
    use_whole = st.checkbox(whole_label, value=True, key=f"{key}-whole")
    first, last = st.slider(
        f"{label} (only used if the box above is unticked)",
        FIRST_YEAR,
        this_year,
        (FIRST_YEAR, this_year),
        key=f"{key}-years",
    )
    return Period() if use_whole else Period(date(first, 1, 1), date(last, 12, 31))
