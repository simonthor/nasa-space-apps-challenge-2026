#!/bin/bash
# Fetch the time series for the garbage-patch analysis (bounding boxes as in giovanni.py REGIONS), 4 at a time.
# Existing CSVs are skipped. Needs a logged-in playwright-cli browser, see giovanni_fetch.sh.
cd "$(dirname "$0")"
MERRA2="1980-01-01 2026-09-30"   # MERRA-2 monthly
MODIS="2002-07-04 2025-11-30"    # MODIS-Aqua ocean colour monthly (R2022)
MODIS_SST="2002-07-04 2026-08-31"
NOBM="1998-01-01 2015-12-31"     # NASA Ocean Biogeochemical Model

GPGP=-155,35,-135,42
PATCHES="north_atlantic_patch -70,25,-40,35
south_pacific_patch -115,-35,-95,-25
south_atlantic_patch -20,-35,0,-25
indian_ocean_patch 70,-35,90,-25
north_pacific_north -155,45,-135,52
north_pacific_south -155,20,-135,27
north_atlantic_north -70,40,-40,50
north_atlantic_south -70,10,-40,20
south_pacific_north -115,-20,-95,-10
south_pacific_south -115,-50,-95,-40
south_atlantic_north -20,-20,0,-10
south_atlantic_south -20,-50,0,-40
indian_ocean_north 70,-20,90,-10
indian_ocean_south 70,-50,90,-40
gpgp_model -151,28,-131,38
gpgp_model_north -151,43,-131,53
gpgp_model_south -151,13,-131,23"

# Broad check of the Great Pacific Garbage Patch, then the variables that discriminate it, in every other region.
# The MODIS IOP variables (adg_443, aph_443, bbp_443) and the euphotic depth are left out: Giovanni fails on them.
{
  # Global and ocean means of the ocean variables, to compare with the patches (boxes as in giovanni.py OCEANS)
  for region in "global -180,-90,180,90" "pacific_northwest 120,-10,180,60" "pacific_southwest 150,-60,180,-10" \
                "pacific_east -180,-60,-100,60" "pacific_southeast -100,-60,-70,8" "atlantic_north -75,0,-10,60" \
                "atlantic_south -65,-60,20,0" "indian_west 20,-60,100,25" "indian_east 100,-60,142,-10"; do
    read -r name bbox <<< "$region"
    for v in M2TMNXOCN_5_12_4_TSKINWTR M2TMNXOCN_5_12_4_RAINOCN M2TMNXFLX_5_12_4_SPEED; do
      echo $name $bbox $MERRA2 $v
    done
    for v in MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a MODISA_L3m_FLH_Mo_4km_R2022_0_nflh MODISA_L3m_POC_Mo_4km_R2022_0_poc \
             MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490; do
      echo $name $bbox $MODIS $v
    done
  done

  for v in M2TMNXOCN_5_12_4_TSKINWTR M2TMNXSLV_5_12_4_SLP M2TMNXSLV_5_12_4_U10M M2TMNXSLV_5_12_4_V10M \
           M2TMNXFLX_5_12_4_SPEED M2TMNXOCN_5_12_4_TAUXWTR M2TMNXOCN_5_12_4_TAUYWTR M2TMNXAER_5_12_4_TOTEXTTAU \
           M2TMNXAER_5_12_4_SSEXTTAU M2TMNXOCN_5_12_4_RAINOCN M2TMNXFLX_5_12_4_EVAP M2TMNXRAD_5_12_4_CLDTOT \
           M2TMNXSLV_5_12_4_T2M; do
    echo gpgp $GPGP $MERRA2 $v
  done
  echo gpgp $GPGP $MODIS_SST MODISA_L3m_NSST_Monthly_9km_R2019_0_sst
  for v in MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a MODISA_L3m_FLH_Mo_4km_R2022_0_nflh MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490 \
           MODISA_L3m_POC_Mo_4km_R2022_0_poc MODISA_L3m_PIC_Mo_4km_R2022_0_pic MODISA_L3m_PAR_Mo_4km_R2022_0_par; do
    echo gpgp $GPGP $MODIS $v
  done
  for v in NOBM_MON_R2017_h NOBM_MON_R2017_rno NOBM_MON_R2017_tot NOBM_MON_R2017_dia NOBM_MON_R2017_cya \
           NOBM_MON_R2017_coc; do
    echo gpgp $GPGP $NOBM $v
  done

  while read -r region bbox; do
    for v in M2TMNXOCN_5_12_4_TSKINWTR M2TMNXSLV_5_12_4_SLP M2TMNXFLX_5_12_4_SPEED M2TMNXOCN_5_12_4_TAUXWTR \
             M2TMNXOCN_5_12_4_TAUYWTR M2TMNXAER_5_12_4_TOTEXTTAU; do
      echo "$region" "$bbox" $MERRA2 $v
    done
    echo "$region" "$bbox" $MODIS_SST MODISA_L3m_NSST_Monthly_9km_R2019_0_sst
    for v in MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a MODISA_L3m_FLH_Mo_4km_R2022_0_nflh MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490 \
             MODISA_L3m_POC_Mo_4km_R2022_0_poc; do
      echo "$region" "$bbox" $MODIS $v
    done
    for v in NOBM_MON_R2017_h NOBM_MON_R2017_rno NOBM_MON_R2017_tot; do
      echo "$region" "$bbox" $NOBM $v
    done
  done <<< "$PATCHES"

  # Wind stress along the edges of each patch box, for the Ekman transport into the box (garbage_patch_ekman.py):
  # zonal stress on 1°-wide strips along the south and north edges, meridional stress along the west and east edges
  while read -r region bbox; do
    IFS=, read -r w s e n <<< "$bbox"
    echo "${region}_edge_south" "$w,$(echo "$s - 0.5" | bc),$e,$(echo "$s + 0.5" | bc)" $MERRA2 M2TMNXOCN_5_12_4_TAUXWTR
    echo "${region}_edge_north" "$w,$(echo "$n - 0.5" | bc),$e,$(echo "$n + 0.5" | bc)" $MERRA2 M2TMNXOCN_5_12_4_TAUXWTR
    echo "${region}_edge_west" "$(echo "$w - 0.5" | bc),$s,$(echo "$w + 0.5" | bc),$n" $MERRA2 M2TMNXOCN_5_12_4_TAUYWTR
    echo "${region}_edge_east" "$(echo "$e - 0.5" | bc),$s,$(echo "$e + 0.5" | bc),$n" $MERRA2 M2TMNXOCN_5_12_4_TAUYWTR
  done <<< "gpgp $GPGP
$(head -4 <<< "$PATCHES")"
} | xargs -P 4 -L 1 ./giovanni_fetch.sh  # Giovanni runs at most 5 simultaneous workflows per session
