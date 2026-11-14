"""Use case: fill the offline cache from NASA (spec 13.1, step 3).

Shared by ``scripts/build_cache.py`` and the app (``ETD_FETCH``): work out
which stored series are missing, fetch them product by product (one call per
NASA product, so files are shared between its variables) and save each
product as soon as it is complete. A failing product is reported and the
others go on.

The app always fetches the **whole record** of a product, whatever period an
analysis looks at, so a cached series is never silently cut short. Only the
build script may limit the period (``--start`` / ``--end``, for a quick trial).
"""

from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass

from earth_trail_detective.application.options import AnalysisRequest
from earth_trail_detective.application.ports import Catalog, LiveDataGateway, SeriesStore
from earth_trail_detective.domain.errors import LiveAccessError
from earth_trail_detective.domain.models import AccessSpec, Period, Region, VariableSpec


@dataclass(frozen=True)
class FetchJob:
    """One NASA product: its variables for the regions that need them."""

    access: AccessSpec
    variables: tuple[VariableSpec, ...]
    regions: tuple[Region, ...]

    @property
    def label(self) -> str:
        return (
            f"{self.access.short_name}: {len(self.variables)} variable(s) "
            f"x {len(self.regions)} region(s)"
        )


@dataclass(frozen=True)
class FetchPlan:
    """What has to be fetched, and what can only be imported by hand."""

    jobs: tuple[FetchJob, ...]
    manual: tuple[VariableSpec, ...]  # missing, but no scripted access (CSV import)

    @property
    def is_empty(self) -> bool:
        return not self.jobs


@dataclass(frozen=True)
class FetchOutcome:
    """Result of one job: the saved series, or the reason it failed."""

    job: FetchJob
    saved: tuple[tuple[str, str, int], ...] = ()  # (variable id, region id, months)
    error: str | None = None


def requested_variables(catalog: Catalog, request: AnalysisRequest) -> list[VariableSpec]:
    """The catalog variables an analysis will show (trail or free choice)."""
    if request.substance_id is None:
        return [catalog.variable(variable_id) for variable_id in request.variable_ids]
    return [
        variable
        for info in catalog.steps()
        if request.steps is None or info.step in request.steps
        for variable in catalog.variables_for(request.substance_id, info.step)
    ]


class CacheFiller:
    """Plans and runs the fetches that fill the offline cache."""

    def __init__(self, catalog: Catalog, store: SeriesStore, gateway: LiveDataGateway) -> None:
        self._catalog = catalog
        self._store = store
        self._gateway = gateway

    def stored_variables(self, variables: Iterable[VariableSpec]) -> list[VariableSpec]:
        """Replace derived variables by their inputs: only those are stored."""
        selected: dict[str, VariableSpec] = {}
        pending = list(variables)
        while pending:
            variable = pending.pop(0)
            if variable.derivation is not None:
                pending.extend(self._catalog.variable(i) for i in variable.derivation.inputs)
            else:
                selected.setdefault(variable.id, variable)
        return list(selected.values())

    def plan(
        self,
        variables: Iterable[VariableSpec],
        regions: Sequence[Region],
        refresh: bool = False,
        skip_products: Collection[str] = (),
    ) -> FetchPlan:
        """Group what is missing (or everything, with ``refresh``) by NASA product."""
        members: dict[AccessSpec, list[VariableSpec]] = defaultdict(list)
        needed_regions: dict[AccessSpec, dict[str, Region]] = defaultdict(dict)
        manual: list[VariableSpec] = []
        for variable in self.stored_variables(variables):
            missing = [
                region
                for region in regions
                if refresh or self._store.load(variable, region) is None
            ]
            if not missing:
                continue
            if not self._gateway.supports(variable):
                manual.append(variable)
                continue
            if variable.access.short_name in skip_products:
                continue
            members[variable.access].append(variable)
            needed_regions[variable.access].update((region.id, region) for region in missing)
        jobs = tuple(
            FetchJob(access, tuple(found), tuple(needed_regions[access].values()))
            for access, found in members.items()
        )
        return FetchPlan(jobs, tuple(manual))

    def run(
        self,
        plan: FetchPlan,
        on_job: Callable[[int, int, FetchJob], None] | None = None,
        period: Period | None = None,
    ) -> list[FetchOutcome]:
        """Fetch every job of the plan and save each product at once.

        ``period`` defaults to the whole record of every product.
        """
        outcomes = []
        for number, job in enumerate(plan.jobs, start=1):
            if on_job is not None:
                on_job(number, len(plan.jobs), job)
            outcomes.append(self._run_job(job, period or Period()))
        return outcomes

    def _run_job(self, job: FetchJob, period: Period) -> FetchOutcome:
        try:
            fetched = self._gateway.fetch(job.variables, job.regions, period)
        except LiveAccessError as error:
            return FetchOutcome(job, error=str(error))
        # ``fetch`` returns the series with the variables in the outer loop.
        pairs = [(variable, region) for variable in job.variables for region in job.regions]
        saved = []
        for (variable, region), series in zip(pairs, fetched, strict=True):
            self._store.save(variable, region, series)
            saved.append((variable.id, region.id, int(series.values.count())))
        return FetchOutcome(job, saved=tuple(saved))
