from __future__ import annotations

import numpy as np
import gc
from glob import glob
from pathlib import Path
import xarray as xr

from downloader.registry import DATASET_REGISTRY


def build_preview_streaming(
    cache_root: str = "../data/.cache_nasa",
    output_dir: str = "../data/preview",
    params: list[str] | None = None,
    coarsen_factor: int = 6,
) -> None:
    """
    Читает файлы из кэша строго ПО ОДНОМУ, сразу сжимает сетку
    и собирает легкий preview без загрузки 15 ГБ в RAM.
    """
    target_params = params or list(DATASET_REGISTRY.keys())
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    for param_key in target_params:
        cfg = DATASET_REGISTRY[param_key]
        cached_files = sorted(glob(f"{cache_root}/{param_key}/*.nc"))
        if not cached_files:
            print(f"[SKIP] No cached files for '{param_key}'")
            continue

        print(f"=== Streaming '{param_key}' ({len(cached_files)} files) ===")
        small_slices: list[xr.Dataset] = []
        convert_fn = cfg.get("convert")

        for i, fp in enumerate(cached_files, 1):
            with xr.open_dataset(fp) as ds:
                # 1. Берем только нужные переменные
                vars_present = [v for v in cfg["vars"] if v in ds.data_vars]
                if not vars_present:
                    continue
                ds_sub = ds[vars_present]

                # 2. СРАЗУ сжимаем сетку (уменьшаем объем данных в factor^2 раз)
                coarsen_dims = {}
                for lat_name in ("lat", "latitude", "y"):
                    if lat_name in ds_sub.dims:
                        coarsen_dims[lat_name] = coarsen_factor
                for lon_name in ("lon", "longitude", "x"):
                    if lon_name in ds_sub.dims:
                        coarsen_dims[lon_name] = coarsen_factor

                if coarsen_dims:
                    ds_sub = ds_sub.coarsen(coarsen_dims, boundary="trim").mean()

                # 3. Применяем конвертацию единиц и переводим в float32
                if convert_fn:
                    ds_sub = convert_fn(ds_sub)

                for v in ds_sub.data_vars:
                    ds_sub[v] = ds_sub[v].astype("float32")

                # Загружаем в память ТОЛЬКО маленький сжатый срез (~100 КБ)
                small_slices.append(ds_sub.load())

            if i % 500 == 0:
                gc.collect()
                print(f"  Processed {i}/{len(cached_files)} files...")

        if not small_slices:
            continue

        # Теперь в списке лежат сотни крошечных срезов (суммарно ~50-150 МБ вместо 40 ГБ)
        ds_final = xr.concat(small_slices, dim="time").sortby("time")

        out_path = out_root / f"{param_key}_preview.nc"
        encoding = {
            v: {"zlib": True, "complevel": 4, "dtype": "float32"}
            for v in ds_final.data_vars
        }
        ds_final.to_netcdf(out_path, encoding=encoding)

        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"  -> Saved {out_path} | shape={dict(ds_final.sizes)} | {size_mb:.1f} MB")

        ds_final.close()
        small_slices.clear()
        gc.collect()


# В конец prepare_preview.py (или отдельной функцией)
def build_microplastic_preview(
    cache_root: str = "../../data/.cache_nasa",
    output_dir: str = "../../data/preview",
    coarsen_factor: int = 1,
) -> None:
    param_key = "microplastic_daily"
    cfg = DATASET_REGISTRY[param_key]
    cached_files = sorted(glob(f"{cache_root}/{param_key}/*.nc"))
    if not cached_files:
        print(f"[SKIP] No cached files for '{param_key}'")
        return

    slices: list[xr.Dataset] = []
    for fp in cached_files:
        with xr.open_dataset(fp) as ds:
            ds_sub = ds[cfg["vars"]]

            # Сжимаем сетку (0.25° -> 0.5° при factor=2)
            coarsen_dims = {d: coarsen_factor for d in ("lat", "lon") if d in ds_sub.dims}
            if coarsen_dims and coarsen_factor > 1:
                ds_sub = ds_sub.coarsen(coarsen_dims, boundary="trim").mean()

            # Переводим долготу 0..360 -> -180..180 и сортируем
            if float(ds_sub["lon"].max()) > 180.0:
                ds_sub = ds_sub.assign_coords(lon=(((ds_sub["lon"] + 180.0) % 360.0) - 180.0)).sortby("lon")

            for v in ds_sub.data_vars:
                ds_sub[v] = ds_sub[v].astype("float32")

            slices.append(ds_sub.load())

    ds_final = xr.concat(slices, dim="time").sortby("time")
    # Убираем возможные дубликаты дат на стыках месячных файлов
    _, idx = np.unique(ds_final["time"].values, return_index=True)
    ds_final = ds_final.isel(time=np.sort(idx))

    # Опционально: сжать ежедневные шаги в среднемесячные, чтобы слайдер листал месяцы как в остальных слоях
    ds_final = ds_final.resample(time="MS").mean()

    out_path = Path(output_dir) / f"{param_key}_preview.nc"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds_final.to_netcdf(out_path, encoding={"MP_concentration": {"zlib": True, "complevel": 4, "dtype": "float32"}})
    print(f"Saved {out_path} | shape={dict(ds_final.sizes)}")


if __name__ == "__main__":
    # build_microplastic_preview()
    build_preview_streaming(
        cache_root="../../data/.cache_nasa",
        output_dir="../../data/preview",
        params=["kd490_monthly"],
        coarsen_factor=8,
    )