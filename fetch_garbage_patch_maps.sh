#!/bin/bash
# Fetch the time-averaged maps for the garbage-patch analysis into data/giovanni/global_maps/ (one at a time, next to
# the time-series fetches of fetch_garbage_patch.sh). Needs a logged-in playwright-cli browser, see giovanni_fetch.sh.
cd "$(dirname "$0")"
for v in M2TMNXOCN_5_12_4_TAUXWTR M2TMNXOCN_5_12_4_TAUYWTR M2TMNXSLV_5_12_4_SLP M2TMNXFLX_5_12_4_SPEED \
         M2TMNXOCN_5_12_4_TSKINWTR; do
  ./giovanni_fetch.sh global_maps -180,-70,180,70 2003-01-01 2024-12-31 $v TmAvMp
done
./giovanni_fetch.sh global_maps -180,-70,180,70 1998-01-01 2015-12-31 NOBM_MON_R2017_tot TmAvMp
