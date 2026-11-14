import os
import xarray
import requests


def download_nc(path, download_path):
  os.makedirs(download_path, exist_ok=True)
  with open(path, "r") as f:
    urls = [line.strip() for line in f if line.strip()]

  session = requests.Session()

  for url in urls:
    filename = os.path.join(download_path, url.split("/")[-1])
    if not os.path.exists(filename):
      resp = session.get(url, allow_redirects=True)
      resp.raise_for_status()  # Will result in an error if the server returns a 401, 403, or 404 response

      if "text/html" in resp.headers.get("Content-Type", ""):
        raise PermissionError(
            f"Giovanni's session has expired, or the Earthdata information for {url}"
        )

      with open(filename, "wb") as out:
        out.write(resp.content)

  print(f"Downloaded: {len(urls)} urls")

  ds = xarray.open_mfdataset(f"{download_path}/*.nc", combine="by_coords")
  temp_c = ds["GLDAS_NOAH025_M_2_1_AvgSurfT_inst"] - 273.15
  print(temp_c)
  return temp_c

def combine_data(path, output_path):
  ds = xarray.open_mfdataset(os.path.join(path, "*.nc"), combine="by_coords")
  temp_c = ds["GLDAS_NOAH025_M_2_1_AvgSurfT_inst"] - 273.15
  temp_c.attrs = ds["GLDAS_NOAH025_M_2_1_AvgSurfT_inst"].attrs.copy()
  temp_c.attrs["units"] = "degC"

  out_dir = os.path.dirname(output_path)
  if out_dir:
    os.makedirs(out_dir, exist_ok=True)

  temp_c = temp_c.compute()
  temp_c.to_netcdf(output_path)

  ds.close()
  print(f"Successfully combined data output: {output_path}")
  return temp_c