"""Plot style shared by the plot scripts (as plot_trends.py on the neutrino-sites branch)."""
from pathlib import Path

import matplotlib.pyplot as plt

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
SLIDE_SIZE = (13.87, 5.65)  # inches; at 120 dpi 1664 px wide: the 832 x 339 pt figure area of the slides
SHORT_NAMES = {"gpgp": "Great Pacific", "north_atlantic_patch": "North Atlantic",
               "south_pacific_patch": "South Pacific", "south_atlantic_patch": "South Atlantic",
               "indian_ocean_patch": "Indian Ocean",
               "north_pacific_north": "N. Pacific, north\n(control)",
               "north_pacific_south": "N. Pacific, south\n(control)"}


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
