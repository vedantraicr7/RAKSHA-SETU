from pathlib import Path

import pandas as pd


INPUT = Path(
    "data/processed/relocation/"
    "priority_habitation_candidate_feasibility.csv"
)

OUTPUT = Path(
    "data/processed/relocation/"
    "final_relocation_recommendations.csv"
)


print("Loading feasibility results...")

df = pd.read_csv(INPUT)

print("Pairs:", len(df))


# =========================================================
# KEEP ONLY CAPACITY-FEASIBLE SITES
# =========================================================

feasible = df[
    df["capacity_feasible"] == True
].copy()

print(
    "Capacity-feasible pairs:",
    len(feasible)
)


# =========================================================
# RANK FEASIBLE OPTIONS
# =========================================================

feasible["recommendation_rank"] = (
    feasible
    .groupby("vlcode")[
        "final_feasibility_score"
    ]
    .rank(
        ascending=False,
        method="first"
    )
    .astype(int)
)


# Keep maximum 3 alternatives per habitation

top = feasible[
    feasible["recommendation_rank"] <= 3
].copy()


# =========================================================
# RECOMMENDATION STATUS
# =========================================================

def recommendation_status(row):

    score = row["final_feasibility_score"]
    distance = row["distance_km"]

    if score >= 70 and distance <= 15:
        return "Strong Candidate"

    if score >= 55 and distance <= 25:
        return "Suitable Candidate"

    if score >= 40:
        return "Conditional Candidate"

    return "Weak Candidate"


top["recommendation_status"] = (
    top.apply(
        recommendation_status,
        axis=1
    )
)


# =========================================================
# HUMAN-READABLE EXPLANATION
# =========================================================

def explanation(row):

    reasons = []

    reasons.append(
        f"{row['area_ha']:.1f} ha available"
    )

    reasons.append(
        f"capacity ratio {row['capacity_ratio']:.1f}x"
    )

    reasons.append(
        f"{row['distance_km']:.1f} km from habitation"
    )

    reasons.append(
        f"flood score {row['site_flood']:.1f}"
    )

    reasons.append(
        f"landslide score {row['site_landslide']:.1f}"
    )

    reasons.append(
        f"mean slope {row['site_slope_deg']:.1f}°"
    )

    return "; ".join(reasons)


top["recommendation_reason"] = (
    top.apply(
        explanation,
        axis=1
    )
)


# =========================================================
# FINAL COLUMNS
# =========================================================

columns = [
    "village",
    "subdistric",
    "vlcode",
    "population",

    "multihazard_priority_100",

    "recommendation_rank",
    "recommendation_status",

    "patch_id",
    "area_ha",
    "required_area_ha",
    "estimated_capacity_people",
    "capacity_ratio",

    "distance_km",

    "site_flood",
    "site_landslide",
    "site_slope_deg",
    "site_road_dist_m",

    "final_feasibility_score",

    "recommendation_reason",
]


top = top[columns]


top = top.sort_values(
    [
        "multihazard_priority_100",
        "recommendation_rank"
    ],
    ascending=[
        False,
        True
    ]
)


# =========================================================
# QA
# =========================================================

print("\nFINAL RECOMMENDATION SUMMARY")
print("=" * 80)

print(
    "Habitations with feasible recommendations:",
    top["vlcode"].nunique()
)

print(
    "Total recommendations:",
    len(top)
)

print("\nRecommendation status:")

print(
    top["recommendation_status"]
    .value_counts()
)


print(
    "\nTOP PRIORITY RECOMMENDATIONS"
)

print("=" * 160)

print(
    top.head(30)
    .to_string(index=False)
)


# =========================================================
# SAVE
# =========================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

top.to_csv(
    OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
