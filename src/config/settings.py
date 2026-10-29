"""
Configuration settings for the Diet Recommendation System.
"""
from pathlib import Path
from typing import Dict, List

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REFERENCE_DATA_DIR = DATA_DIR / "reference"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
REPORTS_DIR = BASE_DIR / "reports"

# Ensure directories exist
for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, REFERENCE_DATA_DIR, ARTIFACTS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class NutritionConstants:
    """Nutritional standards, dietary reference intakes (DRIs), and clinical bounds."""
    # Minimum safe daily calorie floors (kcal)
    MIN_CALORIES_FEMALE: float = 1200.0
    MIN_CALORIES_MALE: float = 1500.0
    MAX_CALORIES_SAFE: float = 5000.0

    # Caloric density (kcal/g)
    CALORIES_PER_GRAM_PROTEIN: float = 4.0
    CALORIES_PER_GRAM_CARB: float = 4.0
    CALORIES_PER_GRAM_FAT: float = 9.0
    CALORIES_PER_GRAM_ALCOHOL: float = 7.0

    # Macro ratio defaults by diet archetype (fraction of total daily calories)
    DIET_MACRO_RATIOS: Dict[str, Dict[str, float]] = {
        "Balanced": {"protein": 0.20, "carbs": 0.50, "fat": 0.30},
        "High-Protein": {"protein": 0.35, "carbs": 0.40, "fat": 0.25},
        "Keto": {"protein": 0.20, "carbs": 0.05, "fat": 0.75},
        "Low-Carb": {"protein": 0.25, "carbs": 0.25, "fat": 0.50},
        "High-Carb (Endurance)": {"protein": 0.15, "carbs": 0.65, "fat": 0.20},
        "Mediterranean": {"protein": 0.20, "carbs": 0.45, "fat": 0.35},
    }

    # Goal adjustments to TDEE (multiplier)
    GOAL_CALORIE_ADJUSTMENTS: Dict[str, float] = {
        "Weight Loss (Aggressive -20%)": 0.80,
        "Weight Loss (Moderate -15%)": 0.85,
        "Weight Loss (Mild -10%)": 0.90,
        "Maintenance": 1.00,
        "Muscle Gain (Mild +10%)": 1.10,
        "Muscle Gain (Moderate +15%)": 1.15,
        "Endurance Training (+10%)": 1.10,
    }

    # Physical Activity Level (PAL) Multipliers
    ACTIVITY_FACTORS: Dict[str, float] = {
        "Sedentary (desk job, minimal movement)": 1.20,
        "Light (light exercise 1-3 days/week)": 1.375,
        "Moderate (moderate exercise 3-5 days/week)": 1.55,
        "Active (hard exercise 6-7 days/week)": 1.725,
        "Very Active (intense training/manual labor)": 1.90,
    }

    # Recommended daily limits / guidelines
    DEFAULT_MAX_SODIUM_MG: float = 2300.0  # AHA / USDA guideline
    DEFAULT_MAX_CHOLESTEROL_MG: float = 300.0
    DEFAULT_MIN_FIBER_G: float = 28.0
    DEFAULT_WATER_ML_PER_KG: float = 35.0  # Baseline ml water per kg body weight


# Supported dietary patterns
SUPPORTED_DIETARY_PATTERNS: List[str] = [
    "Omnivore (No restrictions)",
    "Vegetarian",
    "Vegan",
    "Pescatarian",
    "Keto / Low-Carb",
    "Gluten-Free",
    "Dairy-Free",
]

# Supported allergen tags
SUPPORTED_ALLERGENS: List[str] = [
    "Dairy",
    "Eggs",
    "Gluten",
    "Nuts / Peanuts",
    "Fish / Shellfish",
    "Soy",
]

# Meal slot allocation targets (fraction of daily calories)
MEAL_CALORIE_DISTRIBUTION: Dict[str, float] = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.30,
    "snack": 0.10,
}
