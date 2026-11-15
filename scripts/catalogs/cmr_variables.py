"""Print the variables of one collection, from the CMR variable records (UMM-Var).

    python scripts/catalogs/cmr_variables.py M2TMNXAER  # name <tab> long name
    python scripts/catalogs/cmr_variables.py M2TMNXAER 5.12.4 dust  # version, then filter words

Not every collection has variable records; opendap_variables.py reads them from a file.
"""

import json
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

CMR = "https://cmr.earthdata.nasa.gov/search"

short_name, rest = sys.argv[1], sys.argv[2:]
version = rest.pop(0) if rest and rest[0][:1].isdigit() else None
words = [word.lower() for word in rest]

query = {"short_name": short_name, **({"version": version} if version else {})}
with urlopen(f"{CMR}/collections.umm_json?{urlencode(query)}", timeout=60) as response:
    collections = json.load(response)["items"]
if not collections:
    sys.exit(f"no collection {short_name} {version or ''}")
ids = collections[-1]["meta"].get("associations", {}).get("variables", [])

lines = []
for start in range(0, len(ids), 100):
    query = [("page_size", "2000")] + [("concept_id[]", i) for i in ids[start : start + 100]]
    with urlopen(f"{CMR}/variables.json?{urlencode(query)}", timeout=60) as response:
        lines += [f"{v['name']}\t{v.get('long_name', '')}" for v in json.load(response)["items"]]

for line in sorted(lines):
    if not words or any(word in line.lower() for word in words):
        print(line)
