"""Plots of the garbage-patch time series in data/giovanni/ (style as plot_trends.py on the neutrino-sites branch).

plots/series/<region>/<variable>.png: one overview per series (monthly values with linear trend, and the trend of
each calendar month).
plots/garbage_patch/*.png: the figures for the slides, among them the patch compared with the Pacific and global
means (gpgp_vs_pacific_global.png).
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch

from giovanni import (
    CONTROLS,
    DATA,
    OCEANS,
    PATCH_CONTROLS,
    PATCHES,
    REGIONS,
    VARIABLES,
    decimal_year,
    file_name,
    fit_trend,
    load_ocean_series,
    load_series,
)
from plot_style import (
    AQUA,
    BLUE,
    GRID,
    INK,
    INK_SECONDARY,
    MONTHS,
    ORANGE,
    PURPLE,
    SHORT_NAMES,
    SLIDE_SIZE,
    p_text,
    save,
    style,
    trend_text,
)


def plot_series(ax, s, fit, color, unit, fontsize=None):
    """Monthly values (thin), their 12-month running mean, and the linear trend (fitted to the deseasonalised
    anomaly, drawn at the level of the mean)."""
    s = s.reindex(pd.date_range(s.index[0], s.index[-1], freq="MS"))
    t = decimal_year(s.index)
    ax.plot(t, s.values, color=color, lw=0.7, alpha=0.3)
    ax.plot(t, s.interpolate().rolling(12, center=True).mean().values, color=color, lw=2)
    ax.plot(t, s.mean() + fit["intercept"] + fit["slope_per_decade"] / 10 * t, color=INK, lw=1.5, ls="--")
    ax.text(0, 1.03, "Trend " + trend_text(fit["slope_per_decade"], unit, fit["p_ols_ar1"], fit["ci95_per_decade"]),
            transform=ax.transAxes, color=INK, fontsize=fontsize)
    ax.set_ylabel(unit)
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
        plot_series(ax_time, s, fit, BLUE, unit)
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
        plot_series(ax, s, fit, color, unit, fontsize=10)
        ax.set_ylabel(unit, fontsize=11)
        ax.tick_params(labelsize=11)
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
    for i, region in enumerate(regions):
        if not exists(region, variable):
            ax.text(0.5, i, "no data yet", transform=ax.get_yaxis_transform(), ha="center", va="center",
                    color=INK_SECONDARY, fontsize=11)
            continue
        s = load_series(region, variable)
        fit = fit_trend(s)
        slope, ci = fit["slope_per_decade"], fit["ci95_per_decade"]
        ax.barh(i, slope, xerr=ci, color=ORANGE if slope > 0 else BLUE, alpha=1 if fit["p_ols_ar1"] < 0.05 else 0.35,
                error_kw=dict(ecolor=INK_SECONDARY, lw=1), height=0.6)
    ax.axvline(0, color=INK_SECONDARY, lw=0.8)
    ax.set_title(title, fontsize=13)
    ax.set_xlabel(f"{unit}/decade", fontsize=12)
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

# --- Each patch compared with its controls, its ocean and the global ocean; the other patches also with the GPGP ---
COMPARED = [("M2TMNXOCN_5_12_4_TSKINWTR", "Sea-surface temperature"),
            ("MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a", "Chlorophyll-a"),
            ("MODISA_L3m_FLH_Mo_4km_R2022_0_nflh", "Chl. fluorescence"),
            ("MODISA_L3m_POC_Mo_4km_R2022_0_poc", "Organic carbon (POC)"),
            ("MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490", "Light attenuation (Kd490)"),
            ("M2TMNXFLX_5_12_4_SPEED", "Wind speed")]
OCEAN_NAMES = {"pacific": "Pacific", "atlantic": "Atlantic", "indian": "Indian Ocean"}


def load_region(region):
    """Loader of the series of a region (giovanni.py REGIONS, or an ocean of OCEANS); it returns None if the series
    is not downloaded."""
    if region in OCEANS:
        return lambda v: load_ocean_series(region, v) if all(exists(box, v) for box in OCEANS[region]) else None
    return lambda v: load_series(region, v) if exists(region, v) else None


def latitudes(region):
    s, n = (float(x) for x in REGIONS[region][1].split(",")[1::2])
    return f"{s:g}–{n:g}°N" if s >= 0 else f"{-n:g}–{-s:g}°S"


for patch in PATCHES:
    north, south, ocean = PATCH_CONTROLS[patch]
    # short name for the trends, legend label, colour, line style, opacity, line width, loader: the patch stands
    # out, the controls are slightly and the ocean means strongly faded
    lines = [("patch", f"{SHORT_NAMES[patch]} patch", ORANGE, "-", 1, 3.2, load_region(patch)),
             ("N", f"Control north ({latitudes(north)})", BLUE, "-", 0.75, 2, load_region(north)),
             ("S", f"Control south ({latitudes(south)})", AQUA, "-", 0.75, 2, load_region(south)),
             (OCEAN_NAMES[ocean], f"{OCEAN_NAMES[ocean]} mean", PURPLE, "-", 0.45, 1.5, load_region(ocean)),
             ("global", "Global ocean mean", INK_SECONDARY, "-", 0.45, 1.5, load_region("global"))]
    if patch != "gpgp":
        lines.append(("GPGP", "Great Pacific patch", INK, "--", 0.8, 1.5, load_region("gpgp")))
    # absolute values, and relative to the first complete year (°C for temperature, % otherwise) to compare the rates
    for relative in (False, True):
        fig, axes = plt.subplots(2, 3, figsize=SLIDE_SIZE, sharex=True)
        for ax, (variable, title) in zip(axes.flat, COMPARED):
            unit = VARIABLES[variable][1]
            trends = []
            for short_name, _, color, line_style, alpha, width, load in lines:
                s = load(variable)
                if s is None:
                    continue
                fit = fit_trend(s)
                yearly = s.groupby(s.index.year).mean()[s.groupby(s.index.year).count() == 12]
                if relative:
                    yearly = yearly - yearly.iloc[0] if unit == "°C" else (yearly / yearly.iloc[0] - 1) * 100
                ax.plot(yearly.index + 0.5, yearly.values, color=color, ls=line_style, alpha=alpha, lw=width,
                        marker="o" if line_style == "-" else None, ms=2.5)
                trend = (f"{fit['slope_per_decade']:+.2f}" if unit == "°C"
                         else f"{fit['slope_per_decade'] / s.mean() * 100:+.1f}").replace("-", "−")
                trends.append(f"{short_name} {trend}{'*' if fit['p_ols_ar1'] < 0.05 else ''}")
            ax.set_title(title, fontsize=13, pad=30)
            ax.text(0, 1.02, f"{'°C' if unit == '°C' else '%'}/decade: " + ", ".join(trends[:3]) + "\n"
                    + ", ".join(trends[3:]), transform=ax.transAxes, fontsize=9.5, color=INK)
            if relative:
                ax.axhline(0, color=INK_SECONDARY, lw=0.8)
                ax.set_ylabel(f"{'°C' if unit == '°C' else '%'} since {yearly.index[0]}", fontsize=11)
            else:
                ax.set_ylabel(unit, fontsize=11)
            ax.tick_params(labelsize=10)
            style(ax)
        fig.legend(handles=[plt.Line2D([], [], color=c, ls=ls, alpha=a, lw=w, marker="o" if ls == "-" else None,
                                       ms=3, label=label) for _, label, c, ls, a, w, _ in lines],
                   loc="upper center", ncol=3, fontsize=11)
        shown = ("change of the yearly mean since the first complete year" if relative
                 else "yearly means of complete years")
        fig.text(0.01, 0.005, f"Lines: {shown}. Trends: linear trend of the monthly series (* p < 0.05, "
                 "autocorrelation-corrected), in % of the mean except for temperature.", color=INK_SECONDARY,
                 fontsize=10)
        fig.tight_layout(rect=(0, 0.03, 1, 0.89))
        save(fig, f"garbage_patch/{patch}_vs_controls{'_relative' if relative else ''}.png")
    if patch != "gpgp":
        continue
    # Ratio plot (saved for inspection, not used on the slides): the change since the first complete year as on the
    # relative figure, and below it the patch divided by each other region, 1 in the first complete year (for
    # temperature the difference, 0 in the first year). A falling ratio means the patch declines faster, as tested by
    # the log ratio of the difference table.
    fig = plt.figure(figsize=(13.87, 9))
    grid = fig.add_gridspec(5, 3, height_ratios=[3, 1.5, 0.7, 3, 1.5], hspace=0.12, wspace=0.28, left=0.06,
                            right=0.99, top=0.88, bottom=0.06)  # row 2: space between the two rows of variables
    for k, (variable, title) in enumerate(COMPARED):
        ax = fig.add_subplot(grid[3 * (k // 3), k % 3])
        ax_ratio = fig.add_subplot(grid[3 * (k // 3) + 1, k % 3], sharex=ax)
        unit = VARIABLES[variable][1]
        yearly = {}
        for short_name, _, color, _, alpha, width, load in lines:
            s = load(variable)
            if s is None:
                continue
            yearly[short_name] = s.groupby(s.index.year).mean()[s.groupby(s.index.year).count() == 12]
            y = yearly[short_name]
            change = y - y.iloc[0] if unit == "°C" else (y / y.iloc[0] - 1) * 100
            ax.plot(y.index + 0.5, change.values, color=color, alpha=alpha, lw=width, marker="o", ms=2.5)
            if short_name == "patch":
                continue
            common = yearly["patch"].index.intersection(y.index)
            ratio = yearly["patch"][common] - y[common] if unit == "°C" else yearly["patch"][common] / y[common]
            ratio = ratio - ratio.iloc[0] if unit == "°C" else ratio / ratio.iloc[0]
            ax_ratio.plot(common + 0.5, ratio.values, color=color, alpha=alpha, lw=width, marker="o", ms=2.5)
        ax.axhline(0, color=INK_SECONDARY, lw=0.8)
        ax_ratio.axhline(0 if unit == "°C" else 1, color=INK_SECONDARY, lw=0.8)
        ax.set_title(title, fontsize=13)
        ax.set_ylabel(f"{'°C' if unit == '°C' else '%'} since {min(y.index[0] for y in yearly.values())}",
                      fontsize=11)
        ax_ratio.set_ylabel("patch − region\n(°C)" if unit == "°C" else "patch /\nregion", fontsize=10)
        ax.tick_params(labelbottom=False, labelsize=10)
        ax_ratio.tick_params(labelsize=10)
        style(ax)
        style(ax_ratio)
    fig.legend(handles=[plt.Line2D([], [], color=c, alpha=a, lw=w, marker="o", ms=3, label=label)
                        for _, label, c, _, a, w, _ in lines], loc="upper center", ncol=3, fontsize=11)
    fig.text(0.01, 0.005, "Upper panels: change of the yearly mean since the first complete year. Lower panels: "
             "patch divided by each region, normalised to 1 in the first year (temperature: difference, 0 in the "
             "first year).", color=INK_SECONDARY, fontsize=10)
    save(fig, f"garbage_patch/{patch}_vs_controls_ratio.png")

# --- Which trends are significant: every region, and each patch minus its controls and its ocean ---
TABLE_VARIABLES = [  # variable, column heading, unit of the trend ("%": per cent of the mean)
    ("M2TMNXOCN_5_12_4_TSKINWTR", "Sea-surface\ntemperature\n1980–2026", "°C"),
    ("MODISA_L3m_NSST_Monthly_9km_R2019_0_sst", "Sea-surface\ntemp., night\n2002–2026", "°C"),
    ("MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a", "Chloro-\nphyll-a\n2002–2025", "%"),
    ("MODISA_L3m_FLH_Mo_4km_R2022_0_nflh", "Fluores-\ncence\n2002–2025", "%"),
    ("MODISA_L3m_POC_Mo_4km_R2022_0_poc", "Organic\ncarbon\n2002–2025", "%"),
    ("MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490", "Light\nattenuation\n2002–2025", "%"),
    ("M2TMNXFLX_5_12_4_SPEED", "Wind\nspeed\n1980–2026", "%"),
    ("M2TMNXSLV_5_12_4_SLP", "Sea-level\npressure\n1980–2026", "hPa"),
    ("M2TMNXAER_5_12_4_TOTEXTTAU", "Aerosol\noptical depth\n1980–2026", "%"),
    ("NOBM_MON_R2017_h", "Mixed-layer\ndepth (model)\n1998–2015", "%"),
    ("NOBM_MON_R2017_tot", "Chlorophyll\n(model)\n1998–2015", "%"),
]


def significance_table(rows, name):
    """Trend per decade of each row (label, loader of the series, whether it is a difference series of
    difference(), whether the label is bold) and variable of TABLE_VARIABLES: orange rising, blue falling; strong
    colour p < 0.01, pale p < 0.05, none if not significant (p ≥ 0.05, autocorrelation-corrected). A row None is a gap
    between groups."""
    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fontsize = 12 if len(rows) <= 10 else 9.5
    for i, row in enumerate(rows):
        if row is None:
            continue
        _, load, is_difference, _ = row
        for j, (variable, _, unit) in enumerate(TABLE_VARIABLES):
            s = load(variable)
            if s is None:
                ax.text(j, i, "–", ha="center", va="center", color=GRID, fontsize=fontsize)
                continue
            fit = fit_trend(s.dropna())
            slope, p = fit["slope_per_decade"], fit["p_ols_ar1"]
            # in %: relative to the mean, or for the log ratio of difference() the difference of the relative
            # trends (d ln x = dx / x)
            value = slope if unit != "%" else slope * 100 if is_difference else slope / s.mean() * 100
            alpha = 1 if p < 0.01 else 0.4 if p < 0.05 else 0
            ax.add_patch(plt.Rectangle((j - 0.48, i - 0.45), 0.96, 0.9, color=ORANGE if slope > 0 else BLUE,
                                       alpha=alpha, lw=0))
            text = f"{value:+.2f}" if unit != "%" else f"{value:+.1f}" if abs(value) < 10 else f"{value:+.0f}"
            stars = "**" if p < 0.01 else "*" if p < 0.05 else ""
            ax.text(j, i, text.replace("-", "−") + stars, ha="center", va="center", fontsize=fontsize,
                    color="white" if alpha == 1 else INK, fontweight="bold" if alpha else "normal")
    ax.set_xlim(-0.5, len(TABLE_VARIABLES) - 0.5)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_xticks(range(len(TABLE_VARIABLES)), [f"{heading}\n{unit}/decade" for _, heading, unit in TABLE_VARIABLES],
                  fontsize=10 if len(rows) <= 10 else 9)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(rows)), [row[0] if row else "" for row in rows], fontsize=fontsize + 1)
    for label, row in zip(ax.get_yticklabels(), rows):
        label.set_fontweight("bold" if row and row[3] else "normal")
    ax.tick_params(length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    fig.tight_layout()
    save(fig, f"garbage_patch/{name}.png")


rows = []
for patch in PATCHES:
    north, south, _ = PATCH_CONTROLS[patch]
    rows += [(SHORT_NAMES[patch], load_region(patch), False, True),
             (f"control {latitudes(north)}", load_region(north), False, False),
             (f"control {latitudes(south)}", load_region(south), False, False), None]
rows += [(f"{OCEAN_NAMES[ocean]} mean", load_region(ocean), False, True) for ocean in OCEANS]
rows += [("Global ocean mean", load_region("global"), False, True)]
significance_table(rows, "significance_regions")


def difference(load_patch, load_other):
    """Loader of a patch series minus another region's, for the variables in % of the log ratio ln(patch / other):
    the trend of the difference series tests whether the two (relative) trends differ. The log ratio keeps a control
    with a much larger mean from dominating the difference."""
    units = {variable: unit for variable, _, unit in TABLE_VARIABLES}

    def load(variable):
        patch_series, other = load_patch(variable), load_other(variable)
        if patch_series is None or other is None:
            return None
        return np.log(patch_series) - np.log(other) if units[variable] == "%" else patch_series - other
    return load


rows = []
for patch in PATCHES:
    north, south, ocean = PATCH_CONTROLS[patch]
    rows += [(f"{SHORT_NAMES[patch]} − {what}", difference(load_region(patch), load_region(other)),
              True, False)
             for what, other in [("control north", north), ("control south", south),
                                 (f"{OCEAN_NAMES[ocean]} mean", ocean)]] + [None]
significance_table(rows[:-1], "significance_differences")

# --- The method on real data: Great Pacific chlorophyll from the raw series to the comparison with the Pacific ---
CHLOROPHYLL = "MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a"
patch = load_series("gpgp", CHLOROPHYLL)
fit = fit_trend(patch)
# as in the difference table: the log ratio, whose slope × 100 is the difference of the relative trends
compared = fit_trend((np.log(patch) - np.log(load_ocean_series("pacific", CHLOROPHYLL))).dropna())
steps = [
    ("1 · Fetch", "Monthly area mean from\nNASA Giovanni (MODIS-Aqua)"),
    ("2 · Deseasonalise", "Anomaly: the series minus\nits mean calendar month"),
    ("3 · Fit and test", "Least-squares slope, p corrected\nfor autocorrelated months"),
    ("4 · Compare", "Steps 1–3 on ln(patch / Pacific\nmean): do the trends differ?"),
]
arrows = ["− mean of\neach month", "least\nsquares", "patch vs\nPacific"]
fig = plt.figure(figsize=SLIDE_SIZE)
width, gap, left = 0.19, 0.063, 0.045
axes = [fig.add_axes((left + k * (width + gap), 0.27, width, 0.47)) for k in range(4)]
axes[2].sharey(axes[1])  # the anomalies on one scale, without tick labels: the arrows need the space
for ax, (heading, text) in zip(axes, steps):
    x = ax.get_position().x0
    fig.text(x, 0.93, heading, fontsize=15, fontweight="bold", color=ORANGE, va="top")
    fig.text(x, 0.87, text, fontsize=11.5, color=INK, va="top", linespacing=1.3)
for k, label in enumerate(arrows):
    x0, x1 = axes[k].get_position().x1 + 0.006, axes[k + 1].get_position().x0 - 0.012
    fig.patches.append(FancyArrowPatch((x0, 0.5), (x1, 0.5), transform=fig.transFigure, arrowstyle="-|>",
                                       mutation_scale=22, lw=2.5, color=INK_SECONDARY))
    fig.text((x0 + x1) / 2, 0.53, label, ha="center", va="bottom", fontsize=10, color=INK_SECONDARY)

t = decimal_year(patch.index)
climatology = patch.groupby(patch.index.month).transform("mean")
axes[0].plot(t, patch.values, color=AQUA, lw=1.2, label="monthly mean")
axes[0].plot(t, climatology.values, color=INK_SECONDARY, lw=0.8, ls="--", label="mean calendar month")
axes[0].legend(fontsize=9.5, loc="lower left", bbox_to_anchor=(0, 0.98), ncol=2, handlelength=1.5,
               columnspacing=1)
axes[0].set_ylabel("mg/m³", fontsize=11)

anomaly = fit["anomaly"]
axes[1].plot(t, anomaly.values, color=AQUA, lw=1)


def plot_fit(ax, anomaly_, fit_):
    """Anomaly, its least-squares line and the 95 % band of the slope (pivoting at the mean time)."""
    t_ = decimal_year(anomaly_.index).to_numpy()
    line = fit_["intercept"] + fit_["slope_per_decade"] / 10 * t_
    spread = fit_["ci95_per_decade"] / 10 * (t_ - t_.mean())
    ax.plot(t_, anomaly_.values, color=AQUA, lw=0.8, alpha=0.5)
    ax.fill_between(t_, line - spread, line + spread, color=ORANGE, alpha=0.25, lw=0)
    ax.plot(t_, line, color=ORANGE, lw=2.5)


plot_fit(axes[2], anomaly, fit)
plot_fit(axes[3], compared["anomaly"], compared)
for ax, f, trend in [(axes[2], fit, f"{fit['slope_per_decade']:+.4f} ± {fit['ci95_per_decade']:.4f} mg/m³/decade"),
                     (axes[3], compared, f"{compared['slope_per_decade'] * 100:+.1f} ± "
                                         f"{compared['ci95_per_decade'] * 100:.1f} % per decade")]:
    x = ax.get_position().x0
    fig.text(x, 0.16, trend.replace("-", "−"), fontsize=11, color=INK, va="top")
    fig.text(x, 0.105, f"Autocorrelation {f['r1']:.2f}: {f['n_eff']:.0f} of {len(f['anomaly'])}\n"
             f"months independent; {p_text(f['p_ols_ar1'])}", fontsize=11, color=INK, va="top")
fig.text(axes[0].get_position().x0, 0.16, f"{len(patch)} months, {patch.index[0]:%Y-%m} to {patch.index[-1]:%Y-%m}",
         fontsize=11, color=INK, va="top")
fig.text(axes[1].get_position().x0, 0.16, "Seasonal cycle removed. Steps 2–3\non one scale, grid every 0.025 "
         "mg/m³", fontsize=11, color=INK, va="top")
for ax in axes:
    ax.tick_params(labelsize=10, labelleft=ax is axes[0])
    ax.set_xticks([2005, 2015, 2025])
    style(ax)
save(fig, "garbage_patch/method_pipeline.png")

# --- Backup: the datasets of the significance tables, with their source, grid, unit and period ---
DATASETS = {  # variable: source, grid (as in the Giovanni series titles)
    "M2TMNXOCN_5_12_4_TSKINWTR": ("MERRA-2 reanalysis, ocean surface", "0.5° × 0.625°"),
    "MODISA_L3m_NSST_Monthly_9km_R2019_0_sst": ("MODIS-Aqua, 11 µm at night (R2019.0)", "9 km"),
    "MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a": ("MODIS-Aqua ocean colour (R2022.0)", "4 km"),
    "MODISA_L3m_FLH_Mo_4km_R2022_0_nflh": ("MODIS-Aqua ocean colour (R2022.0)", "4 km"),
    "MODISA_L3m_POC_Mo_4km_R2022_0_poc": ("MODIS-Aqua ocean colour (R2022.0)", "4 km"),
    "MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490": ("MODIS-Aqua ocean colour (R2022.0)", "4 km"),
    "M2TMNXFLX_5_12_4_SPEED": ("MERRA-2 reanalysis, surface fluxes", "0.5° × 0.625°"),
    "M2TMNXSLV_5_12_4_SLP": ("MERRA-2 reanalysis, single level", "0.5° × 0.625°"),
    "M2TMNXAER_5_12_4_TOTEXTTAU": ("MERRA-2 reanalysis, aerosols", "0.5° × 0.625°"),
    "NOBM_MON_R2017_h": ("NOBM ocean model (R2017)", "0.67° × 1.25°"),
    "NOBM_MON_R2017_tot": ("NOBM ocean model (R2017)", "0.67° × 1.25°"),
}
fig, (ax_text, ax_time) = plt.subplots(1, 2, figsize=SLIDE_SIZE, sharey=True, gridspec_kw={"width_ratios": [1.5, 1]})
columns = [(0, "Variable"), (0.34, "Source"), (0.83, "Grid"), (1.0, "Unit")]
for x, heading in columns:
    ax_text.text(x, -1, heading, fontsize=12, fontweight="bold", color=INK, va="center")
for i, (variable, heading, _) in enumerate(TABLE_VARIABLES):
    s = load_series("gpgp", variable)
    source, grid = DATASETS[variable]
    unit = VARIABLES[variable][1] or "–"
    for (x, _), text in zip(columns, [heading.split("\n")[:-1], source, grid, unit]):
        ax_text.text(x, i, " ".join(text).replace("- ", "") if isinstance(text, list) else text, fontsize=11,
                     color=INK, va="center")
    color = ORANGE if "MERRA" in source else AQUA if "MODIS" in source else PURPLE
    ax_time.barh(i, decimal_year(s.index[[-1]])[0] - decimal_year(s.index[[0]])[0],
                 left=decimal_year(s.index[[0]])[0], color=color, height=0.55)
    ax_time.text(decimal_year(s.index[[0]])[0] - 0.5, i, f"{s.index[0]:%Y}", ha="right", va="center", fontsize=10,
                 color=INK_SECONDARY)
    ax_time.text(decimal_year(s.index[[-1]])[0] + 0.5, i, f"{s.index[-1]:%Y}", ha="left", va="center", fontsize=10,
                 color=INK_SECONDARY)
ax_text.set_xlim(0, 1.16)
ax_text.set_ylim(len(TABLE_VARIABLES) - 0.5, -1.6)
ax_text.axis("off")
ax_time.set_xlim(1974, 2032)
ax_time.set_xticks(range(1980, 2031, 10))
ax_time.text(1974, -1, "Monthly series", fontsize=12, fontweight="bold", color=INK, va="center")
ax_time.grid(axis="x", color=GRID, lw=0.8)
ax_time.set_axisbelow(True)
ax_time.tick_params(length=0, left=False, labelsize=11)
ax_time.spines[["top", "right", "left"]].set_visible(False)
fig.tight_layout()
save(fig, "garbage_patch/datasets.png")
