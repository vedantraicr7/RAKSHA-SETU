import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


HABITATIONS = Path(
    "data/processed/raigad_habitations.gpkg"
)

SUBDISTRICTS = Path(
    "data/processed/raigad_subdistricts.gpkg"
)

OUTPUT = Path(
    "data/processed/raigad_population_map.png"
)


print("Loading data...")

villages = gpd.read_file(HABITATIONS)
subdistricts = gpd.read_file(SUBDISTRICTS)

# Ensure both layers use the same CRS
subdistricts = subdistricts.to_crs(villages.crs)

villages["population"] = pd.to_numeric(
    villages["total_popu"],
    errors="coerce"
).fillna(0)

print("Habitations:", len(villages))
print("Total population:", int(villages["population"].sum()))
print("Maximum village population:", int(villages["population"].max()))

fig, ax = plt.subplots(
    figsize=(11, 13)
)

villages.plot(
    ax=ax,
    column="population",
    cmap="YlOrRd",
    linewidth=0.05,
    edgecolor="grey",
    legend=True,
    legend_kwds={
        "label": "Population",
        "shrink": 0.6
    }
)

subdistricts.boundary.plot(
    ax=ax,
    linewidth=0.8,
    color="black"
)

for _, row in subdistricts.iterrows():

    point = row.geometry.representative_point()

    ax.text(
        point.x,
        point.y,
        str(row["SUB_DIST"]),
        fontsize=6,
        ha="center",
        va="center"
    )

ax.set_title(
    "RAKSHA-SETU\n"
    "Raigad Village Population Distribution",
    fontsize=15
)

ax.set_axis_off()

plt.tight_layout()

plt.savefig(
    OUTPUT,
    dpi=250,
    bbox_inches="tight"
)

print("\nMap saved:")
print(OUTPUT)
