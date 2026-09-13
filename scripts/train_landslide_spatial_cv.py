from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import (
    StandardScaler,
    OneHotEncoder,
)
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
)


INPUT = Path(
    "data/processed/landslide/"
    "landslide_training_full.gpkg"
)

OUTPUT = Path(
    "data/processed/landslide/"
    "landslide_spatial_cv_results.csv"
)


print("Loading training dataset...")

gdf = gpd.read_file(INPUT)

print("Records:", len(gdf))

print("\nClass counts:")
print(
    gdf["landslide"]
    .value_counts()
    .sort_index()
)


# ============================================================
# SPATIAL BLOCKS
# ============================================================
#
# 10 km grid blocks.
#
# Points inside the same block are kept together during
# train/test splitting.
# ============================================================

TARGET_CRS = "EPSG:32643"

gdf_metric = gdf.to_crs(TARGET_CRS)

centroids = gdf_metric.geometry

BLOCK_SIZE = 10000  # metres

block_x = (
    np.floor(
        centroids.x / BLOCK_SIZE
    )
    .astype(int)
)

block_y = (
    np.floor(
        centroids.y / BLOCK_SIZE
    )
    .astype(int)
)

gdf["spatial_group"] = (
    block_x.astype(str)
    + "_"
    + block_y.astype(str)
)


print("\nSpatial blocks:")
print(
    gdf["spatial_group"]
    .nunique()
)


# ============================================================
# FEATURES
# ============================================================

slope_features = [
    "slope_deg",
]


full_numeric_features = [
    "slope_deg",
    "elevation_m",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "annual_cv_pct",
    "dist_drainage_m",
    "log_flow_acc",
    "dist_road_m",
]

categorical_features = [
    "lulc_class",
]


# ============================================================
# MODEL BUILDER
# ============================================================

def build_model(
    numeric_features,
    categorical_features=None
):

    if categorical_features is None:
        categorical_features = []

    numeric_pipe = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scale",
                StandardScaler(),
            ),
        ]
    )

    transformers = [
        (
            "num",
            numeric_pipe,
            numeric_features,
        )
    ]

    if categorical_features:

        categorical_pipe = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="most_frequent"
                    ),
                ),
                (
                    "onehot",
                    OneHotEncoder(
                        handle_unknown="ignore"
                    ),
                ),
            ]
        )

        transformers.append(
            (
                "cat",
                categorical_pipe,
                categorical_features,
            )
        )

    preprocessor = ColumnTransformer(
        transformers=transformers
    )

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=5000,
        solver="liblinear",
        random_state=42,
    )

    return Pipeline(
        steps=[
            (
                "preprocess",
                preprocessor,
            ),
            (
                "model",
                model,
            ),
        ]
    )


# ============================================================
# SPATIAL CV
# ============================================================

cv = StratifiedGroupKFold(
    n_splits=5,
    shuffle=True,
    random_state=42,
)

y = gdf["landslide"].astype(int)

groups = gdf["spatial_group"]


model_configs = {
    "slope_only": (
        slope_features,
        []
    ),

    "full_model": (
        full_numeric_features,
        categorical_features
    ),
}


results = []


for model_name, (
    numeric_features,
    categorical_features
) in model_configs.items():

    print()
    print("=" * 100)
    print("MODEL:", model_name)
    print("=" * 100)

    features = (
        numeric_features
        + categorical_features
    )

    X = gdf[features].copy()

    fold_number = 0

    for train_idx, test_idx in cv.split(
        X,
        y,
        groups=groups
    ):

        fold_number += 1

        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]

        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]

        train_groups = (
            groups.iloc[train_idx]
            .nunique()
        )

        test_groups = (
            groups.iloc[test_idx]
            .nunique()
        )

        print(
            f"\nFold {fold_number}"
        )

        print(
            "Train:",
            len(train_idx),
            "Test:",
            len(test_idx)
        )

        print(
            "Train positives:",
            int(y_train.sum()),
            "Test positives:",
            int(y_test.sum())
        )

        print(
            "Train blocks:",
            train_groups,
            "Test blocks:",
            test_groups
        )

        # Safety check
        if y_test.nunique() < 2:

            print(
                "Skipping fold: "
                "test set has one class."
            )

            continue

        model = build_model(
            numeric_features,
            categorical_features
        )

        model.fit(
            X_train,
            y_train
        )

        prob = model.predict_proba(
            X_test
        )[:, 1]

        pred = (
            prob >= 0.5
        ).astype(int)

        roc_auc = roc_auc_score(
            y_test,
            prob
        )

        pr_auc = average_precision_score(
            y_test,
            prob
        )

        bal_acc = balanced_accuracy_score(
            y_test,
            pred
        )

        print(
            f"ROC-AUC:              "
            f"{roc_auc:.3f}"
        )

        print(
            f"PR-AUC:               "
            f"{pr_auc:.3f}"
        )

        print(
            f"Balanced accuracy:    "
            f"{bal_acc:.3f}"
        )

        results.append(
            {
                "model": model_name,
                "fold": fold_number,
                "train_records": len(
                    train_idx
                ),
                "test_records": len(
                    test_idx
                ),
                "train_positives": int(
                    y_train.sum()
                ),
                "test_positives": int(
                    y_test.sum()
                ),
                "train_blocks": train_groups,
                "test_blocks": test_groups,
                "roc_auc": roc_auc,
                "pr_auc": pr_auc,
                "balanced_accuracy": bal_acc,
            }
        )


results = pd.DataFrame(results)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 100)
print("SPATIAL CROSS-VALIDATION SUMMARY")
print("=" * 100)


summary = (
    results
    .groupby("model")
    .agg(
        folds=("fold", "count"),

        roc_auc_mean=(
            "roc_auc",
            "mean"
        ),

        roc_auc_std=(
            "roc_auc",
            "std"
        ),

        pr_auc_mean=(
            "pr_auc",
            "mean"
        ),

        pr_auc_std=(
            "pr_auc",
            "std"
        ),

        balanced_accuracy_mean=(
            "balanced_accuracy",
            "mean"
        ),

        balanced_accuracy_std=(
            "balanced_accuracy",
            "std"
        ),
    )
)


print(
    summary
    .round(3)
    .to_string()
)


results.to_csv(
    OUTPUT,
    index=False
)


print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
