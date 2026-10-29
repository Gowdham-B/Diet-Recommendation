"""
Preprocessing pipeline construction using Scikit-Learn ColumnTransformer.
Ensures rigorous train/test separation and handles categorical encoding and feature scaling.
"""
from typing import Tuple
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from src.features.feature_schema import (
    NUMERICAL_FEATURES,
    INTERACTION_FEATURES,
    CATEGORICAL_FEATURES,
    ALL_FEATURE_COLUMNS,
)


def create_preprocessor() -> ColumnTransformer:
    """
    Constructs a ColumnTransformer applying StandardScaler to numeric features
    and OneHotEncoder to categorical features.
    """
    numeric_cols = NUMERICAL_FEATURES + INTERACTION_FEATURES
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor


def fit_preprocessor(df_train: pd.DataFrame) -> ColumnTransformer:
    """
    Fits preprocessor strictly on training DataFrame.
    """
    preprocessor = create_preprocessor()
    preprocessor.fit(df_train[ALL_FEATURE_COLUMNS])
    return preprocessor
