"""Area statistics from NASA AppEEARS for variables without another route (MODIS snow albedo).

AppEEARS cuts a product to a region box on NASA's side and returns, among the rasters,
a CSV with one mean per date. This script submits one task per region, waits, downloads
only that CSV and imports it into the offline cache (daily means → months).

    python scripts/appeears_area.py submit --variable snow_albedo_modis \
        --region alps --region central_himalaya
    python scripts/appeears_area.py status
    python scripts/appeears_area.py fetch          # downloads + imports every finished task

AppEEARS does not accept the Earthdata token; it needs EARTHDATA_USERNAME and
EARTHDATA_PASSWORD (in .env). Task ids are kept in data/raw/appeears_tasks.json, so the
steps can run in separate sessions. A task over 25 years of daily 500 m data can take
hours on NASA's side.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import requests

from earth_trail_detective.bootstrap import build_container
from earth_trail_detective.config import PROJECT_ROOT, load_env_file

API = "https://appeears.earthdatacloud.nasa.gov/api"
STATE = PROJECT_ROOT / "data" / "raw" / "appeears_tasks.json"
# Catalog variable -> AppEEARS product and layer
LAYERS = {"snow_albedo_modis": ("MOD10A1.061", "Snow_Albedo_Daily_Tile")}


def _token() -> str:
    load_env_file()
    user, password = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if not user or not password:
        sys.exit(
            "Set EARTHDATA_USERNAME and EARTHDATA_PASSWORD in .env (AppEEARS rejects the token)."
        )
    response = requests.post(f"{API}/login", auth=(user, password), timeout=60)
    response.raise_for_status()
    return response.json()["token"]


def _load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def _save(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def _polygon(bbox) -> dict:
    ring = [
        [bbox.west, bbox.south], [bbox.east, bbox.south], [bbox.east, bbox.north],
        [bbox.west, bbox.north], [bbox.west, bbox.south],
    ]  # fmt: skip
    feature = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }
    return {"type": "FeatureCollection", "features": [feature]}


def submit(variable_id: str, region_ids: list[str], start: str | None) -> None:
    catalog = build_container().catalog
    variable = catalog.variable(variable_id)
    product, layer = LAYERS[variable_id]
    first = date.fromisoformat(start or f"{variable.period_start}-01")
    headers = {"Authorization": f"Bearer {_token()}"}
    state = _load()
    for region_id in region_ids:
        region = catalog.region(region_id)
        task = {
            "task_type": "area",
            "task_name": f"etd_{variable_id}_{region_id}",
            "params": {
                "dates": [
                    {
                        "startDate": first.strftime("%m-%d-%Y"),
                        "endDate": date.today().strftime("%m-%d-%Y"),
                    }
                ],
                "layers": [{"product": product, "layer": layer}],
                "output": {"format": {"type": "netcdf4"}, "projection": "geographic"},
                "geo": _polygon(region.bbox),
            },
        }
        response = requests.post(f"{API}/task", json=task, headers=headers, timeout=120)
        if not response.ok:
            sys.exit(f"{region_id}: {response.status_code} {response.text[:500]}")
        task_id = response.json()["task_id"]
        state[task_id] = {"variable": variable_id, "region": region_id, "status": "pending"}
        print(f"submitted {variable_id} / {region_id}: {task_id}")
    _save(state)


def status() -> dict:
    headers = {"Authorization": f"Bearer {_token()}"}
    state = _load()
    for task_id, info in state.items():
        response = requests.get(f"{API}/task/{task_id}", headers=headers, timeout=60)
        response.raise_for_status()
        info["status"] = response.json().get("status", "?")
        print(f"{info['variable']} / {info['region']}: {info['status']} ({task_id})")
    _save(state)
    return state


def fetch() -> None:
    state = status()
    headers = {"Authorization": f"Bearer {_token()}"}
    for task_id, info in state.items():
        if info["status"] != "done" or info.get("imported"):
            continue
        bundle = requests.get(f"{API}/bundle/{task_id}", headers=headers, timeout=60).json()
        stats = [f for f in bundle["files"] if f["file_name"].endswith("Statistics.csv")]
        if not stats:
            print(f"{task_id}: no statistics CSV in the bundle")
            continue
        target = STATE.parent / f"appeears_{info['variable']}__{info['region']}.csv"
        response = requests.get(
            f"{API}/bundle/{task_id}/{stats[0]['file_id']}", headers=headers, timeout=300
        )
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"downloaded {target.name}")
        # values are albedo in percent (0-100), the catalog unit
        subprocess.run(
            [
                sys.executable, str(Path(__file__).parent / "import_csv.py"), str(target),
                "--variable", info["variable"], "--region", info["region"],
                "--date-column", "Date", "--value-column", "Mean", "--unit", "%",
            ],
            check=True,
        )  # fmt: skip
        info["imported"] = True
    _save(state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    submit_parser = commands.add_parser("submit", help="submit one area task per region")
    submit_parser.add_argument("--variable", required=True, choices=sorted(LAYERS))
    submit_parser.add_argument("--region", action="append", required=True)
    submit_parser.add_argument(
        "--start", help="first day YYYY-MM-DD (default: start of the product)"
    )
    commands.add_parser("status", help="show the state of the submitted tasks")
    commands.add_parser("fetch", help="download and import every finished task")
    args = parser.parse_args()
    if args.command == "submit":
        submit(args.variable, args.region, args.start)
    elif args.command == "status":
        status()
    else:
        fetch()


if __name__ == "__main__":
    main()
