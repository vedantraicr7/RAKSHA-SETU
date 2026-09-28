from pathlib import Path
import pandas as pd


# ==========================================================
# PATHS
# ==========================================================

RECOMMENDATIONS = Path(
    "data/processed/relocation/"
    "final_relocation_recommendations.csv"
)

OPTIMIZED = Path(
    "data/processed/relocation/"
    "district_optimized_allocations.csv"
)

OUTPUT = Path(
    "data/processed/relocation/"
    "district_optimized_allocations_complete.csv"
)


# ==========================================================
# CONFIGURATION
# ==========================================================

MIN_FINAL_FEASIBILITY = 40.0
MAX_DISTANCE_KM = 25.0


# ==========================================================
# LOAD
# ==========================================================

print("=" * 90)
print("RAKSHA-SETU DISTRICT OPTIMIZATION FINALIZATION")
print("=" * 90)

recommendations = pd.read_csv(
    RECOMMENDATIONS
)

optimized = pd.read_csv(
    OPTIMIZED
)

recommendations["vlcode"] = (
    recommendations["vlcode"]
    .astype(str)
)

optimized["vlcode"] = (
    optimized["vlcode"]
    .astype(str)
)


# ==========================================================
# COMPLETE HABITATION SET
# ==========================================================

all_habitations = (
    recommendations
    .sort_values(
        "final_feasibility_score",
        ascending=False
    )
    .drop_duplicates(
        subset=["vlcode"]
    )
    .copy()
)


all_codes = set(
    all_habitations["vlcode"]
)

optimized_codes = set(
    optimized["vlcode"]
)

missing_codes = (
    all_codes
    -
    optimized_codes
)


print(
    "Habitations in recommendation dataset:",
    len(all_codes)
)

print(
    "Habitations returned by optimizer:",
    len(optimized_codes)
)

print(
    "Missing after optimization:",
    len(missing_codes)
)


# ==========================================================
# ADD AUDIT FIELDS
# ==========================================================

optimized[
    "best_rejected_patch_id"
] = pd.NA

optimized[
    "best_rejected_distance_km"
] = pd.NA

optimized[
    "best_rejected_feasibility_score"
] = pd.NA


# ==========================================================
# RECONCILE MISSING HABITATIONS
# ==========================================================

extra_rows = []


for vlcode in sorted(missing_codes):

    candidates = (
        recommendations[
            recommendations["vlcode"]
            ==
            vlcode
        ]
        .sort_values(
            "final_feasibility_score",
            ascending=False
        )
        .copy()
    )

    best = candidates.iloc[0]

    acceptable = candidates[
        (
            candidates[
                "final_feasibility_score"
            ]
            >=
            MIN_FINAL_FEASIBILITY
        )
        &
        (
            candidates[
                "distance_km"
            ]
            <=
            MAX_DISTANCE_KM
        )
        &
        (
            candidates[
                "estimated_capacity_people"
            ]
            >
            0
        )
    ]


    # ======================================================
    # REASON
    # ======================================================

    if acceptable.empty:

        status = (
            "Unallocated - No Candidate "
            "Above Quality Threshold"
        )

        reason = (
            f"Best available candidate scored "
            f"{best['final_feasibility_score']:.2f}, "
            f"below minimum accepted feasibility "
            f"threshold of "
            f"{MIN_FINAL_FEASIBILITY:.0f}."
        )

    else:

        status = (
            "Unallocated - District Constraint"
        )

        reason = (
            "Acceptable candidates existed, "
            "but no allocation was selected by "
            "district optimization."
        )


    # ======================================================
    # RESULT ROW
    # ======================================================

    extra_rows.append({

        "vlcode":
            vlcode,

        "village":
            best["village"],

        "subdistric":
            best["subdistric"],

        "population":
            best["population"],

        "multihazard_priority_100":
            best[
                "multihazard_priority_100"
            ],

        "risk_weighted_population":
            (
                best["population"]
                *
                best[
                    "multihazard_priority_100"
                ]
                /
                100.0
            ),

        # No actual allocation
        "patch_id":
            pd.NA,

        "area_ha":
            pd.NA,

        "distance_km":
            pd.NA,

        "site_flood":
            pd.NA,

        "site_landslide":
            pd.NA,

        "site_slope_deg":
            pd.NA,

        "site_road_dist_m":
            pd.NA,

        "final_feasibility_score":
            pd.NA,

        "site_quality_score":
            pd.NA,

        "allocation_status":
            status,

        "allocation_reason":
            reason,

        # Keep rejected candidate separately
        "best_rejected_patch_id":
            best["patch_id"],

        "best_rejected_distance_km":
            best["distance_km"],

        "best_rejected_feasibility_score":
            best[
                "final_feasibility_score"
            ]
    })


# ==========================================================
# COMBINE
# ==========================================================

if extra_rows:

    optimized = pd.concat(
        [
            optimized,
            pd.DataFrame(extra_rows)
        ],
        ignore_index=True
    )


optimized = (
    optimized
    .sort_values(
        "multihazard_priority_100",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


# ==========================================================
# DISTRICT SUMMARY
# ==========================================================

allocated = optimized[
    optimized["allocation_status"]
    ==
    "Optimally Allocated"
]

district_constraint = optimized[
    optimized["allocation_status"]
    ==
    "Unallocated - District Constraint"
]

quality_rejected = optimized[
    optimized["allocation_status"]
    ==
    (
        "Unallocated - No Candidate "
        "Above Quality Threshold"
    )
]


total_population = (
    optimized["population"].sum()
)

allocated_population = (
    allocated["population"].sum()
)

total_risk_weighted = (
    optimized[
        "risk_weighted_population"
    ].sum()
)

protected_risk_weighted = (
    allocated[
        "risk_weighted_population"
    ].sum()
)


# ==========================================================
# SAVE
# ==========================================================

optimized.to_csv(
    OUTPUT,
    index=False
)


# ==========================================================
# DISPLAY
# ==========================================================

print("\n" + "=" * 90)
print("FINAL DISTRICT DECISION SUMMARY")
print("=" * 90)

print(
    "Total habitations:",
    len(optimized)
)

print(
    "Optimally allocated:",
    len(allocated)
)

print(
    "Unallocated - district constraint:",
    len(district_constraint)
)

print(
    "Unallocated - quality threshold:",
    len(quality_rejected)
)

print(
    "Total population:",
    int(total_population)
)

print(
    "Allocated population:",
    int(allocated_population)
)

print(
    "Population allocation rate:",
    round(
        allocated_population
        /
        total_population
        *
        100,
        2
    ),
    "%"
)

print(
    "Risk-weighted population:",
    round(
        total_risk_weighted,
        2
    )
)

print(
    "Protected risk-weighted population:",
    round(
        protected_risk_weighted,
        2
    )
)

print(
    "Risk-weighted protection rate:",
    round(
        protected_risk_weighted
        /
        total_risk_weighted
        *
        100,
        2
    ),
    "%"
)


print("\nUNALLOCATED DECISIONS")
print("=" * 90)

print(
    optimized[
        optimized["allocation_status"]
        !=
        "Optimally Allocated"
    ][
        [
            "village",
            "subdistric",
            "population",
            "multihazard_priority_100",
            "allocation_status",
            "allocation_reason"
        ]
    ]
    .to_string(
        index=False
    )
)


print("\nSaved:")
print(
    OUTPUT
)

print("\nDONE.")
