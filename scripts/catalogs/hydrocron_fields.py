"""Print the SWOT fields Hydrocron can return, per feature type (from its documentation).

python scripts/catalogs/hydrocron_fields.py          # feature <tab> field
python scripts/catalogs/hydrocron_fields.py lake     # only lake fields

Hydrocron has no listing endpoint; the fields page is published as Markdown.
Time series: https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries?
feature=Reach&feature_id=78340600051&start_time=...&end_time=...&fields=reach_id,time_str,wse
"""

import json
import re
import sys
from urllib.request import urlopen

DOCS = "https://podaac.github.io"

with urlopen(f"{DOCS}/hydrocron/user-guide.fields.json", timeout=60) as response:
    markdown_url = DOCS + json.load(response)["frontmatter"]["exports"][0]["url"]
with urlopen(markdown_url, timeout=60) as response:
    markdown = response.read().decode()

words = [word.lower() for word in sys.argv[1:]]
for title, block in re.findall(r"\*\*(.+?) fields\*\*\s*```\w*\n(.*?)```", markdown, re.S):
    for field in re.findall(r"'([^']+)'", block):
        line = f"{title.lower()}\t{field}"
        if not words or any(word in line.lower() for word in words):
            print(line)
