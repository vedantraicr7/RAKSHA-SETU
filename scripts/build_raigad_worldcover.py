from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.merge import merge


TILES = [
    Path(
        "data/raw/landslide/lulc/worldcover/"
        "ESA_WorldCover_10m_2021_v200_N15E072_Map.tif"
    ),
    Path(
        "data/raw/landslide/lulc/worldcover/"
        "ESA_WorldCover_10m_2021_v200_N18E072_Map.tif"
    ),
]

DISTRICT = Path(
    "data/processed/raigad_district.gpkg"
)

OUT_DIR = Path(
    "data/processed/landslide"
)

OUTPUT = OUT_DIR / "raigad_worldcover_2021.tif"

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

district = gpd.read_file(
    DISTRICT
)

temporary_files = []


print("Clipping WorldCover tiles individually...")


for i, tile in enumerate(TILES, start=1):

    print(f"\nProcessing tile {i}:")
    print(tile)

    with rasterio.open(tile) as src:

        boundary = district.to_crs(
            src.crs
        )

        tile_bounds = src.bounds

        # Quick intersection check
        district_bounds = boundary.total_bounds

        intersects = not (
            district_bounds[2] < tile_bounds.left
            or district_bounds[0] > tile_bounds.right
            or district_bounds[3] < tile_bounds.bottom
            or district_bounds[1] > tile_bounds.top
        )

        if not intersects:

            print(
                "No intersection with Raigad. Skipping."
            )

            continue

        shapes = [
            geom.__geo_interface__
            for geom in boundary.geometry
        ]

        clipped, transform = mask(
            src,
            shapes,
            crop=True,
            nodata=0
        )

        profile = src.profile.copy()

        profile.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=transform,
            compress="lzw"
        )

        temp = (
            OUT_DIR /
            f"_worldcover_clip_{i}.tif"
        )

        with rasterio.open(
            temp,
            "w",
            **profile
        ) as dst:

            dst.write(clipped)

        temporary_files.append(
            temp
        )

        print(
            "Saved temporary clip:",
            temp
        )


if not temporary_files:

    raise RuntimeError(
        "No WorldCover tiles intersected Raigad."
    )


print("\nMerging clipped pieces...")


sources = [
    rasterio.open(path)
    for path in temporary_files
]

mosaic, transform = merge(
    sources,
    nodata=0
)

profile = sources[0].profile.copy()

profile.update(
    height=mosaic.shape[1],
    width=mosaic.shape[2],
    transform=transform,
    nodata=0,
    compress="lzw"
)


with rasterio.open(
    OUTPUT,
    "w",
    **profile
) as dst:

    dst.write(mosaic)


for src in sources:
    src.close()


for temp in temporary_files:
    temp.unlink(
        missing_ok=True
    )


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
