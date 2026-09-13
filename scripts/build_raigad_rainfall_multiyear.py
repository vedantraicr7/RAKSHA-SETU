from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box


RAINFALL_DIR = Path("data/raw/rainfall")

DISTRICT_FILE = Path(
    "data/processed/raigad_district.gpkg"
)

OUTPUT_GRID = Path(
    "data/processed/raigad_rainfall_multiyear.gpkg"
)

OUTPUT_SUMMARY = Path(
    "data/processed/raigad_rainfall_year_summary.csv"
)


years = [2023, 2024, 2025]


# --------------------------------------------------
# Load district
# --------------------------------------------------

district = gpd.read_file(DISTRICT_FILE)
district = district.to_crs("EPSG:4326")

raigad_geom = district.geometry.union_all()

minx, miny, maxx, maxy = district.total_bounds

half_cell = 0.125

all_records = []
year_summary = []


# --------------------------------------------------
# Process each year
# --------------------------------------------------

for year in years:

    print("\n" + "=" * 70)
    print("Processing", year)
    print("=" * 70)

    path = (
        RAINFALL_DIR /
        f"RF25_ind{year}_rfp25.nc"
    )

    if not path.exists():
        print("Missing file:", path)
        continue

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

    year_records = []

    for lat in subset.LATITUDE.values:

        for lon in subset.LONGITUDE.values:

            cell = box(
                float(lon) - half_cell,
                float(lat) - half_cell,
                float(lon) + half_cell,
                float(lat) + half_cell
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

            valid = series[
                np.isfinite(series)
            ]

            if len(valid) == 0:
                continue

            record = {
                "year": year,
                "imd_lat": float(lat),
                "imd_lon": float(lon),
                "valid_days": int(len(valid)),

                "annual_rain_mm": float(
                    np.sum(valid)
                ),

                "max_1day_mm": float(
                    np.max(valid)
                ),

                "rain_days_ge50": int(
                    np.sum(valid >= 50)
                ),

                "rain_days_ge100": int(
                    np.sum(valid >= 100)
                ),

                "rain_days_ge150": int(
                    np.sum(valid >= 150)
                ),

                "wet_days_ge1": int(
                    np.sum(valid >= 1)
                ),

                "geometry": cell
            }

            year_records.append(record)
            all_records.append(record)

    if not year_records:
        print("No valid records for", year)
        ds.close()
        continue

    df = pd.DataFrame(
        [
            {
                k: v
                for k, v in r.items()
                if k != "geometry"
            }
            for r in year_records
        ]
    )

    summary = {
        "year": year,
        "grid_cells": len(df),
        "mean_annual_rain_mm":
            df["annual_rain_mm"].mean(),
        "min_annual_rain_mm":
            df["annual_rain_mm"].min(),
        "max_annual_rain_mm":
            df["annual_rain_mm"].max(),
        "mean_max_1day_mm":
            df["max_1day_mm"].mean(),
        "absolute_max_1day_mm":
            df["max_1day_mm"].max(),
        "mean_days_ge50":
            df["rain_days_ge50"].mean(),
        "mean_days_ge100":
            df["rain_days_ge100"].mean(),
        "mean_days_ge150":
            df["rain_days_ge150"].mean(),
    }

    year_summary.append(summary)

    print("Grid cells:", len(df))
    print(
        "Mean annual rainfall:",
        round(
            summary["mean_annual_rain_mm"],
            2
        ),
        "mm"
    )
    print(
        "Maximum 1-day rainfall:",
        round(
            summary["absolute_max_1day_mm"],
            2
        ),
        "mm"
    )

    ds.close()


# --------------------------------------------------
# Save multiyear grid
# --------------------------------------------------

grid = gpd.GeoDataFrame(
    all_records,
    crs="EPSG:4326"
)

grid.to_file(
    OUTPUT_GRID,
    layer="imd_rainfall_multiyear",
    driver="GPKG"
)


# --------------------------------------------------
# Save yearly summary
# --------------------------------------------------

summary_df = pd.DataFrame(year_summary)

summary_df.to_csv(
    OUTPUT_SUMMARY,
    index=False
)


print("\n" + "=" * 70)
print("YEAR SUMMARY")
print("=" * 70)

print(
    summary_df.to_string(
        index=False
    )
)

print("\nSaved:")
print(OUTPUT_GRID)
print(OUTPUT_SUMMARY)
