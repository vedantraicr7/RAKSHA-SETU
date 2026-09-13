from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio


TRAINING = Path(
    "data/processed/landslide/"
    "landslide_training_environment.gpkg"
)

LULC = Path(
    "data/processed/landslide/"
    "raigad_worldcover_2021.tif"
)

OUTPUT = Path(
    "data/processed/landslide/"
    "landslide_training_environment_lulc.gpkg"
)


CLASS_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    80: "Permanent water",
    90: "Herbaceous wetland",
    95: "Mangroves",
}


print("Loading training data...")

gdf = gpd.read_file(TRAINING)

print("Training points:", len(gdf))


with rasterio.open(LULC) as src:

    pts = gdf.to_crs(src.crs)

    coords = [
        (geom.x, geom.y)
        for geom in pts.geometry
    ]

    values = []

    for arr in src.sample(coords):

        value = int(arr[0])

        if value == 0:
            values.append(np.nan)
        else:
            values.append(value)


gdf["lulc_code"] = values

gdf["lulc_class"] = (
    gdf["lulc_code"]
    .map(CLASS_NAMES)
)


print("\nMissing LULC:")
print(
    gdf["lulc_code"]
    .isna()
    .sum()
)


print("\nLULC COUNTS — CONTROLS")
print("=" * 70)

print(
    gdf.loc[
        gdf["landslide"] == 0,
        "lulc_class"
    ]
    .value_counts()
    .to_string()
)


print("\nLULC COUNTS — LANDSLIDES")
print("=" * 70)

print(
    gdf.loc[
        gdf["landslide"] == 1,
        "lulc_class"
    ]
    .value_counts()
    .to_string()
)


print("\nLANDSLIDE RATE BY LULC CLASS")
print("=" * 80)

summary = (
    gdf
    .dropna(
        subset=["lulc_class"]
    )
    .groupby("lulc_class")
    .agg(
        total_points=(
            "landslide",
            "count"
        ),
        landslides=(
            "landslide",
            "sum"
        ),
    )
)

summary["landslide_rate_pct"] = (
    summary["landslides"]
    /
    summary["total_points"]
    * 100
)

summary = summary.sort_values(
    "landslide_rate_pct",
    ascending=False
)

print(
    summary
    .round(2)
    .to_string()
)


gdf.to_file(
    OUTPUT,
    layer="training_environment_lulc",
    driver="GPKG"
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
