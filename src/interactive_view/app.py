from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import xarray as xr

st.set_page_config(
    page_title="NASA Earth System Trend Detective",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Resolve directories relative to project root or current working dir
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
PREVIEW_DIR = DATA_DIR / "preview"
REGIONS_DIR = DATA_DIR / "regions"
COORDINATES_DIR = DATA_DIR / "coordinates"
GEOJSON_PATH = COORDINATES_DIR / "garbage_patches.geojson"

DATASET_CONFIG = {
    "chlorophyll_monthly": {
        "label": "Chlorophyll-a (MODIS Aqua)",
        "var": "chlor_a",
        "units": "mg/m³",
        "colorscale": "Viridis",
        "default_log": True,
        "description": "Concentration of photosynthetic pigment in phytoplankton. Key indicator of marine primary productivity.",
    },
    "sst_monthly": {
        "label": "Sea Surface Temperature (MODIS Aqua)",
        "var": "sst",
        "units": "°C",
        "colorscale": "Thermal",
        "default_log": False,
        "description": "Upper ocean skin temperature measured by thermal infrared bands. Drives oceanic stratification.",
    },
    "kd490_monthly": {
        "label": "Light Diffuse Attenuation Kd490 (MODIS Aqua)",
        "var": "Kd_490",
        "units": "m⁻¹",
        "colorscale": "YlGnBu_r",
        "default_log": True,
        "description": "How quickly blue light (490 nm) attenuates with depth. Indicates water clarity and particle turbidity.",
    },
    "reflectance_monthly": {
        "label": "Remote Sensing Reflectance Rrs 531nm (MODIS Aqua)",
        "var": "Rrs_531",
        "units": "sr⁻¹",
        "colorscale": "Ice",
        "default_log": True,
        "description": "Surface spectral reflectance in the green band, sensitive to suspended particulates and water clarity.",
    },
    "salinity_monthly": {
        "label": "Sea Surface Salinity (SMAP)",
        "var": "smap_sss",
        "units": "PSU",
        "colorscale": "Haline",
        "default_log": False,
        "description": "Ocean salinity from NASA SMAP satellite radiometer (2015–2025). Traces evaporation and precipitation.",
    },
    "microplastic_daily": {
        "label": "Microplastic Concentration (CYGNSS)",
        "var": "MP_concentration",
        "units": "count/km²",
        "colorscale": "Inferno",
        "default_log": True,
        "description": "Derived from ocean surface roughness anomaly measured by CYGNSS radar constellation (2017–2018).",
    },
}

REGION_FRIENDLY_NAMES = {
    "gpgp": "Great Pacific Garbage Patch (GPGP) [35°–42°N, 135°–155°W]",
    "north_pacific_north": "North Pacific North Control [45°–52°N, 135°–155°W]",
    "north_pacific_south": "North Pacific South Control [20°–27°N, 135°–155°W]",
    "north_atlantic_patch": "North Atlantic Garbage Patch [25°–35°N, 40°–70°W]",
    "north_atlantic_north": "North Atlantic North Control [40°–50°N, 40°–70°W]",
    "north_atlantic_south": "North Atlantic South Control [10°–20°N, 40°–70°W]",
    "south_pacific_patch": "South Pacific Garbage Patch [25°–35°S, 95°–115°W]",
    "south_pacific_north": "South Pacific North Control [10°–20°S, 95°–115°W]",
    "south_pacific_south": "South Pacific South Control [40°–50°S, 95°–115°W]",
    "south_atlantic_patch": "South Atlantic Garbage Patch [25°–35°S, 0°–20°W]",
    "south_atlantic_north": "South Atlantic North Control [10°–20°S, 0°–20°W]",
    "south_atlantic_south": "South Atlantic South Control [40°–50°S, 0°–20°W]",
    "indian_ocean_patch": "Indian Ocean Garbage Patch [25°–35°S, 70°–90°E]",
    "indian_ocean_north": "Indian Ocean North Control [10°–20°S, 70°–90°E]",
    "indian_ocean_south": "Indian Ocean South Control [40°–50°S, 70°–90°E]",
    "gpgp_model": "GPGP Ekman Model Center [28°–38°N, 131°–151°W]",
    "gpgp_model_north": "GPGP Model North Control [43°–53°N, 131°–151°W]",
    "gpgp_model_south": "GPGP Model South Control [13°–23°N, 131°–151°W]",
}

PATCH_GROUPS = {
    "gpgp": ("north_pacific_north", "north_pacific_south"),
    "gpgp_model": ("gpgp_model_north", "gpgp_model_south"),
    "north_atlantic_patch": ("north_atlantic_north", "north_atlantic_south"),
    "south_pacific_patch": ("south_pacific_north", "south_pacific_south"),
    "south_atlantic_patch": ("south_atlantic_north", "south_atlantic_south"),
    "indian_ocean_patch": ("indian_ocean_north", "indian_ocean_south"),
}


@st.cache_resource
def load_preview_dataset(nc_path: Path) -> xr.Dataset:
    ds = xr.open_dataset(nc_path)
    rename_map = {}
    if "latitude" in ds.coords or "latitude" in ds.dims:
        rename_map["latitude"] = "lat"
    if "longitude" in ds.coords or "longitude" in ds.dims:
        rename_map["longitude"] = "lon"
    if rename_map:
        ds = ds.rename(rename_map)

    # Standardize time coordinate to real timestamps if stored as integers
    if not np.issubdtype(ds["time"].dtype, np.datetime64):
        n_times = len(ds["time"])
        if "salinity" in nc_path.stem:
            dates = pd.date_range("2015-04-01", periods=n_times, freq="MS")
        elif "microplastic" in nc_path.stem:
            dates = pd.date_range("2017-05-01", periods=n_times, freq="MS")
        else:
            dates = pd.date_range("2002-07-01", periods=n_times, freq="MS")
        ds = ds.assign_coords(time=dates)

    return ds


@st.cache_data
def load_geojson(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_regional_series(region_name: str, dataset_key: str) -> pd.Series | None:
    """Loads pre-extracted 4km resolution regional time series with robust month rounding."""
    nc_path = REGIONS_DIR / region_name / f"{dataset_key}.nc"
    if not nc_path.exists():
        return None
    with xr.open_dataset(nc_path) as ds:
        var_name = list(ds.data_vars)[0]
        da = ds[var_name]
        lat_k = "lat" if "lat" in da.coords else "latitude"
        lon_k = "lon" if "lon" in da.coords else "longitude"
        weights = np.cos(np.deg2rad(da[lat_k]))
        ts = da.weighted(weights).mean(dim=[lat_k, lon_k], skipna=True).compute()
        raw_vals = ts.values
        times = pd.to_datetime(ts["time"].values)
        # Robust month rounding: MODIS monthly products can be stamped at 23:30 on the last day of the prior month
        clean_months = (times + pd.Timedelta(days=15)).to_period("M").to_timestamp()
        s = pd.Series(raw_vals, index=clean_months)
        # Drop duplicates and mask out missing fill values (-32767, etc.)
        s = s[~s.index.duplicated(keep="first")]
        s = s[(s.abs() < 1e10) & (s != -32767)].dropna().sort_index()
        return s


def compute_trend(s: pd.Series) -> dict:
    """Computes deseasonalized anomaly, OLS linear trend, AR(1) correction and p-value."""
    s = s.dropna()
    if len(s) < 12:
        return {}

    rolling_12 = s.rolling(12, center=True, min_periods=6).mean()
    anomaly = s.groupby(s.index.month).transform(lambda x: x - x.mean())

    t_years = (s.index - s.index[0]).total_seconds().values / (365.25 * 86400)
    poly = np.polyfit(t_years, anomaly.values, 1)
    slope = float(poly[0])
    intercept = float(poly[1])

    trend_anomaly = intercept + slope * t_years
    mean_val = float(s.mean())

    residuals = anomaly.values - trend_anomaly
    n = len(s)
    r1 = max(float(np.corrcoef(residuals[:-1], residuals[1:])[0, 1]), 0.0) if n > 3 else 0.0
    n_eff = max(n * (1 - r1) / (1 + r1), 5.0)

    s_err = np.sqrt(np.sum(residuals**2) / (n - 2))
    sum_t_diff_sq = np.sum((t_years - np.mean(t_years))**2)
    slope_err = s_err / np.sqrt(sum_t_diff_sq) if sum_t_diff_sq > 0 else 1.0
    slope_err_adj = slope_err * np.sqrt((n - 2) / (n_eff - 2)) if n_eff > 2 else slope_err
    t_stat = slope / slope_err_adj if slope_err_adj > 0 else 0.0

    p_val = math.erfc(abs(t_stat) / math.sqrt(2))
    slope_decade = slope * 10
    pct_decade = (slope_decade / mean_val) * 100 if mean_val != 0 else np.nan
    total_change = slope * t_years[-1]
    total_change_pct = (total_change / mean_val) * 100 if mean_val != 0 else np.nan

    return {
        "raw": s,
        "rolling_12": rolling_12,
        "anomaly": anomaly,
        "trend_line": pd.Series(trend_anomaly + mean_val, index=s.index),
        "trend_line_anomaly": pd.Series(trend_anomaly, index=s.index),
        "slope_per_decade": slope_decade,
        "pct_per_decade": pct_decade,
        "total_change": total_change,
        "total_change_pct": total_change_pct,
        "p_value": p_val,
        "t_stat": t_stat,
        "r1": r1,
        "n_eff": n_eff,
        "is_significant": p_val < 0.05,
        "mean_val": mean_val,
    }


OCEAN_MAPPING = {
    "North Pacific (GPGP)": ("gpgp", "north_pacific_north", "north_pacific_south"),
    "South Pacific": ("south_pacific_patch", "south_pacific_north", "south_pacific_south"),
    "North Atlantic": ("north_atlantic_patch", "north_atlantic_north", "north_atlantic_south"),
    "South Atlantic": ("south_atlantic_patch", "south_atlantic_north", "south_atlantic_south"),
    "Indian Ocean": ("indian_ocean_patch", "indian_ocean_north", "indian_ocean_south"),
}


@st.cache_data
def get_all_oceans_summary(dataset_key: str) -> pd.DataFrame:
    """Calculates spatial baseline averages and contrasts across all 5 global ocean gyres."""
    rows = []
    for ocean, (p, n, s) in OCEAN_MAPPING.items():
        sp = load_regional_series(p, dataset_key)
        sn = load_regional_series(n, dataset_key)
        ss = load_regional_series(s, dataset_key)
        if sp is not None and sn is not None and ss is not None:
            # Synchronize dates
            matched = pd.DataFrame({"patch": sp, "north": sn, "south": ss}).dropna()
            mp = float(matched["patch"].mean())
            mn = float(matched["north"].mean())
            ms = float(matched["south"].mean())
            m_ctrl = (mn + ms) / 2.0
            diff = mp - m_ctrl
            diff_pct = 100.0 * diff / m_ctrl if m_ctrl != 0 else 0.0

            fit_p = compute_trend(sp)
            slope_dec = fit_p.get("slope_per_decade", np.nan)
            pct_dec = fit_p.get("pct_per_decade", np.nan)

            rows.append({
                "ocean": ocean,
                "patch_mean": mp,
                "north_mean": mn,
                "south_mean": ms,
                "control_mean": m_ctrl,
                "difference": diff,
                "difference_pct": diff_pct,
                "slope_per_decade": slope_dec,
                "pct_per_decade": pct_dec,
            })
    return pd.DataFrame(rows)


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
        vals = np.where(np.isfinite(vals) & (vals > 0), np.log10(np.clip(vals, 1e-4, None)), np.nan)

    lats = da["lat"].values
    lons = da["lon"].values

    valid = vals[np.isfinite(vals)]
    vmin = float(np.percentile(valid, 2)) if len(valid) > 0 else 0.0
    vmax = float(np.percentile(valid, 98)) if len(valid) > 0 else 1.0

    if projection == "equirectangular":
        fig = go.Figure(
            go.Heatmap(
                z=vals,
                x=lons,
                y=lats,
                colorscale=colorscale,
                colorbar=dict(title=colorbar_title, thickness=16, len=0.75),
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
                role = feat.get("properties", {}).get("role", "patch")
                color = "rgba(255, 75, 75, 0.9)" if role == "patch" else "rgba(56, 189, 248, 0.8)"
                fig.add_trace(
                    go.Scatter(
                        x=r_lons,
                        y=r_lats,
                        mode="lines",
                        line=dict(color=color, width=2.0),
                        name=feat.get("properties", {}).get("name", "region"),
                        showlegend=False,
                    )
                )

        fig.update_layout(
            xaxis=dict(title="Longitude", range=[-180, 180], showgrid=False),
            yaxis=dict(title="Latitude", range=[-90, 90], scaleanchor="x", showgrid=False),
            plot_bgcolor="rgb(24, 28, 36)",
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
                colorbar=dict(title=colorbar_title, thickness=16, len=0.75),
                cmin=vmin,
                cmax=vmax,
                showscale=True,
                hoverinfo="skip",
            )
        )
        if geojson_data:
            r = 1.006
            for feat in geojson_data.get("features", []):
                coords = feat["geometry"]["coordinates"][0]
                r_lons = np.deg2rad([c[0] for c in coords])
                r_lats = np.deg2rad([c[1] for c in coords])
                role = feat.get("properties", {}).get("role", "patch")
                color = "#ef4444" if role == "patch" else "#38bdf8"
                fig.add_trace(
                    go.Scatter3d(
                        x=r * np.cos(r_lats) * np.cos(r_lons),
                        y=r * np.cos(r_lats) * np.sin(r_lons),
                        z=r * np.sin(r_lats),
                        mode="lines",
                        line=dict(color=color, width=4),
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
                bgcolor="rgb(15, 18, 24)",
            )
        )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=580,
        paper_bgcolor="rgb(15, 18, 24)",
        font=dict(color="white"),
    )
    return fig


def main() -> None:
    st.markdown(
        """
        # 🌍 NASA Earth System Trend Detective
        **NASA Space Apps Challenge 2026** · Interactive Multi-Decadal Ocean Observation Explorer (2002–2025)
        """,
        unsafe_allow_html=True,
    )

    nc_files = sorted(PREVIEW_DIR.glob("*_preview.nc"))
    if not nc_files:
        st.error(f"No preview NetCDF files found in `{PREVIEW_DIR.resolve()}`.")
        return

    file_map = {f.stem.replace("_preview", ""): f for f in nc_files}

    # ==========================
    # SIDEBAR: DATASET & CONTROLS
    # ==========================
    with st.sidebar:
        st.header("⚙️ Mission & Sensor")
        avail_keys = [k for k in DATASET_CONFIG if k in file_map]
        dataset_key = st.selectbox(
            "Select Earth Observation Variable",
            options=avail_keys,
            format_func=lambda k: DATASET_CONFIG[k]["label"],
        )
        cfg = DATASET_CONFIG[dataset_key]
        st.caption(f"**Variable:** `{cfg['var']}` ({cfg['units']})\n\n{cfg['description']}")

        ds = load_preview_dataset(file_map[dataset_key])
        var_name = cfg["var"]
        if var_name not in ds.data_vars:
            var_name = list(ds.data_vars)[0]

        st.divider()
        st.subheader("🗺️ Map Projection")
        view_mode = st.radio(
            "Projection Mode",
            ["3D Digital Globe", "2D Flat Map (Equirectangular)"],
            horizontal=True,
        )
        projection = "orthographic" if "3D" in view_mode else "equirectangular"

        use_log = st.checkbox("Logarithmic scale (log10)", value=cfg["default_log"])
        stride = st.slider("Grid detail (lower = finer, higher = faster)", 1, 4, 2)

    # ==========================
    # TOP SECTION: 3D GLOBE / 2D MAP
    # ==========================
    times = pd.to_datetime(ds["time"].values)
    time_labels = [t.strftime("%Y-%m") for t in times]

    col_time_sel, col_time_info = st.columns([3, 1])
    with col_time_sel:
        selected_label = st.select_slider(
            "📅 Observation Month (2002–2025)",
            options=time_labels,
            value=time_labels[-1],
        )
    with col_time_info:
        time_idx = time_labels.index(selected_label)
        st.metric("Timeline Step", f"{time_idx + 1} of {len(time_labels)}", selected_label)

    geojson_data = load_geojson(GEOJSON_PATH)
    da_slice = ds[var_name].isel(time=time_idx)

    units = cfg["units"]
    cb_title = f"log10({units})" if use_log and units else (units or var_name)

    fig_map = build_globe_figure(
        da=da_slice,
        projection=projection,
        colorscale=cfg["colorscale"],
        colorbar_title=cb_title,
        geojson_data=geojson_data,
        stride=stride,
        use_log=use_log,
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # ==========================
    # BOTTOM SECTION: FULL WIDTH CHART & STATISTICAL ANALYSIS
    # ==========================
    st.divider()

    tab_ts, tab_bars = st.tabs([
        "📈 Regional Time Series & Trend Analysis (Single Gyre)",
        "📊 Global Bar Charts & Spatial Contrast (All 5 Gyres)",
    ])

    if not geojson_data:
        st.warning("Region geometry file (`garbage_patches.geojson`) not found.")
        return

    features = geojson_data.get("features", [])
    patch_keys = list(PATCH_GROUPS.keys())

    with tab_ts:
        col_reg1, col_reg2, col_reg3 = st.columns([2, 1.5, 1.5])
        with col_reg1:
            selected_patch = st.selectbox(
                "Select Ocean Gyre (Garbage Patch Target)",
                options=patch_keys,
                format_func=lambda k: REGION_FRIENDLY_NAMES.get(k, k),
            )

        with col_reg2:
            chart_mode = st.radio(
                "Time Series Display Mode",
                ["Raw Observations + 12-Mo Moving Avg", "Deseasonalized Anomaly"],
                horizontal=False,
            )
            show_deseasonalized = (chart_mode == "Deseasonalized Anomaly")

        with col_reg3:
            compare_controls = st.checkbox(
                "Overlay North & South Controls",
                value=False,
                help="Directly overlays northern and southern boundary controls in absolute physical units.",
            )

        # Extract primary regional time series
        s_primary = load_regional_series(selected_patch, dataset_key)

        # Fallback to spatial slice from preview dataset if regional NetCDF is absent
        if s_primary is None or len(s_primary) == 0:
            feat = next(f for f in features if f["properties"]["name"] == selected_patch)
            coords = feat["geometry"]["coordinates"][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            da_sub = ds[var_name].sel(lat=slice(min(lats), max(lats)), lon=slice(min(lons), max(lons)))
            if da_sub.sizes.get("lat", 0) == 0:
                da_sub = ds[var_name].sel(lat=slice(max(lats), min(lats)), lon=slice(min(lons), max(lons)))
            s_primary = da_sub.mean(dim=["lat", "lon"], skipna=True).to_series().dropna()
            times_sub = pd.to_datetime(s_primary.index)
            s_primary.index = (times_sub + pd.Timedelta(days=15)).to_period("M").to_timestamp()
            s_primary = s_primary[~s_primary.index.duplicated(keep="first")].sort_index()

        if s_primary is None or len(s_primary) < 12:
            st.warning(f"No continuous time series available for `{selected_patch}` in this variable.")
            return

        fit_primary = compute_trend(s_primary)

        # Build interactive Plotly time series chart across full page width
        fig_ts = go.Figure()
        patch_name_short = REGION_FRIENDLY_NAMES.get(selected_patch, selected_patch).split("[")[0].strip()

        # Absolute units for y-axis
        if show_deseasonalized:
            y_primary = fit_primary["anomaly"]
            y_unit_str = f"Anomaly ({units})"
        else:
            y_primary = fit_primary["raw"]
            y_unit_str = f"{cfg['label']} ({units})"

        # Primary series (Monthly points/thin line in absolute units)
        fig_ts.add_trace(
            go.Scatter(
                x=s_primary.index,
                y=y_primary,
                mode="lines",
                line=dict(color="rgba(249, 115, 22, 0.45)", width=1.0),
                name=f"{patch_name_short} (Monthly Data)",
            )
        )

        # 12-Month Rolling Mean in absolute units
        if not show_deseasonalized:
            fig_ts.add_trace(
                go.Scatter(
                    x=fit_primary["rolling_12"].index,
                    y=fit_primary["rolling_12"].values,
                    mode="lines",
                    line=dict(color="#f97316", width=2.6),
                    name=f"{patch_name_short} (12-Mo Moving Avg)",
                )
            )

        # Linear Trendline (OLS) in absolute units
        trend_y = fit_primary["trend_line_anomaly"] if show_deseasonalized else fit_primary["trend_line"]

        fig_ts.add_trace(
            go.Scatter(
                x=trend_y.index,
                y=trend_y.values,
                mode="lines",
                line=dict(color="#ef4444", width=2.2, dash="dash"),
                name=f"Linear Trend ({fit_primary['slope_per_decade']:+.4g} {units}/dec)",
            )
        )

        # Optional Control zones comparison in absolute units
        if compare_controls and selected_patch in PATCH_GROUPS:
            north_key, south_key = PATCH_GROUPS[selected_patch]
            ctrl_colors = {"north": "#38bdf8", "south": "#34d399"}

            for ctrl_key, side in [(north_key, "North"), (south_key, "South")]:
                s_ctrl = load_regional_series(ctrl_key, dataset_key)
                if s_ctrl is not None and len(s_ctrl) > 12:
                    fit_ctrl = compute_trend(s_ctrl)
                    y_ctrl = fit_ctrl["anomaly"] if show_deseasonalized else fit_ctrl["rolling_12"]
                    label_suffix = " (12-Mo Avg)" if not show_deseasonalized else " Anomaly"

                    fig_ts.add_trace(
                        go.Scatter(
                            x=y_ctrl.index,
                            y=y_ctrl.values,
                            mode="lines",
                            line=dict(color=ctrl_colors[side.lower()], width=2.0),
                            name=f"{side} Control{label_suffix} ({fit_ctrl['slope_per_decade']:+.4g} {units}/dec)",
                        )
                    )

        fig_ts.update_layout(
            height=450,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Observation Year", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            yaxis=dict(title=y_unit_str, showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
            paper_bgcolor="rgb(15, 18, 24)",
            plot_bgcolor="rgb(20, 24, 32)",
            font=dict(color="white"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                bgcolor="rgba(0,0,0,0.5)",
            ),
        )

        st.plotly_chart(fig_ts, use_container_width=True)

        # ==========================
        # STATISTICAL METRICS ROW (ABSOLUTE UNITS)
        # ==========================
        m1, m2, m3, m4 = st.columns(4)

        rate_str = f"{fit_primary['slope_per_decade']:+.4g} {units} / dec"
        pct_str = f"{fit_primary['pct_per_decade']:+.2f}% / decade"

        total_str = f"{fit_primary['total_change']:+.4g} {units}"
        total_pct_str = f"{fit_primary['total_change_pct']:+.1f}% total"

        p_val = fit_primary["p_value"]
        sig_badge = "Significant (p < 0.01) ✅" if p_val < 0.01 else ("Significant (p < 0.05) 🟡" if p_val < 0.05 else "Not Significant ⚪")

        curr_val = float(s_primary.iloc[min(time_idx, len(s_primary) - 1)])
        delta_hist = curr_val - fit_primary["mean_val"]

        with m1:
            st.metric(label="Decadal Trend Rate (Absolute)", value=rate_str, delta=pct_str)
        with m2:
            st.metric(label="Total 23-Year Change (Absolute)", value=total_str, delta=total_pct_str)
        with m3:
            st.metric(label="Significance (t-test / AR1)", value=sig_badge, delta=f"p = {p_val:.3g}")
        with m4:
            st.metric(
                label=f"Selected Month ({selected_label})",
                value=f"{curr_val:.4g} {units}",
                delta=f"{delta_hist:+.4g} vs 23-yr mean",
            )

        # ==========================
        # DATA DETECTIVE CASE BRIEFING
        # ==========================
        st.info(
            f"""
            **🕵️ Data Detective Finding for {patch_name_short}:**
            * **The Oligotrophic Gyre Expansion:** In 3 of the 5 global ocean gyres (*Great Pacific, North Atlantic, Indian Ocean*), 
              phytoplankton chlorophyll declines significantly (**−6% to −8% per decade**, $p < 0.01$) while sea surface temperature rises (**+0.3°C to +0.6°C per decade**). 
              Warm surface waters create strong vertical stratification, preventing nutrient upwelling from below and expanding "ocean deserts".
            * **The Controls Divergence:** Notice how the northern and southern control zones show neutral or positive chlorophyll trends (**+3% to +10% per decade**). 
              This illustrates NASA's challenge objective: *one global warming process driving diametrically opposite environmental trends in different regions*.
            * **Why Satellites Do Not "See" Plastic Directly:** Optical satellite sensors (MODIS 4 km pixels) cannot directly detect microplastics suspended in water. 
              Instead, Earth science satellites document the profound ecological transformation of the oceanic gyres where that debris accumulates.
            """
        )

    # ==========================
    # TAB 2: GLOBAL BAR CHARTS (ALL 5 GYRES)
    # ==========================
    with tab_bars:
        st.markdown(f"### 📊 Five Ocean Gyres Comparison — `{cfg['label']}`")
        st.caption(
            "Comparing the 5 major ocean garbage patches (subtropical gyre centers) with their boundary controls (North and South)."
        )

        df_oceans = get_all_oceans_summary(dataset_key)

        if df_oceans.empty:
            st.warning("Insufficient multi-region data available for this parameter.")
        else:
            col_b1, col_b2 = st.columns(2)

            with col_b1:
                # Graph 1: Grouped bar chart (Patch vs North vs South) in physical units
                st.markdown(f"#### 1. Baseline Regional Means ({units})")
                fig_bar1 = go.Figure()
                fig_bar1.add_trace(go.Bar(
                    x=df_oceans["ocean"],
                    y=df_oceans["patch_mean"],
                    name="Patch Center",
                    marker_color="#f97316",
                ))
                fig_bar1.add_trace(go.Bar(
                    x=df_oceans["ocean"],
                    y=df_oceans["north_mean"],
                    name="North Control",
                    marker_color="#38bdf8",
                ))
                fig_bar1.add_trace(go.Bar(
                    x=df_oceans["ocean"],
                    y=df_oceans["south_mean"],
                    name="South Control",
                    marker_color="#34d399",
                ))
                fig_bar1.update_layout(
                    barmode="group",
                    height=380,
                    margin=dict(l=10, r=10, t=30, b=10),
                    yaxis=dict(title=f"{units}", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
                    paper_bgcolor="rgb(15, 18, 24)",
                    plot_bgcolor="rgb(20, 24, 32)",
                    font=dict(color="white"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                )
                st.plotly_chart(fig_bar1, use_container_width=True)

            with col_b2:
                # Graph 2: Spatial contrast (% difference: Patch vs Average Control)
                st.markdown("#### 2. Spatial Contrast: Patch vs Average Control (%)")
                bar_colors = ["#ef4444" if v < 0 else "#22c55e" for v in df_oceans["difference_pct"]]
                fig_bar2 = go.Figure(go.Bar(
                    x=df_oceans["ocean"],
                    y=df_oceans["difference_pct"],
                    marker_color=bar_colors,
                    text=[f"{v:+.1f}%" for v in df_oceans["difference_pct"]],
                    textposition="auto",
                ))
                fig_bar2.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
                fig_bar2.update_layout(
                    height=380,
                    margin=dict(l=10, r=10, t=30, b=10),
                    yaxis=dict(title="Patch vs Control Mean (%)", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
                    paper_bgcolor="rgb(15, 18, 24)",
                    plot_bgcolor="rgb(20, 24, 32)",
                    font=dict(color="white"),
                )
                st.plotly_chart(fig_bar2, use_container_width=True)

            # Graph 3: Decadal Trend Rate across the 5 Patches
            st.markdown(f"#### 3. Multi-Decadal Climate Trend Rate by Ocean Gyre ({units}/decade)")
            trend_colors = ["#f97316" if v > 0 else "#38bdf8" for v in df_oceans["slope_per_decade"]]
            fig_bar3 = go.Figure(go.Bar(
                x=df_oceans["ocean"],
                y=df_oceans["slope_per_decade"],
                marker_color=trend_colors,
                text=[f"{v:+.3g} {units}/dec" for v in df_oceans["slope_per_decade"]],
                textposition="auto",
            ))
            fig_bar3.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            fig_bar3.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=30, b=10),
                yaxis=dict(title=f"Decadal Trend Rate ({units}/decade)", showgrid=True, gridcolor="rgba(255,255,255,0.1)"),
                paper_bgcolor="rgb(15, 18, 24)",
                plot_bgcolor="rgb(20, 24, 32)",
                font=dict(color="white"),
            )
            st.plotly_chart(fig_bar3, use_container_width=True)

            # Summary Table & Scientific Note
            st.markdown("#### 📋 Numerical Summary Across All 5 Oceans")
            display_df = df_oceans.copy()
            st.dataframe(
                display_df.style.format({
                    "patch_mean": "{:.5g}",
                    "north_mean": "{:.5g}",
                    "south_mean": "{:.5g}",
                    "control_mean": "{:.5g}",
                    "difference": "{:+.4g}",
                    "difference_pct": "{:+.2f}%",
                    "slope_per_decade": "{:+.4g}",
                    "pct_per_decade": "{:+.2f}%",
                }),
                use_container_width=True,
            )

            st.info(
                """
                **💡 Spatial Contrast vs. Temporal Trend:**
                * **Spatial Contrast (Graph 1 & 2):** Compares the core of each subtropical gyre against its surrounding boundaries. 
                  In almost all gyres, the patch center has **significantly lower chlorophyll and lower 531 nm reflectance** (−1% to −13%) 
                  than surrounding subpolar/tropical waters because gyres are ultra-oligotrophic "optical deserts".
                * **Temporal Trend (Graph 3 & Tab 1):** Measures the rate of change over time (2002–2025). 
                  While spatial contrast explains where the gyre is today, the temporal trend shows how climate warming is 
                  intensifying stratification and expanding these deserts further.
                """
            )


if __name__ == "__main__":
    main()
