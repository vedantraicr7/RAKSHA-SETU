from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio


LANDSLIDES = Path(
    "data/processed/landslide/"
    "gsi_raigad_landslides.gpkg"
)

SLOPE = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

DEM = Path(
    "data/processed/terrain/"
    "raigad_dem_utm.tif"
)

OUTPUT = Path(
    "data/processed/landslide/"
    "gsi_raigad_landslides_terrain.gpkg"
)


print("Loading GSI landslides...")

gdf = gpd.read_file(LANDSLIDES)

print("Landslides:", len(gdf))


def sample_raster(gdf, raster_path, field_name):

    with rasterio.open(raster_path) as src:

        pts = gdf.to_crs(src.crs)

        coords = [
            (geom.x, geom.y)
            for geom in pts.geometry
        ]

        values = []

        for value in src.sample(coords):

            v = float(value[0])

            if src.nodata is not None and v == src.nodata:
                values.append(np.nan)
            else:
                values.append(v)

        gdf[field_name] = values

    return gdf


gdf = sample_raster(
    gdf,
    SLOPE,
    "slope_deg"
)

gdf = sample_raster(
    gdf,
    DEM,
    "elevation_m"
)


print("\nMissing sampled values:")
print(
    gdf[
        [
            "slope_deg",
            "elevation_m"
        ]
    ]
    .isna()
    .sum()
)


print("\nLANDSLIDE SLOPE STATISTICS")
print("=" * 70)

print(
    gdf["slope_deg"]
    .describe()
)


print("\nSlope thresholds:")

for threshold in [5, 10, 15, 20, 25, 30, 35]:

    count = int(
        (gdf["slope_deg"] >= threshold)
        .sum()
    )

    pct = (
        count / len(gdf) * 100
    )

    print(
        f">= {threshold:2d}° : "
        f"{count:3d} "
        f"({pct:.2f}%)"
    )


print("\nLANDSLIDE ELEVATION STATISTICS")
print("=" * 70)

print(
    gdf["elevation_m"]
    .describe()
)


print("\nSteepest 20 GSI landslides:")
print("=" * 90)

print(
    gdf[
        [
            "slide_no",
            "latitude",
            "longitude",
            "slope_deg",
            "elevation_m"
        ]
    ]
    .sort_values(
        "slope_deg",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)


gdf.to_file(
    OUTPUT,
    layer="gsi_landslides_terrain",
    driver="GPKG"
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
