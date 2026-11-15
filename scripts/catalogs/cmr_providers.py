"""Print every NASA data centre (CMR provider): GES_DISC, LAADS, NSIDC_ECS, POCLOUD, ...

python scripts/catalogs/cmr_providers.py  # all providers
python scripts/catalogs/cmr_providers.py nsidc  # only lines containing a word
"""

import json
import sys
from urllib.request import urlopen

URL = "https://cmr.earthdata.nasa.gov/search/providers?page_size=200"

with urlopen(URL, timeout=60) as response:
    items = json.load(response)["items"]

words = [word.lower() for word in sys.argv[1:]]
for item in sorted(items, key=lambda item: item["ProviderId"]):
    line = f"{item['ProviderId']}\t{' '.join(item.get('DescriptionOfHolding', '').split())}"
    if not words or any(word in line.lower() for word in words):
        print(line)
