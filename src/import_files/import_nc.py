import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

def test_plot():
    temp_c = xr.open_dataarray("../data/processed/gldas_temp_2001_2025_c.nc")

    # Temperature for regioin
    weights = np.cos(np.deg2rad(temp_c.lat))
    regional_mean = temp_c.weighted(weights).mean(dim=["lat", "lon"])

    regional_mean.to_dataframe(name="temp_c").to_csv("regional_temp.csv")

    fig, ax = plt.subplots(figsize=(12, 5))

    regional_mean.plot(ax=ax, label="Monthly values", alpha=0.5, color="steelblue")
    regional_mean.rolling(time=12, center=True).mean().plot(
        ax=ax, label="Moving Average (12 m.)", color="darkred", linewidth=2
    )

    ax.set_title("Average surface temperature in the region (2001–2025)")
    ax.set_ylabel("Temperature, °C")
    ax.set_xlabel("Year")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend()

    plt.tight_layout()
    plt.savefig("regional_temp_plot.png", dpi=300)
    plt.close()

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