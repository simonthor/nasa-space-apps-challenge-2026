from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RegionSpec:
    name: str
    lat_bounds: tuple[float, float]
    lon_bounds: tuple[float, float]
    properties: dict[str, Any]
    ring_coords: list[tuple[float, float]]  # [(lon, lat), ...]
    is_axis_aligned_box: bool


def parse_geojson_feature(feature: dict[str, Any]) -> RegionSpec:
    """Превращает один GeoJSON Feature (Polygon) в RegionSpec."""
    geom = feature.get("geometry", {})
    if geom.get("type") != "Polygon":
        raise ValueError(f"Expected Polygon geometry, got {geom.get('type')}")

    # В GeoJSON внешнее кольцо полигона — первый элемент coordinates: [[lon, lat], ...]
    outer_ring = geom["coordinates"][0]
    lons = [float(pt[0]) for pt in outer_ring]
    lats = [float(pt[1]) for pt in outer_ring]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Проверяем, является ли полигон точным прямоугольником по осям lat/lon
    unique_pts = {(float(pt[0]), float(pt[1])) for pt in outer_ring}
    expected_corners = {
        (min_lon, min_lat),
        (max_lon, min_lat),
        (max_lon, max_lat),
        (min_lon, max_lat),
    }
    is_box = unique_pts == expected_corners

    props = dict(feature.get("properties") or {})
    name = props.get("name") or props.get("id") or "unnamed_region"

    return RegionSpec(
        name=name,
        lat_bounds=(min_lat, max_lat),
        lon_bounds=(min_lon, max_lon),
        properties=props,
        ring_coords=[(float(pt[0]), float(pt[1])) for pt in outer_ring],
        is_axis_aligned_box=is_box,
    )


def load_geojson_regions(geojson_path: str | Path) -> list[RegionSpec]:
    """Читает GeoJSON-файл (FeatureCollection или одиночный Feature)."""
    data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))

    if data.get("type") == "FeatureCollection":
        return [parse_geojson_feature(feat) for feat in data.get("features", [])]
    if data.get("type") == "Feature":
        return [parse_geojson_feature(data)]

    raise ValueError(f"Unsupported GeoJSON root type: {data.get('type')}")