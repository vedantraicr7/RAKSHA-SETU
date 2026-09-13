import geopandas as gpd
from pathlib import Path


INPUT = Path(
    "data/raw/hydrography/"
    "cwc_river_network/"
    "River_Network.shp"
)


print("Loading CWC river network...")

gdf = gpd.read_file(INPUT)

print("\n" + "=" * 70)
print("CWC RIVER NETWORK")
print("=" * 70)

print("\nRows:")
print(len(gdf))

print("\nCRS:")
print(gdf.crs)

print("\nGeometry types:")
print(gdf.geometry.geom_type.value_counts())

print("\nColumns:")
for col in gdf.columns:
    print("-", col)

print("\nFirst 10 rows:")
print(
    gdf.drop(columns="geometry")
    .head(10)
    .to_string(index=False)
)

print("\nMissing geometries:")
print(gdf.geometry.isna().sum())

print("\nEmpty geometries:")
print(gdf.geometry.is_empty.sum())

print("\nInvalid geometries:")
print((~gdf.geometry.is_valid).sum())

print("\nBounding box:")
print(gdf.total_bounds)
