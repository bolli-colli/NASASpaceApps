"""Smoke test that runs INSIDE the built image (called by container/smoke-test.sh).

1. The installed package, catalog and Parquet cache work together: Demo A1
   produces real (not artificial) trend cards for both regions.
2. The real Streamlit app, driven headless with Streamlit's AppTest, runs the
   first demo without an exception and draws charts.

Exits non-zero with a clear message on the first failure.
"""

import os
import sys

from streamlit.testing.v1 import AppTest

from earth_trail_detective.application.options import AnalysisRequest
from earth_trail_detective.bootstrap import build_container
from earth_trail_detective.domain.results import TrendCard

MIN_TREND_CARDS_PER_REGION = 2
MIN_CHARTS = 4


def fail(message: str) -> None:
    print(f"SMOKE FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def check_analysis() -> None:
    container = build_container()
    catalog = container.catalog
    cached = sorted(container.settings.data_dir.glob("*.parquet"))
    if not cached:
        fail(f"no Parquet files in {container.settings.data_dir} – the image has no data")
    print(f"cache: {len(cached)} series in {container.settings.data_dir}")

    demo = next(demo for demo in catalog.demos() if demo.id == "A1")
    regions = tuple(catalog.region(region_id) for region_id in demo.region_sets[0])
    request = AnalysisRequest(regions=regions, substance_id=demo.substances[0], demo_id=demo.id)
    for trail in container.cache_builder().run(request):
        cards = [card for card in trail.cards if isinstance(card, TrendCard)]
        if len(cards) < MIN_TREND_CARDS_PER_REGION:
            fail(f"Demo A1, {trail.region.name}: only {len(cards)} trend card(s)")
        if any(card.series.is_synthetic for card in cards):
            fail(f"Demo A1, {trail.region.name}: artificial data in the image cache")
        print(f"Demo A1 / {trail.region.name}: {len(cards)} trend cards")


def check_app() -> None:
    app = AppTest.from_file("/app/app.py", default_timeout=120).run()
    if app.exception:
        fail(f"app start raised: {app.exception}")
    app.sidebar.button[0].click().run()  # "Run demo" with the default demo (A1)
    if app.exception:
        fail(f"demo run raised: {app.exception}")
    charts = len(app.get("plotly_chart"))
    if charts < MIN_CHARTS:
        fail(f"demo drew only {charts} chart(s), expected at least {MIN_CHARTS}")
    print(f"app: demo ran headless, {charts} charts")


def main() -> None:
    if os.getuid() == 0:
        fail("the container runs as root")
    if os.environ.get("EARTHDATA_TOKEN"):
        fail("an Earthdata token is set inside the image")
    if os.environ.get("ETD_FETCH", "off") != "off":
        fail("the image must default to ETD_FETCH=off")
    check_analysis()
    check_app()
    print("SMOKE OK (inside the container)")


if __name__ == "__main__":
    main()
