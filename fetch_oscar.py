"""Mean ocean surface current 2004-2023 from OSCAR (Ocean Surface Current Analyses Real-time, final, 0.25°, PO.DAAC
OSCAR_L4_OC_FINAL_V2.0): geostrophic + Ekman current of the top 15 m (Dohan 2017, Earth Space Sci. 4, 302).

The daily maps of the 15th of January, April, July and October of each year are averaged; the 32 MB daily files are
not kept, only the mean, in data/oscar/oscar_mean_2004_2023.npz (lat, lon, u, v in m/s, n = valid samples).
Downloads go through the open playwright-cli browser, which must be logged in to Earthdata (see giovanni_fetch.sh).
"""
import base64
import json
import subprocess
from pathlib import Path

import netCDF4
import numpy as np

OUT = Path(__file__).parent / "data" / "oscar" / "oscar_mean_2004_2023.npz"
URL = "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/OSCAR_L4_OC_FINAL_V2.0/" \
      "oscar_currents_final_{}.nc"
# the first request of a session goes through the Earthdata Login page, which redirects with JavaScript only
DOWNLOAD = """async page => {
  const request = page.context().request;
  let r = await request.get('%s');
  if (r.url().includes('urs.earthdata')) {
    const login = (await r.text()).match(/https:\\/\\/archive\\.podaac\\.earthdata\\.nasa\\.gov\\/login\\?code=[^"' >]+/)[0];
    r = await request.get(login.replace(/&amp;/g, '&'));
  }
  return (await r.body()).toString('base64') }"""

sums, n = None, None
for year in range(2004, 2024):
    for month in [1, 4, 7, 10]:
        date = f"{year}{month:02d}15"
        out = subprocess.run(["playwright-cli", "--raw", "run-code", DOWNLOAD % URL.format(date)], capture_output=True,
                             text=True, check=True).stdout
        data = base64.b64decode(json.loads(out))
        assert data[:4] == b"\x89HDF", f"{date}: not a NetCDF file"
        with netCDF4.Dataset("oscar.nc", memory=data) as nc:
            u, v = (nc[name][0].filled(np.nan).T for name in ["u", "v"])  # (lat, lon)
            if sums is None:
                lat, lon = nc["lat"][:].data, nc["lon"][:].data
                sums, n = [np.zeros_like(u), np.zeros_like(u)], np.zeros(u.shape, int)
        valid = np.isfinite(u) & np.isfinite(v)
        sums[0][valid] += u[valid]
        sums[1][valid] += v[valid]
        n += valid
        print(date, flush=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
with np.errstate(invalid="ignore"):
    np.savez_compressed(OUT, lat=lat, lon=lon, u=sums[0] / n, v=sums[1] / n, n=n)
print(OUT)
