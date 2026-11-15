"""Print the fields of the WoSIS soil profile database (ISRIC GraphQL API). Not NASA.

python scripts/catalogs/wosis_fields.py               # type <tab> field
python scripts/catalogs/wosis_fields.py layer         # only the layer (measurement) fields

WoSIS holds the measured soil profiles behind SoilGrids. Query example:
POST https://graphql.isric.org/wosis/graphql
{"query": "{ wosisLatestProfiles(first: 5) { profileId } }"}
"""

import json
import sys
from urllib.request import Request, urlopen

URL = "https://graphql.isric.org/wosis/graphql"
TYPES = ("WosisLatestSite", "WosisLatestProfile", "WosisLatestLayer", "WosisLatestObservation")
QUERY = " ".join(f'{t}: __type(name: "{t}") {{ fields {{ name }} }}' for t in TYPES)

body = json.dumps({"query": "{" + QUERY + "}"}).encode()
request = Request(URL, body, {"Content-Type": "application/json"})
with urlopen(request, timeout=60) as response:
    types = json.load(response)["data"]

words = [word.lower() for word in sys.argv[1:]]
for name, info in types.items():
    for field in (info or {}).get("fields", []):
        line = f"{name.removeprefix('WosisLatest').lower()}\t{field['name']}"
        if not words or any(word in line.lower() for word in words):
            print(line)
