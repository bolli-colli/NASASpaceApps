"""Print the variables the Giovanni API accepts, one per line.

python scripts/catalogs/giovanni_variables.py            # all variables
python scripts/catalogs/giovanni_variables.py OMI MERRA  # only ids containing one of the words
"""

import json
import sys
from urllib.request import urlopen

URL = "https://api.giovanni.earthdata.nasa.gov/configured-variables/"

with urlopen(URL, timeout=60) as response:
    variables = json.load(response)["configured_variables"]

words = [word.lower() for word in sys.argv[1:]]
for variable in sorted(variables):
    if not words or any(word in variable.lower() for word in words):
        print(variable)
