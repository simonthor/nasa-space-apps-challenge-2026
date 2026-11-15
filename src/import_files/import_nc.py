import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

def inspect_nc(file_path):
    """
    Outputs the structure, coordinates, variables, attributes,
    and brief statistics on the contents of a NetCDF (.nc) file to the console.
    """

    with xr.open_dataset(file_path) as ds:
        print(f"Structure of files: {file_path}")
        print(ds)

        print("\n Summary of Data Variables ")
        for var_name, da in ds.data_vars.items():
            units = da.attrs.get("units", "not specified")
            long_name = da.attrs.get("long_name", "no description")
            min_val = float(da.min().values)
            max_val = float(da.max().values)
            mean_val = float(da.mean().values)

            print(f"\nVariable: {var_name}")
            print(f"  Description:  {long_name}")
            print(f"  Units:   {units}")
            print(f"  Size:   {da.dims} -> {da.shape}")
            print(
                f"  Values:  min = {min_val:.2f}, max = {max_val:.2f}, mean ="
                f" {mean_val:.2f}"
            )

        print("\n=== Data example (first 5 time step) ===")
        if "time" in ds.dims:
            print(ds.isel(time=slice(0, 5)))