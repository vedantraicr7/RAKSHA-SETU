from pathlib import Path

import numpy as np
import rasterio


FLOW = Path(
    "data/processed/hydrology/"
    "raigad_flow_accumulation.tif"
)

OUT_DIR = Path(
    "data/processed/hydrology"
)

THRESHOLDS = [
    2000,
    5000,
    10000
]


with rasterio.open(FLOW) as src:

    flow = src.read(1)

    profile = src.profile.copy()

    nodata = src.nodata

    valid = np.isfinite(flow)

    if nodata is not None:
        valid &= flow != nodata

    cell_area_m2 = (
        abs(src.res[0])
        *
        abs(src.res[1])
    )

    print(
        "Cell area:",
        round(cell_area_m2, 2),
        "m²"
    )

    profile.update(
        dtype="uint8",
        nodata=0,
        count=1,
        compress="lzw"
    )

    for threshold in THRESHOLDS:

        stream = np.zeros(
            flow.shape,
            dtype=np.uint8
        )

        stream[
            valid &
            (flow >= threshold)
        ] = 1

        output = (
            OUT_DIR /
            f"streams_threshold_{threshold}.tif"
        )

        with rasterio.open(
            output,
            "w",
            **profile
        ) as dst:

            dst.write(
                stream,
                1
            )

        stream_pixels = int(
            stream.sum()
        )

        catchment_km2 = (
            threshold
            *
            cell_area_m2
            /
            1_000_000
        )

        print(
            f"\nThreshold: {threshold}"
        )

        print(
            "Approx catchment threshold:",
            round(catchment_km2, 2),
            "km²"
        )

        print(
            "Stream pixels:",
            stream_pixels
        )

        print(
            "Saved:",
            output
        )


print("\nDONE.")
