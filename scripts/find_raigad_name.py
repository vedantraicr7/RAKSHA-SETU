import geopandas as gpd

path = (
    "data/raw/boundaries/india_admin/"
    "State_District_Subdistrict_PAN INDIA/"
    "District_Subdistrict_PAN INDIA/"
    "District Boundary.shp"
)

gdf = gpd.read_file(path)

print("Available states containing 'Mahar':")
print(
    gdf.loc[
        gdf["STATE_UT"]
        .astype(str)
        .str.contains("Mahar", case=False, na=False),
        "STATE_UT"
    ].unique()
)

maharashtra = gdf[
    gdf["STATE_UT"]
    .astype(str)
    .str.contains("Mahar", case=False, na=False)
]

print("\nMaharashtra districts:")
for district in sorted(maharashtra["DISTRICT"].dropna().unique()):
    print(district)
