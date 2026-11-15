"""Print what Harmony can subset for one collection: its variables, or its services.

    python scripts/catalogs/harmony_variables.py M2TMNXAER  # name <tab> long name [units]
    python scripts/catalogs/harmony_variables.py M2TMNXAER dust soot  # only lines containing a word
    python scripts/catalogs/harmony_variables.py M2TMNXAER --services  # Harmony services

A service "giovanni-time-series-adapter" / "giovanni-averaging-service" means the area
means can be computed on NASA's side (as the app does for OMI).
"""

import json
import sys
from urllib.request import urlopen

URL = "https://harmony.earthdata.nasa.gov/capabilities?shortName={}"

short_name, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
with urlopen(URL.format(short_name), timeout=60) as response:
    capabilities = json.load(response)

if "--services" in words:
    lines = [service["name"] for service in capabilities["services"]]
    words = []
else:
    lines = [
        f"{v['name']}\t{v.get('longName', '')} [{v.get('units', '')}]"
        for v in capabilities["variables"]
    ]

for line in sorted(lines):
    if not words or any(word in line.lower() for word in words):
        print(line)
