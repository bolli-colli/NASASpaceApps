"""Print the products AppEEARS can sample (point or area statistics).

    python scripts/catalogs/appeears_products.py  # PRODUCT.VERSION <tab> description
    python scripts/catalogs/appeears_products.py snow albedo  # only lines containing a word

The layers of one product: appeears_layers.py.
"""

import json
import sys
from urllib.request import urlopen

URL = "https://appeears.earthdatacloud.nasa.gov/api/product"

with urlopen(URL, timeout=60) as response:
    products = json.load(response)

words = [word.lower() for word in sys.argv[1:]]
for product in sorted(products, key=lambda product: product["ProductAndVersion"]):
    line = f"{product['ProductAndVersion']}\t{product['Description']} ({product['Platform']})"
    if not words or any(word in line.lower() for word in words):
        print(line)
