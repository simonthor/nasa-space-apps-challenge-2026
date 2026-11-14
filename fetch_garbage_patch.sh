#!/bin/bash
# Fetch the time series for the garbage-patch analysis (bounding boxes as in giovanni.py REGIONS), 4 at a time.
# Existing CSVs are skipped. Needs a logged-in playwright-cli browser, see giovanni_fetch.sh.
cd "$(dirname "$0")"
MERRA2="1980-01-01 2026-09-30"   # MERRA-2 monthly
MODIS="2002-07-04 2025-11-30"    # MODIS-Aqua ocean colour monthly (R2022)
MODIS_SST="2002-07-04 2026-08-31"
ZEU="2002-07-04 2022-02-28"      # MODIS-Aqua euphotic depth (R2018)
NOBM="1998-01-01 2015-12-31"     # NASA Ocean Biogeochemical Model

GPGP=-155,35,-135,42
PATCHES="north_atlantic_patch -70,25,-40,35
south_pacific_patch -115,-35,-95,-25
south_atlantic_patch -20,-35,0,-25
indian_ocean_patch 70,-35,90,-25
north_pacific_north -155,45,-135,52
north_pacific_south -155,20,-135,27"

# Broad check of the Great Pacific Garbage Patch, then the variables that discriminate it, in every other region
{
  for v in M2TMNXOCN_5_12_4_TSKINWTR M2TMNXSLV_5_12_4_SLP M2TMNXSLV_5_12_4_U10M M2TMNXSLV_5_12_4_V10M \
           M2TMNXFLX_5_12_4_SPEED M2TMNXOCN_5_12_4_TAUXWTR M2TMNXOCN_5_12_4_TAUYWTR M2TMNXAER_5_12_4_TOTEXTTAU \
           M2TMNXAER_5_12_4_SSEXTTAU M2TMNXOCN_5_12_4_RAINOCN M2TMNXFLX_5_12_4_EVAP M2TMNXRAD_5_12_4_CLDTOT \
           M2TMNXSLV_5_12_4_T2M; do
    echo gpgp $GPGP $MERRA2 $v
  done
  echo gpgp $GPGP $MODIS_SST MODISA_L3m_NSST_Monthly_9km_R2019_0_sst
  for v in MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a MODISA_L3m_FLH_Mo_4km_R2022_0_nflh MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490 \
           MODISA_L3m_POC_Mo_4km_R2022_0_poc MODISA_L3m_PIC_Mo_4km_R2022_0_pic MODISA_L3m_IOP_Mo_4km_R2022_0_adg_443 \
           MODISA_L3m_IOP_Mo_4km_R2022_0_aph_443 MODISA_L3m_IOP_Mo_4km_R2022_0_bbp_443 MODISA_L3m_PAR_Mo_4km_R2022_0_par; do
    echo gpgp $GPGP $MODIS $v
  done
  echo gpgp $GPGP $ZEU MODISA_L3m_ZLEE_2018_Zeu_lee
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
             MODISA_L3m_POC_Mo_4km_R2022_0_poc MODISA_L3m_IOP_Mo_4km_R2022_0_adg_443 \
             MODISA_L3m_IOP_Mo_4km_R2022_0_bbp_443; do
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
