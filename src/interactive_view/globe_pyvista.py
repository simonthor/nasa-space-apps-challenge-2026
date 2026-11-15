from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import xarray as xr

PREVIEW_DIR = Path("../../data/preview")
GEOJSON_PATH = Path("../../data/coordinates/garbage_patches.geojson")  # Укажите путь к вашему GeoJSON-файлу

# Use standard matplotlib colormaps (do not require cmocean)
DATASETS = [
    ("chlorophyll_monthly", "Chlorophyll (Chl-a)", "viridis", True),
    ("sst_monthly", "Sea Surface Temp (SST)", "plasma", False),
    ("salinity_monthly", "Salinity (SSS)", "cividis", False),
    ("reflectance_monthly", "Remote Sensing Reflectance (Rrs)", "Blues_r", True),
    ("kd490_monthly", "Diffuse Attenuation (Kd490)", "YlGnBu_r", True),
    ("microplastic_daily", "Microplastics (CYGNSS)", "inferno", True),
]


def load_dataset(nc_path: Path, use_log: bool) -> dict:
    ds = xr.open_dataset(nc_path)
    rename_map = {}
    if "latitude" in ds.coords:
        rename_map["latitude"] = "lat"
    if "longitude" in ds.coords:
        rename_map["longitude"] = "lon"
    if rename_map:
        ds = ds.rename(rename_map)

    # Convert longitude from 0..360 to -180..180 and sort
    if float(ds["lon"].max()) > 180.0:
        ds = ds.assign_coords(lon=(((ds["lon"] + 180) % 360) - 180)).sortby("lon")

    var_name = list(ds.data_vars)[0]
    da = ds[var_name].transpose("time", "lat", "lon")
    data_3d = da.values.astype(np.float32)

    if use_log:
        with np.errstate(divide="ignore", invalid="ignore"):
            valid_pos = np.isfinite(data_3d) & (data_3d > 0)
            data_3d = np.where(valid_pos, np.log10(data_3d), np.nan)

    vmin = float(np.nanpercentile(data_3d, 2))
    vmax = float(np.nanpercentile(data_3d, 98))
    times = [str(t)[:7] for t in ds["time"].values]

    return {
        "var_name": var_name,
        "data_3d": data_3d,
        "lats": ds["lat"].values,
        "lons": ds["lon"].values,
        "times": times,
        "vmin": vmin,
        "vmax": vmax,
    }


def create_earth_grid(lats: np.ndarray, lons: np.ndarray, flat: bool = False) -> pv.StructuredGrid:
    """Creates a 3D sphere or a flat equirectangular grid from lat/lon coordinates."""
    if not flat:
        # Close the antimeridian seam (+180°) so there is no gap on the sphere
        lons = np.append(lons, lons[0] + 360.0)

    lon_grid, lat_grid = np.meshgrid(lons, lats)

    if flat:
        x = lon_grid
        y = lat_grid
        z = np.zeros_like(x)
    else:
        lat_rad = np.deg2rad(lat_grid)
        lon_rad = np.deg2rad(lon_grid)
        x = np.cos(lat_rad) * np.cos(lon_rad)
        y = np.cos(lat_rad) * np.sin(lon_rad)
        z = np.sin(lat_rad)

    return pv.StructuredGrid(x, y, z)


def get_frame_scalars(data_slice: np.ndarray, flat: bool = False) -> np.ndarray:
    """Prepares a 2D data slice in Fortran order for VTK StructuredGrid."""
    if not flat:
        # Duplicate the first longitude column at the end for a seamless sphere
        data_slice = np.hstack([data_slice, data_slice[:, :1]])
    return data_slice.ravel(order="F")


def latlon_to_xyz(lats: np.ndarray, lons: np.ndarray, flat: bool = False, radius: float = 1.003) -> np.ndarray:
    """Переводит массивы широт/долгот в 3D-координаты сферы (чуть выше поверхности) или плоской карты."""
    if flat:
        return np.column_stack([lons, lats, np.full_like(lons, 0.2, dtype=np.float64)])

    lat_rad = np.deg2rad(lats)
    lon_rad = np.deg2rad(lons)
    x = radius * np.cos(lat_rad) * np.cos(lon_rad)
    y = radius * np.cos(lat_rad) * np.sin(lon_rad)
    z = radius * np.sin(lat_rad)
    return np.column_stack([x, y, z])


def create_geojson_borders(geojson_path: Path, flat: bool = False, step_deg: float = 1.0) -> pv.PolyData | None:
    """Строит PolyData с полилиниями всех полигонов из GeoJSON с дискретизацией по дуге."""
    if not geojson_path.exists():
        print(f"[Warn] GeoJSON not found: {geojson_path}")
        return None

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    polylines: list[pv.PolyData] = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue

        for ring in geom.get("coordinates", []):
            pts_lon: list[np.ndarray] = []
            pts_lat: list[np.ndarray] = []

            for (lon1, lat1), (lon2, lat2) in zip(ring[:-1], ring[1:]):
                dist = max(abs(lon2 - lon1), abs(lat2 - lat1))
                n_steps = max(2, int(np.ceil(dist / step_deg)) + 1)
                pts_lon.append(np.linspace(lon1, lon2, n_steps))
                pts_lat.append(np.linspace(lat1, lat2, n_steps))

            if pts_lon:
                lons_arr = np.concatenate(pts_lon)
                lats_arr = np.concatenate(pts_lat)
                xyz = latlon_to_xyz(lats_arr, lons_arr, flat=flat)
                polylines.append(pv.lines_from_points(xyz))

    if not polylines:
        return None

    return pv.merge(polylines)


def run_viewer(initial_key: str = "chlorophyll_monthly") -> None:
    loaded_datasets: dict[str, dict] = {}
    available_meta: list[tuple[str, str, str, bool]] = []

    for key, label, cmap, use_log in DATASETS:
        nc_path = PREVIEW_DIR / f"{key}_preview.nc"
        if nc_path.exists():
            print(f"Loading {label} ({nc_path.name})...")
            info = load_dataset(nc_path, use_log)
            info.update({"key": key, "label": label, "cmap": cmap, "use_log": use_log})
            loaded_datasets[key] = info
            available_meta.append((key, label, cmap, use_log))

    if not loaded_datasets:
        print(f"No *_preview.nc files found in {PREVIEW_DIR}")
        return

    if initial_key not in loaded_datasets:
        initial_key = available_meta[0][0]

    state = {
        "key": initial_key,
        "idx": 0,
        "flat": False,
        "playing": False,
        "syncing_ui": False,
        "show_borders": True,
    }

    current = loaded_datasets[initial_key]
    lats = current["lats"]
    lons = current["lons"]

    plotter = pv.Plotter(window_size=(1450, 900), title="NASA Ocean Explorer")
    plotter.set_background("#0b0f19")
    # Lock rotation around the vertical Z-axis (keeps poles upright)
    plotter.enable_terrain_style(mouse_wheel_zooms=True)

    # Initial 3D sphere
    grid = create_earth_grid(lats, lons, flat=False)
    grid["values"] = get_frame_scalars(current["data_3d"][0], flat=False)

    # Dark base sphere for continents (where values == NaN)
    land_sphere = pv.Sphere(radius=0.996, theta_resolution=180, phi_resolution=90)
    land_actor = plotter.add_mesh(land_sphere, color="#1e2430", smooth_shading=True)

    def make_scalar_bar_title(ds_info: dict) -> str:
        prefix = "log10 " if ds_info["use_log"] else ""
        return f"{prefix}{ds_info['var_name']}"

    mesh_actor = plotter.add_mesh(
        grid,
        scalars="values",
        cmap=current["cmap"],
        clim=[current["vmin"], current["vmax"]],
        nan_opacity=0.0,
        smooth_shading=False,
        scalar_bar_args={
            "title": make_scalar_bar_title(current),
            "color": "white",
            "vertical": True,
            "position_x": 0.90,
            "position_y": 0.25,
        },
    )

    borders_mesh = create_geojson_borders(GEOJSON_PATH, flat=False)
    borders_actor = (
        plotter.add_mesh(borders_mesh, color="white", line_width=2.0, lighting=False)
        if borders_mesh is not None
        else None
    )

    # Set camera so the Z-axis (poles) points straight up
    plotter.camera.up = (0.0, 0.0, 1.0)
    plotter.camera.position = (3.2, 0.0, 0.4)
    plotter.camera.focal_point = (0.0, 0.0, 0.0)

    def get_header_text() -> str:
        ds_info = loaded_datasets[state["key"]]
        t_str = ds_info["times"][state["idx"]]
        mode_str = "2D Map" if state["flat"] else "3D Globe"
        return (
            f"{ds_info['label']}  |  Date: {t_str}  |  View: {mode_str}\n"
            f"[1-5: Parameter | Space: Play/Pause | ←/→: Step Month | M: 3D/2D | B: Regions]"
        )

    date_text = plotter.add_text(
        get_header_text(),
        position="upper_left",
        font_size=11,
        color="white",
    )

    def update_frame(new_idx: int) -> None:
        ds_info = loaded_datasets[state["key"]]
        n_times = len(ds_info["times"])
        idx = int(new_idx) % n_times
        state["idx"] = idx

        grid["values"] = get_frame_scalars(ds_info["data_3d"][idx], flat=state["flat"])
        date_text.SetText(2, get_header_text())
        plotter.render()

    def rebuild_mesh() -> None:
        nonlocal grid, mesh_actor, borders_actor
        ds_info = loaded_datasets[state["key"]]
        flat = state["flat"]

        # Remove old mesh and old scalar bar
        plotter.remove_actor(mesh_actor)
        for bar_title in list(plotter.scalar_bars.keys()):
            plotter.remove_scalar_bar(bar_title)

        land_actor.SetVisibility(not flat)

        grid = create_earth_grid(ds_info["lats"], ds_info["lons"], flat=flat)
        grid["values"] = get_frame_scalars(ds_info["data_3d"][state["idx"]], flat=flat)

        mesh_actor = plotter.add_mesh(
            grid,
            scalars="values",
            cmap=ds_info["cmap"],
            clim=[ds_info["vmin"], ds_info["vmax"]],
            nan_opacity=0.0 if not flat else 1.0,
            nan_color="#1e2430",
            smooth_shading=False,
            scalar_bar_args={
                "title": make_scalar_bar_title(ds_info),
                "color": "white",
                "vertical": True,
                "position_x": 0.90,
                "position_y": 0.25,
            },
        )

        if borders_actor is not None:
            plotter.remove_actor(borders_actor)
            borders_mesh = create_geojson_borders(GEOJSON_PATH, flat=flat)
            if borders_mesh is not None:
                borders_actor = plotter.add_mesh(borders_mesh, color="white", line_width=2.0, lighting=False)
                borders_actor.SetVisibility(state["show_borders"])

    # Time slider at the bottom of the window
    slider = plotter.add_slider_widget(
        callback=lambda val: update_frame(round(val)),
        rng=[0, len(current["times"]) - 1],
        value=0,
        title="Month",
        pointa=(0.28, 0.06),
        pointb=(0.85, 0.06),
        style="modern",
        color="white",
    )

    # Parameter switcher (Chlorophyll, SST, Salinity, Reflectance, Microplastics)
    checkboxes: dict[str, object] = {}

    def select_dataset(new_key: str) -> None:
        if new_key not in loaded_datasets or state["key"] == new_key:
            return

        state["key"] = new_key
        ds_info = loaded_datasets[new_key]
        n_times = len(ds_info["times"])
        state["idx"] = min(state["idx"], n_times - 1)

        # Synchronize radio-button checkboxes in UI
        state["syncing_ui"] = True
        for k, cb in checkboxes.items():
            cb.GetRepresentation().SetState(int(k == new_key))
        state["syncing_ui"] = False

        # Update slider range for the selected dataset
        rep = slider.GetRepresentation()
        rep.SetMaximumValue(n_times - 1)
        rep.SetValue(state["idx"])

        rebuild_mesh()
        date_text.SetText(2, get_header_text())
        plotter.render()

    # Place parameter selection buttons in the bottom-left corner (bottom-up)
    # so they stay visible regardless of window resizing
    n_btns = len(available_meta)
    base_y = 85
    step_y = 36

    for idx_btn, (key, label, _, _) in enumerate(available_meta):
        y_pos = base_y + (n_btns - 1 - idx_btn) * step_y

        def make_cb(target_key: str):
            def _on_click(flag: bool) -> None:
                if state["syncing_ui"]:
                    return
                if not flag:
                    # Keep the active radio button checked
                    state["syncing_ui"] = True
                    checkboxes[target_key].GetRepresentation().SetState(1)
                    state["syncing_ui"] = False
                    return
                select_dataset(target_key)

            return _on_click

        cb = plotter.add_checkbox_button_widget(
            callback=make_cb(key),
            value=(key == initial_key),
            position=(25, y_pos),
            size=24,
            border_size=2,
            color_on="#38bdf8",
            color_off="#1e293b",
            background_color="#0f172a",
        )
        checkboxes[key] = cb
        plotter.add_text(f"[{idx_btn + 1}] {label}", position=(58, y_pos + 3), font_size=10, color="white")

    # 3D / 2D projection toggle
    def set_projection(flat: bool) -> None:
        if state["flat"] == flat:
            return
        state["flat"] = flat
        rebuild_mesh()

        if flat:
            # Disable 3D rotation in 2D mode (pan and zoom only)
            plotter.enable_image_style()
            plotter.view_xy()
            plotter.reset_camera()
        else:
            # Restore Z-axis constrained rotation in 3D mode
            plotter.enable_terrain_style(mouse_wheel_zooms=True)
            plotter.camera.up = (0.0, 0.0, 1.0)
            plotter.camera.position = (3.2, 0.0, 0.4)
            plotter.camera.focal_point = (0.0, 0.0, 0.0)
            plotter.reset_camera_clipping_range()

        date_text.SetText(2, get_header_text())
        plotter.render()

    def on_2d_checkbox(flag: bool) -> None:
        if not state["syncing_ui"]:
            set_projection(flag)

    mode_checkbox = plotter.add_checkbox_button_widget(
        callback=on_2d_checkbox,
        value=False,
        position=(25, 25),
        size=24,
        border_size=2,
        color_on="#38bdf8",
        color_off="#1e293b",
        background_color="#0f172a",
    )
    plotter.add_text("2D Map (M)", position=(58, 28), font_size=10, color="white")

    def toggle_projection_key() -> None:
        new_flat = not state["flat"]
        state["syncing_ui"] = True
        mode_checkbox.GetRepresentation().SetState(int(new_flat))
        state["syncing_ui"] = False
        set_projection(new_flat)

    # Regions borders visibility toggle
    def set_borders_visible(visible: bool) -> None:
        state["show_borders"] = visible
        if borders_actor is not None:
            borders_actor.SetVisibility(visible)
        plotter.render()

    def on_borders_checkbox(flag: bool) -> None:
        if not state["syncing_ui"]:
            set_borders_visible(flag)

    borders_checkbox = plotter.add_checkbox_button_widget(
        callback=on_borders_checkbox,
        value=True,
        position=(190, 25),
        size=24,
        border_size=2,
        color_on="#38bdf8",
        color_off="#1e293b",
        background_color="#0f172a",
    )
    plotter.add_text("Regions (B)", position=(223, 28), font_size=10, color="white")

    def toggle_borders_key() -> None:
        new_vis = not state["show_borders"]
        state["syncing_ui"] = True
        borders_checkbox.GetRepresentation().SetState(int(new_vis))
        state["syncing_ui"] = False
        set_borders_visible(new_vis)

    # Keyboard controls and timelapse playback
    def step_frame(delta: int) -> None:
        n_times = len(loaded_datasets[state["key"]]["times"])
        next_i = (state["idx"] + delta) % n_times
        slider.GetRepresentation().SetValue(next_i)
        update_frame(next_i)

    plotter.add_key_event("Right", lambda: step_frame(1))
    plotter.add_key_event("Left", lambda: step_frame(-1))
    plotter.add_key_event("space", lambda: state.update({"playing": not state["playing"]}))
    plotter.add_key_event("m", toggle_projection_key)
    plotter.add_key_event("b", toggle_borders_key)

    for idx_btn, (key, _, _, _) in enumerate(available_meta):
        plotter.add_key_event(str(idx_btn + 1), lambda k=key: select_dataset(k))

    def timer_callback(step: int) -> None:
        if state["playing"]:
            step_frame(1)

    plotter.add_timer_event(max_steps=100000, duration=80, callback=timer_callback)
    plotter.show()


if __name__ == "__main__":
    param = sys.argv[1] if len(sys.argv) > 1 else "chlorophyll_monthly"
    run_viewer(param)