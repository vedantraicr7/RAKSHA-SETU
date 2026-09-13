from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from rasterio.features import shapes
from scipy.ndimage import label
from shapely.geometry import shape

INPUT = Path(
    "data/processed/relocation/"
    "raigad_safe_land_strict.tif"
)

OUTPUT = Path(
    "data/processed/relocation/"
    "raigad_relocation_candidate_sites.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/relocation/"
    "raigad_relocation_candidate_sites.csv"
)


# ==========================================================
# SETTINGS
# ==========================================================

MIN_AREA_HA = 2.0


print("Loading strict safe-land mask...")


with rasterio.open(INPUT) as src:

    safe = src.read(1)

    transform = src.transform
    crs = src.crs

    pixel_area_m2 = (
        abs(transform.a)
        *
        abs(transform.e)
    )


safe_mask = safe == 1


print(
    "Safe pixels:",
    int(safe_mask.sum())
)


# ==========================================================
# CONNECTED COMPONENTS
# ==========================================================
#
# 8-neighbour connectivity:
# diagonal pixels are considered connected.
# ==========================================================

structure = np.ones(
    (3, 3),
    dtype=np.uint8
)


print(
    "Identifying contiguous safe-land patches..."
)


labels, num_features = label(
    safe_mask,
    structure=structure
)


print(
    "Raw connected patches:",
    num_features
)


# ==========================================================
# PATCH AREAS
# ==========================================================

counts = np.bincount(
    labels.ravel()
)


# label 0 = background
patch_ids = np.arange(
    1,
    len(counts)
)


patch_pixels = counts[1:]


patch_area_m2 = (
    patch_pixels
    *
    pixel_area_m2
)


patch_area_ha = (
    patch_area_m2
    /
    10000
)


keep_ids = patch_ids[
    patch_area_ha
    >= MIN_AREA_HA
]


print(
    f"Patches >= {MIN_AREA_HA} ha:",
    len(keep_ids)
)


# ==========================================================
# FILTER RASTER
# ==========================================================

keep_lookup = np.zeros(
    len(counts),
    dtype=np.uint8
)

keep_lookup[
    keep_ids
] = 1


filtered = keep_lookup[
    labels
]


print(
    "Pixels retained:",
    int(filtered.sum())
)


# ==========================================================
# POLYGONIZE
# ==========================================================

print(
    "Converting retained patches "
    "to polygons..."
)


records = []

keep_set = set(
    int(x)
    for x in keep_ids
)


for geom, value in shapes(
    labels.astype(np.int32),
    mask=filtered.astype(bool),
    transform=transform
):

    patch_id = int(value)

    if patch_id not in keep_set:
        continue

    records.append(
        {
            "patch_id": patch_id,
            "geometry": shape(geom),
        }
    )


gdf = gpd.GeoDataFrame(
    records,
    geometry="geometry",
    crs=crs
)


# ==========================================================
# DISSOLVE
# ==========================================================

gdf = (
    gdf
    .dissolve(
        by="patch_id"
    )
    .reset_index()
)


# ==========================================================
# AREA
# ==========================================================

gdf["area_m2"] = (
    gdf.geometry.area
)

gdf["area_ha"] = (
    gdf["area_m2"]
    /
    10000
)

gdf["area_km2"] = (
    gdf["area_m2"]
    /
    1_000_000
)


# ==========================================================
# BASIC SIZE CLASS
# ==========================================================

def size_class(area_ha):

    if area_ha >= 50:
        return "Very Large"

    if area_ha >= 20:
        return "Large"

    if area_ha >= 10:
        return "Medium"

    if area_ha >= 5:
        return "Small"

    return "Very Small"


gdf["site_size_class"] = (
    gdf["area_ha"]
    .apply(size_class)
)


# ==========================================================
# CENTROIDS
# ==========================================================

centroids = (
    gdf.geometry
    .centroid
)


gdf["centroid_x"] = (
    centroids.x
)

gdf["centroid_y"] = (
    centroids.y
)


# ==========================================================
# RANK BY AREA
# ==========================================================

gdf["area_rank"] = (
    gdf["area_ha"]
    .rank(
        ascending=False,
        method="min"
    )
    .astype(int)
)


gdf = (
    gdf
    .sort_values(
        "area_ha",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


# ==========================================================
# QA
# ==========================================================

print(
    "\nCANDIDATE SITE SUMMARY"
)

print("=" * 80)


print(
    "Candidate sites:",
    len(gdf)
)


print(
    "Total retained area:",
    round(
        gdf["area_km2"].sum(),
        3
    ),
    "km²"
)


print(
    "\nSize classes:"
)

print(
    gdf[
        "site_size_class"
    ]
    .value_counts()
)


print(
    "\nArea statistics (hectares):"
)

print(
    gdf[
        "area_ha"
    ]
    .describe()
)


# ==========================================================
# TOP SITES
# ==========================================================

display_cols = [
    "patch_id",
    "area_rank",
    "area_ha",
    "area_km2",
    "site_size_class",
    "centroid_x",
    "centroid_y",
]


print(
    "\nTOP 30 LARGEST "
    "STRICT CANDIDATE SITES"
)

print("=" * 100)


print(
    gdf[
        display_cols
    ]
    .head(30)
    .to_string(
        index=False
    )
)


# ==========================================================
# SAVE
# ==========================================================

gdf.to_file(
    OUTPUT,
    layer="candidate_sites",
    driver="GPKG"
)


gdf.drop(
    columns="geometry"
).to_csv(
    CSV_OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)
print(CSV_OUTPUT)

print("\nDONE.")
