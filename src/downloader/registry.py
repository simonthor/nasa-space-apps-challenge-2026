DATASET_REGISTRY = {
    "chlorophyll_monthly": {
        "short_name": "MODISA_L3m_CHL",
        "version": "2022.0",
        "granule_name": "*.MO.CHL.chlor_a.4km.nc",
        "vars": ["chlor_a"],
        "units": {"chlor_a": "mg/m^3"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },
    "sst_monthly": {
        "short_name": "MODISA_L3m_SST",
        "version": "R2019.0",
        "granule_name": "*.MO.SST.sst.4km.nc",
        "vars": ["sst"],
        "units": {"sst": "degC"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },
    "reflectance_monthly": {
        "short_name": "MODISA_L3m_RRS",
        "version": "2022.0",
        "granule_name": "*.MO.RRS.Rrs_531.4km.nc",
        "vars": ["Rrs_531"],
        "units": {"Rrs_531": "sr^-1"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },
    "salinity_monthly": {
        "short_name": "SMAP_JPL_L3_SSS_CAP_MONTHLY_V5",
        "vars": ["smap_sss"],
        "units": {"smap_sss": "PSU"},
        "convert": lambda ds: ds,
    },

    "microplastic_daily": {
        "short_name": "CYGNSS_L3_MICROPLASTIC_V1.0",  # или CYGNSS_L3_MICROPLASTIC_V3.2
        "vars": ["MP_concentration"],
        "units": {"MP_concentration": "count/km^2"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },

    "kd490_monthly": {
        "short_name": "MODISA_L3m_KD",
        "version": "2022.0",
        "granule_name": "*.MO.KD.Kd_490.4km.nc",
        "vars": ["Kd_490"],
        "units": {"Kd_490": "m^-1"},
        "global_granules": True,
        "convert": lambda ds: ds,
    },

    "currents_daily": {
        "short_name": "OSCAR_L4_OC_FINAL_V2.0",
        "vars": ["u", "v"],
        "units": {"u": "m/s", "v": "m/s"},
        "convert": lambda ds: ds,
    },
    "wind_daily": {
        "short_name": "CCMP_WINDS_10M6HR_L4_V3.1",
        "vars": ["uwnd", "vwnd"],
        "units": {"uwnd": "m/s", "vwnd": "m/s"},
        "convert": lambda ds: ds,
    },
    "sst_daily_1km": {
        "short_name": "MUR-JPL-L4-GLOB-v4.1",
        "vars": ["analysed_sst"],
        "units": {"analysed_sst": "degC"},
        "convert": lambda ds: ds - 273.15,
    },
}