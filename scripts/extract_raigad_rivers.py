from pathlib import Path

import geopandas as gpd


RIVERS = Path(
    "data/raw/hydrography/"
    "cwc_river_network/"
    "River_Network.shp"
)

RAIGAD = Path(
    "data/processed/"
    "raigad_district.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_river_network.gpkg"
)


print("Loading CWC rivers...")
rivers = gpd.read_file(RIVERS)

print("Loading Raigad boundary...")
district = gpd.read_file(RAIGAD)


# --------------------------------------------------
# Match CRS
# --------------------------------------------------

district = district.to_crs(rivers.crs)

raigad_geom = district.geometry.union_all()


# --------------------------------------------------
# Spatial filter first
# --------------------------------------------------

print("Filtering rivers intersecting Raigad...")

raigad_rivers = rivers[
    rivers.intersects(raigad_geom)
].copy()

print("River features intersecting Raigad:", len(raigad_rivers))


# --------------------------------------------------
# Clip exactly to district boundary
# --------------------------------------------------

print("Clipping river geometries...")

raigad_rivers = gpd.clip(
    raigad_rivers,
    district
)


# --------------------------------------------------
# Remove empty geometries if any
# --------------------------------------------------

raigad_rivers = raigad_rivers[
    ~raigad_rivers.geometry.is_empty
].copy()


# --------------------------------------------------
# Basic QA
# --------------------------------------------------

print("\nGeometry types:")
print(
    raigad_rivers.geometry
    .geom_type
    .value_counts()
)

print("\nNamed rivers:")
print(
    raigad_rivers["rivname"]
    .notna()
    .sum()
)

print("\nUnique river names:")
print(
    raigad_rivers["rivname"]
    .dropna()
    .nunique()
)

print("\nSample river records:")

cols = [
    "rivname",
    "sub_basin",
    "ba_name",
    "length_km",
    "UID_River"
]

print(
    raigad_rivers[cols]
    .head(30)
    .to_string(index=False)
)


# --------------------------------------------------
# Save
# --------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

raigad_rivers.to_file(
    OUTPUT,
    layer="raigad_river_network",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)
