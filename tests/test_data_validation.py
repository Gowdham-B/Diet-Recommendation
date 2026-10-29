"""
Tests for data schema validation, Atwater balance, and profile validation.
"""
import pytest
from pydantic import ValidationError
from src.data.validation import FoodItemSchema, UserProfileSchema, validate_atwater_balance


class TestDataValidation:
    def test_valid_food_schema(self):
        food = {
            "food_id": "test_apple",
            "name": "Fresh Apple",
            "category": "fruits",
            "serving_size_g": 182.0,
            "serving_unit": "1 medium (182g)",
            "calories_per_100g": 52.0,
            "protein_per_100g": 0.3,
            "carbs_per_100g": 13.8,
            "fat_per_100g": 0.2,
            "calories_per_serving": 95.0,
            "protein_per_serving": 0.5,
            "carbs_per_serving": 25.1,
            "fat_per_serving": 0.3,
            "is_vegan": True,
            "is_vegetarian": True,
            "is_pescatarian": True,
            "is_gluten_free": True,
            "is_dairy_free": True,
            "is_keto_friendly": False,
        }
        item = FoodItemSchema(**food)
        assert item.name == "Fresh Apple"
        assert item.serving_size_g == 182.0

    def test_invalid_food_serving_mismatch(self):
        # Calories per 100g is 50, but serving of 100g claimed to have 500 kcal
        food = {
            "food_id": "bad_food",
            "name": "Bad Food",
            "category": "fruits",
            "serving_size_g": 100.0,
            "serving_unit": "100g",
            "calories_per_100g": 50.0,
            "protein_per_100g": 1.0,
            "carbs_per_100g": 10.0,
            "fat_per_100g": 0.5,
            "calories_per_serving": 500.0,  # Severe mismatch
            "protein_per_serving": 1.0,
            "carbs_per_serving": 10.0,
            "fat_per_serving": 0.5,
        }
        with pytest.raises(ValidationError):
            FoodItemSchema(**food)

    def test_user_profile_validation_pass(self):
        profile = {
            "age": 30,
            "gender": "Male",
            "height_cm": 180.0,
            "weight_kg": 75.0,
        }
        u = UserProfileSchema(**profile)
        assert u.gender == "Male"
        assert u.age == 30

    def test_user_profile_invalid_gender(self):
        with pytest.raises(ValidationError):
            UserProfileSchema(age=30, gender="InvalidGender", height_cm=180.0, weight_kg=75.0)

    def test_user_profile_out_of_bound_stats(self):
        with pytest.raises(ValidationError):
            UserProfileSchema(age=5, gender="Male", height_cm=180.0, weight_kg=75.0)  # Age < 12
        with pytest.raises(ValidationError):
            UserProfileSchema(age=25, gender="Male", height_cm=300.0, weight_kg=75.0)  # Height > 250cm

    def test_atwater_physics(self):
        # 10g P (40 kcal) + 20g C (80 kcal) + 5g F (45 kcal) = 165 kcal
        res = validate_atwater_balance(protein_g=10.0, carb_g=20.0, fat_g=5.0, recorded_cal=165.0)
        assert res["theoretical_calories"] == 165.0
        assert res["is_physically_consistent"] is True

        # Severe violation: recorded 400 kcal when theoretical is 165 kcal
        bad = validate_atwater_balance(protein_g=10.0, carb_g=20.0, fat_g=5.0, recorded_cal=400.0)
        assert bad["is_physically_consistent"] is False
