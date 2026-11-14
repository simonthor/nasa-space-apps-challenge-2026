"""Mean, linear trend and its significance of every series of the garbage-patch and control regions in data/giovanni/,
written to data/garbage_patch_trend_summary.csv.

Then the signature of the patches: which variables are different in all patches compared to the controls, and which
trend the same way in all of them.
"""
import pandas as pd

from giovanni import CONTROLS, DATA, PATCHES, VARIABLES, file_name, fit_trend, load_series

rows = []
for region in PATCHES + CONTROLS:
    for variable, (label, unit, _) in VARIABLES.items():
        if not (DATA / region / f"{file_name(variable)}.csv").exists():
            continue
        s = load_series(region, variable)
        fit = fit_trend(s)
        strongest = max(fit["monthly_slope"], key=lambda m: abs(fit["monthly_slope"][m]))
        rows.append(dict(
            region=region, variable=variable, label=label, unit=unit, first=s.index[0].strftime("%Y-%m"),
            last=s.index[-1].strftime("%Y-%m"), mean=s.mean(), slope_per_decade=fit["slope_per_decade"],
            ci95_per_decade=fit["ci95_per_decade"],
            # a relative change is meaningless on the Celsius scale or for signed quantities (winds)
            percent_per_decade=float("nan") if unit == "°C" or s.min() < 0
            else fit["slope_per_decade"] / s.mean() * 100,
            p_ols_ar1=fit["p_ols_ar1"], mk_tau=fit["mk_tau"], p_mk=fit["p_mk"], sen_per_decade=fit["sen_per_decade"],
            strongest_month=strongest, strongest_month_slope=fit["monthly_slope"][strongest],
            strongest_month_p=fit["monthly_p"][strongest],
            monthly_slopes=" ".join(f"{fit['monthly_slope'][m]:+.3g}" for m in range(1, 13))))

summary = pd.DataFrame(rows)
summary.to_csv(DATA.parent / "garbage_patch_trend_summary.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 52, "display.max_rows", 500)
print("Great Pacific Garbage Patch:")
print(summary[summary.region == "gpgp"].drop(columns=["region", "variable", "monthly_slopes", "first"])
      .to_string(index=False, float_format=lambda v: f"{v:.3g}"))

print("\nMean and trend in each region (* p < 0.05 with the AR(1)-corrected OLS test):")
summary["trend"] = [f"{slope:+.3g}{'*' if p < 0.05 else ' '}" for slope, p in
                    zip(summary.slope_per_decade, summary.p_ols_ar1)]
for column in ["mean", "trend"]:
    table = summary.pivot(index="label", columns="region", values=column)[
        [r for r in PATCHES + CONTROLS if r in summary.region.unique()]]
    print(f"\n{column}:")
    print(table.to_string(float_format=lambda v: f"{v:.3g}"))
