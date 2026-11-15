from __future__ import annotations

from collections.abc import Callable, Sequence
import numpy as np
import pandas as pd
import xarray as xr


class NetCDFNormalizer:
    """Приводит разнородные сеточные NetCDF-гранулы (L3/L4) к единому каноническому виду:
    - измерения: (time, lat, lon)
    - lat: float64, строго по возрастанию
    - lon: float64, в диапазоне [-180, 180], строго по возрастанию
    - time: timezone-naive datetime64[ns], без дубликатов, отсортировано
    """

    LAT_ALIASES = ("latitude", "Latitude", "LAT", "y")
    LON_ALIASES = ("longitude", "Longitude", "LON", "x")
    TIME_ATTR_ALIASES = (
        "time_coverage_start",
        "Start_Time",
        "rangebeginningdate",
        "start_time",
    )

    def __init__(self, coord_precision: int = 5):
        self.coord_precision = coord_precision

    def normalize_file(
        self,
        file_path: str,
        vars_list: Sequence[str],
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
    ) -> xr.Dataset | None:
        """Открывает один NetCDF-файл, нормализует его и вырезает целевой регион."""
        with xr.open_dataset(file_path, engine="netcdf4") as raw_ds:
            return self.normalize_dataset(
                raw_ds,
                vars_list=vars_list,
                lat_bounds=lat_bounds,
                lon_bounds=lon_bounds,
            )

    def normalize_dataset(
        self,
        ds: xr.Dataset,
        vars_list: Sequence[str],
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
    ) -> xr.Dataset | None:
        """Нормализует xarray.Dataset и возвращает обрезанный фрагмент, загруженный в память."""
        available_vars = [v for v in vars_list if v in ds.data_vars]
        if not available_vars:
            return None

        ds = ds[available_vars]
        ds = self._standardize_spatial_coords(ds)
        ds = self._crop_spatial(ds, lat_bounds, lon_bounds)

        if ds.sizes.get("lat", 0) == 0 or ds.sizes.get("lon", 0) == 0:
            return None

        ds = self._ensure_time_dim(ds)
        return ds.load()

    def merge_files(
        self,
        file_paths: Sequence[str],
        vars_list: Sequence[str],
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
        start_date: str | None = None,
        end_date: str | None = None,
        convert_fn: Callable[[xr.Dataset], xr.Dataset] | None = None,
        resample_freq: str | None = None,
        units: dict[str, str] | None = None,
        attrs: dict[str, str] | None = None,
    ) -> xr.Dataset:
        """Нормализует список файлов по одному и склеивает их в единый временной ряд."""
        slices: list[xr.Dataset] = []
        for fpath in sorted(file_paths):
            normalized = self.normalize_file(
                fpath,
                vars_list=vars_list,
                lat_bounds=lat_bounds,
                lon_bounds=lon_bounds,
            )
            if normalized is not None:
                slices.append(normalized)

        if not slices:
            raise RuntimeError("No valid data left after normalizing and cropping files.")

        ds = xr.concat(
            slices,
            dim="time",
            coords="minimal",
            compat="override",
            join="outer",
        )
        ds = self._finalize_time(ds, start_date=start_date, end_date=end_date)

        if convert_fn is not None:
            ds = convert_fn(ds)

        if resample_freq and "time" in ds.dims:
            ds = ds.resample(time=resample_freq).mean()

        if units:
            for var_name, unit in units.items():
                if var_name in ds:
                    ds[var_name].attrs["units"] = unit

        if attrs:
            ds.attrs.update(attrs)

        return ds

    def _standardize_spatial_coords(self, ds: xr.Dataset) -> xr.Dataset:
        rename_map = {}
        for cand in self.LAT_ALIASES:
            if cand in ds.coords or cand in ds.dims:
                rename_map[cand] = "lat"
                break
        for cand in self.LON_ALIASES:
            if cand in ds.coords or cand in ds.dims:
                rename_map[cand] = "lon"
                break
        if rename_map:
            ds = ds.rename(rename_map)

        if "lat" not in ds.dims or "lon" not in ds.dims:
            raise ValueError(f"Dataset lacks 1D lat/lon dimensions: {list(ds.dims)}")

        if "lat" not in ds.indexes:
            ds = ds.set_index(lat="lat")
        if "lon" not in ds.indexes:
            ds = ds.set_index(lon="lon")

        # Перевод долготы из [0, 360] в [-180, 180]
        if float(ds["lon"].max()) > 180.0:
            ds = ds.assign_coords(lon=(((ds["lon"] + 180.0) % 360.0) - 180.0))

        # Округление в float64 убирает артефакты точности float32 (напр. 25.000002 -> 25.0)
        ds = ds.assign_coords(
            lat=np.round(ds["lat"].values.astype("float64"), self.coord_precision),
            lon=np.round(ds["lon"].values.astype("float64"), self.coord_precision),
        )

        # Строго возрастающий порядок по обеим осям
        ds = ds.sortby("lat").sortby("lon")
        return ds

    @staticmethod
    def _crop_spatial(
        ds: xr.Dataset,
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
    ) -> xr.Dataset:
        lat_min, lat_max = min(lat_bounds), max(lat_bounds)
        lon_min, lon_max = min(lon_bounds), max(lon_bounds)
        return ds.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

    def _ensure_time_dim(self, ds: xr.Dataset) -> xr.Dataset:
        if "time" in ds.dims:
            t_vals = pd.to_datetime(ds["time"].values).tz_localize(None)
            return ds.assign_coords(time=t_vals)

        if "time" in ds.coords:
            t_val = pd.to_datetime(ds["time"].values).tz_localize(None)
            return ds.drop_vars("time").expand_dims(time=[t_val])

        for attr_name in self.TIME_ATTR_ALIASES:
            if attr_name in ds.attrs:
                t_val = self._parse_timestamp(ds.attrs[attr_name])
                return ds.expand_dims(time=[t_val])

        raise ValueError("Cannot determine timestamp: no 'time' dim/coord or known time attributes.")

    @staticmethod
    def _finalize_time(
        ds: xr.Dataset,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> xr.Dataset:
        ds = ds.sortby("time")
        _, unique_idx = np.unique(ds["time"].values, return_index=True)
        ds = ds.isel(time=np.sort(unique_idx))

        if start_date is not None or end_date is not None:
            ds = ds.sel(time=slice(start_date, end_date))
        return ds

    @staticmethod
    def _parse_timestamp(raw_time: str) -> pd.Timestamp:
        clean_str = str(raw_time).strip().rstrip("Z")
        try:
            return pd.to_datetime(clean_str).tz_localize(None)
        except ValueError:
            return pd.to_datetime(clean_str, format="%Y-%jT%H:%M:%S.%f").tz_localize(None)