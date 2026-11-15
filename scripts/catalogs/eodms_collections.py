"""Print the collections of EODMS (Natural Resources Canada: RADARSAT, RCM, air photos). Not NASA.

python scripts/catalogs/eodms_collections.py          # id <tab> title
python scripts/catalogs/eodms_collections.py radarsat

Listing is open. Search and order use HTTP basic auth with the EODMS username and
password (there is no token): https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi/search?
collection=RCMImageProducts&...  Python client: pip install py-eodms-rapi
"""

import sys
import xml.etree.ElementTree as ET
from urllib.request import urlopen

URL = "https://www.eodms-sgdot.nrcan-rncan.gc.ca/wes/rapi/collections"

with urlopen(URL, timeout=120) as response:
    root = ET.fromstring(response.read())

words = [word.lower() for word in sys.argv[1:]]
for element in root.iter():
    if element.tag.endswith("collection") and element.get("collectionId"):
        line = f"{element.get('collectionId')}\t{element.get('title', '')}"
        if not words or any(word in line.lower() for word in words):
            print(line)
