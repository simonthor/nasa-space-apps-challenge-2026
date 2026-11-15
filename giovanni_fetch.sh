#!/bin/bash
# Fetch one Giovanni "Time Series, Area-Averaged" (service ArAvTs) as CSV into data/giovanni/<region>/.
#
# Runs the request inside an open playwright-cli browser that is logged in to Giovanni with Earthdata
# (open https://giovanni.gsfc.nasa.gov/giovanni/ in it and log in first), since downloads need the login cookie.
#
# usage: giovanni_fetch.sh <region> <bbox W,S,E,N> <start YYYY-MM-DD> <end YYYY-MM-DD> <variable id> [service]
#   e.g. giovanni_fetch.sh south_pole -180,-90,180,-89 1980-01-01 2026-09-30 "M2IMNPASM_5_12_4_T(z=50)"
# With service TmAvMp ("Time Averaged Map"), the map is saved as data/giovanni/<region>/<variable>_TmAvMp.nc.
set -euo pipefail
region=$1; bbox=$2; start=$3; end=$4; variable=$5; service=${6:-ArAvTs}
out=$(dirname "$0")/data/giovanni/$region
mkdir -p "$out"
stem=$out/$(echo "$variable" | tr -c 'A-Za-z0-9_\n' '_')
if [ "$service" = ArAvTs ]; then csv=$stem.csv; extension=.csv; else csv=${stem}_$service.nc; extension=.nc; fi
[ -s "$csv" ] && { echo "exists $csv"; exit 0; }

js() { playwright-cli --raw eval "$1" | python3 -c "import json,sys; sys.stdout.write(json.loads(sys.stdin.read()))"; }

variable_encoded=$(python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "$variable")
query="service=$service&starttime=${start}T00:00:00Z&endtime=${end}T23:59:59Z&bbox=${bbox}&data=${variable_encoded}&portal=GIOVANNI&format=json"
# The Giovanni session id is kept in the userSessions cookie. Giovanni cancels a request while 5 workflows of the
# session are running: then wait and submit again. An empty reply (browser busy) is retried.
for _ in $(seq 1 60); do
  read -r session resultset result <<< "$(js "async () => {
    const cookie = document.cookie.split('; ').find(c => c.startsWith('userSessions='));
    const session = Object.values(JSON.parse(decodeURIComponent(cookie.slice(13))).userSessions)[0].GIOVANNI.session;
    const j = await (await fetch('/giovanni/daac-bin/service_manager.pl?session=' + session + '&$query')).json();
    const rs = j.session.resultset[0];
    return session + ' ' + rs.id + ' ' + rs.result[0].id }" 2> /dev/null || echo "- - -")"
  [ "$session" = - ] && { sleep 10; continue; }

  for _ in $(seq 1 360); do
    status=$(js "async () => {
      const j = await (await fetch('/giovanni/daac-bin/service_manager.pl?session=$session&resultset=$resultset&result=$result&portal=GIOVANNI&format=json')).json();
      const r = j.session.resultset[0].result[0];
      let url = '';
      try { url = r.data[0].fileGroup[0].dataFile[0].dataUrl.find(d => d.label.endsWith('$extension')).value } catch (e) {}
      return r.status[0].percentComplete[0].value + '|' + r.status[0].message[0].value + '|' + url }" 2> /dev/null) \
      || status=""
    percent=${status%%|*}; url=${status##*|}
    if [ "$percent" = 100 ] && [ -n "$url" ]; then
      if [ "$service" = ArAvTs ]; then
        # an empty reply (browser busy) is retried; only a CSV with the time column is kept
        for _ in $(seq 1 10); do
          js "async () => await (await fetch('/giovanni/$url')).text()" > "$csv.part" 2> /dev/null || true
          grep -q "^time" "$csv.part" && { mv "$csv.part" "$csv"; echo "ok $csv ($(wc -l < "$csv") lines)"; exit 0; }
          sleep 5
        done
        rm -f "$csv.part"; echo "FAILED $variable: no time series in the reply from $url"; exit 1
      fi
      # binary NetCDF: passed out of the browser as base64; the map links are not relative to /giovanni/ as the CSV ones
      js "async () => { const blob = await (await fetch(new URL('$url', location.origin + '/giovanni/'))).blob();
        return await new Promise(resolve => { const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(',')[1]); reader.readAsDataURL(blob) }) }" | base64 -d > "$csv"
      if [ "$(head -c 3 "$csv" | tail -c 2)" != HD ] && [ "$(head -c 3 "$csv")" != CDF ]; then
        rm "$csv"; echo "FAILED $variable: not a NetCDF file at $url"; exit 1
      fi
      echo "ok $csv ($(du -h "$csv" | cut -f1))"; exit 0
    fi
    case "$status" in *ancel*|*simultaneous*) sleep 30; continue 2;; *rror*|*ailed*) echo "FAILED $variable: $status"; exit 1;; esac
    sleep 5
  done
  echo "TIMEOUT $variable: $status"; exit 1
done
echo "GAVE UP $variable: $status"; exit 1
