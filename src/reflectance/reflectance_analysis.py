
"""Compare reflectance at 531 nm across five ocean patches and their controls."""

from pathlib import Path
import argparse

import h5py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ===================================================
# 1. FILE LOCATIONS
# ===================================================

# Each entry contains:
# (patch folder, north control folder, south control folder)

OCEANS = {
    "North Pacific": (
        "gpgp",
        "north_pacific_north",
        "north_pacific_south",
    ),
    "South Pacific": (
        "south_pacific_patch",
        "south_pacific_north",
        "south_pacific_south",
    ),
    "North Atlantic": (
        "north_atlantic_patch",
        "north_atlantic_north",
        "north_atlantic_south",
    ),
    "South Atlantic": (
        "south_atlantic_patch",
        "south_atlantic_north",
        "south_atlantic_south",
    ),
    "Indian Ocean": (
        "indian_ocean_patch",
        "indian_ocean_north",
        "indian_ocean_south",
    ),
}


# ===================================================
# 2. READ MONTHLY REFLECTANCE
# ===================================================

def monthly_reflectance(file_path):
    """
    Return one area-weighted Rrs_531 value per month.

    Units: sr^-1

    Invalid pixels are excluded.
    Latitude weighting accounts for differences
    in pixel surface area.
    """

    with h5py.File(file_path, "r") as ds:

        band = ds["Rrs_531"]
        latitude = ds["lat"][:]

        if band.ndim != 3:
            raise ValueError(
                f"Unexpected dimensions in {file_path}"
            )

        # NetCDF stores calibrated reflectance as
        # packed integers. Decode the physical values.

        scale = float(band.attrs["scale_factor"][0])
        offset = float(band.attrs["add_offset"][0])
        fill = int(band.attrs["_FillValue"][0])
        valid_min = int(band.attrs["valid_min"][0])
        valid_max = int(band.attrs["valid_max"][0])

        # Decode the satellite observation dates.

        time_units = ds["time"].attrs["units"]

        if isinstance(time_units, bytes):
            time_units = time_units.decode()

        if not time_units.startswith("milliseconds since "):
            raise ValueError(
                f"Unexpected time format: {time_units}"
            )

        origin = pd.Timestamp(
            time_units.split(" since ", 1)[1]
        )

        dates = origin + pd.to_timedelta(
            ds["time"][:], unit="ms"
        )

        # Some dates are stamped at the end of the
        # previous month. This normalizes the monthly
        # timestamps in these specific NASA exports.

        months = (
            dates + pd.Timedelta(days=15)
        ).to_period("M").to_timestamp()

        if months.has_duplicates:
            raise ValueError(
                f"Duplicate months in {file_path}"
            )

        # Cosine latitude weighting is appropriate
        # for these regular latitude-longitude grids.

        weights = np.cos(
            np.deg2rad(latitude)
        )[None, :, None]

        values_by_month = []

        # Read 24 months at a time to limit RAM usage.

        for start in range(0, band.shape[0], 24):

            raw = band[start:start + 24]

            values = (
                raw.astype(np.float64) * scale + offset
            )

            # Keep valid, positive reflectance only.
            # Negative retrievals are excluded to
            # avoid nonphysical values affecting means.

            valid = (
                (raw != fill)
                & (raw >= valid_min)
                & (raw <= valid_max)
                & (values > 0)
            )

            weighted_sum = (
                np.where(valid, values, 0.0) * weights
            ).sum(axis=(1, 2))

            total_weight = (
                valid * weights
            ).sum(axis=(1, 2))

            monthly = np.divide(
                weighted_sum,
                total_weight,
                out=np.full_like(
                    weighted_sum, np.nan
                ),
                where=total_weight > 0
            )

            values_by_month.extend(monthly)

    return pd.Series(
        values_by_month,
        index=months
    )


# ===================================================
# 3. ESTIMATE UNCERTAINTY
# ===================================================

def block_bootstrap_ci(annual_differences, seed):
    """
    Estimate a 95% confidence interval for
    the average patch-control difference.

    Resample consecutive three-year blocks.
    This partially accounts for autocorrelation.

    Use 3000 bootstrap repetitions.
    """

    values = annual_differences.to_numpy()

    n = len(values)
    block = min(3, n)

    rng = np.random.default_rng(seed)

    bootstrap_means = []

    for _ in range(3000):

        sampled = []

        while len(sampled) < n:

            start = rng.integers(
                0, n - block + 1
            )

            sampled.extend(
                values[start:start + block]
            )

        bootstrap_means.append(
            np.mean(sampled[:n])
        )

    return np.quantile(
        bootstrap_means,
        [0.025, 0.975]
    )


# ===================================================
# 4. COMPARE ONE PATCH WITH ITS CONTROLS
# ===================================================

def analyze_ocean(root, ocean, folders, seed):

    series = {}

    for label, folder in zip(
        ("patch", "north", "south"),
        folders
    ):

        file_path = (
            root / folder / "reflectance_monthly.nc"
        )

        if not file_path.is_file():
            raise FileNotFoundError(file_path)

        series[label] = monthly_reflectance(
            file_path
        )

    # Match dates between all three regions.

    frame = pd.DataFrame(series).dropna()

    # Keep only complete years (12 matched months).

    counts = frame.groupby(
        frame.index.year
    ).size()

    full_years = counts[
        counts == 12
    ].index

    frame = frame[
        frame.index.year.isin(full_years)
    ].copy()

    if len(full_years) < 6:
        raise ValueError(
            f"Too few complete years for {ocean}"
        )

    # Calculate the reference reflectance.

    frame["control_mean"] = (
        frame["north"] + frame["south"]
    ) / 2

    # Monthly difference between patch and controls.

    frame["difference"] = (
        frame["patch"] - frame["control_mean"]
    )

    # Average monthly differences within each year.

    annual_difference = (
        frame["difference"]
        .groupby(frame.index.year)
        .mean()
    )

    # Confidence interval for the mean difference.

    ci_low, ci_high = block_bootstrap_ci(
        annual_difference,
        seed
    )

    # Calculate regional averages.

    patch = frame["patch"].mean()
    north = frame["north"].mean()
    south = frame["south"].mean()
    control = frame["control_mean"].mean()

    difference = patch - control

    # Return one row for the ocean.

    return {
        "ocean": ocean,
        "years": len(full_years),

        "patch_mean": patch,
        "north_mean": north,
        "south_mean": south,
        "control_mean": control,

        "difference": difference,

        "difference_pct":
            100 * difference / control,

        "vs_north_pct":
            100 * (patch - north) / north,

        "vs_south_pct":
            100 * (patch - south) / south,

        "ci95_low": ci_low,
        "ci95_high": ci_high,
    }


# ===================================================
# 5. RUN ANALYSIS ON ALL FIVE OCEANS
# ===================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to the downloaded regions folder"
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reflectance_results")
    )

    args = parser.parse_args()

    root = args.data_dir.expanduser().resolve()

    if not root.is_dir():
        parser.error(
            f"Folder not found: {root}"
        )

    args.out.mkdir(
        parents=True,
        exist_ok=True
    )

    # Analyze the five patch-control groups.

    results = []

    for i, (ocean, folders) in enumerate(
        OCEANS.items()
    ):

        result = analyze_ocean(
            root,
            ocean,
            folders,
            seed=2026 + i
        )

        results.append(result)

    summary = pd.DataFrame(results)

    # Save numerical results.

    summary.to_csv(
        args.out / "five_oceans_reflectance.csv",
        index=False
    )

    # Print a readable summary.

    print("\nReflectance at 531 nm (sr^-1)\n")

    columns = [
        "ocean",
        "years",
        "patch_mean",
        "north_mean",
        "south_mean",
        "difference_pct",
        "ci95_low",
        "ci95_high",
    ]

    print(
        summary[columns]
        .round(6)
        .to_string(index=False)
    )

    # Create a comparison graph.

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    ax.bar(
        summary["ocean"],
        summary["difference_pct"]
    )

    ax.axhline(
        0,
        color="black",
        linewidth=1
    )

    ax.set_ylabel(
        "Patch vs average control (%)"
    )

    ax.set_title(
        "531 nm reflectance: five ocean patches"
    )

    ax.tick_params(
        axis="x",
        rotation=20
    )

    fig.tight_layout()

    fig.savefig(
        args.out / "five_oceans_reflectance.png",
        dpi=160
    )

    plt.close(fig)

    print(
        f"\nResults saved in: "
        f"{args.out.resolve()}"
    )


if __name__ == "__main__":
    main()