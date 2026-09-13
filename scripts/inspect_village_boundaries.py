import geopandas as gpd
from pathlib import Path

INPUT = Path(
    "data/raw/boundaries/"
    "maharashtra_villages/"
    "vb_soi_mh.shp"
)

print("Loading Maharashtra village boundaries...")

gdf = gpd.read_file(INPUT)

print("\n" + "=" * 70)
print("MAHARASHTRA VILLAGE BOUNDARY DATASET")
print("=" * 70)

print("\nTotal records:")
print(len(gdf))

print("\nCRS:")
print(gdf.crs)

print("\nGeometry types:")
print(gdf.geometry.geom_type.value_counts())

print("\nColumns:")
for column in gdf.columns:
    print("-", column)

print("\nFirst 5 records:")
print(gdf.head().to_string())

print("\nMissing geometries:")
print(gdf.geometry.isna().sum())

print("\nEmpty geometries:")
print(gdf.geometry.is_empty.sum())

print("\nInvalid geometries:")
print((~gdf.geometry.is_valid).sum())

print("\nBounding box:")
print(gdf.total_bounds)
