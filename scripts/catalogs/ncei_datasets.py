"""Print the datasets of the NOAA NCEI Access Data Service (station and climate data). Not NASA.

    python scripts/catalogs/ncei_datasets.py  # id <tab> name
    python scripts/catalogs/ncei_datasets.py daily monthly  # only lines containing a word

The data types of one dataset:
https://www.ncei.noaa.gov/access/services/support/v3/datasets/{id}.json
"""

import json
import sys
from urllib.request import urlopen

URL = "https://www.ncei.noaa.gov/access/services/search/v1/datasets?limit=1000"

with urlopen(URL, timeout=120) as response:
    results = json.load(response)["results"]

words = [word.lower() for word in sys.argv[1:]]
for line in sorted(f"{r['id']}\t{r.get('name', '')}" for r in results):
    if not words or any(word in line.lower() for word in words):
        print(line)
