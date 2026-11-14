"""Plots of the garbage-patch time series in data/giovanni/ (style as plot_trends.py on the neutrino-sites branch).

plots/series/<region>/<variable>.png: one overview per series (deseasonalised anomaly with linear trend,
and the trend of each calendar month).
plots/garbage_patch/*.png: the figures for the slides.
"""
import matplotlib.pyplot as plt
import pandas as pd

from giovanni import CONTROLS, DATA, PATCHES, REGIONS, VARIABLES, decimal_year, file_name, fit_trend, load_series
from plot_style import (AQUA, BLUE, GRID, INK, INK_SECONDARY, MONTHS, ORANGE, SHORT_NAMES, SLIDE_SIZE, p_text, save,
                        style, trend_text)


def plot_anomaly(ax, s, fit, color, unit, fontsize=None):
    """Monthly anomaly (thin), its 12-month running mean, and the linear trend."""
    anomaly = fit["anomaly"].reindex(pd.date_range(s.index[0], s.index[-1], freq="MS"))
    t = decimal_year(anomaly.index)
    ax.plot(t, anomaly.values, color=color, lw=0.7, alpha=0.3)
    ax.plot(t, anomaly.interpolate().rolling(12, center=True).mean().values, color=color, lw=2)
    ax.plot(t, fit["intercept"] + fit["slope_per_decade"] / 10 * t, color=INK, lw=1.5, ls="--")
    ax.text(0, 1.03, "Trend " + trend_text(fit["slope_per_decade"], unit, fit["p_ols_ar1"], fit["ci95_per_decade"]),
            transform=ax.transAxes, color=INK, fontsize=fontsize)
    ax.axhline(0, color=INK_SECONDARY, lw=0.8)
    ax.set_ylabel(f"Anomaly ({unit})" if unit else "Anomaly")
    style(ax)


def plot_monthly_slopes(ax, slopes, p_values, unit):
    """Trend of each calendar month; solid if p < 0.05, pale otherwise."""
    for month in range(1, 13):
        slope = slopes[month]
        ax.bar(month, slope, width=0.75, color=ORANGE if slope > 0 else BLUE, alpha=1.0 if p_values[month] < 0.05
               else 0.35)
    ax.axhline(0, color=INK_SECONDARY, lw=0.8)
    ax.set_xticks(range(1, 13), list(MONTHS))
    ax.set_ylabel(f"{unit}/decade" if unit else "per decade")
    style(ax)


def exists(region, variable):
    return (DATA / region / f"{file_name(variable)}.csv").exists()


# --- one overview per series ---
for region in PATCHES + CONTROLS:
    for variable, (label, unit, _) in VARIABLES.items():
        if not exists(region, variable):
            continue
        s = load_series(region, variable)
        fit = fit_trend(s)
        fig, (ax_time, ax_month) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw=dict(height_ratios=[3, 2]))
        ax_time.set_title(f"{label}: {REGIONS[region][0]}, {s.index[0]:%Y-%m} to {s.index[-1]:%Y-%m}", pad=36)
        plot_anomaly(ax_time, s, fit, BLUE, unit)
        ax_month.set_title("Trend per calendar month (pale: p ≥ 0.05)", fontsize=14, fontweight="normal")
        plot_monthly_slopes(ax_month, fit["monthly_slope"], fit["monthly_p"], unit)
        fig.text(0.01, 0.01, f"Data: {variable}, NASA Giovanni area average over {REGIONS[region][1]} (W,S,E,N). "
                 f"Mann-Kendall {p_text(fit['p_mk'])}", color=INK_SECONDARY, fontsize=11)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        save(fig, f"series/{region}/{file_name(variable)}.png")

# --- Great Pacific Garbage Patch: the broad check, one panel per variable ---
overviews = {
    "gpgp_ocean": [("M2TMNXOCN_5_12_4_TSKINWTR", "Sea-surface temperature", ORANGE),
                   ("MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a", "Chlorophyll-a", AQUA),
                   ("MODISA_L3m_FLH_Mo_4km_R2022_0_nflh", "Chl. fluorescence", AQUA),
                   ("MODISA_L3m_POC_Mo_4km_R2022_0_poc", "Organic carbon (POC)", AQUA),
                   ("M2TMNXOCN_5_12_4_RAINOCN", "Rainfall", BLUE), ("M2TMNXFLX_5_12_4_EVAP", "Evaporation", ORANGE)],
    "gpgp_plankton": [("NOBM_MON_R2017_h", "Mixed-layer depth", BLUE), ("NOBM_MON_R2017_rno", "Nitrate", BLUE),
                      ("NOBM_MON_R2017_tot", "Total chlorophyll", AQUA), ("NOBM_MON_R2017_dia", "Diatoms", AQUA),
                      ("NOBM_MON_R2017_cya", "Cyanobacteria", AQUA), ("NOBM_MON_R2017_coc", "Coccolithophores", AQUA)],
}
for name, overview in overviews.items():
    fig, axes = plt.subplots(2, 3, figsize=SLIDE_SIZE, sharex=True)
    for ax, (variable, title, color) in zip(axes.flat, overview):
        unit = VARIABLES[variable][1]
        s = load_series("gpgp", variable)
        fit = fit_trend(s)
        plot_anomaly(ax, s, fit, color, unit, fontsize=10)
        ax.set_ylabel(unit, fontsize=11)
        ax.tick_params(labelsize=11)
        if unit not in ["°C", "hPa"]:
            title += f": {fit['slope_per_decade'] / s.mean() * 100:+.1f}%/decade".replace("-", "−")
        ax.set_title(title, fontsize=13, pad=20)
    fig.tight_layout()
    save(fig, f"garbage_patch/{name}.png")

# --- Trends in all patches and the controls (the regions with data) ---
compare = [("M2TMNXOCN_5_12_4_TSKINWTR", "Sea-surface temperature"),
           ("MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a", "Chlorophyll-a"),
           ("MODISA_L3m_FLH_Mo_4km_R2022_0_nflh", "Chl. fluorescence"),
           ("MODISA_L3m_POC_Mo_4km_R2022_0_poc", "Organic carbon (POC)")]
regions = [r for r in PATCHES + CONTROLS if any(exists(r, v) for v, _ in compare)]
fig, axes = plt.subplots(1, len(compare), figsize=SLIDE_SIZE, sharey=True)
for ax, (variable, title) in zip(axes, compare):
    unit = VARIABLES[variable][1]
    relative = unit != "°C"
    for i, region in enumerate(regions):
        if not exists(region, variable):
            ax.text(0.5, i, "no data yet", transform=ax.get_yaxis_transform(), ha="center", va="center",
                    color=INK_SECONDARY, fontsize=11)
            continue
        s = load_series(region, variable)
        fit = fit_trend(s)
        scale = 100 / s.mean() if relative else 1
        slope, ci = fit["slope_per_decade"] * scale, fit["ci95_per_decade"] * scale
        ax.barh(i, slope, xerr=ci, color=ORANGE if slope > 0 else BLUE, alpha=1 if fit["p_ols_ar1"] < 0.05 else 0.35,
                error_kw=dict(ecolor=INK_SECONDARY, lw=1), height=0.6)
    ax.axvline(0, color=INK_SECONDARY, lw=0.8)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("%/decade" if relative else f"{unit}/decade", fontsize=12)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0, labelsize=12)
    ax.set_axisbelow(True)
axes[0].set_yticks(range(len(regions)), [SHORT_NAMES[r] for r in regions])
axes[0].invert_yaxis()
fig.tight_layout()
save(fig, "garbage_patch/patch_trends.png")

# --- Mean state: what makes a patch different from its surroundings ---
means = [("MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a", "Chlorophyll-a (mg/m³)"),
         ("MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490", "Light attenuation Kd490 (1/m)"),
         ("M2TMNXSLV_5_12_4_SLP", "Sea-level pressure (hPa)"), ("M2TMNXFLX_5_12_4_SPEED", "Wind speed (m/s)"),
         ("NOBM_MON_R2017_h", "Mixed-layer depth (m, model)"), ("NOBM_MON_R2017_rno", "Nitrate (µmol/L, model)")]
fig, axes = plt.subplots(2, 3, figsize=(13.87, 8.4), sharey=True)
for ax, (variable, title) in zip(axes.flat, means):
    for i, region in enumerate(regions):
        if exists(region, variable):
            ax.barh(i, load_series(region, variable).mean(), color=AQUA if region in PATCHES else INK_SECONDARY,
                    height=0.7)
    if variable == "M2TMNXSLV_5_12_4_SLP":
        ax.set_xlim(1005, 1025)
    ax.axhline(len(PATCHES) - 0.5, color=GRID, lw=1.5)
    ax.set_title(title, fontsize=13)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0, labelsize=12)
    ax.set_axisbelow(True)
axes[0, 0].set_yticks(range(len(regions)), [SHORT_NAMES[r] for r in regions])
axes[0, 0].invert_yaxis()
fig.tight_layout()
save(fig, "garbage_patch/patch_means.png")
