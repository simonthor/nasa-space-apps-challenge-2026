"""CYGNSS L3 ocean microplastic concentration (V3.2, data/cygnss/, fetched by fetch_cygnss.sh) in the garbage patches.

The product converts the anomaly of the ocean surface roughness (mean square slope, MSS) relative to the one
expected for the wind speed into a number density, rho = 4320 exp(-12.06 MSS_anomaly) /km² (ATBD 148-0402-2 Rev 2,
eq. 3). Here: its 2018-2026 mean map, its monthly geometric mean in each patch box (north of 37°N there is no
coverage: the Great Pacific Garbage Patch box is only covered at 35-37°N), and how it relates to the wind speed.

plots/garbage_patch/cygnss_*.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
from scipy import stats
from scipy.interpolate import RegularGridInterpolator

from giovanni import CONTROLS, DATA, PATCHES, REGIONS, fit_trend
from plot_style import AQUA, BLUE, INK, INK_SECONDARY, ORANGE, SHORT_NAMES, SLIDE_SIZE, save, style

files = sorted((DATA.parent / "cygnss").glob("*.nc"))
log_maps, months = [], []
for path in files:
    with netCDF4.Dataset(path) as nc:
        log_maps.append(np.log10(nc["mp_concentration"][0].filled(np.nan)))
        lat, lon = nc["lat"][:].data, (nc["lon"][:].data + 180) % 360 - 180
    months.append(pd.Timestamp(path.name.split(".s")[1][:6] + "01"))
order = np.argsort(lon)
lon, log_maps = lon[order], np.array(log_maps)[:, :, order]
LON, LAT = np.meshgrid(lon, lat)
mean_map = np.nanmean(log_maps, axis=0)

# --- monthly geometric mean in each box ---
series = {}
for region in PATCHES + CONTROLS:
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    box = (LON >= w) & (LON <= e) & (LAT >= s) & (LAT <= n)
    if not box.any():
        continue
    series[region] = pd.Series(10 ** np.nanmean(log_maps[:, box], axis=1), index=months)
    fit = fit_trend(series[region])
    print(f"{REGIONS[region][0]:40} mean {series[region].mean():8.0f} /km²  trend "
          f"{fit['slope_per_decade'] / series[region].mean() * 100:+.1f} %/decade (p = {fit['p_ols_ar1']:.2g}), "
          f"{box.sum()} cells")

# --- relation to wind speed: MERRA-2 2003-2024 mean on the CYGNSS grid ---
speed_path = DATA / "global_maps" / "M2TMNXFLX_5_12_4_SPEED_TmAvMp.nc"
if speed_path.exists():
    with netCDF4.Dataset(speed_path) as nc:
        name = next(v for v in nc.variables if nc[v].ndim >= 2)
        speed = RegularGridInterpolator((nc["lat"][:].data, nc["lon"][:].data),
                                        np.squeeze(nc[name][:].filled(np.nan)), bounds_error=False)((LAT, LON))
    ok = np.isfinite(speed) & np.isfinite(mean_map)
    r, p = stats.pearsonr(speed[ok], mean_map[ok])
    print(f"Pearson r between the mean log10 concentration and the mean wind speed: {r:.2f} (p = {p:.1g})")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hexbin(speed[ok], mean_map[ok], gridsize=60, cmap="Greys", mincnt=1, bins="log")
    for region, color in zip(PATCHES, [ORANGE, BLUE, AQUA, INK, INK_SECONDARY]):
        w, s, e, n = map(float, REGIONS[region][1].split(","))
        box = ok & (LON >= w) & (LON <= e) & (LAT >= s) & (LAT <= n)
        ax.plot(speed[box], mean_map[box], ".", color=color, ms=2, alpha=0.5, label=SHORT_NAMES[region])
    ax.set_xlabel("MERRA-2 mean wind speed (m/s)")
    ax.set_ylabel("CYGNSS mean log10(microplastic /km²)")
    ax.set_title(f"CYGNSS microplastic vs. wind speed (r = {r:.2f})", fontsize=14)
    ax.legend(markerscale=6, fontsize=11)
    style(ax)
    fig.tight_layout()
    save(fig, "garbage_patch/cygnss_vs_wind.png")

# --- mean map ---
fig, ax = plt.subplots(figsize=SLIDE_SIZE)
ax.set_facecolor("#d9d7d0")
mesh = ax.pcolormesh(lon, lat, 10 ** mean_map, cmap="viridis", vmin=10 ** np.nanpercentile(mean_map, 2),
                     vmax=10 ** np.nanpercentile(mean_map, 98))
for region in PATCHES:
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    ax.plot([w, e, e, w, w], [s, s, n, n, s], color=ORANGE, lw=2)
fig.colorbar(mesh, ax=ax, orientation="horizontal", shrink=0.5, pad=0.12,
             label=f"Microplastic (count/km²), mean {months[0]:%Y-%m} to {months[-1]:%Y-%m}")
ax.set_aspect(1.4)
ax.set_ylim(-38, 38)
ax.set_xticks(range(-180, 181, 60),
              [f"{abs(x)}°{'W' if x < 0 else 'E' if x > 0 else ''}" for x in range(-180, 181, 60)])
ax.set_yticks(range(-30, 31, 30), [f"{abs(y)}°{'S' if y < 0 else 'N' if y > 0 else ''}" for y in range(-30, 31, 30)])
ax.tick_params(length=0)
fig.tight_layout()
save(fig, "garbage_patch/cygnss_mean_map.png")

# --- time series ---
fig, ax = plt.subplots(figsize=SLIDE_SIZE)
for region, color in zip(PATCHES + CONTROLS, [ORANGE, BLUE, AQUA, INK, INK_SECONDARY, "#9b59b6", "#b8860b"]):
    if region not in series:
        continue
    ax.plot(series[region].index, series[region].values, color=color, lw=2,
            label=SHORT_NAMES[region].replace("\n", " "))
ax.set_ylabel("Microplastic, box geometric mean (count/km²)")
ax.legend(fontsize=11, ncol=4, loc="upper left")
style(ax)
fig.tight_layout()
save(fig, "garbage_patch/cygnss_series.png")
pd.DataFrame(series).to_csv(Path(DATA.parent / "cygnss_microplastic_by_region.csv"), index_label="month")
