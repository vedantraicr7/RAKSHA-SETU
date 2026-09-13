from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
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
    "landslide_production_model.joblib"
)

COEF_OUT = Path(
    "data/processed/landslide/"
    "landslide_production_coefficients.csv"
)


print("Loading training data...")

gdf = gpd.read_file(INPUT)

print("Records:", len(gdf))


# --------------------------------------------------
# Non-linear road proximity
# --------------------------------------------------

gdf["road_proximity"] = np.exp(
    -gdf["dist_road_m"] / 500.0
)


numeric_features = [
    "slope_deg",
    "clim_mean_annual_mm",
    "hist_max_1day_mm",
    "road_proximity",
]

categorical_features = [
    "lulc_class",
]


X = gdf[
    numeric_features
    + categorical_features
].copy()

y = gdf["landslide"].astype(int)


numeric_pipe = Pipeline(
    [
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
    [
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
    [
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
    [
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


print("Training production model...")

pipeline.fit(
    X,
    y
)


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
).sort_values(
    "abs_coefficient",
    ascending=False
)


print("\nPRODUCTION MODEL COEFFICIENTS")
print("=" * 100)

print(
    coef_df
    .to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


MODEL_OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

joblib.dump(
    pipeline,
    MODEL_OUT
)

coef_df.to_csv(
    COEF_OUT,
    index=False
)


print("\nSaved:")
print(MODEL_OUT)
print(COEF_OUT)

print("\nDONE.")
