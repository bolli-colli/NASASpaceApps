"""Print the collections of one NASA data centre from CMR-STAC (STAC catalogue API).

    python scripts/catalogs/cmr_stac_collections.py GES_DISC  # id <tab> title
    python scripts/catalogs/cmr_stac_collections.py LAADS cloud  # only lines containing a word

Same content as cmr_collections.py, but through STAC (pystac-client, stackstac, ...).
STAC pages hold 100 collections, so large data centres take a few seconds.
"""

import json
import sys
from urllib.request import urlopen

provider, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
url = f"https://cmr.earthdata.nasa.gov/stac/{provider}/collections?limit=100"
lines = []
while url:
    with urlopen(url, timeout=120) as response:
        page = json.load(response)
    lines += [f"{c['id']}\t{c.get('title', '')}" for c in page["collections"]]
    url = next((link["href"] for link in page["links"] if link["rel"] == "next"), None)

for line in sorted(lines):
    if not words or any(word in line.lower() for word in words):
        print(line)
