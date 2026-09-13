from pathlib import Path

import geopandas as gpd


ROADS = Path(
    "data/raw/landslide/roads/osm/"
    "raigad_roads.gpkg"
)

DISTRICT = Path(
    "data/processed/"
    "raigad_district.gpkg"
)

OUTPUT = Path(
    "data/processed/landslide/"
    "raigad_roads.gpkg"
)


print("Loading roads...")

roads = gpd.read_file(
    ROADS,
    layer="roads"
)

print("Input roads:", len(roads))

print("Loading Raigad district...")

district = gpd.read_file(DISTRICT)

roads = roads.to_crs(
    district.crs
)

print("Clipping...")

clipped = gpd.clip(
    roads,
    district
)

print("Clipped roads:", len(clipped))

print("\nRoad classes:")
print(
    clipped["highway"]
    .value_counts(dropna=False)
    .to_string()
)

clipped.to_file(
    OUTPUT,
    layer="roads",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
