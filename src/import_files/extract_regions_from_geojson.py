from glob import glob
from pathlib import Path

from import_files.geojson_parser import load_geojson_regions
from downloader.normalize import NetCDFNormalizer
from downloader.registry import DATASET_REGISTRY


def extract_regions_from_cache(
    geojson_path: str,
    cache_root: str = "../data/.cache_nasa",
    output_root: str = "../data/regions",
    params: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> None:
    regions = load_geojson_regions(geojson_path)
    normalizer = NetCDFNormalizer()
    target_params = params or list(DATASET_REGISTRY.keys())

    for param_key in target_params:
        cfg = DATASET_REGISTRY[param_key]
        cached_files = sorted(glob(f"{cache_root}/{param_key}/*.nc"))
        if not cached_files:
            print(f"[SKIP] No cached files for '{param_key}'")
            continue

        print(f"=== Processing '{param_key}' ({len(cached_files)} files) ===")

        for region in regions:
            out_path = Path(output_root) / region.name / f"{param_key}.nc"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            netcdf_attrs = {
                "parameter": param_key,
                "source_dataset": cfg["short_name"],
                "region_name": region.name,
                **{f"region_{k}": str(v) for k, v in region.properties.items()},
            }

            ds = normalizer.merge_files(
                file_paths=cached_files,
                vars_list=cfg["vars"],
                lat_bounds=region.lat_bounds,
                lon_bounds=region.lon_bounds,
                start_date=start_date,
                end_date=end_date,
                convert_fn=cfg.get("convert"),
                units=cfg.get("units"),
                attrs=netcdf_attrs,
            )

            ds.to_netcdf(out_path)
            ds.close()
            print(f"  -> Saved {out_path} | shape={dict(ds.sizes)}")


import gc
from pathlib import Path
from glob import glob
import xarray as xr


def extract_regions_from_cache_large(
        geojson_path: str,
        cache_root: str = "../data/.cache_nasa",
        output_root: str = "../data/regions",
        params: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
) -> None:
    regions = load_geojson_regions(geojson_path)
    normalizer = NetCDFNormalizer()
    target_params = params or list(DATASET_REGISTRY.keys())

    start_year = int(start_date[:4]) if start_date else 2001
    end_year = int(end_date[:4]) if end_date else 2025

    for param_key in target_params:
        cfg = DATASET_REGISTRY[param_key]
        cached_files = sorted(glob(f"{cache_root}/{param_key}/*.nc"))
        if not cached_files:
            print(f"[SKIP] No cached files for '{param_key}'")
            continue

        print(f"=== Processing '{param_key}' ({len(cached_files)} files) ===")

        for region in regions:
            out_path = Path(output_root) / region.name / f"{param_key}.nc"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            temp_dir = out_path.parent / f"_tmp_{param_key}"
            temp_dir.mkdir(exist_ok=True)

            netcdf_attrs = {
                "parameter": param_key,
                "source_dataset": cfg["short_name"],
                "region_name": region.name,
                **{f"region_{k}": str(v) for k, v in region.properties.items()},
            }

            temp_files = []
            for year in range(start_year, end_year + 1):
                y_start = max(start_date, f"{year}-01-01") if start_date else f"{year}-01-01"
                y_end = min(end_date, f"{year}-12-31") if end_date else f"{year}-12-31"
                if y_start > y_end:
                    continue

                ds_year = normalizer.merge_files(
                    file_paths=cached_files,
                    vars_list=cfg["vars"],
                    lat_bounds=region.lat_bounds,
                    lon_bounds=region.lon_bounds,
                    start_date=y_start,
                    end_date=y_end,
                    convert_fn=cfg.get("convert"),
                    units=cfg.get("units"),
                    attrs=netcdf_attrs,
                )

                if any(size == 0 for size in ds_year.sizes.values()):
                    print(f"    [WARN] Empty slice for {region.name} in {year}: sizes={dict(ds_year.sizes)}")
                    ds_year.close()
                    del ds_year
                    gc.collect()
                    continue

                tmp_file = temp_dir / f"{year}.nc"
                ds_year.to_netcdf(tmp_file)
                ds_year.close()
                del ds_year
                gc.collect()
                temp_files.append(tmp_file)

            if not temp_files:
                print(f"  [SKIP] No non-empty data for {region.name} ({param_key})")
                temp_dir.rmdir()
                continue

            with xr.open_mfdataset(
                    temp_files,
                    combine="nested",
                    concat_dim="time",
                    chunks={"time": 365},
            ) as ds_full:
                ds_full.to_netcdf(out_path)
                print(f"  -> Saved {out_path} | shape={dict(ds_full.sizes)}")

            for f in temp_files:
                f.unlink()
            temp_dir.rmdir()
            gc.collect()