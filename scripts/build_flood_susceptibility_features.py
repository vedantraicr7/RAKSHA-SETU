from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


INPUT = Path(
    "data/processed/"
    "raigad_habitations_environment_hydrology.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_features.gpkg"
)


print("Loading habitation environmental dataset...")

gdf = gpd.read_file(INPUT)

print("Habitations:", len(gdf))


# ---------------------------------------------------------
# Check required columns
# ---------------------------------------------------------

required = [
    "elev_mean_m",
    "slope_mean_deg",
    "dist_river_m",
    "dem_drain_mean_m",
    "pct_area_drain_250m",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
]

missing = [
    col for col in required
    if col not in gdf.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ---------------------------------------------------------
# Robust percentile scaling
# ---------------------------------------------------------

def high_score(series):
    """
    Higher raw value = higher susceptibility.

    Uses 5th-95th percentile scaling so extreme
    outliers do not dominate the entire dataset.
    """

    x = pd.to_numeric(
        series,
        errors="coerce"
    )

    low = x.quantile(0.05)
    high = x.quantile(0.95)

    if high == low:
        return pd.Series(
            np.zeros(len(x)),
            index=x.index
        )

    score = (
        (x - low) /
        (high - low)
    )

    return score.clip(0, 1)


def low_score(series):
    """
    Lower raw value = higher susceptibility.
    """

    return 1 - high_score(series)


# ---------------------------------------------------------
# Physical flood-susceptibility features
# ---------------------------------------------------------

# Lower elevation -> generally greater susceptibility
gdf["f_elevation"] = low_score(
    gdf["elev_mean_m"]
)

# Flatter terrain -> greater tendency for water accumulation
gdf["f_flatness"] = low_score(
    gdf["slope_mean_deg"]
)

# Closer to mapped CWC river -> greater susceptibility
gdf["f_river_proximity"] = low_score(
    gdf["dist_river_m"]
)

# Closer to DEM-derived drainage -> greater susceptibility
gdf["f_drain_proximity"] = low_score(
    gdf["dem_drain_mean_m"]
)

# Larger part of polygon near drainage -> greater susceptibility
gdf["f_drain_area"] = high_score(
    gdf["pct_area_drain_250m"]
)

# Higher long-term rainfall -> greater rainfall loading
gdf["f_clim_rain"] = high_score(
    gdf["clim_mean_annual_mm"]
)

# Larger historical one-day rainfall extreme
gdf["f_extreme_rain"] = high_score(
    gdf["hist_max_1day_mm"]
)


# ---------------------------------------------------------
# QA
# ---------------------------------------------------------

feature_cols = [
    "f_elevation",
    "f_flatness",
    "f_river_proximity",
    "f_drain_proximity",
    "f_drain_area",
    "f_clim_rain",
    "f_extreme_rain",
]

print("\nMissing feature values:")
print(
    gdf[feature_cols]
    .isna()
    .sum()
)

print("\nFeature statistics:")
print(
    gdf[feature_cols]
    .describe()
    .T
)


# ---------------------------------------------------------
# Temporary diagnostic mean
# ---------------------------------------------------------
#
# IMPORTANT:
# This is NOT our final flood-risk score.
#
# It is only used to inspect whether the features
# produce sensible rankings before we choose weights.
# ---------------------------------------------------------

gdf["diagnostic_mean"] = (
    gdf[feature_cols]
    .mean(axis=1)
)


# ---------------------------------------------------------
# Display highest diagnostic values
# ---------------------------------------------------------

display_cols = [
    "village",
    "subdistric",
    "vlcode",
    "total_popu",
    "elev_mean_m",
    "slope_mean_deg",
    "dist_river_m",
    "dem_drain_mean_m",
    "pct_area_drain_250m",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "diagnostic_mean",
]

print(
    "\nTop 25 diagnostic "
    "flood-susceptibility records"
)

print("=" * 120)

print(
    gdf[display_cols]
    .sort_values(
        "diagnostic_mean",
        ascending=False
    )
    .head(25)
    .to_string(index=False)
)


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

gdf.to_file(
    OUTPUT,
    layer="raigad_habitations_flood_features",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
