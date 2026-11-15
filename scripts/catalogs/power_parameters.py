"""Print the parameters of NASA POWER (MERRA-2/CERES based weather and solar values).

    python scripts/catalogs/power_parameters.py  # PARAMETER <tab> name [units]
    python scripts/catalogs/power_parameters.py aerosol cloud  # only lines containing a word

Lists the monthly parameters of all three communities (AG, RE, SB) together.
"""

import json
import sys
from urllib.request import urlopen

URL = "https://power.larc.nasa.gov/api/system/manager/parameters?community={}&temporal=monthly"

parameters = {}
for community in ("AG", "RE", "SB"):
    with urlopen(URL.format(community), timeout=120) as response:
        parameters |= json.load(response)

words = [word.lower() for word in sys.argv[1:]]
for parameter, info in sorted(parameters.items()):
    line = f"{parameter}\t{info['name']} [{info.get('units', '')}]"
    if not words or any(word in line.lower() for word in words):
        print(line)
