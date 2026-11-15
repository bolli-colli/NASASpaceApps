"""Print the AERONET ground stations (sun photometers: aerosol optical depth on the ground).

    python scripts/catalogs/aeronet_sites.py  # site <tab> lon <tab> lat <tab> elevation
    python scripts/catalogs/aeronet_sites.py kanpur davos  # only lines containing a word

Data per site: https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v3?site=Kanpur&...
"""

import sys
from urllib.request import urlopen

URL = "https://aeronet.gsfc.nasa.gov/aeronet_locations_v3.txt"

with urlopen(URL, timeout=60) as response:
    rows = response.read().decode().splitlines()[2:]  # skip title and header lines

words = [word.lower() for word in sys.argv[1:]]
for line in sorted(row.replace(",", "\t") for row in rows if row.strip()):
    if not words or any(word in line.lower() for word in words):
        print(line)
