"""Methods report as Markdown (requirement S6): all parameters and sources."""

from collections.abc import Sequence
from datetime import datetime

from earth_trail_detective import APP_NAME, __version__
from earth_trail_detective.application.formatting import (
    DIRECTION_TEXT,
    EVIDENCE_TEXT,
    KIND_TEXT,
    format_number,
    format_p,
    format_percent,
)
from earth_trail_detective.application.narrative import CAUSATION_NOTE
from earth_trail_detective.application.options import AnalysisOptions
from earth_trail_detective.domain.results import (
    Trail,
    TrailEndCard,
    TrendCard,
    UnavailableCard,
)


def _settings_section(options: AnalysisOptions) -> list[str]:
    """List every statistical parameter of the run."""
    return [
        "## Settings",
        "",
        f"- Period: {options.period.label}",
        "- Aggregation: monthly area means, weighted with cos(latitude)",
        f"- Seasonal cycle removed (anomalies): {'yes' if options.use_anomalies else 'no'}",
        f"- Climatology period: {options.climatology.label}",
        f"- Mann-Kendall variant: {options.mk_variant.value}",
        f"- Significance level: {options.alpha}",
        f"- Benjamini-Hochberg correction: {'yes' if options.benjamini_hochberg else 'no'}",
        "- Trend estimators: Sen's slope; OLS with confidence interval",
        "- Missing values: marked, not interpolated",
        "",
    ]


def _trend_section(card: TrendCard) -> list[str]:
    """Describe one analysed variable with its numbers and its source."""
    variable, result = card.variable, card.result
    low, high = result.ci_per_decade
    lines = [
        f"### {variable.name}",
        "",
        f"- Product / version / variable: {card.series.meta.product} / "
        f"{card.series.meta.version} / {card.series.meta.variable}",
        f"- Data kind: {KIND_TEXT[variable.kind]}; unit: {variable.unit}",
        f"- Record: {result.start:%Y-%m} to {result.end:%Y-%m} ({result.years:.1f} years, "
        f"{result.missing_fraction:.0%} missing)",
        f"- Sen's slope: {format_number(result.slope_per_decade, signed=True)} per decade "
        f"({format_percent(result.percent_of_mean_per_decade)} of the mean), "
        f"{DIRECTION_TEXT[result.direction]}",
        f"- OLS slope: {format_number(result.ols_slope_per_decade, signed=True)} per decade, "
        f"confidence interval {format_number(low, signed=True)} to "
        f"{format_number(high, signed=True)}",
        f"- Mann-Kendall p: {format_p(result.mk_p)} (classic: {format_p(result.mk_p_classic)})",
    ]
    if result.mk_p_adjusted is not None:
        lines.append(f"- Benjamini-Hochberg adjusted p: {format_p(result.mk_p_adjusted)}")
    lines.append(f"- Evidence: {EVIDENCE_TEXT[result.evidence]}")
    lines.extend(f"- Warning: {warning}" for warning in (*result.warnings, *variable.caveats))
    lines.extend([f"- Source: {card.series.meta.source_url}", ""])
    return lines


def _trail_section(trail: Trail) -> list[str]:
    """Describe all cards of one region."""
    lines = [f"## Region: {trail.region.name} ({trail.region.bbox.label})", ""]
    for card in trail.cards:
        if isinstance(card, TrendCard):
            lines.extend(_trend_section(card))
        elif isinstance(card, TrailEndCard):
            lines.extend(
                [
                    f"### {card.step.value}: no time series",
                    "",
                    f"- {card.gap.reason}",
                    f"- Reference: {card.gap.reference_label} ({card.gap.reference_url})",
                    "",
                ]
            )
        elif isinstance(card, UnavailableCard):
            lines.extend([f"### {card.variable.name}", "", f"- Not analysed: {card.reason}", ""])
    return lines


def build_methods_report(
    trails: Sequence[Trail], options: AnalysisOptions, generated_at: datetime
) -> str:
    """Build the full report for one analysis run."""
    lines = [
        f"# Methods report – {APP_NAME} {__version__}",
        "",
        f"Generated: {generated_at:%Y-%m-%d %H:%M}",
        "",
        "Screening and learning tool – not a publication-grade assessment.",
        "",
        *_settings_section(options),
    ]
    for trail in trails:
        lines.extend(_trail_section(trail))
    lines.extend(["---", "", CAUSATION_NOTE, ""])
    return "\n".join(lines)
