from pathlib import Path

import geopandas as gpd
import pandas as pd


INPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_susceptibility.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_exposure_v2.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/"
    "raigad_flood_exposure_ranking_v2.csv"
)


print("Loading susceptibility dataset...")

gdf = gpd.read_file(INPUT)

print("Habitations:", len(gdf))


# ============================================================
# 1. CLEAN POPULATION / HOUSEHOLDS
# ============================================================

gdf["population"] = pd.to_numeric(
    gdf["total_popu"],
    errors="coerce"
).fillna(0)

gdf["households"] = pd.to_numeric(
    gdf["total_hous"],
    errors="coerce"
).fillna(0)


# ============================================================
# 2. RAW EXPOSURE PROXIES
# ============================================================

gdf["population_exposure"] = (
    gdf["population"]
    *
    gdf["flood_susceptibility"]
)

gdf["household_exposure"] = (
    gdf["households"]
    *
    gdf["flood_susceptibility"]
)


# ============================================================
# 3. RELATIVE EXPOSURE PERCENTILES
#
# These are relative rankings inside Raigad.
# They are NOT probabilities.
# ============================================================

gdf["population_exposure_percentile"] = (
    gdf["population_exposure"]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)

gdf["household_exposure_percentile"] = (
    gdf["household_exposure"]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)


# ============================================================
# 4. PRIMARY EXPOSURE SCORE
#
# Population exposure is the primary administrative
# exposure indicator.
#
# Household exposure is retained separately rather than
# arbitrarily double-counting the same population.
# ============================================================

gdf["exposure_percentile"] = (
    gdf["population_exposure_percentile"]
)


# ============================================================
# 5. RELATIVE EXPOSURE CLASS
# ============================================================

labels = [
    "Very Low",
    "Low",
    "Moderate",
    "High",
    "Very High",
]

gdf["exposure_class"] = pd.qcut(
    gdf["population_exposure"],
    q=5,
    labels=labels,
    duplicates="drop"
)


# ============================================================
# 6. QA
# ============================================================

print("\nPopulation vs household correlation:")

print(
    gdf[
        [
            "population",
            "households"
        ]
    ]
    .corr(method="spearman")
    .round(3)
)


print("\nRaw population exposure:")
print(
    gdf["population_exposure"]
    .describe()
)


print("\nExposure percentile:")
print(
    gdf["exposure_percentile"]
    .describe()
)


print("\nExposure classes:")
print(
    gdf["exposure_class"]
    .value_counts()
    .sort_index()
)


# ============================================================
# 7. TOP 30
# ============================================================

cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",
    "households",
    "flood_susceptibility_100",
    "population_exposure",
    "household_exposure",
    "exposure_percentile",
    "exposure_class",
]

print("\nTOP 30 RELATIVE FLOOD EXPOSURE")
print("=" * 120)

top30 = (
    gdf
    .sort_values(
        "population_exposure",
        ascending=False
    )
    .head(30)
)

print(
    top30[cols]
    .to_string(index=False)
)


# ============================================================
# 8. SAVE
# ============================================================

gdf.to_file(
    OUTPUT,
    layer="flood_exposure_v2",
    driver="GPKG"
)

(
    gdf
    .sort_values(
        "population_exposure",
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
