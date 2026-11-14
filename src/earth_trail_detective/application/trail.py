"""Use case: build the cards of a trail (requirement M9) or of free variables."""

from collections.abc import Iterable, Sequence

from earth_trail_detective.application.options import AnalysisOptions, AnalysisRequest
from earth_trail_detective.application.ports import Catalog, SeriesSource
from earth_trail_detective.application.trend_analysis import TrendAnalyzer
from earth_trail_detective.domain.enums import GapStatus, Step
from earth_trail_detective.domain.errors import InsufficientDataError
from earth_trail_detective.domain.models import Region, VariableSpec
from earth_trail_detective.domain.results import (
    Card,
    Trail,
    TrailEndCard,
    TrendCard,
    UnavailableCard,
)
from earth_trail_detective.domain.statistics.multiple_testing import benjamini_hochberg


class TrailBuilder:
    """Turns catalog entries and series into cards, one region at a time."""

    def __init__(self, catalog: Catalog, source: SeriesSource, analyzer: TrendAnalyzer) -> None:
        self._catalog = catalog
        self._source = source
        self._analyzer = analyzer

    def run(self, request: AnalysisRequest) -> tuple[Trail, ...]:
        """Answer a request with one trail per requested region."""
        if request.substance_id is not None:
            return tuple(
                self.build_trail(request.substance_id, region, request.options, request.steps)
                for region in request.regions
            )
        return tuple(
            self.analyse_variables(request.variable_ids, region, request.options)
            for region in request.regions
        )

    def build_trail(
        self,
        substance_id: str,
        region: Region,
        options: AnalysisOptions,
        steps: Sequence[Step] | None = None,
    ) -> Trail:
        """Follow one substance through all (or the selected) steps."""
        cards: list[Card] = []
        for info in self._catalog.steps():
            if steps is not None and info.step not in steps:
                continue
            variables = self._catalog.variables_for(substance_id, info.step)
            if variables:
                cards.extend(self._card(variable, region, options) for variable in variables)
                continue
            # No variable: the catalog guarantees a documented gap for this cell.
            gap = self._catalog.gap(substance_id, info.step)
            if gap is not None and gap.status is not GapStatus.NOT_APPLICABLE:
                cards.append(TrailEndCard(info.step, gap))
        cards = self._adjust(cards, options)
        return Trail(region, tuple(cards), self._catalog.substance(substance_id))

    def analyse_variables(
        self, variable_ids: Iterable[str], region: Region, options: AnalysisOptions
    ) -> Trail:
        """Analyse freely chosen catalog variables (researcher mode)."""
        cards = [
            self._card(self._catalog.variable(variable_id), region, options)
            for variable_id in variable_ids
        ]
        return Trail(region, tuple(self._adjust(cards, options)))

    def _card(self, variable: VariableSpec, region: Region, options: AnalysisOptions) -> Card:
        """Load and analyse one variable; never raises for missing data."""
        series = self._source.load(variable, region)
        if series is None:
            reason = self._source.explain_missing(variable)
            return UnavailableCard(variable.step, variable, reason)
        try:
            result = self._analyzer.analyze(series, options)
        except InsufficientDataError as error:
            return UnavailableCard(variable.step, variable, str(error))
        return TrendCard(variable.step, variable, series, result)

    @staticmethod
    def _adjust(cards: list[Card], options: AnalysisOptions) -> list[Card]:
        """Apply Benjamini-Hochberg across all trend cards of a trail (C6)."""
        if not options.benjamini_hochberg:
            return cards
        trend_cards = [card for card in cards if isinstance(card, TrendCard)]
        adjusted = benjamini_hochberg([card.result.mk_p for card in trend_cards])
        replacements = {
            id(card): TrendCard(
                card.step, card.variable, card.series, card.result.with_adjusted_p(p_value)
            )
            for card, p_value in zip(trend_cards, adjusted, strict=True)
        }
        return [replacements.get(id(card), card) for card in cards]
