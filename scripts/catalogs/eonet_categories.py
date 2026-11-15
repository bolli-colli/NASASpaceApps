"""Print the event categories of NASA EONET (wildfires, dust and haze, volcanoes, ...).

python scripts/catalogs/eonet_categories.py  # id <tab> title
python scripts/catalogs/eonet_categories.py --events  # open events: date, category, title
"""

import json
import sys
from urllib.request import urlopen

URL = "https://eonet.gsfc.nasa.gov/api/v3/"

if "--events" in sys.argv:
    with urlopen(URL + "events?status=open", timeout=60) as response:
        events = json.load(response)["events"]
    lines = [
        f"{e['geometry'][-1]['date'][:10]}\t{e['categories'][0]['id']}\t{e['title']}"
        for e in events
    ]
else:
    with urlopen(URL + "categories", timeout=60) as response:
        lines = [f"{c['id']}\t{c['title']}" for c in json.load(response)["categories"]]

for line in sorted(lines):
    print(line)
