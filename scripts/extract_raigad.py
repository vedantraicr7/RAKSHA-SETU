import geopandas as gpd
from pathlib import Path

INPUT = Path(
    "data/raw/boundaries/india_admin/"
    "State_District_Subdistrict_PAN INDIA/"
    "District_Subdistrict_PAN INDIA/"
    "District Boundary.shp"
)

OUTPUT = Path("data/processed/raigad_district.gpkg")

gdf = gpd.read_file(INPUT)

raigad = gdf[
    (gdf["STATE_UT"].str.upper() == "MAHARASHTRA")
    & (gdf["DISTRICT"].str.upper() == "RAIGAD")
].copy()

if raigad.empty:
    raise ValueError("RAIGAD district not found.")

print("Raigad rows:", len(raigad))
print("CRS:", raigad.crs)
print("Geometry:", raigad.geometry.geom_type.tolist())
print("District LGD code:", raigad["DIST_LGD"].tolist())

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

raigad.to_file(
    OUTPUT,
    layer="raigad_district",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)
