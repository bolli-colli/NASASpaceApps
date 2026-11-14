"""Results of an analysis: trend numbers, trail cards and comparisons."""

from dataclasses import dataclass, replace

import pandas as pd

from earth_trail_detective.domain.enums import (
    ComparisonOutcome,
    EvidenceLabel,
    Step,
    TrendDirection,
)
from earth_trail_detective.domain.models import Region, Substance, TrailGap, VariableSpec
from earth_trail_detective.domain.series import MonthlySeries
from earth_trail_detective.domain.statistics.evidence import classify_evidence

YEARS_PER_DECADE = 10


@dataclass(frozen=True, eq=False)
class TrendResult:
    """Everything the statistics core found out about one series."""

    start: pd.Timestamp  # first month with data
    end: pd.Timestamp  # last month with data
    years: float  # record length
    missing_fraction: float  # share of months without data inside the record
    mean_value: float  # mean of the original (not deseasonalised) values
    sen_slope_per_year: float
    ols_slope_per_year: float
    ci_low_per_year: float
    ci_high_per_year: float
    mk_p: float  # p-value of the selected Mann-Kendall variant
    mk_p_classic: float  # classic Mann-Kendall, for comparison
    alpha: float  # significance level
    used_anomalies: bool
    analysed: pd.Series  # the values that were tested (anomalies or raw)
    sen_line: pd.Series
    ols_band: pd.DataFrame  # columns fit / lower / upper
    warnings: tuple[str, ...] = ()
    mk_p_adjusted: float | None = None  # after Benjamini-Hochberg, if applied

    @property
    def effective_p(self) -> float:
        """The p-value that decides significance (adjusted if available)."""
        return self.mk_p if self.mk_p_adjusted is None else self.mk_p_adjusted

    @property
    def evidence(self) -> EvidenceLabel:
        """Evidence label according to spec 9."""
        return classify_evidence(
            self.effective_p, self.ci_low_per_year, self.ci_high_per_year, self.years, self.alpha
        )

    @property
    def direction(self) -> TrendDirection:
        """Direction of the robust (Sen) slope."""
        if self.sen_slope_per_year > 0:
            return TrendDirection.INCREASING
        if self.sen_slope_per_year < 0:
            return TrendDirection.DECREASING
        return TrendDirection.FLAT

    @property
    def slopes_agree(self) -> bool:
        """True if Sen's slope and the OLS slope point the same way."""
        return self.sen_slope_per_year * self.ols_slope_per_year > 0

    @property
    def slope_per_decade(self) -> float:
        """Sen's slope per decade."""
        return self.sen_slope_per_year * YEARS_PER_DECADE

    @property
    def ols_slope_per_decade(self) -> float:
        """OLS slope per decade."""
        return self.ols_slope_per_year * YEARS_PER_DECADE

    @property
    def ci_per_decade(self) -> tuple[float, float]:
        """OLS confidence interval per decade."""
        return (
            self.ci_low_per_year * YEARS_PER_DECADE,
            self.ci_high_per_year * YEARS_PER_DECADE,
        )

    @property
    def percent_of_mean_per_decade(self) -> float | None:
        """Change per decade in % of the mean; ``None`` if the mean is zero."""
        if self.mean_value == 0 or pd.isna(self.mean_value):
            return None
        return 100 * self.slope_per_decade / abs(self.mean_value)

    def with_adjusted_p(self, adjusted_p: float) -> "TrendResult":
        """Copy of the result that carries a multiple-testing adjusted p-value."""
        return replace(self, mk_p_adjusted=adjusted_p)


@dataclass(frozen=True, eq=False)
class TrendCard:
    """A step with data: series plus trend result."""

    step: Step
    variable: VariableSpec
    series: MonthlySeries
    result: TrendResult


@dataclass(frozen=True)
class TrailEndCard:
    """A step without any time series: "Trail ends here" (requirement M9)."""

    step: Step
    gap: TrailGap


@dataclass(frozen=True)
class UnavailableCard:
    """A catalog variable that could not be analysed (not cached, too short...)."""

    step: Step
    variable: VariableSpec
    reason: str


Card = TrendCard | TrailEndCard | UnavailableCard


@dataclass(frozen=True)
class Trail:
    """All cards of one region, ordered along the trail."""

    region: Region
    cards: tuple[Card, ...]
    substance: Substance | None = None  # None for a free choice of variables

    @property
    def trend_cards(self) -> tuple[TrendCard, ...]:
        """Only the cards that carry a trend result."""
        return tuple(card for card in self.cards if isinstance(card, TrendCard))


@dataclass(frozen=True)
class Comparison:
    """Plain-language verdict of a two-region comparison (requirement M8)."""

    outcome: ComparisonOutcome
    text: str
