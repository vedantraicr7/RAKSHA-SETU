from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box


# ============================================================
# CONFIGURATION
# ============================================================

RAINFALL_DIR = Path("data/raw/rainfall")

DISTRICT_FILE = Path(
    "data/processed/raigad_district.gpkg"
)

OUTPUT_GRID = Path(
    "data/processed/raigad_rainfall_climatology_1995_2024.gpkg"
)

OUTPUT_YEARLY = Path(
    "data/processed/raigad_rainfall_yearly_1995_2024.csv"
)

START_YEAR = 1995
END_YEAR = 2024

YEARS = range(START_YEAR, END_YEAR + 1)

HALF_CELL = 0.125


# ============================================================
# LOAD RAIGAD
# ============================================================

print("Loading Raigad boundary...")

district = gpd.read_file(DISTRICT_FILE)
district = district.to_crs("EPSG:4326")

raigad_geom = district.geometry.union_all()

minx, miny, maxx, maxy = district.total_bounds

print("Raigad bounds:")
print(minx, miny, maxx, maxy)


# ============================================================
# STORAGE
# ============================================================

cell_year_records = []
year_summary_records = []


# ============================================================
# PROCESS 1995-2024
# ============================================================

for year in YEARS:

    print("\n" + "=" * 70)
    print(f"Processing {year}")
    print("=" * 70)

    path = (
        RAINFALL_DIR /
        f"RF25_ind{year}_rfp25.nc"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Missing rainfall file: {path}"
        )

    ds = xr.open_dataset(path)

    rain = ds["RAINFALL"]

    subset = rain.sel(
        LATITUDE=slice(
            miny - 0.25,
            maxy + 0.25
        ),
        LONGITUDE=slice(
            minx - 0.25,
            maxx + 0.25
        )
    )

    current_year = []

    for lat in subset.LATITUDE.values:

        for lon in subset.LONGITUDE.values:

            cell = box(
                float(lon) - HALF_CELL,
                float(lat) - HALF_CELL,
                float(lon) + HALF_CELL,
                float(lat) + HALF_CELL
            )

            if not cell.intersects(raigad_geom):
                continue

            series = subset.sel(
                LATITUDE=lat,
                LONGITUDE=lon
            ).values

            series = np.asarray(
                series,
                dtype=float
            )

            valid = series[np.isfinite(series)]

            if len(valid) == 0:
                continue

            expected_days = (
                366
                if pd.Timestamp(
                    f"{year}-12-31"
                ).dayofyear == 366
                else 365
            )

            record = {
                "year": year,
                "imd_lat": float(lat),
                "imd_lon": float(lon),

                "valid_days": int(len(valid)),
                "expected_days": expected_days,

                "annual_rain_mm": float(
                    np.sum(valid)
                ),

                "max_1day_mm": float(
                    np.max(valid)
                ),

                "wet_days_ge1": int(
                    np.sum(valid >= 1)
                ),

                "days_ge50": int(
                    np.sum(valid >= 50)
                ),

                "days_ge100": int(
                    np.sum(valid >= 100)
                ),

                "days_ge150": int(
                    np.sum(valid >= 150)
                ),

                "geometry": cell
            }

            current_year.append(record)
            cell_year_records.append(record)

    ds.close()

    if len(current_year) == 0:
        raise ValueError(
            f"No Raigad rainfall cells for {year}"
        )

    df_year = pd.DataFrame([
        {
            k: v
            for k, v in r.items()
            if k != "geometry"
        }
        for r in current_year
    ])

    incomplete = (
        df_year["valid_days"]
        < df_year["expected_days"]
    ).sum()

    print("Grid cells:", len(df_year))
    print("Incomplete cells:", incomplete)

    print(
        "Mean annual rainfall:",
        round(
            df_year["annual_rain_mm"].mean(),
            2
        ),
        "mm"
    )

    year_summary_records.append({
        "year": year,

        "grid_cells": len(df_year),

        "incomplete_cells": int(incomplete),

        "mean_annual_rain_mm": float(
            df_year["annual_rain_mm"].mean()
        ),

        "median_annual_rain_mm": float(
            df_year["annual_rain_mm"].median()
        ),

        "min_annual_rain_mm": float(
            df_year["annual_rain_mm"].min()
        ),

        "max_annual_rain_mm": float(
            df_year["annual_rain_mm"].max()
        ),

        "mean_days_ge50": float(
            df_year["days_ge50"].mean()
        ),

        "mean_days_ge100": float(
            df_year["days_ge100"].mean()
        ),

        "mean_days_ge150": float(
            df_year["days_ge150"].mean()
        ),

        "absolute_max_1day_mm": float(
            df_year["max_1day_mm"].max()
        )
    })


# ============================================================
# CONVERT TO DATAFRAME
# ============================================================

print("\nBuilding 30-year climatology...")

all_df = pd.DataFrame([
    {
        k: v
        for k, v in r.items()
        if k != "geometry"
    }
    for r in cell_year_records
])


# ============================================================
# CALCULATE CLIMATOLOGY PER IMD CELL
# ============================================================

climatology = (
    all_df
    .groupby(
        ["imd_lat", "imd_lon"],
        as_index=False
    )
    .agg(
        years_available=(
            "year",
            "nunique"
        ),

        clim_mean_annual_mm=(
            "annual_rain_mm",
            "mean"
        ),

        clim_median_annual_mm=(
            "annual_rain_mm",
            "median"
        ),

        clim_std_annual_mm=(
            "annual_rain_mm",
            "std"
        ),

        clim_min_annual_mm=(
            "annual_rain_mm",
            "min"
        ),

        clim_max_annual_mm=(
            "annual_rain_mm",
            "max"
        ),

        clim_mean_days_ge50=(
            "days_ge50",
            "mean"
        ),

        clim_mean_days_ge100=(
            "days_ge100",
            "mean"
        ),

        clim_mean_days_ge150=(
            "days_ge150",
            "mean"
        ),

        hist_max_1day_mm=(
            "max_1day_mm",
            "max"
        )
    )
)


# coefficient of variation
climatology["annual_cv_pct"] = (
    climatology["clim_std_annual_mm"]
    /
    climatology["clim_mean_annual_mm"]
    * 100
)


# ============================================================
# ADD GEOMETRY BACK
# ============================================================

geometry_lookup = {}

for record in cell_year_records:

    key = (
        record["imd_lat"],
        record["imd_lon"]
    )

    geometry_lookup[key] = record["geometry"]


climatology["geometry"] = climatology.apply(
    lambda row: geometry_lookup[
        (
            row["imd_lat"],
            row["imd_lon"]
        )
    ],
    axis=1
)


clim_gdf = gpd.GeoDataFrame(
    climatology,
    geometry="geometry",
    crs="EPSG:4326"
)


# ============================================================
# QA
# ============================================================

print("\n" + "=" * 70)
print("CLIMATOLOGY QA")
print("=" * 70)

print("Years expected:", 30)

print(
    "Grid cells:",
    len(clim_gdf)
)

print("\nYears available per cell:")

print(
    clim_gdf["years_available"]
    .value_counts()
    .sort_index()
)

print("\n30-year mean annual rainfall:")

print(
    clim_gdf["clim_mean_annual_mm"]
    .describe()
)

print("\nHistorical maximum 1-day rainfall:")

print(
    clim_gdf["hist_max_1day_mm"]
    .describe()
)

print("\nMean days >= 50 mm/year:")

print(
    clim_gdf["clim_mean_days_ge50"]
    .describe()
)

print("\nAnnual rainfall CV (%):")

print(
    clim_gdf["annual_cv_pct"]
    .describe()
)


# ============================================================
# SAVE CLIMATOLOGY
# ============================================================

clim_gdf.to_file(
    OUTPUT_GRID,
    layer="rainfall_climatology_1995_2024",
    driver="GPKG"
)


# ============================================================
# SAVE YEARLY SUMMARY
# ============================================================

year_summary = pd.DataFrame(
    year_summary_records
)

year_summary.to_csv(
    OUTPUT_YEARLY,
    index=False
)


print("\n" + "=" * 70)
print("YEARLY DISTRICT-GRID SUMMARY")
print("=" * 70)

print(
    year_summary[
        [
            "year",
            "grid_cells",
            "incomplete_cells",
            "mean_annual_rain_mm",
            "absolute_max_1day_mm"
        ]
    ].to_string(index=False)
)


print("\nSaved:")
print(OUTPUT_GRID)
print(OUTPUT_YEARLY)

print("\nDONE.")
