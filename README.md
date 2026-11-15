# NASA Earth System Trend Detective
### *The Ocean Gyre Investigation: Unmasking Climate Signals & Microplastic Accumulation Zones*

[![NASA Space Apps Challenge 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-brightgreen.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io/)
[![NASA Earthdata](https://img.shields.io/badge/Data-NASA%20Earthdata%20%2F%20Giovanni-orange.svg)](https://earthdata.nasa.gov/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An interactive Earth science discovery platform built for the **NASA International Space Apps Challenge 2026** under the challenge **"Be An Earth System Trend Detective!"**.

---

## The Detective Story: The Myth vs. The Reality

### The Hypothesis
Can spaceborne Earth-observing satellites (such as NASA's MODIS Aqua) directly detect the **Great Pacific Garbage Patch (GPGP)** and the four other major subtropical ocean gyres? Could spectral changes in green reflectance ($R_{rs\_531}$) or water optical clarity ($K_{d\_490}$) serve as direct proxies for floating marine microplastics?

### The Investigation
We gathered over 23 years (July 2002 – October 2025, 282 monthly timesteps) of satellite data across **all 5 oceanic subtropical gyres**:
1. **North Pacific Gyre** (Great Pacific Garbage Patch — GPGP)
2. **South Pacific Gyre**
3. **North Atlantic Gyre**
4. **South Atlantic Gyre**
5. **Indian Ocean Gyre**

To test whether observed patterns were unique to plastic convergence zones, we established **paired North and South Control baseline boundaries** for each gyre. 

When analyzing initial correlations, apparent optical anomalies in the Great Pacific Garbage Patch failed to replicate in the other four gyres. This proved that optical satellites with 4 km spatial resolution **do not directly observe sub-millimeter dispersed microplastics**; the direct optical signature was a coincidence.

```
       O P E N    O C E A N    S T R A T I F I C A T I O N    C Y C L E
       
  Atmospheric Warming               Higher Sea Surface Temp (+0.3°C to +0.6°C / dec)
         │                                               │
         ▼                                               ▼
  Stronger Density Barrier  ──────►  Suppressed Deep-Nutrient Upwelling (Nitrates / Phosphates)
                                                         │
                                                         ▼
  Expanding "Ocean Deserts" ◄──────  Declining Chlorophyll-a (-6% to -8% / dec, p < 0.05)
```

### The Discovery: Oligotrophic Gyre Expansion
While satellites cannot see floating plastic particles directly, NASA Earth science data revealed a profound, statistically validated planetary trend:
* **Accelerating Ocean Stratification**: Sea Surface Temperatures (SST) across the gyres have surged by **$+0.3^\circ\text{C}$ to $+0.6^\circ\text{C}$ per decade** ($p < 0.001$).
* **Starving Ocean Deserts**: The enhanced thermal stratification acts as a physical cap, preventing colder, nutrient-rich deep water from mixing upward into the photic zone.
* **Significant Phytoplankton Decline**: In the North Pacific (GPGP), North Atlantic, and Indian Ocean, photosynthetic Chlorophyll-a shows a statistically significant long-term decline of **$-6\%$ to $-8\%$ per decade** ($p < 0.01$). Meanwhile, adjacent northern boundary waters exhibit opposite, positive trends ($+3\%$ to $+10\%$).
* **Conclusion**: The calm subtropical gyres where ocean currents naturally trap anthropogenic plastics are simultaneously ground zero for the expansion of **oligotrophic marine deserts**.

---

## Key Features

- **Interactive 3D Globe & 2D Projection**: High-performance interactive visualization of global satellite fields with equirectangular maps and 3D globe renderings.
- **Precise Gyre & Control Boundary Overlay**: Real-time rendering of all 5 subtropical plastic convergence zones alongside latitudinally shifted North/South control polygons.
- **23-Year Dynamic Time Scrubbing**: Interactive slider spanning from **July 2002 to October 2025** (282 monthly time slices) with instant spatial updates.
- **Comprehensive Time-Series Deep Dives**:
  - Raw monthly observations capturing interannual events.
  - 12-month rolling moving averages filtering out seasonal cycles.
  - Ordinary Least Squares (OLS) multi-decadal trendlines.
  - Multi-region overlays comparing the patch center directly with its northern and southern control baselines.
- **Global Bar Charts & Spatial Contrast Tab**:
  - **Grouped Baseline Comparison**: Triple bar charts comparing baseline means across all 5 gyre systems in absolute physical units.
  - **Spatial Contrast Bar Chart**: Visualizes the relative contrast $\Delta \% = 100 \times \frac{\text{Patch} - \text{Controls}}{\text{Controls}}$ with block bootstrap 95% confidence intervals.
  - **Decadal Trend Rate Bar Chart**: Direct cross-gyre comparison of decade-scale climate velocity (`units/decade`).
- **Robust Scientific Statistics**:
  - Automatic computation of decadal rates and 23-year cumulative percentage changes.
  - Two-tailed Student’s $t$-test with **Santer et al. AR(1) autocorrelation lag-1 correction** for effective degrees of freedom ($N_{\text{eff}}$), preventing false positive trend detection.
- **Data Detective Case Briefings**:
  - Automated, human-readable scientific interpretations accompanying every graph, translating complex oceanographic metrics into clear educational insights.

---

##  NASA Datasets & Physical Variables

| Variable | Instrument / Mission | Spatial / Temporal Resolution | Physical Units | Scientific Role |
| :--- | :--- | :--- | :--- | :--- |
| **Chlorophyll-a** (`chlor_a`) | **MODIS Aqua** (NASA GSFC / OBPG) | 4 km / Monthly (2002–2025) | $\text{mg/m}^3$ | Marine primary productivity and phytoplankton biomass. |
| **Sea Surface Temperature** (`sst`) | **MODIS Aqua** Thermal IR | 4 km / Monthly (2002–2025) | $^\circ\text{C}$ | Surface thermal structure driving vertical stratification. |
| **Diffuse Attenuation** ($K_{d\_490}$) | **MODIS Aqua** (490 nm band) | 4 km / Monthly (2002–2025) | $\text{m}^{-1}$ | Water clarity, turbidity, and light penetration depth. |
| **Reflectance** ($R_{rs\_531}$) | **MODIS Aqua** (531 nm band) | 4 km / Monthly (2002–2025) | $\text{sr}^{-1}$ | Spectral backscattering from suspended particulates. |
| **Sea Surface Salinity** (`sss`) | **SMAP** Microwave Radiometer | 0.25° / Monthly (2015–2025) | $\text{PSU}$ | Haline stratification and evaporation-precipitation balance. |
| **Microplastic Concentration** | **CYGNSS** Radar Constellation Proxy | 0.25° / Daily (2017–2018) | $\text{count/km}^2$ | Ocean roughness suppression due to surfactant-plastic layers. |

---

## Methodology & Statistical Rigor

### 1. Spatial Boundary Definition
Subtropical gyres and control zones were delineated using standard physical oceanography coordinates:
* **Patch Centers**: Low-energy convergence cores (e.g., GPGP at $35^\circ–42^\circ\text{N}, 135^\circ–155^\circ\text{W}$).
* **Control Regions**: Identical longitudinal swaths shifted $\pm 10^\circ–15^\circ$ North and South outside the convergence convergence zone to isolate local convergence effects from macro-scale basin climate signals.

### 2. Time-Series Deseasonalization & Trend Estimation
Linear trends are computed via Ordinary Least Squares (OLS) regression over the monthly mean time series $y(t)$:
$$\text{Slope} = \frac{\sum (t_i - \bar{t})(y_i - \bar{y})}{\sum (t_i - \bar{t})^2}$$
$$\text{Decadal Rate} = \text{Slope} \times 120\text{ months}$$

### 3. Autocorrelation Correction (Santer et al., 2000)
Monthly Earth science data exhibit strong lag-1 serial autocorrelation ($\rho_1$), which artificially inflates ordinary $t$-test significance. We calculate the effective sample size ($N_{\text{eff}}$):
$$N_{\text{eff}} = N \frac{1 - \rho_1}{1 + \rho_1}$$
The standard error of the slope ($SE_b$) is corrected using $N_{\text{eff}}$, and two-tailed $p$-values are computed:
$$t = \frac{\text{Slope}}{SE_b}, \quad p = 2 \times (1 - \Phi(|t|))$$
Trends are classified as **Significant ($p < 0.05$)** or **Not Statistically Significant ($p \ge 0.05$)**.

### 4. Block Bootstrap Spatial Difference
Spatial contrast between patch centers and controls is computed as:
$$\Delta \% = 100 \times \frac{\overline{X}_{\text{patch}} - \overline{X}_{\text{controls}}}{\overline{X}_{\text{controls}}}$$
95% confidence intervals are generated using 10,000 block-bootstrap resamples across matched, complete observation years.

---

## Interactive Platform Walkthrough

```
┌────────────────────────────────────────────────────────────────────────┐
│               🌍 NASA EARTH SYSTEM TREND DETECTIVE                     │
│               Investigating Ocean Gyres & Climate Change               │
├────────────────────────────────────────────────────────────────────────┤
│  [Dataset Selector]  [Month Slider: 2002-07 ────────●──── 2025-10]     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│                    INTERACTIVE GLOBAL MAP / 3D GLOBE                   │
│        (Displays selected physical variable with gyre boundaries)      │
│                                                                        │
├──────────────────────────────────┬─────────────────────────────────────┤
│  TAB 1: 📈 Regional Time Series  │  TAB 2: 📊 Global Bar Charts        │
│  - Raw monthly observations      │  - Grouped Patch vs Control Means   │
│  - 12-month moving average       │  - Spatial Contrast (Delta %)       │
│  - OLS Linear trendline          │  - Decadal Trend Rate Comparison    │
│  - North / South Control overlay │  - Comprehensive Summary Table      │
│  - 4 Key Statistical Cards       │  - Comparative Methodology Brief    │
│  - Detective Case Briefing       │                                     │
└──────────────────────────────────┴─────────────────────────────────────┘
```
## Visual Walkthrough

## Platform Screenshots & Visualizations

### 3D Globe Renders (PyVista)
| Chlorophyll-a (`chlor_a`) | Microplastic Proxy (CYGNSS) | Global Overview |
| :---: | :---: | :---: |
| ![PyVista Chlorophyll](img/pyvista_chlorophyll.png) | ![PyVista Plastic](img/pyvista_plastic.png) | ![PyVista Overview](img/pyvista_img1.png) |

### Interactive Dashboard & Spatial Maps (Streamlit)
| Chlorophyll-a Distribution | Microplastic Accumulation | Diffuse Attenuation ($K_{d\_490}$) |
| :---: | :---: | :---: |
| ![Streamlit Chlorophyll](img/streamlit_chlorophyll.png) | ![Streamlit Plastic](img/streamlit_plastic.png) | ![Streamlit Diffuse](img/streamlit_diffuse.png) |
| **Reflectance ($R_{rs\_531}$) — View 1** | **Reflectance ($R_{rs\_531}$) — View 2** | |
| ![Streamlit Reflectance](img/streamlit_reflectance.png) | ![Streamlit Reflectance v2](img/streamlit_reflectance_v2.png) | |

### Statistical Diagnostics & Multi-Gyre Comparisons
| Chlorophyll-a Time Series | Chlorophyll-a Cross-Gyre Compare | Reflectance Cross-Gyre Compare |
| :---: | :---: | :---: |
| ![Chlorophyll Diagnostics](img/streamlit_diag_chlorophyll.png) | ![Chlorophyll Compare](img/streamlit_diag_chlorophyll_compare.png) | ![Reflectance Compare](img/streamlit_diag_reflectance_compare.png) |

---

## Quick Start & Installation

### Option 1: Using Devenv / Nix (Recommended)
This repository includes a reproducible [`devenv.nix`](file:///home/basilisk/Projects/nasa_space_apps_challenge/devenv.nix) configuration with all required C++/X11 graphics libraries and Python dependencies pre-packaged:

```bash
# Clone the repository
git clone https://github.com/your-team/nasa-space-apps-challenge.git
cd nasa-space-apps-challenge

# Enter the reproducible shell
devenv shell

# Launch the Streamlit application
streamlit run src/interactive_view/app.py
```

### Option 2: Using Standard Python Virtual Environment
Requires **Python 3.10+** (Python 3.11 recommended):

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install numpy pandas xarray netcdf4 h5netcdf h5py requests earthaccess streamlit plotly pyvista

# Launch the application
streamlit run src/interactive_view/app.py
```

Open your browser at `http://localhost:8501`.

---

## Repository Structure

```text
├── data/
│   ├── coordinates/               # GeoJSON polygons of gyres & controls
│   ├── preview/                   # Downsampled NetCDF preview grids (2002–2025)
│   └── regions/                   # Pre-extracted regional NetCDF time series
├── img/                           # Application screenshots and visualization assets
├── src/
│   ├── downloader/                # NASA Earthdata & Giovanni data downloaders
│   │   ├── downloader.py          # NASA Earthaccess automated retrieval
│   │   ├── normalize.py           # Standardize variables, coordinates & timestamps
│   │   └── registry.py            # Dataset catalog definitions
│   ├── import_files/              # GeoJSON parsing and spatial cropping
│   │   ├── extract_regions_from_geojson.py
│   │   └── geojson_parser.py
│   ├── interactive_view/          # Streamlit Interactive Web Application
│   │   ├── app.py                 # Main application dashboard
│   │   ├── globe_pyvista.py       # 3D PyVista globe rendering engine
│   │   └── prepare_preview.py     # Grid downsampling & time-index synchronization
│   └── reflectance/               # Statistical spatial contrast module
│       ├── reflectance_analysis.py# Block bootstrap analysis across 5 oceans
│       ├── reflectance_plot.py    # Spatial contrast plotting routines
│       └── reflectance_results/   # Output figures and CSV summaries
├── devenv.nix                     # Reproducible Nix development environment
└── README.md                      # Project documentation
```

---

## Alignment with Challenge Objectives

| Challenge Requirement | How Our Project Solves It |
| :--- | :--- |
| **Select Variables of Interest** | Integrates 6 diverse variables across biological, physical, and optical domains (Chlorophyll-a, SST, $K_d$, $R_{rs}$, Salinity, Microplastics). |
| **Regional Boundary Definition** | Defines targeted polygons for all 5 global subtropical gyres alongside paired North/South background control regions. |
| **Generate & Visualize Time Series** | Delivers 23-year (2002–2025) continuous monthly time series with interactive seasonal smoothing and control comparisons. |
| **Statistical Trend & Significance Testing** | Calculates decadal change rates and performs two-tailed $t$-tests with **AR(1) autocorrelation correction** for scientific validity. |
| **Target Audience: Citizen Data Detectives** | Features an intuitive English UI with interactive maps, comparison tabs, and educational "Case Briefings" explaining the science in accessible language. |

---

## Citations & Acknowledgments

- **NASA Goddard Space Flight Center (GSFC) Ocean Biology Processing Group (OBPG)**: MODIS Aqua Ocean Color & SST products.
- **NASA Physical Oceanography DAAC (PO.DAAC)**: SMAP Sea Surface Salinity and CYGNSS Level 3 microplastic proxy datasets.
- **Santer, B. D., et al. (2000)**: *Accounting for the effect of serial correlation in estimating the significance of trends in atmospheric temperature.* Journal of Geophysical Research: Atmospheres.
- **Law, K. L., et al. (2010)**: *Plastic Accumulation in the North Atlantic Subtropical Gyre.* Science, 329(5996), 1185–1188.
- **Lebreton, L., et al. (2018)**: *Evidence that the Great Pacific Garbage Patch is rapidly accumulating plastic.* Scientific Reports, 8(1), 4666.

---
*Developed for the **NASA Space Apps Challenge 2026**.*
