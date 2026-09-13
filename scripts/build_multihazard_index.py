from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


INPUT = Path(
    "data/processed/"
    "raigad_habitations_multihazard_base.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_multihazard.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/"
    "raigad_multihazard_ranking.csv"
)


print("Loading habitation multi-hazard base...")

gdf = gpd.read_file(INPUT)

print("Habitations:", len(gdf))


# --------------------------------------------------
# Required fields
# --------------------------------------------------

required = [
    "susceptibility_percentile",
    "landslide_percentile",
    "exposure_percentile",
    "vulnerability_percentile",
    "population",
]

missing = [
    col for col in required
    if col not in gdf.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# --------------------------------------------------
# 1. Hazard percentiles (0-1)
# --------------------------------------------------

flood_hazard = (
    gdf["susceptibility_percentile"]
    / 100.0
)

landslide_hazard = (
    gdf["landslide_percentile"]
    / 100.0
)


# --------------------------------------------------
# 2. Multi-hazard susceptibility
#
# Geometric mean rewards locations that are
# elevated in BOTH hazards, while still allowing
# one strong hazard to matter.
# --------------------------------------------------

gdf["multihazard_susceptibility"] = np.sqrt(
    flood_hazard
    *
    landslide_hazard
)

gdf["multihazard_susceptibility_100"] = (
    gdf["multihazard_susceptibility"]
    * 100
)


# --------------------------------------------------
# 3. Dominant hazard
# --------------------------------------------------

conditions = [
    (
        gdf["susceptibility_percentile"]
        >
        gdf["landslide_percentile"] + 10
    ),
    (
        gdf["landslide_percentile"]
        >
        gdf["susceptibility_percentile"] + 10
    ),
]

choices = [
    "Flood-dominant",
    "Landslide-dominant",
]

gdf["dominant_hazard"] = np.select(
    conditions,
    choices,
    default="Mixed"
)


# --------------------------------------------------
# 4. Exposure + vulnerability
# --------------------------------------------------

valid_priority = (
    (gdf["population"] > 0)
    &
    gdf["vulnerability_percentile"].notna()
)


exposure = (
    gdf["exposure_percentile"]
    / 100.0
)

vulnerability = (
    gdf["vulnerability_percentile"]
    / 100.0
)


# --------------------------------------------------
# 5. Multi-hazard intervention priority
#
# Hazard is now multi-hazard.
# Exposure and vulnerability remain separate.
# --------------------------------------------------

gdf["multihazard_priority"] = np.nan

gdf.loc[
    valid_priority,
    "multihazard_priority"
] = (
    gdf.loc[
        valid_priority,
        "multihazard_susceptibility"
    ]
    *
    np.sqrt(
        exposure[valid_priority]
        *
        vulnerability[valid_priority]
    )
) ** 0.5


gdf["multihazard_priority_100"] = (
    gdf["multihazard_priority"]
    * 100
)


# --------------------------------------------------
# 6. Percentile + class
# --------------------------------------------------

gdf["multihazard_priority_percentile"] = np.nan

gdf.loc[
    valid_priority,
    "multihazard_priority_percentile"
] = (
    gdf.loc[
        valid_priority,
        "multihazard_priority"
    ]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)


gdf["multihazard_priority_class"] = (
    "Insufficient Data"
)


labels = [
    "Very Low",
    "Low",
    "Moderate",
    "High",
    "Very High",
]


scores = gdf.loc[
    valid_priority,
    "multihazard_priority"
]


classes = pd.qcut(
    scores,
    q=5,
    labels=labels,
    duplicates="drop"
)


gdf.loc[
    valid_priority,
    "multihazard_priority_class"
] = classes.astype(str)


# --------------------------------------------------
# 7. QA
# --------------------------------------------------

print("\nDominant hazard counts:")
print(
    gdf["dominant_hazard"]
    .value_counts()
)


print("\nMulti-hazard susceptibility summary:")
print(
    gdf[
        "multihazard_susceptibility_100"
    ]
    .describe()
)


print("\nMulti-hazard priority summary:")
print(
    gdf.loc[
        valid_priority,
        "multihazard_priority_100"
    ]
    .describe()
)


print("\nPriority classes:")
print(
    gdf[
        "multihazard_priority_class"
    ]
    .value_counts()
)


# --------------------------------------------------
# 8. Top 40
# --------------------------------------------------

cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",

    "flood_susceptibility_100",
    "susceptibility_percentile",

    "ls_mean",
    "landslide_percentile",

    "multihazard_susceptibility_100",

    "exposure_percentile",
    "vulnerability_percentile",

    "multihazard_priority_100",
    "multihazard_priority_percentile",
    "multihazard_priority_class",

    "dominant_hazard",
]


print(
    "\nTOP 40 MULTI-HAZARD PRIORITY HABITATIONS"
)

print("=" * 160)


top40 = (
    gdf[valid_priority]
    .sort_values(
        "multihazard_priority",
        ascending=False
    )
    .head(40)
)


print(
    top40[cols]
    .to_string(index=False)
)


# --------------------------------------------------
# 9. Save
# --------------------------------------------------

gdf.to_file(
    OUTPUT,
    layer="multihazard",
    driver="GPKG"
)


(
    gdf
    .sort_values(
        "multihazard_priority",
        ascending=False,
        na_position="last"
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
