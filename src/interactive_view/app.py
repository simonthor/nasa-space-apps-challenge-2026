from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import xarray as xr

st.set_page_config(page_title="NASA Ocean Explorer", layout="wide")

PREVIEW_DIR = Path("../../data/preview")
GEOJSON_PATH = Path("../../data/coordinates/ocean_means.geojson")

COLORSCALES = {
    "chlorophyll_monthly": "Viridis",
    "sst_monthly": "Thermal",
    "reflectance_monthly": "Ice",
    "salinity_monthly": "Haline",
}


@st.cache_resource
def load_dataset(nc_path: Path) -> xr.Dataset:
    ds = xr.open_dataset(nc_path)
    rename_map = {}
    if "latitude" in ds.coords:
        rename_map["latitude"] = "lat"
    if "longitude" in ds.coords:
        rename_map["longitude"] = "lon"
    if rename_map:
        ds = ds.rename(rename_map)
    return ds


@st.cache_data
def load_geojson(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_slice_df(
    ds: xr.Dataset,
    var_name: str,
    time_idx: int,
    stride: int = 2,
    use_log: bool = False,
) -> pd.DataFrame:
    da = ds[var_name].isel(time=time_idx)

    if stride > 1 and da.sizes["lat"] > 200:
        da = da.isel(lat=slice(None, None, stride), lon=slice(None, None, stride))

    vals = da.values
    lats = da["lat"].values
    lons = da["lon"].values

    lon_grid, lat_grid = np.meshgrid(lons, lats)
    mask = np.isfinite(vals)

    z = vals[mask]
    if use_log:
        z = np.log10(np.clip(z, 1e-4, None))

    return pd.DataFrame(
        {
            "lat": lat_grid[mask],
            "lon": lon_grid[mask],
            "val": z,
            "raw": vals[mask],
        }
    )


def build_globe_figure(
    da: xr.DataArray,
    projection: str,
    colorscale: str,
    colorbar_title: str,
    geojson_data: dict | None = None,
    stride: int = 2,
    use_log: bool = False,
) -> go.Figure:
    if stride > 1 and da.sizes["lat"] > 180:
        da = da.isel(lat=slice(None, None, stride), lon=slice(None, None, stride))

    vals = da.values.astype("float32")
    if use_log:
        vals = np.where(np.isfinite(vals), np.log10(np.clip(vals, 1e-4, None)), np.nan)

    lats = da["lat"].values
    lons = da["lon"].values

    vmin = float(np.nanpercentile(vals, 2))
    vmax = float(np.nanpercentile(vals, 98))

    if projection == "equirectangular":
        fig = go.Figure(
            go.Heatmap(
                z=vals,
                x=lons,
                y=lats,
                colorscale=colorscale,
                colorbar=dict(title=colorbar_title, thickness=15, len=0.75),
                zmin=vmin,
                zmax=vmax,
                zsmooth="best",
            )
        )

        if geojson_data:
            for feat in geojson_data.get("features", []):
                coords = feat["geometry"]["coordinates"][0]
                r_lons = [c[0] for c in coords]
                r_lats = [c[1] for c in coords]
                fig.add_trace(
                    go.Scatter(
                        x=r_lons,
                        y=r_lats,
                        mode="lines",
                        line=dict(color="rgba(255, 255, 255, 0.8)", width=1.5),
                        name=feat.get("properties", {}).get("name", "region"),
                        showlegend=False,
                    )
                )

        fig.update_layout(
            xaxis=dict(title="Longitude", range=[-180, 180], showgrid=False),
            yaxis=dict(title="Latitude", range=[-90, 90], scaleanchor="x", showgrid=False),
            plot_bgcolor="rgb(28, 32, 40)",
        )
    else:
        lon_rad = np.deg2rad(lons)
        lat_rad = np.deg2rad(lats)
        lon_grid, lat_grid = np.meshgrid(lon_rad, lat_rad)

        x = np.cos(lat_grid) * np.cos(lon_grid)
        y = np.cos(lat_grid) * np.sin(lon_grid)
        z = np.sin(lat_grid)

        fig = go.Figure(
            go.Surface(
                x=x,
                y=y,
                z=z,
                surfacecolor=vals,
                colorscale=colorscale,
                colorbar=dict(title=colorbar_title, thickness=15, len=0.75),
                cmin=vmin,
                cmax=vmax,
                showscale=True,
                hoverinfo="skip",
            )
        )

        if geojson_data:
            r = 1.005
            for feat in geojson_data.get("features", []):
                coords = feat["geometry"]["coordinates"][0]
                r_lons = np.deg2rad([c[0] for c in coords])
                r_lats = np.deg2rad([c[1] for c in coords])
                fig.add_trace(
                    go.Scatter3d(
                        x=r * np.cos(r_lats) * np.cos(r_lons),
                        y=r * np.cos(r_lats) * np.sin(r_lons),
                        z=r * np.sin(r_lats),
                        mode="lines",
                        line=dict(color="white", width=3),
                        name=feat.get("properties", {}).get("name", "region"),
                        showlegend=False,
                    )
                )

        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                aspectmode="data",
                bgcolor="rgb(14, 17, 23)",
            )
        )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=680,
        paper_bgcolor="rgb(14, 17, 23)",
        font=dict(color="white"),
    )
    return fig


def main() -> None:
    st.title("🌍 NASA Earth Observation — Global Ocean Explorer")

    nc_files = sorted(PREVIEW_DIR.glob("*_preview.nc"))
    if not nc_files:
        st.error(f"Не найдены *_preview.nc файлы в {PREVIEW_DIR.resolve()}")
        return

    file_map = {f.stem.replace("_preview", ""): f for f in nc_files}

    with st.sidebar:
        st.header("Параметры отображения")
        dataset_key = st.selectbox("Датасет", list(file_map.keys()))
        ds = load_dataset(file_map[dataset_key])

        var_name = st.selectbox("Переменная", list(ds.data_vars))

        view_mode = st.radio(
            "Проекция",
            ["3D Глобус", "Плоская карта"],
            horizontal=True,
        )
        projection = "orthographic" if view_mode == "3D Глобус" else "equirectangular"

        default_log = "chlorophyll" in dataset_key or "reflectance" in dataset_key
        use_log = st.checkbox("Логарифмическая шкала (log10)", value=default_log)

        stride = st.slider(
            "Детализация сетки (меньше = четче)",
            min_value=1,
            max_value=4,
            value=2,
        )

        st.divider()
        st.subheader("Вращение камеры")
        center_lon = st.slider("Долгота центра", -180, 180, -140)
        center_lat = st.slider("Широта центра", -90, 90, 10)

    # --- Временная шкала ---
    times = pd.to_datetime(ds["time"].values)
    time_labels = [t.strftime("%Y-%m") for t in times]

    selected_label = st.select_slider(
        "Месяц наблюдения",
        options=time_labels,
        value=time_labels[-1],
    )
    time_idx = time_labels.index(selected_label)

    col_map, col_stats = st.columns([2.2, 1])

    geojson_data = load_geojson(GEOJSON_PATH)
    da_slice = ds[var_name].isel(time=time_idx)

    units = ds[var_name].attrs.get("units", "")
    cb_title = f"log10({units})" if use_log and units else (f"log10({var_name})" if use_log else units or var_name)

    with col_map:
        fig = build_globe_figure(
            da=da_slice,
            projection=projection,
            colorscale=COLORSCALES.get(dataset_key, "Viridis"),
            colorbar_title=cb_title,
            geojson_data=geojson_data,
            stride=stride,
            use_log=use_log,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.subheader("📊 Тренд по региону")
        if geojson_data:
            features = geojson_data.get("features", [])
            region_names = [f["properties"]["name"] for f in features]
            sel_region = st.selectbox("Регион из GeoJSON", region_names)

            feat = next(f for f in features if f["properties"]["name"] == sel_region)
            coords = feat["geometry"]["coordinates"][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]

            da_reg = ds[var_name].sel(
                lat=slice(min(lats), max(lats)),
                lon=slice(min(lons), max(lons)),
            )
            if da_reg.sizes["lat"] == 0:
                da_reg = ds[var_name].sel(
                    lat=slice(max(lats), min(lats)),
                    lon=slice(min(lons), max(lons)),
                )

            ts_mean = da_reg.mean(dim=["lat", "lon"], skipna=True).to_series()
            st.line_chart(ts_mean, height=280)

            curr_val = float(ts_mean.iloc[time_idx])
            hist_mean = float(ts_mean.mean())
            delta = curr_val - hist_mean
            st.metric(
                label=f"Среднее за {selected_label}",
                value=f"{curr_val:.4g} {units}",
                delta=f"{delta:+.4g} от среднего за 25 лет",
            )
        else:
            st.info("Файл ocean_means.geojson не найден — показана только глобальная карта.")


if __name__ == "__main__":
    main()