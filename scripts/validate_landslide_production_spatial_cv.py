from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
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
    "landslide_production_spatial_cv_results.csv"
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

# ---------------------------------------------------------
# EXACT SAME ROAD TRANSFORMATION AS PRODUCTION MODEL
# ---------------------------------------------------------

gdf["road_proximity"] = np.exp(
    -gdf["dist_road_m"] / 500.0
)

# ---------------------------------------------------------
# SPATIAL GROUPS
# 10 km x 10 km blocks
# ---------------------------------------------------------

TARGET_CRS = "EPSG:32643"

gdf_metric = gdf.to_crs(TARGET_CRS)

BLOCK_SIZE = 10000

block_x = np.floor(
    gdf_metric.geometry.x / BLOCK_SIZE
).astype(int)

block_y = np.floor(
    gdf_metric.geometry.y / BLOCK_SIZE
).astype(int)

gdf["spatial_group"] = (
    block_x.astype(str)
    + "_"
    + block_y.astype(str)
)

print(
    "\nSpatial blocks:",
    gdf["spatial_group"].nunique()
)

# ---------------------------------------------------------
# EXACT PRODUCTION FEATURES
# ---------------------------------------------------------

numeric_features = [
    "slope_deg",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "road_proximity",
]

categorical_features = [
    "lulc_class",
]

features = (
    numeric_features
    + categorical_features
)

X = gdf[features].copy()

y = gdf["landslide"].astype(int)

groups = gdf["spatial_group"]

# ---------------------------------------------------------
# PREPROCESSING
# EXACT SAME LOGIC AS PRODUCTION MODEL
# ---------------------------------------------------------

numeric_pipe = Pipeline(
    [
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

categorical_pipe = Pipeline(
    [
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

preprocessor = ColumnTransformer(
    [
        (
            "num",
            numeric_pipe,
            numeric_features,
        ),
        (
            "cat",
            categorical_pipe,
            categorical_features,
        ),
    ]
)

# ---------------------------------------------------------
# SPATIAL CROSS VALIDATION
# ---------------------------------------------------------

cv = StratifiedGroupKFold(
    n_splits=5,
    shuffle=True,
    random_state=42,
)

results = []

fold_number = 0

for train_idx, test_idx in cv.split(
    X,
    y,
    groups=groups,
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

    print()
    print("=" * 70)
    print(f"FOLD {fold_number}")
    print("=" * 70)

    print(
        "Train:",
        len(train_idx),
        "Test:",
        len(test_idx),
    )

    print(
        "Train positives:",
        int(y_train.sum()),
        "Test positives:",
        int(y_test.sum()),
    )

    print(
        "Train blocks:",
        train_groups,
        "Test blocks:",
        test_groups,
    )

    if y_test.nunique() < 2:
        print(
            "Skipping fold: test set has one class."
        )
        continue

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=5000,
        solver="liblinear",
        random_state=42,
    )

    pipeline = Pipeline(
        [
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

    pipeline.fit(
        X_train,
        y_train,
    )

    prob = pipeline.predict_proba(
        X_test
    )[:, 1]

    pred = (
        prob >= 0.5
    ).astype(int)

    roc_auc = roc_auc_score(
        y_test,
        prob,
    )

    pr_auc = average_precision_score(
        y_test,
        prob,
    )

    balanced_accuracy = (
        balanced_accuracy_score(
            y_test,
            pred,
        )
    )

    print(
        f"ROC-AUC:           "
        f"{roc_auc:.3f}"
    )

    print(
        f"PR-AUC:            "
        f"{pr_auc:.3f}"
    )

    print(
        f"Balanced Accuracy: "
        f"{balanced_accuracy:.3f}"
    )

    results.append(
        {
            "fold": fold_number,
            "train_records":
                len(train_idx),
            "test_records":
                len(test_idx),
            "train_positives":
                int(y_train.sum()),
            "test_positives":
                int(y_test.sum()),
            "train_blocks":
                train_groups,
            "test_blocks":
                test_groups,
            "roc_auc":
                roc_auc,
            "pr_auc":
                pr_auc,
            "balanced_accuracy":
                balanced_accuracy,
        }
    )

results = pd.DataFrame(results)

print()
print("=" * 70)
print(
    "PRODUCTION MODEL "
    "SPATIAL CV SUMMARY"
)
print("=" * 70)

summary = results[
    [
        "roc_auc",
        "pr_auc",
        "balanced_accuracy",
    ]
].agg(
    ["mean", "std"]
)

print(
    summary
    .round(3)
    .to_string()
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

results.to_csv(
    OUTPUT,
    index=False,
)

print("\nSaved:")
print(OUTPUT)

print("\nDONE.")
