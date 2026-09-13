from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt


INPUT = Path(
    "data/processed/hydrology/"
    "raigad_dem_drainage.tif"
)

OUTPUT = Path(
    "data/processed/hydrology/"
    "raigad_distance_to_drainage_m.tif"
)


print("Loading drainage raster...")

with rasterio.open(INPUT) as src:

    drainage = src.read(1)

    profile = src.profile.copy()

    pixel_x = abs(src.res[0])
    pixel_y = abs(src.res[1])

    print("CRS:", src.crs)
    print("Resolution:", src.res)

    stream_mask = drainage == 1

    print(
        "Drainage pixels:",
        int(stream_mask.sum())
    )

    if stream_mask.sum() == 0:
        raise ValueError(
            "No drainage pixels found."
        )

    # distance_transform_edt measures distance
    # to the nearest zero.
    # Therefore drainage pixels are set to zero.
    distance_m = distance_transform_edt(
        ~stream_mask,
        sampling=(pixel_y, pixel_x)
    ).astype("float32")

    profile.update(
        dtype="float32",
        nodata=-9999,
        compress="deflate"
    )

    with rasterio.open(
        OUTPUT,
        "w",
        **profile
    ) as dst:

        dst.write(
            distance_m,
            1
        )


print("\nDistance statistics:")

print(
    "Min:",
    round(float(distance_m.min()), 2),
    "m"
)

print(
    "Mean:",
    round(float(distance_m.mean()), 2),
    "m"
)

print(
    "Median:",
    round(float(np.median(distance_m)), 2),
    "m"
)

print(
    "Max:",
    round(float(distance_m.max()), 2),
    "m"
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
