from pathlib import Path

import pandas as pd
import numpy as np


INPUT = Path(
    "data/processed/relocation/"
    "priority_habitation_candidate_ranking.csv"
)

OUTPUT = Path(
    "data/processed/relocation/"
    "priority_habitation_candidate_feasibility.csv"
)


# ==========================================================
# CONFIGURATION
# ==========================================================

# Prototype assumption:
# gross land requirement per person
LAND_M2_PER_PERSON = 100.0

# Require some spare capacity rather than exact equality
MIN_CAPACITY_RATIO = 1.10


print("Loading habitation-site ranking...")

df = pd.read_csv(INPUT)

print(
    "Habitation-site pairs:",
    len(df)
)


# ==========================================================
# REQUIRED LAND
# ==========================================================

df["required_area_m2"] = (
    df["population"]
    *
    LAND_M2_PER_PERSON
)

df["required_area_ha"] = (
    df["required_area_m2"]
    /
    10000.0
)


# ==========================================================
# SITE CAPACITY
# ==========================================================

df["estimated_capacity_people"] = (
    df["area_ha"]
    *
    10000.0
    /
    LAND_M2_PER_PERSON
)


df["capacity_ratio"] = (
    df["estimated_capacity_people"]
    /
    df["population"]
)


# ==========================================================
# FEASIBILITY
# ==========================================================

df["capacity_feasible"] = (
    df["capacity_ratio"]
    >= MIN_CAPACITY_RATIO
)


def capacity_class(ratio):

    if ratio >= 3.0:
        return "High spare capacity"

    if ratio >= 1.5:
        return "Good spare capacity"

    if ratio >= 1.10:
        return "Adequate"

    if ratio >= 1.0:
        return "Marginal"

    return "Insufficient"


df["capacity_class"] = (
    df["capacity_ratio"]
    .apply(capacity_class)
)


# ==========================================================
# DISTANCE FEASIBILITY
# ==========================================================

def distance_class(km):

    if km <= 5:
        return "Very Near"

    if km <= 10:
        return "Near"

    if km <= 15:
        return "Moderate"

    if km <= 25:
        return "Far"

    return "Very Far"


df["distance_class"] = (
    df["distance_km"]
    .apply(distance_class)
)


# ==========================================================
# FINAL FEASIBILITY SCORE
# ==========================================================
#
# Existing site score already considers:
# distance, area, road, flood, landslide, slope.
#
# We now add a strong capacity penalty.
# ==========================================================

capacity_score = np.clip(
    df["capacity_ratio"]
    / 2.0,
    0,
    1
)


df["final_feasibility_score"] = (
      0.75
      * (
          df["relocation_site_score"]
          / 100.0
      )

    + 0.25
      * capacity_score
) * 100


# Hard reject clearly undersized sites
df.loc[
    ~df["capacity_feasible"],
    "final_feasibility_score"
] *= 0.40


# ==========================================================
# RE-RANK WITHIN EACH HABITATION
# ==========================================================

df["feasible_rank"] = (
    df
    .groupby("vlcode")[
        "final_feasibility_score"
    ]
    .rank(
        ascending=False,
        method="first"
    )
    .astype(int)
)


df = (
    df
    .sort_values(
        [
            "multihazard_priority_100",
            "feasible_rank"
        ],
        ascending=[
            False,
            True
        ]
    )
    .reset_index(
        drop=True
    )
)


# ==========================================================
# QA
# ==========================================================

print("\nCAPACITY FEASIBILITY SUMMARY")
print("=" * 100)

print(
    "Capacity-feasible pairs:",
    int(
        df["capacity_feasible"]
        .sum()
    )
)

print(
    "Capacity-infeasible pairs:",
    int(
        (~df["capacity_feasible"])
        .sum()
    )
)

print(
    "\nCapacity classes:"
)

print(
    df["capacity_class"]
    .value_counts()
)


print(
    "\nDistance classes:"
)

print(
    df["distance_class"]
    .value_counts()
)


# ==========================================================
# BEST OPTION PER HABITATION
# ==========================================================

best = (
    df
    .sort_values(
        [
            "vlcode",
            "final_feasibility_score"
        ],
        ascending=[
            True,
            False
        ]
    )
    .groupby(
        "vlcode",
        as_index=False
    )
    .first()
)


print(
    "\nBEST RELOCATION OPTION "
    "FOR EACH PRIORITY HABITATION"
)

print("=" * 180)

display_cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",

    "patch_id",
    "area_ha",

    "required_area_ha",
    "estimated_capacity_people",
    "capacity_ratio",
    "capacity_class",
    "capacity_feasible",

    "distance_km",
    "distance_class",

    "site_flood",
    "site_landslide",
    "site_slope_deg",
    "site_road_dist_m",

    "final_feasibility_score",
]


print(
    best[
        display_cols
    ]
    .sort_values(
        "final_feasibility_score",
        ascending=False
    )
    .to_string(
        index=False
    )
)


# ==========================================================
# SAVE
# ==========================================================

df.to_csv(
    OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
