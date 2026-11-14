#!/bin/bash
# Fetch every time series used in trends.py and plot_trends.py (bounding boxes as in giovanni.py REGIONS).
# Existing CSVs are skipped. Needs a logged-in playwright-cli browser, see giovanni_fetch.sh.
cd "$(dirname "$0")"
fetch=./giovanni_fetch.sh
MERRA2="1980-01-01 2026-09-30"   # MERRA-2 monthly
MODIS="2002-07-04 2025-10-31"    # MODIS-Aqua monthly

$fetch global -180,-90,180,90 $MERRA2 M2TMNXOCN_5_12_4_TSKINWTR
$fetch global -180,-90,180,90 $MERRA2 M2TMNXSLV_5_12_4_T2M

for v in M2TMNXSLV_5_12_4_T2M M2TMNXSLV_5_12_4_T10M M2TMNXSLV_5_12_4_PS M2TMNXSLV_5_12_4_TQV M2TMNXSLV_5_12_4_TO3 \
         M2TMNXFLX_5_12_4_PRECSNO M2TMNXFLX_5_12_4_SPEED M2TMNXRAD_5_12_4_CLDTOT M2TMNXAER_5_12_4_TOTEXTTAU \
         "M2IMNPASM_5_12_4_T(z=10)" "M2IMNPASM_5_12_4_T(z=50)" "M2IMNPASM_5_12_4_T(z=100)" "M2IMNPASM_5_12_4_T(z=500)"; do
  $fetch south_pole -180,-90,180,-89 $MERRA2 "$v"
done
$fetch antarctic_sea_ice -180,-75,180,-55 $MERRA2 M2TMNXOCN_5_12_4_FRSEAICE

$fetch mediterranean -5,30,36,46 $MERRA2 M2TMNXOCN_5_12_4_TSKINWTR
$fetch mediterranean -5,30,36,46 $MODIS MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a

for site in "orca 5.6,42.4,6.4,42.95" "arca 15.6,35.8,16.6,36.7"; do
  read -r region bbox <<< "$site"
  for v in M2TMNXOCN_5_12_4_TSKINWTR M2TMNXFLX_5_12_4_SPEED M2TMNXAER_5_12_4_DUEXTTAU M2TMNXAER_5_12_4_TOTEXTTAU \
           M2TMNXFLX_5_12_4_PRECTOTCORR; do
    $fetch "$region" "$bbox" $MERRA2 "$v"
  done
  for v in MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490 MODISA_L3m_POC_Mo_4km_R2022_0_poc \
           MODISA_L3m_NSST_Monthly_4km_R2019_0_sst; do
    $fetch "$region" "$bbox" $MODIS "$v"
  done
done
$fetch arca 15.6,35.8,16.6,36.7 $MERRA2 M2TMNXADG_5_12_4_DUDP003
$fetch arca 15.6,35.8,16.6,36.7 $MERRA2 M2TMNXADG_5_12_4_DUWT003

$fetch medoc 4,41.5,6,42.5 $MERRA2 M2TMNXFLX_5_12_4_SPEED
$fetch medoc 4,41.5,6,42.5 $MERRA2 M2TMNXOCN_5_12_4_TSKINWTR
$fetch medoc 4,41.5,6,42.5 $MODIS MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a
