"""Plotly figures. The numbers come ready-made from the ``TrendResult``."""

import plotly.graph_objects as go

from earth_trail_detective.domain.results import TrendCard
from earth_trail_detective.presentation import theme

CHART_HEIGHT = 300


def trend_figure(card: TrendCard) -> go.Figure:
    """Time series with OLS line, its confidence band (S9) and Sen's slope."""
    result = card.result
    band = result.ols_band
    confidence = f"{1 - result.alpha:.0%}"
    figure = go.Figure()
    # Confidence band: lower edge first, then the upper edge filled down to it.
    figure.add_trace(
        go.Scatter(
            x=band.index, y=band["lower"], line={"width": 0}, showlegend=False, hoverinfo="skip"
        )
    )
    figure.add_trace(
        go.Scatter(
            x=band.index,
            y=band["upper"],
            line={"width": 0},
            fill="tonexty",
            fillcolor=theme.BAND_COLOUR,
            name=f"{confidence} confidence band",
            hoverinfo="skip",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=result.analysed.index,
            y=result.analysed,
            mode="lines",
            line={"color": theme.DATA_COLOUR, "width": 1},
            name="Monthly anomaly" if result.used_anomalies else "Monthly value",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=band.index,
            y=band["fit"],
            mode="lines",
            line={"color": theme.OLS_COLOUR, "width": 2},
            name="Trend (OLS)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=result.sen_line.index,
            y=result.sen_line,
            mode="lines",
            line={"color": theme.SEN_COLOUR, "width": 2, "dash": "dash"},
            name="Trend (Sen's slope)",
        )
    )
    prefix = "Anomaly, " if result.used_anomalies else ""
    figure.update_layout(
        height=CHART_HEIGHT,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        yaxis_title=f"{prefix}{card.variable.unit}",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0},
    )
    return figure
