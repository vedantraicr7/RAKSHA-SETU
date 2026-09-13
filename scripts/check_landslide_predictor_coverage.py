from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

from rasterio.features import rasterize


MASTER = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

DISTRICT = Path(
    "data/processed/"
    "raigad_district.gpkg"
)

PRED = Path(
    "data/processed/landslide/"
    "predictors"
)


files = {
    "clim_rain":
        PRED / "clim_mean_annual_mm.tif",

    "extreme_rain":
        PRED / "hist_max_1day_mm.tif",

    "lulc":
        PRED / "lulc_class.tif",

    "road_proximity":
        PRED / "road_proximity.tif",
}


# ----------------------------------------------------
# Master grid
# ----------------------------------------------------

with rasterio.open(MASTER) as src:

    slope = src.read(1)

    profile = src.profile.copy()

    crs = src.crs
    transform = src.transform

    shape = (
        src.height,
        src.width
    )

    slope_nodata = src.nodata


terrain_valid = np.isfinite(slope)

if slope_nodata is not None:
    terrain_valid &= (
        slope != slope_nodata
    )


# ----------------------------------------------------
# Raigad district mask
# ----------------------------------------------------

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
    out_shape=shape,
    transform=transform,
    fill=0,
    dtype="uint8",
    all_touched=False,
).astype(bool)


analysis_mask = (
    district_mask
    &
    terrain_valid
)


print(
    "Total master pixels:",
    slope.size
)

print(
    "Terrain-valid pixels:",
    int(
        terrain_valid.sum()
    )
)

print(
    "Pixels inside Raigad:",
    int(
        district_mask.sum()
    )
)

print(
    "Inside Raigad + terrain valid:",
    int(
        analysis_mask.sum()
    )
)


# ----------------------------------------------------
# Check predictors
# ----------------------------------------------------

print("\nPREDICTOR COVERAGE INSIDE RAIGAD")
print("=" * 80)

complete = analysis_mask.copy()


for name, path in files.items():

    with rasterio.open(path) as src:

        arr = src.read(1)

        nodata = src.nodata


    if name == "lulc":

        valid = (
            arr != 0
        )

    else:

        valid = np.isfinite(arr)

        if nodata is not None:
            valid &= (
                arr != nodata
            )


    missing_inside = (
        analysis_mask
        &
        ~valid
    )

    valid_inside = (
        analysis_mask
        &
        valid
    )


    print(f"\n{name}")

    print(
        "Valid:",
        int(
            valid_inside.sum()
        )
    )

    print(
        "Missing:",
        int(
            missing_inside.sum()
        )
    )

    if analysis_mask.sum() > 0:

        print(
            "Coverage:",
            round(
                valid_inside.sum()
                /
                analysis_mask.sum()
                * 100,
                3
            ),
            "%"
        )


    complete &= valid


# ----------------------------------------------------
# Overall complete coverage
# ----------------------------------------------------

complete_inside = (
    analysis_mask
    &
    complete
)


print(
    "\nCOMPLETE PREDICTOR COVERAGE"
)

print("=" * 80)

print(
    "Complete pixels:",
    int(
        complete_inside.sum()
    )
)

print(
    "Total analysis pixels:",
    int(
        analysis_mask.sum()
    )
)

print(
    "Complete coverage:",
    round(
        complete_inside.sum()
        /
        analysis_mask.sum()
        * 100,
        3
    ),
    "%"
)


# ----------------------------------------------------
# Save analysis mask for later prediction
# ----------------------------------------------------

out = (
    Path(
        "data/processed/landslide/"
        "predictors/"
        "raigad_analysis_mask.tif"
    )
)

out_profile = profile.copy()

out_profile.update(
    dtype="uint8",
    nodata=0,
    count=1,
    compress="lzw",
)


with rasterio.open(
    out,
    "w",
    **out_profile
) as dst:

    dst.write(
        complete_inside.astype(
            np.uint8
        ),
        1
    )


print("\nSaved:")
print(out)

print("\nDONE.")
