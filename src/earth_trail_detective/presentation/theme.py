"""Visual vocabulary of the app.

Colours come from the colour-blind safe Okabe-Ito palette, and every colour
is paired with a symbol and a word, so nothing depends on colour alone
(spec 14).
"""

from earth_trail_detective.application.formatting import (
    DIRECTION_TEXT,
    EVIDENCE_TEXT,
    KIND_TEXT,
)
from earth_trail_detective.domain.enums import (
    DataKind,
    EvidenceLabel,
    GapStatus,
    TrendDirection,
)

# Okabe-Ito colours
BLUE = "#0072B2"
VERMILLION = "#D55E00"
GREEN = "#009E73"
GREY = "#666666"

DATA_COLOUR = BLUE
OLS_COLOUR = VERMILLION
SEN_COLOUR = GREEN
BAND_COLOUR = "rgba(213, 94, 0, 0.2)"  # translucent vermillion

_DIRECTION_ARROW = {
    TrendDirection.INCREASING: "▲",
    TrendDirection.DECREASING: "▼",
    TrendDirection.FLAT: "▶",
}

# Streamlit badge colours; the symbol repeats the information without colour.
_EVIDENCE_BADGE = {
    EvidenceLabel.STRONG: ("blue", "●●"),
    EvidenceLabel.WEAK: ("orange", "●○"),
    EvidenceLabel.NONE: ("gray", "○○"),
}

# Legend of spec 10.2: ✅ measured, 🟡 model or estimate
_KIND_SYMBOL = {
    DataKind.MEASURED: "✅",
    DataKind.MODEL: "🟡",
    DataKind.ESTIMATE: "🟡",
}

GAP_TITLE = {
    GapStatus.NO_RECORD: "🛑 Trail ends here",
    GapStatus.OPTIONAL_GROUND: "🛑 Trail ends here – only ground data could continue it",
    GapStatus.PENDING: "🚧 Not in the catalog yet",
}


def direction_label(direction: TrendDirection) -> str:
    """Arrow plus word, e.g. ``▼ decreasing``."""
    return f"{_DIRECTION_ARROW[direction]} {DIRECTION_TEXT[direction]}"


def evidence_badge(label: EvidenceLabel) -> str:
    """Markdown badge for an evidence label."""
    colour, symbol = _EVIDENCE_BADGE[label]
    return f":{colour}-badge[{symbol} {EVIDENCE_TEXT[label]}]"


def kind_label(kind: DataKind | str) -> str:
    """Symbol plus word for the data kind, e.g. ``🟡 model``."""
    kind = DataKind(kind)
    return f"{_KIND_SYMBOL[kind]} {KIND_TEXT[kind]}"
