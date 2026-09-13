from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterstats import zonal_stats


HABITATIONS = Path(
    "data/processed/"
    "raigad_habitations_environment_hydro.gpkg"
)

DISTANCE_RASTER = Path(
    "data/processed/hydrology/"
    "raigad_distance_to_drainage_m.tif"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_environment_hydrology.gpkg"
)


print("Loading habitations...")

hab = gpd.read_file(HABITATIONS)

print("Habitations:", len(hab))


with rasterio.open(DISTANCE_RASTER) as src:
    raster_crs = src.crs

hab_metric = hab.to_crs(
    raster_crs
)


# --------------------------------------------------
# Custom statistics
# --------------------------------------------------

def p10(values):

    values = values.compressed()

    if len(values) == 0:
        return np.nan

    return float(
        np.percentile(values, 10)
    )


def pct_le_100(values):

    values = values.compressed()

    if len(values) == 0:
        return np.nan

    return float(
        np.mean(values <= 100) * 100
    )


def pct_le_250(values):

    values = values.compressed()

    if len(values) == 0:
        return np.nan

    return float(
        np.mean(values <= 250) * 100
    )


def pct_le_500(values):

    values = values.compressed()

    if len(values) == 0:
        return np.nan

    return float(
        np.mean(values <= 500) * 100
    )


# --------------------------------------------------
# Zonal statistics
# --------------------------------------------------

print(
    "\nCalculating habitation "
    "drainage-proximity metrics..."
)

stats = zonal_stats(
    hab_metric,
    DISTANCE_RASTER,

    stats=[
        "min",
        "mean"
    ],

    add_stats={
        "p10": p10,
        "pct_le100": pct_le_100,
        "pct_le250": pct_le_250,
        "pct_le500": pct_le_500
    },

    nodata=-9999
)


# --------------------------------------------------
# Attach metrics
# --------------------------------------------------

hab["dem_drain_min_m"] = [
    x["min"] for x in stats
]

hab["dem_drain_mean_m"] = [
    x["mean"] for x in stats
]

hab["dem_drain_p10_m"] = [
    x["p10"] for x in stats
]

hab["pct_area_drain_100m"] = [
    x["pct_le100"] for x in stats
]

hab["pct_area_drain_250m"] = [
    x["pct_le250"] for x in stats
]

hab["pct_area_drain_500m"] = [
    x["pct_le500"] for x in stats
]


# --------------------------------------------------
# QA
# --------------------------------------------------

columns = [
    "dem_drain_min_m",
    "dem_drain_mean_m",
    "dem_drain_p10_m",
    "pct_area_drain_100m",
    "pct_area_drain_250m",
    "pct_area_drain_500m"
]

print("\nMissing values:")

print(
    hab[columns]
    .isna()
    .sum()
)

print("\nMinimum drainage distance:")

print(
    hab["dem_drain_min_m"]
    .describe()
)

print("\n% area within 250 m of drainage:")

print(
    hab["pct_area_drain_250m"]
    .describe()
)


print(
    "\nTop 20 habitations by "
    "area close to drainage"
)

print("=" * 90)

display = [
    "village",
    "subdistric",
    "vlcode",
    "total_popu",
    "dem_drain_min_m",
    "pct_area_drain_100m",
    "pct_area_drain_250m",
    "pct_area_drain_500m",
    "dist_river_m"
]

print(
    hab[display]
    .sort_values(
        "pct_area_drain_250m",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)


# --------------------------------------------------
# Save
# --------------------------------------------------

hab.to_file(
    OUTPUT,
    layer="raigad_habitations_environment_hydrology",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
