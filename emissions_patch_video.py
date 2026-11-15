"""Videos of the Pacific: each country coloured by its yearly CO2 emissions (CEDS), the ocean by a yearly mean NASA
variable (fetch_yearly_maps.sh): sea-surface temperature (MERRA-2, 1980-2023) and chlorophyll-a (MODIS-Aqua,
2003-2023). Land and ocean have separate colour scales. A reference level is outlined, dashed for the first year and
solid for the current one: the 20 °C isotherm, and 0.07 mg/m³ of chlorophyll, the edge of the least productive
(oligotrophic) gyre waters (Polovina et al. 2008, Geophys. Res. Lett. 35, L03618).

Below the map: the yearly mean in the Great Pacific Garbage Patch box and over the Pacific Ocean (PACIFIC_BOXES), and
the Pacific-rim CO2 emissions, with their correlation.

usage: python emissions_patch_video.py [sst|chlorophyll ...]   (default: both)
data/giovanni/<variable>_yearly_pacific.npz (the yearly maps on a 0.25° grid over the map);
plots/garbage_patch/emissions_<variable>.mp4
"""
import json
import sys

import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
from matplotlib.animation import FFMpegWriter
from matplotlib.colors import LogNorm, Normalize
from matplotlib.lines import Line2D
from matplotlib.path import Path as Polygon
from matplotlib.ticker import MaxNLocator
from scipy import stats

from giovanni import DATA, PACIFIC_BOXES, REGIONS
from pacific_patch_model import PACIFIC_SHARE
from plot_style import AQUA, BACKGROUND, BLUE, INK, INK_SECONDARY, PLOTS

SPECIES = "CO2"
FRAMES_PER_YEAR = 4  # the colours are interpolated between years
LON_RANGE, LAT_RANGE = (100, 290), (-55, 62)  # map, lon 0-360
GRID_LON = np.arange(LON_RANGE[0], LON_RANGE[1], 0.25) + 0.125
GRID_LAT = np.arange(LAT_RANGE[0], LAT_RANGE[1], 0.25) + 0.125
COUNTRIES = DATA.parent / "natural_earth" / "ne_50m_admin_0_countries.geojson"
OCEAN = {
    # 1981 on: two months of 1980 are ~10 K too cold in the Giovanni MERRA-2 output (see giovanni.load_series)
    "sst": dict(variable="M2TMNXOCN_5_12_4_TSKINWTR", folders=[""], years=range(1981, 2024),
                to_display=lambda x: x - 273.15,
                label="Sea-surface temperature (°C)", unit="°C", cmap="RdYlBu_r", norm=Normalize(0, 30), level=20,
                level_label="20 °C isotherm", source="MERRA-2 sea-surface skin temperature"),
    "chlorophyll": dict(variable="MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a", folders=["west", "east"],
                        years=range(2003, 2024), to_display=lambda x: x, label="Chlorophyll-a (mg/m³)", unit="mg/m³",
                        cmap="YlGn", norm=LogNorm(0.03, 3), level=0.07, level_label="0.07 mg/m³ (oligotrophic edge)",
                        source="MODIS-Aqua chlorophyll-a, 4 km"),
}


def yearly_maps(name):
    """The yearly maps on the 0.25° grid of the map (nearest source cell), cached."""
    cache = DATA / f"{name}_yearly_pacific.npz"
    if cache.exists():
        return np.load(cache)["maps"]
    config, maps = OCEAN[name], []
    for year in config["years"]:
        mean = np.full((len(GRID_LAT), len(GRID_LON)), np.nan)
        for folder in config["folders"]:
            path = DATA / f"{name}_yearly" / str(year) / folder / f"{config['variable']}_TmAvMp.nc"
            with netCDF4.Dataset(path) as nc:
                field = np.squeeze(nc[config["variable"]][:].filled(np.nan)).astype(float)
                lat, lon = nc["lat"][:].data, nc["lon"][:].data % 360
            rows = np.abs(lat[:, None] - GRID_LAT[None, :]).argmin(axis=0)
            cols = np.abs(lon[:, None] - GRID_LON[None, :]).argmin(axis=0)
            half_step = np.abs(np.diff(lon)).min() / 2
            inside = (GRID_LON >= lon.min() - half_step) & (GRID_LON <= lon.max() + half_step)
            mean[:, inside] = config["to_display"](field[np.ix_(rows, cols[inside])])
        maps.append(mean)
        print(year, flush=True)
    np.savez_compressed(cache, maps=np.array(maps, dtype=np.float32))
    return np.array(maps)


# countries rasterised on the 0.25° grid of the map
GLON, GLAT = np.meshgrid((GRID_LON + 180) % 360 - 180, GRID_LAT)
points = np.column_stack([GLON.ravel(), GLAT.ravel()])
country_of_cell = np.full(GLON.shape, "", dtype=object)
for feature in json.loads(COUNTRIES.read_text())["features"]:
    properties = feature["properties"]
    code = (properties["ISO_A3"] if properties["ISO_A3"] != "-99" else properties["ADM0_A3"]).lower()
    geometry = feature["geometry"]
    for polygon in geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]:
        ring = np.array(polygon[0])  # exterior ring; lakes and other holes are ignored
        lo, hi = ring.min(axis=0), ring.max(axis=0)
        candidates = np.flatnonzero((points[:, 0] >= lo[0]) & (points[:, 0] <= hi[0])
                                    & (points[:, 1] >= lo[1]) & (points[:, 1] <= hi[1]))
        country_of_cell.ravel()[candidates[Polygon(ring).contains_points(points[candidates])]] = code
land = country_of_cell != ""
codes, cell_index = np.unique(country_of_cell, return_inverse=True)
cell_index = cell_index.reshape(country_of_cell.shape)

ceds = pd.read_csv(DATA.parent / "emissions" / "ceds" / f"{SPECIES}_CEDS_estimates_by_country_v_2025_03_18.csv")
by_country = ceds.set_index("country").filter(like="X").rename(columns=lambda c: int(c[1:]))  # kt/yr
emission_table = by_country.reindex(codes)  # countries x years; NaN for land without CEDS data
missing = sorted(set(codes) - set(by_country.index) - {""})
print(f"Land without CEDS emissions (grey): {', '.join(missing)}")
pacific = pd.read_csv(DATA.parent / "emissions" / "pacific_emissions.csv").query("species == @SPECIES")
pacific_total = (pacific.kt * pacific.country.map(PACIFIC_SHARE).fillna(1)).groupby(pacific.year).sum() / 1e6


def land_field(year_float, last_year):
    year, weight = int(year_float), year_float % 1
    values = (1 - weight) * emission_table[year].values + weight * emission_table[min(year + 1, last_year)].values
    return np.where(land, values[cell_index], np.nan)


def box_mask(bbox):
    w, s, e, n = map(float, bbox.split(","))
    lon = (GRID_LON[None, :] + 180) % 360 - 180
    return (GRID_LAT[:, None] >= s) & (GRID_LAT[:, None] <= n) & (lon >= w) & (lon <= e)


def area_mean(field, mask):
    weight = np.cos(np.radians(GRID_LAT))[:, None] * mask * np.isfinite(field)
    return np.nansum(field * weight) / weight.sum()


patch_mask = box_mask(REGIONS["gpgp"][1])
pacific_mask = np.any([box_mask(bbox) for _, bbox in PACIFIC_BOXES.values()], axis=0) & ~land
for name in sys.argv[1:] or list(OCEAN):
    config = OCEAN[name]
    years = list(config["years"])
    maps = yearly_maps(name)
    patch = pd.Series([area_mean(m, patch_mask) for m in maps], index=years)
    pacific_mean = pd.Series([area_mean(m, pacific_mask) for m in maps], index=years)
    emissions = pacific_total.loc[years[0]:years[-1]]
    patch_common = patch.loc[emissions.index]
    r, p = stats.pearsonr(emissions, patch_common)
    r_detrended, p_detrended = stats.pearsonr(*(s - np.polyval(np.polyfit(s.index, s, 1), s.index)
                                                for s in (emissions, patch_common)))
    print(f"{name}: patch box vs Pacific-rim {SPECIES} emissions r = {r:.2f} (p = {p:.2g}); after removing both linear "
          f"trends r = {r_detrended:.2f} (p = {p_detrended:.2g})")

    fig = plt.figure(figsize=(13.87, 9.6))
    ax_map = fig.add_axes([0.05, 0.3, 0.74, 0.62], anchor="W")
    ax_land_bar = fig.add_axes([0.80, 0.66, 0.012, 0.22])
    ax_ocean_bar = fig.add_axes([0.80, 0.33, 0.012, 0.22])
    ax_ts = fig.add_axes([0.07, 0.075, 0.74, 0.16])
    ax_map.set_facecolor("#ffffff")
    ocean_mesh = ax_map.pcolormesh(GRID_LON, GRID_LAT, np.where(land, np.nan, maps[0]), cmap=config["cmap"],
                                   norm=config["norm"])
    ax_map.pcolormesh(GRID_LON, GRID_LAT, np.where(land & np.isnan(land_field(years[0], years[-1])), 1.0, np.nan),
                      cmap="Greys", vmin=0, vmax=3)
    land_mesh = ax_map.pcolormesh(GRID_LON, GRID_LAT, land_field(years[0], years[-1]), cmap="Purples",
                                  norm=LogNorm(1e2, 1e7))
    fig.colorbar(land_mesh, cax=ax_land_bar, label=f"{SPECIES} emissions (kt/yr)", extend="both")
    fig.colorbar(ocean_mesh, cax=ax_ocean_bar, label=config["label"], extend="both")
    for ax, text in [(ax_land_bar, "Land"), (ax_ocean_bar, "Ocean")]:
        ax.set_title(text, fontsize=12, loc="left", pad=12)
    ax_map.contour(GRID_LON, GRID_LAT, np.where(land, np.nan, maps[0]), [config["level"]], colors=INK,
                   linewidths=1.2, linestyles="--")
    current_level = []
    w, s_, e, n = map(float, REGIONS["gpgp"][1].split(","))
    ax_map.plot(np.array([w, e, e, w, w]) + 360, [s_, s_, n, n, s_], color=AQUA, lw=2.2)
    ax_map.legend(handles=[Line2D([], [], color=INK, ls="--", label=f"{config['level_label']}, {years[0]}"),
                           Line2D([], [], color=INK, label=f"{config['level_label']}, current year"),
                           Line2D([], [], color=AQUA, lw=2.2, label="Great Pacific Garbage Patch")],
                  loc="lower left", fontsize=10, framealpha=0.85)
    ax_map.set_xlim(*LON_RANGE)
    ax_map.set_ylim(*LAT_RANGE)
    ax_map.set_aspect(1.0)
    ax_map.set_xticks(range(120, 290, 30), [f"{x}°E" if x <= 180 else f"{360 - x}°W" for x in range(120, 290, 30)])
    ax_map.set_yticks(range(-40, 61, 20),
                      [f"{abs(y)}°{'S' if y < 0 else 'N' if y > 0 else ''}" for y in range(-40, 61, 20)])
    ax_map.tick_params(length=0, labelsize=11)
    title = ax_map.set_title("", loc="left", fontsize=17)
    fig.text(0.05, 0.97, f"Land: each country's {SPECIES} emissions. Ocean: yearly mean "
             f"{config['label'].split(' (')[0].lower()}.", fontsize=12, color=INK_SECONDARY)

    ax_ts2 = ax_ts.twinx()
    ax_ts.set_xlim(years[0], years[-1] + 1)
    ax_ts.xaxis.set_major_locator(MaxNLocator(integer=True))
    margin = (max(patch.max(), pacific_mean.max()) - min(patch.min(), pacific_mean.min())) * 0.15
    ax_ts.set_ylim(min(patch.min(), pacific_mean.min()) - margin, max(patch.max(), pacific_mean.max()) + margin)
    ax_ts.set_ylabel(config["unit"], fontsize=11)
    ax_ts2.set_ylim(0, emissions.max() * 1.1)
    ax_ts2.set_ylabel(f"Pacific-rim {SPECIES}\n(Gt/yr)", color="#6a51a3", fontsize=11)
    ax_ts.text(0.01, 0.95, f"Patch vs emissions: r = {r:.2f}; after removing both linear trends r = {r_detrended:.2f} "
               f"(p = {p_detrended:.2f})", transform=ax_ts.transAxes, fontsize=10, color=INK_SECONDARY, va="top")
    for ax in [ax_ts, ax_ts2]:
        ax.tick_params(length=0, labelsize=10)
        ax.spines[["top"]].set_visible(False)
    line_patch, = ax_ts.plot([], [], color=AQUA, lw=2.5, marker="o", ms=3, label="Garbage patch box")
    line_pacific, = ax_ts.plot([], [], color=BLUE, lw=2, marker="o", ms=3, label="Pacific Ocean")
    line_emission, = ax_ts2.plot([], [], color="#6a51a3", lw=2, label=f"Pacific-rim {SPECIES} emissions")
    ax_ts.legend(handles=[line_patch, line_pacific, line_emission], fontsize=9, loc="lower right", ncol=3)
    fig.text(0.04, 0.004, f"Data: {config['source']} via NASA Giovanni; CEDS v_2025_03_18 emissions by country; "
             "borders Natural Earth 1:50m. Grey land: no CEDS data.\nPacific-rim total: countries around the Pacific, "
             "Pacific-side share. Patch box 135–155°W, 35–42°N.", fontsize=9, color=INK_SECONDARY)

    path = PLOTS / "garbage_patch" / f"emissions_{name}.mp4"
    writer = FFMpegWriter(fps=8, bitrate=6000)
    with writer.saving(fig, path, dpi=120):
        for k in range((len(years) - 1) * FRAMES_PER_YEAR + 1):
            i, weight = divmod(k, FRAMES_PER_YEAR)
            weight /= FRAMES_PER_YEAR
            ocean = maps[i] if weight == 0 else (1 - weight) * maps[i] + weight * maps[i + 1]
            ocean_mesh.set_array(np.where(land, np.nan, ocean).ravel())
            land_mesh.set_array(land_field(years[i] + weight, years[-1]).ravel())
            for artist in current_level:
                artist.remove()
            current_level = [ax_map.contour(GRID_LON, GRID_LAT, np.where(land, np.nan, ocean), [config["level"]],
                                            colors=INK, linewidths=1.6)]
            title.set_text(f"{years[i]}")
            line_patch.set_data(patch.index[:i + 1] + 0.5, patch.values[:i + 1])
            line_pacific.set_data(pacific_mean.index[:i + 1] + 0.5, pacific_mean.values[:i + 1])
            line_emission.set_data(emissions.index[:i + 1] + 0.5, emissions.values[:i + 1])
            writer.grab_frame(facecolor=BACKGROUND)
    plt.close(fig)
    print(path)
