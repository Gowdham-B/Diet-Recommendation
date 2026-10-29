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

__all__ = [
    "compute_bmi",
    "classify_bmi",
    "get_healthy_weight_range",
    "compute_bmr_mifflin",
    "compute_bmr_harris_benedict",
    "activity_factor",
    "compute_tdee",
    "personalize_calories",
    "calculate_macro_targets",
    "calculate_food_nutrition",
    "aggregate_meal_nutrition",
    "calculate_target_adherence",
]
