"""Print the collections of the USGS Water Data OGC API (streamflow, groundwater). Not NASA.

python scripts/catalogs/usgs_collections.py  # id <tab> title
python scripts/catalogs/usgs_collections.py daily  # only lines containing a word
"""

import json
import sys
from urllib.request import urlopen

URL = "https://api.waterdata.usgs.gov/ogcapi/v0/collections?f=json"

with urlopen(URL, timeout=120) as response:
    collections = json.load(response)["collections"]

words = [word.lower() for word in sys.argv[1:]]
for line in sorted(f"{c['id']}\t{c.get('title', '')}" for c in collections):
    if not words or any(word in line.lower() for word in words):
        print(line)
