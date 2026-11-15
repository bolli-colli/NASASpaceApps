"""Run every catalogue script in this folder one after the other.

python scripts/catalogs/run_all.py                    # print every list, with a header each
python scripts/catalogs/run_all.py data/raw/catalogs  # save one .txt per list, print a summary

Scripts that need an argument get an example (a product, dataset or date range) that
matters for this project. A failing API is reported and the run continues.
"""

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
RUNS = [
    # NASA
    ("giovanni_variables", []),
    ("cmr_providers", []),
    ("cmr_collections", ["GES_DISC"]),
    ("cmr_collections", ["LAADS"]),
    ("cmr_collections", ["OB_CLOUD"]),
    ("cmr_stac_collections", ["GES_DISC"]),
    ("cmr_variables", ["M2TMNXAER"]),
    ("cmr_granules", ["MODISA_L3m_CHL", "*.MO.*.9km*", "2020-10-01", "2020-10-31"]),
    ("harmony_variables", ["M2TMNXAER"]),
    ("harmony_variables", ["MOD08_M3", "--services"]),
    ("opendap_variables", ["OMAERUVd"]),  # needs EARTHDATA_TOKEN
    ("appeears_products", []),
    ("appeears_layers", ["MCD43A3.061"]),
    ("laads_products", []),
    ("obdaac_datatypes", []),
    ("obdaac_files", ["7", "1043", "2024-01-01", "2024-01-31", "*.L3m.MO.CHL*"]),
    ("hydrocron_fields", []),
    ("power_parameters", []),
    ("gibs_layers", []),
    ("eonet_categories", []),
    ("aeronet_sites", []),
    # not NASA
    ("cds_datasets", []),
    ("geomet_collections", []),
    ("usgs_collections", []),
    ("ncei_datasets", []),
    ("ncei_datatypes", ["global-summary-of-the-month"]),
    ("ncei_files", ["data/global-summary-of-the-month/"]),
    ("soilgrids_coverages", []),
    ("wosis_fields", []),
    ("eodms_collections", []),
]

out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if out_dir:
    out_dir.mkdir(parents=True, exist_ok=True)

failed = []
for script, args in RUNS:
    label = " ".join([script, *args])
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(HERE / f"{script}.py"), *args], capture_output=True, text=True
    )
    seconds = time.monotonic() - started
    lines = result.stdout.splitlines()
    status = "ok" if result.returncode == 0 else "FAILED"
    if result.returncode:
        failed.append(label)
    if out_dir:
        name = "_".join([script, *args]).replace("*", "x").replace("/", "-").strip("-")
        (out_dir / f"{name}.txt").write_text(result.stdout)
        print(f"{status:6} {len(lines):6} lines {seconds:6.1f}s  {label}", flush=True)
    else:
        print(f"\n### {label}  ({status}, {len(lines)} lines, {seconds:.1f}s)", flush=True)
        print(result.stdout, end="", flush=True)
    if result.returncode:
        last = result.stderr.strip().splitlines()[-1:] or ["no error message"]
        print(f"       {last[0]}", flush=True)

print(
    f"\n{len(RUNS) - len(failed)} of {len(RUNS)} lists done"
    + (f"; failed: {failed}" if failed else "")
)
sys.exit(1 if failed else 0)
