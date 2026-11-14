"""Composition root: the only place that wires concrete classes together.

Everything else depends on the ports in ``application.ports``. The Streamlit
app and the command line scripts both start from ``build_container``.
"""

import os
from dataclasses import dataclass

from earth_trail_detective.application.ports import LiveDataGateway, SeriesSource
from earth_trail_detective.application.sources import (
    DerivedSeriesSource,
    LiveSeriesSource,
    RoutingGateway,
)
from earth_trail_detective.application.trail import TrailBuilder
from earth_trail_detective.application.trend_analysis import TrendAnalyzer
from earth_trail_detective.config import TOKEN_VARIABLE, Settings, load_env_file
from earth_trail_detective.domain.models import Period
from earth_trail_detective.infrastructure.earthaccess_gateway import EarthaccessGateway
from earth_trail_detective.infrastructure.giovanni_gateway import GiovanniGateway
from earth_trail_detective.infrastructure.harmony_gateway import HarmonyGateway
from earth_trail_detective.infrastructure.parquet_repository import ParquetSeriesRepository
from earth_trail_detective.infrastructure.yaml_catalog import YamlCatalog


@dataclass(frozen=True)
class Container:
    """The wired application objects."""

    settings: Settings
    catalog: YamlCatalog
    repository: ParquetSeriesRepository
    gateway: LiveDataGateway

    def _builder(self, source: SeriesSource) -> TrailBuilder:
        """Create a trail builder on top of any series source."""
        return TrailBuilder(
            self.catalog, DerivedSeriesSource(source, self.catalog), TrendAnalyzer()
        )

    def cache_builder(self) -> TrailBuilder:
        """Trail builder that reads the offline cache."""
        return self._builder(self.repository)

    def live_builder(self, period: Period) -> TrailBuilder:
        """Trail builder that fetches from NASA Earthdata for the given period."""
        return self._builder(LiveSeriesSource(self.gateway, period))

    @property
    def has_token(self) -> bool:
        """True if an Earthdata token is configured in the environment."""
        return bool(os.environ.get(TOKEN_VARIABLE))


def build_container(settings: Settings | None = None) -> Container:
    """Wire the application with the default adapters.

    Reads ``.env`` first, so the app and all scripts see the same variables.
    """
    load_env_file()
    settings = settings or Settings.from_environment()
    return Container(
        settings=settings,
        catalog=YamlCatalog(settings.catalog_dir),
        repository=ParquetSeriesRepository(settings.data_dir),
        gateway=RoutingGateway([EarthaccessGateway(), HarmonyGateway(), GiovanniGateway()]),
    )
