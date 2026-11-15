"""Build "Garbage Patch Trends vs Controls.pptx": the trends in the patches, compared with the control boxes north and
south of each patch and with the ocean and global means, and which of them are statistically significant. Figures
from plot_garbage_patch.py and garbage_patch_regions.py; slides built as in garbage_patch_slides.py.
"""
from garbage_patch_slides import CARDS4, FIGURE, REPO, TITLE, build

DECK = REPO / "Garbage Patch Trends vs Controls.pptx"
SOURCE = "MERRA-2 1980–2026, MODIS-Aqua 2002–2025 and NOBM 1998–2015, monthly area averages via NASA Giovanni"
COLOURS = ("Strong colour: p < 0.01 (**), pale: p < 0.05 (*), no colour: not significant. Orange: rising, "
           "blue: falling.")

VALUES = "Patch: orange; controls: blue and green; faint: ocean and global means. * p < 0.05."
CHANGE = "Change since the first complete year: °C for temperature, % otherwise."


def patch_slide(name, title, boxes, ocean, notes):
    """Slide of one of the other patches: the relative figure of plot_garbage_patch.py with the GPGP dashed."""
    return (FIGURE, {
        2: f"{name.upper()} · CHANGE",
        3: title,
        4: f"Change since the first year, °C or %. Faint: {ocean} and global means; dashed: Great Pacific patch.",
        6: f"{boxes}; MERRA-2 and MODIS-Aqua via NASA Giovanni",
    }, f"{name.lower().replace(' ', '_')}_patch_vs_controls_relative.png", notes)


slides = [
    (TITLE, {
        3: "Is the garbage patch changing faster than its surroundings?",
        4: "Trends in five garbage patches, their control boxes and the ocean and global means, and which of them are "
           "statistically significant",
        5: "11 variables · 5 patches, 10 controls, 3 oceans · MERRA-2, MODIS-Aqua and NOBM via NASA Giovanni",
    }, None,
     "A trend in a patch only says something about the patch if the water around it does not show the same trend. "
     "So we compare each patch with two control boxes right next to it, with the mean of its ocean and the global "
     "ocean, and the other patches with the Great Pacific patch, and test every trend and every difference for "
     "significance."),
    (FIGURE, {
        2: "REGIONS",
        3: "Five patches, ten controls and three ocean means",
        4: "Controls: boxes of the patch's size and longitudes, north and south of it. Purple: ocean means.",
        6: "Bounding boxes as in giovanni.py; Giovanni cannot average across the date line, hence several boxes per "
           "ocean",
    }, "regions.png",
     "Great Pacific patch 135–155°W, 35–42°N as on Wikipedia, with controls of its size at 45–52°N and 20–27°N. The "
     "other patches are the gyre centres of the North Atlantic, South Pacific, South Atlantic and Indian Ocean, each "
     "10° high, with controls of the same size 5° poleward and equatorward. The "
     "ocean means are area-weighted means of the purple boxes; they leave out marginal seas such as the Gulf of "
     "Mexico, the Mediterranean and the Indonesian seas. The global mean covers the whole ocean."),
    (CARDS4, {
        2: "VARIABLES",
        3: "What the ocean's colour tells about its life",
        5: "Chlorophyll-a",
        6: "Green pigment of phytoplankton",
        7: "From how green rather than blue the sea looks: more phytoplankton, more chlorophyll (mg/m³).",
        9: "Fluorescence (nFLH)",
        10: "Red glow of phytoplankton",
        11: "Chlorophyll re-emits a little of the sunlight it absorbs as red light near 678 nm.",
        13: "Organic carbon (POC)",
        14: "Carbon in particles",
        15: "Living and dead plankton and debris in the water, in mg/m³: the food of the ocean's life.",
        17: "Light attenuation (Kd490)",
        18: "How fast blue light fades",
        19: "How quickly blue light (490\u00a0nm) dims with depth, in 1/m; higher means murkier water.",
    }, None,
     "All four come from the MODIS-Aqua satellite, which measures the light leaving the sea surface in several colours "
     "(NASA Ocean Biology Processing Group products, 4 km, monthly). Phytoplankton are the microscopic algae at the "
     "base "
     "of the marine food web. Fluorescence is measured independently of the chlorophyll colour ratio; it also depends "
     "on how stressed the phytoplankton are. Kd490 is the diffuse attenuation coefficient at 490 nm: light falls to "
     "1/e of its surface value at a depth of 1/Kd490, about 25 m in the patch. Sea-surface temperature and wind come "
     "from the MERRA-2 reanalysis."),
    (FIGURE, {
        2: "METHOD",
        3: "From a raw time series to a significance test",
        4: "Real data: Great Pacific chlorophyll-a. Orange line and band: trend and its 95 % interval.",
        6: "MODIS-Aqua 2002–2025 via NASA Giovanni; autocorrelation correction of Santer et al. 2000; code: "
           "giovanni.fit_trend",
    }, "method_pipeline.png",
     "1: Giovanni averages the satellite map over the box for each month. 2: subtracting each calendar month's mean "
     "removes the seasonal cycle, which would otherwise dominate. 3: the least-squares slope of the anomalies is the "
     "trend; neighbouring months are not independent, so the t-test uses the effective sample size "
     "n_eff = n (1 − r1) / (1 + r1), with r1 the lag-1 autocorrelation of the residuals (Santer et al. 2000, JGR 105, "
     "7337): here 74 of 281 months, p = 0.01. Trends are then quoted per decade and, except for temperature and "
     "pressure, in % of the region's mean. 4: the same steps on the log ratio ln(patch / Pacific mean) test whether "
     "the two relative trends differ (its slope × 100 is the difference in % per decade); using the ratio accounts "
     "for the weather the two regions share. Here they do: −9.3 % per decade, p = 0.005."),
    (TITLE, {
        2: "PART 1",
        3: "The Great Pacific Garbage Patch",
        4: "How it changes compared with the water north and south of it, the Pacific Ocean and the global ocean",
        5: "135–155°W, 35–42°N · controls at 45–52°N and 20–27°N",
    }, None,
     "First the best-studied patch, in the box given on Wikipedia. Its controls lie on "
     "the same longitudes: the subpolar transition zone to the north and the trade-wind belt to the south."),
    (FIGURE, {
        2: "GREAT PACIFIC · VALUES",
        3: "The patch warms twice as fast as its surroundings",
        4: VALUES,
        6: "Patch 35–42°N, controls 45–52°N and 20–27°N, all at 135–155°W; MERRA-2 and MODIS-Aqua via NASA Giovanni",
    }, "gpgp_vs_controls.png",
     "Sea surface +0.33 °C per decade in the patch, +0.17 north and +0.13 south of it, +0.16 for the Pacific and "
     "+0.15 for the global mean. Chlorophyll −8.3 % per decade in the patch (p = 0.01), +0.3 % north (p = 0.93), "
     "−4.2 % south (p = 0.06, Mann-Kendall p = 0.007), +1.4 % in the Pacific mean (not significant) and +3.5 % "
     "globally. Fluorescence −10.1 % and organic carbon −6.2 % per decade in the patch. The wind weakens only in the "
     "patch (−1.4 % per decade)."),
    (FIGURE, {
        2: "GREAT PACIFIC · CHANGE",
        3: "From the same start, the patch warms and loses plankton fastest",
        4: CHANGE + " Faint: Pacific and global means.",
        6: "Patch 35–42°N, controls 45–52°N and 20–27°N, all at 135–155°W; MERRA-2 and MODIS-Aqua via NASA Giovanni",
    }, "gpgp_vs_controls_relative.png",
     "Every line starts at 0 in its first complete year (1981 for temperature, because two months of 1980 are faulty "
     "in the Giovanni output; 1980 for wind; 2003 for MODIS). The patch is 1.5 °C warmer than in 1981, the controls "
     "and the ocean means about 0.6–0.7 °C. Its chlorophyll and organic carbon are about 20 % below 2003; the controls "
     "and ocean means stay within ±10 %. A single start year is noisy, so the end points are only a guide; the trends "
     "above the panels use all months."),
    (TITLE, {
        2: "PART 2",
        3: "The other garbage patches",
        4: "Do the North Atlantic, South Pacific, South Atlantic and Indian Ocean patches change the same way?",
        5: "One slide per patch · each with its own controls and ocean · dashed: the Great Pacific patch",
    }, None,
     "The same comparison for the four other subtropical gyres. The dashed line repeats the Great Pacific patch, so "
     "each patch can be compared with it directly."),
    patch_slide("North Atlantic", "In the North Atlantic, only the patch loses chlorophyll",
                "Patch 25–35°N, controls 40–50°N and 10–20°N, all at 40–70°W", "Atlantic",
                "Sea surface +0.26 °C per decade, like its controls (+0.28 north, +0.20 south) and faster than the "
                "Atlantic mean (+0.17). Chlorophyll −6.4 % per decade in the patch, but +5.8 % north, +5.4 % south and "
                "+3.9 % in the Atlantic mean: the patch's chlorophyll falls 10–12 % per decade faster than each of "
                "them (p < 0.01). Fluorescence −10.3 % per decade, as fast as in the Great Pacific patch, and as fast "
                "in the south control (−10.4 %)."),
    patch_slide("South Pacific", "The South Pacific patch loses fluorescence, not chlorophyll",
                "Patch 25–35°S, controls 10–20°S and 40–50°S, all at 95–115°W", "Pacific",
                "Sea surface +0.14 °C per decade, like the south control (+0.12) and the Pacific mean (+0.16); the "
                "north control does not warm. Chlorophyll −2.4 % per decade, not significant, in the clearest water "
                "on Earth (0.036 mg/m³). Fluorescence −5.6 % per decade, significantly faster than in both controls "
                "(+1.8 % and −0.9 %). The wind weakens relative to both controls."),
    patch_slide("South Atlantic", "The South Atlantic patch shows no plankton decline",
                "Patch 25–35°S, controls 10–20°S and 40–50°S, all at 0–20°W", "Atlantic",
                "Every region here warms by about +0.13 °C per decade. Chlorophyll +3.6 % and fluorescence −3.1 % per "
                "decade in the patch, neither significant. The only significant difference is fluorescence against "
                "the south control (−3.7 % per decade, p < 0.05), which among this many tests could be chance."),
    patch_slide("Indian Ocean", "The Indian Ocean patch loses plankton like the Great Pacific",
                "Patch 25–35°S, controls 10–20°S and 40–50°S, all at 70–90°E", "Indian Ocean",
                "Sea surface +0.26 °C per decade: faster than the south control (+0.09) and the Indian Ocean mean "
                "(+0.15), as fast as the north control (+0.22). Chlorophyll −7.6 %, fluorescence −8.1 %, organic "
                "carbon −5.5 % and light attenuation −3.0 % per decade; all fall significantly faster than in the "
                "south control and the Indian Ocean mean, but not than the north control (10–20°S), where they also "
                "fall, not significantly. Caveat: whether a stable patch exists in the southern Indian Ocean is "
                "debated (van der Mheen, Pattiaratchi and van Sebille)."),
    (CARDS4, {
        2: "CONCLUSION",
        3: "Shared plankton loss; the fast warming is the Great Pacific's",
        5: "Warming",
        6: "Fastest in the Great Pacific",
        7: "+0.33 °C per decade, faster than both controls; the other patches mostly warm like their surroundings.",
        9: "Less phytoplankton",
        10: "Three of five patches",
        11: "Great Pacific, North Atlantic and Indian Ocean: chlorophyll 9–10 % per decade faster than their ocean.",
        13: "Against the controls",
        14: "Clearest in the North Atlantic",
        15: "Chlorophyll 10–12 % per decade faster than both controls; Great Pacific: fluorescence.",
        17: "Answer",
        18: "Not the Great Pacific alone",
        19: "The plankton decline is a pattern of three gyres; the South Atlantic does not show it.",
    }, None,
     "Warming: only the Great Pacific patch warms significantly faster than both its controls (+0.16 and +0.20 °C per "
     "decade); the Indian Ocean patch warms faster than its south control and its ocean, the North Atlantic patch "
     "faster than the Atlantic mean. Phytoplankton: chlorophyll falls faster than the ocean mean in the Great Pacific "
     "(−9.3 % per decade), North Atlantic (−10.0 %) and Indian Ocean (−9.7 %) patches, all p < 0.01. The South "
     "Pacific patch only loses fluorescence; the South Atlantic patch shows nothing beyond chance."),
    (FIGURE, {
        2: "ALL REGIONS",
        3: "Every region warms; patch chlorophyll falls in three of five",
        4: "Trend per decade. " + COLOURS,
        6: SOURCE + "; p-values corrected for autocorrelation",
    }, "significance_regions.png",
     "Each patch is followed by its controls north and south; the ocean and global means are at the bottom. 83 of "
     "the 189 trends are significant at p < 0.05 (53 at p < 0.01); chance alone would give about 9. Sea-surface "
     "temperature rises significantly in every region except the control north of the South Pacific patch."),
    (FIGURE, {
        2: "IS EACH PATCH DIFFERENT?",
        3: "Three patches lose plankton faster than their ocean",
        4: "Trend of the difference (°C, hPa) or of the log ratio (%). Coloured: the two trends differ significantly.",
        6: "Colours as on the previous slide. " + SOURCE,
    }, "significance_differences.png",
     "A coloured cell means the patch changes significantly faster (or slower) than the region it is compared with. "
     "43 of the 140 differences are significant at p < 0.05 (27 at p < 0.01); chance alone would give about 7. "
     "Chlorophyll falls faster than the ocean mean in the Great Pacific, North Atlantic and Indian Ocean patches; "
     "fluorescence falls faster than both controls in the Great Pacific and South Pacific patches."),
    (CARDS4, {
        2: "SUMMARY",
        3: "What is significant",
        5: "Warming",
        6: "+0.33 °C per decade",
        7: "Every region warms; the Great Pacific patch fastest, twice its controls and the ocean means.",
        9: "Less phytoplankton",
        10: "−6 to −8 % per decade",
        11: "Chlorophyll in the Great Pacific, North Atlantic and Indian Ocean patches, not in the ocean means.",
        13: "Patch vs surroundings",
        14: "9–10 % per decade faster",
        15: "The chlorophyll decline in those three patches, relative to their ocean mean (p < 0.01).",
        17: "Chance",
        18: "83 of 189 trends significant",
        19: "About 9 expected by chance at p < 0.05: trust the strong cells and the repeated patterns.",
    }, None,
     "With many tests, some pale (p < 0.05) cells are expected by chance; the strong (p < 0.01) cells and the "
     "patterns repeated across regions and variables are the robust results. None of these variables measures the "
     "plastic itself: the trends describe the gyres the plastic collects in."),
    (TITLE, {
        2: "BACKUP",
        3: "Datasets and choices",
        4: "The data behind the trends, and whether the choice of the Great Pacific box matters",
        5: "MERRA-2 · MODIS-Aqua · NOBM · NASA Giovanni",
    }, None, "Backup slides for questions about the data and the choice of boxes."),
    (CARDS4, {
        2: "BACKUP · DATA SOURCES",
        3: "Three NASA data products, one tool",
        5: "MERRA-2",
        6: "Reanalysis\n1980–2026",
        7: "A weather model fitted to observations; 0.5° × 0.625°: temperature, wind, pressure, aerosols.",
        9: "MODIS-Aqua",
        10: "Satellite\n2002–2026",
        11: "Ocean colour at 4 km (chlorophyll, fluorescence, carbon, Kd490) and night temperature at 9 km.",
        13: "NOBM",
        14: "Ocean model\n1998–2015",
        15: "NASA Ocean Biogeochemical Model, assimilating satellite chlorophyll; 0.67° × 1.25°.",
        17: "NASA Giovanni",
        18: "Area means per month",
        19: "Averages each product over a box for every month; we fetch 400+ such series.",
    }, None,
     "MERRA-2 (Modern-Era Retrospective analysis for Research and Applications, version 2) is NASA GMAO's "
     "reanalysis; we use its monthly ocean-surface, flux, single-level and aerosol collections (version 5.12.4). "
     "MODIS-Aqua level-3 mapped monthly products come from the NASA Ocean Biology Processing Group: ocean colour in "
     "reprocessing R2022.0, night sea-surface temperature (11 µm) in R2019.0. NOBM (NASA Ocean Biogeochemical Model, "
     "R2017) simulates nutrients and four phytoplankton groups and assimilates satellite chlorophyll. Giovanni's "
     "area-averaged time series (service ArAvTs) weights the grid cells by area; the ocean means weight their boxes "
     "by ocean area (OSCAR mask)."),
    (FIGURE, {
        2: "BACKUP · DATASETS",
        3: "Every variable, its source, grid and period",
        4: "All series are monthly area means over each box, computed by NASA Giovanni.",
        6: "MERRA-2 (orange), MODIS-Aqua (green) and NOBM (purple); periods as downloaded for the Great Pacific box",
    }, "datasets.png",
     "Sea-surface temperature from MERRA-2 is the skin temperature over open water, converted to °C; two months of "
     "1980 are faulty in the Giovanni output and left out. Fluorescence is the normalized fluorescence line height "
     "(nFLH), shown in µW/cm²/µm/sr. Aerosol optical depth is the total extinction at 550 nm. NOBM ends in 2015 in "
     "Giovanni."),
    (CARDS4, {
        2: "BACKUP · GREAT PACIFIC BOX",
        3: "A box at the model maximum gives the same main trends",
        5: "Box used",
        6: "35–42°N\n135–155°W",
        7: "As on Wikipedia; on the northern edge of the gyre, where greener water from the north reaches in.",
        9: "Model maximum",
        10: "33°N, 141°W",
        11: "Where floating particles, drifted with the 2003–2024 wind-driven flow, gather most.",
        13: "Alternative box",
        14: "28–38°N\n131–151°W",
        15: "Same size, centred on the maximum: 3 °C warmer, half the chlorophyll of the box used.",
        17: "Result",
        18: "Same main trends",
        19: "Chlorophyll −7.8 % (box used −8.3 %), warming +0.30 °C (+0.33) per decade.",
    }, None,
     "Wikipedia places the patch at 135–155°W, 35–42°N. Lebreton et al. 2018 (Scientific Reports 8, 4666) define the "
     "patch by more than 10 kg of plastic per km², 1.6 million km², not by a box. Our Ekman-drift model puts the "
     "particle maximum at 33°N, 141°W, south of the Wikipedia box; an emissions-weighted Lagrangian model with OSCAR "
     "currents puts it near 29°N, 135°W. In a box of the same size centred on the maximum, with its own controls at "
     "43–53°N and 13–23°N, chlorophyll still falls faster than in the Pacific mean (−8.9 % per decade, p = 0.001) and "
     "the patch still warms faster than the Pacific mean (+0.13 °C per decade, p = 0.01), but not significantly "
     "faster than its north control (+0.12, p = 0.09). Fluorescence (−7.0 % against −10.1 % per decade) and organic "
     "carbon (−4.4 % against −6.2 %) fall more slowly there: part of their decline in the box used comes from the "
     "moving edge of the gyre."),
]

if __name__ == "__main__":
    build(DECK, slides)
