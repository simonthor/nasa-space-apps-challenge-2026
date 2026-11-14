#!/bin/bash
# Fetch the CYGNSS L3 ocean microplastic concentration (PO.DAAC CYGNSS_L3_MICROPLASTIC_V3.2) into data/cygnss/.
#
# Each daily file is a 30-day running mean on a 0.25° grid (37°S to 37°N); the files of the 15th of each month are
# taken as the monthly means. Downloads go through the open playwright-cli browser, which must be logged in to
# Earthdata (see giovanni_fetch.sh).
set -euo pipefail
out=$(dirname "$0")/data/cygnss
mkdir -p "$out"
cmr="https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C2893924134-POCLOUD&page_size=2000"
urls=$(for page in 1 2; do curl -s "$cmr&page_num=$page"; echo; done | python3 -c "
import json, sys
for line in sys.stdin:
    for e in json.loads(line)['feed']['entry'] if line.strip() else []:
        if e['time_start'][8:10] == '15':
            print(next(l['href'] for l in e['links'] if l['href'].startswith('https') and l['href'].endswith('.nc')))")

for url in $urls; do
  nc=$out/$(basename "$url")
  [ -s "$nc" ] && continue
  # The first request of a session goes through the Earthdata Login page, which redirects with JavaScript only
  playwright-cli --raw run-code "async page => {
    const request = page.context().request;
    let r = await request.get('$url');
    if (r.url().includes('urs.earthdata')) {
      const login = (await r.text()).match(/https:\/\/archive\.podaac\.earthdata\.nasa\.gov\/login\?code=[^\"' >]+/)[0];
      r = await request.get(login.replace(/&amp;/g, '&'));
    }
    return (await r.body()).toString('base64') }" | python3 -c "
import base64, json, sys
data = base64.b64decode(json.loads(sys.stdin.read()))
assert data[:4] == b'\x89HDF', 'not a NetCDF file'
open(sys.argv[1], 'wb').write(data)" "$nc"
  echo "ok $nc"
done
