"""
Profile service managing user profiles, physiological metrics, dietary target calculations,
and persistent database synchronization.
"""
from typing import Dict, Any, Optional
import json
from src.data.validation import UserProfileSchema
from src.nutrition.bmi import compute_bmi, classify_bmi
from src.nutrition.energy_requirements import compute_bmr_mifflin, compute_bmr_harris_benedict, compute_tdee, personalize_calories
from src.nutrition.targets import calculate_macro_targets
from src.database.connection import get_db_context
from src.database.repositories import ProfileRepository


class ProfileService:
    """Handles profile creation, validation, metabolic calculation, and database persistence."""

    @staticmethod
    def get_default_profile() -> Dict[str, Any]:
        """Provides a sensible initial default profile."""
        return {
            "age": 28,
            "gender": "Male",
            "height_cm": 178.0,
            "weight_kg": 75.0,
            "activity_level": "Moderate (moderate exercise 3-5 days/week)",
            "goal": "Maintenance",
            "dietary_pattern": "Omnivore (No restrictions)",
            "allergens": [],
            "disliked_foods": [],
            "target_calorie_override": None,
        }

    @classmethod
    def calculate_profile_metrics(cls, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates profile via Pydantic and computes complete physiological metrics.
        """
        validated = UserProfileSchema(**profile_data)

        # BMI
        bmi = compute_bmi(validated.weight_kg, validated.height_cm)
        bmi_info = classify_bmi(bmi, validated.height_cm)

        # BMR (Mifflin & Harris-Benedict comparison)
        bmr_mifflin = compute_bmr_mifflin(
            validated.weight_kg, validated.height_cm, validated.age, validated.gender
        )
        bmr_hb = compute_bmr_harris_benedict(
            validated.weight_kg, validated.height_cm, validated.age, validated.gender
        )

        # TDEE
        tdee = compute_tdee(bmr_mifflin, validated.activity_level)

        # Personalized Calorie Target
        if validated.target_calorie_override:
            cal_info = {
                "raw_tdee": tdee,
                "goal_multiplier": round(validated.target_calorie_override / tdee, 2),
                "unclamped_target_calories": validated.target_calorie_override,
                "target_calories": validated.target_calorie_override,
                "was_safety_clamped": False,
                "safety_floor_kcal": 1500.0 if validated.gender == "Male" else 1200.0,
            }
        else:
            cal_info = personalize_calories(tdee, validated.goal, validated.gender)

        # Targets
        targets = calculate_macro_targets(
            daily_calories=cal_info["target_calories"],
            dietary_pattern=validated.dietary_pattern,
            goal=validated.goal,
            weight_kg=validated.weight_kg,
            activity_level=validated.activity_level,
        )

        return {
            "profile": validated.model_dump(),
            "bmi_info": bmi_info,
            "bmr_mifflin": bmr_mifflin,
            "bmr_harris_benedict": bmr_hb,
            "tdee": tdee,
            "calorie_info": cal_info,
            "targets": targets,
        }

    @classmethod
    def save_user_profile_and_preferences(cls, user_id: int, profile_dict: Dict[str, Any]) -> None:
        """Persists profile and dietary preferences to database."""
        with get_db_context() as session:
            # 1. Profile
            profile_data = {
                "age": profile_dict["age"],
                "gender": profile_dict["gender"],
                "height_cm": profile_dict["height_cm"],
                "weight_kg": profile_dict["weight_kg"],
                "activity_level": profile_dict["activity_level"],
                "goal": profile_dict["goal"],
                "target_calorie_override": profile_dict.get("target_calorie_override"),
            }
            ProfileRepository.upsert_profile(session, user_id, profile_data)

            # 2. Preferences
            pref_data = {
                "dietary_pattern": profile_dict.get("dietary_pattern", "Omnivore (No restrictions)"),
                "allergens": json.dumps(profile_dict.get("allergens", [])),
                "excluded_foods": json.dumps(profile_dict.get("disliked_foods", [])),
                "preferred_foods": "[]",
                "meals_per_day": 4,
            }
            ProfileRepository.upsert_preferences(session, user_id, pref_data)

    @classmethod
    def load_user_profile_and_preferences(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Loads saved profile and preferences from database for an authenticated user."""
        with get_db_context() as session:
            db_profile = ProfileRepository.get_profile(session, user_id)
            if not db_profile:
                return None

            db_pref = ProfileRepository.get_preferences(session, user_id)

            allergens = []
            excluded = []
            diet_pattern = "Omnivore (No restrictions)"

            if db_pref:
                diet_pattern = db_pref.dietary_pattern
                try:
                    allergens = json.loads(db_pref.allergens) if db_pref.allergens else []
                except Exception:
                    allergens = [a.strip() for a in db_pref.allergens.split(",") if a.strip()]
                try:
                    excluded = json.loads(db_pref.excluded_foods) if db_pref.excluded_foods else []
                except Exception:
                    excluded = []

            return {
                "age": db_profile.age,
                "gender": db_profile.gender,
                "height_cm": db_profile.height_cm,
                "weight_kg": db_profile.weight_kg,
                "activity_level": db_profile.activity_level,
                "goal": db_profile.goal,
                "target_calorie_override": db_profile.target_calorie_override,
                "dietary_pattern": diet_pattern,
                "allergens": allergens,
                "disliked_foods": excluded,
            }
