import geopandas as gpd
import matplotlib.pyplot as plt


district = gpd.read_file(
    "data/processed/raigad_district.gpkg"
)

rivers = gpd.read_file(
    "data/processed/raigad_river_network.gpkg"
)

district = district.to_crs(rivers.crs)


fig, ax = plt.subplots(
    figsize=(10, 12)
)

district.boundary.plot(
    ax=ax,
    linewidth=1.5
)

rivers.plot(
    ax=ax,
    linewidth=0.7
)

ax.set_title(
    "RAKSHA-SETU\n"
    "Raigad CWC River Network"
)

ax.set_axis_off()

plt.tight_layout()

output = (
    "data/processed/"
    "raigad_river_network_map.png"
)

plt.savefig(
    output,
    dpi=250,
    bbox_inches="tight"
)

print("Map saved:", output)
