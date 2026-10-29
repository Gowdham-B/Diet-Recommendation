"""
Unit tests for feature engineering and preprocessor pipelines.
Verifies transformation of raw user and food features into interaction features,
schema conformity, and ColumnTransformer integrity.
"""
import pytest
import pandas as pd
from src.features.feature_schema import ALL_FEATURE_COLUMNS, NUMERICAL_FEATURES, CATEGORICAL_FEATURES, INTERACTION_FEATURES
from src.features.feature_engineering import build_feature_dataframe
from src.features.preprocessing import create_preprocessor


class TestFeaturePreprocessing:
    def test_feature_engineering_creates_all_interactions(self):
        sample_records = [
            {
                "user_age": 28,
                "user_gender": "Male",
                "user_bmi": 23.5,
                "user_tdee": 2400.0,
                "user_target_calories": 2400.0,
                "user_protein_target_g": 150.0,
                "user_carb_target_g": 270.0,
                "user_fat_target_g": 80.0,
                "user_goal": "Maintenance",
                "user_diet_pattern": "Omnivore (No restrictions)",
                "food_id": "chicken_breast_100g",
                "food_name": "Chicken Breast, cooked",
                "food_category": "Poultry & Meat",
                "food_calories_serving": 165.0,
                "food_protein_serving": 31.0,
                "food_carbs_serving": 0.0,
                "food_fat_serving": 3.6,
                "food_fiber_serving": 0.0,
                "food_sodium_serving": 74.0,
            }
        ]

        df = build_feature_dataframe(sample_records)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

        # Check interaction features exist
        for col in INTERACTION_FEATURES:
            assert col in df.columns, f"Missing engineered feature: {col}"

        # Verify specific non-linear interactions
        # protein_density = (31 * 4) / 165 = ~0.7515 (75.2% of calories from protein)
        assert round(df["protein_density"].iloc[0], 2) == 0.75
        # calorie_share_of_target = 165 / 2400 = ~0.0687
        assert round(df["calorie_share_of_target"].iloc[0], 3) == 0.069

    def test_column_transformer_fit_and_transform(self):
        sample_records = [
            {
                "user_age": 28,
                "user_gender": "Male",
                "user_bmi": 23.5,
                "user_tdee": 2400.0,
                "user_target_calories": 2400.0,
                "user_protein_target_g": 150.0,
                "user_carb_target_g": 270.0,
                "user_fat_target_g": 80.0,
                "user_goal": "Maintenance",
                "user_diet_pattern": "Omnivore (No restrictions)",
                "food_id": "chicken_breast",
                "food_name": "Chicken Breast",
                "food_category": "Poultry & Meat",
                "food_calories_serving": 165.0,
                "food_protein_serving": 31.0,
                "food_carbs_serving": 0.0,
                "food_fat_serving": 3.6,
                "food_fiber_serving": 0.0,
                "food_sodium_serving": 74.0,
            },
            {
                "user_age": 35,
                "user_gender": "Female",
                "user_bmi": 22.0,
                "user_tdee": 1800.0,
                "user_target_calories": 1500.0,
                "user_protein_target_g": 110.0,
                "user_carb_target_g": 150.0,
                "user_fat_target_g": 50.0,
                "user_goal": "Weight Loss (Moderate deficit, -20%)",
                "user_diet_pattern": "Vegetarian (Lacto-ovo: no meat/fish)",
                "food_id": "spinach",
                "food_name": "Spinach",
                "food_category": "Vegetables",
                "food_calories_serving": 23.0,
                "food_protein_serving": 2.9,
                "food_carbs_serving": 3.6,
                "food_fat_serving": 0.4,
                "food_fiber_serving": 2.2,
                "food_sodium_serving": 79.0,
            }
        ]

        df = build_feature_dataframe(sample_records)
        preprocessor = create_preprocessor()
        X_trans = preprocessor.fit_transform(df[ALL_FEATURE_COLUMNS])
        assert X_trans.shape[0] == 2
        assert X_trans.shape[1] > len(NUMERICAL_FEATURES)  # Includes one-hot encoded categories

