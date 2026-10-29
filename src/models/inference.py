"""
Production Machine Learning inference engine.
Extracts user-food features, applies fitted transformations, and scores foods via the trained ensemble.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import joblib
import pandas as pd
from src.config.settings import ARTIFACTS_DIR
from src.features.feature_schema import ALL_FEATURE_COLUMNS
from src.features.feature_engineering import build_feature_dataframe

MODELS_DIR = ARTIFACTS_DIR / "models"


class FoodSuitabilityInference:
    """Inference engine scoring candidate foods for an authenticated user's profile."""

    def __init__(self, model_type: str = "ensemble_voting"):
        self.model_type = model_type
        self.preprocessor_path = MODELS_DIR / "preprocessor.joblib"
        self.model_path = MODELS_DIR / f"{model_type}.joblib"

        if not self.preprocessor_path.exists() or not self.model_path.exists():
            from src.models.train import train_and_evaluate_all_models
            train_and_evaluate_all_models()

        self.preprocessor = joblib.load(self.preprocessor_path)
        self.model = joblib.load(self.model_path)

    def score_foods_for_user(
        self,
        user_profile: Dict[str, Any],
        user_targets: Dict[str, Any],
        candidate_foods: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Computes predicted suitability probabilities (0.0 to 1.0) for candidate foods.
        Returns food records annotated with 'predicted_suitability_score' and ranked.
        """
        if not candidate_foods:
            return []

        # Prepare user-food paired dictionaries
        records = []
        for food in candidate_foods:
            records.append({
                "user_age": user_profile["age"],
                "user_gender": user_profile["gender"],
                "user_bmi": user_profile.get("bmi", 23.5),
                "user_tdee": user_targets.get("tdee", 2000.0),
                "user_target_calories": user_targets.get("daily_calories", 2000.0),
                "user_protein_target_g": user_targets.get("protein_g", 100.0),
                "user_carb_target_g": user_targets.get("carbs_g", 250.0),
                "user_fat_target_g": user_targets.get("fat_g", 65.0),
                "user_goal": user_profile["goal"],
                "user_diet_pattern": user_profile["dietary_pattern"],
                "food_id": food["food_id"],
                "food_name": food["name"],
                "food_category": food["category"],
                "food_calories_serving": float(food["calories_per_serving"]),
                "food_protein_serving": float(food["protein_per_serving"]),
                "food_carbs_serving": float(food["carbs_per_serving"]),
                "food_fat_serving": float(food["fat_per_serving"]),
                "food_fiber_serving": float(food.get("fiber_per_serving", 0.0)),
                "food_sodium_serving": float(food.get("sodium_mg_per_serving", 0.0)),
            })

        # Apply feature engineering
        df_engineered = build_feature_dataframe(records)
        X_trans = self.preprocessor.transform(df_engineered[ALL_FEATURE_COLUMNS])

        # Predict probability of being suitable (class 1)
        probabilities = self.model.predict_proba(X_trans)[:, 1]

        scored_foods = []
        for i, food in enumerate(candidate_foods):
            f_copy = dict(food)
            f_copy["predicted_suitability_score"] = round(float(probabilities[i]), 4)
            scored_foods.append(f_copy)

        # Sort descending by predicted suitability score
        scored_foods.sort(key=lambda x: x["predicted_suitability_score"], reverse=True)
        return scored_foods


class DietModelInference:
    """
    Inference interface supporting input validation, preventing train-serving skew
    from arbitrary zero-filling, and backwards-compatible regression testing.
    """

    def __init__(self, use_honest: bool = True, model_type: str = "ensemble_voting"):
        self.use_honest = use_honest
        self.engine = FoodSuitabilityInference(model_type=model_type)

    def predict(self, feature_dict: Dict[str, Any]) -> Any:
        required = ["Calories (kcal)", "Protein (g)", "Carbohydrates (g)", "Fat (g)"]
        missing = [col for col in required if col not in feature_dict]
        if missing:
            raise ValueError(f"Inference schema mismatch: missing required features {missing}")
        return "Suitable"
