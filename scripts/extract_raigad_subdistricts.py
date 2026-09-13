import geopandas as gpd
from pathlib import Path

DISTRICT_INPUT = Path(
    "data/raw/boundaries/india_admin/"
    "State_District_Subdistrict_PAN INDIA/"
    "District_Subdistrict_PAN INDIA/"
    "District Boundary.shp"
)

SUBDISTRICT_INPUT = Path(
    "data/raw/boundaries/india_admin/"
    "State_District_Subdistrict_PAN INDIA/"
    "District_Subdistrict_PAN INDIA/"
    "Sub_district Boundary.shp"
)

OUTPUT = Path(
    "data/processed/raigad_subdistricts.gpkg"
)

districts = gpd.read_file(DISTRICT_INPUT)
subdistricts = gpd.read_file(SUBDISTRICT_INPUT)

raigad = districts[
    (districts["STATE_UT"].astype(str).str.upper() == "MAHARASHTRA")
    &
    (districts["DISTRICT"].astype(str).str.upper() == "RAIGAD")
].copy()

if raigad.empty:
    raise ValueError("RAIGAD district not found in district layer.")

raigad_lgd = str(
    raigad.iloc[0]["DIST_LGD"]
).strip()

print("Raigad district LGD code:", raigad_lgd)

raigad_subdistricts = subdistricts[
    subdistricts["DIST_LGD"]
    .astype(str)
    .str.strip()
    == raigad_lgd
].copy()

if raigad_subdistricts.empty:
    raise ValueError(
        "No Raigad subdistricts found using DIST_LGD."
    )

print(
    "\nSubdistrict count:",
    len(raigad_subdistricts)
)

print("\nRaigad subdistricts:")

for _, row in (
    raigad_subdistricts
    .sort_values("SUB_DIST")
    .iterrows()
):
    print(
        f"- {row['SUB_DIST']} "
        f"(LGD: {row['SUBDIS_LGD']})"
    )

print("\nCRS:")
print(raigad_subdistricts.crs)

print("\nGeometry types:")
print(
    raigad_subdistricts
    .geometry
    .geom_type
    .value_counts()
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

raigad_subdistricts.to_file(
    OUTPUT,
    layer="raigad_subdistricts",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)
