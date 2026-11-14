"""Global area-averaged MERRA-2 temperatures from NASA Giovanni, as a function of time."""
import matplotlib.pyplot as plt
import pandas as pd

# Variable id -> (label, colour). CSVs are Giovanni "Time Series, Area-Averaged" downloads.
variables = {
    "M2TMNXOCN_5_12_4_TSKINWTR": ("Open water skin temperature (ocean)", "#2a78d6"),
    "M2TMNXSLV_5_12_4_T2M": ("2-meter air temperature", "#eb6834"),
}

fig, ax = plt.subplots(figsize=(11, 5.5), facecolor="#fcfcfb")
ax.set_facecolor("#fcfcfb")
for variable, (label, color) in variables.items():
    # 7 metadata lines and a blank line precede the "time, value" header
    df = pd.read_csv(f"data/giovanni/{variable}.csv", skiprows=8, names=["time", "T"], header=0, parse_dates=["time"])
    T_celsius = df["T"] - 273.15
    # 1980-05 and 1980-11 of TSKINWTR are ~10 K below their neighbours in the Giovanni output: not physical, masked
    T_celsius = T_celsius.mask((T_celsius.diff().abs() > 5) & (T_celsius.diff(-1).abs() > 5))
    running_mean = T_celsius.interpolate().rolling(12, center=True).mean()
    ax.plot(df["time"], T_celsius, color=color, lw=0.8, alpha=0.35)
    ax.plot(df["time"], running_mean, color=color, lw=2, label=label)
    last = running_mean.last_valid_index()
    ax.annotate(f"{running_mean[last]:.1f} °C", (df["time"][last], running_mean[last]),
                xytext=(6, 0), textcoords="offset points", va="center", color="#52514e")

ax.set_title("Global mean ocean surface and near-surface air temperature, 1980–2026",
             loc="left", color="#0b0b0b", fontweight="bold", pad=42)
ax.set_ylabel("Temperature (°C)", color="#52514e")
ax.grid(axis="y", color="#e4e3df", lw=0.8)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(colors="#52514e", length=0)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1), ncol=2, borderaxespad=0.3,
          title="Bold: 12-month running mean, thin: monthly", alignment="left")
fig.text(0.01, 0.01, "Data: MERRA-2 monthly (M2TMNXOCN, M2TMNXSLV v5.12.4), area-averaged over 180°W–180°E, 90°S–90°N, via NASA Giovanni",
         color="#52514e", fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig("temperature_time_series.png", dpi=150)
