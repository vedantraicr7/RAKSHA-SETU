from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio


HABITATIONS = Path(
    "data/processed/"
    "raigad_habitations_multihazard.gpkg"
)

CANDIDATES = Path(
    "data/processed/relocation/"
    "raigad_relocation_candidate_sites.gpkg"
)

FLOOD = Path(
    "data/processed/"
    "raigad_flood_susceptibility.tif"
)

LANDSLIDE = Path(
    "data/processed/landslide/"
    "raigad_landslide_susceptibility.tif"
)

SLOPE = Path(
    "data/processed/terrain/"
    "raigad_slope.tif"
)

ROAD_DIST = Path(
    "data/processed/landslide/predictors/"
    "dist_road_m.tif"
)

OUTPUT = Path(
    "data/processed/relocation/"
    "priority_habitation_candidate_ranking.csv"
)


TARGET_CRS = "EPSG:32643"

TOP_HABITATIONS = 40
MAX_SITE_DISTANCE_KM = 25
TOP_SITES_PER_HAB = 5


print("Loading habitations...")

hab = gpd.read_file(HABITATIONS)

hab = (
    hab[
        hab["multihazard_priority_100"]
        .notna()
    ]
    .sort_values(
        "multihazard_priority_100",
        ascending=False
    )
    .head(TOP_HABITATIONS)
    .copy()
)

print(
    "Priority habitations:",
    len(hab)
)


print("Loading candidate sites...")

sites = gpd.read_file(
    CANDIDATES,
    layer="candidate_sites"
)

print(
    "Candidate sites:",
    len(sites)
)


hab_m = hab.to_crs(
    TARGET_CRS
)

sites_m = sites.to_crs(
    TARGET_CRS
)


# -------------------------------------------------------
# Representative points
# -------------------------------------------------------

hab_m["rep_point"] = (
    hab_m.geometry
    .representative_point()
)

sites_m["site_point"] = (
    sites_m.geometry
    .representative_point()
)


# -------------------------------------------------------
# Raster sampling helper
# -------------------------------------------------------

def sample_raster_at_points(
    raster_path,
    points
):

    with rasterio.open(
        raster_path
    ) as src:

        points_gdf = gpd.GeoDataFrame(
            geometry=points,
            crs=TARGET_CRS
        ).to_crs(
            src.crs
        )

        coords = [
            (p.x, p.y)
            for p in points_gdf.geometry
        ]

        vals = []

        for arr in src.sample(
            coords
        ):

            v = float(
                arr[0]
            )

            if (
                src.nodata is not None
                and v == src.nodata
            ):
                vals.append(
                    np.nan
                )
            else:
                vals.append(
                    v
                )

        return np.array(
            vals,
            dtype=float
        )


# -------------------------------------------------------
# Candidate residual quality
# -------------------------------------------------------

print(
    "Sampling candidate-site conditions..."
)

sites_m["site_flood"] = (
    sample_raster_at_points(
        FLOOD,
        sites_m["site_point"]
    )
)

sites_m["site_landslide"] = (
    sample_raster_at_points(
        LANDSLIDE,
        sites_m["site_point"]
    )
)

sites_m["site_slope"] = (
    sample_raster_at_points(
        SLOPE,
        sites_m["site_point"]
    )
)

sites_m["site_road_dist_m"] = (
    sample_raster_at_points(
        ROAD_DIST,
        sites_m["site_point"]
    )
)


# -------------------------------------------------------
# Scaling helpers
# -------------------------------------------------------

def low_score(
    values,
    max_value
):

    return np.clip(
        1.0
        -
        (
            values
            /
            max_value
        ),
        0,
        1
    )


def high_score(
    values,
    max_value
):

    return np.clip(
        values
        /
        max_value,
        0,
        1
    )


# -------------------------------------------------------
# Candidate capacity score
# -------------------------------------------------------

sites_m["area_score"] = (
    high_score(
        sites_m[
            "area_ha"
        ],
        50
    )
)


# -------------------------------------------------------
# Intrinsic site-quality scores
# -------------------------------------------------------

sites_m["flood_safety_score"] = (
    low_score(
        sites_m[
            "site_flood"
        ],
        60
    )
)

sites_m[
    "landslide_safety_score"
] = (
    low_score(
        sites_m[
            "site_landslide"
        ],
        60
    )
)

sites_m[
    "slope_quality_score"
] = (
    low_score(
        sites_m[
            "site_slope"
        ],
        10
    )
)

sites_m[
    "road_access_score"
] = (
    low_score(
        sites_m[
            "site_road_dist_m"
        ],
        3000
    )
)


# -------------------------------------------------------
# Pair each priority habitation with nearby sites
# -------------------------------------------------------

records = []


for _, h in hab_m.iterrows():

    h_point = h["rep_point"]

    distances_m = (
        sites_m[
            "site_point"
        ]
        .distance(
            h_point
        )
    )

    nearby = sites_m[
        distances_m
        <= (
            MAX_SITE_DISTANCE_KM
            * 1000
        )
    ].copy()

    if nearby.empty:
        continue

    nearby[
        "distance_to_hab_m"
    ] = (
        distances_m[
            nearby.index
        ]
    )

    nearby[
        "distance_score"
    ] = (
        low_score(
            nearby[
                "distance_to_hab_m"
            ],
            MAX_SITE_DISTANCE_KM
            * 1000
        )
    )


    # ---------------------------------------------------
    # Final candidate score
    # ---------------------------------------------------
    #
    # Distance and site area matter most.
    # Safety still contributes even though
    # all candidates already pass the safe mask.
    # ---------------------------------------------------

    nearby[
        "relocation_site_score"
    ] = (
          0.30
          * nearby[
              "distance_score"
          ]

        + 0.25
          * nearby[
              "area_score"
          ]

        + 0.15
          * nearby[
              "road_access_score"
          ]

        + 0.10
          * nearby[
              "flood_safety_score"
          ]

        + 0.10
          * nearby[
              "landslide_safety_score"
          ]

        + 0.10
          * nearby[
              "slope_quality_score"
          ]
    )


    nearby = (
        nearby
        .sort_values(
            "relocation_site_score",
            ascending=False
        )
        .head(
            TOP_SITES_PER_HAB
        )
    )


    rank = 1

    for _, s in nearby.iterrows():

        records.append(
            {
                "village":
                    h["village"],

                "subdistric":
                    h["subdistric"],

                "vlcode":
                    h["vlcode"],

                "population":
                    h["population"],

                "multihazard_priority_100":
                    h[
                        "multihazard_priority_100"
                    ],

                "candidate_rank":
                    rank,

                "patch_id":
                    int(
                        s["patch_id"]
                    ),

                "area_ha":
                    s["area_ha"],

                "distance_km":
                    (
                        s[
                            "distance_to_hab_m"
                        ]
                        / 1000
                    ),

                "site_flood":
                    s["site_flood"],

                "site_landslide":
                    s[
                        "site_landslide"
                    ],

                "site_slope_deg":
                    s[
                        "site_slope"
                    ],

                "site_road_dist_m":
                    s[
                        "site_road_dist_m"
                    ],

                "relocation_site_score":
                    (
                        s[
                            "relocation_site_score"
                        ]
                        * 100
                    ),
            }
        )

        rank += 1


results = pd.DataFrame(
    records
)


print(
    "\nRELOCATION CANDIDATE SUMMARY"
)

print("=" * 100)

print(
    "Habitation-site pairs:",
    len(results)
)

print(
    "Habitations with candidates:",
    results[
        "vlcode"
    ].nunique()
)


print(
    "\nTOP CANDIDATES FOR TOP 10 PRIORITY HABITATIONS"
)

print("=" * 160)


top10_codes = (
    hab
    .head(10)[
        "vlcode"
    ]
    .tolist()
)


print(
    results[
        results[
            "vlcode"
        ]
        .isin(
            top10_codes
        )
    ]
    .sort_values(
        [
            "multihazard_priority_100",
            "candidate_rank"
        ],
        ascending=[
            False,
            True
        ]
    )
    .to_string(
        index=False
    )
)


results.to_csv(
    OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
