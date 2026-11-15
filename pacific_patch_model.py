"""Floating particles released at the Pacific coasts from 1950 and drifted with the OSCAR mean surface current.

A Lagrangian model in the spirit of Maximenko et al. 2012 (Mar. Pollut. Bull. 65, 51) and Lebreton et al. 2012
(Mar. Pollut. Bull. 64, 653):
- each country of the Pacific rim releases particles at its main Pacific-side coastal cities and river mouths,
  2 per point and month from 1950 (the start of the mass production of plastics);
- they drift with the 2004-2023 mean OSCAR surface current (fetch_oscar.py), plus a random walk for the eddies
  (horizontal eddy diffusivity K = 1000 m²/s);
- particles that reach land are beached and leave the floating population; there is no other sink.
Transport does not depend on how much each source emits, so every particle keeps its country and release year, and
the weights are set afterwards: the country's emissions of BC, NOx, SO2 or CO2 in the release year (CEDS,
pacific_emissions.py) times the share of the country that drains to the Pacific (PACIFIC_SHARE).

data/model/pacific_patch_model.npz: for every quarter 1950-2023, the weighted particle count on a 1° grid for each
species (the release weights are in kt of emissions; pacific_patch_video.py turns them into kg of plastic).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage

OSCAR = Path(__file__).parent / "data" / "oscar" / "oscar_mean_2004_2023.npz"
OUT = Path(__file__).parent / "data" / "model" / "pacific_patch_model.npz"
EARTH_RADIUS = 6.371e6  # m
DIFFUSIVITY = 1000  # m²/s
DT_DAYS = 3
FIRST_YEAR, LAST_YEAR = 1950, 2023
PARTICLES_PER_POINT_PER_MONTH = 2
SPECIES = ["BC", "NOx", "SO2", "CO2"]
GRID_LAT, GRID_LON = np.arange(-70, 71, 1.0), np.arange(0, 361, 1.0)  # edges of the 1° output grid, lon 0-360

# Release points (lat, lon) on the Pacific side of each country: major coastal cities and river mouths
RELEASE_POINTS = {
    "chn": [(31.0, 122.5), (22.0, 113.8), (38.8, 118.5), (36.0, 120.8), (24.4, 118.3)],
    "hkg": [(22.2, 114.2)], "mac": [(22.1, 113.6)], "twn": [(25.2, 121.6), (22.5, 120.2)],
    "kor": [(35.0, 129.1), (37.4, 126.4)], "prk": [(38.9, 125.0), (39.8, 127.7)],
    "jpn": [(35.4, 139.9), (34.5, 135.2), (34.9, 136.8), (33.7, 130.3)], "rus": [(43.0, 131.9)],
    "phl": [(14.5, 120.8), (10.3, 123.9)], "vnm": [(10.3, 106.9), (20.7, 106.9)], "khm": [(10.5, 103.5)],
    "tha": [(13.4, 100.6)], "mys": [(3.8, 103.4), (1.7, 110.4)], "sgp": [(1.25, 103.9)], "brn": [(5.0, 115.0)],
    "idn": [(-6.0, 106.8), (-6.9, 112.8)], "tls": [(-8.5, 125.6)],
    "usa": [(33.7, -118.3), (37.8, -122.6), (46.25, -124.1), (21.3, -157.9)], "can": [(49.2, -123.3)],
    "mex": [(23.2, -106.4), (16.8, -99.9)], "gtm": [(13.9, -90.8)], "slv": [(13.3, -89.3)], "hnd": [(13.3, -87.6)],
    "nic": [(12.1, -86.8)], "cri": [(9.9, -84.8)], "pan": [(8.9, -79.5)], "col": [(3.9, -77.1)],
    "ecu": [(-2.3, -80.0)], "per": [(-12.1, -77.2)], "chl": [(-33.0, -71.7), (-36.8, -73.1)],
    "aus": [(-33.9, 151.3), (-27.3, 153.2)], "nzl": [(-36.8, 174.9), (-41.3, 174.8)],
    "png": [(-9.5, 147.1), (-6.8, 147.0)], "slb": [(-9.4, 160.0)], "vut": [(-17.7, 168.3)], "fji": [(-18.1, 178.4)],
    "ncl": [(-22.3, 166.4)], "ton": [(-21.1, -175.2)], "wsm": [(-13.8, -171.8)], "kir": [(1.4, 173.0)],
    "fsm": [(6.9, 158.2)], "mhl": [(7.1, 171.4)], "plw": [(7.3, 134.5)], "cok": [(-21.2, -159.8)],
    "niu": [(-19.05, -169.9)], "pyf": [(-17.5, -149.6)], "gum": [(13.4, 144.7)], "asm": [(-14.3, -170.7)],
    "tkl": [(-9.2, -171.8)], "wlf": [(-13.3, -176.2)],
}
# Rough share of each country's emissions that comes from its Pacific side (from where its population lives);
# 1 for the countries whose only coast is the Pacific or its marginal seas
PACIFIC_SHARE = {"rus": 0.06, "usa": 0.16, "can": 0.14, "mex": 0.3, "gtm": 0.5, "hnd": 0.1, "nic": 0.7, "cri": 0.5,
                 "pan": 0.7, "col": 0.1, "ecu": 0.9, "mys": 0.5, "idn": 0.6, "aus": 0.5, "tha": 0.8}

if __name__ == "__main__":
    oscar = np.load(OSCAR)
    lat, lon = oscar["lat"], oscar["lon"]  # 0.25°, lon 0-359.75
    ocean = oscar["n"] > 0
    u, v = np.nan_to_num(oscar["u"]), np.nan_to_num(oscar["v"])
    dlat, dlon = lat[1] - lat[0], lon[1] - lon[0]

    def sample(field, p):
        """Bilinear interpolation of a (lat, lon) field at positions p = (lat, lon 0-360), periodic in longitude."""
        rows = (p[:, 0] - lat[0]) / dlat
        cols = (p[:, 1] - lon[0]) / dlon
        return ndimage.map_coordinates(field, [rows, cols], order=1, mode="grid-wrap")

    def snap_to_ocean(point):
        """Nearest ocean grid cell of a release point (lat, lon -180..180)."""
        y, x = point[0], point[1] % 360
        distance = (lat[:, None] - y) ** 2 + ((lon[None, :] - x + 180) % 360 - 180) ** 2 * np.cos(np.radians(y)) ** 2
        i, j = np.unravel_index(np.where(ocean, distance, np.inf).argmin(), distance.shape)
        return lat[i], lon[j]

    points = [(country, *snap_to_ocean(p)) for country, ps in RELEASE_POINTS.items() for p in ps]
    print(f"{len(points)} release points")

    # every particle: release time, country and position
    months = pd.date_range(f"{FIRST_YEAR}-01-01", f"{LAST_YEAR}-12-01", freq="MS")
    release_time = np.repeat((months.year + (months.month - 1) / 12).values,
                             len(points) * PARTICLES_PER_POINT_PER_MONTH)
    country = np.tile(np.repeat([c for c, _, _ in points], PARTICLES_PER_POINT_PER_MONTH), len(months))
    position = np.tile(np.repeat([(y, x) for _, y, x in points], PARTICLES_PER_POINT_PER_MONTH, axis=0),
                       (len(months), 1)).astype(float)

    # weights: the emissions of the country in the release year, shared out over its particles of that year
    emissions = pd.read_csv(Path(__file__).parent / "data" / "emissions" / "pacific_emissions.csv")
    per_year = emissions.pivot_table(index=["species", "country"], columns="year", values="kt")
    particles_per_year = {c: 12 * PARTICLES_PER_POINT_PER_MONTH * len(ps) for c, ps in RELEASE_POINTS.items()}
    year = release_time.astype(int)
    weights = {s: np.array([per_year.loc[(s, c), y] * PACIFIC_SHARE.get(c, 1) / particles_per_year[c]
                            for c, y in zip(country, year)]) for s in SPECIES}

    rng = np.random.default_rng(1)
    step = DT_DAYS * 86400
    sigma = np.degrees(np.sqrt(2 * DIFFUSIVITY * step) / EARTH_RADIUS)  # random-walk step, degrees of latitude
    afloat = np.zeros(len(position), bool)
    released = np.zeros(len(position), bool)
    snapshot_times = np.arange(FIRST_YEAR + 0.25, LAST_YEAR + 1.001, 0.25)
    density = {s: [] for s in SPECIES}
    t, next_snapshot = float(FIRST_YEAR), 0
    while next_snapshot < len(snapshot_times):
        new = ~released & (release_time <= t)
        released |= new
        afloat |= new
        p = position[afloat]
        to_degrees = np.column_stack([np.ones(len(p)), 1 / np.cos(np.radians(p[:, 0]))]) * np.degrees(1 / EARTH_RADIUS)
        k1 = np.column_stack([sample(v, p), sample(u, p)]) * to_degrees * step
        mid = p + k1 / 2
        k2 = np.column_stack([sample(v, mid), sample(u, mid)]) * to_degrees * step
        p = p + k2 + rng.normal(0, sigma, p.shape) * np.column_stack([np.ones(len(p)), 1 / np.cos(np.radians(p[:, 0]))])
        p[:, 1] %= 360
        p[:, 0] = np.clip(p[:, 0], -89, 89)
        position[afloat] = p
        beached = sample(ocean.astype(float), p) < 0.5
        afloat[np.flatnonzero(afloat)[beached]] = False
        t += DT_DAYS / 365.25
        if t >= snapshot_times[next_snapshot]:
            for s in SPECIES:
                density[s].append(np.histogram2d(position[afloat, 0], position[afloat, 1], [GRID_LAT, GRID_LON],
                                                 weights=weights[s][afloat])[0].astype(np.float32))
            print(f"{snapshot_times[next_snapshot]:.2f}: {afloat.sum()} afloat of {released.sum()} released",
                  flush=True)
            next_snapshot += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT, times=snapshot_times, lat_edges=GRID_LAT, lon_edges=GRID_LON,
                        release_points=np.array([(y, x) for _, y, x in points]),
                        release_countries=np.array([c for c, _, _ in points]),
                        **{f"density_{s}": np.array(density[s]) for s in SPECIES})
    print(OUT)
