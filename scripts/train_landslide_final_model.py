from pathlib import Path

import geopandas as gpd
import pandas as pd
import numpy as np
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression


INPUT = Path(
    "data/processed/landslide/"
    "landslide_training_full.gpkg"
)

MODEL_OUT = Path(
    "models/"
    "landslide_logistic_model.joblib"
)

COEF_OUT = Path(
    "data/processed/landslide/"
    "landslide_model_coefficients.csv"
)

MODEL_OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)


print("Loading training data...")

gdf = gpd.read_file(INPUT)

print("Records:", len(gdf))


numeric_features = [
    "slope_deg",
    "elevation_m",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "dist_road_m",
]

categorical_features = [
    "lulc_class",
]

y = gdf["landslide"].astype(int)

X = gdf[
    numeric_features
    + categorical_features
].copy()


numeric_pipe = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scale",
            StandardScaler()
        ),
    ]
)

categorical_pipe = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            )
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        ),
    ]
)

preprocessor = ColumnTransformer(
    transformers=[
        (
            "num",
            numeric_pipe,
            numeric_features
        ),
        (
            "cat",
            categorical_pipe,
            categorical_features
        ),
    ]
)

model = LogisticRegression(
    class_weight="balanced",
    max_iter=5000,
    solver="liblinear",
    random_state=42,
)

pipeline = Pipeline(
    steps=[
        (
            "preprocess",
            preprocessor
        ),
        (
            "model",
            model
        ),
    ]
)


print("Training final model...")

pipeline.fit(
    X,
    y
)


# ============================================================
# FEATURE NAMES
# ============================================================

feature_names = (
    pipeline
    .named_steps["preprocess"]
    .get_feature_names_out()
)

coefficients = (
    pipeline
    .named_steps["model"]
    .coef_[0]
)

coef_df = pd.DataFrame(
    {
        "feature": feature_names,
        "coefficient": coefficients,
        "abs_coefficient": np.abs(
            coefficients
        ),
    }
)

coef_df = coef_df.sort_values(
    "abs_coefficient",
    ascending=False
)


print("\nMODEL COEFFICIENTS")
print("=" * 100)

print(
    coef_df
    .to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


coef_df.to_csv(
    COEF_OUT,
    index=False
)

joblib.dump(
    pipeline,
    MODEL_OUT
)


print("\nSaved:")
print(MODEL_OUT)
print(COEF_OUT)

print("\nDONE.")
