from pathlib import Path
import rasterio

folder = Path(
    "data/raw/dem/copernicus_glo30"
)

files = sorted(folder.glob("*.tif"))

print("DEM tile count:", len(files))

for tif in files:

    print("\n" + "=" * 70)
    print(tif.name)
    print("=" * 70)

    with rasterio.open(tif) as src:

        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)
        print("Data type:", src.dtypes)
        print("NoData:", src.nodata)
