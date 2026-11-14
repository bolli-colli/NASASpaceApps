"""Use case: run the statistics pipeline of spec 9 on one series."""

from earth_trail_detective.application.formatting import format_p
from earth_trail_detective.application.options import AnalysisOptions
from earth_trail_detective.domain.enums import MannKendallVariant
from earth_trail_detective.domain.errors import InsufficientDataError
from earth_trail_detective.domain.results import TrendResult
from earth_trail_detective.domain.series import MonthlySeries
from earth_trail_detective.domain.statistics.anomalies import deseasonalize
from earth_trail_detective.domain.statistics.evidence import (
    MIN_YEARS_FOR_STRONG,
    MIN_YEARS_WITHOUT_WARNING,
)
from earth_trail_detective.domain.statistics.mann_kendall import mann_kendall_p
from earth_trail_detective.domain.statistics.trend import MONTHS_PER_YEAR, ols_trend, sen_slope

# Two full years are the minimum for a climatology and a slope to exist.
MIN_MONTHS = 2 * MONTHS_PER_YEAR
MAX_MISSING_FRACTION = 0.10  # warn above 10 % gaps (spec 9)


class TrendAnalyzer:
    """Pipeline: crop -> anomalies -> Sen / OLS -> Mann-Kendall -> warnings."""

    def analyze(self, series: MonthlySeries, options: AnalysisOptions) -> TrendResult:
        """Analyse one series; raises ``InsufficientDataError`` if it is too short."""
        raw = options.period.crop(series.values)
        present = raw.dropna()
        if len(present) < MIN_MONTHS:
            raise InsufficientDataError(
                f"Only {len(present)} months with data; at least {MIN_MONTHS} are needed."
            )
        # The record runs from the first to the last month that holds data.
        raw = raw.loc[present.index[0] : present.index[-1]]
        analysed = deseasonalize(raw, options.climatology) if options.use_anomalies else raw
        if analysed.count() < MIN_MONTHS:
            raise InsufficientDataError(
                "Too few months remain after removing the seasonal cycle; "
                "check the climatology period."
            )

        sen = sen_slope(analysed)
        ols = ols_trend(analysed, options.alpha)
        mk_p = mann_kendall_p(analysed, options.mk_variant)
        mk_p_classic = mann_kendall_p(analysed, MannKendallVariant.ORIGINAL)
        years = len(raw) / MONTHS_PER_YEAR
        missing_fraction = float(raw.isna().mean())

        return TrendResult(
            start=present.index[0],
            end=present.index[-1],
            years=years,
            missing_fraction=missing_fraction,
            mean_value=float(present.mean()),
            sen_slope_per_year=sen.slope_per_year,
            ols_slope_per_year=ols.slope_per_year,
            ci_low_per_year=ols.ci_low_per_year,
            ci_high_per_year=ols.ci_high_per_year,
            mk_p=mk_p,
            mk_p_classic=mk_p_classic,
            alpha=options.alpha,
            used_anomalies=options.use_anomalies,
            analysed=analysed,
            sen_line=sen.line,
            ols_band=ols.band,
            warnings=self._warnings(years, missing_fraction, mk_p, mk_p_classic, options.alpha),
        )

    @staticmethod
    def _warnings(
        years: float, missing_fraction: float, mk_p: float, mk_p_classic: float, alpha: float
    ) -> tuple[str, ...]:
        """Collect the data-quality hints required by spec 9."""
        warnings = []
        if years < MIN_YEARS_WITHOUT_WARNING:
            warnings.append(
                f"Short record ({years:.1f} years): below {MIN_YEARS_WITHOUT_WARNING} years "
                "a trend test is unreliable."
            )
        elif years < MIN_YEARS_FOR_STRONG:
            warnings.append(
                f"Record of {years:.1f} years: {MIN_YEARS_FOR_STRONG} years or more "
                "are recommended."
            )
        if missing_fraction > MAX_MISSING_FRACTION:
            warnings.append(
                f"{missing_fraction:.0%} of the months are missing (gaps are not filled)."
            )
        if (mk_p < alpha) != (mk_p_classic < alpha):
            warnings.append(
                "The classic Mann-Kendall test alone would call this significant "
                f"(p-values: {format_p(mk_p_classic)} classic vs. {format_p(mk_p)} corrected): "
                "the values depend on their predecessors (autocorrelation)."
            )
        return tuple(warnings)
