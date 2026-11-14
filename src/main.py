from import_files.import_nc import inspect_nc

if __name__ == "__main__":
    # temp_c = combine_data(
    #     path="../data/skin_temp",
    #     output_path="../processed/gldas_temp_2001_2025_c.nc"
    # )

    # download_nc("../data/prov.postprocess+sMpAn+dGLDAS_NOAH025_M_2_1_AvgSurfT_inst+zNA+t20010101000000_20251231235959+b66.0000W13.5000S60.0000W8.0000S.txt", "../data/skin_temp")

    inspect_nc("../data/processed/gldas_temp_2001_2025_c.nc")