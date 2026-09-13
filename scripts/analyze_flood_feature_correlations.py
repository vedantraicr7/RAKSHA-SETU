import geopandas as gpd
import pandas as pd


INPUT = (
    "data/processed/"
    "raigad_habitations_flood_features.gpkg"
)

OUTPUT = (
    "data/processed/"
    "flood_feature_correlations.csv"
)


print("Loading flood features...")

gdf = gpd.read_file(INPUT)

features = [
    "f_elevation",
    "f_flatness",
    "f_river_proximity",
    "f_drain_proximity",
    "f_drain_area",
    "f_clim_rain",
    "f_extreme_rain",
]


# --------------------------------------------------
# Correlation matrix
# --------------------------------------------------

corr = gdf[features].corr(
    method="spearman"
)

print("\nSPEARMAN CORRELATION MATRIX")
print("=" * 100)

print(
    corr.round(3).to_string()
)


# --------------------------------------------------
# Find strongly related feature pairs
# --------------------------------------------------

pairs = []

for i in range(len(features)):

    for j in range(i + 1, len(features)):

        a = features[i]
        b = features[j]

        value = corr.loc[a, b]

        pairs.append(
            {
                "feature_1": a,
                "feature_2": b,
                "spearman_r": value,
                "abs_r": abs(value),
            }
        )


pairs = pd.DataFrame(pairs)

pairs = pairs.sort_values(
    "abs_r",
    ascending=False
)


print("\nFEATURE PAIRS — strongest first")
print("=" * 80)

print(
    pairs[
        [
            "feature_1",
            "feature_2",
            "spearman_r",
        ]
    ]
    .round(3)
    .to_string(index=False)
)


print("\nPotential redundancy |r| >= 0.70")
print("=" * 80)

strong = pairs[
    pairs["abs_r"] >= 0.70
]

if len(strong) == 0:

    print(
        "No feature pairs reached "
        "|Spearman r| >= 0.70"
    )

else:

    print(
        strong[
            [
                "feature_1",
                "feature_2",
                "spearman_r",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )


# --------------------------------------------------
# Save
# --------------------------------------------------

corr.to_csv(OUTPUT)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
