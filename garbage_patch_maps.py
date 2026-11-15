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
import numpy as np
import pandas as pd
from scipy import ndimage

from ekman import (
    DRIFT_YEARS,
    EARTH_RADIUS,
    EDGES_LAT,
    EDGES_LON,
    MIN_LATITUDE,
    RHO,
    coriolis,
    ekman_drift,
    load_map,
)
from giovanni import DATA, PATCHES, REGIONS
from plot_style import INK, INK_SECONDARY, SHORT_NAMES, SLIDE_SIZE, save


def box_outline(ax, region, **kwargs):
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    ax.plot([w, e, e, w, w], [s, s, n, n, s], **kwargs)


lat, lon, taux = load_map("M2TMNXOCN_5_12_4_TAUXWTR")
_, _, tauy = load_map("M2TMNXOCN_5_12_4_TAUYWTR")
ocean = np.isfinite(taux) & np.isfinite(tauy)
LON, LAT = np.meshgrid(lon, lat)
f = coriolis(LAT)

# --- Ekman pumping ---
dx = EARTH_RADIUS * np.cos(np.radians(LAT)) * np.radians(np.gradient(lon))[None, :]
dy = EARTH_RADIUS * np.radians(np.gradient(lat))[:, None]
w_ekman = (np.gradient(tauy / (RHO * f), axis=1) / dx - np.gradient(taux / (RHO * f), axis=0) / dy)
w_ekman[np.abs(LAT) < MIN_LATITUDE] = np.nan
w_ekman_m_per_year = w_ekman * 86400 * 365.25

# --- particle drift with the Ekman velocity ---
density, afloat_fraction = ekman_drift(lat, lon, taux, tauy)
print(f"{afloat_fraction:.0%} of the particles still afloat after {DRIFT_YEARS} years")

# candidate patches: the local maxima of the particle concentration
smooth = ndimage.gaussian_filter(density, 2, mode=["nearest", "wrap"])
peaks = (smooth == ndimage.maximum_filter(smooth, size=11, mode=["nearest", "wrap"])) & (smooth > 3)
centres_lat, centres_lon = (EDGES_LAT[:-1] + 1), (EDGES_LON[:-1] + 1)
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
mesh = ax.pcolormesh(EDGES_LON, EDGES_LAT, np.where(density > 0, density, np.nan), cmap="magma_r", vmin=0,
                     vmax=np.nanpercentile(density[density > 0], 99))
for _, c in candidates.iterrows():
    ax.plot(c.lon, c.lat, "o", ms=13, mfc="none", mec="#1baf7a", mew=2.5)
fig.colorbar(mesh, ax=ax, shrink=0.75, pad=0.01, label="Particle concentration (× start)")
fig.tight_layout()
save(fig, "garbage_patch/ekman_particles.png")
