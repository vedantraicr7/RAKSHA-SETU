from pathlib import Path

import geopandas as gpd
import pandas as pd


TRAINING = Path(
    "data/processed/landslide/"
    "landslide_training_environment_lulc.gpkg"
)

ROADS = Path(
    "data/processed/landslide/"
    "raigad_roads.gpkg"
)

OUTPUT = Path(
    "data/processed/landslide/"
    "landslide_training_full.gpkg"
)


print("Loading training points...")

gdf = gpd.read_file(TRAINING)

print("Training points:", len(gdf))


print("Loading roads...")

roads = gpd.read_file(
    ROADS,
    layer="roads"
)

print("Road features:", len(roads))


# --------------------------------------------------
# Use metric CRS
# --------------------------------------------------

TARGET_CRS = "EPSG:32643"

pts = gdf.to_crs(TARGET_CRS)
roads = roads.to_crs(TARGET_CRS)


# --------------------------------------------------
# Nearest road
# --------------------------------------------------

print("Calculating nearest-road distances...")

joined = gpd.sjoin_nearest(
    pts,
    roads[
        [
            "highway",
            "name",
            "geometry"
        ]
    ],
    how="left",
    distance_col="dist_road_m"
)


# Some points may tie to multiple equally near roads.
# Keep only the nearest/first match per original point.

joined = (
    joined
    .reset_index()
    .sort_values(
        [
            "index",
            "dist_road_m"
        ]
    )
    .drop_duplicates(
        subset="index",
        keep="first"
    )
    .set_index("index")
    .reindex(pts.index)
)


gdf["dist_road_m"] = (
    joined["dist_road_m"].to_numpy()
)

gdf["nearest_road_type"] = (
    joined["highway"].to_numpy()
)

gdf["nearest_road_name"] = (
    joined["name"].to_numpy()
)


# --------------------------------------------------
# QA
# --------------------------------------------------

print("\nMissing road distances:")
print(
    gdf["dist_road_m"]
    .isna()
    .sum()
)


print("\nROAD DISTANCE COMPARISON")
print("=" * 80)

summary = (
    gdf
    .groupby("landslide")[
        "dist_road_m"
    ]
    .agg(
        [
            "count",
            "mean",
            "median",
            "std",
            "min",
            "max",
        ]
    )
)

print(summary)


print("\nROAD PROXIMITY THRESHOLDS")
print("=" * 80)

for threshold in [
    25,
    50,
    100,
    250,
    500,
    1000
]:

    print(
        f"\nWithin {threshold} m"
    )

    for cls in [0, 1]:

        subset = gdf[
            gdf["landslide"] == cls
        ]

        pct = (
            (
                subset["dist_road_m"]
                <= threshold
            )
            .mean()
            * 100
        )

        label = (
            "Control"
            if cls == 0
            else "Landslide"
        )

        print(
            f"{label:10s}: "
            f"{pct:6.2f}%"
        )


print("\nNearest road classes at landslides:")
print(
    gdf.loc[
        gdf["landslide"] == 1,
        "nearest_road_type"
    ]
    .value_counts(dropna=False)
    .to_string()
)


# --------------------------------------------------
# Save
# --------------------------------------------------

gdf.to_file(
    OUTPUT,
    layer="training_full",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
