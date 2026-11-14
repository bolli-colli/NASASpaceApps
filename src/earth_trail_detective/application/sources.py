"""Series sources that build on other sources.

* ``DerivedSeriesSource`` is a decorator: it adds derived variables (sum,
  ratio) on top of any source – cache and live access behave the same.
* ``LiveSeriesSource`` adapts a ``LiveDataGateway`` to the ``SeriesSource`` port.
* ``RoutingGateway`` combines several gateways behind the one gateway port.
"""

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd

from earth_trail_detective.application.ports import Catalog, LiveDataGateway, SeriesSource
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import Period, Region, VariableSpec
from earth_trail_detective.domain.series import MonthlySeries, SeriesMeta


def _sum(inputs: list[pd.Series]) -> pd.Series:
    """Add all inputs; a month is missing if any input is missing."""
    return pd.concat(inputs, axis=1).sum(axis=1, skipna=False)


def _ratio(inputs: list[pd.Series]) -> pd.Series:
    """Divide the first input by the second; division by zero gives a gap."""
    numerator, denominator = inputs
    return numerator / denominator.replace(0, np.nan)


# Registry of derivation operations: a new operation is one new entry.
_OPERATIONS: dict[str, Callable[[list[pd.Series]], pd.Series]] = {
    "sum": _sum,
    "ratio": _ratio,
}
DERIVATION_OPERATIONS = frozenset(_OPERATIONS)


class DerivedSeriesSource:
    """Adds catalog variables that are computed from other variables (S7)."""

    def __init__(self, inner: SeriesSource, catalog: Catalog) -> None:
        self._inner = inner
        self._catalog = catalog

    def load(self, variable: VariableSpec, region: Region) -> MonthlySeries | None:
        if variable.derivation is None:
            return self._inner.load(variable, region)
        inputs = [
            self.load(self._catalog.variable(input_id), region)
            for input_id in variable.derivation.inputs
        ]
        if any(series is None for series in inputs):
            return None
        values = _OPERATIONS[variable.derivation.operation]([s.values for s in inputs])
        # Unit, kind and product of the result are those of the catalog entry.
        return MonthlySeries(values, SeriesMeta.describe(variable, region))

    def explain_missing(self, variable: VariableSpec) -> str:
        if variable.derivation is None:
            return self._inner.explain_missing(variable)
        inputs = ", ".join(variable.derivation.inputs)
        return f"Derived value: at least one input series is unavailable ({inputs})."


class LiveSeriesSource:
    """Loads series through a live gateway for a fixed period."""

    def __init__(self, gateway: LiveDataGateway, period: Period) -> None:
        self._gateway = gateway
        self._period = period

    def load(self, variable: VariableSpec, region: Region) -> MonthlySeries | None:
        if not self._gateway.supports(variable):
            return None
        return self._gateway.fetch([variable], [region], self._period)[0]

    def explain_missing(self, variable: VariableSpec) -> str:
        return (
            "Live access is not available for this product. "
            "Export a CSV and import it into the cache instead (see README)."
        )


class RoutingGateway:
    """Sends every variable to the first gateway that supports it.

    Callers see one ``LiveDataGateway``; which NASA service delivers a
    product stays a detail of the catalog (``access.provider``).
    """

    def __init__(self, gateways: Sequence[LiveDataGateway]) -> None:
        self._gateways = tuple(gateways)

    def _gateway_for(self, variable: VariableSpec) -> LiveDataGateway | None:
        return next((g for g in self._gateways if g.supports(variable)), None)

    def supports(self, variable: VariableSpec) -> bool:
        return self._gateway_for(variable) is not None

    def fetch(
        self, variables: Sequence[VariableSpec], regions: Sequence[Region], period: Period
    ) -> list[MonthlySeries]:
        unsupported = [variable.id for variable in variables if not self.supports(variable)]
        if unsupported:
            raise LiveAccessError(f"No scripted access for: {unsupported}")
        # One call per gateway, so each gateway can share files between its variables.
        fetched: dict[tuple[str, str], MonthlySeries] = {}
        for gateway in self._gateways:
            own = [variable for variable in variables if self._gateway_for(variable) is gateway]
            if not own:
                continue
            keys = [(variable.id, region.id) for variable in own for region in regions]
            fetched.update(zip(keys, gateway.fetch(own, regions, period), strict=True))
        return [fetched[(variable.id, region.id)] for variable in variables for region in regions]
