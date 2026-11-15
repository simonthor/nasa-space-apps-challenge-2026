"""Loading and linear-trend fitting of the Giovanni "Time Series, Area-Averaged" CSVs in data/giovanni/.

Files are data/giovanni/<region>/<variable>.csv (fetched by fetch_all.sh and fetch_garbage_patch.sh).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA = Path(__file__).parent / "data" / "giovanni"

# Region -> (label, bounding box W,S,E,N as passed to Giovanni)
REGIONS = {
    "global": ("Global", "-180,-90,180,90"),
    "south_pole": ("South Pole (IceCube)", "-180,-90,180,-89"),
    "antarctic_sea_ice": ("Antarctic sea-ice zone", "-180,-75,180,-55"),
    "mediterranean": ("Mediterranean Sea", "-5,30,36,46"),
    "orca": ("KM3NeT/ORCA site (off Toulon)", "5.6,42.4,6.4,42.95"),
    "arca": ("KM3NeT/ARCA site (off Capo Passero)", "15.6,35.8,16.6,36.7"),
    "medoc": ("Gulf of Lion deep-convection area", "4,41.5,6,42.5"),
    # Garbage patches: the Great Pacific Garbage Patch (box as on Wikipedia), and the centres of the other subtropical
    # gyres where floating debris accumulates (Maximenko et al. 2012, Mar. Pollut. Bull. 65, 51; Law et al. 2010,
    # Science 329, 1185; Eriksen et al. 2013, Mar. Pollut. Bull. 68, 71)
    "gpgp": ("Great Pacific Garbage Patch", "-155,35,-135,42"),
    "north_atlantic_patch": ("North Atlantic garbage patch", "-70,25,-40,35"),
    "south_pacific_patch": ("South Pacific garbage patch", "-115,-35,-95,-25"),
    "south_atlantic_patch": ("South Atlantic garbage patch", "-20,-35,0,-25"),
    "indian_ocean_patch": ("Indian Ocean garbage patch", "70,-35,90,-25"),
    # Controls at the longitudes of the Great Pacific Garbage Patch: north of it (subpolar transition zone) and
    # south of it (trade-wind belt)
    "north_pacific_north": ("North Pacific, north of the patch", "-155,45,-135,52"),
    "north_pacific_south": ("North Pacific, south of the patch", "-155,20,-135,27"),
    # Controls of the other patches: boxes of the patch's size and longitudes, 5° north and south of it
    "north_atlantic_north": ("North Atlantic, north of the patch", "-70,40,-40,50"),
    "north_atlantic_south": ("North Atlantic, south of the patch", "-70,10,-40,20"),
    "south_pacific_north": ("South Pacific, north of the patch", "-115,-20,-95,-10"),
    "south_pacific_south": ("South Pacific, south of the patch", "-115,-50,-95,-40"),
    "south_atlantic_north": ("South Atlantic, north of the patch", "-20,-20,0,-10"),
    "south_atlantic_south": ("South Atlantic, south of the patch", "-20,-50,0,-40"),
    "indian_ocean_north": ("Indian Ocean, north of the patch", "70,-20,90,-10"),
    "indian_ocean_south": ("Indian Ocean, south of the patch", "70,-50,90,-40"),
    # The Great Pacific Garbage Patch centred on the particle-concentration maximum of the Ekman-drift model (33°N,
    # 141°W, data/garbage_patch_candidates.csv), with the size of the Wikipedia box, and its controls 5° north and
    # south: a check that the trends do not depend on the box (backup of garbage_patch_significance_slides.py)
    "gpgp_model": ("Great Pacific Garbage Patch, model maximum", "-151,28,-131,38"),
    "gpgp_model_north": ("North Pacific, north of the model patch", "-151,43,-131,53"),
    "gpgp_model_south": ("North Pacific, south of the model patch", "-151,13,-131,23"),
}
# The Pacific Ocean, 60°S-60°N, in four boxes that Giovanni can average (no date-line crossing) and that leave out the
# Indian Ocean around Australia and the Gulf of Mexico and Caribbean; the Pacific mean weights them by ocean area
PACIFIC_BOXES = {
    "pacific_northwest": ("Pacific Ocean, 120°E-180°, 10°S-60°N", "120,-10,180,60"),
    "pacific_southwest": ("Pacific Ocean, 150°E-180°, 60°S-10°S", "150,-60,180,-10"),
    "pacific_east": ("Pacific Ocean, 180°-100°W, 60°S-60°N", "-180,-60,-100,60"),
    "pacific_southeast": ("Pacific Ocean, 100°W-70°W, 60°S-8°N", "-100,-60,-70,8"),
}
# The Atlantic, 60°S-60°N, without the Gulf of Mexico, the western Caribbean, the Mediterranean and the North Sea, and
# the Indian Ocean, 60°S-25°N, without the Indonesian seas and the Coral Sea (as for the Pacific, the boundaries at
# 20°E and around Australia follow the IHO limits only roughly)
ATLANTIC_BOXES = {
    "atlantic_north": ("Atlantic Ocean, 75°W-10°W, 0-60°N", "-75,0,-10,60"),
    "atlantic_south": ("Atlantic Ocean, 65°W-20°E, 60°S-0", "-65,-60,20,0"),
}
INDIAN_BOXES = {
    "indian_west": ("Indian Ocean, 20°E-100°E, 60°S-25°N", "20,-60,100,25"),
    "indian_east": ("Indian Ocean, 100°E-142°E, 60°S-10°S", "100,-60,142,-10"),
}
OCEANS = {"pacific": PACIFIC_BOXES, "atlantic": ATLANTIC_BOXES, "indian": INDIAN_BOXES}
for boxes in OCEANS.values():
    REGIONS.update(boxes)
PATCHES = ["gpgp", "north_atlantic_patch", "south_pacific_patch", "south_atlantic_patch", "indian_ocean_patch"]
CONTROLS = ["north_pacific_north", "north_pacific_south"]
# for each patch: its controls north and south of it, and the ocean it lies in (OCEANS)
PATCH_CONTROLS = {
    "gpgp": ("north_pacific_north", "north_pacific_south", "pacific"),
    "north_atlantic_patch": ("north_atlantic_north", "north_atlantic_south", "atlantic"),
    "south_pacific_patch": ("south_pacific_north", "south_pacific_south", "pacific"),
    "south_atlantic_patch": ("south_atlantic_north", "south_atlantic_south", "atlantic"),
    "indian_ocean_patch": ("indian_ocean_north", "indian_ocean_south", "indian"),
}

SECONDS_PER_YEAR = 86400 * 365.25
# Giovanni variable id -> (label, display unit, conversion from the native unit)
VARIABLES = {
    "M2TMNXSLV_5_12_4_T2M": ("2 m air temperature", "°C", lambda x: x - 273.15),
    "M2TMNXSLV_5_12_4_T10M": ("10 m air temperature", "°C", lambda x: x - 273.15),
    "M2IMNPASM_5_12_4_T(z=10)": ("Air temperature at 10 hPa", "°C", lambda x: x - 273.15),
    "M2IMNPASM_5_12_4_T(z=50)": ("Air temperature at 50 hPa", "°C", lambda x: x - 273.15),
    "M2IMNPASM_5_12_4_T(z=100)": ("Air temperature at 100 hPa", "°C", lambda x: x - 273.15),
    "M2IMNPASM_5_12_4_T(z=500)": ("Air temperature at 500 hPa", "°C", lambda x: x - 273.15),
    "M2TMNXSLV_5_12_4_PS": ("Surface pressure", "hPa", lambda x: x),
    "M2TMNXSLV_5_12_4_TQV": ("Total precipitable water vapour", "mm", lambda x: x),
    "M2TMNXSLV_5_12_4_TO3": ("Total column ozone", "DU", lambda x: x),
    "M2TMNXFLX_5_12_4_PRECSNO": ("Snowfall", "mm water eq./yr", lambda x: x * SECONDS_PER_YEAR),
    "M2TMNXFLX_5_12_4_PRECTOTCORR": ("Precipitation", "mm/yr", lambda x: x * SECONDS_PER_YEAR),
    "M2TMNXFLX_5_12_4_SPEED": ("Surface wind speed", "m/s", lambda x: x),
    "M2TMNXRAD_5_12_4_CLDTOT": ("Total cloud fraction", "%", lambda x: x * 100),
    "M2TMNXAER_5_12_4_TOTEXTTAU": ("Aerosol optical depth (550 nm)", "", lambda x: x),
    "M2TMNXAER_5_12_4_DUEXTTAU": ("Dust aerosol optical depth (550 nm)", "", lambda x: x),
    "M2TMNXADG_5_12_4_DUDP003": ("Dust dry deposition (bin 3)", "mg/m²/yr", lambda x: x * 1e6 * SECONDS_PER_YEAR),
    "M2TMNXADG_5_12_4_DUWT003": ("Dust wet deposition (bin 3)", "mg/m²/yr", lambda x: x * 1e6 * SECONDS_PER_YEAR),
    "M2TMNXOCN_5_12_4_TSKINWTR": ("Sea-surface skin temperature (MERRA-2)", "°C", lambda x: x - 273.15),
    "M2TMNXOCN_5_12_4_FRSEAICE": ("Sea-ice fraction", "%", lambda x: x * 100),
    "MODISA_L3m_CHL_Mo_4km_R2022_0_chlor_a": ("Chlorophyll-a (MODIS-Aqua)", "mg/m³", lambda x: x),
    "MODISA_L3m_KD_Mo_4km_R2022_0_Kd_490": ("Diffuse attenuation at 490 nm (MODIS-Aqua)", "1/m", lambda x: x),
    "MODISA_L3m_POC_Mo_4km_R2022_0_poc": ("Particulate organic carbon (MODIS-Aqua)", "mg/m³", lambda x: x),
    "MODISA_L3m_NSST_Monthly_4km_R2019_0_sst": ("Sea-surface temperature, night (MODIS-Aqua)", "°C", lambda x: x),
    "MODISA_L3m_NSST_Monthly_9km_R2019_0_sst": ("Sea-surface temperature, night (MODIS-Aqua)", "°C", lambda x: x),
    "M2TMNXSLV_5_12_4_SLP": ("Sea-level pressure", "hPa", lambda x: x),  # Giovanni gives hPa, not the Pa of MERRA-2
    "M2TMNXSLV_5_12_4_U10M": ("10 m eastward wind", "m/s", lambda x: x),
    "M2TMNXSLV_5_12_4_V10M": ("10 m northward wind", "m/s", lambda x: x),
    "M2TMNXOCN_5_12_4_TAUXWTR": ("Eastward wind stress over water", "mN/m²", lambda x: x * 1000),
    "M2TMNXOCN_5_12_4_TAUYWTR": ("Northward wind stress over water", "mN/m²", lambda x: x * 1000),
    "M2TMNXAER_5_12_4_SSEXTTAU": ("Sea-salt aerosol optical depth (550 nm)", "", lambda x: x),
    "M2TMNXOCN_5_12_4_RAINOCN": ("Rainfall over the ocean", "mm/yr", lambda x: x * SECONDS_PER_YEAR),
    "M2TMNXFLX_5_12_4_EVAP": ("Evaporation", "mm/yr", lambda x: x * SECONDS_PER_YEAR),
    "MODISA_L3m_FLH_Mo_4km_R2022_0_nflh": ("Chlorophyll fluorescence line height (MODIS-Aqua)", "µW/cm²/µm/sr",
                                           lambda x: x * 1000),
    "MODISA_L3m_PIC_Mo_4km_R2022_0_pic": ("Particulate inorganic carbon (calcite) (MODIS-Aqua)", "mmol/m³",
                                          lambda x: x * 1000),
    "MODISA_L3m_IOP_Mo_4km_R2022_0_adg_443": ("CDOM + detritus absorption at 443 nm (MODIS-Aqua)", "1/m", lambda x: x),
    "MODISA_L3m_IOP_Mo_4km_R2022_0_aph_443": ("Phytoplankton absorption at 443 nm (MODIS-Aqua)", "1/m", lambda x: x),
    "MODISA_L3m_IOP_Mo_4km_R2022_0_bbp_443": ("Particulate backscattering at 443 nm (MODIS-Aqua)", "1/m", lambda x: x),
    "MODISA_L3m_PAR_Mo_4km_R2022_0_par": ("Photosynthetically available radiation (MODIS-Aqua)", "E/m²/day",
                                          lambda x: x),
    "NOBM_MON_R2017_h": ("Mixed-layer depth (NOBM model)", "m", lambda x: x),
    "NOBM_MON_R2017_rno": ("Nitrate (NOBM model)", "µmol/L", lambda x: x),
    "NOBM_MON_R2017_tot": ("Total chlorophyll (NOBM model)", "mg/m³", lambda x: x),
    "NOBM_MON_R2017_dia": ("Diatoms (NOBM model)", "mg chl/m³", lambda x: x),
    "NOBM_MON_R2017_cya": ("Cyanobacteria (NOBM model)", "mg chl/m³", lambda x: x),
    "NOBM_MON_R2017_coc": ("Coccolithophores (NOBM model)", "mg chl/m³", lambda x: x),
}


def file_name(variable):
    """Giovanni variable id -> CSV file stem, as written by giovanni_fetch.sh."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in variable)


def load_series(region, variable):
    """Monthly series in display units, indexed by the first day of the month."""
    folder = DATA / region
    # 7 metadata lines and a blank line precede the "time, value" header
    df = pd.read_csv(folder / f"{file_name(variable)}.csv", skiprows=8, names=["time", "x"], header=0,
                     parse_dates=["time"])
    x = pd.to_numeric(df["x"], errors="coerce")
    # Months are stamped at their start, except the MODIS SST months up to 2021-11, which are stamped at the
    # end of the previous month (e.g. July 2006 at 2006-06-30): round to the nearest month start
    month = (df["time"] + pd.Timedelta(days=15)).dt.to_period("M").dt.to_timestamp()
    s = pd.Series(x.values, index=month)
    s = s[(s.abs() < 1e14) & (s != -32767)].dropna()  # fill values 1e15 (MERRA-2) and -32767 (MODIS)
    if "TSKINWTR" in variable:
        # 1980-05 and 1980-11 are ~10 K below their neighbours in every region in the Giovanni output: not physical
        s = s.drop(pd.to_datetime(["1980-05-01", "1980-11-01"]), errors="ignore")
    return VARIABLES[variable][2](s)


def load_ocean_series(ocean, variable):
    """Mean over an ocean of OCEANS: the series of its boxes weighted by the ocean area of each box (OSCAR ocean mask,
    0.25°), in the months all boxes have data."""
    oscar = np.load(DATA.parent / "oscar" / "oscar_mean_2004_2023.npz")
    lat, lon = oscar["lat"], (oscar["lon"] + 180) % 360 - 180
    cell_area = np.cos(np.radians(lat))[:, None] * (oscar["n"] > 0)
    weighted, weights = [], []
    for box, (_, bbox) in OCEANS[ocean].items():
        w, s, e, n = map(float, bbox.split(","))
        weight = cell_area[(lat >= s) & (lat <= n)][:, (lon >= w) & (lon <= e)].sum()
        weighted.append(load_series(box, variable) * weight)
        weights.append(weight)
    return (pd.concat(weighted, axis=1).dropna().sum(axis=1) / sum(weights)).rename(variable)


def decimal_year(index):
    return index.year + (index.month - 0.5) / 12


def fit_trend(s):
    """OLS trend of the deseasonalised anomaly (monthly climatology removed).

    Significance uses the lag-1 autocorrelation correction of the effective sample size,
    n_eff = n (1 - r1) / (1 + r1) (Santer et al. 2000, JGR 105, 7337). Mann-Kendall test and
    Theil-Sen slope are computed on complete-year annual means.
    """
    anomaly = s - s.groupby(s.index.month).transform("mean")
    t = decimal_year(s.index)
    fit = stats.linregress(t, anomaly.values)
    residual = anomaly.values - (fit.intercept + fit.slope * t)
    r1 = max(np.corrcoef(residual[:-1], residual[1:])[0, 1], 0)
    n_eff = len(s) * (1 - r1) / (1 + r1)
    stderr = fit.stderr * np.sqrt((len(s) - 2) / (n_eff - 2))
    p = 2 * stats.t.sf(abs(fit.slope / stderr), n_eff - 2)

    counts = s.groupby(s.index.year).count()
    annual = s.groupby(s.index.year).mean()[counts == 12]
    tau, p_mk = stats.kendalltau(annual.index, annual.values)

    monthly_slope, monthly_p = {}, {}
    for month, g in s.groupby(s.index.month):
        m_fit = stats.linregress(g.index.year, g.values)
        monthly_slope[month], monthly_p[month] = m_fit.slope * 10, m_fit.pvalue
    return dict(anomaly=anomaly, intercept=fit.intercept, slope_per_decade=fit.slope * 10,
                ci95_per_decade=stats.t.ppf(0.975, n_eff - 2) * stderr * 10, p_ols_ar1=p, r1=r1, n_eff=n_eff,
                mk_tau=tau, p_mk=p_mk, sen_per_decade=stats.theilslopes(annual.values, annual.index)[0] * 10,
                monthly_slope=monthly_slope, monthly_p=monthly_p)


def annual_trend(s, first_year, last_year, months=None):
    """OLS and Mann-Kendall trend of the yearly mean over [first_year, last_year], optionally of some months only."""
    s = s[(s.index.year >= first_year) & (s.index.year <= last_year)]
    if months:
        s = s[s.index.month.isin(months)]
    yearly = s.groupby(s.index.year).mean()
    fit = stats.linregress(yearly.index, yearly.values)
    return dict(yearly=yearly, intercept=fit.intercept, slope_per_decade=fit.slope * 10, p_ols=fit.pvalue,
                p_mk=stats.kendalltau(yearly.index, yearly.values)[1])
