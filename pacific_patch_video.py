"""Video and summary of the modelled Great Pacific Garbage Patch, 1950-2023 (pacific_patch_model.py).

The model counts are in kt of emissions; to turn them into kg of floating plastic, every species run is calibrated
so that the Great Pacific Garbage Patch region (BOX) holds 79,000 t in 2015 (Lebreton et al. 2018, Sci. Rep. 8, 4666).
Two checks of when the patch formed:
- contrast: when the patch region becomes denser than the rest of the North Pacific around it;
- absolute: when the mass in the patch region passes given fractions of the 2015 mass.
and one check against observations: the growth of the mass in the region from 1972-1985 to 1999-2010, which net tows
put at about two orders of magnitude (Goldstein et al. 2012, Biol. Lett. 8, 817).

plots/garbage_patch/pacific_patch.mp4 (CO2-weighted run), plots/garbage_patch/pacific_patch_growth.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FFMpegWriter
from matplotlib.colors import LogNorm

from pacific_patch_model import OSCAR, OUT, PACIFIC_SHARE, RELEASE_POINTS, SPECIES
from plot_style import AQUA, BACKGROUND, BLUE, GRID, INK, INK_SECONDARY, ORANGE, PLOTS, save

EARTH_RADIUS_KM = 6371
PATCH_MASS_2015 = 79e3  # t, Lebreton et al. 2018
# S, N, W, E (lon 0-360). The model gathers the North Pacific debris at about 29°N 135°W, 5° south-east of the patch
# as given on Wikipedia (135-155°W, 35-42°N, WIKIPEDIA_BOX); the patch region covers both
BOX = (25, 42, 200, 230)
WIKIPEDIA_BOX = (35, 42, 205, 225)
# the North Pacific around the patch region, for the contrast
SURROUNDING = (15, 50, 150, 245)
VIDEO_SPECIES = "CO2"
SPECIES_LABEL = {"BC": "black carbon", "NOx": "NOx", "SO2": "SO2", "CO2": "CO2"}
COLORS = {"BC": INK, "NOx": BLUE, "SO2": AQUA, "CO2": ORANGE}

model = np.load(OUT)
times, lat_edges, lon_edges = model["times"], model["lat_edges"], model["lon_edges"]
lat_c, lon_c = (lat_edges[:-1] + lat_edges[1:]) / 2, (lon_edges[:-1] + lon_edges[1:]) / 2
cell_km2 = (EARTH_RADIUS_KM ** 2 * np.radians(np.diff(lon_edges))[None, :]
            * np.abs(np.diff(np.sin(np.radians(lat_edges))))[:, None])
LAT, LON = np.meshgrid(lat_c, lon_c, indexing="ij")
in_box = (LAT >= BOX[0]) & (LAT < BOX[1]) & (LON >= BOX[2]) & (LON < BOX[3])
in_surrounding = (LAT >= SURROUNDING[0]) & (LAT < SURROUNDING[1]) & (LON >= SURROUNDING[2]) & (
    LON < SURROUNDING[3]) & ~in_box
year_2015 = (times > 2015) & (times <= 2016)

mass, concentration, box_mass, contrast = {}, {}, {}, {}
for s in SPECIES:
    counts = model[f"density_{s}"]
    t_per_unit = PATCH_MASS_2015 / counts[year_2015][:, in_box].sum(axis=1).mean()
    mass[s] = counts * t_per_unit  # t per cell
    concentration[s] = mass[s] * 1000 / cell_km2  # kg/km²
    box_mass[s] = pd.Series(mass[s][:, in_box].sum(axis=1), index=times)
    box_mean = box_mass[s] / cell_km2[in_box].sum()
    surrounding_mean = mass[s][:, in_surrounding].sum(axis=1) / cell_km2[in_surrounding].sum()
    contrast[s] = pd.Series(np.where(surrounding_mean > 0, box_mean / np.maximum(surrounding_mean, 1e-30), np.nan),
                            index=times)

emissions = pd.read_csv(Path(__file__).parent / "data" / "emissions" / "pacific_emissions.csv")
emissions["kt_pacific"] = emissions.kt * emissions.country.map(PACIFIC_SHARE).fillna(1)
pacific_total = emissions.groupby(["species", "year"]).kt_pacific.sum()



def first_time_staying_above(series, level):
    """First time from which the series stays at or above the level."""
    below_later = (series < level)[::-1].cummax()[::-1]
    return series.index[~below_later.values][0]


print("When does the patch form? (first time, staying above afterwards)")
for s in SPECIES:
    early = box_mass[s][(times > 1972) & (times <= 1986)].mean()
    late = box_mass[s][(times > 1999) & (times <= 2011)].mean()
    contrast_year = first_time_staying_above(contrast[s], 2)
    percent_1, percent_10 = (first_time_staying_above(box_mass[s], f * PATCH_MASS_2015) for f in [0.01, 0.1])
    print(f"  {s:4}: denser than the surroundings (contrast > 2) from {contrast_year:.1f}; "
          f"box mass > 1 % of 2015 from {percent_1:.1f}, > 10 % from {percent_10:.1f}; "
          f"1988: {box_mass[s][(times > 1988) & (times <= 1989)].mean():.0f} t; "
          f"growth 1972-85 -> 1999-2010: ×{late / early:.1f}")

# --- summary: mass in the box and contrast, for each emission species used as the release weights ---
fig, axes = plt.subplots(1, 2, figsize=(13.87, 5.65))
for s in SPECIES:
    axes[0].plot(times, box_mass[s], color=COLORS[s], lw=2, label=f"released ∝ {SPECIES_LABEL[s]} emissions")
    axes[1].plot(times, contrast[s], color=COLORS[s], lw=2)
axes[0].set_yscale("log")
axes[0].set_ylim(10, 2e5)
axes[0].set_ylabel("Floating plastic in the patch region (t)")
axes[0].set_title("Mass in the Great Pacific Garbage Patch region", fontsize=14)
axes[0].legend(fontsize=11, loc="lower right")
axes[1].axhline(1, color=INK_SECONDARY, lw=0.8)
axes[1].set_ylabel("Patch concentration / surroundings")
axes[1].set_title("Contrast with the rest of the North Pacific", fontsize=14)
for ax in axes:
    for year, text, side in [(1988, "1988: patch predicted\n(Day et al.)", "right"),
                             (1997, "1997: found\n(Moore)", "left")]:
        ax.axvline(year, color=INK_SECONDARY, lw=1, ls=":")
        ax.text(year + (-0.7 if side == "right" else 0.7), 0.97, text, transform=ax.get_xaxis_transform(), va="top",
                ha=side, fontsize=10, color=INK_SECONDARY)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, labelsize=12)
    ax.set_xlim(1950, 2024)
fig.tight_layout()
save(fig, "garbage_patch/pacific_patch_growth.png")

# --- video ---
oscar = np.load(OSCAR)
land = np.where(oscar["n"] > 0, np.nan, 1.0)
points, point_countries = model["release_points"], model["release_countries"]
points_per_country = {c: len(ps) for c, ps in RELEASE_POINTS.items()}
per_country = emissions[emissions.species == VIDEO_SPECIES].pivot_table(index="year", columns="country",
                                                                         values="kt_pacific")
c_series = concentration[VIDEO_SPECIES]
series = box_mass[VIDEO_SPECIES]
emission_series = pacific_total[VIDEO_SPECIES].loc[1950:2023] / 1e6  # Gt/yr

fig = plt.figure(figsize=(13.87, 9.6))
ax_map = fig.add_axes([0.05, 0.3, 0.8, 0.62], anchor="W")
ax_bar = fig.add_axes([0.81, 0.38, 0.012, 0.46])
ax_ts = fig.add_axes([0.07, 0.075, 0.78, 0.16])
ax_map.set_facecolor("#e9eef2")
ax_map.pcolormesh(oscar["lon"], oscar["lat"], land, cmap="Greys", vmin=0, vmax=4)
mesh = ax_map.pcolormesh(lon_edges, lat_edges, np.full(c_series[0].shape, np.nan), cmap="magma_r",
                         norm=LogNorm(0.1, 300))
fig.colorbar(mesh, cax=ax_bar, label="Floating plastic (kg/km²)", extend="both")
bubbles = ax_map.scatter(points[:, 1], points[:, 0], s=0, color=ORANGE, alpha=0.5, edgecolor=INK, lw=0.5)
for (s_, n, w, e), ls in [(BOX, "-"), (WIKIPEDIA_BOX, ":")]:
    ax_map.plot([w, e, e, w, w], [s_, s_, n, n, s_], color=AQUA, lw=2, ls=ls)
for label, x, y in [("China", 112, 33), ("Japan", 139, 39), ("USA", 240, 40), ("Mexico", 252, 24), ("Peru", 285, -9),
                    ("Chile", 288, -30), ("Australia", 140, -27), ("Indonesia", 115, -3), ("Canada", 236, 56)]:
    ax_map.text(x, y, label, fontsize=11, color=INK_SECONDARY, ha="center")
ax_map.set_xlim(100, 290)
ax_map.set_ylim(-55, 62)
ax_map.set_aspect(1.0)
ax_map.set_xticks(range(120, 290, 30), [f"{x}°E" if x <= 180 else f"{360 - x}°W" for x in range(120, 290, 30)])
ax_map.set_yticks(range(-40, 61, 20),
                  [f"{abs(y)}°{'S' if y < 0 else 'N' if y > 0 else ''}" for y in range(-40, 61, 20)])
ax_map.tick_params(length=0, labelsize=11)
title = ax_map.set_title("", loc="left", fontsize=17)
fig.text(0.05, 0.97, "Modelled floating plastic from the Pacific coasts, released in proportion to each country's "
         f"{SPECIES_LABEL[VIDEO_SPECIES]} emissions (bubbles)", fontsize=12, color=INK_SECONDARY)

ax_ts2 = ax_ts.twinx()
ax_ts.set_xlim(1950, 2024)
ax_ts.set_yscale("log")
ax_ts.set_ylim(10, 2e5)
ax_ts.set_ylabel("Patch region (t)", color=AQUA, fontsize=11)
ax_ts2.set_ylabel(f"Pacific-rim {SPECIES_LABEL[VIDEO_SPECIES]} (Gt/yr)", color=ORANGE, fontsize=11)
ax_ts2.set_ylim(0, emission_series.max() * 1.1)
for year, text in [(1988, "1988 predicted"), (1997, "1997 found")]:
    ax_ts.axvline(year, color=INK_SECONDARY, lw=1, ls=":")
    ax_ts.text(year + 0.5, 15, text, fontsize=10, color=INK_SECONDARY)
for ax in [ax_ts, ax_ts2]:
    ax.tick_params(length=0, labelsize=10)
    ax.spines[["top"]].set_visible(False)
line_mass, = ax_ts.plot([], [], color=AQUA, lw=2.5)
line_emission, = ax_ts2.plot([], [], color=ORANGE, lw=2)
fig.text(0.04, 0.004, "Model: OSCAR 2004–2023 mean surface current + eddy diffusion; emissions CEDS v_2025_03_18 "
         "(Pacific-side share).\n79,000 t in the patch region (solid, 25–42°N 130–160°W) in 2015 "
         "(Lebreton et al. 2018). Dotted: patch as on Wikipedia.", fontsize=9, color=INK_SECONDARY)

path = PLOTS / "garbage_patch" / "pacific_patch.mp4"
writer = FFMpegWriter(fps=12, bitrate=6000)
with writer.saving(fig, path, dpi=120):
    for k, t in enumerate(times):
        year = int(t - 1e-6)  # snapshots are at the end of each quarter
        mesh.set_array(np.where(c_series[k] > 0, c_series[k], np.nan).ravel())
        sizes = np.array([per_country.loc[year, c] / points_per_country[c] for c in point_countries])
        bubbles.set_sizes(sizes / 3e3)  # 3 Mt CO2 per year -> 1 pt²
        title.set_text(f"{year}   ·   patch region: {series.iloc[k]:,.0f} t")
        line_mass.set_data(times[:k + 1], series.iloc[:k + 1])
        line_emission.set_data(emission_series.loc[:year].index + 0.5, emission_series.loc[:year].values)
        writer.grab_frame(facecolor=BACKGROUND)
print(path)
