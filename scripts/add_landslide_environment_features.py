from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio


TRAINING = Path(
    "data/processed/landslide/"
    "landslide_training_terrain.gpkg"
)

RAINFALL = Path(
    "data/processed/"
    "raigad_rainfall_climatology_1995_2024.gpkg"
)

DRAIN_DIST = Path(
    "data/processed/hydrology/"
    "raigad_distance_to_drainage_m.tif"
)

FLOW_ACC = Path(
    "data/processed/hydrology/"
    "raigad_flow_accumulation.tif"
)

OUTPUT = Path(
    "data/processed/landslide/"
    "landslide_training_environment.gpkg"
)


print("Loading training data...")

gdf = gpd.read_file(TRAINING)

print("Training points:", len(gdf))


# ============================================================
# RAINFALL FEATURES
# ============================================================

print("Loading rainfall climatology...")

rain = gpd.read_file(RAINFALL)

points_wgs = gdf.to_crs("EPSG:4326")
rain = rain.to_crs("EPSG:4326")

rain_cols = [
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "annual_cv_pct",
    "geometry",
]

joined = gpd.sjoin(
    points_wgs,
    rain[rain_cols],
    how="left",
    predicate="within"
)

# Equal-boundary cases can occasionally duplicate rows
joined = (
    joined
    .groupby(joined.index)
    .first()
    .reindex(points_wgs.index)
)

gdf["clim_mean_annual_mm"] = (
    joined["clim_mean_annual_mm"].to_numpy()
)

gdf["hist_max_1day_mm"] = (
    joined["hist_max_1day_mm"].to_numpy()
)

gdf["annual_cv_pct"] = (
    joined["annual_cv_pct"].to_numpy()
)


# ============================================================
# RASTER SAMPLER
# ============================================================

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


print("Sampling drainage distance...")

gdf = sample_raster(
    gdf,
    DRAIN_DIST,
    "dist_drainage_m"
)


print("Sampling flow accumulation...")

gdf = sample_raster(
    gdf,
    FLOW_ACC,
    "flow_acc_cells"
)


# Log transform because flow accumulation is extremely skewed
gdf["log_flow_acc"] = np.log1p(
    gdf["flow_acc_cells"]
)


# ============================================================
# QA
# ============================================================

features = [
    "slope_deg",
    "elevation_m",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "annual_cv_pct",
    "dist_drainage_m",
    "flow_acc_cells",
    "log_flow_acc",
]

print("\nMissing values:")
print(
    gdf[features]
    .isna()
    .sum()
)


print("\nENVIRONMENT COMPARISON")
print("=" * 100)

summary = (
    gdf
    .groupby("landslide")[features]
    .agg(
        [
            "mean",
            "median"
        ]
    )
)

print(summary)


# ============================================================
# SIMPLE EFFECT CHECKS
# ============================================================

print("\nMEDIAN DIFFERENCES")
print("=" * 80)

for feature in features:

    control = (
        gdf.loc[
            gdf["landslide"] == 0,
            feature
        ]
        .median()
    )

    slide = (
        gdf.loc[
            gdf["landslide"] == 1,
            feature
        ]
        .median()
    )

    print(
        f"{feature:25s} "
        f"Control={control:10.3f}  "
        f"Landslide={slide:10.3f}"
    )


# ============================================================
# SAVE
# ============================================================

gdf.to_file(
    OUTPUT,
    layer="training_environment",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
