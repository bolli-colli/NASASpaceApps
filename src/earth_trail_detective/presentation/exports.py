"""Download buttons: CSV and methods report (requirement S6).

PNG export is built into every chart: the camera button of the Plotly toolbar
saves the plot as PNG in the browser, offline and without extra software.
"""

from collections.abc import Sequence
from datetime import datetime

import pandas as pd
import streamlit as st

from earth_trail_detective.application.methods_report import build_methods_report
from earth_trail_detective.application.options import AnalysisOptions
from earth_trail_detective.domain.results import Trail

ANALYSED_COLUMN = "analysed_value"  # the tested value (anomaly unless switched off)


def series_table(trails: Sequence[Trail]) -> pd.DataFrame:
    """All analysed series in the common data format, plus the tested values."""
    frames = [
        card.series.to_frame().assign(
            **{ANALYSED_COLUMN: card.result.analysed.reindex(card.series.values.index).to_numpy()}
        )
        for trail in trails
        for card in trail.trend_cards
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def render_exports(trails: Sequence[Trail], options: AnalysisOptions) -> None:
    """Show the export section below the results."""
    st.subheader("Export")
    left, right = st.columns(2)
    left.download_button(
        "⬇️ Data (CSV)",
        series_table(trails).to_csv(index=False),
        file_name="earth_trail_detective_data.csv",
        mime="text/csv",
    )
    right.download_button(
        "⬇️ Methods report (Markdown)",
        build_methods_report(trails, options, datetime.now()),
        file_name="earth_trail_detective_methods.md",
        mime="text/markdown",
    )
    st.caption("PNG: use the camera button in the toolbar of each chart.")
