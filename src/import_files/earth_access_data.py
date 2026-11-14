import os
import shutil
import time
import earthaccess
import pandas as pd
import xarray as xr

DATASET_REGISTRY = {
    "chlorophyll_monthly": {
        "short_name": "MODISA_L3m_CHL",
        "version": "2022.0",
        "granule_name": "*.MO.CHL.chlor_a.4km.nc",
        "vars": ["chlor_a"],
        "units": {"chlor_a": "mg/m^3"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },
    "sst_monthly": {
        "short_name": "MODISA_L3m_SST",
        "version": "R2019.0",
        "granule_name": "*.MO.SST.sst.4km.nc",
        "vars": ["sst"],
        "units": {"sst": "degC"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },
    "reflectance_monthly": {
        "short_name": "MODISA_L3m_RRS",
        "version": "2022.0",
        "granule_name": "*.MO.RRS.Rrs_531.4km.nc",
        "vars": ["Rrs_531"],
        "units": {"Rrs_531": "sr^-1"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },
    "salinity_monthly": {
        "short_name": "SMAP_JPL_L3_SSS_CAP_MONTHLY_V5",
        "vars": ["smap_sss"],
        "units": {"smap_sss": "PSU"},
        "convert": lambda ds: ds,
    },

    "currents_daily": {
        "short_name": "OSCAR_L4_OC_FINAL_V2.0",
        "vars": ["u", "v"],
        "units": {"u": "m/s", "v": "m/s"},
        "convert": lambda ds: ds,
    },
    "wind_daily": {
        "short_name": "CCMP_WINDS_10M6HR_L4_V3.1",
        "vars": ["uwnd", "vwnd"],
        "units": {"uwnd": "m/s", "vwnd": "m/s"},
        "convert": lambda ds: ds,
    },
    "sst_daily_1km": {
        "short_name": "MUR-JPL-L4-GLOB-v4.1",
        "vars": ["analysed_sst"],
        "units": {"analysed_sst": "degC"},
        "convert": lambda ds: ds - 273.15,
    },
}


class NasaDataDownloader:

    def __init__(self, cache_dir: str = "../data/.cache_nasa", keep_cache: bool = True):
        self.cache_dir = cache_dir
        self.keep_cache = keep_cache
        t0 = time.perf_counter()
        earthaccess.login()
        print(f"[Auth] Success, took {time.perf_counter() - t0:.2f} s.")

    def fetch(
        self,
        param_key: str,
        start_date: str,
        end_date: str,
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
        output_path: str,
        stride: int = 1,
        resample_freq: str | None = None,
    ) -> xr.Dataset:
        t_start = time.perf_counter()

        if param_key not in DATASET_REGISTRY:
            raise ValueError(f"Unknown param '{param_key}'")
        cfg = DATASET_REGISTRY[param_key]
        search_kwargs = {
            "short_name": cfg["short_name"],
            "temporal": (start_date, end_date),
        }
        if not cfg.get("global_granules", False):
            search_kwargs["bounding_box"] = (
                min(lon_bounds),
                min(lat_bounds),
                max(lon_bounds),
                max(lat_bounds),
            )
        if "version" in cfg:
            search_kwargs["version"] = cfg["version"]
        if "granule_name" in cfg:
            search_kwargs["granule_name"] = cfg["granule_name"]

        # 1. Searching in catalog
        t0 = time.perf_counter()
        results = earthaccess.search_data(**search_kwargs)
        if not results:
            raise RuntimeError(
                f"Files for '{param_key}' for {start_date}..{end_date} not found."
            )
        if stride > 1:
            results = results[::stride]
            print(f"Applied step stride={stride}: for downloading")
        print(
            f"[1/3] Found ({param_key}): {len(results)} took"
            f" {time.perf_counter() - t0:.2f} s."
        )

        # 2. Multithread download
        t0 = time.perf_counter()
        param_cache = os.path.join(self.cache_dir, param_key)
        os.makedirs(param_cache, exist_ok=True)
        local_files = earthaccess.download(results, local_path=param_cache)
        print(
            "[2/3] File download in cache took"
            f" {time.perf_counter() - t0:.2f} s."
        )

        # 3. Local reading, cutting region
        t0 = time.perf_counter()
        # ds = xr.open_mfdataset(
        #     local_files,
        #     engine="netcdf4",
        #     combine="nested",
        #     concat_dim="time",
        #     preprocess=lambda d: self._crop_dataset(
        #         d, cfg["vars"], lat_bounds, lon_bounds
        #     ),
        # )
        ds = xr.open_mfdataset(
            local_files,
            engine="netcdf4",
            combine="by_coords",
            preprocess=lambda d: self._crop_dataset(
                d, cfg["vars"], lat_bounds, lon_bounds
            ),
        )

        if "time" in ds.coords:
            ds = ds.sortby("time")
            ds = ds.sel(time=slice(start_date, end_date))

        ds = cfg["convert"](ds).compute()
        if resample_freq and "time" in ds.dims:
            ds = ds.resample(time=resample_freq).mean()
        for var_name, unit in cfg.get("units", {}).items():
            if var_name in ds:
                ds[var_name].attrs["units"] = unit

        ds.attrs["parameter"] = param_key
        ds.attrs["source_dataset"] = cfg["short_name"]

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        ds.to_netcdf(output_path)
        ds.close()
        print(
            "[3/3] Region cut and saved"
            f" {output_path} took {time.perf_counter() - t0:.2f} s."
        )

        if not self.keep_cache:
            shutil.rmtree(param_cache, ignore_errors=True)

        print(
            f"=== [{param_key}] Done took {time.perf_counter() - t_start:.2f}"
            " s. ===\n"
        )
        return ds

    @staticmethod
    def _parse_nasa_time(time_str: str) -> pd.Timestamp:
        clean_str = time_str.strip().rstrip("Z")
        try:
            return pd.to_datetime(clean_str)
        except ValueError:
            return pd.to_datetime(clean_str, format="%Y-%jT%H:%M:%S.%f")

    @classmethod
    def _crop_dataset(
        cls,
        ds: xr.Dataset,
        vars_list: list[str],
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
    ) -> xr.Dataset:
        lat_name = "lat" if "lat" in ds.coords else "latitude"
        lon_name = "lon" if "lon" in ds.coords else "longitude"

        lat_desc = bool(ds[lat_name][0] > ds[lat_name][-1])
        lat_slice = (
            slice(max(lat_bounds), min(lat_bounds))
            if lat_desc
            else slice(min(lat_bounds), max(lat_bounds))
        )

        lon_min, lon_max = min(lon_bounds), max(lon_bounds)
        if float(ds[lon_name].min()) >= 0.0 and float(ds[lon_name].max()) > 180.0:
            lon_min = lon_min % 360.0
            lon_max = lon_max % 360.0

        available_vars = [v for v in vars_list if v in ds.data_vars]
        cropped = ds[available_vars].sel(
            {lat_name: lat_slice, lon_name: slice(lon_min, lon_max)}
        )

        if "time" not in cropped.dims:
            time_str = ds.attrs.get("time_coverage_start") or ds.attrs.get("Start_Time")
            if time_str:
                t_val = cls._parse_nasa_time(time_str).tz_localize(None)
                cropped = cropped.expand_dims(time=[t_val])

        return cropped