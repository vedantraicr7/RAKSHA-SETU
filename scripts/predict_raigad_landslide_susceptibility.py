from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import rasterio


MODEL_PATH = Path(
    "models/"
    "landslide_production_model.joblib"
)

SLOPE = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

PRED_DIR = Path(
    "data/processed/landslide/"
    "predictors"
)

CLIM = PRED_DIR / "clim_mean_annual_mm.tif"
EXTREME = PRED_DIR / "hist_max_1day_mm.tif"
ROAD = PRED_DIR / "road_proximity.tif"
LULC = PRED_DIR / "lulc_class.tif"
MASK = PRED_DIR / "raigad_analysis_mask.tif"

OUTPUT = Path(
    "data/processed/landslide/"
    "raigad_landslide_susceptibility.tif"
)


LULC_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    80: "Permanent water",
    90: "Herbaceous wetland",
    95: "Mangroves",
}


print("Loading model...")

model = joblib.load(
    MODEL_PATH
)


# --------------------------------------------------
# Read master/profile
# --------------------------------------------------

with rasterio.open(SLOPE) as src:

    slope = src.read(1)

    profile = src.profile.copy()

    nodata = src.nodata


def read_float(path):

    with rasterio.open(path) as src:
        arr = src.read(1)

    return arr


clim = read_float(CLIM)
extreme = read_float(EXTREME)
road = read_float(ROAD)

with rasterio.open(LULC) as src:
    lulc = src.read(1)

with rasterio.open(MASK) as src:
    mask = src.read(1).astype(bool)


print(
    "Prediction pixels:",
    int(mask.sum())
)


# --------------------------------------------------
# Output array
# --------------------------------------------------

susceptibility = np.full(
    slope.shape,
    -9999.0,
    dtype=np.float32
)


# --------------------------------------------------
# Chunked prediction
# --------------------------------------------------

rows, cols = np.where(mask)

N = len(rows)

CHUNK = 250000


print("Predicting in chunks...")


for start in range(
    0,
    N,
    CHUNK
):

    end = min(
        start + CHUNK,
        N
    )

    r = rows[start:end]
    c = cols[start:end]


    lulc_codes = lulc[r, c]

    lulc_classes = [
        LULC_NAMES.get(
            int(code),
            "Unknown"
        )
        for code in lulc_codes
    ]


    X = pd.DataFrame(
        {
            "slope_deg":
                slope[r, c],

            "clim_mean_annual_mm":
                clim[r, c],

            "hist_max_1day_mm":
                extreme[r, c],

            "road_proximity":
                road[r, c],

            "lulc_class":
                lulc_classes,
        }
    )


    prob = model.predict_proba(
        X
    )[:, 1]


    susceptibility[
        r,
        c
    ] = (
        prob * 100
    ).astype(
        np.float32
    )


    print(
        f"{end:,} / {N:,}"
    )


# --------------------------------------------------
# Save raster
# --------------------------------------------------

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
        susceptibility,
        1
    )


# --------------------------------------------------
# QA
# --------------------------------------------------

valid = susceptibility[
    susceptibility != -9999.0
]


print("\nLANDSLIDE SUSCEPTIBILITY SUMMARY")
print("=" * 70)

print(
    "Valid pixels:",
    len(valid)
)

print(
    "Minimum:",
    float(valid.min())
)

print(
    "Mean:",
    float(valid.mean())
)

print(
    "Median:",
    float(
        np.median(valid)
    )
)

print(
    "Maximum:",
    float(valid.max())
)


for threshold in [
    20,
    40,
    60,
    80,
]:

    pct = (
        (valid >= threshold)
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
