import geopandas as gpd
import matplotlib.pyplot as plt

district_path = "data/processed/raigad_district.gpkg"
subdistrict_path = "data/processed/raigad_subdistricts.gpkg"

district = gpd.read_file(district_path)
subdistricts = gpd.read_file(subdistrict_path)

fig, ax = plt.subplots(figsize=(10, 12))

# Outer Raigad district boundary
district.boundary.plot(
    ax=ax,
    linewidth=2
)

# Taluka/subdistrict boundaries
subdistricts.boundary.plot(
    ax=ax,
    linewidth=0.8
)

# Add taluka names
for _, row in subdistricts.iterrows():
    point = row.geometry.representative_point()

    ax.text(
        point.x,
        point.y,
        str(row["SUB_DIST"]),
        fontsize=7,
        ha="center",
        va="center"
    )

ax.set_title("Raigad District - Subdistrict Boundaries")
ax.set_axis_off()

plt.tight_layout()

output = "data/processed/raigad_subdistricts_map.png"

plt.savefig(
    output,
    dpi=220,
    bbox_inches="tight"
)

print(f"Map saved: {output}")
