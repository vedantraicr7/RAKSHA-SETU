from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box


RAINFALL_FILE = Path(
    "data/raw/rainfall/RF25_ind2024_rfp25.nc"
)

DISTRICT_FILE = Path(
    "data/processed/raigad_district.gpkg"
)

OUTPUT = Path(
    "data/processed/raigad_rainfall_2024.gpkg"
)


print("Loading IMD rainfall...")

ds = xr.open_dataset(RAINFALL_FILE)

rain = ds["RAINFALL"]


# --------------------------------------------------
# 1. Load Raigad boundary in WGS84
# --------------------------------------------------

district = gpd.read_file(DISTRICT_FILE)

district = district.to_crs("EPSG:4326")

raigad_geom = district.geometry.union_all()

minx, miny, maxx, maxy = district.total_bounds

print("\nRaigad bounds:")
print(minx, miny, maxx, maxy)


# --------------------------------------------------
# 2. Select nearby IMD grid centres
#
# Add half-cell padding because IMD resolution
# is 0.25 degrees.
# --------------------------------------------------

subset = rain.sel(
    LATITUDE=slice(miny - 0.25, maxy + 0.25),
    LONGITUDE=slice(minx - 0.25, maxx + 0.25)
)

print("\nCandidate rainfall grid:")
print(
    len(subset.LATITUDE),
    "latitudes ×",
    len(subset.LONGITUDE),
    "longitudes"
)


# --------------------------------------------------
# 3. Build 0.25-degree grid polygons
# --------------------------------------------------

records = []

half_cell = 0.125

for lat in subset.LATITUDE.values:

    for lon in subset.LONGITUDE.values:

        cell = box(
            float(lon) - half_cell,
            float(lat) - half_cell,
            float(lon) + half_cell,
            float(lat) + half_cell
        )

        # Ignore cells that do not intersect Raigad
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

        records.append({
            "year": 2024,

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
        })


# --------------------------------------------------
# 4. Create GeoDataFrame
# --------------------------------------------------

grid = gpd.GeoDataFrame(
    records,
    crs="EPSG:4326"
)

print("\nValid Raigad-intersecting IMD cells:")
print(len(grid))


# --------------------------------------------------
# 5. QA
# --------------------------------------------------

print("\nValid-day counts:")
print(
    grid["valid_days"]
    .value_counts()
    .sort_index()
)

print("\nAnnual rainfall summary (mm):")
print(
    grid["annual_rain_mm"]
    .describe()
)

print("\nMaximum 1-day rainfall summary (mm):")
print(
    grid["max_1day_mm"]
    .describe()
)

print("\nHeavy rainfall days >= 50 mm:")
print(
    grid["rain_days_ge50"]
    .describe()
)

print("\nVery heavy rainfall days >= 100 mm:")
print(
    grid["rain_days_ge100"]
    .describe()
)

print("\nExtreme rainfall days >= 150 mm:")
print(
    grid["rain_days_ge150"]
    .describe()
)


# --------------------------------------------------
# 6. Show grid-cell metrics
# --------------------------------------------------

display_columns = [
    "imd_lat",
    "imd_lon",
    "valid_days",
    "annual_rain_mm",
    "max_1day_mm",
    "rain_days_ge50",
    "rain_days_ge100",
    "rain_days_ge150"
]

print("\nRaigad rainfall cells:")
print(
    grid[display_columns]
    .sort_values(
        ["imd_lat", "imd_lon"]
    )
    .to_string(index=False)
)


# --------------------------------------------------
# 7. Save
# --------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

grid.to_file(
    OUTPUT,
    layer="imd_rainfall_2024",
    driver="GPKG"
)

print("\nSaved:")
print(OUTPUT)

ds.close()
