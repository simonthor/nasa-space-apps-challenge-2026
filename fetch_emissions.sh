#!/bin/bash
# Fetch the CEDS anthropogenic emissions by country, 1750-2023 (Community Emissions Data System, release v_2025_03_18,
# Hoesly et al. 2018, Geosci. Model Dev. 11, 369; https://zenodo.org/records/15059443) into data/emissions/ceds/,
# and extract the per-country totals of black carbon, NOx (as NO2), SO2 and CO2.
set -euo pipefail
out=$(dirname "$0")/data/emissions/ceds
mkdir -p "$out"
zip=$out/CEDS_v_2025_03_18_aggregate.zip
[ -s "$zip" ] || curl -sL -o "$zip" \
  "https://zenodo.org/api/records/15059443/files/CEDS_v_2025_03_18_aggregate.zip/content"
for species in BC NOx SO2 CO2; do
  unzip -o -j -q "$zip" "CEDS_v_2025_03_18_aggregate/${species}_CEDS_estimates_by_country_v_2025_03_18.csv" -d "$out"
done
ls "$out"
