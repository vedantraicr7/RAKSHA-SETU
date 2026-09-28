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

OUTPUT_GPKG = OUTPUT_DIR / "dynamic_red_zones.gpkg"
OUTPUT_CSV = OUTPUT_DIR / "dynamic_red_zones.csv"


# ==========================================================
# CONFIGURATION
# ==========================================================
#
# These rainfall sensitivity coefficients are prototype
# scenario parameters, NOT government standards.
#
# Flood responds more strongly to current rainfall.
# Landslide susceptibility also increases, but more slowly.
# ==========================================================

FLOOD_RAINFALL_SENSITIVITY = 0.65
LANDSLIDE_RAINFALL_SENSITIVITY = 0.45


# ==========================================================
# ARGUMENTS
# ==========================================================

parser = argparse.ArgumentParser(
    description=(
        "RAKSHA-SETU dynamic multi-hazard "
        "red-zone scenario engine"
    )
)

parser.add_argument(
    "--rainfall-trigger",
    type=float,
    default=0.0,
    help=(
        "Rainfall trigger between 0 and 1. "
        "0 = baseline, 1 = extreme scenario."
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
# LOAD
# ==========================================================

print("=" * 90)
print("RAKSHA-SETU DYNAMIC MULTI-HAZARD RED ZONE ENGINE")
print("=" * 90)

print(
    "\nRainfall trigger:",
    rainfall_trigger
)

print("\nLoading baseline multi-hazard dataset...")

gdf = gpd.read_file(INPUT)

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
]

missing = [
    column
    for column in required_columns
    if column not in gdf.columns
]

if missing:
    raise ValueError(
        "Missing required columns: "
        + ", ".join(missing)
    )


# ==========================================================
# VALID HABITATIONS
# ==========================================================

valid = (
    (gdf["population"] > 0)
    &
    gdf["susceptibility_percentile"].notna()
    &
    gdf["landslide_percentile"].notna()
    &
    gdf["exposure_percentile"].notna()
    &
    gdf["vulnerability_percentile"].notna()
    &
    gdf["multihazard_priority_100"].notna()
)


print(
    "Valid habitations:",
    int(valid.sum())
)


# ==========================================================
# BASELINE HAZARDS
# ==========================================================

baseline_flood = (
    gdf["susceptibility_percentile"]
    .astype(float)
)

baseline_landslide = (
    gdf["landslide_percentile"]
    .astype(float)
)


# ==========================================================
# DYNAMIC HAZARD RESPONSE
# ==========================================================
#
# Instead of simply multiplying risk, rainfall pushes
# the current hazard percentile toward 100.
#
# Example:
#
# baseline flood = 70
# trigger = 1
# sensitivity = 0.65
#
# dynamic flood =
# 70 + (100 - 70) * 0.65
#
# This keeps all values between their baseline and 100.
# ==========================================================

gdf["dynamic_flood_percentile"] = (
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

gdf["dynamic_landslide_percentile"] = (
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


gdf["dynamic_flood_percentile"] = (
    gdf[
        "dynamic_flood_percentile"
    ]
    .clip(
        lower=0,
        upper=100
    )
)

gdf["dynamic_landslide_percentile"] = (
    gdf[
        "dynamic_landslide_percentile"
    ]
    .clip(
        lower=0,
        upper=100
    )
)


# ==========================================================
# DYNAMIC MULTI-HAZARD SUSCEPTIBILITY
# ==========================================================
#
# Same structure as existing baseline engine:
#
# H = sqrt(F * L)
#
# F and L are 0-1 hazard percentiles.
# ==========================================================

dynamic_flood = (
    gdf["dynamic_flood_percentile"]
    /
    100.0
)

dynamic_landslide = (
    gdf["dynamic_landslide_percentile"]
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
# DYNAMIC PRIORITY
# ==========================================================
#
# Preserve existing RAKSHA-SETU methodology:
#
# dynamic priority =
#
# [
#    dynamic hazard
#    *
#    sqrt(exposure * vulnerability)
# ] ^ 0.5
# ==========================================================

exposure = (
    gdf["exposure_percentile"]
    /
    100.0
)

vulnerability = (
    gdf["vulnerability_percentile"]
    /
    100.0
)


gdf["dynamic_priority"] = np.nan


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


gdf["dynamic_priority_100"] = (
    gdf["dynamic_priority"]
    *
    100.0
)


# ==========================================================
# CHANGE FROM BASELINE
# ==========================================================

gdf["priority_change"] = (
    gdf["dynamic_priority_100"]
    -
    gdf["multihazard_priority_100"]
)


# ==========================================================
# FIXED BASELINE RED-ZONE THRESHOLDS
# ==========================================================
#
# IMPORTANT:
#
# We calculate thresholds from the BASELINE distribution.
# Then keep them fixed for every future scenario.
#
# This allows the number of Red Zones to expand as
# conditions worsen.
#
# If we recalculated percentiles every scenario, there
# would always be roughly the same number of Red Zones.
# ==========================================================

baseline_scores = (
    gdf.loc[
        valid,
        "multihazard_priority_100"
    ]
)


GREEN_THRESHOLD = float(
    baseline_scores.quantile(0.40)
)

YELLOW_THRESHOLD = float(
    baseline_scores.quantile(0.60)
)

ORANGE_THRESHOLD = float(
    baseline_scores.quantile(0.80)
)


print("\nFixed baseline thresholds")
print("=" * 70)

print(
    "Yellow threshold:",
    round(
        GREEN_THRESHOLD,
        3
    )
)

print(
    "Orange threshold:",
    round(
        YELLOW_THRESHOLD,
        3
    )
)

print(
    "Red threshold:",
    round(
        ORANGE_THRESHOLD,
        3
    )
)


# ==========================================================
# DYNAMIC ZONE CLASS
# ==========================================================

def classify_zone(score):

    if pd.isna(score):
        return "Insufficient Data"

    if score >= ORANGE_THRESHOLD:
        return "RED"

    if score >= YELLOW_THRESHOLD:
        return "ORANGE"

    if score >= GREEN_THRESHOLD:
        return "YELLOW"

    return "GREEN"


gdf["dynamic_zone"] = (
    gdf[
        "dynamic_priority_100"
    ]
    .apply(
        classify_zone
    )
)


# ==========================================================
# RELOCATION URGENCY
# ==========================================================
#
# First version.
#
# We intentionally keep urgency separate from the
# relocation-site feasibility decision.
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
        return "Insufficient Data"

    if (
        zone == "RED"
        and
        change >= 5
    ):
        return "Immediate"

    if zone == "RED":
        return "Short-Term"

    if zone == "ORANGE":
        return "Medium-Term"

    return "Monitor"


gdf["relocation_urgency"] = (
    gdf.apply(
        classify_urgency,
        axis=1
    )
)


# ==========================================================
# DYNAMIC DOMINANT HAZARD
# ==========================================================

conditions = [

    (
        gdf[
            "dynamic_flood_percentile"
        ]
        >
        gdf[
            "dynamic_landslide_percentile"
        ]
        +
        10
    ),

    (
        gdf[
            "dynamic_landslide_percentile"
        ]
        >
        gdf[
            "dynamic_flood_percentile"
        ]
        +
        10
    ),
]


choices = [
    "Flood-dominant",
    "Landslide-dominant",
]


gdf[
    "dynamic_dominant_hazard"
] = np.select(
    conditions,
    choices,
    default="Mixed"
)


# ==========================================================
# SCENARIO METADATA
# ==========================================================

gdf[
    "rainfall_trigger"
] = rainfall_trigger


if rainfall_trigger == 0:
    scenario_name = "Baseline"

elif rainfall_trigger <= 0.25:
    scenario_name = "Elevated Rainfall"

elif rainfall_trigger <= 0.50:
    scenario_name = "Severe Rainfall"

elif rainfall_trigger <= 0.75:
    scenario_name = "Very Severe Rainfall"

else:
    scenario_name = "Extreme Rainfall"


gdf[
    "scenario_name"
] = scenario_name


# ==========================================================
# SUMMARY
# ==========================================================

print("\n" + "=" * 90)
print("DYNAMIC RISK SUMMARY")
print("=" * 90)

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


# ==========================================================
# TOP DYNAMIC RISK
# ==========================================================

print("\nTOP 20 DYNAMIC RISK HABITATIONS")
print("=" * 90)


display_columns = [
    "village",
    "subdistric",
    "population",
    "multihazard_priority_100",
    "dynamic_priority_100",
    "priority_change",
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
    layer="dynamic_red_zones",
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
    "dynamic_zone",
    "relocation_urgency",
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


print("\nSaved:")
print(
    OUTPUT_GPKG
)

print(
    OUTPUT_CSV
)

print("\nDONE.")
