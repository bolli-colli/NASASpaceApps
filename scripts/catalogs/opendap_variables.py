"""Print the variables inside one file (granule) of a collection, via cloud OPeNDAP.

    python scripts/catalogs/opendap_variables.py M2TMNXAER  # every variable path
    python scripts/catalogs/opendap_variables.py OMAERUVd aerosol  # only paths containing a word

Reads the dataset description (DMR) of the newest granule, so it also works for
collections without CMR variable records. Needs EARTHDATA_TOKEN (environment or .env).
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name={}&page_size=1&sort_key=-start_date"
DMR = "https://opendap.earthdata.nasa.gov/collections/{}/granules/{}.dmr.xml"
TYPES = {"Byte", "Char", "String", "Float32", "Float64", "Structure"} | {
    f"{sign}Int{bits}" for sign in ("", "U") for bits in (8, 16, 32, 64)
}


def token() -> str:
    env = Path(__file__).resolve().parents[2] / ".env"
    if "EARTHDATA_TOKEN" not in os.environ and env.exists():
        for line in env.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "EARTHDATA_TOKEN":
                return value.strip().strip("\"'")
    return os.environ["EARTHDATA_TOKEN"]


def paths(element, prefix=""):
    for child in element:
        tag, name = child.tag.split("}")[-1], child.get("name")
        if tag == "Group":
            yield from paths(child, f"{prefix}/{name}")
        elif tag in TYPES:
            yield f"{prefix}/{name}" if prefix else name


short_name, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
with urlopen(GRANULES.format(short_name), timeout=60) as response:
    granule = json.load(response)["items"][0]
url = DMR.format(granule["meta"]["collection-concept-id"], quote(granule["umm"]["GranuleUR"]))
request = Request(url, headers={"Authorization": f"Bearer {token()}"})
with urlopen(request, timeout=120) as response:
    root = ET.fromstring(response.read())

for line in sorted(paths(root)):
    if not words or any(word in line.lower() for word in words):
        print(line)
