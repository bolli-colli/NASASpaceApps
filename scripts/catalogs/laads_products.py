"""Print the products of LAADS DAAC (MODIS/VIIRS atmosphere: clouds, aerosols, ...).

python scripts/catalogs/laads_products.py  # PRODUCT <tab> title
python scripts/catalogs/laads_products.py MOD08 MYD08  # only lines containing a word
"""

import json
import sys
from urllib.request import urlopen

URL = "https://ladsweb.modaps.eosdis.nasa.gov/api/v2/measurements/products"

with urlopen(URL, timeout=120) as response:
    products = json.load(response)

words = [word.lower() for word in sys.argv[1:]]
for product, info in sorted(products.items()):
    line = f"{product}\t{info.get('title', '')}"
    if not words or any(word in line.lower() for word in words):
        print(line)
