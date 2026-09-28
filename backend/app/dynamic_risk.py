from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


# ==========================================================
# DATA
# ==========================================================

BASE_DATA = Path(
    "data/processed/"
    "raigad_habitations_multihazard.gpkg"
)


# ==========================================================
# PROTOTYPE PARAMETERS
# ==========================================================

FLOOD_RAINFALL_SENSITIVITY = 0.65
LANDSLIDE_RAINFALL_SENSITIVITY = 0.45

IMMEDIATE_ABSOLUTE_PRIORITY = 80.0
IMMEDIATE_PRIORITY_INCREASE = 5.0


# ==========================================================
# LOAD BASELINE ONCE
# ==========================================================

@lru_cache(maxsize=1)
def load_baseline():

    gdf = gpd.read_file(
        BASE_DATA
    )

    required = [
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

    missing = [
        c for c in required
        if c not in gdf.columns
    ]

    if missing:
        raise RuntimeError(
            "Dynamic risk dataset missing: "
            + ", ".join(missing)
        )

    # Make sure map coordinates are WGS84.
    if gdf.crs is None:
        raise RuntimeError(
            "Baseline GeoPackage has no CRS."
        )

    gdf = gdf.to_crs(
        "EPSG:4326"
    )

    # Representative map points.
    #
    # Calculate them in projected coordinates first,
    # then return to WGS84.
    projected = gdf.to_crs(
        "EPSG:3857"
    )

    points = (
        projected
        .geometry
        .representative_point()
    )

    points = (
        gpd.GeoSeries(
            points,
            crs="EPSG:3857"
        )
        .to_crs(
            "EPSG:4326"
        )
    )

    gdf["map_lon"] = points.x
    gdf["map_lat"] = points.y

    return gdf


# ==========================================================
# ZONE FUNCTION
# ==========================================================

def zone_from_score(
    score,
    yellow_threshold,
    orange_threshold,
    red_threshold,
):

    if pd.isna(score):
        return "Insufficient Data"

    if score >= red_threshold:
        return "RED"

    if score >= orange_threshold:
        return "ORANGE"

    if score >= yellow_threshold:
        return "YELLOW"

    return "GREEN"


# ==========================================================
# SCENARIO NAME
# ==========================================================

def scenario_name(trigger):

    if trigger == 0:
        return "Baseline"

    if trigger <= 0.25:
        return "Elevated Rainfall"

    if trigger <= 0.50:
        return "Severe Rainfall"

    if trigger <= 0.75:
        return "Very Severe Rainfall"

    return "Extreme Rainfall"


# ==========================================================
# DYNAMIC ENGINE
# ==========================================================

def calculate_dynamic_risk(
    rainfall_trigger: float
):

    trigger = float(
        np.clip(
            rainfall_trigger,
            0.0,
            1.0
        )
    )

    baseline = (
        load_baseline()
        .copy()
    )


    # ------------------------------------------------------
    # VALID RECORDS
    # ------------------------------------------------------

    valid = (

        (baseline["population"] > 0)

        & baseline[
            "susceptibility_percentile"
        ].notna()

        & baseline[
            "landslide_percentile"
        ].notna()

        & baseline[
            "exposure_percentile"
        ].notna()

        & baseline[
            "vulnerability_percentile"
        ].notna()

        & baseline[
            "multihazard_priority_100"
        ].notna()
    )


    # ------------------------------------------------------
    # BASELINE THRESHOLDS
    # ------------------------------------------------------

    baseline_scores = baseline.loc[
        valid,
        "multihazard_priority_100"
    ]

    yellow_threshold = float(
        baseline_scores.quantile(0.40)
    )

    orange_threshold = float(
        baseline_scores.quantile(0.60)
    )

    red_threshold = float(
        baseline_scores.quantile(0.80)
    )


    # ------------------------------------------------------
    # DYNAMIC FLOOD
    # ------------------------------------------------------

    base_flood = (
        baseline[
            "susceptibility_percentile"
        ].astype(float)
    )

    baseline[
        "dynamic_flood_percentile"
    ] = (

        base_flood

        +

        (
            100.0
            -
            base_flood
        )

        *
        FLOOD_RAINFALL_SENSITIVITY

        *
        trigger
    ).clip(
        0,
        100
    )


    # ------------------------------------------------------
    # DYNAMIC LANDSLIDE
    # ------------------------------------------------------

    base_landslide = (
        baseline[
            "landslide_percentile"
        ].astype(float)
    )

    baseline[
        "dynamic_landslide_percentile"
    ] = (

        base_landslide

        +

        (
            100.0
            -
            base_landslide
        )

        *
        LANDSLIDE_RAINFALL_SENSITIVITY

        *
        trigger
    ).clip(
        0,
        100
    )


    # ------------------------------------------------------
    # DYNAMIC MULTI-HAZARD
    # ------------------------------------------------------

    flood = (
        baseline[
            "dynamic_flood_percentile"
        ]
        /
        100.0
    )

    landslide = (
        baseline[
            "dynamic_landslide_percentile"
        ]
        /
        100.0
    )

    baseline[
        "dynamic_multihazard_susceptibility"
    ] = np.sqrt(
        flood
        *
        landslide
    )


    # ------------------------------------------------------
    # PRIORITY
    # ------------------------------------------------------

    exposure = (
        baseline[
            "exposure_percentile"
        ]
        /
        100.0
    )

    vulnerability = (
        baseline[
            "vulnerability_percentile"
        ]
        /
        100.0
    )

    baseline[
        "dynamic_priority_100"
    ] = np.nan

    baseline.loc[
        valid,
        "dynamic_priority_100"
    ] = (

        baseline.loc[
            valid,
            "dynamic_multihazard_susceptibility"
        ]

        *

        np.sqrt(
            exposure[valid]
            *
            vulnerability[valid]
        )

    ) ** 0.5 * 100.0


    baseline[
        "priority_change"
    ] = (

        baseline[
            "dynamic_priority_100"
        ]

        -

        baseline[
            "multihazard_priority_100"
        ]
    )


    # ------------------------------------------------------
    # BASELINE + DYNAMIC ZONES
    # ------------------------------------------------------

    baseline[
        "baseline_zone"
    ] = baseline[
        "multihazard_priority_100"
    ].apply(
        lambda score:
            zone_from_score(
                score,
                yellow_threshold,
                orange_threshold,
                red_threshold,
            )
    )

    baseline[
        "dynamic_zone"
    ] = baseline[
        "dynamic_priority_100"
    ].apply(
        lambda score:
            zone_from_score(
                score,
                yellow_threshold,
                orange_threshold,
                red_threshold,
            )
    )


    baseline[
        "newly_red"
    ] = (

        (
            baseline[
                "dynamic_zone"
            ]
            ==
            "RED"
        )

        &

        (
            baseline[
                "baseline_zone"
            ]
            !=
            "RED"
        )
    )


    # ------------------------------------------------------
    # URGENCY
    # ------------------------------------------------------

    def urgency(row):

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


    baseline[
        "relocation_urgency"
    ] = baseline.apply(
        urgency,
        axis=1
    )


    # ------------------------------------------------------
    # DYNAMIC HAZARD DRIVER
    # ------------------------------------------------------

    def hazard_driver(row):

        flood_value = row[
            "dynamic_flood_percentile"
        ]

        landslide_value = row[
            "dynamic_landslide_percentile"
        ]

        base_driver = row[
            "dominant_hazard"
        ]

        if (
            pd.isna(flood_value)
            or
            pd.isna(landslide_value)
        ):
            return "Insufficient Data"

        if (
            flood_value
            >
            landslide_value + 10
        ):
            return "Flood-dominant"

        if (
            landslide_value
            >
            flood_value + 10
        ):
            return "Landslide-dominant"

        if base_driver in [
            "Flood-dominant",
            "Landslide-dominant",
        ]:
            return base_driver

        return "Mixed"


    baseline[
        "dynamic_dominant_hazard"
    ] = baseline.apply(
        hazard_driver,
        axis=1
    )


    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------

    red = baseline[
        baseline[
            "dynamic_zone"
        ]
        ==
        "RED"
    ]

    new_red = baseline[
        baseline[
            "newly_red"
        ]
    ]

    immediate = baseline[
        baseline[
            "relocation_urgency"
        ]
        ==
        "Immediate"
    ]


    summary = {

        "rainfall_trigger":
            trigger,

        "scenario_name":
            scenario_name(
                trigger
            ),

        "total_habitations":
            int(
                len(baseline)
            ),

        "valid_habitations":
            int(
                valid.sum()
            ),

        "red_habitations":
            int(
                len(red)
            ),

        "red_population":
            int(
                red[
                    "population"
                ]
                .fillna(0)
                .sum()
            ),

        "newly_red_habitations":
            int(
                len(new_red)
            ),

        "newly_red_population":
            int(
                new_red[
                    "population"
                ]
                .fillna(0)
                .sum()
            ),

        "immediate_habitations":
            int(
                len(immediate)
            ),

        "immediate_population":
            int(
                immediate[
                    "population"
                ]
                .fillna(0)
                .sum()
            ),

        "thresholds": {

            "yellow":
                round(
                    yellow_threshold,
                    3
                ),

            "orange":
                round(
                    orange_threshold,
                    3
                ),

            "red":
                round(
                    red_threshold,
                    3
                ),
        }
    }


    # ------------------------------------------------------
    # LIGHTWEIGHT MAP FEATURES
    # ------------------------------------------------------
    #
    # We return points rather than all 1,950 polygons.
    # This keeps slider interaction fast.
    # ------------------------------------------------------

    features = []

    for _, row in baseline.iterrows():

        if (
            pd.isna(
                row["map_lat"]
            )
            or
            pd.isna(
                row["map_lon"]
            )
        ):
            continue

        properties = {

            "vlcode":
                str(
                    row["vlcode"]
                ),

            "village":
                row["village"],

            "subdistric":
                row["subdistric"],

            "population":
                (
                    None
                    if pd.isna(
                        row["population"]
                    )
                    else float(
                        row["population"]
                    )
                ),

            "baseline_priority":
                (
                    None
                    if pd.isna(
                        row[
                            "multihazard_priority_100"
                        ]
                    )
                    else float(
                        row[
                            "multihazard_priority_100"
                        ]
                    )
                ),

            "dynamic_priority":
                (
                    None
                    if pd.isna(
                        row[
                            "dynamic_priority_100"
                        ]
                    )
                    else float(
                        row[
                            "dynamic_priority_100"
                        ]
                    )
                ),

            "priority_change":
                (
                    None
                    if pd.isna(
                        row[
                            "priority_change"
                        ]
                    )
                    else float(
                        row[
                            "priority_change"
                        ]
                    )
                ),

            "baseline_zone":
                row[
                    "baseline_zone"
                ],

            "dynamic_zone":
                row[
                    "dynamic_zone"
                ],

            "newly_red":
                bool(
                    row[
                        "newly_red"
                    ]
                ),

            "relocation_urgency":
                row[
                    "relocation_urgency"
                ],

            "dominant_hazard":
                row[
                    "dynamic_dominant_hazard"
                ],
        }

        features.append({

            "type":
                "Feature",

            "geometry": {
                "type":
                    "Point",

                "coordinates": [
                    float(
                        row["map_lon"]
                    ),
                    float(
                        row["map_lat"]
                    ),
                ],
            },

            "properties":
                properties,
        })


    return {

        "summary":
            summary,

        "geojson": {

            "type":
                "FeatureCollection",

            "features":
                features,
        },
    }
