"""Anthropogenic emissions of black carbon, NOx, SO2 and CO2 of the countries around the Pacific Ocean, 1750-2023.

Data: CEDS v_2025_03_18 emissions by country (fetch_emissions.sh), kt per year; NOx is given as NO2 mass, CO2 is
fossil fuel and industry (no land use). Countries are those with a coast on the Pacific Ocean or its marginal seas
(South and East China Seas, Sea of Japan, Bering, Philippine, Coral and Tasman Seas, Gulf of Thailand). Whole-country
totals: for the USA, Canada, Mexico and Russia most of the emissions are far from the Pacific coast.

data/emissions/pacific_emissions.csv (long format); plots/garbage_patch/pacific_emissions.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from plot_style import AQUA, BLUE, GRID, INK, INK_SECONDARY, ORANGE, SLIDE_SIZE, save

CEDS = Path(__file__).parent / "data" / "emissions" / "ceds"
SPECIES = {"BC": "Black carbon", "NOx": "NOx (as NO2)", "SO2": "SO2", "CO2": "CO2 (fossil, industry)"}
# CEDS country codes (ISO 3166 alpha-3, lower case); Nauru and Tuvalu are not in CEDS
PACIFIC_REGIONS = {
    "East Asia": ["chn", "hkg", "mac", "twn", "kor", "prk", "jpn", "rus"],
    "Southeast Asia": ["phl", "vnm", "khm", "tha", "mys", "sgp", "brn", "idn", "tls"],
    "North America": ["usa", "can", "mex"],
    "Central and South America": ["gtm", "slv", "hnd", "nic", "cri", "pan", "col", "ecu", "per", "chl"],
    "Oceania": ["aus", "nzl", "png", "slb", "vut", "fji", "ncl", "ton", "wsm", "kir", "fsm", "mhl", "plw", "cok",
                "niu", "pyf", "gum", "asm", "tkl", "wlf"],
}
REGION_OF = {country: region for region, countries in PACIFIC_REGIONS.items() for country in countries}

frames = []
for species in SPECIES:
    wide = pd.read_csv(CEDS / f"{species}_CEDS_estimates_by_country_v_2025_03_18.csv")
    long = wide.melt(id_vars=["em", "country", "units"], var_name="year", value_name="kt")
    long["year"] = long["year"].str.lstrip("X").astype(int)
    frames.append(long)
emissions = pd.concat(frames).rename(columns={"em": "species"})
# the row "global" holds international shipping and aviation, which no country is assigned
world = emissions.groupby(["species", "year"]).kt.sum()
pacific = emissions[emissions.country.isin(REGION_OF)].copy()
pacific["region"] = pacific.country.map(REGION_OF)
missing = sorted(set(REGION_OF) - set(pacific.country))
assert not missing, f"not in CEDS: {missing}"
pacific[["species", "region", "country", "year", "units", "kt"]].to_csv(
    CEDS.parent / "pacific_emissions.csv", index=False)

by_region = pacific.groupby(["species", "region", "year"]).kt.sum().unstack("region")
print("Pacific-rim share of the world total, and the largest emitter:")
for species in SPECIES:
    total = by_region.loc[species].sum(axis=1)
    for year in [1900, 1950, 1980, 2000, 2023]:
        top = pacific[(pacific.species == species) & (pacific.year == year)].nlargest(1, "kt").iloc[0]
        print(f"  {species:4} {year}: {total[year]:10.0f} kt, {total[year] / world[species, year]:4.0%} of the world;"
              f" largest {top.country} ({top.kt / total[year]:.0%})")

colors = [ORANGE, AQUA, BLUE, "#9b59b6", INK_SECONDARY]
fig, axes = plt.subplots(1, 4, figsize=SLIDE_SIZE)
for ax, (species, title) in zip(axes, SPECIES.items()):
    data = by_region.loc[species].loc[1850:] / (1e6 if species == "CO2" else 1e3)
    ax.stackplot(data.index, data.T.values, colors=colors, labels=data.columns, alpha=0.9, lw=0)
    ax.plot(world[species].loc[1850:].index, world[species].loc[1850:] / (1e6 if species == "CO2" else 1e3),
            color=INK, lw=1.2, ls="--", label="World")
    ax.set_title(title, fontsize=13)
    ax.set_ylabel("Gt/yr" if species == "CO2" else "Mt/yr", fontsize=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0, labelsize=11)
    ax.set_xlim(1850, 2023)
axes[0].legend(loc="upper left", fontsize=10)
fig.tight_layout()
save(fig, "garbage_patch/pacific_emissions.png")
