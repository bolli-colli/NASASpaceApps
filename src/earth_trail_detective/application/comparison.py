"""Use cases: compare two regions (M8) and check a result against a reference (M12)."""

from earth_trail_detective.application.formatting import DIRECTION_TEXT
from earth_trail_detective.domain.enums import ComparisonOutcome, EvidenceLabel, TrendDirection
from earth_trail_detective.domain.models import ReferenceTrend
from earth_trail_detective.domain.results import Comparison, TrendResult


def _has_evidence(result: TrendResult) -> bool:
    """True if a trend is at least "Weak" and has a direction."""
    return result.evidence is not EvidenceLabel.NONE and result.direction is not TrendDirection.FLAT


def compare_trends(
    first: TrendResult, second: TrendResult, first_name: str, second_name: str
) -> Comparison:
    """Compare two independently tested regions.

    "Opposite trends" is only stated if both trends are at least "Weak" (spec 9).
    """
    if not (_has_evidence(first) and _has_evidence(second)):
        return Comparison(
            ComparisonOutcome.INCONCLUSIVE,
            "No clear comparison: at least one region shows no evidence of a trend.",
        )
    first_direction = DIRECTION_TEXT[first.direction]
    second_direction = DIRECTION_TEXT[second.direction]
    if first.direction is second.direction:
        return Comparison(
            ComparisonOutcome.SAME,
            f"Same direction: {first_name} and {second_name} are both {first_direction}.",
        )
    return Comparison(
        ComparisonOutcome.OPPOSITE,
        f"Opposite trends: {first_name} is {first_direction} "
        f"while {second_name} is {second_direction}.",
    )


def check_reference(result: TrendResult, reference: ReferenceTrend) -> dict[str, bool]:
    """Acceptance criteria of the validation case (spec 13.2), one flag each."""
    overlaps = (
        result.ci_low_per_year <= reference.high_per_year
        and result.ci_high_per_year >= reference.low_per_year
    )
    return {
        "Trend is significant and positive": (
            result.effective_p < result.alpha and result.direction is TrendDirection.INCREASING
        ),
        "Evidence label is Strong": result.evidence is EvidenceLabel.STRONG,
        "Confidence interval overlaps the reference value": overlaps,
        "Sen's slope and OLS point the same way": result.slopes_agree,
    }
