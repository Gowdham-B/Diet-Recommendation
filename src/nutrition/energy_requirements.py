"""
Energy expenditure calculations: BMR (Mifflin-St Jeor & Harris-Benedict), TDEE, and safe caloric targets.
"""
from typing import Dict, Any
from src.config.settings import NutritionConstants


def compute_bmr_mifflin(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Computes Basal Metabolic Rate using the Mifflin-St Jeor Equation.
    Men:   10 * W + 6.25 * H - 5 * A + 5
    Women: 10 * W + 6.25 * H - 5 * A - 161
    """
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        raise ValueError("Weight, height, and age must be strictly positive.")
    
    g = gender.strip().capitalize()
    base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
    bmr = base + 5.0 if g == "Male" else base - 161.0
    return round(bmr, 1)


def compute_bmr_harris_benedict(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Computes Basal Metabolic Rate using the revised Harris-Benedict Equation.
    Provided for comparative clinical validation.
    """
    g = gender.strip().capitalize()
    if g == "Male":
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
    return round(bmr, 1)


def activity_factor(level: str) -> float:
    """
    Maps activity description to standard Physical Activity Level (PAL) multiplier.
    """
    clean_level = str(level).strip().lower()
    for key, multiplier in NutritionConstants.ACTIVITY_FACTORS.items():
        if clean_level in key.lower() or key.lower().startswith(clean_level):
            return multiplier
    # Keyword fallbacks
    if "sedentary" in clean_level:
        return 1.20
    elif "light" in clean_level:
        return 1.375
    elif "active" in clean_level and "very" in clean_level:
        return 1.90
    elif "active" in clean_level:
        return 1.725
    return 1.55  # Default Moderate


def compute_tdee(bmr: float, activity_level: str) -> float:
    """
    Computes Total Daily Energy Expenditure (TDEE) = BMR * PAL.
    """
    pal = activity_factor(activity_level)
    return round(bmr * pal, 1)


def personalize_calories(tdee: float, goal: str, gender: str = "Male") -> Dict[str, Any]:
    """
    Adjusts TDEE based on user goal while enforcing clinical safety floors.
    """
    clean_goal = str(goal).strip().lower()
    multiplier = 1.00
    
    for key, mult in NutritionConstants.GOAL_CALORIE_ADJUSTMENTS.items():
        if clean_goal in key.lower():
            multiplier = mult
            break
            
    if multiplier == 1.00:
        if "loss" in clean_goal or "cut" in clean_goal:
            multiplier = 0.85
        elif "gain" in clean_goal or "bulk" in clean_goal:
            multiplier = 1.15
        elif "endurance" in clean_goal:
            multiplier = 1.10

    unclamped_calories = tdee * multiplier
    
    # Enforce minimum healthy calorie floor
    is_male = gender.strip().capitalize() == "Male"
    safety_floor = NutritionConstants.MIN_CALORIES_MALE if is_male else NutritionConstants.MIN_CALORIES_FEMALE
    
    was_clamped = False
    final_calories = unclamped_calories
    if final_calories < safety_floor:
        final_calories = safety_floor
        was_clamped = True

    return {
        "raw_tdee": tdee,
        "goal_multiplier": multiplier,
        "unclamped_target_calories": round(unclamped_calories, 1),
        "target_calories": round(final_calories, 1),
        "was_safety_clamped": was_clamped,
        "safety_floor_kcal": safety_floor,
    }
