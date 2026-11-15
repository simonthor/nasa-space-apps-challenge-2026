#!/bin/bash
# Fetch yearly mean maps for emissions_patch_video.py as Giovanni time-averaged maps (NetCDF):
# - sea-surface skin temperature (MERRA-2, global, 0.5°), 1980-2023, into data/giovanni/sst_yearly/<year>/;
# - chlorophyll-a (MODIS-Aqua, 4 km), 2003-2023, over the Pacific in a western and an eastern half (Giovanni does
#   not average across the date line), into data/giovanni/chlorophyll_yearly/<year>/{west,east}/.
# PARALLEL at a time (default 1, next to fetch_garbage_patch.sh; Giovanni runs at most 5 workflows per session).
# Existing files are skipped. Needs a logged-in playwright-cli browser, see giovanni_fetch.sh.
cd "$(dirname "$0")"
{
  for year in $(seq 1980 2023); do
    echo "sst_yearly/$year -180,-90,180,90 $year-01-01 $year-12-31 M2TMNXOCN_5_12_4_TSKINWTR TmAvMp"
  done
  for year in $(seq 2003 2023); do
    echo "chlorophyll_yearly/$year/west 100,-55,180,62 $year-01-01 $year-12-31 MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a TmAvMp"
    echo "chlorophyll_yearly/$year/east -180,-55,-70,62 $year-01-01 $year-12-31 MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a TmAvMp"
  done
} | xargs -P "${PARALLEL:-1}" -L 1 ./giovanni_fetch.sh
