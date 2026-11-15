"""Print the OB.DAAC data type ids (dtid) needed by its file search.

python scripts/catalogs/obdaac_datatypes.py              # dtid <tab> name <tab> description
python scripts/catalogs/obdaac_datatypes.py MODISA_L3m   # only lines containing a word

Sensor ids: 6 SeaWiFS, 7 Aqua-MODIS, 8 Terra-MODIS, 14 SNPP-VIIRS, 29/36 S3A/S3B-OLCI,
33 NOAA20-VIIRS, 42 PACE-OCI (full list: https://oceandata.sci.gsfc.nasa.gov/api/file_search/help/).
"""

import html
import re
import sys
from urllib.request import urlopen

URL = "https://oceandata.sci.gsfc.nasa.gov/api/file_search/datatype_lookup/"

with urlopen(URL, timeout=120) as response:
    page = response.read().decode()

words = [word.lower() for word in sys.argv[1:]]
for row in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", page):
    cells = [
        html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
        for c in re.findall(r"(?s)<td[^>]*>(.*?)</td>", row)
    ]
    line = "\t".join(cells)
    if cells and (not words or any(word in line.lower() for word in words)):
        print(line)
