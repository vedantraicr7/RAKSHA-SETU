from pathlib import Path

import numpy as np
import rasterio


FLOOD = Path(
    "data/processed/"
    "raigad_flood_susceptibility.tif"
)

LANDSLIDE = Path(
    "data/processed/landslide/"
    "raigad_landslide_susceptibility.tif"
)

SLOPE = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

DRAIN_DIST = Path(
    "data/processed/hydrology/"
    "raigad_distance_to_drainage_m.tif"
)

LULC = Path(
    "data/processed/landslide/predictors/"
    "lulc_class.tif"
)

ROAD_DIST = Path(
    "data/processed/landslide/predictors/"
    "dist_road_m.tif"
)

ANALYSIS_MASK = Path(
    "data/processed/landslide/predictors/"
    "raigad_analysis_mask.tif"
)


OUT_STRICT = Path(
    "data/processed/relocation/"
    "raigad_safe_land_strict.tif"
)

OUT_CONDITIONAL = Path(
    "data/processed/relocation/"
    "raigad_safe_land_conditional.tif"
)

OUT_DIR = OUT_STRICT.parent
OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def read(path):

    with rasterio.open(path) as src:
        return (
            src.read(1),
            src.profile.copy(),
            src.nodata
        )


print("Loading rasters...")

flood, profile, flood_nodata = read(FLOOD)
landslide, _, ls_nodata = read(LANDSLIDE)
slope, _, slope_nodata = read(SLOPE)
drain, _, drain_nodata = read(DRAIN_DIST)
lulc, _, _ = read(LULC)
road, _, road_nodata = read(ROAD_DIST)
analysis, _, _ = read(ANALYSIS_MASK)


# ==========================================================
# VALID ANALYSIS AREA
# ==========================================================

valid = analysis == 1

valid &= np.isfinite(flood)
valid &= np.isfinite(landslide)
valid &= np.isfinite(slope)
valid &= np.isfinite(drain)
valid &= np.isfinite(road)

if flood_nodata is not None:
    valid &= flood != flood_nodata

if ls_nodata is not None:
    valid &= landslide != ls_nodata

if slope_nodata is not None:
    valid &= slope != slope_nodata

if drain_nodata is not None:
    valid &= drain != drain_nodata

if road_nodata is not None:
    valid &= road != road_nodata


print(
    "Valid analysis pixels:",
    int(valid.sum())
)


# ==========================================================
# RELATIVE HAZARD THRESHOLDS
# ==========================================================

flood_p40 = np.percentile(
    flood[valid],
    40
)

landslide_p40 = np.percentile(
    landslide[valid],
    40
)


print("\nSafety thresholds")
print("=" * 70)

print(
    "Flood 40th percentile:",
    round(
        float(flood_p40),
        3
    )
)

print(
    "Landslide 40th percentile:",
    round(
        float(landslide_p40),
        3
    )
)


# ==========================================================
# PHYSICAL SAFETY
# ==========================================================

physical_safe = (
    valid
    &
    (flood <= flood_p40)
    &
    (landslide <= landslide_p40)
    &
    (slope <= 10.0)
    &
    (drain >= 250.0)
)


# ==========================================================
# ACCESSIBILITY
# ==========================================================
#
# Keep land reasonably accessible.
# This is prototype screening, not an engineering standard.
#

accessible = (
    road <= 3000.0
)


# ==========================================================
# LAND COVER
# ==========================================================

preferred_lulc = np.isin(
    lulc,
    [
        30,  # Grassland
        60,  # Bare/sparse vegetation
    ]
)


conditional_lulc = np.isin(
    lulc,
    [
        30,
        40,  # Cropland
        60,
    ]
)


strict = (
    physical_safe
    &
    accessible
    &
    preferred_lulc
)


conditional = (
    physical_safe
    &
    accessible
    &
    conditional_lulc
)


# ==========================================================
# SAVE
# ==========================================================

out_profile = profile.copy()

out_profile.update(
    dtype="uint8",
    count=1,
    nodata=0,
    compress="lzw",
)


with rasterio.open(
    OUT_STRICT,
    "w",
    **out_profile
) as dst:

    dst.write(
        strict.astype(
            np.uint8
        ),
        1
    )


with rasterio.open(
    OUT_CONDITIONAL,
    "w",
    **out_profile
) as dst:

    dst.write(
        conditional.astype(
            np.uint8
        ),
        1
    )


# ==========================================================
# AREA STATISTICS
# ==========================================================

pixel_area_m2 = (
    abs(profile["transform"].a)
    *
    abs(profile["transform"].e)
)

pixel_area_km2 = (
    pixel_area_m2
    / 1_000_000
)


analysis_area = (
    valid.sum()
    *
    pixel_area_km2
)

physical_area = (
    physical_safe.sum()
    *
    pixel_area_km2
)

strict_area = (
    strict.sum()
    *
    pixel_area_km2
)

conditional_area = (
    conditional.sum()
    *
    pixel_area_km2
)


print("\nSAFE-LAND SUMMARY")
print("=" * 70)

print(
    "Analysis area:",
    round(
        analysis_area,
        2
    ),
    "km²"
)

print(
    "Physically safe:",
    round(
        physical_area,
        2
    ),
    "km²"
)

print(
    "Strict preferred land:",
    round(
        strict_area,
        2
    ),
    "km²"
)

print(
    "Conditional incl. cropland:",
    round(
        conditional_area,
        2
    ),
    "km²"
)


print(
    "\nStrict % of district:",
    round(
        strict.sum()
        /
        valid.sum()
        * 100,
        2
    ),
    "%"
)

print(
    "Conditional % of district:",
    round(
        conditional.sum()
        /
        valid.sum()
        * 100,
        2
    ),
    "%"
)


print("\nSaved:")
print(OUT_STRICT)
print(OUT_CONDITIONAL)

print("\nDONE.")
