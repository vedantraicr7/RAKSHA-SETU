from pathlib import Path

import geopandas as gpd


HABITATIONS = Path(
    "data/processed/raigad_habitations_terrain_rainfall.gpkg"
)

CLIMATOLOGY = Path(
    "data/processed/raigad_rainfall_climatology_1995_2024.gpkg"
)

OUTPUT = Path(
    "data/processed/raigad_habitations_environment.gpkg"
)


print("Loading habitation digital twins...")
villages = gpd.read_file(HABITATIONS)

print("Habitations:", len(villages))

print("Loading rainfall climatology...")
clim = gpd.read_file(CLIMATOLOGY)

print("Climatology cells:", len(clim))


# --------------------------------------------------
# Convert both to WGS84
# --------------------------------------------------

villages_wgs = villages.to_crs("EPSG:4326")
clim = clim.to_crs("EPSG:4326")


# --------------------------------------------------
# Representative point for each habitation
# --------------------------------------------------

points = villages_wgs.copy()

points["geometry"] = (
    villages_wgs.geometry
    .representative_point()
)


# --------------------------------------------------
# Fields from climatology
# --------------------------------------------------

clim_columns = [
    "years_available",
    "clim_mean_annual_mm",
    "clim_median_annual_mm",
    "clim_std_annual_mm",
    "clim_min_annual_mm",
    "clim_max_annual_mm",
    "clim_mean_days_ge50",
    "clim_mean_days_ge100",
    "clim_mean_days_ge150",
    "hist_max_1day_mm",
    "annual_cv_pct",
    "geometry"
]


# --------------------------------------------------
# Spatial join
# --------------------------------------------------

joined = gpd.sjoin(
    points,
    clim[clim_columns],
    how="left",
    predicate="within"
)


# --------------------------------------------------
# Attach climatology
# --------------------------------------------------

output_columns = [
    "years_available",
    "clim_mean_annual_mm",
    "clim_median_annual_mm",
    "clim_std_annual_mm",
    "clim_min_annual_mm",
    "clim_max_annual_mm",
    "clim_mean_days_ge50",
    "clim_mean_days_ge100",
    "clim_mean_days_ge150",
    "hist_max_1day_mm",
    "annual_cv_pct"
]

for col in output_columns:
    villages[col] = joined[col].values


# --------------------------------------------------
# Calculate 2024 anomaly
# --------------------------------------------------

villages["rain_2024_anomaly_mm"] = (
    villages["annual_rain_mm"]
    -
    villages["clim_mean_annual_mm"]
)

villages["rain_2024_anomaly_pct"] = (
    villages["rain_2024_anomaly_mm"]
    /
    villages["clim_mean_annual_mm"]
    * 100
)


# --------------------------------------------------
# QA
# --------------------------------------------------

print("\nMissing climatology values:")

print(
    villages[output_columns]
    .isna()
    .sum()
)

print("\nYears available:")
print(
    villages["years_available"]
    .value_counts()
    .sort_index()
)

print("\nClimatological annual rainfall:")
print(
    villages["clim_mean_annual_mm"]
    .describe()
)

print("\n2024 rainfall anomaly (%):")
print(
    villages["rain_2024_anomaly_pct"]
    .describe()
)


# --------------------------------------------------
# Highest positive anomalies
# --------------------------------------------------

print("\nTop 15 positive 2024 rainfall anomalies:")
print("=" * 80)

cols = [
    "village",
    "subdistric",
    "vlcode",
    "clim_mean_annual_mm",
    "annual_rain_mm",
    "rain_2024_anomaly_mm",
    "rain_2024_anomaly_pct",
    "slope_mean_deg"
]

print(
    villages[cols]
    .sort_values(
        "rain_2024_anomaly_pct",
        ascending=False
    )
    .head(15)
    .to_string(index=False)
)


# --------------------------------------------------
# Save
# --------------------------------------------------

villages.to_file(
    OUTPUT,
    layer="raigad_habitations_environment",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
