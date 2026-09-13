from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask


FLOW = Path(
    "data/processed/hydrology/"
    "raigad_flow_accumulation.tif"
)

DISTRICT = Path(
    "data/processed/raigad_district.gpkg"
)

OUTPUT = Path(
    "data/processed/hydrology/"
    "raigad_dem_drainage.tif"
)

THRESHOLD = 5000


print("Loading flow accumulation...")

with rasterio.open(FLOW) as src:

    flow = src.read(1)

    profile = src.profile.copy()

    raster_crs = src.crs
    transform = src.transform
    nodata = src.nodata

    district = gpd.read_file(DISTRICT)

    district = district.to_crs(
        raster_crs
    )

    inside_raigad = geometry_mask(
        district.geometry,
        out_shape=flow.shape,
        transform=transform,
        invert=True
    )

    valid = np.isfinite(flow)

    if nodata is not None:
        valid &= flow != nodata

    stream = np.zeros(
        flow.shape,
        dtype=np.uint8
    )

    stream[
        valid
        & inside_raigad
        & (flow >= THRESHOLD)
    ] = 1

    profile.update(
        dtype="uint8",
        nodata=0,
        count=1,
        compress="lzw"
    )

    with rasterio.open(
        OUTPUT,
        "w",
        **profile
    ) as dst:

        dst.write(
            stream,
            1
        )

    cell_area = (
        abs(src.res[0])
        * abs(src.res[1])
    )

    print("\nThreshold:", THRESHOLD)

    print(
        "Approx contributing area:",
        round(
            THRESHOLD
            * cell_area
            / 1_000_000,
            2
        ),
        "km²"
    )

    print(
        "Final stream pixels:",
        int(stream.sum())
    )


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
