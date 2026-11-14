"""Linear trend and its significance for every series in data/giovanni/, written to data/trend_summary.csv.

Then the checks of trends that are not linear over the whole record (fits over sub-periods).
"""
import pandas as pd

from giovanni import DATA, REGIONS, VARIABLES, annual_trend, file_name, fit_trend, load_series

rows = []
for region in REGIONS:
    for variable, (label, unit, _) in VARIABLES.items():
        folder = DATA if region == "global" else DATA / region
        if not (folder / f"{file_name(variable)}.csv").exists():
            continue
        s = load_series(region, variable)
        fit = fit_trend(s)
        strongest = max(fit["monthly_slope"], key=lambda m: abs(fit["monthly_slope"][m]))
        rows.append(dict(
            region=region, variable=variable, label=label, unit=unit, first=s.index[0].strftime("%Y-%m"),
            last=s.index[-1].strftime("%Y-%m"), mean=s.mean(), slope_per_decade=fit["slope_per_decade"],
            ci95_per_decade=fit["ci95_per_decade"],
            # a relative change is meaningless on the Celsius scale
            percent_per_decade=float("nan") if unit == "°C" else fit["slope_per_decade"] / abs(s.mean()) * 100,
            p_ols_ar1=fit["p_ols_ar1"], mk_tau=fit["mk_tau"], p_mk=fit["p_mk"], sen_per_decade=fit["sen_per_decade"],
            strongest_month=strongest, strongest_month_slope=fit["monthly_slope"][strongest],
            strongest_month_p=fit["monthly_p"][strongest],
            monthly_slopes=" ".join(f"{fit['monthly_slope'][m]:+.3g}" for m in range(1, 13))))

summary = pd.DataFrame(rows)
summary.to_csv(DATA.parent / "trend_summary.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 50)
print(summary.drop(columns=["variable", "monthly_slopes"]).to_string(float_format=lambda v: f"{v:.3g}"))

print("\nSub-period trends (yearly means):")
checks = [
    ("south_pole", "M2TMNXSLV_5_12_4_TO3", [10], [(1980, 2000), (2001, 2026)]),
    ("antarctic_sea_ice", "M2TMNXOCN_5_12_4_FRSEAICE", None, [(1980, 2015), (2016, 2025)]),
    ("south_pole", "M2TMNXSLV_5_12_4_T2M", None, [(1980, 2000), (1989, 2018), (2000, 2025)]),
    # same period as MODIS, to compare MERRA-2 with the satellite SST
    ("orca", "M2TMNXOCN_5_12_4_TSKINWTR", None, [(2003, 2024)]),
    ("orca", "MODISA_L3m_NSST_Monthly_4km_R2019_0_sst", None, [(2003, 2024)]),
    ("arca", "M2TMNXOCN_5_12_4_TSKINWTR", None, [(2003, 2024)]),
    ("arca", "MODISA_L3m_NSST_Monthly_4km_R2019_0_sst", None, [(2003, 2024)]),
]
for region, variable, months, periods in checks:
    label, unit, _ = VARIABLES[variable]
    s = load_series(region, variable)
    for first, last in periods:
        t = annual_trend(s, first, last, months)
        print(f"  {region:18} {label:45} months={months}  {first}-{last}: {t['slope_per_decade']:+.3g} {unit}/decade"
              f"  p_OLS={t['p_ols']:.2g}  p_MK={t['p_mk']:.2g}")
