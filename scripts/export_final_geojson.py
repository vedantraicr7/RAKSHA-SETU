from pathlib import Path

import geopandas as gpd


DECISIONS = Path(
    "data/processed/relocation/"
    "raigad_complete_relocation_decisions.gpkg"
)

RECOMMENDATIONS = Path(
    "data/processed/relocation/"
    "raigad_relocation_recommendations.gpkg"
)

OUT_DIR = Path(
    "data/processed/frontend"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# 1. Complete priority decisions
# --------------------------------------------------

print("Exporting priority decisions...")

decisions = gpd.read_file(
    DECISIONS,
    layer="priority_decisions"
)

decisions = decisions.to_crs(
    "EPSG:4326"
)

decisions.to_file(
    OUT_DIR / "priority_decisions.geojson",
    driver="GeoJSON"
)


# --------------------------------------------------
# 2. Recommended relocation sites
# --------------------------------------------------

print("Exporting recommended sites...")

sites = gpd.read_file(
    RECOMMENDATIONS,
    layer="recommended_sites"
)

sites = sites.to_crs(
    "EPSG:4326"
)

sites.to_file(
    OUT_DIR / "recommended_sites.geojson",
    driver="GeoJSON"
)


# --------------------------------------------------
# 3. Relocation links
# --------------------------------------------------

print("Exporting relocation links...")

links = gpd.read_file(
    RECOMMENDATIONS,
    layer="relocation_links"
)

links = links.to_crs(
    "EPSG:4326"
)

links.to_file(
    OUT_DIR / "relocation_links.geojson",
    driver="GeoJSON"
)


# --------------------------------------------------
# 4. Priority habitations with recommendations
# --------------------------------------------------

print("Exporting recommended habitations...")

hab = gpd.read_file(
    RECOMMENDATIONS,
    layer="priority_habitations"
)

hab = hab.to_crs(
    "EPSG:4326"
)

hab.to_file(
    OUT_DIR / "recommended_habitations.geojson",
    driver="GeoJSON"
)


print("\nSaved:")
print(
    OUT_DIR /
    "priority_decisions.geojson"
)
print(
    OUT_DIR /
    "recommended_sites.geojson"
)
print(
    OUT_DIR /
    "relocation_links.geojson"
)
print(
    OUT_DIR /
    "recommended_habitations.geojson"
)

print("\nDONE.")
