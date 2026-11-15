"""Print the collections of MSC GeoMet (Environment Canada weather, climate, hydrometric). Not NASA.

python scripts/catalogs/geomet_collections.py  # id <tab> title
python scripts/catalogs/geomet_collections.py hydrometric  # only lines containing a word
"""

import json
import sys
from urllib.request import urlopen

URL = "https://api.weather.gc.ca/collections?f=json&lang=en"

with urlopen(URL, timeout=120) as response:
    collections = json.load(response)["collections"]

words = [word.lower() for word in sys.argv[1:]]
for line in sorted(f"{c['id']}\t{c.get('title', '')}" for c in collections):
    if not words or any(word in line.lower() for word in words):
        print(line)
