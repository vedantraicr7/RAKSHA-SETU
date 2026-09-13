from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


INPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_susceptibility.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_exposure.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/"
    "raigad_flood_exposure_ranking.csv"
)


print("Loading susceptibility layer...")

gdf = gpd.read_file(INPUT)

print("Habitations:", len(gdf))


# --------------------------------------------------
# Numeric cleanup
# --------------------------------------------------

gdf["population"] = pd.to_numeric(
    gdf["total_popu"],
    errors="coerce"
).fillna(0)

gdf["households"] = pd.to_numeric(
    gdf["total_hous"],
    errors="coerce"
).fillna(0)


# --------------------------------------------------
# Flag analytical habitations
# --------------------------------------------------

# zero population records remain in the physical
# susceptibility dataset, but exposure should be zero.

gdf["has_population"] = (
    gdf["population"] > 0
)


# --------------------------------------------------
# Raw exposure indicators
# --------------------------------------------------

gdf["population_exposure"] = (
    gdf["population"]
    * gdf["flood_susceptibility"]
)

gdf["household_exposure"] = (
    gdf["households"]
    * gdf["flood_susceptibility"]
)


# --------------------------------------------------
# Normalize exposure using robust percentile scaling
# --------------------------------------------------

def robust_score(series):

    x = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    low = x.quantile(0.05)
    high = x.quantile(0.95)

    if high == low:
        return pd.Series(
            np.zeros(len(x)),
            index=x.index
        )

    score = (
        (x - low)
        /
        (high - low)
    )

    return score.clip(0, 1)


gdf["population_exposure_score"] = (
    robust_score(
        gdf["population_exposure"]
    )
)

gdf["household_exposure_score"] = (
    robust_score(
        gdf["household_exposure"]
    )
)


# --------------------------------------------------
# Exposure component
# --------------------------------------------------

gdf["exposure_component"] = (
      0.70 * gdf["population_exposure_score"]
    + 0.30 * gdf["household_exposure_score"]
)


gdf["exposure_100"] = (
    gdf["exposure_component"]
    * 100
)


# --------------------------------------------------
# QA
# --------------------------------------------------

print("\nPopulation summary:")
print(
    gdf["population"]
    .describe()
)

print("\nHousehold summary:")
print(
    gdf["households"]
    .describe()
)

print("\nExposure summary:")
print(
    gdf[
        [
            "population_exposure",
            "household_exposure",
            "exposure_100"
        ]
    ]
    .describe()
    .T
)


# --------------------------------------------------
# Top exposure records
# --------------------------------------------------

cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",
    "households",
    "flood_susceptibility_100",
    "population_exposure",
    "household_exposure",
    "exposure_100"
]

print("\nTOP 30 FLOOD EXPOSURE HABITATIONS")
print("=" * 120)

print(
    gdf[cols]
    .sort_values(
        "exposure_100",
        ascending=False
    )
    .head(30)
    .to_string(index=False)
)


# --------------------------------------------------
# Save
# --------------------------------------------------

gdf.to_file(
    OUTPUT,
    layer="flood_exposure",
    driver="GPKG"
)

gdf[cols].sort_values(
    "exposure_100",
    ascending=False
).to_csv(
    CSV_OUTPUT,
    index=False
)

print("\nSaved:")
print(OUTPUT)
print(CSV_OUTPUT)

print("\nDONE.")
