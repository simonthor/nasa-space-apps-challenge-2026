import os
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import xarray as xr


def plot_netcdf_timeseries(
    nc_path: str,
    output_dir: str,
    var_name: str | None = None,
    rolling_window: int | None = None,
    save_spatial: bool = True,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(nc_path))[0]

    with xr.open_dataset(nc_path) as ds:
        if var_name is None:
            var_name = list(ds.data_vars)[0]
        if var_name not in ds.data_vars:
            raise ValueError(
                f"Переменная '{var_name}' не найдена в {nc_path}. "
                f"Доступные: {list(ds.data_vars)}"
            )

        da = ds[var_name]
        lat_name = "lat" if "lat" in da.coords else "latitude"
        lon_name = "lon" if "lon" in da.coords else "longitude"

        weights = np.cos(np.deg2rad(da[lat_name]))
        regional_mean = da.weighted(weights).mean(dim=[lat_name, lon_name], skipna=True)

        regional_mean = regional_mean.compute()
        spatial_mean = da.mean(dim="time", skipna=True).compute() if save_spatial else None

        units = da.attrs.get("units", "")
        long_name = da.attrs.get("long_name") or da.attrs.get("standard_name") or var_name
        param_label = ds.attrs.get("parameter", var_name)

    csv_path = os.path.join(output_dir, f"{base_name}_{var_name}.csv")
    regional_mean.to_dataframe(name=var_name)[[var_name]].to_csv(csv_path)

    n_steps = regional_mean.sizes.get("time", 0)
    span_days = 0
    if n_steps > 1:
        t_min = np.datetime64(regional_mean.time.min().values, "D")
        t_max = np.datetime64(regional_mean.time.max().values, "D")
        span_days = int((t_max - t_min) / np.timedelta64(1, "D"))

    if rolling_window is None:
        if span_days > 365 * 5:
            rolling_window = 12
        elif span_days > 400:
            rolling_window = 6
        else:
            rolling_window = 3

    is_long_series = n_steps > 36
    fig_width = 14 if span_days > 365 * 5 else 10
    fig, ax = plt.subplots(figsize=(fig_width, 5))

    regional_mean.plot(
        ax=ax,
        marker=None if is_long_series else "o",
        markersize=4,
        alpha=0.65 if is_long_series else 0.9,
        label="Values",
        color="steelblue",
        linewidth=1.0 if is_long_series else 1.5,
    )

    if n_steps >= rolling_window:
        min_p = max(1, rolling_window // 2)
        regional_mean.rolling(
            time=rolling_window, center=True, min_periods=min_p
        ).mean().plot(
            ax=ax,
            label=f"Moving Average ({rolling_window} steps)",
            color="darkorange",
            linewidth=2.0,
        )

    locator = mdates.AutoDateLocator(minticks=6, maxticks=14)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    val_range = float(regional_mean.max() - regional_mean.min())
    if 0 < val_range < 0.05:
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.4f"))

    ylabel = f"{var_name} ({units})" if units else var_name
    ax.set_title(f"{long_name} — Regional Mean ({param_label})")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Date")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    plt.tight_layout()
    ts_png_path = os.path.join(output_dir, f"{base_name}_{var_name}_timeseries.png")
    plt.savefig(ts_png_path, dpi=300)
    plt.close(fig)

    if save_spatial and spatial_mean is not None:
        fig, ax = plt.subplots(figsize=(7, 6))
        spatial_mean.plot(
            ax=ax,
            cmap="viridis",
            cbar_kwargs={"label": ylabel},
        )
        ax.set_title(f"{long_name} — Spatial Mean")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        plt.tight_layout()
        map_png_path = os.path.join(output_dir, f"{base_name}_{var_name}_spatial.png")
        plt.savefig(map_png_path, dpi=300)
        plt.close(fig)

    print(f"[Plot] Saved outputs for '{var_name}' in: {output_dir}")