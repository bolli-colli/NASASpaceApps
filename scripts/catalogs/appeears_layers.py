"""Print the layers (variables) of one AppEEARS product.

python scripts/catalogs/appeears_layers.py MOD10A1.061  # layer <tab> description
python scripts/catalogs/appeears_layers.py MCD43A3.061 shortwave  # only lines containing a word
"""

import json
import sys
from urllib.request import urlopen

URL = "https://appeears.earthdatacloud.nasa.gov/api/product/{}"

product, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
with urlopen(URL.format(product), timeout=60) as response:
    layers = json.load(response)

for name, layer in sorted(layers.items()):
    line = f"{name}\t{layer.get('Description', '')} [{layer.get('Units', '')}]"
    if not words or any(word in line.lower() for word in words):
        print(line)
