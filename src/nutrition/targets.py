"""
Nutrient and macronutrient target calculation based on dietary pattern, body weight, and clinical guidelines.
"""
from typing import Dict, Any
from src.config.settings import NutritionConstants, MEAL_CALORIE_DISTRIBUTION


def calculate_macro_targets(
    daily_calories: float,
    dietary_pattern: str,
    goal: str,
    weight_kg: float,
    activity_level: str = "Moderate",
) -> Dict[str, Any]:
    """
    Calculates target calories, macronutrients (g), micronutrients, and hydration.
    """
    clean_diet = dietary_pattern.strip()
    ratios = NutritionConstants.DIET_MACRO_RATIOS.get("Balanced")
    
    # Match appropriate macro distribution archetype
    if "keto" in clean_diet.lower():
        ratios = NutritionConstants.DIET_MACRO_RATIOS["Keto"]
    elif "low-carb" in clean_diet.lower():
        ratios = NutritionConstants.DIET_MACRO_RATIOS["Low-Carb"]
    elif "endurance" in goal.lower() or "high-carb" in clean_diet.lower():
        ratios = NutritionConstants.DIET_MACRO_RATIOS["High-Carb (Endurance)"]
    elif "muscle" in goal.lower() or "high-protein" in clean_diet.lower():
        ratios = NutritionConstants.DIET_MACRO_RATIOS["High-Protein"]
    elif "mediterranean" in clean_diet.lower():
        ratios = NutritionConstants.DIET_MACRO_RATIOS["Mediterranean"]

    # Calculate gram targets from caloric fractions
    protein_cal = daily_calories * ratios["protein"]
    carbs_cal = daily_calories * ratios["carbs"]
    fat_cal = daily_calories * ratios["fat"]

    protein_g = protein_cal / NutritionConstants.CALORIES_PER_GRAM_PROTEIN
    carbs_g = carbs_cal / NutritionConstants.CALORIES_PER_GRAM_CARB
    fat_g = fat_cal / NutritionConstants.CALORIES_PER_GRAM_FAT

    # Fiber guideline (14g per 1000 kcal, minimum 25g)
    fiber_g = max(NutritionConstants.DEFAULT_MIN_FIBER_G, round((daily_calories / 1000.0) * 14.0, 1))

    # Water requirement: ~35 ml/kg baseline + activity bonus
    water_ml = weight_kg * NutritionConstants.DEFAULT_WATER_ML_PER_KG
    if "active" in activity_level.lower():
        water_ml += 500.0
    if "very active" in activity_level.lower():
        water_ml += 1000.0
    water_cups = round(water_ml / 240.0, 1)

    # Meal distribution breakdowns
    meal_targets = {}
    for meal, pct in MEAL_CALORIE_DISTRIBUTION.items():
        meal_targets[meal] = {
            "calories": round(daily_calories * pct, 1),
            "protein_g": round(protein_g * pct, 1),
            "carbs_g": round(carbs_g * pct, 1),
            "fat_g": round(fat_g * pct, 1),
        }

    return {
        "daily_calories": round(daily_calories, 1),
        "macro_ratios": ratios,
        "macro_split": {
            "protein_pct": int(round(ratios["protein"] * 100)),
            "carbs_pct": int(round(ratios["carbs"] * 100)),
            "fat_pct": int(round(ratios["fat"] * 100)),
        },
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_g, 1),
        "fat_g": round(fat_g, 1),
        "fiber_g": round(fiber_g, 1),
        "max_sodium_mg": NutritionConstants.DEFAULT_MAX_SODIUM_MG,
        "sodium_mg_max": NutritionConstants.DEFAULT_MAX_SODIUM_MG,
        "max_cholesterol_mg": NutritionConstants.DEFAULT_MAX_CHOLESTEROL_MG,
        "water_target_ml": round(water_ml, 0),
        "water_target_cups": water_cups,
        "meal_targets": meal_targets,
    }

