"""Build "Great Pacific Garbage Patch Trends.pptx" from the figures in plots/garbage_patch/.

The slides are copies of the template slides of "Neutrino Sites Trends.pptx" (branch neutrino-sites), edited with
DeckCraft's command line (flatpak ai.storyteller.deckcraft): title, cards and figure slides get new text, pictures and
speaker notes, then the 17 neutrino slides are deleted. Run it again after the figures change.
"""
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).parent
PLOTS = f"{REPO}/plots/garbage_patch/"
DECK = REPO / "Great Pacific Garbage Patch Trends.pptx"
DECKCRAFT = ["flatpak", "run", "--user", f"--filesystem={REPO}", "--command=deckcraft-cli", "ai.storyteller.deckcraft"]
TEMPLATE_SLIDES = 17
TITLE, CARDS2, CARDS4, FIGURE, NEXT = 0, 1, 2, 3, 16

slides = [
    (TITLE, {
        3: "Trend detectives at the Great Pacific Garbage Patch",
        4: "What NASA Earth-science data say about the ocean in and around the plastic garbage patches",
        5: "42 monthly time series · 3 patches so far · MERRA-2, MODIS-Aqua, NOBM and CYGNSS via NASA Giovanni and "
           "PO.DAAC",
    }, None,
     "The Great Pacific Garbage Patch is the largest accumulation of floating plastic in the ocean. We asked which "
     "ocean and atmosphere variables are changing there, whether the same happens in the other garbage patches, and "
     "whether satellite data can help find patches at all."),
    (CARDS2, {
        2: "THE PATCH",
        3: "Plastic gathers where the wind pushes surface water together",
        5: "Great Pacific Garbage Patch · 135–155°W, 35–42°N",
        6: "About 1.6 million km² and 80,000 t of floating plastic",
        7: "1.8 trillion pieces, mostly microplastics; in the gyre, plastic outweighs the plankton about six to one.",
        8: "The plastic itself is invisible to most satellites: we look at its surroundings.",
        10: "Why there · the North Pacific gyre",
        11: "Wind drives surface water to the right of it: Ekman transport",
        12: "Westerlies to the north and trade winds to the south push water inward under the subtropical high.",
        13: "The water sinks; floating debris stays. Five such gyres hold the five known patches.",
    }, None,
     "Numbers from the Ocean Cleanup surveys (Lebreton et al. 2018) as summarised on Wikipedia; the six-to-one ratio "
     "is "
     "from Moore et al. 2001. In the Northern Hemisphere the Ekman transport is 90° to the right of the wind stress."),
    (CARDS4, {
        2: "METHOD",
        6: "Area averages and maps from NASA Giovanni",
        7: "MERRA-2 1980–2026, MODIS-Aqua 2002–2025, NOBM model 1998–2015; CYGNSS 2018–2026.",
        17: "4 · Compare",
        18: "Other patches, and the wind",
        19: "Same tests in four other patches; virtual particles drifted with the wind-driven flow.",
    }, None,
     "Same statistics as in the neutrino-site study: deseasonalised monthly anomalies, least-squares trend with a 95 % "
     "interval, p-value corrected for lag-1 autocorrelation (Santer et al. 2000), Mann-Kendall test on yearly means."),
    (FIGURE, {
        2: "GREAT PACIFIC GARBAGE PATCH · OCEAN",
        3: "The patch is warming, and its phytoplankton is declining",
        4: "Thin: monthly anomaly. Bold: 12-month running mean. Dashed: linear trend. All six trends: p < 0.01.",
        6: "MERRA-2 1980–2026 and MODIS-Aqua 2002–2025, monthly area averages over 135–155°W, 35–42°N, via NASA "
           "Giovanni",
    }, "gpgp_ocean.png",
     "Sea surface +0.33 °C per decade since 1980; MODIS sees +0.58 °C per decade since 2002, including the marine "
     "heatwaves of 2014–15 and 2019–23. Chlorophyll −8 %, fluorescence −10 % and particulate organic carbon −6 % per "
     "decade: less phytoplankton. Less rain and more evaporation make the surface water saltier. Sea-level pressure "
     "rose 0.4 hPa per decade and the wind weakened 1.4 % per decade. Aerosols show no trend once the El Chichón and "
     "Pinatubo eruptions are accounted for."),
    (FIGURE, {
        2: "GREAT PACIFIC GARBAGE PATCH · LIFE",
        3: "The model hints at a shift from diatoms to smaller plankton",
        4: "NASA Ocean Biogeochemical Model, which assimilates satellite chlorophyll. Only coccolithophores reach p "
           "< 0.05.",
        6: "NOBM monthly 1998–2015, area average over 135–155°W, 35–42°N, via NASA Giovanni",
    }, "gpgp_plankton.png",
     "A shallower mixed layer and less nitrate are what a warmer, more stratified surface ocean does. Diatoms need "
     "nutrients; cyanobacteria and coccolithophores cope better with few. Each trend alone is weak over 18 years, but "
     "they point the same way as the satellite chlorophyll decline. With less plankton, the plastic-to-plankton ratio "
     "grows."),
    (FIGURE, {
        2: "OCEAN CURRENTS",
        3: "All five patches sit where the wind makes surface water sink",
        4: "Red: Ekman downwelling, w = curl(τ / ρf), from the 2003–2024 mean wind stress (arrows). Boxes: known "
           "patches.",
        6: "MERRA-2 wind stress over water, time-averaged map via NASA Giovanni",
    }, "ekman_pumping.png",
     "Giovanni has no ocean-current product, but the wind stress gives the wind-driven part of the surface flow, the "
     "Ekman transport. Its convergence is what traps floating debris; the large geostrophic gyre currents themselves "
     "hardly converge (Maximenko et al. 2012). Blue at the coasts and in the subpolar oceans: upwelling."),
    (FIGURE, {
        2: "FINDING PATCHES",
        3: "Wind alone gathers floating particles into the known patches",
        4: "One particle per 1° of ocean, drifted for 10 years with the Ekman velocity. Green circles: concentration "
           "maxima.",
        6: "MERRA-2 2003–2024 mean wind stress; Ekman transport τ × ẑ / (ρf) spread over 50 m",
    }, "ekman_particles.png",
     "The four strongest maxima are the Great Pacific, South Atlantic, South Pacific and Indian Ocean patches. The "
     "fifth, "
     "at 33°N 33°W, is the North Atlantic gyre, east of the surveyed patch: the model has no Gulf Stream or other "
     "geostrophic currents. Weaker maxima east of Japan (where a western Pacific patch is known), in the Tasman Sea, "
     "south of Australia and south of Madagascar are candidates. Maxima near the equator are artefacts of f → 0."),
    (FIGURE, {
        2: "OTHER PATCHES",
        3: "The North Atlantic patch shows the same signature",
        4: "Trend of the deseasonalised anomaly ± 95 % interval; pale: p ≥ 0.05. The other patches are still "
           "downloading.",
        6: "MERRA-2 1980–2026 and MODIS-Aqua 2002–2025 via NASA Giovanni; North Atlantic box 40–70°W, 25–35°N",
    }, "patch_trends.png",
     "Warming plus declining chlorophyll, fluorescence and organic carbon in both northern patches. This matches the "
     "known expansion of the least productive subtropical waters (Polovina et al. 2008). It is a climate signal of the "
     "gyres, not an effect of the plastic: none of these variables measures the plastic."),
    (FIGURE, {
        2: "POLLUTION FROM SPACE?",
        3: "The satellite microplastic product does not see the patches",
        4: "CYGNSS V3.2 varies by only ±10 % worldwide and is lowest in the trade-wind belts, not in the patches.",
        6: "CYGNSS L3 ocean microplastic concentration V3.2 (PO.DAAC), mean of monthly maps 2018–2026; 37°S–37°N only",
    }, "cygnss_mean_map.png",
     "CYGNSS infers microplastic from how much smoother the sea surface is than the wind speed predicts, "
     "ρ = 4320 exp(−12.06 × MSS anomaly) per km². Box means: 12,800–13,200 per km² in the patches, 12,650 in the "
     "control south of the Great Pacific patch; no significant trends. The pattern follows the winds, and the "
     "algorithm documents caveats at the ITCZ and for surfactants. CYGNSS also stops at 37°N, the southern edge of the "
     "Great Pacific box."),
    (CARDS4, {
        2: "SUMMARY",
        3: "What the data say",
        5: "Warming",
        6: "+0.33 °C per decade",
        7: "Since 1980 at the patch; +0.58 °C per decade since 2002 in MODIS.",
        9: "Less phytoplankton",
        10: "−8 % chlorophyll per decade",
        11: "Fluorescence −10 %, organic carbon −6 %; the same in the North Atlantic patch.",
        13: "Saltier, calmer",
        14: "Less rain, more evaporation",
        15: "Rain −6 %, evaporation +5 % per decade; weaker wind, higher pressure.",
        17: "Patches from wind",
        18: "4 of 5 patches from wind alone",
        19: "Ekman drift of virtual particles puts its strongest maxima on known patches.",
    }, None,
     "All trends quoted are significant at p < 0.01 with the autocorrelation-corrected test, except the wind (p < "
     "0.001) "
     "and the North Atlantic chlorophyll (p < 0.05)."),
    (NEXT, {
        5: "All five patches",
        6: "Finish the comparison",
        7: "Fetch the remaining patches and controls: is the plankton decline general to the gyres?",
        9: "Currents",
        10: "Add the geostrophic currents",
        11: "OSCAR or altimetry currents should move the North Atlantic maximum west, onto the patch.",
        13: "Convergence",
        14: "Is the inflow changing?",
        15: "Wind stress on the box edges gives the Ekman inflow per month since 1980; the script is ready.",
        17: "Microplastic",
        18: "Test CYGNSS against wind",
        19: "Correlate it with wind speed; compare with net-tow data (NOAA NCEI marine microplastics).",
    }, None,
     "fetch_garbage_patch.sh fetches the remaining series; garbage_patch_ekman.py computes the inflow once the edge "
     "strips are downloaded."),
]

DECK.write_bytes(subprocess.run(["git", "show", "neutrino-sites:Neutrino Sites Trends.pptx"], cwd=REPO,
                                capture_output=True, check=True).stdout)
command_file = REPO / ".deckcraft_commands.txt"


def run(commands):
    """Run DeckCraft commands on the deck and save it; the answers of the commands."""
    command_file.write_text("".join(f"{name}={json.dumps(args, ensure_ascii=False)}\n" for name, args in commands))
    out = subprocess.run(DECKCRAFT + ["run", "--in", DECK, "--cmd-file", command_file, "--save", DECK, "--print"],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if " → " in line]


for k, (template, texts, picture, notes) in enumerate(slides):
    index = TEMPLATE_SLIDES + k
    duplicated = run([("slide.duplicate", {"index": template}), ("slide.move", {"from": template + 1, "to": index})])
    slide_id = json.loads(duplicated[0].split(" → ", 1)[1])["ids"][0]
    offset = slide_id - 1  # the shape ids of a duplicated slide follow its slide id
    commands = [("slide.go", {"index": index})]
    # no line break between a number and its unit
    commands += [("text.set", {"id": offset + shape_id, "text": text.replace(" %", "\u00a0%")})
                 for shape_id, text in texts.items()]
    if picture:
        ids = [offset + 5]
        commands += [("picture.change", {"path": PLOTS + picture, "ids": ids}), ("picture.reset", {"ids": ids}),
                     ("shape.sizePosition", {"x": 64, "y": 149, "w": 832, "h": 339, "ids": ids}),
                     ("shape.altText", {"text": texts[3], "ids": ids})]
    if texts.get(2) == "SUMMARY":
        # the method slide's first card has a three-line heading; here it has two, so its body moves up
        commands.append(("shape.sizePosition", {"y": 237, "ids": [offset + 7]}))
    commands.append(("slide.notes", {"text": notes, "index": index}))
    run(commands)
    print(index, texts.get(3, ""))
run([("slide.delete", {"index": 0})] * TEMPLATE_SLIDES)
command_file.unlink()
print(DECK)
