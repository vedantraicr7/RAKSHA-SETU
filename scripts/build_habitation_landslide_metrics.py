from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


HABITATIONS = Path(
    "data/processed/"
    "raigad_habitations_flood_priority.gpkg"
)

SUSCEPTIBILITY = Path(
    "data/processed/landslide/"
    "raigad_landslide_susceptibility.tif"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_multihazard_base.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/landslide/"
    "raigad_habitation_landslide_ranking.csv"
)


print("Loading habitations...")

gdf = gpd.read_file(HABITATIONS)

print("Habitations:", len(gdf))


with rasterio.open(SUSCEPTIBILITY) as src:

    raster_crs = src.crs
    nodata = src.nodata

    hab = gdf.to_crs(
        raster_crs
    )

    mean_vals = []
    median_vals = []
    p90_vals = []
    max_vals = []

    pct_ge40 = []
    pct_ge60 = []
    pct_ge80 = []

    valid_pixels = []


    print(
        "Calculating habitation "
        "landslide metrics..."
    )


    for idx, geom in enumerate(
        hab.geometry
    ):

        try:

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

                mean_vals.append(np.nan)
                median_vals.append(np.nan)
                p90_vals.append(np.nan)
                max_vals.append(np.nan)

                pct_ge40.append(np.nan)
                pct_ge60.append(np.nan)
                pct_ge80.append(np.nan)

                valid_pixels.append(0)

                continue


            mean_vals.append(
                float(
                    np.mean(values)
                )
            )

            median_vals.append(
                float(
                    np.median(values)
                )
            )

            p90_vals.append(
                float(
                    np.percentile(
                        values,
                        90
                    )
                )
            )

            max_vals.append(
                float(
                    np.max(values)
                )
            )


            pct_ge40.append(
                float(
                    (
                        values >= 40
                    ).mean()
                    * 100
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


        except ValueError:

            mean_vals.append(np.nan)
            median_vals.append(np.nan)
            p90_vals.append(np.nan)
            max_vals.append(np.nan)

            pct_ge40.append(np.nan)
            pct_ge60.append(np.nan)
            pct_ge80.append(np.nan)

            valid_pixels.append(0)


        if (
            idx + 1
        ) % 250 == 0:

            print(
                f"{idx + 1} / "
                f"{len(hab)}"
            )


# --------------------------------------------------
# Attach back to original CRS dataset
# --------------------------------------------------

gdf["ls_mean"] = mean_vals
gdf["ls_median"] = median_vals
gdf["ls_p90"] = p90_vals
gdf["ls_max"] = max_vals

gdf["ls_pct_ge40"] = pct_ge40
gdf["ls_pct_ge60"] = pct_ge60
gdf["ls_pct_ge80"] = pct_ge80

gdf["ls_valid_pixels"] = (
    valid_pixels
)


# --------------------------------------------------
# QA
# --------------------------------------------------

metrics = [
    "ls_mean",
    "ls_median",
    "ls_p90",
    "ls_max",
    "ls_pct_ge40",
    "ls_pct_ge60",
    "ls_pct_ge80",
]


print("\nMissing values:")
print(
    gdf[metrics]
    .isna()
    .sum()
)


print("\nLANDSLIDE HABITATION SUMMARY")
print("=" * 80)

print(
    gdf[metrics]
    .describe()
    .T
)


# --------------------------------------------------
# Relative ranking
# --------------------------------------------------

gdf["landslide_percentile"] = (
    gdf["ls_mean"]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)


labels = [
    "Very Low",
    "Low",
    "Moderate",
    "High",
    "Very High",
]


valid_mask = (
    gdf["ls_mean"]
    .notna()
)


gdf["landslide_class"] = (
    "Insufficient Data"
)


gdf.loc[
    valid_mask,
    "landslide_class"
] = pd.qcut(
    gdf.loc[
        valid_mask,
        "ls_mean"
    ],
    q=5,
    labels=labels,
    duplicates="drop"
).astype(str)


# --------------------------------------------------
# Top 30
# --------------------------------------------------

cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",
    "ls_mean",
    "ls_p90",
    "ls_pct_ge60",
    "ls_pct_ge80",
    "landslide_percentile",
    "landslide_class",
]


print(
    "\nTOP 30 LANDSLIDE-SUSCEPTIBLE "
    "HABITATIONS"
)

print("=" * 120)


top30 = (
    gdf
    .sort_values(
        "ls_mean",
        ascending=False
    )
    .head(30)
)


print(
    top30[cols]
    .to_string(index=False)
)


# --------------------------------------------------
# Save
# --------------------------------------------------

gdf.to_file(
    OUTPUT,
    layer="multihazard_base",
    driver="GPKG"
)


(
    gdf
    .sort_values(
        "ls_mean",
        ascending=False
    )[cols]
    .to_csv(
        CSV_OUTPUT,
        index=False
    )
)


print("\nSaved:")
print(OUTPUT)
print(CSV_OUTPUT)

print("\nDONE.")
