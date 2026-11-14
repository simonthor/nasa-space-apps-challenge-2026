from import_files.earth_access_data import NasaDataDownloader
from import_files.import_nc import inspect_nc

from plot_data.plot_data import plot_netcdf_timeseries

def test_name():
    import earthaccess
    earthaccess.login()

    for kw in ["MODISA_L3m_CHL", "MODISA_L3m_SST", "MODISA_L3m_RRS"]:
        datasets = earthaccess.search_datasets(keyword=kw)
        for d in datasets:
            print(d["umm"]["ShortName"], "-> version:", d["umm"]["Version"])

    granules = earthaccess.search_data(
        short_name="MODISA_L3m_CHL",
        temporal=("2023-01-01", "2023-03-01"),
        granule_name="*.MO.*4km*"
    )
    print("Found:", len(granules))
    if granules:
        print(granules[0]["umm"]["GranuleUR"])


if __name__ == "__main__":
    # test_name()
    # downloader = NasaDataDownloader(cache_dir="../data/.cache_nasa", keep_cache=True)
    #
    # lat_region = (25.0, 35.0)
    # lon_region = (-145.0, -135.0)
    #
    # out_file = "../data/reflectance_monthly2023.nc"
    #
    # ds_salinity = downloader.fetch(
    #     param_key="reflectance_monthly",
    #     start_date="2001-01-01",
    #     end_date="2024-12-31",
    #     lat_bounds=lat_region,
    #     lon_bounds=lon_region,
    #     output_path=out_file,
    # )
    #
    # inspect_nc(out_file)
    # plot_reflectance("../data/reflectance_monthly2023.nc")

    plot_netcdf_timeseries(
        nc_path="../data/chlorophyll_data2023.nc",
        output_dir="../output/chlorophyll",
    )