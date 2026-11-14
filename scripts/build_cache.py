"""Fill the offline data cache from NASA Earthdata (spec 13.1, step 3).

Fetches every variable of the chosen demo cases that has scripted access
(``access.provider: earthaccess`` in the catalog), reduces it to monthly
cos(latitude)-weighted area means and stores it as Parquet in ``data/``.

Needs the "live" extra and an Earthdata token:

    pip install -e ".[live]"
    cp .env.example .env                  # then fill in EARTHDATA_TOKEN
    python scripts/build_cache.py --demo A1 --start 2000-01

Variables without scripted access are listed at the end; export them by hand
and load them with ``scripts/import_csv.py``.
"""

import argparse
from datetime import date

from earth_trail_detective.bootstrap import Container, build_container
from earth_trail_detective.domain.models import DemoCase, Period, VariableSpec


def _month(text: str) -> date:
    """Parse ``YYYY-MM`` into the first day of that month."""
    return date.fromisoformat(f"{text}-01")


def _demo_variables(container: Container, demo: DemoCase) -> list[VariableSpec]:
    """All variables of a demo's substances, plus the inputs of derived ones."""
    catalog = container.catalog
    selected: dict[str, VariableSpec] = {}
    pending = [
        variable
        for variable in catalog.variables()
        if set(variable.substances) & set(demo.substances)
    ]
    while pending:
        variable = pending.pop()
        if variable.id in selected:
            continue
        selected[variable.id] = variable
        if variable.derivation:
            pending.extend(catalog.variable(i) for i in variable.derivation.inputs)
    # Derived variables are computed on the fly and never stored themselves.
    return [variable for variable in selected.values() if variable.derivation is None]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", action="append", help="demo id (repeatable); default: all")
    parser.add_argument("--start", type=_month, help="first month, YYYY-MM (default: full record)")
    parser.add_argument("--end", type=_month, help="last month, YYYY-MM (default: today)")
    arguments = parser.parse_args()

    container = build_container()
    catalog, gateway = container.catalog, container.gateway
    demos = [demo for demo in catalog.demos() if not arguments.demo or demo.id in arguments.demo]
    period = Period(arguments.start, arguments.end)

    manual: set[str] = set()
    for demo in demos:
        variables = _demo_variables(container, demo)
        scripted = [variable for variable in variables if gateway.supports(variable)]
        manual.update(variable.id for variable in variables if not gateway.supports(variable))
        region_ids = sorted(
            {region_id for region_set in demo.region_sets for region_id in region_set}
        )
        regions = [catalog.region(region_id) for region_id in region_ids]
        print(f"Demo {demo.id}: {len(scripted)} variables x {len(regions)} regions ...")

        fetched = gateway.fetch(scripted, regions, period)
        # ``fetch`` returns the series with the variables in the outer loop.
        pairs = [(variable, region) for variable in scripted for region in regions]
        for (variable, region), series in zip(pairs, fetched, strict=True):
            container.repository.save(variable, region, series)
            print(f"  saved {variable.id} / {region.id} ({series.values.count()} months)")

    if manual:
        print("\nNo scripted access - export by hand and use scripts/import_csv.py:")
        for variable_id in sorted(manual):
            print(f"  {variable_id}: {catalog.variable(variable_id).access.hint}")


if __name__ == "__main__":
    main()
