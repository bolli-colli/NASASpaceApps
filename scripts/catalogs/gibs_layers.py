"""Print the map layers of NASA GIBS (ready-made imagery tiles, WMTS).

python scripts/catalogs/gibs_layers.py  # layer id <tab> title
python scripts/catalogs/gibs_layers.py aerosol cloud  # only lines containing a word
"""

import sys
import xml.etree.ElementTree as ET
from urllib.request import urlopen

URL = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml"
NS = {"w": "http://www.opengis.net/wmts/1.0", "ows": "http://www.opengis.net/ows/1.1"}

with urlopen(URL, timeout=120) as response:
    root = ET.fromstring(response.read())

words = [word.lower() for word in sys.argv[1:]]
for layer in root.iterfind(".//w:Layer", NS):
    line = f"{layer.findtext('ows:Identifier', '', NS)}\t{layer.findtext('ows:Title', '', NS)}"
    if not words or any(word in line.lower() for word in words):
        print(line)
