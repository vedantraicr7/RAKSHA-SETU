from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterstats import zonal_stats


HABITATIONS = Path(
    "data/processed/raigad_habitations.gpkg"
)

DEM = Path(
    "data/processed/terrain/raigad_dem_utm.tif"
)

SLOPE = Path(
    "data/processed/terrain/raigad_slope.tif"
)

OUTPUT = Path(
    "data/processed/raigad_habitations_terrain.gpkg"
)


print("Loading habitations...")

villages = gpd.read_file(HABITATIONS)

print("Habitations:", len(villages))


# --------------------------------------------------
# Reproject villages to raster CRS
# --------------------------------------------------

with rasterio.open(DEM) as src:
    raster_crs = src.crs

print("Terrain CRS:", raster_crs)

villages_utm = villages.to_crs(raster_crs)


# --------------------------------------------------
# Helper percentile functions
# --------------------------------------------------

def percentile_10(values):
    values = values.compressed()
    if len(values) == 0:
        return np.nan
    return float(np.percentile(values, 10))


def percentile_90(values):
    values = values.compressed()
    if len(values) == 0:
        return np.nan
    return float(np.percentile(values, 90))


def pct_ge_15(values):
    values = values.compressed()
    if len(values) == 0:
        return np.nan
    return float(np.mean(values >= 15) * 100)


def pct_ge_25(values):
    values = values.compressed()
    if len(values) == 0:
        return np.nan
    return float(np.mean(values >= 25) * 100)


def pct_ge_35(values):
    values = values.compressed()
    if len(values) == 0:
        return np.nan
    return float(np.mean(values >= 35) * 100)


# --------------------------------------------------
# Elevation statistics
# --------------------------------------------------

print("\nCalculating elevation statistics...")

elevation_stats = zonal_stats(
    villages_utm,
    DEM,
    stats=[
        "min",
        "max",
        "mean"
    ],
    add_stats={
        "p10": percentile_10,
        "p90": percentile_90
    },
    nodata=-9999
)


# --------------------------------------------------
# Slope statistics
# --------------------------------------------------

print("Calculating slope statistics...")

slope_stats = zonal_stats(
    villages_utm,
    SLOPE,
    stats=[
        "mean",
        "max"
    ],
    add_stats={
        "p90": percentile_90,
        "pct_ge15": pct_ge_15,
        "pct_ge25": pct_ge_25,
        "pct_ge35": pct_ge_35
    },
    nodata=-9999
)


# --------------------------------------------------
# Attach results
# --------------------------------------------------

villages["elev_min_m"] = [
    x["min"] for x in elevation_stats
]

villages["elev_max_m"] = [
    x["max"] for x in elevation_stats
]

villages["elev_mean_m"] = [
    x["mean"] for x in elevation_stats
]

villages["elev_p10_m"] = [
    x["p10"] for x in elevation_stats
]

villages["elev_p90_m"] = [
    x["p90"] for x in elevation_stats
]

villages["slope_mean_deg"] = [
    x["mean"] for x in slope_stats
]

villages["slope_max_deg"] = [
    x["max"] for x in slope_stats
]

villages["slope_p90_deg"] = [
    x["p90"] for x in slope_stats
]

villages["pct_slope_ge15"] = [
    x["pct_ge15"] for x in slope_stats
]

villages["pct_slope_ge25"] = [
    x["pct_ge25"] for x in slope_stats
]

villages["pct_slope_ge35"] = [
    x["pct_ge35"] for x in slope_stats
]


# --------------------------------------------------
# QA
# --------------------------------------------------

terrain_columns = [
    "elev_mean_m",
    "slope_mean_deg",
    "pct_slope_ge15",
    "pct_slope_ge25",
    "pct_slope_ge35"
]

print("\nMissing terrain values:")
print(
    villages[terrain_columns]
    .isna()
    .sum()
)

print("\nElevation summary:")
print(
    villages["elev_mean_m"]
    .describe()
)

print("\nSlope summary:")
print(
    villages["slope_mean_deg"]
    .describe()
)


# --------------------------------------------------
# Save
# --------------------------------------------------

villages.to_file(
    OUTPUT,
    layer="raigad_habitations_terrain",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)
