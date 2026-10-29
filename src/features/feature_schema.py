"""
Feature schema and column specifications for NutriPlan AI machine learning models.
"""
from typing import List

# Numerical features directly from user and food profiles
NUMERICAL_FEATURES: List[str] = [
    "user_age",
    "user_bmi",
    "user_tdee",
    "user_target_calories",
    "user_protein_target_g",
    "user_carb_target_g",
    "user_fat_target_g",
    "food_calories_serving",
    "food_protein_serving",
    "food_carbs_serving",
    "food_fat_serving",
    "food_fiber_serving",
    "food_sodium_serving",
]

# Engineered interaction and context features
INTERACTION_FEATURES: List[str] = [
    "protein_density",
    "carb_density",
    "fat_density",
    "fiber_density",
    "calorie_share_of_target",
    "protein_share_of_target",
    "goal_protein_alignment",
    "satiety_index",
    "macro_compatibility_score",
]

# Categorical features requiring encoding
CATEGORICAL_FEATURES: List[str] = [
    "user_goal",
    "user_diet_pattern",
    "food_category",
]

ALL_FEATURE_COLUMNS: List[str] = NUMERICAL_FEATURES + INTERACTION_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN: str = "is_suitable"
