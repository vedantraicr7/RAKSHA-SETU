from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from scipy.stats import spearmanr, pearsonr


HABITATIONS = Path(
    "data/processed/"
    "raigad_habitations_flood_susceptibility.gpkg"
)

RASTER = Path(
    "data/processed/"
    "raigad_flood_susceptibility.tif"
)

OUTPUT = Path(
    "data/processed/"
    "flood_raster_habitation_validation.csv"
)


print("Loading habitation flood dataset...")

gdf = gpd.read_file(HABITATIONS)

print("Habitations:", len(gdf))


with rasterio.open(RASTER) as src:

    raster_crs = src.crs
    nodata = src.nodata

    hab = gdf.to_crs(
        raster_crs
    )

    raster_mean = []
    raster_median = []
    raster_p90 = []
    raster_max = []

    pct_ge60 = []
    pct_ge80 = []

    valid_pixels = []


    print(
        "Summarizing flood raster "
        "by habitation..."
    )


    for idx, geom in enumerate(
        hab.geometry
    ):

        clipped, _ = mask(
            src,
            [
                geom.__geo_interface__
            ],
            crop=True,
            filled=True,
            nodata=nodata
        )

        arr = clipped[0]

        valid = np.isfinite(arr)

        if nodata is not None:
            valid &= (
                arr != nodata
            )

        values = arr[valid]


        if len(values) == 0:

            raster_mean.append(np.nan)
            raster_median.append(np.nan)
            raster_p90.append(np.nan)
            raster_max.append(np.nan)

            pct_ge60.append(np.nan)
            pct_ge80.append(np.nan)

            valid_pixels.append(0)

            continue


        raster_mean.append(
            float(
                np.mean(values)
            )
        )

        raster_median.append(
            float(
                np.median(values)
            )
        )

        raster_p90.append(
            float(
                np.percentile(
                    values,
                    90
                )
            )
        )

        raster_max.append(
            float(
                np.max(values)
            )
        )

        pct_ge60.append(
            float(
                (
                    values >= 60
                ).mean()
                * 100
            )
        )

        pct_ge80.append(
            float(
                (
                    values >= 80
                ).mean()
                * 100
            )
        )

        valid_pixels.append(
            len(values)
        )


        if (
            idx + 1
        ) % 250 == 0:

            print(
                f"{idx + 1} / "
                f"{len(hab)}"
            )


gdf["raster_flood_mean"] = (
    raster_mean
)

gdf["raster_flood_median"] = (
    raster_median
)

gdf["raster_flood_p90"] = (
    raster_p90
)

gdf["raster_flood_max"] = (
    raster_max
)

gdf["raster_pct_ge60"] = (
    pct_ge60
)

gdf["raster_pct_ge80"] = (
    pct_ge80
)

gdf["raster_valid_pixels"] = (
    valid_pixels
)


# ============================================================
# CORRELATIONS
# ============================================================

valid = gdf[
    [
        "flood_susceptibility_100",
        "raster_flood_mean"
    ]
].dropna()


spearman_r, spearman_p = (
    spearmanr(
        valid[
            "flood_susceptibility_100"
        ],
        valid[
            "raster_flood_mean"
        ]
    )
)


pearson_r, pearson_p = (
    pearsonr(
        valid[
            "flood_susceptibility_100"
        ],
        valid[
            "raster_flood_mean"
        ]
    )
)


print("\nVALIDATION")
print("=" * 80)

print(
    "Compared habitations:",
    len(valid)
)

print(
    f"Spearman correlation: "
    f"{spearman_r:.4f}"
)

print(
    f"Pearson correlation:  "
    f"{pearson_r:.4f}"
)


# ============================================================
# DIFFERENCE
# ============================================================

gdf["flood_score_difference"] = (
    gdf["raster_flood_mean"]
    -
    gdf["flood_susceptibility_100"]
)


print("\nDifference summary:")
print(
    gdf[
        "flood_score_difference"
    ]
    .describe()
)


# ============================================================
# TOP ORIGINAL VS RASTER
# ============================================================

cols = [
    "village",
    "subdistric",
    "vlcode",
    "flood_susceptibility_100",
    "raster_flood_mean",
    "raster_flood_p90",
    "raster_pct_ge60",
    "raster_pct_ge80",
    "flood_score_difference",
]


print(
    "\nTOP 25 BY ORIGINAL "
    "HABITATION MODEL"
)

print("=" * 120)

print(
    gdf[cols]
    .sort_values(
        "flood_susceptibility_100",
        ascending=False
    )
    .head(25)
    .to_string(index=False)
)


print(
    "\nTOP 25 BY NEW "
    "RASTER MEAN"
)

print("=" * 120)

print(
    gdf[cols]
    .sort_values(
        "raster_flood_mean",
        ascending=False
    )
    .head(25)
    .to_string(index=False)
)


# ============================================================
# RANK COMPARISON
# ============================================================

gdf["old_rank_pct"] = (
    gdf[
        "flood_susceptibility_100"
    ]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)

gdf["raster_rank_pct"] = (
    gdf[
        "raster_flood_mean"
    ]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)


gdf["rank_gap_pct"] = (
    gdf["raster_rank_pct"]
    -
    gdf["old_rank_pct"]
).abs()


print(
    "\nLargest ranking disagreements"
)

print("=" * 120)

print(
    gdf[
        [
            "village",
            "subdistric",
            "vlcode",
            "old_rank_pct",
            "raster_rank_pct",
            "rank_gap_pct",
            "flood_susceptibility_100",
            "raster_flood_mean",
        ]
    ]
    .sort_values(
        "rank_gap_pct",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)


# ============================================================
# SAVE
# ============================================================

gdf[
    cols
    + [
        "old_rank_pct",
        "raster_rank_pct",
        "rank_gap_pct",
    ]
].to_csv(
    OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
