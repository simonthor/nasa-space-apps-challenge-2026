"""Plots of the trends in data/giovanni/.

plots/series/<region>/<variable>.png: one overview per series (deseasonalised anomaly with linear trend,
and the trend of each calendar month).
plots/*.png: the figures for the slides.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from giovanni import DATA, REGIONS, VARIABLES, annual_trend, decimal_year, file_name, fit_trend, load_series

PLOTS = Path(__file__).parent / "plots"
BACKGROUND, INK, INK_SECONDARY, GRID = "#f7f6f2", "#1d1c1a", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MONTHS = "JFMAMJJASOND"
plt.rcParams.update({
    "font.size": 15, "axes.titlesize": 16, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlecolor": INK, "axes.labelcolor": INK_SECONDARY, "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY, "axes.edgecolor": INK_SECONDARY, "figure.facecolor": BACKGROUND,
    "axes.facecolor": BACKGROUND, "legend.frameon": False, "savefig.facecolor": BACKGROUND,
})
SLIDE_SIZE = (13.87, 6.3)  # inches; at 120 dpi 1664 px, the content width of a 1920 px slide


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)


def p_text(p):
    if p >= 0.001:
        return f"p = {p:.2g}"
    mantissa, exponent = f"{p:.0e}".split("e")
    return rf"p = ${mantissa}\times10^{{{int(exponent)}}}$"


def trend_text(slope, unit, p, ci=None):
    ci_text = f" ± {ci:.2g}" if ci is not None else ""
    return f"{slope:+.2g}".replace("-", "−") + f"{ci_text} {unit}/decade, {p_text(p)}"


def save(fig, name):
    path = PLOTS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(path)


def plot_anomaly(ax, s, fit, color, unit):
    """Monthly anomaly (thin), its 12-month running mean, and the linear trend."""
    anomaly = fit["anomaly"].reindex(pd.date_range(s.index[0], s.index[-1], freq="MS"))
    t = decimal_year(anomaly.index)
    ax.plot(t, anomaly.values, color=color, lw=0.7, alpha=0.3)
    ax.plot(t, anomaly.interpolate().rolling(12, center=True).mean().values, color=color, lw=2)
    ax.plot(t, fit["intercept"] + fit["slope_per_decade"] / 10 * t, color=INK, lw=1.5, ls="--")
    ax.text(0, 1.03, "Trend " + trend_text(fit["slope_per_decade"], unit, fit["p_ols_ar1"], fit["ci95_per_decade"]),
            transform=ax.transAxes, color=INK)
    ax.axhline(0, color=INK_SECONDARY, lw=0.8)
    ax.set_ylabel(f"Anomaly ({unit})" if unit else "Anomaly")
    style(ax)


def plot_monthly_slopes(ax, slopes, p_values, unit, x_offset=0.0, width=0.75, color_up=ORANGE, color_down=BLUE,
                        label=None):
    """Trend of each calendar month; solid if p < 0.05, pale otherwise."""
    for month in range(1, 13):
        slope = slopes[month]
        ax.bar(month + x_offset, slope, width=width, color=color_up if slope > 0 else color_down,
               alpha=1.0 if p_values[month] < 0.05 else 0.35, label=label if month == 1 else None)
    ax.axhline(0, color=INK_SECONDARY, lw=0.8)
    ax.set_xticks(range(1, 13), list(MONTHS))
    ax.set_ylabel(f"{unit}/decade" if unit else "per decade")
    style(ax)


# --- one overview per series ---
for region in REGIONS:
    for variable, (label, unit, _) in VARIABLES.items():
        folder = DATA if region == "global" else DATA / region
        if not (folder / f"{file_name(variable)}.csv").exists():
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

# --- South Pole: surface warming, stratospheric cooling ---
fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE, sharex=True)
for ax, variable, title, color in [
    (axes[0], "M2TMNXSLV_5_12_4_T2M", "Surface (2 m air temperature)", ORANGE),
    (axes[1], "M2IMNPASM_5_12_4_T(z=50)", "Lower stratosphere (50 hPa, ~20 km)", BLUE),
]:
    s = load_series("south_pole", variable)
    plot_anomaly(ax, s, fit_trend(s), color, "°C")
    ax.set_title(title, pad=36)
global_fit = fit_trend(load_series("global", "M2TMNXSLV_5_12_4_T2M"))
axes[0].text(0.99, 0.03, "Global mean: " + trend_text(global_fit["slope_per_decade"], "°C", global_fit["p_ols_ar1"],
                                                       global_fit["ci95_per_decade"]).split(",")[0],
             transform=axes[0].transAxes, ha="right", color=INK_SECONDARY)
fig.tight_layout()
save(fig, "south_pole_temperature.png")

# --- South Pole: trends per calendar month ---
fig, axes = plt.subplots(2, 2, figsize=(13.87, 6.8), sharex=True)
for ax, variable, title in zip(axes.flat, ["M2TMNXSLV_5_12_4_T2M", "M2IMNPASM_5_12_4_T(z=50)",
                                           "M2TMNXSLV_5_12_4_PS", "M2TMNXSLV_5_12_4_TO3"],
                               ["2 m temperature", "50 hPa temperature", "Surface pressure", "Total ozone"]):
    unit = VARIABLES[variable][1]
    fit = fit_trend(load_series("south_pole", variable))
    plot_monthly_slopes(ax, fit["monthly_slope"], fit["monthly_p"], unit)
    ax.set_title(f"{title} (all months: {fit['slope_per_decade']:+.2g} {unit}/decade)".replace("-", "−"),
                 fontsize=15)
fig.tight_layout()
save(fig, "south_pole_monthly_trends.png")

# --- South Pole: October ozone, one line vs. two ---
o3 = load_series("south_pole", "M2TMNXSLV_5_12_4_TO3")
october = o3[o3.index.month == 10]
fig, ax = plt.subplots(figsize=SLIDE_SIZE)
ax.plot(october.index.year, october.values, "o", color=BLUE, ms=8, mec=BACKGROUND, mew=2)
whole = stats.linregress(october.index.year, october.values)
ax.plot([1980, 2026], whole.intercept + whole.slope * np.array([1980, 2026]), color=INK_SECONDARY, lw=1.5, ls=":")
ax.text(2026.5, whole.intercept + whole.slope * 2026,
        "One line, 1980–2026:\n" + trend_text(whole.slope * 10, "DU", whole.pvalue).replace(", ", "\n"),
        va="center", color=INK_SECONDARY)
for first, last in [(1980, 2000), (2001, 2026)]:
    t = annual_trend(o3, first, last, [10])
    years = np.array([first, last])
    ax.plot(years, t["intercept"] + t["slope_per_decade"] / 10 * years, color=ORANGE, lw=2.5)
    ax.text(first, 250, f"{first}–{last}:\n" + trend_text(t["slope_per_decade"], "DU", t["p_ols"]), color=INK)
ax.set_ylabel("October total column ozone (DU)")
ax.set_xlim(1978, 2038)
ax.set_ylim(95, 275)
style(ax)
fig.tight_layout()
save(fig, "south_pole_ozone_october.png")

# --- Antarctic sea ice: rise, then a regime change ---
ice = load_series("antarctic_sea_ice", "M2TMNXOCN_5_12_4_FRSEAICE")
ice_anomaly = (ice - ice.groupby(ice.index.month).transform("mean"))
yearly = ice_anomaly.groupby(ice_anomaly.index.year).mean()[ice.groupby(ice.index.year).count() == 12]
fig, ax = plt.subplots(figsize=SLIDE_SIZE)
ax.bar(yearly.index, yearly.values, color=[BLUE if v > 0 else ORANGE for v in yearly.values], width=0.75)
for first, last, xy_text in [(1980, 2015, (1979.6, 3.6)), (2016, 2025, (2003.6, -2.4))]:
    t = annual_trend(ice_anomaly, first, last)
    years = np.array([first, last])
    ax.plot(years, t["intercept"] + t["slope_per_decade"] / 10 * years, color=INK, lw=2, ls="--")
    ax.text(*xy_text, f"{first}–{last}: " + trend_text(t["slope_per_decade"], "%", t["p_ols"]), color=INK)
ax.axhline(0, color=INK_SECONDARY, lw=0.8)
ax.set_ylim(-2.7, 4.4)
ax.set_ylabel("Sea-ice fraction anomaly, 55–75°S (%)")
style(ax)
fig.tight_layout()
save(fig, "antarctic_sea_ice.png")

# --- South Pole: snowfall and wind (IceTop snow load) ---
fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE)
for ax, variable, color in [(axes[0], "M2TMNXFLX_5_12_4_PRECSNO", BLUE), (axes[1], "M2TMNXFLX_5_12_4_SPEED", AQUA)]:
    label, unit, _ = VARIABLES[variable]
    t = annual_trend(load_series("south_pole", variable), 1980, 2025)
    ax.plot(t["yearly"].index, t["yearly"].values, "o-", color=color, lw=1.5, ms=6, mec=BACKGROUND)
    ax.plot([1980, 2025], t["intercept"] + t["slope_per_decade"] / 10 * np.array([1980, 2025]), color=INK, lw=1.5,
            ls="--")
    ax.set_title(f"{label} ({unit})", pad=36)
    ax.text(0.01, 1.04, trend_text(t["slope_per_decade"], unit, t["p_ols"]), transform=ax.transAxes, color=INK)
    style(ax)
fig.tight_layout()
save(fig, "south_pole_snow_wind.png")

# --- Mediterranean vs. global sea-surface temperature ---
fig, ax = plt.subplots(figsize=SLIDE_SIZE)
for region, color in [("mediterranean", ORANGE), ("orca", AQUA), ("global", BLUE)]:
    s = load_series(region, "M2TMNXOCN_5_12_4_TSKINWTR")
    t = annual_trend(s - s["1981":"2010"].mean(), 1980, 2025)
    ax.plot(t["yearly"].index, t["yearly"].values, color=color, lw=2)
    ax.text(2026, t["yearly"].iloc[-1], f"{REGIONS[region][0].split(' (')[0]}\n{t['slope_per_decade']:+.2f} °C/decade",
            va="center", color=INK)
ax.axhline(0, color=INK_SECONDARY, lw=0.8)
ax.set_ylabel("Yearly mean vs. 1981–2010 (°C)")
ax.set_xlim(1979, 2034)
style(ax)
fig.tight_layout()
save(fig, "mediterranean_sst.png")

# --- Spring bloom: chlorophyll climatology, early vs. late half of the MODIS record ---
fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE, sharey=True)
for ax, region in zip(axes, ["orca", "medoc"]):
    chl = load_series(region, "MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a")
    for first, last, color in [(2003, 2013, BLUE), (2014, 2024, ORANGE)]:
        part = chl[(chl.index.year >= first) & (chl.index.year <= last)]
        climatology = part.groupby(part.index.month).mean()
        ax.plot(climatology.index, climatology.values, "o-", color=color, lw=2, ms=7, mec=BACKGROUND,
                label=f"{first}–{last}")
    ax.set_title(REGIONS[region][0])
    ax.set_xticks(range(1, 13), list(MONTHS))
    style(ax)
axes[0].set_ylabel("Mean chlorophyll-a (mg/m³)")
axes[0].legend(loc="upper right")
fig.tight_layout()
save(fig, "chlorophyll_seasonal_cycle.png")

# --- Spring bloom per year: ORCA April and Gulf of Lion February, early vs. late period ---
fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE, sharey=True)
for ax, region, month, month_name in [(axes[0], "orca", 4, "April"), (axes[1], "medoc", 2, "February")]:
    chl = load_series(region, "MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a")
    s = chl[(chl.index.month == month) & (chl.index.year >= 2003)]
    s.index = s.index.year
    for first, last, color in [(2003, 2013, BLUE), (2014, s.index[-1], ORANGE)]:
        part = s.loc[first:last]
        ax.bar(part.index, part.values, color=color, width=0.75, label=f"{first}–{last}")
        ax.plot([first - 0.4, last + 0.4], [part.median()] * 2, color=INK, lw=2)
        ax.text(last + 0.4, part.median() + 0.03, f"median {part.median():.2f}", va="bottom", ha="right", color=INK,
                fontsize=14, bbox=dict(facecolor=BACKGROUND, edgecolor="none", pad=2))
    for year in s.nlargest(2).index:
        ax.text(year, s[year], str(year), ha="center", va="bottom", color=INK_SECONDARY, fontsize=13)
    p_mk = stats.kendalltau(s.index, s.values)[1]
    ax.set_title(f"{REGIONS[region][0].split(' (')[0]}: {month_name}", pad=36)
    ax.text(0, 1.03, f"Mann-Kendall {p_text(p_mk)}; Theil-Sen "
            + f"{stats.theilslopes(s.values, s.index)[0] * 10:+.2f}".replace("-", "−") + " mg/m³/decade",
            transform=ax.transAxes, color=INK, fontsize=14)
    style(ax)
axes[0].set_ylabel("Chlorophyll-a (mg/m³)")
axes[0].legend(loc="upper right")
fig.tight_layout()
save(fig, "chlorophyll_bloom_per_year.png")

# --- Spring bloom: every year's seasonal cycle overlaid, with the median of each period ---
fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE, sharey=True)
for ax, region in zip(axes, ["orca", "medoc"]):
    chl = load_series(region, "MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a")
    chl = chl[chl.index.year >= 2003]
    by_year = pd.DataFrame({"year": chl.index.year, "month": chl.index.month, "chl": chl.values}).pivot(
        index="month", columns="year", values="chl")
    for first, last, color in [(2003, 2013, BLUE), (2014, by_year.columns[-1], ORANGE)]:
        part = by_year.loc[:, first:last]
        ax.plot(part.index, part.values, color=color, lw=1, alpha=0.4)
        ax.plot(part.index, part.median(axis=1), color=color, lw=3.5, label=f"{first}–{last} median")
    for year in [2006, 2013, 2021]:
        peak_month = by_year[year].idxmax()
        if by_year[year].max() > 1.25:
            ax.text(peak_month + 0.15, by_year[year].max(), str(year), color=INK_SECONDARY, fontsize=13, va="center")
    ax.set_title(REGIONS[region][0])
    ax.set_xticks(range(1, 13), list(MONTHS))
    style(ax)
axes[0].set_ylabel("Chlorophyll-a (mg/m³)")
axes[0].legend(loc="upper right")
fig.tight_layout()
save(fig, "chlorophyll_seasonal_cycle_all_years.png")

# --- Aerosols at the KM3NeT sites: significant 1980-2025 trends that are not trends ---
def plot_two_period_fits(ax, s, y_texts):
    """Yearly means with the 1980-2025 and 1995-2025 linear fits, labelled in %/decade of the period mean."""
    for (first, last, ls), y_text in zip([(1980, 2025, "--"), (1995, 2025, "-")], y_texts):
        t = annual_trend(s, first, last)
        years = np.array([first, last])
        ax.plot(years, t["intercept"] + t["slope_per_decade"] / 10 * years, color=INK, lw=1.8, ls=ls)
        relative = t["slope_per_decade"] / s[str(first):str(last)].mean() * 100
        ax.text(1995 if first == 1995 else 1980, y_text, f"{first}–{last}: " + trend_text(relative, "%", t["p_ols"]),
                color=INK, fontsize=14)


fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE)
aod = load_series("orca", "M2TMNXAER_5_12_4_TOTEXTTAU")
axes[0].plot(aod.groupby(aod.index.year).mean().loc[:2025], color=BLUE, lw=2)
for year, name, y_text in [(1982, "El Chichón eruption", 0.333), (1991, "Pinatubo eruption", 0.315)]:
    axes[0].axvline(year + 0.3, color=INK_SECONDARY, lw=1, ls=":")
    axes[0].text(year + 0.8, y_text, name, color=INK_SECONDARY, fontsize=14)
plot_two_period_fits(axes[0], aod, [0.115, 0.10])
axes[0].set_title("ORCA: aerosol optical depth (all aerosols)", pad=12)
axes[0].set_ylim(0.09, 0.345)
dust = load_series("arca", "M2TMNXADG_5_12_4_DUDP003")
axes[1].plot(dust.groupby(dust.index.year).mean().loc[:2025], color=ORANGE, lw=2)
plot_two_period_fits(axes[1], dust, [100, 85])
axes[1].set_title("ARCA: dust dry deposition (mg/m²/yr, bin 3)", pad=12)
axes[1].set_ylim(75, 270)
for ax in axes:
    style(ax)
fig.tight_layout()
save(fig, "km3net_aerosols.png")

# --- Satellite vs. reanalysis SST: trend per calendar month over the same years ---
fig, axes = plt.subplots(1, 2, figsize=SLIDE_SIZE, sharey=True)
for ax, region in zip(axes, ["orca", "arca"]):
    for variable, offset, color, name in [("M2TMNXOCN_5_12_4_TSKINWTR", -0.2, BLUE, "MERRA-2 reanalysis"),
                                          ("MODISA_L3m_NSST_Monthly_4km_R2019_0_sst", 0.2, ORANGE,
                                           "MODIS-Aqua satellite (night)")]:
        s = load_series(region, variable)
        s = s[(s.index.year >= 2003) & (s.index.year <= 2024)]
        fits = {m: stats.linregress(g.index.year, g.values) for m, g in s.groupby(s.index.month)}
        plot_monthly_slopes(ax, {m: f.slope * 10 for m, f in fits.items()}, {m: f.pvalue for m, f in fits.items()},
                            "°C", x_offset=offset, width=0.4, color_up=color, color_down=color, label=name)
    ax.set_title(f"{region.upper()}, 2003–2024")
axes[0].legend(loc="upper left", fontsize=13)
fig.tight_layout()
save(fig, "sst_monthly_trends_satellite_vs_reanalysis.png")
