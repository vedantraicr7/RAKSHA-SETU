from pathlib import Path

import pandas as pd
import pulp


# ==========================================================
# PATHS
# ==========================================================

INPUT = Path(
    "data/processed/relocation/"
    "final_relocation_recommendations.csv"
)

OUTPUT_ALLOCATIONS = Path(
    "data/processed/relocation/"
    "district_optimized_allocations.csv"
)

OUTPUT_SITE_LOAD = Path(
    "data/processed/relocation/"
    "district_site_load_summary.csv"
)


# ==========================================================
# CONFIGURATION
# ==========================================================

# Keep 10% reserve capacity.
CAPACITY_SAFETY_FACTOR = 1.10

MAX_DISTANCE_KM = 25.0

# Do not use very weak relocation alternatives
# in the district optimizer.
MIN_FINAL_FEASIBILITY = 40.0

# Site quality only affects Stage 2.
FEASIBILITY_WEIGHT = 0.70
PROXIMITY_WEIGHT = 0.30


# ==========================================================
# LOAD DATA
# ==========================================================

print("=" * 90)
print("RAKSHA-SETU DISTRICT RELOCATION OPTIMIZER V2")
print("LEXICOGRAPHIC RISK-WEIGHTED POPULATION OPTIMIZATION")
print("=" * 90)

print("\nLoading relocation recommendations...")

df = pd.read_csv(INPUT)

df["vlcode"] = df["vlcode"].astype(str)

df["patch_id"] = pd.to_numeric(
    df["patch_id"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "vlcode",
        "patch_id",
        "population",
        "multihazard_priority_100",
        "distance_km",
        "final_feasibility_score",
        "estimated_capacity_people",
    ]
).copy()

df["patch_id"] = (
    df["patch_id"]
    .astype(int)
)


# ==========================================================
# REMOVE DUPLICATE HABITATION-SITE PAIRS
# ==========================================================

df = (
    df
    .sort_values(
        "final_feasibility_score",
        ascending=False
    )
    .drop_duplicates(
        subset=[
            "vlcode",
            "patch_id"
        ],
        keep="first"
    )
)


print(
    "Candidate habitation-site pairs:",
    len(df)
)

print(
    "Habitations:",
    df["vlcode"].nunique()
)

print(
    "Candidate sites:",
    df["patch_id"].nunique()
)


# ==========================================================
# FILTER CANDIDATES
# ==========================================================

df = df[
    df["distance_km"]
    <=
    MAX_DISTANCE_KM
].copy()

df = df[
    df["estimated_capacity_people"]
    >
    0
].copy()

df = df[
    df["final_feasibility_score"]
    >=
    MIN_FINAL_FEASIBILITY
].copy()


print(
    "\nPairs after quality and feasibility filtering:",
    len(df)
)

print(
    "Habitations still represented:",
    df["vlcode"].nunique()
)

print(
    "Sites still represented:",
    df["patch_id"].nunique()
)


if df.empty:
    raise RuntimeError(
        "No candidate pairs remain after filtering."
    )


# ==========================================================
# NORMALIZED COMPONENTS
# ==========================================================

df["priority_component"] = (
    df["multihazard_priority_100"]
    .clip(0, 100)
    /
    100.0
)

df["feasibility_component"] = (
    df["final_feasibility_score"]
    .clip(0, 100)
    /
    100.0
)

df["proximity_component"] = (
    1.0
    -
    (
        df["distance_km"]
        .clip(
            lower=0,
            upper=MAX_DISTANCE_KM
        )
        /
        MAX_DISTANCE_KM
    )
)


# ==========================================================
# SITE QUALITY
# ==========================================================
#
# IMPORTANT:
#
# This is NOT the primary objective.
#
# First we maximize risk-weighted population.
# Only then do we select the best-quality allocation.
# ==========================================================

df["site_quality_score"] = (

    FEASIBILITY_WEIGHT
    *
    df["feasibility_component"]

    +

    PROXIMITY_WEIGHT
    *
    df["proximity_component"]
)


# ==========================================================
# RISK-WEIGHTED POPULATION
# ==========================================================
#
# Example:
#
# Population = 1000
# Priority = 80
#
# Risk-weighted population = 800
#
# This allows district planning to prioritize both:
#
#     risk severity
#     population exposed
#
# ==========================================================

df["risk_weighted_population"] = (

    df["population"]
    *
    df["priority_component"]
)


# ==========================================================
# SETS
# ==========================================================

habitations = sorted(
    df["vlcode"].unique()
)

sites = sorted(
    df["patch_id"].unique()
)


# ==========================================================
# LOOKUPS
# ==========================================================

population = (
    df
    .groupby("vlcode")["population"]
    .first()
    .to_dict()
)

priority_score = (
    df
    .groupby("vlcode")[
        "multihazard_priority_100"
    ]
    .first()
    .to_dict()
)

priority_component = {
    habitation:
        priority_score[habitation]
        /
        100.0

    for habitation in habitations
}


site_capacity = (
    df
    .groupby("patch_id")[
        "estimated_capacity_people"
    ]
    .max()
    .to_dict()
)


# ==========================================================
# USABLE CAPACITY
# ==========================================================
#
# Existing capacity is based on the prototype's
# 100 m²/person assumption.
#
# We preserve 10% spare capacity.
# ==========================================================

usable_site_capacity = {

    site:
        site_capacity[site]
        /
        CAPACITY_SAFETY_FACTOR

    for site in sites
}


# ==========================================================
# PAIR LOOKUP
# ==========================================================

pair_rows = {}

for _, row in df.iterrows():

    key = (
        row["vlcode"],
        int(row["patch_id"])
    )

    pair_rows[key] = row


# ==========================================================
# OPTIMIZATION MODEL
# ==========================================================

model = pulp.LpProblem(
    "RAKSHA_SETU_District_Relocation_V2",
    pulp.LpMaximize
)


# ==========================================================
# BINARY ASSIGNMENT VARIABLES
# ==========================================================
#
# x[i,j] = 1
#
# habitation i is assigned to site j
#
# x[i,j] = 0 otherwise
# ==========================================================

x = {}

for habitation, site in pair_rows:

    x[
        (
            habitation,
            site
        )
    ] = pulp.LpVariable(

        f"x_{habitation}_{site}",

        lowBound=0,
        upBound=1,

        cat="Binary"
    )


# ==========================================================
# CONSTRAINT 1
# ONE RELOCATION SITE PER HABITATION
# ==========================================================

for habitation in habitations:

    variables = [

        x[
            (
                h,
                site
            )
        ]

        for h, site in x

        if h == habitation
    ]

    if variables:

        model += (

            pulp.lpSum(
                variables
            )
            <=
            1,

            f"OneSite_{habitation}"
        )


# ==========================================================
# CONSTRAINT 2
# SHARED DISTRICT SITE CAPACITY
# ==========================================================

for site in sites:

    site_population = []

    for habitation in habitations:

        key = (
            habitation,
            site
        )

        if key not in x:
            continue

        site_population.append(

            population[habitation]
            *
            x[key]
        )

    if site_population:

        model += (

            pulp.lpSum(
                site_population
            )
            <=
            usable_site_capacity[site],

            f"Capacity_{site}"
        )


# ==========================================================
# STAGE 1 OBJECTIVE
# ==========================================================
#
# MAXIMIZE RISK-WEIGHTED POPULATION PROTECTED
#
# Population × Hazard Priority
#
# This is the primary government planning objective.
# ==========================================================

primary_objective = pulp.lpSum(

    population[habitation]
    *
    priority_component[habitation]
    *
    variable

    for (
        habitation,
        site
    ), variable in x.items()
)


model += primary_objective


# ==========================================================
# STAGE 1 SOLVE
# ==========================================================

solver = pulp.PULP_CBC_CMD(
    msg=False
)

print("\nSTAGE 1")
print(
    "Maximizing risk-weighted population protected..."
)

model.solve(solver)

stage1_status = (
    pulp.LpStatus[
        model.status
    ]
)

print(
    "Stage 1 status:",
    stage1_status
)


if stage1_status != "Optimal":

    raise RuntimeError(
        "Stage 1 optimization was not optimal."
    )


maximum_risk_weighted_population = (
    pulp.value(
        primary_objective
    )
)

print(
    "Maximum protected risk-weighted population:",
    round(
        maximum_risk_weighted_population,
        3
    )
)


# ==========================================================
# LOCK STAGE 1 OPTIMUM
# ==========================================================
#
# Stage 2 is NOT allowed to sacrifice meaningful
# risk-weighted population just to obtain nicer sites.
# ==========================================================

PRIMARY_TOLERANCE = 0.001

model += (

    primary_objective
    >=
    maximum_risk_weighted_population
    -
    PRIMARY_TOLERANCE,

    "Preserve_Maximum_Risk_Weighted_Population"
)


# ==========================================================
# STAGE 2 OBJECTIVE
# ==========================================================
#
# Among allocations that preserve Stage 1,
# maximize population-weighted site quality.
#
# Site quality considers:
#
# 70% final feasibility
# 30% proximity
# ==========================================================

secondary_objective = pulp.lpSum(

    population[habitation]
    *
    float(
        pair_rows[
            (
                habitation,
                site
            )
        ]["site_quality_score"]
    )
    *
    variable

    for (
        habitation,
        site
    ), variable in x.items()
)


model.setObjective(
    secondary_objective
)


# ==========================================================
# STAGE 2 SOLVE
# ==========================================================

print("\nSTAGE 2")

print(
    "Selecting highest-quality allocation "
    "without reducing Stage 1 optimum..."
)

model.solve(solver)

stage2_status = (
    pulp.LpStatus[
        model.status
    ]
)

print(
    "Stage 2 status:",
    stage2_status
)


if stage2_status != "Optimal":

    raise RuntimeError(
        "Stage 2 optimization was not optimal."
    )


# ==========================================================
# EXTRACT ASSIGNMENTS
# ==========================================================

allocation_rows = []

assigned_habitations = set()


for (
    habitation,
    site
), variable in x.items():

    value = variable.value()

    if value is None:
        continue

    if value < 0.5:
        continue

    row = pair_rows[
        (
            habitation,
            site
        )
    ]

    assigned_habitations.add(
        habitation
    )

    allocation_rows.append({

        "vlcode":
            habitation,

        "village":
            row["village"],

        "subdistric":
            row["subdistric"],

        "population":
            row["population"],

        "multihazard_priority_100":
            row[
                "multihazard_priority_100"
            ],

        "risk_weighted_population":
            row[
                "risk_weighted_population"
            ],

        "patch_id":
            site,

        "area_ha":
            row["area_ha"],

        "distance_km":
            row["distance_km"],

        "site_flood":
            row["site_flood"],

        "site_landslide":
            row["site_landslide"],

        "site_slope_deg":
            row["site_slope_deg"],

        "site_road_dist_m":
            row["site_road_dist_m"],

        "final_feasibility_score":
            row[
                "final_feasibility_score"
            ],

        "site_quality_score":
            row[
                "site_quality_score"
            ]
            *
            100.0,

        "allocation_status":
            "Optimally Allocated",

        "allocation_reason":
            (
                "Selected by district-level "
                "risk-weighted population optimization"
            )
    })


allocation_df = pd.DataFrame(
    allocation_rows
)


# ==========================================================
# UNALLOCATED HABITATIONS
# ==========================================================

unallocated_rows = []


for habitation in habitations:

    if habitation in assigned_habitations:
        continue

    candidates = (
        df[
            df["vlcode"]
            ==
            habitation
        ]
        .sort_values(
            "final_feasibility_score",
            ascending=False
        )
    )

    source = candidates.iloc[0]

    unallocated_rows.append({

        "vlcode":
            habitation,

        "village":
            source["village"],

        "subdistric":
            source["subdistric"],

        "population":
            source["population"],

        "multihazard_priority_100":
            source[
                "multihazard_priority_100"
            ],

        "risk_weighted_population":
            source[
                "risk_weighted_population"
            ],

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
            "Unallocated - District Constraint",

        "allocation_reason":
            (
                "No compatible site could be assigned "
                "without reducing the maximum protected "
                "risk-weighted population"
            ),

        "candidate_site_count":
            len(candidates)
    })


if unallocated_rows:

    unallocated_df = pd.DataFrame(
        unallocated_rows
    )

    allocation_df = pd.concat(
        [
            allocation_df,
            unallocated_df
        ],
        ignore_index=True
    )


# ==========================================================
# SITE LOAD SUMMARY
# ==========================================================

site_rows = []


for site in sites:

    assigned = allocation_df[
        allocation_df["patch_id"]
        ==
        site
    ]

    assigned_population = (
        assigned["population"].sum()
        if len(assigned)
        else 0.0
    )

    assigned_risk_population = (
        assigned[
            "risk_weighted_population"
        ].sum()
        if len(assigned)
        else 0.0
    )

    raw_capacity = (
        site_capacity[site]
    )

    usable_capacity = (
        usable_site_capacity[site]
    )

    remaining_capacity = (
        usable_capacity
        -
        assigned_population
    )

    utilization = (

        assigned_population
        /
        usable_capacity

        if usable_capacity > 0

        else 0.0
    )

    site_rows.append({

        "patch_id":
            site,

        "raw_capacity_people":
            raw_capacity,

        "usable_capacity_people":
            usable_capacity,

        "assigned_population":
            assigned_population,

        "assigned_risk_weighted_population":
            assigned_risk_population,

        "remaining_capacity":
            remaining_capacity,

        "utilization_percent":
            utilization
            *
            100.0,

        "assigned_habitations":
            len(assigned)
    })


site_load_df = pd.DataFrame(
    site_rows
)


# ==========================================================
# SORT OUTPUTS
# ==========================================================

allocation_df = (
    allocation_df
    .sort_values(
        "multihazard_priority_100",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)

site_load_df = (
    site_load_df
    .sort_values(
        "assigned_population",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


# ==========================================================
# DISTRICT SUMMARY
# ==========================================================

total_population = sum(
    population.values()
)

total_risk_weighted_population = sum(

    population[h]
    *
    priority_component[h]

    for h in habitations
)


allocated_mask = (

    allocation_df[
        "allocation_status"
    ]
    ==
    "Optimally Allocated"
)


allocated_count = int(
    allocated_mask.sum()
)

unallocated_count = int(
    (
        ~allocated_mask
    ).sum()
)

allocated_population = (

    allocation_df.loc[
        allocated_mask,
        "population"
    ]
    .sum()
)

protected_risk_weighted_population = (

    allocation_df.loc[
        allocated_mask,
        "risk_weighted_population"
    ]
    .sum()
)


population_allocation_rate = (

    allocated_population
    /
    total_population
    *
    100.0

    if total_population > 0

    else 0.0
)


risk_protection_rate = (

    protected_risk_weighted_population
    /
    total_risk_weighted_population
    *
    100.0

    if total_risk_weighted_population > 0

    else 0.0
)


# ==========================================================
# SAVE
# ==========================================================

OUTPUT_ALLOCATIONS.parent.mkdir(
    parents=True,
    exist_ok=True
)

allocation_df.to_csv(
    OUTPUT_ALLOCATIONS,
    index=False
)

site_load_df.to_csv(
    OUTPUT_SITE_LOAD,
    index=False
)


# ==========================================================
# PRINT RESULTS
# ==========================================================

print("\n" + "=" * 90)
print("DISTRICT OPTIMIZATION V2 SUMMARY")
print("=" * 90)

print(
    "Priority habitations considered:",
    len(habitations)
)

print(
    "Optimally allocated:",
    allocated_count
)

print(
    "Unallocated:",
    unallocated_count
)

print(
    "Population considered:",
    int(total_population)
)

print(
    "Population allocated:",
    int(allocated_population)
)

print(
    "Population allocation rate:",
    round(
        population_allocation_rate,
        2
    ),
    "%"
)

print(
    "Risk-weighted population available:",
    round(
        total_risk_weighted_population,
        2
    )
)

print(
    "Risk-weighted population protected:",
    round(
        protected_risk_weighted_population,
        2
    )
)

print(
    "Risk-weighted protection rate:",
    round(
        risk_protection_rate,
        2
    ),
    "%"
)


print("\nTOP DISTRICT ALLOCATIONS")
print("=" * 90)


display_columns = [

    "village",
    "subdistric",
    "population",
    "multihazard_priority_100",
    "risk_weighted_population",
    "patch_id",
    "distance_km",
    "final_feasibility_score",
    "site_quality_score",
    "allocation_status"
]


print(
    allocation_df[
        display_columns
    ]
    .head(25)
    .to_string(
        index=False
    )
)


print("\nUNALLOCATED HABITATIONS")
print("=" * 90)


unallocated_display = allocation_df[
    allocation_df[
        "allocation_status"
    ]
    !=
    "Optimally Allocated"
]


if len(unallocated_display) == 0:

    print(
        "None — every habitation received an allocation."
    )

else:

    print(
        unallocated_display[
            [
                "village",
                "subdistric",
                "population",
                "multihazard_priority_100",
                "risk_weighted_population",
                "allocation_status"
            ]
        ]
        .to_string(
            index=False
        )
    )


print("\nSITE LOAD SUMMARY")
print("=" * 90)


print(
    site_load_df[
        [
            "patch_id",
            "usable_capacity_people",
            "assigned_population",
            "remaining_capacity",
            "utilization_percent",
            "assigned_habitations"
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print("\nSaved:")

print(
    OUTPUT_ALLOCATIONS
)

print(
    OUTPUT_SITE_LOAD
)

print("\nDONE.")
