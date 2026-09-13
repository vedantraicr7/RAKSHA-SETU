import re
import geopandas as gpd
import pandas as pd

TXT = "/tmp/landslide_inventory.txt"
BOUNDARY = "data/processed/raigad_district.gpkg"

OUT_GPKG = "data/processed/landslide/gsi_raigad_landslides.gpkg"
OUT_CSV = "data/processed/landslide/gsi_raigad_landslides.csv"

# GSI slide-number pattern
slide_pattern = re.compile(
    r"(MH/[A-Z]+/[A-Z0-9]+/\d{4}/[A-Z0-9]+)"
)

# Latitude/longitude pair appropriate for Maharashtra
coord_pattern = re.compile(
    r"\b(1[56789]\.\d+)\s+(7[2345]\.\d+)\b"
)

records = []

with open(TXT, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:

        # Restrict extraction to Maharashtra records
        if "Maharashtra" not in line:
            continue

        slide_match = slide_pattern.search(line)
        if not slide_match:
            continue

        coord_match = coord_pattern.search(line)
        if not coord_match:
            continue

        slide_no = slide_match.group(1)
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))

        records.append(
            {
                "slide_no": slide_no,
                "latitude": lat,
                "longitude": lon,
                "source_line": line.strip(),
            }
        )

df = pd.DataFrame(records)

print("Parsed Maharashtra coordinate records:", len(df))

# Remove exact duplicate slide IDs/coordinates
df = df.drop_duplicates(
    subset=["slide_no", "latitude", "longitude"]
).copy()

print("After duplicate removal:", len(df))

# Convert to GIS points
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(
        df["longitude"],
        df["latitude"]
    ),
    crs="EPSG:4326",
)

# Load authoritative Raigad boundary
district = gpd.read_file(BOUNDARY)

if district.crs is None:
    raise ValueError("Raigad boundary has no CRS.")

# Use same CRS for spatial filtering
district_4326 = district.to_crs("EPSG:4326")

raigad_geom = district_4326.geometry.union_all()

# Keep only points actually inside Raigad
raigad = gdf[gdf.geometry.within(raigad_geom)].copy()

print()
print("=" * 70)
print("GSI RAIGAD LANDSLIDE INVENTORY")
print("=" * 70)

print("Spatially verified landslides:", len(raigad))

if len(raigad):
    print()
    print("Coordinate ranges:")
    print(
        raigad[
            ["latitude", "longitude"]
        ].describe()
    )

    print()
    print("First 20:")
    print(
        raigad[
            [
                "slide_no",
                "latitude",
                "longitude",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

# Save
raigad.to_file(
    OUT_GPKG,
    layer="gsi_landslides",
    driver="GPKG",
)

raigad.drop(
    columns="geometry"
).to_csv(
    OUT_CSV,
    index=False,
)

print()
print("Saved:")
print(OUT_GPKG)
print(OUT_CSV)
print()
print("DONE.")
