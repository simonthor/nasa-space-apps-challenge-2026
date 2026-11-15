"""Map of the regions of the garbage-patch analysis (giovanni.py REGIONS): the five patches of PATCHES, the control
boxes north and south of each (PATCH_CONTROLS) and the boxes of the Pacific, Atlantic and Indian Ocean means
(OCEANS). plots/garbage_patch/regions.png.

The same boxes as GeoJSON (RFC 7946): garbage_patches.geojson (every patch of PATCH_CONTROLS with its controls) and
ocean_means.geojson (the boxes of OCEANS).
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

from giovanni import DATA, OCEANS, PATCH_CONTROLS, PATCHES, REGIONS
from plot_style import INK, INK_SECONDARY, ORANGE, PURPLE, SHORT_NAMES, SLIDE_SIZE, save

COUNTRIES = DATA.parent / "natural_earth" / "ne_50m_admin_0_countries.geojson"

fig, ax = plt.subplots(figsize=SLIDE_SIZE)
ax.set_facecolor("#e8eef3")  # ocean
for feature in json.loads(COUNTRIES.read_text())["features"]:
    geometry = feature["geometry"]
    for polygon in geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]:
        for shift in (0, 360):  # map centred on the Pacific: longitudes 20°E-380°E
            ring = [(x + shift, y) for x, y in polygon[0]]
            ax.add_patch(Polygon(ring, fc="#d9d7d0", ec="none", zorder=1))


def add_box(region, label_position, label, **kwargs):
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    w, e = w % 360, w % 360 + (e - w)  # longitudes 0-360
    ax.add_patch(Rectangle((w, s), e - w, n - s, zorder=2, **kwargs))
    if label:
        x, y, ha, va = {"above": ((w + e) / 2, n + 1.5, "center", "bottom"),
                        "below": ((w + e) / 2, s - 1.5, "center", "top"),
                        "right": (e + 2, (s + n) / 2, "left", "center"),
                        "left": (w - 2, (s + n) / 2, "right", "center")}[label_position]
        ax.text(x, y, label, ha=ha, va=va, fontsize=12, color=kwargs.get("ec", INK), zorder=3)


for boxes in OCEANS.values():
    for region in boxes:
        add_box(region, None, None, fc=PURPLE, alpha=0.1, ec="none")
        add_box(region, None, None, fc="none", ec=PURPLE, lw=0.8, ls=":")
for x, ocean in [(205, "Pacific"), (337, "Atlantic"), (81, "Indian Ocean")]:
    ax.text(x, -57, f"{ocean} mean ({len(OCEANS[ocean.split()[0].lower()])} boxes)", ha="center", fontsize=12,
            color=PURPLE)
ax.text(378, 63, "Global mean: the whole globe", ha="right", va="top", fontsize=12, color=INK_SECONDARY,
        bbox=dict(fc="white", ec="none", alpha=0.85))
for region in PATCHES:
    add_box(region, "left", SHORT_NAMES[region], fc="none", ec=INK, lw=2)
    for control in PATCH_CONTROLS[region][:2]:
        add_box(control, None, None, fc="none", ec=ORANGE, lw=1.6, ls="--")
ax.legend(handles=[Rectangle((0, 0), 1, 1, fc="none", ec=INK, lw=2, label="Garbage patch"),
                   Rectangle((0, 0), 1, 1, fc="none", ec=ORANGE, lw=1.6, ls="--", label="Control north / south"),
                   Rectangle((0, 0), 1, 1, fc=PURPLE, alpha=0.25, ec=PURPLE, ls=":", label="Ocean mean")],
          loc="upper left", fontsize=11, frameon=True, facecolor="white", edgecolor="none", framealpha=0.85)

ax.set_xlim(20, 380)
ax.set_ylim(-65, 65)
ax.set_aspect(1)
ax.set_xticks(range(30, 380, 60), [f"{abs((x + 180) % 360 - 180)}°{'W' if x > 180 else 'E' if x < 180 else ''}"
                                    for x in range(30, 380, 60)])
ax.set_yticks(range(-60, 61, 30), [f"{abs(y)}°{'S' if y < 0 else 'N' if y > 0 else ''}" for y in range(-60, 61, 30)])
ax.tick_params(length=0, colors=INK_SECONDARY)
for side in ax.spines.values():
    side.set_visible(False)
fig.tight_layout()
save(fig, "garbage_patch/regions.png")


def feature(region, **properties):
    """GeoJSON polygon of a giovanni.py REGIONS box; the ring runs counter-clockwise (RFC 7946)."""
    w, s, e, n = (int(x) if float(x).is_integer() else float(x) for x in REGIONS[region][1].split(","))
    return {"type": "Feature", "properties": {"name": region, "label": REGIONS[region][0], **properties},
            "geometry": {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}}


patch_features = []
for patch, (north, south, _) in PATCH_CONTROLS.items():
    patch_features += [feature(patch, role="patch", patch=patch), feature(north, role="control north", patch=patch),
                       feature(south, role="control south", patch=patch)]
ocean_features = [feature(box, role="ocean mean", ocean=ocean) for ocean, boxes in OCEANS.items() for box in boxes]
for name, features in [("garbage_patches", patch_features), ("ocean_means", ocean_features)]:
    path = Path(__file__).parent / f"{name}.geojson"
    collection = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n")
    print(path)
