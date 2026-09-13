from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from rasterio.plot import show


DISTRICT = Path(
    "data/processed/raigad_district.gpkg"
)

CWC = Path(
    "data/processed/raigad_river_network.gpkg"
)

HYDRO = Path(
    "data/processed/hydrology"
)

OUTPUT = HYDRO / "stream_threshold_comparison.png"

THRESHOLDS = [
    2000,
    5000,
    10000
]


district = gpd.read_file(DISTRICT)
cwc = gpd.read_file(CWC)


fig, axes = plt.subplots(
    1,
    3,
    figsize=(18, 10)
)


for ax, threshold in zip(
    axes,
    THRESHOLDS
):

    raster_path = (
        HYDRO /
        f"streams_threshold_{threshold}.tif"
    )

    with rasterio.open(
        raster_path
    ) as src:

        district_plot = district.to_crs(
            src.crs
        )

        cwc_plot = cwc.to_crs(
            src.crs
        )

        stream = src.read(1)

        show(
            stream,
            transform=src.transform,
            ax=ax
        )

        district_plot.boundary.plot(
            ax=ax,
            linewidth=1.2
        )

        cwc_plot.plot(
            ax=ax,
            linewidth=0.8
        )

    ax.set_title(
        f"Flow accumulation ≥ {threshold:,} cells"
    )

    ax.set_axis_off()


plt.suptitle(
    "RAKSHA-SETU — DEM-derived drainage threshold comparison",
    fontsize=16
)

plt.tight_layout()

plt.savefig(
    OUTPUT,
    dpi=200,
    bbox_inches="tight"
)

print("Saved:")
print(OUTPUT)
