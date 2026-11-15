"""Closed vocabularies of the domain.

All enums are ``StrEnum`` so their values can be written to and read from
YAML, Parquet and CSV files without any extra mapping.
"""

from enum import StrEnum


class Step(StrEnum):
    """One stage of the trail (spec 10.1). The definition order is the trail order."""

    AIR = "air"
    CLOUD = "cloud"
    PRECIPITATION = "precipitation"
    GLACIER = "glacier"
    SOIL = "soil"
    RIVER = "river"


class DataKind(StrEnum):
    """How a value was obtained; shown on every card (spec 6.5)."""

    MEASURED = "measured"
    MODEL = "model"
    ESTIMATE = "estimate"


class EvidenceLabel(StrEnum):
    """Strength of the statistical evidence for a trend (spec 9)."""

    STRONG = "strong"
    WEAK = "weak"
    NONE = "no_evidence"


class TrendDirection(StrEnum):
    """Sign of the robust (Sen) slope."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    FLAT = "flat"


class GapStatus(StrEnum):
    """Why a substance has no trend card at a step (matrix 10.2)."""

    NO_RECORD = "no_record"  # no time series exists: "Trail ends here"
    OPTIONAL_GROUND = "optional_ground"  # only open ground data could continue the trail
    NOT_APPLICABLE = "not_applicable"  # the step makes no sense for this substance
    PENDING = "pending"  # listed in the spec matrix, variable not fixed yet


class MannKendallVariant(StrEnum):
    """Selectable Mann-Kendall tests (researcher mode)."""

    HAMED_RAO = "hamed_rao"
    YUE_WANG = "yue_wang"
    PRE_WHITENING = "pre_whitening"
    ORIGINAL = "original"


class ComparisonOutcome(StrEnum):
    """Result of comparing the trends of two regions."""

    OPPOSITE = "opposite"
    SAME = "same"
    INCONCLUSIVE = "inconclusive"
