"""Print the entries of an NCEI bulk download folder (the "FTP" links of CDO). Not NASA.

python scripts/catalogs/ncei_files.py data/global-summary-of-the-month/access/ AU0000
python scripts/catalogs/ncei_files.py pub/data/ghcn/daily/

Paths are relative to https://www.ncei.noaa.gov/; no token needed.
"""

import re
import sys
from urllib.request import urlopen

path, words = sys.argv[1], [word.lower() for word in sys.argv[2:]]
with urlopen(f"https://www.ncei.noaa.gov/{path.strip('/')}/", timeout=300) as response:
    page = response.read().decode(errors="replace")

for name in re.findall(r'href="([^"?/][^"?]*)"', page):
    if not name.startswith(("http", "..")) and (not words or any(w in name.lower() for w in words)):
        print(name)
