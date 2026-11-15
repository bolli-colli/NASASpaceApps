"""Print the file (granule) names of one collection, optionally by name pattern and dates.

python scripts/catalogs/cmr_granules.py MODISA_L3m_CHL "*.MO.*.9km*" 2020-10-01 2020-10-31
python scripts/catalogs/cmr_granules.py PACE_OCI_L3M_BGC "*.MO.*" 2025-07-01 2025-07-31
python scripts/catalogs/cmr_granules.py M2TMNXAER                   # newest 100 files

The pattern is what earthaccess calls granule_name: OB.DAAC (OB_CLOUD) keeps several
variants (DAY/8D/MO, 4km/9km, one file per variable) under one short name.
"""

import json
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

URL = "https://cmr.earthdata.nasa.gov/search/granules.json?"

short_name, rest = sys.argv[1], sys.argv[2:]
query = {"short_name": short_name, "page_size": 100, "sort_key": "-start_date"}
if rest:
    query |= {"readable_granule_name": rest[0], "options[readable_granule_name][pattern]": "true"}
if len(rest) >= 3:
    query["temporal"] = f"{rest[1]}T00:00:00Z,{rest[2]}T23:59:59Z"

with urlopen(URL + urlencode(query), timeout=120) as response:
    for entry in json.load(response)["feed"]["entry"]:
        print(entry["title"])
