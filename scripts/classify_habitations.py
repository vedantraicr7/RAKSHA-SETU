import geopandas as gpd
import pandas as pd
from pathlib import Path


INPUT = Path(
    "data/processed/raigad_villages.gpkg"
)

OUTPUT_ALL = Path(
    "data/processed/raigad_villages_classified.gpkg"
)

OUTPUT_HAB = Path(
    "data/processed/raigad_habitations.gpkg"
)


print("Loading Raigad villages...")

gdf = gpd.read_file(INPUT)

print("Total records:", len(gdf))


# --------------------------------------------------
# 1. Default classification
# --------------------------------------------------

gdf["record_type"] = "habitation"

gdf["is_habitation"] = True

gdf["review_status"] = "accepted"


# --------------------------------------------------
# 2. Known non-habitation polygons
#
# vlcode 999999 in this dataset is being used for
# mapped water/geographic features rather than
# normal village records.
# --------------------------------------------------

non_habitation = (
    gdf["vlcode"]
    .astype(str)
    .str.strip()
    == "999999"
)

gdf.loc[
    non_habitation,
    "record_type"
] = "water_feature"

gdf.loc[
    non_habitation,
    "is_habitation"
] = False

gdf.loc[
    non_habitation,
    "review_status"
] = "excluded_from_habitation_analysis"


# --------------------------------------------------
# 3. Zero-population village records
#
# Do NOT delete them.
#
# Population = 0 does not prove that the polygon
# itself is not an administrative village.
# --------------------------------------------------

population = pd.to_numeric(
    gdf["total_popu"],
    errors="coerce"
)

zero_population_village = (
    population.eq(0)
    &
    (~non_habitation)
)

gdf.loc[
    zero_population_village,
    "review_status"
] = "zero_population_review"


# --------------------------------------------------
# 4. Administrative mismatch flag
# --------------------------------------------------

gdf.loc[
    gdf["admin_mismatch"] == True,
    "review_status"
] = "admin_boundary_review"


# Don't overwrite the stronger non-habitation
# classification for water features.

gdf.loc[
    non_habitation,
    "review_status"
] = "excluded_from_habitation_analysis"


# --------------------------------------------------
# 5. Create stable internal identifier
#
# Do not use vlcode alone because 999999 is repeated.
# --------------------------------------------------

gdf["raksha_id"] = [
    f"RAI-{i:04d}"
    for i in range(1, len(gdf) + 1)
]


# --------------------------------------------------
# 6. Create analytical habitation subset
# --------------------------------------------------

habitations = gdf[
    gdf["is_habitation"] == True
].copy()


# --------------------------------------------------
# 7. Statistics
# --------------------------------------------------

print("\nCLASSIFICATION")
print("=" * 60)

print(
    gdf["record_type"]
    .value_counts(dropna=False)
)

print("\nREVIEW STATUS")
print("=" * 60)

print(
    gdf["review_status"]
    .value_counts(dropna=False)
)

print("\nTotal source polygons:", len(gdf))
print("Habitation polygons:", len(habitations))
print(
    "Non-habitation polygons:",
    (~gdf["is_habitation"]).sum()
)

print(
    "Zero-population habitations:",
    (
        pd.to_numeric(
            habitations["total_popu"],
            errors="coerce"
        ).eq(0)
    ).sum()
)


# --------------------------------------------------
# 8. Check village-code uniqueness in habitation set
# --------------------------------------------------

duplicate_habitation_codes = (
    habitations["vlcode"]
    .duplicated(keep=False)
)

print(
    "Duplicate village-code rows "
    "after excluding water features:",
    duplicate_habitation_codes.sum()
)


# --------------------------------------------------
# 9. Save BOTH datasets
# --------------------------------------------------

gdf.to_file(
    OUTPUT_ALL,
    layer="raigad_villages_classified",
    driver="GPKG"
)

habitations.to_file(
    OUTPUT_HAB,
    layer="raigad_habitations",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT_ALL)
print(OUTPUT_HAB)
