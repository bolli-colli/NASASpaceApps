"""Shared wording and number formatting for texts, reports and the UI."""

from earth_trail_detective.domain.enums import DataKind, EvidenceLabel, TrendDirection

EVIDENCE_TEXT = {
    EvidenceLabel.STRONG: "Strong evidence",
    EvidenceLabel.WEAK: "Weak evidence",
    EvidenceLabel.NONE: "No evidence",
}

KIND_TEXT = {
    DataKind.MEASURED: "measured",
    DataKind.MODEL: "model",
    DataKind.ESTIMATE: "estimate",
}

DIRECTION_TEXT = {
    TrendDirection.INCREASING: "increasing",
    TrendDirection.DECREASING: "decreasing",
    TrendDirection.FLAT: "flat",
}

_SMALLEST_PLAIN = 1e-3  # below this, scientific notation is easier to read
_LARGEST_PLAIN = 1e5
_SMALLEST_P = 0.001


def format_number(value: float, signed: bool = False) -> str:
    """Format with three significant digits, e.g. ``0.0123`` or ``1.20e-06``."""
    sign = "+" if signed else ""
    if value != 0 and not _SMALLEST_PLAIN <= abs(value) < _LARGEST_PLAIN:
        return f"{value:{sign}.2e}"
    return f"{value:{sign}.3g}"


def format_p(p_value: float) -> str:
    """Format a p-value; very small values are shown as ``< 0.001``."""
    return f"< {_SMALLEST_P}" if p_value < _SMALLEST_P else f"{p_value:.3f}"


def format_percent(value: float | None) -> str:
    """Format a percentage with sign, or ``n/a`` if it cannot be computed."""
    return "n/a" if value is None else f"{value:+.1f} %"
