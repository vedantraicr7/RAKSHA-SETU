from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling

from scipy.ndimage import distance_transform_edt


# ============================================================
# PATHS
# ============================================================

MASTER = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

RAINFALL = Path(
    "data/processed/"
    "raigad_rainfall_climatology_1995_2024.gpkg"
)

LULC = Path(
    "data/processed/landslide/"
    "raigad_worldcover_2021.tif"
)

ROADS = Path(
    "data/processed/landslide/"
    "raigad_roads.gpkg"
)

OUT_DIR = Path(
    "data/processed/landslide/predictors"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MASTER GRID
# ============================================================

print("Loading master grid...")

with rasterio.open(MASTER) as src:

    profile = src.profile.copy()

    master_crs = src.crs
    transform = src.transform

    width = src.width
    height = src.height

    slope = src.read(1)

    slope_nodata = src.nodata


valid_mask = (
    np.isfinite(slope)
)

if slope_nodata is not None:

    valid_mask &= (
        slope != slope_nodata
    )


print("CRS:", master_crs)
print("Size:", width, "x", height)
print("Resolution:", transform.a, "m")


# ============================================================
# HELPER — SAVE FLOAT RASTER
# ============================================================

def save_float(name, array):

    path = OUT_DIR / name

    out_profile = profile.copy()

    out_profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="lzw",
    )

    output = array.astype(
        np.float32
    )

    output[~valid_mask] = -9999.0

    with rasterio.open(
        path,
        "w",
        **out_profile
    ) as dst:

        dst.write(
            output,
            1
        )

    print("Saved:", path)


# ============================================================
# 1. RAINFALL
# ============================================================

print("\nRasterizing rainfall...")

rain = gpd.read_file(
    RAINFALL
)

rain = rain.to_crs(
    master_crs
)


def rasterize_field(field):

    shapes = [
        (
            geom,
            float(value)
        )
        for geom, value in zip(
            rain.geometry,
            rain[field]
        )
        if geom is not None
        and np.isfinite(value)
    ]

    arr = rasterize(
        shapes=shapes,
        out_shape=(
            height,
            width
        ),
        transform=transform,
        fill=np.nan,
        dtype="float32",
        all_touched=True,
    )

    return arr


clim_rain = rasterize_field(
    "clim_mean_annual_mm"
)

extreme_rain = rasterize_field(
    "hist_max_1day_mm"
)


print(
    "Missing climate pixels:",
    int(
        np.isnan(
            clim_rain[valid_mask]
        ).sum()
    )
)

print(
    "Missing extreme-rain pixels:",
    int(
        np.isnan(
            extreme_rain[valid_mask]
        ).sum()
    )
)


save_float(
    "clim_mean_annual_mm.tif",
    clim_rain
)

save_float(
    "hist_max_1day_mm.tif",
    extreme_rain
)


# ============================================================
# 2. LULC — nearest neighbour
# ============================================================

print("\nAligning WorldCover...")

lulc_aligned = np.zeros(
    (
        height,
        width
    ),
    dtype=np.uint8
)


with rasterio.open(LULC) as src:

    reproject(
        source=rasterio.band(
            src,
            1
        ),

        destination=lulc_aligned,

        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=0,

        dst_transform=transform,
        dst_crs=master_crs,
        dst_nodata=0,

        resampling=Resampling.nearest,
    )


lulc_profile = profile.copy()

lulc_profile.update(
    dtype="uint8",
    count=1,
    nodata=0,
    compress="lzw",
)


lulc_path = (
    OUT_DIR /
    "lulc_class.tif"
)

with rasterio.open(
    lulc_path,
    "w",
    **lulc_profile
) as dst:

    dst.write(
        lulc_aligned,
        1
    )


print(
    "Saved:",
    lulc_path
)


# ============================================================
# 3. ROADS
# ============================================================

print("\nRasterizing roads...")

roads = gpd.read_file(
    ROADS,
    layer="roads"
)

roads = roads.to_crs(
    master_crs
)


road_shapes = [
    (
        geom,
        1
    )
    for geom in roads.geometry
    if geom is not None
    and not geom.is_empty
]


road_mask = rasterize(
    shapes=road_shapes,
    out_shape=(
        height,
        width
    ),
    transform=transform,
    fill=0,
    dtype="uint8",
    all_touched=True,
)


print(
    "Road pixels:",
    int(
        (road_mask == 1)
        .sum()
    )
)


# ============================================================
# DISTANCE TO ROAD
# ============================================================

print(
    "Calculating distance-to-road raster..."
)

pixel_size_y = abs(
    transform.e
)

pixel_size_x = abs(
    transform.a
)


dist_road = distance_transform_edt(
    road_mask == 0,
    sampling=(
        pixel_size_y,
        pixel_size_x
    )
).astype(
    np.float32
)


save_float(
    "dist_road_m.tif",
    dist_road
)


# ============================================================
# ROAD PROXIMITY
# Same transformation used in production model
# ============================================================

road_proximity = np.exp(
    -dist_road / 500.0
).astype(
    np.float32
)


save_float(
    "road_proximity.tif",
    road_proximity
)


# ============================================================
# QA
# ============================================================

print("\nPREDICTOR QA")
print("=" * 70)

print(
    "Climate rainfall:",
    float(
        np.nanmin(
            clim_rain[valid_mask]
        )
    ),
    "to",
    float(
        np.nanmax(
            clim_rain[valid_mask]
        )
    )
)

print(
    "Extreme rainfall:",
    float(
        np.nanmin(
            extreme_rain[valid_mask]
        )
    ),
    "to",
    float(
        np.nanmax(
            extreme_rain[valid_mask]
        )
    )
)

print(
    "Road distance:",
    float(
        dist_road[valid_mask]
        .min()
    ),
    "to",
    float(
        dist_road[valid_mask]
        .max()
    )
)

print(
    "Road proximity:",
    float(
        road_proximity[valid_mask]
        .min()
    ),
    "to",
    float(
        road_proximity[valid_mask]
        .max()
    )
)

values, counts = np.unique(
    lulc_aligned[
        valid_mask
    ],
    return_counts=True
)

print("\nAligned LULC classes:")

for value, count in zip(
    values,
    counts
):

    print(
        int(value),
        int(count)
    )


print("\nDONE.")
