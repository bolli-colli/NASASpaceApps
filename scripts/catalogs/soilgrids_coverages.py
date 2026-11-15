"""Print the SoilGrids map layers (WCS coverages: property_depth_statistic). Not NASA.

python scripts/catalogs/soilgrids_coverages.py              # all properties
python scripts/catalogs/soilgrids_coverages.py soc clay     # only these properties

Uses the WCS map service, which answers quickly; the REST point query
(https://rest.isric.org/soilgrids/v2.0/properties/query?lon=..&lat=..&property=soc)
works but is slow, and its /properties/layers listing often times out.
"""

import re
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

PROPERTIES = "bdod cec cfvo clay nitrogen ocd ocs phh2o sand silt soc wv0010 wv0033 wv1500"
URL = "https://maps.isric.org/mapserv?map=/map/{}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities"


def capabilities(prop: str) -> str:
    """GetCapabilities of one property; the map server sometimes answers 503, so retry once."""
    for attempt in (1, 2):
        try:
            with urlopen(URL.format(prop), timeout=120) as response:
                return response.read().decode()
        except URLError:
            if attempt == 2:
                raise
            time.sleep(5)
    return ""


failed = []
for prop in sys.argv[1:] or PROPERTIES.split():
    try:
        text = capabilities(prop)
    except URLError as error:
        print(f"{prop}: {error}", file=sys.stderr)
        failed.append(prop)
        continue
    for coverage in re.findall(r"<wcs:CoverageId>([^<]+)</wcs:CoverageId>", text):
        print(coverage)
if failed:
    sys.exit(f"failed: {' '.join(failed)}")
