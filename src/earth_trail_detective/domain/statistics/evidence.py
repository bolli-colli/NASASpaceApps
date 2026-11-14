"""Evidence label (spec 9, table "Evidenzlabel").

Two criteria are combined:
  1. the Mann-Kendall test is significant (p < alpha)
  2. the OLS confidence interval of the slope excludes zero

Strong       both criteria and a record of at least 15 years
Weak         only one criterion, or both criteria on a record under 15 years
No evidence  neither criterion

The spec does not define the label for records under 10 years. They are
capped at "Weak" here and always carry a short-record warning.
"""

from earth_trail_detective.domain.enums import EvidenceLabel

MIN_YEARS_WITHOUT_WARNING = 10  # below: warning "record too short"
MIN_YEARS_FOR_STRONG = 15  # recommended record length


def classify_evidence(
    mk_p: float, ci_low: float, ci_high: float, years: float, alpha: float
) -> EvidenceLabel:
    """Derive the evidence label of one trend result."""
    # A NaN p-value compares False and therefore counts as "not significant".
    mk_significant = mk_p < alpha
    ci_excludes_zero = ci_low > 0 or ci_high < 0
    if mk_significant and ci_excludes_zero:
        long_enough = years >= MIN_YEARS_FOR_STRONG
        return EvidenceLabel.STRONG if long_enough else EvidenceLabel.WEAK
    if mk_significant or ci_excludes_zero:
        return EvidenceLabel.WEAK
    return EvidenceLabel.NONE
