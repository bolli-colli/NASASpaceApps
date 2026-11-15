"""Input objects of the use cases, independent of any user interface."""

from dataclasses import dataclass, field

from earth_trail_detective.domain.enums import MannKendallVariant, Step
from earth_trail_detective.domain.models import Period, Region

DEFAULT_ALPHA = 0.05  # significance level 5 % (spec 9)


@dataclass(frozen=True)
class AnalysisOptions:
    """Statistical settings; the defaults are the student-mode settings."""

    period: Period = field(default_factory=Period)  # default: longest available record
    climatology: Period = field(default_factory=Period)  # default: whole record
    mk_variant: MannKendallVariant = MannKendallVariant.HAMED_RAO
    alpha: float = DEFAULT_ALPHA
    use_anomalies: bool = True
    benjamini_hochberg: bool = False


@dataclass(frozen=True)
class AnalysisRequest:
    """What the user asked for – produced by a form or a demo button.

    Either ``substance_id`` (follow a substance along the trail) or
    ``variable_ids`` (free choice of catalog variables) is set.
    """

    regions: tuple[Region, ...]  # one region, or two for a comparison
    options: AnalysisOptions = field(default_factory=AnalysisOptions)
    substance_id: str | None = None
    steps: tuple[Step, ...] | None = None  # None: the whole trail
    variable_ids: tuple[str, ...] = ()
    live: bool = False  # True: fetch from NASA instead of the offline cache
    demo_id: str | None = None  # set when the request comes from a demo case
