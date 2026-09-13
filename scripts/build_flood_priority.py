from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


INPUT = Path(
    "data/processed/"
    "raigad_habitations_vulnerability_score.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_habitations_flood_priority.gpkg"
)

CSV_OUTPUT = Path(
    "data/processed/"
    "raigad_flood_priority_ranking.csv"
)


print("Loading vulnerability + exposure dataset...")

gdf = gpd.read_file(INPUT)

print("Habitations:", len(gdf))


# ============================================================
# REQUIRED FIELDS
# ============================================================

required = [
    "population",
    "flood_susceptibility_100",
    "exposure_percentile",
    "vulnerability_percentile",
]

missing = [
    col for col in required
    if col not in gdf.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ============================================================
# 1. VALID PRIORITY RECORDS
# ============================================================

positive_population = (
    gdf["population"] > 0
)

complete_vulnerability = (
    gdf["vulnerability_percentile"]
    .notna()
)

valid_priority = (
    positive_population
    &
    complete_vulnerability
)


# ============================================================
# 2. CONVERT PERCENTILES TO 0-1
# ============================================================

exposure = (
    gdf["exposure_percentile"] / 100
)

vulnerability = (
    gdf["vulnerability_percentile"] / 100
)


# ============================================================
# 3. INTERVENTION PRIORITY
#
# Geometric mean:
#
# sqrt(exposure * vulnerability)
#
# Exposure already contains susceptibility,
# so susceptibility is NOT added again here.
# ============================================================

gdf["flood_priority_score"] = np.nan

gdf.loc[
    valid_priority,
    "flood_priority_score"
] = np.sqrt(
    exposure[valid_priority]
    *
    vulnerability[valid_priority]
)


gdf["flood_priority_100"] = (
    gdf["flood_priority_score"]
    * 100
)


# ============================================================
# 4. STATUS
# ============================================================

gdf["priority_status"] = "Eligible"

gdf.loc[
    ~complete_vulnerability,
    "priority_status"
] = "Insufficient Vulnerability Data"

gdf.loc[
    ~positive_population,
    "priority_status"
] = "No Recorded Population"


# ============================================================
# 5. RELATIVE PRIORITY PERCENTILE
# ============================================================

gdf["priority_percentile"] = np.nan

gdf.loc[
    valid_priority,
    "priority_percentile"
] = (
    gdf.loc[
        valid_priority,
        "flood_priority_score"
    ]
    .rank(
        pct=True,
        method="average"
    )
    * 100
)


# ============================================================
# 6. RELATIVE PRIORITY CLASS
# ============================================================

gdf["priority_class"] = (
    "Insufficient Data"
)

gdf.loc[
    ~positive_population,
    "priority_class"
] = "No Recorded Population"


labels = [
    "Very Low",
    "Low",
    "Moderate",
    "High",
    "Very High",
]

valid_scores = gdf.loc[
    valid_priority,
    "flood_priority_score"
]

classes = pd.qcut(
    valid_scores,
    q=5,
    labels=labels,
    duplicates="drop"
)

gdf.loc[
    valid_priority,
    "priority_class"
] = classes.astype(str)


# ============================================================
# 7. EXPLANATION FIELDS
# ============================================================

def priority_reason(row):

    if row["priority_status"] != "Eligible":
        return row["priority_status"]

    reasons = []

    if row["flood_susceptibility_100"] >= 70:
        reasons.append(
            "high physical flood susceptibility"
        )

    if row["exposure_percentile"] >= 80:
        reasons.append(
            "high exposed population"
        )

    if row["vulnerability_percentile"] >= 80:
        reasons.append(
            "high coping vulnerability"
        )

    if not reasons:
        reasons.append(
            "combined exposure and vulnerability"
        )

    return "; ".join(reasons)


gdf["priority_reason"] = gdf.apply(
    priority_reason,
    axis=1
)


# ============================================================
# 8. QA
# ============================================================

print("\nPriority eligibility:")
print(
    gdf["priority_status"]
    .value_counts()
)

print("\nPriority score summary:")
print(
    gdf.loc[
        valid_priority,
        "flood_priority_100"
    ]
    .describe()
)

print("\nPriority classes:")
print(
    gdf["priority_class"]
    .value_counts()
)


# ============================================================
# 9. TOP 40
# ============================================================

cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",
    "flood_susceptibility_100",
    "exposure_percentile",
    "vulnerability_100",
    "vulnerability_percentile",
    "flood_priority_100",
    "priority_percentile",
    "priority_class",
    "priority_reason",
]


print("\nTOP 40 FLOOD INTERVENTION PRIORITY")
print("=" * 150)

top40 = (
    gdf[valid_priority]
    .sort_values(
        "flood_priority_score",
        ascending=False
    )
    .head(40)
)

print(
    top40[cols]
    .to_string(index=False)
)


# ============================================================
# 10. SUBDISTRICT SUMMARY
# ============================================================

summary = (
    gdf[valid_priority]
    .groupby("subdistric")
    .agg(
        eligible_habitations=(
            "vlcode",
            "count"
        ),

        mean_priority=(
            "flood_priority_100",
            "mean"
        ),

        median_priority=(
            "flood_priority_100",
            "median"
        ),

        very_high_priority=(
            "priority_class",
            lambda x: (
                x == "Very High"
            ).sum()
        ),

        exposed_population=(
            "population",
            "sum"
        ),
    )
    .sort_values(
        "mean_priority",
        ascending=False
    )
)


print("\nSUBDISTRICT PRIORITY SUMMARY")
print("=" * 110)

print(
    summary
    .round(2)
    .to_string()
)


# ============================================================
# 11. SAVE
# ============================================================

gdf.to_file(
    OUTPUT,
    layer="flood_priority",
    driver="GPKG"
)


(
    gdf
    .sort_values(
        "flood_priority_score",
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
