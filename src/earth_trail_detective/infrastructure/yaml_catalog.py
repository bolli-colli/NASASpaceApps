"""Catalog adapter: reads the YAML files in ``catalog/`` (requirement M1).

The files are parsed and cross-checked once at start-up. A broken reference
or a matrix cell without variable *and* without documented gap raises a
``CatalogError`` – the app never silently drops a card.
"""

from pathlib import Path
from typing import Any

import yaml

from earth_trail_detective.application.sources import DERIVATION_OPERATIONS
from earth_trail_detective.domain.enums import DataKind, GapStatus, Step
from earth_trail_detective.domain.errors import CatalogError
from earth_trail_detective.domain.models import (
    AccessSpec,
    BoundingBox,
    DemoCase,
    Derivation,
    ReferenceTrend,
    Region,
    StepInfo,
    Substance,
    TrailGap,
    VariableSpec,
)

VARIABLES_FILE = "variables.yaml"
SUBSTANCES_FILE = "substances.yaml"
REGIONS_FILE = "regions.yaml"
TRAIL_FILE = "trail.yaml"
DEMOS_FILE = "demos.yaml"


def _as_tuple(value: Any) -> tuple:
    """Accept a single YAML value or a list and always return a tuple."""
    return tuple(value) if isinstance(value, list) else (value,)


def _parse_substance(raw: dict) -> Substance:
    return Substance(
        id=raw["id"],
        name=raw["name"],
        icon=raw["icon"],
        description=raw["description"],
        student_visible=raw.get("student_visible", True),
    )


def _parse_region(raw: dict) -> Region:
    return Region(raw["id"], raw["name"], raw["category"], BoundingBox(*raw["bbox"]))


def _parse_step(raw: dict) -> StepInfo:
    return StepInfo(Step(raw["id"]), raw["label"], raw["icon"], raw["description"])


def _parse_gap(raw: dict) -> TrailGap:
    return TrailGap(
        substance=raw["substance"],
        step=Step(raw["step"]),
        status=GapStatus(raw["status"]),
        reason=raw["reason"],
        reference_label=raw.get("reference_label", ""),
        reference_url=raw.get("reference_url", ""),
    )


def _parse_variable(raw: dict) -> VariableSpec:
    access = raw.get("access")
    derivation = raw.get("derivation")
    return VariableSpec(
        id=raw["id"],
        name=raw["name"],
        definition=raw["definition"],
        unit=raw["unit"],
        source_unit=raw.get("source_unit", raw["unit"]),
        product=raw["product"],
        version=str(raw["version"]),
        source_variables=_as_tuple(raw["variable"]),
        substances=_as_tuple(raw["substance"]),
        step=Step(raw["step"]),
        kind=DataKind(raw["kind"]),
        period_start=raw["period"]["start"],
        period_end=raw["period"]["end"],
        coverage=raw["coverage"],
        source_url=raw["source_url"],
        caveats=tuple(raw.get("caveats", ())),
        access=AccessSpec(**access) if access else None,
        derivation=(
            Derivation(derivation["operation"], tuple(derivation["inputs"])) if derivation else None
        ),
    )


def _parse_demo(raw: dict) -> DemoCase:
    reference = raw.get("reference")
    return DemoCase(
        id=raw["id"],
        title=raw["title"],
        purpose=raw["purpose"],
        explanation=raw["explanation"],
        substances=tuple(raw["substances"]),
        region_sets=tuple(tuple(region_set) for region_set in raw["region_sets"]),
        reference=ReferenceTrend(**reference) if reference else None,
    )


class YamlCatalog:
    """Implements the ``Catalog`` port on top of the YAML files."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        trail = self._read(TRAIL_FILE)
        self._substances = self._index(SUBSTANCES_FILE, "substances", _parse_substance)
        self._regions = self._index(REGIONS_FILE, "regions", _parse_region)
        self._variables = self._index(VARIABLES_FILE, "variables", _parse_variable)
        self._demos = self._index(DEMOS_FILE, "demos", _parse_demo)
        self._steps = tuple(self._parse_all(TRAIL_FILE, trail["steps"], _parse_step))
        self._gaps = {
            (gap.substance, gap.step): gap
            for gap in self._parse_all(TRAIL_FILE, trail["gaps"], _parse_gap)
        }
        self._validate()

    # --- reading -------------------------------------------------------------------

    def _read(self, file_name: str) -> dict:
        """Load one YAML file of the catalog directory."""
        path = self._directory / file_name
        try:
            with path.open(encoding="utf-8") as handle:
                return yaml.safe_load(handle)
        except (OSError, yaml.YAMLError) as error:
            raise CatalogError(f"Cannot read catalog file {path}: {error}") from error

    @staticmethod
    def _parse_all(file_name: str, entries: list[dict], parse) -> list:
        """Parse a list of entries and report the offending entry on failure."""
        parsed = []
        for raw in entries:
            try:
                parsed.append(parse(raw))
            except (KeyError, TypeError, ValueError) as error:
                label = raw.get("id", raw) if isinstance(raw, dict) else raw
                raise CatalogError(f"{file_name}: invalid entry {label!r}: {error!r}") from error
        return parsed

    def _index(self, file_name: str, key: str, parse) -> dict:
        """Read a file and index its entries by id (ids must be unique)."""
        entries = self._parse_all(file_name, self._read(file_name)[key], parse)
        index = {entry.id: entry for entry in entries}
        if len(index) != len(entries):
            raise CatalogError(f"{file_name}: ids must be unique.")
        return index

    # --- consistency checks ----------------------------------------------------------

    def _validate(self) -> None:
        """Check all cross references between the catalog files."""
        if {info.step for info in self._steps} != set(Step):
            raise CatalogError(f"{TRAIL_FILE}: every step needs exactly one entry.")
        for variable in self._variables.values():
            self._require_known(variable.substances, self._substances, variable.id, "substance")
            if variable.derivation:
                self._require_known(
                    variable.derivation.inputs, self._variables, variable.id, "input variable"
                )
                if variable.derivation.operation not in DERIVATION_OPERATIONS:
                    raise CatalogError(
                        f"{variable.id}: unknown operation '{variable.derivation.operation}'."
                    )
        for demo in self._demos.values():
            self._require_known(demo.substances, self._substances, demo.id, "substance")
            for region_set in demo.region_sets:
                self._require_known(region_set, self._regions, demo.id, "region")
        # Honesty rule: every substance x step cell is a variable or a documented gap.
        for substance_id in self._substances:
            for step in Step:
                has_variable = bool(self.variables_for(substance_id, step))
                if not has_variable and (substance_id, step) not in self._gaps:
                    raise CatalogError(
                        f"No variable and no gap entry for '{substance_id}' at step '{step}'."
                    )

    @staticmethod
    def _require_known(ids: tuple[str, ...], known: dict, owner: str, what: str) -> None:
        """Raise if an entry refers to an id that does not exist."""
        unknown = [entry_id for entry_id in ids if entry_id not in known]
        if unknown:
            raise CatalogError(f"{owner}: unknown {what} {unknown}.")

    @staticmethod
    def _lookup(index: dict, entry_id: str, what: str):
        """Return an entry by id or raise a readable error."""
        try:
            return index[entry_id]
        except KeyError:
            raise CatalogError(f"Unknown {what} '{entry_id}'.") from None

    # --- Catalog port ----------------------------------------------------------------

    def substances(self) -> tuple[Substance, ...]:
        return tuple(self._substances.values())

    def substance(self, substance_id: str) -> Substance:
        return self._lookup(self._substances, substance_id, "substance")

    def variables(self) -> tuple[VariableSpec, ...]:
        return tuple(self._variables.values())

    def variable(self, variable_id: str) -> VariableSpec:
        return self._lookup(self._variables, variable_id, "variable")

    def variables_for(self, substance_id: str, step: Step) -> tuple[VariableSpec, ...]:
        return tuple(
            variable
            for variable in self._variables.values()
            if substance_id in variable.substances and variable.step is step
        )

    def regions(self) -> tuple[Region, ...]:
        return tuple(self._regions.values())

    def region(self, region_id: str) -> Region:
        return self._lookup(self._regions, region_id, "region")

    def steps(self) -> tuple[StepInfo, ...]:
        # Sorted by the enum definition order, which is the order of the trail.
        order = list(Step)
        return tuple(sorted(self._steps, key=lambda info: order.index(info.step)))

    def gap(self, substance_id: str, step: Step) -> TrailGap | None:
        return self._gaps.get((substance_id, step))

    def demos(self) -> tuple[DemoCase, ...]:
        return tuple(self._demos.values())
