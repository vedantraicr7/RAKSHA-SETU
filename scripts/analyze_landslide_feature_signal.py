import geopandas as gpd
import pandas as pd
import numpy as np

from sklearn.metrics import roc_auc_score
from scipy.stats import mannwhitneyu, spearmanr


INPUT = (
    "data/processed/landslide/"
    "landslide_training_environment.gpkg"
)

OUTPUT = (
    "data/processed/landslide/"
    "landslide_feature_signal.csv"
)


print("Loading landslide training dataset...")

gdf = gpd.read_file(INPUT)

print("Records:", len(gdf))
print()
print(gdf["landslide"].value_counts().sort_index())


features = [
    "slope_deg",
    "elevation_m",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "annual_cv_pct",
    "dist_drainage_m",
    "log_flow_acc",
]


results = []

y = gdf["landslide"].astype(int)


for feature in features:

    valid = gdf[
        ["landslide", feature]
    ].dropna()

    y_valid = valid["landslide"].astype(int)
    x = valid[feature].astype(float)

    control = valid.loc[
        valid["landslide"] == 0,
        feature
    ]

    landslide = valid.loc[
        valid["landslide"] == 1,
        feature
    ]

    auc = roc_auc_score(
        y_valid,
        x
    )

    # Direction-independent discrimination.
    # Example:
    # AUC 0.20 means the feature is strongly predictive
    # but in the negative direction.
    auc_strength = max(
        auc,
        1 - auc
    )

    direction = (
        "higher_at_landslides"
        if auc >= 0.5
        else "lower_at_landslides"
    )

    stat, p_value = mannwhitneyu(
        landslide,
        control,
        alternative="two-sided"
    )

    results.append(
        {
            "feature": feature,
            "control_mean": control.mean(),
            "landslide_mean": landslide.mean(),
            "control_median": control.median(),
            "landslide_median": landslide.median(),
            "auc_raw": auc,
            "auc_strength": auc_strength,
            "direction": direction,
            "mannwhitney_p": p_value,
        }
    )


results = pd.DataFrame(results)

results = results.sort_values(
    "auc_strength",
    ascending=False
)


print("\nINDIVIDUAL FEATURE DISCRIMINATION")
print("=" * 120)

print(
    results.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# ----------------------------------------------------------
# FEATURE CORRELATION
# ----------------------------------------------------------

print("\nSPEARMAN FEATURE CORRELATIONS")
print("=" * 100)

corr = (
    gdf[features]
    .corr(method="spearman")
)

print(
    corr.round(3).to_string()
)


print("\nHIGH CORRELATIONS |r| >= 0.70")
print("=" * 100)

found = False

for i in range(len(features)):

    for j in range(i + 1, len(features)):

        f1 = features[i]
        f2 = features[j]

        r = corr.loc[f1, f2]

        if abs(r) >= 0.70:

            found = True

            print(
                f"{f1:25s} "
                f"{f2:25s} "
                f"r={r:.3f}"
            )


if not found:
    print("None")


results.to_csv(
    OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
