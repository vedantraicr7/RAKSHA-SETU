from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import Point


LANDSLIDES = Path(
    "data/processed/landslide/gsi_raigad_landslides_terrain.gpkg"
)

DISTRICT = Path(
    "data/processed/raigad_district.gpkg"
)

SLOPE = Path(
    "data/processed/terrain/raigad_slope.tif"
)

DEM = Path(
    "data/processed/terrain/raigad_dem_utm.tif"
)

OUTPUT = Path(
    "data/processed/landslide/landslide_training_terrain.gpkg"
)

RANDOM_SEED = 42
N_CONTROLS = 1000
EXCLUSION_DISTANCE_M = 500


print("Loading landslides...")

landslides = gpd.read_file(LANDSLIDES)

with rasterio.open(SLOPE) as src:
    target_crs = src.crs

landslides = landslides.to_crs(target_crs)

landslides["landslide"] = 1


print("Loading district boundary...")

district = gpd.read_file(DISTRICT).to_crs(target_crs)

district_geom = district.geometry.union_all()


print("Creating landslide exclusion zone...")

exclusion = landslides.geometry.buffer(
    EXCLUSION_DISTANCE_M
).union_all()


# ---------------------------------------------------------
# RANDOM CONTROL POINTS
# ---------------------------------------------------------

print("Generating control points...")

rng = np.random.default_rng(RANDOM_SEED)

minx, miny, maxx, maxy = district_geom.bounds

points = []

attempts = 0
max_attempts = 500000

while len(points) < N_CONTROLS and attempts < max_attempts:

    x = rng.uniform(minx, maxx)
    y = rng.uniform(miny, maxy)

    p = Point(x, y)

    attempts += 1

    if not district_geom.contains(p):
        continue

    if exclusion.contains(p):
        continue

    points.append(p)


if len(points) < N_CONTROLS:
    raise RuntimeError(
        f"Only generated {len(points)} controls."
    )


controls = gpd.GeoDataFrame(
    {
        "landslide": [0] * len(points)
    },
    geometry=points,
    crs=target_crs
)


print("Controls generated:", len(controls))
print("Attempts:", attempts)


# ---------------------------------------------------------
# RASTER SAMPLING
# ---------------------------------------------------------

def sample_raster(gdf, raster_path, field):

    with rasterio.open(raster_path) as src:

        pts = gdf.to_crs(src.crs)

        coords = [
            (geom.x, geom.y)
            for geom in pts.geometry
        ]

        vals = []

        for arr in src.sample(coords):

            value = float(arr[0])

            if (
                src.nodata is not None
                and value == src.nodata
            ):
                vals.append(np.nan)
            else:
                vals.append(value)

    gdf[field] = vals

    return gdf


controls = sample_raster(
    controls,
    SLOPE,
    "slope_deg"
)

controls = sample_raster(
    controls,
    DEM,
    "elevation_m"
)


# ---------------------------------------------------------
# COMBINE
# ---------------------------------------------------------

landslides = landslides[
    [
        "landslide",
        "slope_deg",
        "elevation_m",
        "geometry"
    ]
].copy()

controls = controls[
    [
        "landslide",
        "slope_deg",
        "elevation_m",
        "geometry"
    ]
].copy()

training = pd.concat(
    [landslides, controls],
    ignore_index=True
)

training = gpd.GeoDataFrame(
    training,
    geometry="geometry",
    crs=target_crs
)


print("\nCLASS COUNTS")
print("=" * 70)

print(
    training["landslide"]
    .value_counts()
    .sort_index()
)


print("\nTERRAIN COMPARISON")
print("=" * 70)

summary = (
    training
    .groupby("landslide")[
        [
            "slope_deg",
            "elevation_m"
        ]
    ]
    .agg(
        [
            "count",
            "mean",
            "median",
            "std"
        ]
    )
)

print(summary)


print("\nSLOPE THRESHOLD COMPARISON")
print("=" * 70)

for threshold in [5, 10, 15, 20, 25, 30]:

    print(
        f"\nSlope >= {threshold}°"
    )

    for cls in [0, 1]:

        subset = training[
            training["landslide"] == cls
        ]

        pct = (
            (subset["slope_deg"] >= threshold)
            .mean()
            * 100
        )

        label = (
            "Control"
            if cls == 0
            else "Landslide"
        )

        print(
            f"{label:10s}: {pct:6.2f}%"
        )


training.to_file(
    OUTPUT,
    layer="training_terrain",
    driver="GPKG"
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
