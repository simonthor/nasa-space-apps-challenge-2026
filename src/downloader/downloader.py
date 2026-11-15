import os
import shutil
import time
import earthaccess
import xarray as xr

from downloader.normalize import NetCDFNormalizer
from downloader.registry import DATASET_REGISTRY


class NasaDataDownloader:
    def __init__(
        self,
        cache_dir: str = "../data/.cache_nasa",
        keep_cache: bool = True,
        normalizer: NetCDFNormalizer | None = None,
    ):
        self.cache_dir = cache_dir
        self.keep_cache = keep_cache
        self.normalizer = normalizer or NetCDFNormalizer()

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

        # 1. Search
        t0 = time.perf_counter()
        search_kwargs = self._build_search_kwargs(cfg, start_date, end_date, lat_bounds, lon_bounds)
        results = earthaccess.search_data(**search_kwargs)
        if not results:
            raise RuntimeError(f"Files for '{param_key}' for {start_date}..{end_date} not found.")
        if stride > 1:
            results = results[::stride]
            print(f"Applied step stride={stride} for downloading")
        print(f"[1/3] Found ({param_key}): {len(results)} took {time.perf_counter() - t0:.2f} s.")

        # 2. Download
        t0 = time.perf_counter()
        param_cache = os.path.join(self.cache_dir, param_key)
        os.makedirs(param_cache, exist_ok=True)
        local_files = earthaccess.download(results, local_path=param_cache, show_progress=True)
        print(f"[2/3] File download in cache took {time.perf_counter() - t0:.2f} s.")

        # 3. Normalize, crop & merge
        t0 = time.perf_counter()
        ds = self.normalizer.merge_files(
            file_paths=local_files,
            vars_list=cfg["vars"],
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            start_date=start_date,
            end_date=end_date,
            convert_fn=cfg.get("convert"),
            resample_freq=resample_freq,
            units=cfg.get("units"),
            attrs={"parameter": param_key, "source_dataset": cfg["short_name"]},
        )

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        ds.to_netcdf(output_path)
        print(f"[3/3] Region cut and saved {output_path} took {time.perf_counter() - t0:.2f} s.")

        if not self.keep_cache:
            shutil.rmtree(param_cache, ignore_errors=True)

        print(f"=== [{param_key}] Done took {time.perf_counter() - t_start:.2f} s. ===\n")
        return ds

    @staticmethod
    def _build_search_kwargs(
        cfg: dict,
        start_date: str,
        end_date: str,
        lat_bounds: tuple[float, float],
        lon_bounds: tuple[float, float],
    ) -> dict:
        kwargs = {
            "short_name": cfg["short_name"],
            "temporal": (start_date, end_date),
        }
        if not cfg.get("global_granules", False):
            kwargs["bounding_box"] = (
                min(lon_bounds),
                min(lat_bounds),
                max(lon_bounds),
                max(lat_bounds),
            )
        if "version" in cfg:
            kwargs["version"] = cfg["version"]
        if "granule_name" in cfg:
            kwargs["granule_name"] = cfg["granule_name"]
        return kwargs