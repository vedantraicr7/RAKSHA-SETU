from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


HABITATIONS = Path(
    "data/processed/"
    "raigad_habitations_multihazard.gpkg"
)

PAIR_RANKING = Path(
    "data/processed/relocation/"
    "priority_habitation_candidate_ranking.csv"
)

FEASIBILITY = Path(
    "data/processed/relocation/"
    "priority_habitation_candidate_feasibility.csv"
)

FINAL_RECOMMENDATIONS = Path(
    "data/processed/relocation/"
    "final_relocation_recommendations.csv"
)

OUTPUT_CSV = Path(
    "data/processed/relocation/"
    "complete_priority_habitation_decisions.csv"
)

OUTPUT_GPKG = Path(
    "data/processed/relocation/"
    "raigad_complete_relocation_decisions.gpkg"
)


TOP_N = 40


# =========================================================
# LOAD
# =========================================================

print("Loading datasets...")

hab = gpd.read_file(
    HABITATIONS
)

pairs = pd.read_csv(
    PAIR_RANKING
)

feas = pd.read_csv(
    FEASIBILITY
)

rec = pd.read_csv(
    FINAL_RECOMMENDATIONS
)


# Normalize IDs
hab["vlcode"] = (
    hab["vlcode"]
    .astype(str)
)

pairs["vlcode"] = (
    pairs["vlcode"]
    .astype(str)
)

feas["vlcode"] = (
    feas["vlcode"]
    .astype(str)
)

rec["vlcode"] = (
    rec["vlcode"]
    .astype(str)
)


# =========================================================
# TOP 40 PRIORITY HABITATIONS
# =========================================================

priority = (
    hab[
        hab[
            "multihazard_priority_100"
        ]
        .notna()
    ]
    .sort_values(
        "multihazard_priority_100",
        ascending=False
    )
    .head(TOP_N)
    .copy()
)


print(
    "Priority habitations:",
    len(priority)
)


# =========================================================
# BEST FEASIBLE RECOMMENDATION
# =========================================================

best_rec = (
    rec[
        rec[
            "recommendation_rank"
        ] == 1
    ]
    .copy()
)


best_lookup = (
    best_rec
    .set_index("vlcode")
)


# =========================================================
# DIAGNOSTIC SETS
# =========================================================

hab_with_any_candidate = set(
    pairs["vlcode"]
    .unique()
)

hab_with_feasible_pair = set(
    feas.loc[
        feas["capacity_feasible"] == True,
        "vlcode"
    ]
    .unique()
)

hab_with_recommendation = set(
    best_rec["vlcode"]
    .unique()
)


# =========================================================
# BUILD DECISION RECORDS
# =========================================================

records = []


for _, row in priority.iterrows():

    code = row["vlcode"]

    record = {
        "village":
            row["village"],

        "subdistric":
            row["subdistric"],

        "vlcode":
            code,

        "population":
            row["population"],

        "multihazard_priority_100":
            row[
                "multihazard_priority_100"
            ],

        "multihazard_priority_percentile":
            row[
                "multihazard_priority_percentile"
            ],

        "dominant_hazard":
            row[
                "dominant_hazard"
            ],
    }


    # -----------------------------------------------------
    # Recommendation exists
    # -----------------------------------------------------

    if code in hab_with_recommendation:

        r = best_lookup.loc[
            code
        ]

        record.update(
            {
                "decision_status":
                    "Recommended",

                "decision_reason":
                    (
                        "Capacity-feasible strict "
                        "candidate identified"
                    ),

                "patch_id":
                    int(
                        r["patch_id"]
                    ),

                "recommendation_status":
                    r[
                        "recommendation_status"
                    ],

                "area_ha":
                    r["area_ha"],

                "required_area_ha":
                    r[
                        "required_area_ha"
                    ],

                "capacity_ratio":
                    r[
                        "capacity_ratio"
                    ],

                "distance_km":
                    r["distance_km"],

                "site_flood":
                    r["site_flood"],

                "site_landslide":
                    r[
                        "site_landslide"
                    ],

                "site_slope_deg":
                    r[
                        "site_slope_deg"
                    ],

                "site_road_dist_m":
                    r[
                        "site_road_dist_m"
                    ],

                "final_feasibility_score":
                    r[
                        "final_feasibility_score"
                    ],
            }
        )


    # -----------------------------------------------------
    # Candidate(s) found but none capacity feasible
    # -----------------------------------------------------

    elif code in hab_with_any_candidate:

        subset = feas[
            feas["vlcode"] == code
        ].copy()

        best_attempt = (
            subset
            .sort_values(
                "final_feasibility_score",
                ascending=False
            )
            .iloc[0]
        )


        record.update(
            {
                "decision_status":
                    "No Capacity-Feasible Site",

                "decision_reason":
                    (
                        "Strict candidate sites were "
                        "identified within 25 km, but "
                        "none met the prototype land-"
                        "capacity requirement."
                    ),

                "patch_id":
                    int(
                        best_attempt[
                            "patch_id"
                        ]
                    ),

                "recommendation_status":
                    "Rejected",

                "area_ha":
                    best_attempt[
                        "area_ha"
                    ],

                "required_area_ha":
                    best_attempt[
                        "required_area_ha"
                    ],

                "capacity_ratio":
                    best_attempt[
                        "capacity_ratio"
                    ],

                "distance_km":
                    best_attempt[
                        "distance_km"
                    ],

                "site_flood":
                    best_attempt[
                        "site_flood"
                    ],

                "site_landslide":
                    best_attempt[
                        "site_landslide"
                    ],

                "site_slope_deg":
                    best_attempt[
                        "site_slope_deg"
                    ],

                "site_road_dist_m":
                    best_attempt[
                        "site_road_dist_m"
                    ],

                "final_feasibility_score":
                    best_attempt[
                        "final_feasibility_score"
                    ],
            }
        )


    # -----------------------------------------------------
    # No strict candidate found within search radius
    # -----------------------------------------------------

    else:

        record.update(
            {
                "decision_status":
                    "No Nearby Strict Site",

                "decision_reason":
                    (
                        "No strict safe-land candidate "
                        "of at least 2 ha was identified "
                        "within the 25 km search radius."
                    ),

                "patch_id":
                    np.nan,

                "recommendation_status":
                    "Not Available",

                "area_ha":
                    np.nan,

                "required_area_ha":
                    (
                        row["population"]
                        / 100.0
                    ),

                "capacity_ratio":
                    np.nan,

                "distance_km":
                    np.nan,

                "site_flood":
                    np.nan,

                "site_landslide":
                    np.nan,

                "site_slope_deg":
                    np.nan,

                "site_road_dist_m":
                    np.nan,

                "final_feasibility_score":
                    np.nan,
            }
        )


    records.append(
        record
    )


decision_df = pd.DataFrame(
    records
)


# =========================================================
# QA
# =========================================================

print(
    "\nCOMPLETE DECISION SUMMARY"
)

print("=" * 100)


print(
    decision_df[
        "decision_status"
    ]
    .value_counts()
)


print(
    "\nHabitations represented:",
    len(decision_df)
)


print(
    "\nNO-FEASIBLE-SITE CASES"
)

print("=" * 140)


problem_cases = (
    decision_df[
        decision_df[
            "decision_status"
        ]
        != "Recommended"
    ]
    .sort_values(
        "multihazard_priority_100",
        ascending=False
    )
)


display_cols = [
    "village",
    "subdistric",
    "vlcode",
    "population",
    "multihazard_priority_100",
    "dominant_hazard",

    "decision_status",
    "decision_reason",

    "patch_id",
    "area_ha",
    "required_area_ha",
    "capacity_ratio",
    "distance_km",
]


print(
    problem_cases[
        display_cols
    ]
    .to_string(
        index=False
    )
)


# =========================================================
# SAVE CSV
# =========================================================

decision_df.to_csv(
    OUTPUT_CSV,
    index=False
)


# =========================================================
# CREATE COMPLETE GIS HABITATION LAYER
# =========================================================

priority_gis = priority[
    [
        "vlcode",
        "geometry"
    ]
].copy()


complete_gis = (
    priority_gis
    .merge(
        decision_df,
        on="vlcode",
        how="left"
    )
)


if OUTPUT_GPKG.exists():
    OUTPUT_GPKG.unlink()


complete_gis.to_file(
    OUTPUT_GPKG,
    layer="priority_decisions",
    driver="GPKG"
)


print("\nSaved:")
print(OUTPUT_CSV)
print(OUTPUT_GPKG)

print("\nDONE.")
