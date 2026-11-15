from downloader.downloader import NasaDataDownloader, NetCDFNormalizer
from downloader.registry import DATASET_REGISTRY
from import_files.import_nc import inspect_nc
from glob import glob
from plot_data.plot_data import plot_netcdf_timeseries

def download(lat_region, lon_region, name:str):
    downloader = NasaDataDownloader(cache_dir="../data/.cache_nasa", keep_cache=True)

    out_file = f"../data/{name}01-25.nc"

    ds_sst = downloader.fetch(
        param_key=name,
        start_date="2001-01-01",
        end_date="2025-12-31",
        lat_bounds=lat_region,
        lon_bounds=lon_region,
        output_path=out_file,
    )

    inspect_nc(out_file)
    return out_file

def use_existing(lat_region, lon_region, name:str):
    normalizer = NetCDFNormalizer()
    cfg = DATASET_REGISTRY[name]

    cached_files = glob(f"../data/.cache_nasa/{name}/*.nc")
    out_file = f"../data/{name}01-25.nc"

    ds = normalizer.merge_files(
        file_paths=cached_files,
        vars_list=cfg["vars"],
        lat_bounds=lat_region,
        lon_bounds=lon_region,
        start_date="2001-01-01",
        end_date="2025-12-31",
        convert_fn=cfg.get("convert"),
        units=cfg.get("units"),
        attrs={"parameter": name, "source_dataset": cfg["short_name"]},
    )

    ds.to_netcdf(out_file)
    inspect_nc(out_file)
    return out_file

if __name__ == "__main__":
    lat_region = (25.0, 35.0)
    lon_region = (-145.0, -135.0)
    name = "microplastic_daily"

    nc = download(lat_region, lon_region, name)

    # plot_netcdf_timeseries(
    #     # nc_path=f"../data/{name}01-25.nc",
    #     nc_path="../data/regions/north_atlantic_north/salinity_monthly.nc",
    #     output_dir=f"../output/salinity_monthly",
    # )