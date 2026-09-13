from pathlib import Path

import geopandas as gpd
import numpy as np


HABITATIONS = Path(
    "data/processed/raigad_habitations_environment.gpkg"
)

RIVERS = Path(
    "data/processed/raigad_river_network.gpkg"
)

OUTPUT = Path(
    "data/processed/raigad_habitations_environment_hydro.gpkg"
)

WORKING_CRS = "EPSG:32643"


print("Loading habitations...")
hab = gpd.read_file(HABITATIONS)

print("Habitations:", len(hab))

print("Loading CWC river network...")
rivers = gpd.read_file(RIVERS)

print("River features:", len(rivers))


# ============================================================
# PROJECT TO METRIC CRS
# ============================================================

hab_m = hab.to_crs(WORKING_CRS)
rivers_m = rivers.to_crs(WORKING_CRS)


# ============================================================
# REPRESENTATIVE POINTS
# ============================================================

points = hab_m.copy()

points["geometry"] = (
    hab_m.geometry.representative_point()
)


# ============================================================
# NEAREST RIVER
# ============================================================

print("\nCalculating nearest-river distances...")

river_fields = [
    "rivname",
    "UID_River",
    "geometry"
]

nearest = gpd.sjoin_nearest(
    points,
    rivers_m[river_fields],
    how="left",
    distance_col="dist_river_m"
)


# In rare cases, equal-distance river features can create
# duplicate habitation rows. Keep nearest result per original row.

nearest = (
    nearest
    .sort_values("dist_river_m")
    .groupby(nearest.index)
    .first()
)

nearest = nearest.reindex(points.index)


# ============================================================
# ATTACH RESULTS
# ============================================================

hab["dist_river_m"] = (
    nearest["dist_river_m"]
    .to_numpy()
)

hab["nearest_river"] = (
    nearest["rivname"]
    .to_numpy()
)

hab["nearest_river_uid"] = (
    nearest["UID_River"]
    .astype("string")
    .to_numpy()
)


# ============================================================
# DISTANCE FLAGS
# ============================================================

hab["river_within_250m"] = (
    hab["dist_river_m"] <= 250
)

hab["river_within_500m"] = (
    hab["dist_river_m"] <= 500
)

hab["river_within_1km"] = (
    hab["dist_river_m"] <= 1000
)

hab["river_within_2km"] = (
    hab["dist_river_m"] <= 2000
)


# ============================================================
# QA
# ============================================================

print("\nMissing river distances:")
print(
    hab["dist_river_m"].isna().sum()
)

print("\nRiver-distance statistics (metres):")
print(
    hab["dist_river_m"].describe()
)

print("\nDistance thresholds:")

for distance, column in [
    (250, "river_within_250m"),
    (500, "river_within_500m"),
    (1000, "river_within_1km"),
    (2000, "river_within_2km")
]:
    count = int(hab[column].sum())

    pct = (
        count / len(hab) * 100
    )

    print(
        f"Within {distance:4d} m: "
        f"{count:4d} "
        f"({pct:.2f}%)"
    )


print("\nClosest 20 habitations to CWC rivers:")
print("=" * 90)

cols = [
    "village",
    "subdistric",
    "vlcode",
    "total_popu",
    "dist_river_m",
    "nearest_river",
    "elev_mean_m",
    "slope_mean_deg"
]

print(
    hab[cols]
    .sort_values("dist_river_m")
    .head(20)
    .to_string(index=False)
)


# ============================================================
# SAVE
# ============================================================

hab.to_file(
    OUTPUT,
    layer="raigad_habitations_environment_hydro",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
