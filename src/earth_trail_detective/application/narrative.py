"""Plain-language result of a trend card (requirement M11)."""

from earth_trail_detective.application.formatting import (
    DIRECTION_TEXT,
    EVIDENCE_TEXT,
    KIND_TEXT,
    format_number,
    format_p,
    format_percent,
)
from earth_trail_detective.domain.enums import EvidenceLabel
from earth_trail_detective.domain.results import TrendCard

CAUSATION_NOTE = (
    "Correlation is not causation: a trend shows that something changed, not why it changed."
)
LONGER_RECORD_NOTE = "A longer record might make it significant."

_SIGNIFICANCE_ANSWER = {
    EvidenceLabel.STRONG: "Yes",
    EvidenceLabel.WEAK: "Partly",
    EvidenceLabel.NONE: "No",
}


def describe_trend(card: TrendCard, region_name: str) -> str:
    """Answer "What, Where, How strong, Significant?" as Markdown."""
    variable, result = card.variable, card.result
    low, high = result.ci_per_decade
    confidence = f"{1 - result.alpha:.0%}"
    significance = (
        f"{_SIGNIFICANCE_ANSWER[result.evidence]} – {EVIDENCE_TEXT[result.evidence].lower()} "
        f"(Mann-Kendall p-value: {format_p(result.effective_p)})."
    )
    if result.evidence is EvidenceLabel.NONE:
        significance += f" {LONGER_RECORD_NOTE}"
    return "\n\n".join(
        [
            f"**What?** {variable.name} ({KIND_TEXT[variable.kind]}, {card.series.meta.product}).",
            f"**Where?** {region_name}, {result.start:%b %Y} to {result.end:%b %Y}.",
            f"**How strong?** {DIRECTION_TEXT[result.direction].capitalize()}: "
            f"{format_number(result.slope_per_decade, signed=True)} {variable.unit} per decade "
            f"({format_percent(result.percent_of_mean_per_decade)} of the mean), "
            f"{confidence} confidence interval {format_number(low, signed=True)} "
            f"to {format_number(high, signed=True)}.",
            f"**Significant?** {significance}",
        ]
    )
