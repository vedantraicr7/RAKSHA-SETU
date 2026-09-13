from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling
from scipy.ndimage import distance_transform_edt, uniform_filter


# ============================================================
# INPUTS
# ============================================================

DEM = Path(
    "data/processed/terrain/"
    "raigad_dem_utm.tif"
)

SLOPE = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

DISTRICT = Path(
    "data/processed/"
    "raigad_district.gpkg"
)

RIVERS = Path(
    "data/processed/"
    "raigad_river_network.gpkg"
)

DRAIN_DIST = Path(
    "data/processed/hydrology/"
    "raigad_distance_to_drainage_m.tif"
)

CLIM_RAIN = Path(
    "data/processed/landslide/predictors/"
    "clim_mean_annual_mm.tif"
)

EXTREME_RAIN = Path(
    "data/processed/landslide/predictors/"
    "hist_max_1day_mm.tif"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_flood_susceptibility.tif"
)


# ============================================================
# MASTER GRID
# ============================================================

print("Loading master grid...")

with rasterio.open(SLOPE) as src:

    slope = src.read(1).astype(
        np.float32
    )

    profile = src.profile.copy()

    transform = src.transform
    crs = src.crs

    height = src.height
    width = src.width

    slope_nodata = src.nodata


with rasterio.open(DEM) as src:

    elevation = src.read(1).astype(
        np.float32
    )

    dem_nodata = src.nodata


terrain_valid = np.isfinite(slope)

if slope_nodata is not None:
    terrain_valid &= (
        slope != slope_nodata
    )

if dem_nodata is not None:
    terrain_valid &= (
        elevation != dem_nodata
    )


# ============================================================
# DISTRICT MASK
# ============================================================

district = gpd.read_file(
    DISTRICT
).to_crs(crs)

district_mask = rasterize(
    [
        (geom, 1)
        for geom in district.geometry
        if geom is not None
        and not geom.is_empty
    ],
    out_shape=(
        height,
        width
    ),
    transform=transform,
    fill=0,
    dtype="uint8",
).astype(bool)


analysis_mask = (
    district_mask
    &
    terrain_valid
)


print(
    "Analysis pixels:",
    int(
        analysis_mask.sum()
    )
)


# ============================================================
# HELPER — read aligned raster
# ============================================================

def read_aligned(path):

    with rasterio.open(path) as src:

        same_grid = (
            src.crs == crs
            and src.width == width
            and src.height == height
            and src.transform.almost_equals(
                transform
            )
        )

        if same_grid:

            return src.read(1).astype(
                np.float32
            )


        arr = np.full(
            (
                height,
                width
            ),
            np.nan,
            dtype=np.float32
        )

        reproject(
            source=rasterio.band(
                src,
                1
            ),
            destination=arr,

            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,

            dst_transform=transform,
            dst_crs=crs,
            dst_nodata=np.nan,

            resampling=Resampling.bilinear,
        )

        return arr


# ============================================================
# DRAINAGE DISTANCE
# ============================================================

print("Loading drainage distance...")

drain_dist = read_aligned(
    DRAIN_DIST
)


# ============================================================
# RIVER DISTANCE
# ============================================================

print("Building river-distance raster...")

rivers = gpd.read_file(
    RIVERS
).to_crs(crs)


river_mask = rasterize(
    [
        (geom, 1)
        for geom in rivers.geometry
        if geom is not None
        and not geom.is_empty
    ],
    out_shape=(
        height,
        width
    ),
    transform=transform,
    fill=0,
    dtype="uint8",
    all_touched=True,
)


pixel_y = abs(
    transform.e
)

pixel_x = abs(
    transform.a
)


river_dist = distance_transform_edt(
    river_mask == 0,
    sampling=(
        pixel_y,
        pixel_x
    )
).astype(
    np.float32
)


print(
    "River pixels:",
    int(
        river_mask.sum()
    )
)


# ============================================================
# LOCAL DRAINAGE-AREA PROXY
# ============================================================
#
# Original habitation model:
# pct_area_drain_250m
#
# Raster equivalent:
# proportion of a local ~500 m window that lies
# within 250 m of DEM-derived drainage.
#
# ============================================================

print(
    "Calculating local drainage-area proxy..."
)

near_drainage = (
    drain_dist <= 250
).astype(
    np.float32
)


pixel_size = (
    abs(transform.a)
)

radius_pixels = int(
    round(
        250 / pixel_size
    )
)

window_size = (
    radius_pixels * 2
    + 1
)


print(
    "Local window:",
    window_size,
    "x",
    window_size,
    "pixels"
)


drain_area_pct = (
    uniform_filter(
        near_drainage,
        size=window_size,
        mode="nearest"
    )
    * 100.0
).astype(
    np.float32
)


# ============================================================
# RAINFALL
# ============================================================

print("Loading rainfall rasters...")

clim_rain = read_aligned(
    CLIM_RAIN
)

extreme_rain = read_aligned(
    EXTREME_RAIN
)


# ============================================================
# ROBUST 5–95% SCALING
# ============================================================
#
# Same logic as habitation flood model,
# but scaling is calculated over the 30 m
# Raigad raster domain.
#
# ============================================================

def high_score(
    array,
    name
):

    values = array[
        analysis_mask
        &
        np.isfinite(array)
    ]

    low = np.percentile(
        values,
        5
    )

    high = np.percentile(
        values,
        95
    )


    print(
        f"{name:25s} "
        f"P05={low:.3f} "
        f"P95={high:.3f}"
    )


    score = (
        array - low
    ) / (
        high - low
    )

    return np.clip(
        score,
        0,
        1
    ).astype(
        np.float32
    )


def low_score(
    array,
    name
):

    return (
        1.0
        -
        high_score(
            array,
            name
        )
    ).astype(
        np.float32
    )


print("\nROBUST SCALING")
print("=" * 80)


f_elevation = low_score(
    elevation,
    "elevation"
)

f_flatness = low_score(
    slope,
    "slope"
)

f_river = low_score(
    river_dist,
    "river distance"
)

f_drain = low_score(
    drain_dist,
    "drainage distance"
)

f_drain_area = high_score(
    drain_area_pct,
    "local drainage area %"
)

f_clim = high_score(
    clim_rain,
    "climatic rainfall"
)

f_extreme = high_score(
    extreme_rain,
    "extreme rainfall"
)


# ============================================================
# COMPONENTS
# ============================================================

terrain_component = (
    f_elevation
    +
    f_flatness
) / 2.0


drainage_component = (
    f_drain
    +
    f_drain_area
) / 2.0


river_component = (
    f_river
)


rainfall_component = (
    f_clim
    +
    f_extreme
) / 2.0


# ============================================================
# FINAL BASELINE
# ============================================================

flood = (
      0.25
      * terrain_component

    + 0.25
      * drainage_component

    + 0.25
      * river_component

    + 0.25
      * rainfall_component
)


flood_100 = (
    flood
    * 100.0
).astype(
    np.float32
)


# ============================================================
# VALIDITY
# ============================================================

predictor_valid = (
    analysis_mask

    &
    np.isfinite(
        elevation
    )

    &
    np.isfinite(
        slope
    )

    &
    np.isfinite(
        river_dist
    )

    &
    np.isfinite(
        drain_dist
    )

    &
    np.isfinite(
        clim_rain
    )

    &
    np.isfinite(
        extreme_rain
    )
)


output = np.full(
    (
        height,
        width
    ),
    -9999.0,
    dtype=np.float32
)


output[
    predictor_valid
] = flood_100[
    predictor_valid
]


# ============================================================
# SAVE
# ============================================================

profile.update(
    dtype="float32",
    count=1,
    nodata=-9999.0,
    compress="lzw",
)


with rasterio.open(
    OUTPUT,
    "w",
    **profile
) as dst:

    dst.write(
        output,
        1
    )


# ============================================================
# QA
# ============================================================

valid = output[
    output != -9999.0
]


print("\nFLOOD SUSCEPTIBILITY SUMMARY")
print("=" * 80)

print(
    "Valid pixels:",
    len(valid)
)

print(
    "Coverage:",
    round(
        len(valid)
        /
        analysis_mask.sum()
        * 100,
        3
    ),
    "%"
)

print(
    "Minimum:",
    float(
        valid.min()
    )
)

print(
    "Mean:",
    float(
        valid.mean()
    )
)

print(
    "Median:",
    float(
        np.median(valid)
    )
)

print(
    "Maximum:",
    float(
        valid.max()
    )
)


for threshold in [
    20,
    40,
    60,
    80
]:

    pct = (
        (
            valid >= threshold
        )
        .mean()
        * 100
    )

    print(
        f">= {threshold}: "
        f"{pct:.2f}%"
    )


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
