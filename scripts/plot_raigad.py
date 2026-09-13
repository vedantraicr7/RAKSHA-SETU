import geopandas as gpd
import matplotlib.pyplot as pltpath = "data/processed/raigad_district.gpkg"

gdf = gpd.read_file(path)

ax = gdf.plot(
    figsize=(8, 10),
    edgecolor="black"
)

ax.set_title("Raigad District Boundary")
ax.set_axis_off()

plt.tight_layout()
plt.savefig(
    "data/processed/raigad_district_map.png",
    dpi=200,
    bbox_inches="tight"
)

print("Map saved: data/processed/raigad_district_map.png")
