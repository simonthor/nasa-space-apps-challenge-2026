"""Ekman transport into each garbage-patch box, monthly 1980-2026, from the MERRA-2 wind stress on the box edges.

The Ekman volume transport per unit length is M = τ × ẑ / (ρ f), i.e. (U, V) = (τ_y, -τ_x) / (ρ f) (Vallis,
Atmospheric and Oceanic Fluid Dynamics, ch. 5). Its net inflow through the four edges of the box,
    C = V(south) L(south) - V(north) L(north) + U(west) L_y - U(east) L_y,
is the wind-driven surface convergence that gathers floating debris (positive: inflow, downwelling C / area).
Edge strips as fetched by fetch_garbage_patch.sh (data/giovanni/<patch>_edge_<side>/).

data/garbage_patch_ekman.csv; plots/garbage_patch/ekman_convergence.png
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from giovanni import DATA, PATCHES, REGIONS, fit_trend, load_series
from plot_style import AQUA, BLUE, INK, INK_SECONDARY, ORANGE, SHORT_NAMES, p_text, save, style

RHO = 1025  # sea water density, kg/m³
OMEGA = 7.2921e-5  # Earth's rotation rate, 1/s
EARTH_RADIUS = 6.371e6  # m
SVERDRUP = 1e6  # m³/s


def coriolis(latitude):
    return 2 * OMEGA * np.sin(np.radians(latitude))


rows, convergence = [], {}
for region in PATCHES:
    w, s, e, n = map(float, REGIONS[region][1].split(","))
    stress = {side: load_series(f"{region}_edge_{side}", "M2TMNXOCN_5_12_4_" + ("TAUXWTR" if side in ["south", "north"]
                                                                               else "TAUYWTR")) / 1000  # N/m²
              for side in ["south", "north", "west", "east"]}
    length_x = {side: EARTH_RADIUS * np.cos(np.radians(lat)) * np.radians(e - w) for side, lat in [("south", s),
                                                                                                  ("north", n)]}
    length_y = EARTH_RADIUS * np.radians(n - s)
    f_mid = coriolis((s + n) / 2)
    inflow = (-stress["south"] / (RHO * coriolis(s)) * length_x["south"]
              + stress["north"] / (RHO * coriolis(n)) * length_x["north"]
              + (stress["west"] - stress["east"]) / (RHO * f_mid) * length_y).dropna()
    area = EARTH_RADIUS ** 2 * np.radians(e - w) * abs(np.sin(np.radians(n)) - np.sin(np.radians(s)))
    convergence[region] = inflow / SVERDRUP
    fit = fit_trend(convergence[region])
    mean = convergence[region].mean()
    rows.append(dict(region=region, mean_sv=mean, downwelling_m_per_year=mean * SVERDRUP / area * 86400 * 365.25,
                     slope_sv_per_decade=fit["slope_per_decade"], ci95=fit["ci95_per_decade"],
                     percent_per_decade=fit["slope_per_decade"] / mean * 100, p_ols_ar1=fit["p_ols_ar1"],
                     p_mk=fit["p_mk"]))
summary = pd.DataFrame(rows)
summary.to_csv(DATA.parent / "garbage_patch_ekman.csv", index=False)
print(summary.to_string(index=False, float_format=lambda v: f"{v:.3g}"))

fig, axes = plt.subplots(1, 2, figsize=(13.87, 6.3), gridspec_kw=dict(width_ratios=[2, 1]))
for region, color in zip(PATCHES, [ORANGE, BLUE, AQUA, INK, INK_SECONDARY]):
    c = convergence[region]
    yearly = c.groupby(c.index.year).mean()[c.groupby(c.index.year).count() == 12]
    axes[0].plot(yearly.index, yearly.values, color=color, lw=2, label=SHORT_NAMES[region])
axes[0].set_ylabel("Ekman inflow into the box (Sv), yearly mean")
axes[0].set_title("Wind-driven surface convergence into the garbage patches")
axes[0].legend(fontsize=11, ncol=2)
style(axes[0])
for i, row in summary.iterrows():
    axes[1].barh(i, row.percent_per_decade, xerr=abs(row.ci95 / row.mean_sv * 100), height=0.7,
                 color=ORANGE if row.percent_per_decade > 0 else BLUE, alpha=1 if row.p_ols_ar1 < 0.05 else 0.35,
                 error_kw=dict(ecolor=INK_SECONDARY, lw=1))
    axes[1].text(0.98, i, p_text(row.p_ols_ar1), transform=axes[1].get_yaxis_transform(), ha="right", va="center",
                 fontsize=11, color=INK_SECONDARY)
axes[1].set_yticks(range(len(PATCHES)), [SHORT_NAMES[r] for r in PATCHES], fontsize=12)
axes[1].invert_yaxis()
axes[1].axvline(0, color=INK_SECONDARY, lw=0.8)
axes[1].set_xlabel("Trend 1980–2026 (%/decade)")
axes[1].set_title("Trend of the inflow")
axes[1].spines[["top", "right", "left"]].set_visible(False)
axes[1].tick_params(length=0)
fig.tight_layout()
save(fig, "garbage_patch/ekman_convergence.png")
