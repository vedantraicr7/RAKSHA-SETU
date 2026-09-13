from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask


DEM_DIR = Path(
    "data/raw/dem/copernicus_glo30"
)

DISTRICT_FILE = Path(
    "data/processed/raigad_district.gpkg"
)

OUTPUT = Path(
    "data/processed/raigad_dem.tif"
)


print("Finding DEM tiles...")

dem_files = sorted(
    DEM_DIR.glob("*.tif")
)

print("Tiles found:", len(dem_files))

if not dem_files:
    raise FileNotFoundError(
        "No DEM files found."
    )


# --------------------------------------------------
# 1. Open all DEM tiles
# --------------------------------------------------

datasets = [
    rasterio.open(path)
    for path in dem_files
]


# --------------------------------------------------
# 2. Mosaic
# --------------------------------------------------

print("\nCreating DEM mosaic...")

mosaic, transform = merge(datasets)

metadata = datasets[0].meta.copy()

metadata.update({
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": transform,
    "count": 1,
    "compress": "deflate"
})


# --------------------------------------------------
# 3. Create temporary mosaic
# --------------------------------------------------

TEMP = Path(
    "data/interim/raigad_dem_mosaic.tif"
)

TEMP.parent.mkdir(
    parents=True,
    exist_ok=True
)

with rasterio.open(
    TEMP,
    "w",
    **metadata
) as dst:

    dst.write(mosaic)


# --------------------------------------------------
# 4. Close source files
# --------------------------------------------------

for ds in datasets:
    ds.close()


# --------------------------------------------------
# 5. Load Raigad boundary
# --------------------------------------------------

print("Loading Raigad district boundary...")

district = gpd.read_file(
    DISTRICT_FILE
)


# --------------------------------------------------
# 6. Reproject boundary to DEM CRS
# --------------------------------------------------

with rasterio.open(TEMP) as src:

    district = district.to_crs(
        src.crs
    )

    geometries = [
        geom.__geo_interface__
        for geom in district.geometry
    ]


# --------------------------------------------------
# 7. Clip mosaic to Raigad polygon
# --------------------------------------------------

print("Clipping DEM to Raigad...")

with rasterio.open(TEMP) as src:

    clipped, clipped_transform = mask(
        src,
        geometries,
        crop=True
    )

    clipped_metadata = src.meta.copy()

    clipped_metadata.update({
        "height": clipped.shape[1],
        "width": clipped.shape[2],
        "transform": clipped_transform,
        "compress": "deflate"
    })


# --------------------------------------------------
# 8. Save final DEM
# --------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

with rasterio.open(
    OUTPUT,
    "w",
    **clipped_metadata
) as dst:

    dst.write(clipped)


print("\nSaved:")
print(OUTPUT)


# --------------------------------------------------
# 9. Inspect final DEM
# --------------------------------------------------

with rasterio.open(OUTPUT) as src:

    print("\nFinal DEM")
    print("=" * 60)

    print("CRS:", src.crs)
    print("Width:", src.width)
    print("Height:", src.height)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("Data type:", src.dtypes)
