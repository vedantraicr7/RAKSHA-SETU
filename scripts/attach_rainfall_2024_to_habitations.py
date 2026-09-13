from pathlib import Path

import geopandas as gpd


HABITATIONS = Path(
    "data/processed/raigad_habitations_terrain.gpkg"
)

RAINFALL_GRID = Path(
    "data/processed/raigad_rainfall_2024.gpkg"
)

OUTPUT = Path(
    "data/processed/raigad_habitations_terrain_rainfall.gpkg"
)


print("Loading habitations...")
villages = gpd.read_file(HABITATIONS)

print("Loading rainfall grid...")
rain = gpd.read_file(RAINFALL_GRID)


# --------------------------------------------------
# 1. Convert both to WGS84
# --------------------------------------------------

villages_wgs = villages.to_crs("EPSG:4326")
rain = rain.to_crs("EPSG:4326")


# --------------------------------------------------
# 2. Representative point for each habitation
# --------------------------------------------------

points = villages_wgs.copy()

points["geometry"] = (
    villages_wgs.geometry
    .representative_point()
)


# --------------------------------------------------
# 3. Spatial join to rainfall cell
# --------------------------------------------------

rain_cols = [
    "annual_rain_mm",
    "max_1day_mm",
    "rain_days_ge50",
    "rain_days_ge100",
    "rain_days_ge150",
    "wet_days_ge1",
    "imd_lat",
    "imd_lon",
    "geometry"
]

joined = gpd.sjoin(
    points,
    rain[rain_cols],
    how="left",
    predicate="within"
)


# --------------------------------------------------
# 4. Attach rainfall values back to original geometry
# --------------------------------------------------

rain_columns = [
    "annual_rain_mm",
    "max_1day_mm",
    "rain_days_ge50",
    "rain_days_ge100",
    "rain_days_ge150",
    "wet_days_ge1",
    "imd_lat",
    "imd_lon"
]

for col in rain_columns:
    villages[col] = joined[col].values


# --------------------------------------------------
# 5. QA
# --------------------------------------------------

print("\nMissing rainfall values:")
print(
    villages[rain_columns]
    .isna()
    .sum()
)

print("\nAnnual rainfall summary:")
print(
    villages["annual_rain_mm"]
    .describe()
)

print("\nMax 1-day rainfall summary:")
print(
    villages["max_1day_mm"]
    .describe()
)


# --------------------------------------------------
# 6. Save
# --------------------------------------------------

villages.to_file(
    OUTPUT,
    layer="raigad_habitations_terrain_rainfall",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)
