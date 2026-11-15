"""Fill the offline data cache from NASA Earthdata (spec 13.1, step 3).

Fetches every variable of the chosen demo cases that has scripted access
(``access.provider`` giovanni, harmony or earthaccess in the catalog), reduces
it to monthly cos(latitude)-weighted area means and stores it as Parquet in
``data/``. The app can do the same on demand (``ETD_FETCH`` in ``.env``); both
use ``application.cache_filler``.

Needs the "live" extra and an Earthdata token:

    pip install -e ".[live]"
    cp .env.example .env                  # then fill in EARTHDATA_TOKEN
    python scripts/build_cache.py --demo A1 --start 2000-01

Every product is saved as soon as it is complete, and series that are already in
the cache are skipped (``--refresh`` reloads them), so an interrupted run can simply
be started again.

Variables without scripted access are listed at the end; export them by hand
and load them with ``scripts/import_csv.py``.
"""

import argparse
import logging
from datetime import date

from earth_trail_detective.application.cache_filler import FetchJob
from earth_trail_detective.bootstrap import build_container
from earth_trail_detective.domain.models import Period


def _month(text: str) -> date:
    """Parse ``YYYY-MM`` into the first day of that month."""
    return date.fromisoformat(f"{text}-01")


def _announce(number: int, total: int, job: FetchJob) -> None:
    print(f"  [{number}/{total}] {job.label} ...", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", action="append", help="demo id (repeatable); default: all")
    parser.add_argument("--start", type=_month, help="first month, YYYY-MM (default: full record)")
    parser.add_argument("--end", type=_month, help="last month, YYYY-MM (default: today)")
    parser.add_argument("--refresh", action="store_true", help="reload series already cached")
    parser.add_argument(
        "--skip-product",
        action="append",
        default=[],
        metavar="SHORT_NAME",
        help="leave out a NASA product, e.g. OMSO2e (repeatable)",
    )
    arguments = parser.parse_args()

    container = build_container()
    catalog, filler = container.catalog, container.cache_filler()
    demos = [demo for demo in catalog.demos() if not arguments.demo or demo.id in arguments.demo]

    manual: set[str] = set()
    failed: list[str] = []
    for demo in demos:
        variables = [
            variable
            for variable in catalog.variables()
            if set(variable.substances) & set(demo.substances)
        ]
        region_ids = sorted(
            {region_id for region_set in demo.region_sets for region_id in region_set}
        )
        regions = [catalog.region(region_id) for region_id in region_ids]
        plan = filler.plan(
            variables, regions, refresh=arguments.refresh, skip_products=arguments.skip_product
        )
        manual.update(variable.id for variable in plan.manual)
        print(f"Demo {demo.id}: {len(plan.jobs)} product(s) to fetch for {len(regions)} regions")
        period = Period(arguments.start, arguments.end)
        for outcome in filler.run(plan, on_job=_announce, period=period):
            if outcome.error:
                failed.append(f"{outcome.job.access.short_name} (demo {demo.id}): {outcome.error}")
                print(f"    FAILED - {outcome.error}", flush=True)
            for variable_id, region_id, months in outcome.saved:
                print(f"    saved {variable_id} / {region_id} ({months} months)")

    if manual:
        print("\nNo scripted access - export by hand and use scripts/import_csv.py:")
        for variable_id in sorted(manual):
            print(f"  {variable_id}: {catalog.variable(variable_id).access.hint}")

    if failed:
        print("\nFailed products - run the script again to retry only these:")
        for message in failed:
            print(f"  {message}")
        raise SystemExit(1)


if __name__ == "__main__":
    # progress lines of the gateways (e.g. "CLDPROP_M3_MODIS_Aqua: 30/291 files")
    logging.basicConfig(level=logging.INFO, format="      %(message)s")
    main()
