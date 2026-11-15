"""Print the datasets of the Copernicus Climate Data Store (ERA5, ERA5-Land, ...). Not NASA.

    python scripts/catalogs/cds_datasets.py  # id <tab> title
    python scripts/catalogs/cds_datasets.py era5 land  # only lines containing a word

Listing is open; downloading needs a CDS token (cdsapi).
"""

import json
import sys
from urllib.request import urlopen

URL = "https://cds.climate.copernicus.eu/api/catalogue/v1/collections?limit=1000"

with urlopen(URL, timeout=120) as response:
    collections = json.load(response)["collections"]

words = [word.lower() for word in sys.argv[1:]]
for line in sorted(f"{c['id']}\t{c.get('title', '')}" for c in collections):
    if not words or any(word in line.lower() for word in words):
        print(line)
