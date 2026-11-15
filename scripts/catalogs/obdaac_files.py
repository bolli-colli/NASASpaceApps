"""Print OB.DAAC file names from its own file search (sensor id + data type id + dates).

python scripts/catalogs/obdaac_files.py 7 1043 2024-01-01 2024-01-31 "*.L3m.MO.CHL*"

7 = Aqua-MODIS, 1043 = MODISA_L3m_OC; ids from obdaac_datatypes.py. The pattern needs
a dot ("*.L3m.MO.CHL*" works, "*CHL*" is rejected). Download a file with
https://oceandata.sci.gsfc.nasa.gov/getfile/<name> (Earthdata login).
"""

import sys
from urllib.parse import urlencode
from urllib.request import urlopen

URL = "https://oceandata.sci.gsfc.nasa.gov/api/file_search?"

sensor_id, dtid, start, end, *pattern = sys.argv[1:]
query = {"sensor_id": sensor_id, "dtid": dtid, "sdate": start, "edate": end, "results_as_file": 1}
if pattern:
    query["search"] = pattern[0]

with urlopen(URL + urlencode(query), timeout=120) as response:
    text = response.read().decode().strip()
if text.startswith(("The database had an error", "Filename pattern invalid")):
    sys.exit(text)
if text != "No Results Found":
    print(text)
