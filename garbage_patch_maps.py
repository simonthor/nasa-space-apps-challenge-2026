"""Where does floating debris collect? Maps from the MERRA-2 wind stress (Giovanni time-averaged maps, 2003-2024).

The wind-driven Ekman transport M = τ × ẑ / (ρ f) (Vallis, Atmospheric and Oceanic Fluid Dynamics, ch. 5) is the
convergent part of the surface flow that gathers floating plastic into the subtropical gyres (Kubota 1994, J. Oceanogr.
50, 361; Maximenko et al. 2012, Mar. Pollut. Bull. 65, 51); the geostrophic gyre circulation itself is nearly
divergence-free. So
- the Ekman pumping w_E = curl(τ / (ρ f)) shows where surface water converges (w_E < 0: downwelling), and
- virtual floating particles released uniformly over the ocean and drifted with the Ekman velocity M / H gather in
  the same places: the candidate garbage patches.
Then the CYGNSS microplastic product (data/cygnss/) and its time series in the patches.

plots/garbage_patch/ekman_*.png, cygnss_*.png; data/garbage_patch_candidates.csv.
"""

import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator

from giovanni import DATA, PATCHES, REGIONS
from plot_style import INK, INK_SECONDARY, SHORT_NAMES, SLIDE_SIZE, save

RHO = 1025  # sea water density, kg/m³
OMEGA = 7.2921e-5  # Earth's rotation rate, 1/s
EARTH_RADIUS = 6.371e6  # m
EKMAN_DEPTH = 50  # m, depth over which the Ekman transport is spread for the particle drift
MIN_LATITUDE = 5  # degrees: f -> 0 at the equator; |f| is held at its value at 5° closer to it
DRIFT_YEARS = 10


def load_map(variable):
    """Time-averaged Giovanni map: latitudes, longitudes (both ascending) and the field (NaN where missing)."""
    with netCDF4.Dataset(DATA / "global_maps" / f"{variable}_TmAvMp.nc") as nc:
        name = next(v for v in nc.variables if nc[v].ndim >= 2)
        field = np.squeeze(nc[name][:].filled(np.nan)).astype(float)
        return nc["lat"][:].data.astype(float), nc["lon"][:].data.astype(float), field


def box_outline(ax, region, **kwargs):
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    ax.plot([w, e, e, w, w], [s, s, n, n, s], **kwargs)


lat, lon, taux = load_map("M2TMNXOCN_5_12_4_TAUXWTR")
_, _, tauy = load_map("M2TMNXOCN_5_12_4_TAUYWTR")
ocean = np.isfinite(taux) & np.isfinite(tauy)
LON, LAT = np.meshgrid(lon, lat)
f = 2 * OMEGA * np.sin(np.radians(LAT))
f_limited = np.where(LAT >= 0, 1, -1) * np.maximum(np.abs(f), 2 * OMEGA * np.sin(np.radians(MIN_LATITUDE)))

# --- Ekman pumping ---
dx = EARTH_RADIUS * np.cos(np.radians(LAT)) * np.radians(np.gradient(lon))[None, :]
dy = EARTH_RADIUS * np.radians(np.gradient(lat))[:, None]
w_ekman = (np.gradient(tauy / (RHO * f), axis=1) / dx - np.gradient(taux / (RHO * f), axis=0) / dy)
w_ekman[np.abs(LAT) < MIN_LATITUDE] = np.nan
w_ekman_m_per_year = w_ekman * 86400 * 365.25

# --- particle drift with the Ekman velocity ---
u_ekman = np.nan_to_num(tauy / (RHO * f_limited * EKMAN_DEPTH))
v_ekman = np.nan_to_num(-taux / (RHO * f_limited * EKMAN_DEPTH))
# periodic in longitude
lon_periodic = np.concatenate([lon - 360, lon, lon + 360])
interpolators = [RegularGridInterpolator((lat, lon_periodic), np.tile(field, 3), bounds_error=False, fill_value=0)
                 for field in (u_ekman, v_ekman, ocean.astype(float))]


def velocity(p):
    """Ekman velocity in degrees/day at particle positions p = (lat, lon)."""
    u, v = interpolators[0](p), interpolators[1](p)
    return np.column_stack([np.degrees(v / EARTH_RADIUS),
                            np.degrees(u / (EARTH_RADIUS * np.cos(np.radians(p[:, 0]))))]) * 86400


# one particle per 1°x1° ocean cell between 60°S and 60°N
start = np.array([(y, x) for y in np.arange(-59.5, 60, 1) for x in np.arange(-179.5, 180, 1)])
start = start[interpolators[2](start) > 0.99]
p = start.copy()
afloat = np.ones(len(p), bool)
for day in range(int(DRIFT_YEARS * 365.25)):
    k1 = velocity(p[afloat])
    k2 = velocity(p[afloat] + k1 / 2)  # midpoint step (RK2), dt = 1 day
    p[afloat] += k2
    p[:, 1] = (p[:, 1] + 180) % 360 - 180
    p[:, 0] = np.clip(p[:, 0], -89, 89)
    afloat &= interpolators[2](p) > 0.5  # particles reaching the coast stay there (beached)
print(f"{len(p)} particles, {afloat.mean():.0%} still afloat after {DRIFT_YEARS} years")

# density of the afloat particles on a 2° grid, relative to the uniform start; candidate patches are its local maxima
edges_lat, edges_lon = np.arange(-70, 71, 2), np.arange(-180, 181, 2)
density = np.histogram2d(p[afloat, 0], p[afloat, 1], [edges_lat, edges_lon])[0]
density /= np.histogram2d(start[:, 0], start[:, 1], [edges_lat, edges_lon])[0].clip(1)
smooth = ndimage.gaussian_filter(density, 2, mode=["nearest", "wrap"])
peaks = (smooth == ndimage.maximum_filter(smooth, size=11, mode=["nearest", "wrap"])) & (smooth > 3)
centres_lat, centres_lon = (edges_lat[:-1] + 1), (edges_lon[:-1] + 1)
# near the equator the drift is set by the limited f, so maxima there are not trusted
candidates = pd.DataFrame([dict(lat=centres_lat[i], lon=centres_lon[j], concentration=smooth[i, j])
                           for i, j in zip(*np.nonzero(peaks)) if abs(centres_lat[i]) >= 2 * MIN_LATITUDE]
                          ).sort_values("concentration", ascending=False)


def in_box(lat_, lon_, region):
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    return w - 5 <= lon_ <= e + 5 and s - 5 <= lat_ <= n + 5


candidates["known_patch"] = [next((SHORT_NAMES[r] for r in PATCHES if in_box(y, x, r)), "")
                             for y, x in zip(candidates.lat, candidates.lon)]
candidates.to_csv(DATA.parent / "garbage_patch_candidates.csv", index=False)
print(candidates.to_string(index=False, float_format=lambda v: f"{v:.3g}"))


def map_axes():
    """Map of 50°S-52°N with the known patches; title and notes are on the slide."""
    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    ax.set_facecolor("#d9d7d0")  # land
    ax.set_xlim(-180, 180)
    ax.set_ylim(-50, 52)
    ax.set_aspect(1.4)
    ax.set_xticks(range(-180, 181, 60), [f"{abs(x)}°{'W' if x < 0 else 'E' if x > 0 else ''}"
                                          for x in range(-180, 181, 60)])
    ax.set_yticks(range(-40, 41, 20), [f"{abs(y)}°{'S' if y < 0 else 'N' if y > 0 else ''}"
                                        for y in range(-40, 41, 20)])
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    for region in PATCHES:
        box_outline(ax, region, color=INK, lw=1.8)
    return fig, ax


# --- map: Ekman pumping ---
fig, ax = map_axes()
mesh = ax.pcolormesh(lon, lat, np.where(ocean, w_ekman_m_per_year, np.nan), cmap="RdBu", vmin=-60, vmax=60)
ax.quiver(LON[::8, ::10], LAT[::8, ::10], taux[::8, ::10], tauy[::8, ::10], color=INK_SECONDARY, scale=4, width=0.0015)
fig.colorbar(mesh, ax=ax, shrink=0.75, pad=0.01, label="Ekman pumping (m/yr)\nred: downwelling", extend="both")
fig.tight_layout()
save(fig, "garbage_patch/ekman_pumping.png")

# --- map: where Ekman drift gathers floating particles ---
fig, ax = map_axes()
ax.pcolormesh(lon, lat, np.where(ocean, 1, np.nan), cmap="Greys", vmin=0, vmax=8)  # ocean
mesh = ax.pcolormesh(edges_lon, edges_lat, np.where(density > 0, density, np.nan), cmap="magma_r", vmin=0,
                     vmax=np.nanpercentile(density[density > 0], 99))
for _, c in candidates.iterrows():
    ax.plot(c.lon, c.lat, "o", ms=13, mfc="none", mec="#1baf7a", mew=2.5)
fig.colorbar(mesh, ax=ax, shrink=0.75, pad=0.01, label="Particle concentration (× start)")
fig.tight_layout()
save(fig, "garbage_patch/ekman_particles.png")
