from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid


VILLAGE_INPUT = Path(
    "data/raw/boundaries/"
    "maharashtra_villages/"
    "vb_soi_mh.shp"
)

SUBDISTRICT_INPUT = Path(
    "data/processed/"
    "raigad_subdistricts.gpkg"
)

OUTPUT = Path(
    "data/processed/"
    "raigad_villages.gpkg"
)


print("Loading Maharashtra villages...")

villages = gpd.read_file(VILLAGE_INPUT)

print("Total Maharashtra villages:", len(villages))


# --------------------------------------------------
# 1. Extract Raigad
# --------------------------------------------------

raigad = villages[
    villages["district"]
    .astype(str)
    .str.strip()
    .str.upper()
    == "RAIGAD"
].copy()

print("\nRaigad villages:", len(raigad))

if raigad.empty:
    raise ValueError("No Raigad villages found.")


# --------------------------------------------------
# 2. Preserve original administrative attributes
# --------------------------------------------------

raigad["source_district"] = raigad["district"]
raigad["source_dtcode"] = raigad["dtcode"]

raigad["source_subdistrict"] = raigad["subdistric"]
raigad["source_sdcode"] = raigad["sdcode"]


# --------------------------------------------------
# 3. Check geometry quality
# --------------------------------------------------

invalid_before = (~raigad.geometry.is_valid).sum()

print("\nInvalid geometries before repair:", invalid_before)

if invalid_before > 0:

    raigad["geometry"] = raigad.geometry.apply(
        lambda geom: make_valid(geom)
        if geom is not None and not geom.is_valid
        else geom
    )

invalid_after = (~raigad.geometry.is_valid).sum()

print("Invalid geometries after repair:", invalid_after)


# --------------------------------------------------
# 4. Load authoritative Raigad subdistrict polygons
# --------------------------------------------------

subdistricts = gpd.read_file(SUBDISTRICT_INPUT)

print(
    "\nAuthoritative subdistrict polygons:",
    len(subdistricts)
)


# --------------------------------------------------
# 5. Match CRS
# --------------------------------------------------

subdistricts = subdistricts.to_crs(raigad.crs)

print("Working CRS:", raigad.crs)


# --------------------------------------------------
# 6. Assign village to subdistrict spatially
#
# Use representative points so polygon boundary
# overlaps do not create multiple matches.
# --------------------------------------------------

points = raigad.copy()

points["geometry"] = (
    raigad.geometry
    .representative_point()
)

sub_lookup = subdistricts[
    [
        "SUB_DIST",
        "SUBDIS_LGD",
        "geometry"
    ]
].copy()

joined = gpd.sjoin(
    points,
    sub_lookup,
    how="left",
    predicate="within"
)


# --------------------------------------------------
# 7. Add authoritative spatial assignment
# --------------------------------------------------

raigad["verified_subdistrict"] = joined[
    "SUB_DIST"
].values

raigad["verified_sdcode"] = joined[
    "SUBDIS_LGD"
].astype("string").values


# --------------------------------------------------
# 8. Compare source vs spatial assignment
# --------------------------------------------------

source_name = (
    raigad["source_subdistrict"]
    .astype(str)
    .str.strip()
    .str.upper()
)

verified_name = (
    raigad["verified_subdistrict"]
    .astype(str)
    .str.strip()
    .str.upper()
)

source_code = (
    raigad["source_sdcode"]
    .astype(str)
    .str.strip()
)

verified_code = (
    raigad["verified_sdcode"]
    .astype(str)
    .str.strip()
)

raigad["subdistrict_name_match"] = (
    source_name == verified_name
)

raigad["subdistrict_code_match"] = (
    source_code == verified_code
)

raigad["admin_mismatch"] = ~(
    raigad["subdistrict_name_match"]
    &
    raigad["subdistrict_code_match"]
)


# --------------------------------------------------
# 9. Basic village-code checks
# --------------------------------------------------

duplicate_village_codes = (
    raigad["vlcode"]
    .duplicated(keep=False)
    .sum()
)

missing_village_codes = (
    raigad["vlcode"]
    .isna()
    .sum()
)

print("\nDuplicate village-code rows:", duplicate_village_codes)
print("Missing village codes:", missing_village_codes)


# --------------------------------------------------
# 10. Population checks
# --------------------------------------------------

missing_population = (
    raigad["total_popu"]
    .isna()
    .sum()
)

zero_population = (
    pd.to_numeric(
        raigad["total_popu"],
        errors="coerce"
    )
    .eq(0)
    .sum()
)

print("\nMissing population:", missing_population)
print("Zero population:", zero_population)


# --------------------------------------------------
# 11. Administrative mismatch report
# --------------------------------------------------

mismatches = raigad[
    raigad["admin_mismatch"]
].copy()

print(
    "\nAdministrative mismatches:",
    len(mismatches)
)

if not mismatches.empty:

    print("\nMismatch examples:")

    columns = [
        "village",
        "vlcode",
        "source_subdistrict",
        "source_sdcode",
        "verified_subdistrict",
        "verified_sdcode"
    ]

    print(
        mismatches[columns]
        .head(30)
        .to_string(index=False)
    )


# --------------------------------------------------
# 12. Save clean Raigad dataset
# --------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

raigad.to_file(
    OUTPUT,
    layer="raigad_villages",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nFinal Raigad village count:", len(raigad))
