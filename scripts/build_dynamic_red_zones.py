from pathlib import Path
import argparse

import geopandas as gpd
import numpy as np
import pandas as pd


# ==========================================================
# PATHS
# ==========================================================

INPUT = Path(
    "data/processed/"
    "raigad_habitations_multihazard.gpkg"
)

OUTPUT_DIR = Path(
    "data/processed/dynamic_risk"
)

OUTPUT_GPKG = (
    OUTPUT_DIR /
    "dynamic_red_zones.gpkg"
)

OUTPUT_CSV = (
    OUTPUT_DIR /
    "dynamic_red_zones.csv"
)


# ==========================================================
# CONFIGURATION
# ==========================================================
#
# PROTOTYPE SCENARIO PARAMETERS
#
# These are not government standards.
# They describe how strongly the current rainfall
# scenario pushes baseline hazard toward its upper range.
# ==========================================================

FLOOD_RAINFALL_SENSITIVITY = 0.65

LANDSLIDE_RAINFALL_SENSITIVITY = 0.45


# ==========================================================
# URGENCY THRESHOLDS
# ==========================================================
#
# Prototype decision thresholds.
#
# Immediate relocation-planning review can be triggered
# either by:
#
#   1. extremely high absolute dynamic priority
#
# OR
#
#   2. Red Zone + substantial deterioration
#
# ==========================================================

IMMEDIATE_ABSOLUTE_PRIORITY = 80.0

IMMEDIATE_PRIORITY_INCREASE = 5.0


# ==========================================================
# ARGUMENTS
# ==========================================================

parser = argparse.ArgumentParser(
    description=(
        "RAKSHA-SETU Dynamic "
        "Multi-Hazard Red Zone Engine V2"
    )
)

parser.add_argument(
    "--rainfall-trigger",
    type=float,
    default=0.0,
    help=(
        "Scenario trigger from 0 to 1. "
        "0 = baseline, 1 = extreme rainfall."
    )
)

args = parser.parse_args()


rainfall_trigger = float(
    np.clip(
        args.rainfall_trigger,
        0.0,
        1.0
    )
)


# ==========================================================
# START
# ==========================================================

print("=" * 95)

print(
    "RAKSHA-SETU DYNAMIC "
    "MULTI-HAZARD RED ZONE ENGINE V2"
)

print("=" * 95)

print(
    "\nRainfall trigger:",
    rainfall_trigger
)


# ==========================================================
# LOAD DATA
# ==========================================================

print(
    "\nLoading baseline "
    "multi-hazard dataset..."
)

gdf = gpd.read_file(
    INPUT
)

print(
    "Habitations:",
    len(gdf)
)


# ==========================================================
# REQUIRED COLUMNS
# ==========================================================

required_columns = [

    "village",
    "subdistric",
    "vlcode",
    "population",

    "susceptibility_percentile",
    "landslide_percentile",

    "exposure_percentile",
    "vulnerability_percentile",

    "multihazard_priority_100",
    "dominant_hazard",
]


missing_columns = [

    column

    for column
    in required_columns

    if column
    not in gdf.columns
]


if missing_columns:

    raise ValueError(
        "Missing required columns: "
        +
        ", ".join(
            missing_columns
        )
    )


# ==========================================================
# VALID HABITATIONS
# ==========================================================

valid = (

    (gdf["population"] > 0)

    &

    gdf[
        "susceptibility_percentile"
    ].notna()

    &

    gdf[
        "landslide_percentile"
    ].notna()

    &

    gdf[
        "exposure_percentile"
    ].notna()

    &

    gdf[
        "vulnerability_percentile"
    ].notna()

    &

    gdf[
        "multihazard_priority_100"
    ].notna()
)


print(
    "Valid habitations:",
    int(valid.sum())
)


# ==========================================================
# BASELINE HAZARDS
# ==========================================================

baseline_flood = (
    gdf[
        "susceptibility_percentile"
    ]
    .astype(float)
)

baseline_landslide = (
    gdf[
        "landslide_percentile"
    ]
    .astype(float)
)


# ==========================================================
# DYNAMIC HAZARD RESPONSE
# ==========================================================
#
# Hazard is pushed toward 100 according to:
#
# H_dynamic =
#
# H_baseline
# +
# (100 - H_baseline)
# × rainfall_trigger
# × sensitivity
#
# ==========================================================

gdf[
    "dynamic_flood_percentile"
] = (

    baseline_flood

    +

    (
        100.0
        -
        baseline_flood
    )

    *
    FLOOD_RAINFALL_SENSITIVITY

    *
    rainfall_trigger
)


gdf[
    "dynamic_landslide_percentile"
] = (

    baseline_landslide

    +

    (
        100.0
        -
        baseline_landslide
    )

    *
    LANDSLIDE_RAINFALL_SENSITIVITY

    *
    rainfall_trigger
)


gdf[
    "dynamic_flood_percentile"
] = (

    gdf[
        "dynamic_flood_percentile"
    ]
    .clip(
        0,
        100
    )
)


gdf[
    "dynamic_landslide_percentile"
] = (

    gdf[
        "dynamic_landslide_percentile"
    ]
    .clip(
        0,
        100
    )
)


# ==========================================================
# DYNAMIC MULTI-HAZARD SUSCEPTIBILITY
# ==========================================================
#
# Preserve the original RAKSHA-SETU formulation:
#
# H = sqrt(F × L)
#
# ==========================================================

dynamic_flood = (

    gdf[
        "dynamic_flood_percentile"
    ]

    /
    100.0
)


dynamic_landslide = (

    gdf[
        "dynamic_landslide_percentile"
    ]

    /
    100.0
)


gdf[
    "dynamic_multihazard_susceptibility"
] = np.sqrt(

    dynamic_flood

    *

    dynamic_landslide
)


gdf[
    "dynamic_multihazard_susceptibility_100"
] = (

    gdf[
        "dynamic_multihazard_susceptibility"
    ]

    *
    100.0
)


# ==========================================================
# EXPOSURE + VULNERABILITY
# ==========================================================

exposure = (

    gdf[
        "exposure_percentile"
    ]

    /
    100.0
)


vulnerability = (

    gdf[
        "vulnerability_percentile"
    ]

    /
    100.0
)


# ==========================================================
# DYNAMIC PRIORITY
# ==========================================================
#
# Same baseline methodology:
#
# Priority =
#
# [
#   MultiHazard
#   × sqrt(Exposure × Vulnerability)
# ] ^ 0.5
#
# ==========================================================

gdf[
    "dynamic_priority"
] = np.nan


gdf.loc[
    valid,
    "dynamic_priority"
] = (

    gdf.loc[
        valid,
        "dynamic_multihazard_susceptibility"
    ]

    *

    np.sqrt(

        exposure[valid]

        *

        vulnerability[valid]
    )

) ** 0.5


gdf[
    "dynamic_priority_100"
] = (

    gdf[
        "dynamic_priority"
    ]

    *
    100.0
)


# ==========================================================
# CHANGE FROM BASELINE
# ==========================================================

gdf[
    "priority_change"
] = (

    gdf[
        "dynamic_priority_100"
    ]

    -

    gdf[
        "multihazard_priority_100"
    ]
)


# ==========================================================
# FIXED BASELINE ZONE THRESHOLDS
# ==========================================================

baseline_scores = (

    gdf.loc[
        valid,
        "multihazard_priority_100"
    ]
)


YELLOW_THRESHOLD = float(

    baseline_scores.quantile(
        0.40
    )
)


ORANGE_THRESHOLD = float(

    baseline_scores.quantile(
        0.60
    )
)


RED_THRESHOLD = float(

    baseline_scores.quantile(
        0.80
    )
)


print(
    "\nFixed baseline thresholds"
)

print("=" * 70)

print(
    "Yellow threshold:",
    round(
        YELLOW_THRESHOLD,
        3
    )
)

print(
    "Orange threshold:",
    round(
        ORANGE_THRESHOLD,
        3
    )
)

print(
    "Red threshold:",
    round(
        RED_THRESHOLD,
        3
    )
)


# ==========================================================
# ZONE CLASSIFIER
# ==========================================================

def classify_zone(score):

    if pd.isna(score):
        return "Insufficient Data"

    if score >= RED_THRESHOLD:
        return "RED"

    if score >= ORANGE_THRESHOLD:
        return "ORANGE"

    if score >= YELLOW_THRESHOLD:
        return "YELLOW"

    return "GREEN"


# ==========================================================
# BASELINE ZONE
# ==========================================================

gdf[
    "baseline_zone"
] = (

    gdf[
        "multihazard_priority_100"
    ]
    .apply(
        classify_zone
    )
)


# ==========================================================
# DYNAMIC ZONE
# ==========================================================

gdf[
    "dynamic_zone"
] = (

    gdf[
        "dynamic_priority_100"
    ]
    .apply(
        classify_zone
    )
)


# ==========================================================
# ZONE TRANSITION
# ==========================================================

gdf[
    "zone_transition"
] = (

    gdf[
        "baseline_zone"
    ]
    .astype(str)

    +

    " -> "

    +

    gdf[
        "dynamic_zone"
    ]
    .astype(str)
)


gdf[
    "newly_red"
] = (

    (gdf["dynamic_zone"] == "RED")

    &

    (gdf["baseline_zone"] != "RED")
)


# ==========================================================
# IMPROVED RELOCATION URGENCY
# ==========================================================
#
# IMMEDIATE:
#
# A. very high absolute risk
#
# OR
#
# B. Red Zone with strong deterioration
#
# SHORT-TERM:
#
# remaining Red Zones
#
# MEDIUM-TERM:
#
# Orange Zones
#
# MONITOR:
#
# Green / Yellow
#
# ==========================================================

def classify_urgency(row):

    score = row[
        "dynamic_priority_100"
    ]

    zone = row[
        "dynamic_zone"
    ]

    change = row[
        "priority_change"
    ]


    if pd.isna(score):

        return (
            "Insufficient Data"
        )


    if (
        score
        >=
        IMMEDIATE_ABSOLUTE_PRIORITY
    ):

        return "Immediate"


    if (
        zone == "RED"

        and

        change
        >=
        IMMEDIATE_PRIORITY_INCREASE
    ):

        return "Immediate"


    if zone == "RED":

        return "Short-Term"


    if zone == "ORANGE":

        return "Medium-Term"


    return "Monitor"


gdf[
    "relocation_urgency"
] = (

    gdf.apply(
        classify_urgency,
        axis=1
    )
)


# ==========================================================
# URGENCY EXPLANATION
# ==========================================================

def urgency_reason(row):

    score = row[
        "dynamic_priority_100"
    ]

    zone = row[
        "dynamic_zone"
    ]

    change = row[
        "priority_change"
    ]


    if pd.isna(score):

        return (
            "Insufficient data "
            "for dynamic priority."
        )


    if (
        score
        >=
        IMMEDIATE_ABSOLUTE_PRIORITY
    ):

        return (
            "Extremely high absolute "
            "dynamic priority."
        )


    if (
        zone == "RED"

        and

        change
        >=
        IMMEDIATE_PRIORITY_INCREASE
    ):

        return (
            "Red Zone with substantial "
            "scenario-driven risk increase."
        )


    if zone == "RED":

        return (
            "Red Zone requiring "
            "short-term relocation planning."
        )


    if zone == "ORANGE":

        return (
            "Elevated risk requiring "
            "medium-term intervention planning."
        )


    return (
        "Below current relocation "
        "planning threshold; continue monitoring."
    )


gdf[
    "urgency_reason"
] = (

    gdf.apply(
        urgency_reason,
        axis=1
    )
)


# ==========================================================
# DYNAMIC HAZARD DRIVER
# ==========================================================
#
# We do not allow both hazards rising toward 100
# to automatically erase the baseline hazard driver.
#
# Rules:
#
# 1. If dynamic difference exceeds 10,
#    use dynamic dominant hazard.
#
# 2. Otherwise preserve baseline dominant hazard.
#
# This keeps the explanation stable unless another
# hazard genuinely overtakes the previous driver.
# ==========================================================

def dynamic_hazard_driver(row):

    flood = row[
        "dynamic_flood_percentile"
    ]

    landslide = row[
        "dynamic_landslide_percentile"
    ]

    baseline_driver = row[
        "dominant_hazard"
    ]


    if pd.isna(flood) or pd.isna(landslide):

        return "Insufficient Data"


    if flood > landslide + 10:

        return "Flood-dominant"


    if landslide > flood + 10:

        return "Landslide-dominant"


    if baseline_driver in [

        "Flood-dominant",
        "Landslide-dominant",

    ]:

        return baseline_driver


    return "Mixed"


gdf[
    "dynamic_dominant_hazard"
] = (

    gdf.apply(
        dynamic_hazard_driver,
        axis=1
    )
)


# ==========================================================
# SCENARIO NAME
# ==========================================================

if rainfall_trigger == 0:

    scenario_name = "Baseline"


elif rainfall_trigger <= 0.25:

    scenario_name = (
        "Elevated Rainfall"
    )


elif rainfall_trigger <= 0.50:

    scenario_name = (
        "Severe Rainfall"
    )


elif rainfall_trigger <= 0.75:

    scenario_name = (
        "Very Severe Rainfall"
    )


else:

    scenario_name = (
        "Extreme Rainfall"
    )


gdf[
    "rainfall_trigger"
] = rainfall_trigger


gdf[
    "scenario_name"
] = scenario_name


# ==========================================================
# SUMMARY
# ==========================================================

print(
    "\n"
    +
    "=" * 95
)

print(
    "DYNAMIC RISK V2 SUMMARY"
)

print("=" * 95)

print(
    "Scenario:",
    scenario_name
)


print(
    "\nZone counts:"
)

print(
    gdf[
        "dynamic_zone"
    ]
    .value_counts()
)


print(
    "\nRelocation urgency:"
)

print(
    gdf[
        "relocation_urgency"
    ]
    .value_counts()
)


red = gdf[
    gdf["dynamic_zone"]
    ==
    "RED"
]


new_red = gdf[
    gdf["newly_red"]
]


immediate = gdf[
    gdf["relocation_urgency"]
    ==
    "Immediate"
]


print(
    "\nRed-zone habitations:",
    len(red)
)


print(
    "Population in Red Zones:",
    int(
        red[
            "population"
        ]
        .fillna(0)
        .sum()
    )
)


print(
    "Newly entered Red Zone:",
    len(new_red)
)


print(
    "Population newly entering Red Zone:",
    int(
        new_red[
            "population"
        ]
        .fillna(0)
        .sum()
    )
)


print(
    "Immediate-priority habitations:",
    len(immediate)
)


print(
    "Immediate-priority population:",
    int(
        immediate[
            "population"
        ]
        .fillna(0)
        .sum()
    )
)


# ==========================================================
# TOP RISK
# ==========================================================

print(
    "\nTOP 20 DYNAMIC RISK HABITATIONS"
)

print("=" * 95)


display_columns = [

    "village",
    "subdistric",
    "population",

    "multihazard_priority_100",
    "dynamic_priority_100",

    "priority_change",

    "baseline_zone",
    "dynamic_zone",

    "relocation_urgency",

    "dynamic_dominant_hazard",
]


print(

    gdf.loc[
        valid,
        display_columns
    ]

    .sort_values(
        "dynamic_priority_100",
        ascending=False
    )

    .head(20)

    .to_string(
        index=False
    )
)


# ==========================================================
# ZONE TRANSITION SUMMARY
# ==========================================================

print(
    "\nZONE TRANSITIONS"
)

print("=" * 95)


print(

    gdf[
        "zone_transition"
    ]
    .value_counts()
    .head(20)
)


# ==========================================================
# SAVE
# ==========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


if OUTPUT_GPKG.exists():

    OUTPUT_GPKG.unlink()


gdf.to_file(

    OUTPUT_GPKG,

    layer=(
        "dynamic_red_zones"
    ),

    driver="GPKG"
)


csv_columns = [

    "vlcode",
    "village",
    "subdistric",
    "population",

    "susceptibility_percentile",
    "landslide_percentile",

    "exposure_percentile",
    "vulnerability_percentile",

    "multihazard_priority_100",

    "dynamic_flood_percentile",
    "dynamic_landslide_percentile",

    "dynamic_multihazard_susceptibility_100",

    "dynamic_priority_100",
    "priority_change",

    "baseline_zone",
    "dynamic_zone",
    "zone_transition",
    "newly_red",

    "relocation_urgency",
    "urgency_reason",

    "dominant_hazard",
    "dynamic_dominant_hazard",

    "rainfall_trigger",
    "scenario_name",
]


gdf[
    csv_columns
].to_csv(

    OUTPUT_CSV,

    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_GPKG
)

print(
    OUTPUT_CSV
)

print(
    "\nDONE."
)
