"""
Unit tests for nutrition calculations: BMI, BMR, TDEE, macro targets, and clinical floors.
"""
import pytest
from src.nutrition.bmi import compute_bmi, classify_bmi, get_healthy_weight_range
from src.nutrition.energy_requirements import (
    compute_bmr_mifflin,
    compute_bmr_harris_benedict,
    activity_factor,
    compute_tdee,
    personalize_calories,
)
from src.nutrition.targets import calculate_macro_targets
from src.nutrition.nutrient_calculator import (
    calculate_food_nutrition,
    aggregate_meal_nutrition,
    calculate_target_adherence,
)


class TestBMICalculator:
    def test_compute_bmi_standard(self):
        # 70 kg, 175 cm -> 70 / (1.75^2) = 22.86
        bmi = compute_bmi(weight_kg=70.0, height_cm=175.0)
        assert pytest.approx(bmi, 0.01) == 22.86

    def test_bmi_invalid_inputs(self):
        with pytest.raises(ValueError):
            compute_bmi(weight_kg=-70.0, height_cm=175.0)
        with pytest.raises(ValueError):
            compute_bmi(weight_kg=70.0, height_cm=0.0)

    def test_classify_bmi_categories(self):
        # Underweight (< 18.5)
        res_under = classify_bmi(17.5, height_cm=170.0)
        assert res_under["category"] == "Underweight"

        # Normal (18.5 - 24.9)
        res_normal = classify_bmi(22.0, height_cm=170.0)
        assert res_normal["category"] == "Normal Weight"

        # Overweight (25.0 - 29.9)
        res_over = classify_bmi(27.5, height_cm=170.0)
        assert res_over["category"] == "Overweight"

        # Obese (>= 30.0)
        res_obese = classify_bmi(32.0, height_cm=170.0)
        assert "Obesity" in res_obese["category"]


class TestEnergyExpenditure:
    def test_mifflin_men_and_women(self):
        # Men: 10*80 + 6.25*180 - 5*25 + 5 = 800 + 1125 - 125 + 5 = 1805
        bmr_m = compute_bmr_mifflin(weight_kg=80.0, height_cm=180.0, age=25, gender="Male")
        assert bmr_m == 1805.0

        # Women: 10*60 + 6.25*165 - 5*30 - 161 = 600 + 1031.25 - 150 - 161 = 1320.25 -> 1320.2 or 1320.3
        bmr_f = compute_bmr_mifflin(weight_kg=60.0, height_cm=165.0, age=30, gender="Female")
        assert pytest.approx(bmr_f, 0.2) == 1320.2

    def test_activity_multipliers(self):
        assert activity_factor("Sedentary") == 1.20
        assert activity_factor("Light") == 1.375
        assert activity_factor("Moderate") == 1.55
        assert activity_factor("Active") == 1.725
        assert activity_factor("Very Active") == 1.90

    def test_tdee_calculation(self):
        bmr = 1800.0
        tdee = compute_tdee(bmr, "Moderate")
        assert tdee == 1800.0 * 1.55

    def test_clinical_safety_floor_enforcement(self):
        # Sedentary petite female: TDEE might be ~1300. An aggressive -20% deficit gives 1040 kcal.
        # Clinical floor should clamp to 1200 kcal.
        tdee = 1300.0
        res = personalize_calories(tdee, "Weight Loss (Aggressive -20%)", gender="Female")
        assert res["target_calories"] == 1200.0
        assert res["was_safety_clamped"] is True

        # Male floor should clamp to 1500 kcal
        res_m = personalize_calories(1500.0, "Weight Loss (Moderate -15%)", gender="Male")
        assert res_m["target_calories"] == 1500.0
        assert res_m["was_safety_clamped"] is True


class TestMacroTargets:
    def test_balanced_macro_split(self):
        targets = calculate_macro_targets(
            daily_calories=2000.0,
            dietary_pattern="Balanced",
            goal="Maintenance",
            weight_kg=70.0,
        )
        # 20% P = 400 kcal / 4 = 100g
        # 50% C = 1000 kcal / 4 = 250g
        # 30% F = 600 kcal / 9 = 66.7g
        assert pytest.approx(targets["protein_g"], 0.5) == 100.0
        assert pytest.approx(targets["carbs_g"], 0.5) == 250.0
        assert pytest.approx(targets["fat_g"], 0.5) == 66.7
        assert targets["water_target_ml"] >= 70.0 * 35.0

    def test_nutrient_aggregation(self):
        items = [
            {"calories": 200.0, "protein_g": 20.0, "carbs_g": 20.0, "fat_g": 5.0, "fiber_g": 3.0, "sodium_mg": 100.0, "cholesterol_mg": 10.0, "estimated_cost_usd": 1.5},
            {"calories": 300.0, "protein_g": 30.0, "carbs_g": 10.0, "fat_g": 10.0, "fiber_g": 2.0, "sodium_mg": 200.0, "cholesterol_mg": 20.0, "estimated_cost_usd": 2.5},
        ]
        totals = aggregate_meal_nutrition(items)
        assert totals["calories"] == 500.0
        assert totals["protein_g"] == 50.0
        assert totals["carbs_g"] == 30.0
        assert totals["estimated_cost_usd"] == 4.0
