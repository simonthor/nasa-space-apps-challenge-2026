from import_files.extract_regions_from_geojson import extract_regions_from_cache, extract_regions_from_cache_large


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
    # extract_regions_from_cache_large(
    #     geojson_path="../data/coordinates/ocean_means.geojson",
    #     cache_root="../data/.cache_nasa",
    #     output_root="../data/regions_2",
    #     start_date="2001-01-01",
    #     end_date="2025-12-31",
    # )
    extract_regions_from_cache(
        geojson_path="../data/coordinates/garbage_patches.geojson",
        cache_root="../data/.cache_nasa",
        output_root="../data/regions",
        params=["microplastic_daily"],
        start_date="2001-01-01",
        end_date="2025-12-31",
    )
