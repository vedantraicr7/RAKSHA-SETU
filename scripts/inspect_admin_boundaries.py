from pathlib import Path
import geopandas as gpd

BASE = Path(
    "data/raw/boundaries/india_admin/"
    "State_District_Subdistrict_PAN INDIA"
)

layers = {
    "state": BASE / "State Boundary" / "State Boundary.shp",
    "district": BASE / "District_Subdistrict_PAN INDIA" / "District Boundary.shp",
    "subdistrict": BASE / "District_Subdistrict_PAN INDIA" / "Sub_district Boundary.shp",
}

for name, path in layers.items():
    print("\n" + "=" * 80)
    print(name.upper())
    print("=" * 80)

    gdf = gpd.read_file(path)

    print("Rows:", len(gdf))
    print("CRS:", gdf.crs)
    print("Geometry types:")
    print(gdf.geometry.geom_type.value_counts())

    print("\nColumns:")
    for col in gdf.columns:
        print(" -", col)

    print("\nFirst 5 rows:")
    print(gdf.head(5).to_string())
