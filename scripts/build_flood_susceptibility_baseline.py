from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


INPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_features.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_susceptibility.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/"
    "raigad_flood_susceptibility_ranking.csv"
)


print("Loading flood features...")

gdf = gpd.read_file(INPUT)

print("Habitations:", len(gdf))


# =========================================================
# 1. COMPONENT SCORES
# =========================================================

# Terrain:
# correlated elevation + flatness treated as one component
gdf["terrain_component"] = (
    gdf["f_elevation"] +
    gdf["f_flatness"]
) / 2


# DEM drainage:
# correlated proximity + area-near-drainage
# treated as one component
gdf["drainage_component"] = (
    gdf["f_drain_proximity"] +
    gdf["f_drain_area"]
) / 2


# Independent mapped-river information
gdf["river_component"] = (
    gdf["f_river_proximity"]
)


# Rainfall:
# long-term climatology + historical daily extreme
gdf["rainfall_component"] = (
    gdf["f_clim_rain"] +
    gdf["f_extreme_rain"]
) / 2


# =========================================================
# 2. BASELINE SUSCEPTIBILITY
# =========================================================
#
# Equal weighting across PHYSICAL COMPONENTS.
#
# This is a baseline model, NOT a calibrated
# probability of flooding.
# =========================================================

gdf["flood_susceptibility"] = (
      0.25 * gdf["terrain_component"]
    + 0.25 * gdf["drainage_component"]
    + 0.25 * gdf["river_component"]
    + 0.25 * gdf["rainfall_component"]
)


# Convert to easier-to-read 0-100 scale
gdf["flood_susceptibility_100"] = (
    gdf["flood_susceptibility"] * 100
)


# =========================================================
# 3. RELATIVE SUSCEPTIBILITY CLASSES
# =========================================================
#
# Quintiles = relative ranking within Raigad.
# They are NOT official flood-hazard classes.
# =========================================================

labels = [
    "Very Low",
    "Low",
    "Moderate",
    "High",
    "Very High",
]

gdf["susceptibility_class"] = pd.qcut(
    gdf["flood_susceptibility"],
    q=5,
    labels=labels,
    duplicates="drop"
)


# Percentile rank
gdf["susceptibility_percentile"] = (
    gdf["flood_susceptibility"]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)


# =========================================================
# 4. QA
# =========================================================

component_cols = [
    "terrain_component",
    "drainage_component",
    "river_component",
    "rainfall_component",
    "flood_susceptibility",
]

print("\nMissing values:")
print(
    gdf[component_cols]
    .isna()
    .sum()
)


print("\nComponent statistics:")
print(
    gdf[component_cols]
    .describe()
    .T
)


print("\nSusceptibility classes:")
print(
    gdf["susceptibility_class"]
    .value_counts()
    .sort_index()
)


# =========================================================
# 5. TOP HABITATIONS
# =========================================================

display_cols = [
    "village",
    "subdistric",
    "vlcode",
    "total_popu",
    "terrain_component",
    "drainage_component",
    "river_component",
    "rainfall_component",
    "flood_susceptibility_100",
    "susceptibility_percentile",
    "susceptibility_class",
]


print("\nTOP 30 FLOOD-SUSCEPTIBILITY HABITATIONS")
print("=" * 120)

top30 = (
    gdf
    .sort_values(
        "flood_susceptibility",
        ascending=False
    )
    .head(30)
)

print(
    top30[display_cols]
    .to_string(index=False)
)


# =========================================================
# 6. SUBDISTRICT SUMMARY
# =========================================================

summary = (
    gdf.groupby("subdistric")
    .agg(
        habitations=(
            "vlcode",
            "count"
        ),
        mean_susceptibility=(
            "flood_susceptibility_100",
            "mean"
        ),
        median_susceptibility=(
            "flood_susceptibility_100",
            "median"
        ),
        very_high_count=(
            "susceptibility_class",
            lambda x: (
                x == "Very High"
            ).sum()
        ),
    )
    .sort_values(
        "mean_susceptibility",
        ascending=False
    )
)


print("\nSUBDISTRICT SUMMARY")
print("=" * 90)

print(
    summary
    .round(2)
    .to_string()
)


# =========================================================
# 7. SAVE
# =========================================================

gdf.to_file(
    OUTPUT,
    layer="flood_susceptibility",
    driver="GPKG"
)


csv_cols = [
    c for c in display_cols
    if c in gdf.columns
]

(
    gdf
    .sort_values(
        "flood_susceptibility_100",
        ascending=False
    )[csv_cols]
    .to_csv(
        CSV_OUTPUT,
        index=False
    )
)


print("\nSaved:")
print(OUTPUT)
print(CSV_OUTPUT)

print("\nDONE.")
