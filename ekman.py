"""Wind-driven (Ekman) surface drift from a Giovanni wind-stress map, shared by garbage_patch_maps.py and
emissions_patch_video.py.

The Ekman volume transport is M = τ × ẑ / (ρ f) (Vallis, Atmospheric and Oceanic Fluid Dynamics, ch. 5); spread over
EKMAN_DEPTH it gives the drift velocity of floating particles.
"""
import netCDF4
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from giovanni import DATA

RHO = 1025  # sea water density, kg/m³
OMEGA = 7.2921e-5  # Earth's rotation rate, 1/s
EARTH_RADIUS = 6.371e6  # m
EKMAN_DEPTH = 50  # m, depth over which the Ekman transport is spread for the particle drift
MIN_LATITUDE = 5  # degrees: f -> 0 at the equator; |f| is held at its value at 5° closer to it
DRIFT_YEARS = 10
EDGES_LAT, EDGES_LON = np.arange(-70, 71, 2), np.arange(-180, 181, 2)  # grid of the particle density


def load_map(variable, folder=DATA / "global_maps"):
    """Time-averaged Giovanni map: latitudes, longitudes (both ascending) and the field (NaN where missing)."""
    with netCDF4.Dataset(folder / f"{variable}_TmAvMp.nc") as nc:
        name = next(v for v in nc.variables if nc[v].ndim >= 2)
        field = np.squeeze(nc[name][:].filled(np.nan)).astype(float)
        return nc["lat"][:].data.astype(float), nc["lon"][:].data.astype(float), field


def coriolis(latitude):
    return 2 * OMEGA * np.sin(np.radians(latitude))


def ekman_drift(lat, lon, taux, tauy):
    """Drift one particle per 1°x1° ocean cell between 60°S and 60°N for DRIFT_YEARS with the Ekman velocity of the
    wind stress (taux, tauy in N/m² on the lat, lon grid; NaN over land). Particles that reach land are beached.

    Returns the concentration of the afloat particles on the EDGES_LAT x EDGES_LON grid relative to the uniform start,
    and the fraction still afloat.
    """
    ocean = np.isfinite(taux) & np.isfinite(tauy)
    LAT = np.meshgrid(lon, lat)[1]
    f_limited = np.where(LAT >= 0, 1, -1) * np.maximum(np.abs(coriolis(LAT)), coriolis(MIN_LATITUDE))
    u_ekman = np.nan_to_num(tauy / (RHO * f_limited * EKMAN_DEPTH))
    v_ekman = np.nan_to_num(-taux / (RHO * f_limited * EKMAN_DEPTH))
    # periodic in longitude
    lon_periodic = np.concatenate([lon - 360, lon, lon + 360])
    u_at, v_at, ocean_at = [RegularGridInterpolator((lat, lon_periodic), np.tile(field, 3), bounds_error=False,
                                                    fill_value=0) for field in (u_ekman, v_ekman, ocean.astype(float))]

    def velocity(p):
        """Ekman velocity in degrees/day at particle positions p = (lat, lon)."""
        return np.column_stack([np.degrees(v_at(p) / EARTH_RADIUS),
                                np.degrees(u_at(p) / (EARTH_RADIUS * np.cos(np.radians(p[:, 0]))))]) * 86400

    start = np.array([(y, x) for y in np.arange(-59.5, 60, 1) for x in np.arange(-179.5, 180, 1)])
    start = start[ocean_at(start) > 0.99]
    p = start.copy()
    afloat = np.ones(len(p), bool)
    for _ in range(int(DRIFT_YEARS * 365.25)):
        k1 = velocity(p[afloat])
        k2 = velocity(p[afloat] + k1 / 2)  # midpoint step (RK2), dt = 1 day
        p[afloat] += k2
        p[:, 1] = (p[:, 1] + 180) % 360 - 180
        p[:, 0] = np.clip(p[:, 0], -89, 89)
        afloat &= ocean_at(p) > 0.5  # particles reaching the coast stay there (beached)
    density = np.histogram2d(p[afloat, 0], p[afloat, 1], [EDGES_LAT, EDGES_LON])[0]
    density /= np.histogram2d(start[:, 0], start[:, 1], [EDGES_LAT, EDGES_LON])[0].clip(1)
    return density, afloat.mean()
