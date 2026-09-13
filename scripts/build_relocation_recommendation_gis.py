from pathlib import Path

import geopandas as gpd
import pandas as pd


HABITATIONS = Path(
    "data/processed/raigad_habitations_multihazard.gpkg"
)

SITES = Path(
    "data/processed/relocation/"
    "raigad_relocation_candidate_sites.gpkg"
)

RECOMMENDATIONS = Path(
    "data/processed/relocation/"
    "final_relocation_recommendations.csv"
)

OUTPUT = Path(
    "data/processed/relocation/"
    "raigad_relocation_recommendations.gpkg"
)


print("Loading datasets...")

hab = gpd.read_file(HABITATIONS)
sites = gpd.read_file(SITES)
rec = pd.read_csv(RECOMMENDATIONS)

print("Habitations:", len(hab))
print("Candidate sites:", len(sites))
print("Recommendations:", len(rec))


# =========================================================
# NORMALIZE KEYS
# =========================================================

hab["vlcode"] = hab["vlcode"].astype(str)
rec["vlcode"] = rec["vlcode"].astype(str)

sites["patch_id"] = sites["patch_id"].astype(int)
rec["patch_id"] = rec["patch_id"].astype(int)


# =========================================================
# BEST RECOMMENDATION ONLY
# =========================================================

best = rec[
    rec["recommendation_rank"] == 1
].copy()

print(
    "Habitations with best recommendation:",
    len(best)
)


# =========================================================
# HABITATION LAYER
# =========================================================

hab_best = hab.merge(
    best,
    on="vlcode",
    how="inner",
    suffixes=("_hab", "")
)

print(
    "Matched habitation recommendations:",
    len(hab_best)
)


# =========================================================
# SITE LAYER
# =========================================================

site_best = sites.merge(
    best,
    on="patch_id",
    how="inner",
    suffixes=("_site", "")
)

print(
    "Recommended site records:",
    len(site_best)
)


# =========================================================
# CREATE CONNECTION LINES
# =========================================================

# Use projected CRS for geometry construction.
# Candidate sites are already expected to be in UTM 43N.

target_crs = sites.crs

hab_projected = hab_best.to_crs(target_crs)

# Get site centroid by patch ID
site_centroids = (
    sites[
        ["patch_id", "geometry"]
    ]
    .copy()
)

site_centroids["geometry"] = (
    site_centroids.geometry.centroid
)

centroid_lookup = dict(
    zip(
        site_centroids["patch_id"],
        site_centroids.geometry
    )
)


from shapely.geometry import LineString


lines = []

for _, row in hab_projected.iterrows():

    patch_id = int(row["patch_id"])

    site_point = centroid_lookup.get(
        patch_id
    )

    if site_point is None:
        continue

    habitation_point = (
        row.geometry.centroid
    )

    line = LineString(
        [
            habitation_point,
            site_point
        ]
    )

    record = {
        "vlcode": row["vlcode"],
        "village": row["village"],
        "patch_id": patch_id,
        "recommendation_status":
            row["recommendation_status"],
        "distance_km":
            row["distance_km"],
        "final_feasibility_score":
            row["final_feasibility_score"],
        "geometry": line,
    }

    lines.append(record)


connection_gdf = gpd.GeoDataFrame(
    lines,
    geometry="geometry",
    crs=target_crs
)


print(
    "Connection lines:",
    len(connection_gdf)
)


# =========================================================
# SAVE GPKG
# =========================================================

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

# Remove old output to prevent stale layers
if OUTPUT.exists():
    OUTPUT.unlink()


hab_best.to_file(
    OUTPUT,
    layer="priority_habitations",
    driver="GPKG"
)

site_best.to_file(
    OUTPUT,
    layer="recommended_sites",
    driver="GPKG"
)

connection_gdf.to_file(
    OUTPUT,
    layer="relocation_links",
    driver="GPKG"
)


print("\nSaved:")
print(OUTPUT)

print("\nLayers:")
print("priority_habitations")
print("recommended_sites")
print("relocation_links")

print("\nDONE.")
