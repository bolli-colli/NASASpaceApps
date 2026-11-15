"""Print the data types (variables) of one NOAA NCEI dataset. Not NASA; no token needed.

python scripts/catalogs/ncei_datatypes.py global-summary-of-the-month        # id <tab> name [units]
python scripts/catalogs/ncei_datatypes.py daily-summaries snow precipitation

Dataset ids: ncei_datasets.py. Data (no token, CSV/JSON):
https://www.ncei.noaa.gov/access/services/data/v1?dataset=global-summary-of-the-month&
dataTypes=PRCP,TAVG&stations=AU000005901&startDate=2020-01-01&endDate=2020-12-31&format=csv
"""

import json
import sys
from urllib.request import urlopen

URL = "https://www.ncei.noaa.gov/access/services/support/v3/datasets/{}.json"

dataset, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
with urlopen(URL.format(dataset), timeout=120) as response:
    data_types = json.load(response)["dataTypes"]

for line in sorted(f"{t['id']}\t{t.get('name', '')} [{t.get('units', '')}]" for t in data_types):
    if not words or any(word in line.lower() for word in words):
        print(line)
