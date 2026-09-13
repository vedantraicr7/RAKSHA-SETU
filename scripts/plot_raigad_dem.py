import rasterio
import matplotlib.pyplot as plt
import numpy as np

path = "data/processed/raigad_dem.tif"

with rasterio.open(path) as src:

    dem = src.read(1)

    extent = [
        src.bounds.left,
        src.bounds.right,
        src.bounds.bottom,
        src.bounds.top
    ]

dem = np.where(
    np.isfinite(dem),
    dem,
    np.nan
)

fig, ax = plt.subplots(
    figsize=(10, 12)
)

img = ax.imshow(
    dem,
    extent=extent,
    origin="upper"
)

ax.set_title(
    "RAKSHA-SETU\n"
    "Raigad Elevation Model"
)

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

cbar = plt.colorbar(
    img,
    ax=ax,
    shrink=0.7
)

cbar.set_label(
    "Elevation (metres)"
)

plt.tight_layout()

output = (
    "data/processed/"
    "raigad_dem_map.png"
)

plt.savefig(
    output,
    dpi=250,
    bbox_inches="tight"
)

print("Map saved:", output)
