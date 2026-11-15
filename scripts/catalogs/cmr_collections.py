"""Print the collections (products) of one NASA data centre, from the CMR search API.

    python scripts/catalogs/cmr_collections.py GES_DISC  # SHORT_NAME.VERSION <tab> title
    python scripts/catalogs/cmr_collections.py LAADS cloud MOD08  # only lines containing a word

Data centre ids come from cmr_providers.py. GES DISC has no catalogue API of its own;
its collections are searched here (provider GES_DISC).
"""

import json
import sys
from urllib.request import urlopen

URL = (
    "https://cmr.earthdata.nasa.gov/search/collections.json?provider={}&page_size=2000&page_num={}"
)

provider, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
lines, page = [], 1
while True:
    with urlopen(URL.format(provider, page), timeout=120) as response:
        entries = json.load(response)["feed"]["entry"]
    if not entries:
        break
    lines += [f"{e['short_name']}.{e.get('version_id', '')}\t{e['title']}" for e in entries]
    page += 1

for line in sorted(lines):
    if not words or any(word in line.lower() for word in words):
        print(line)
