"""
Feature engineering transformations for User-Food suitability pairing.
Computes non-linear nutritional interactions, satiety indices, and goal alignment metrics.
"""
from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_interaction_features(row: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes domain-grounded nutritional interactions between user metabolic targets and food attributes.
    """
    food_cal = max(1.0, float(row.get("food_calories_serving", 1.0)))
    food_p = float(row.get("food_protein_serving", 0.0))
    food_c = float(row.get("food_carbs_serving", 0.0))
    food_f = float(row.get("food_fat_serving", 0.0))
    food_fib = float(row.get("food_fiber_serving", 0.0))

    user_cal = max(1000.0, float(row.get("user_target_calories", 2000.0)))
    user_p = max(50.0, float(row.get("user_protein_target_g", 100.0)))
    user_goal = str(row.get("user_goal", "Maintenance")).lower()
    user_diet = str(row.get("user_diet_pattern", "Omnivore")).lower()

    # 1. Macro caloric densities (fraction of food energy from each macro)
    p_density = (food_p * 4.0) / food_cal
    c_density = (food_c * 4.0) / food_cal
    f_density = (food_f * 9.0) / food_cal

    # 2. Fiber density per 100 kcal
    fib_density = food_fib / (food_cal / 100.0)

    # 3. Share of daily target in a single serving
    cal_share = food_cal / user_cal
    p_share = food_p / user_p

    # 4. Satiety Index: favors high protein + fiber with low-to-moderate energy density
    satiety = (food_p * 2.5) + (food_fib * 3.0) - (food_cal * 0.02)
    satiety_idx = float(np.clip(satiety, -5.0, 30.0))

    # 5. Goal protein alignment:
    goal_p_align = 0.0
    if "muscle" in user_goal or "gain" in user_goal:
        goal_p_align = 2.0 if p_density >= 0.25 else -1.0
    elif "loss" in user_goal:
        goal_p_align = 1.5 if (p_density >= 0.20 and food_cal <= 250.0) else 0.0
    elif "endurance" in user_goal:
        goal_p_align = 1.5 if c_density >= 0.50 else 0.0

    # 6. Overall Macro Compatibility Score
    macro_compat = 1.0
    if "keto" in user_diet and c_density > 0.15:
        macro_compat = -3.0
    elif "keto" in user_diet and f_density >= 0.60:
        macro_compat = 2.5

    return {
        "protein_density": round(p_density, 4),
        "carb_density": round(c_density, 4),
        "fat_density": round(f_density, 4),
        "fiber_density": round(fib_density, 4),
        "calorie_share_of_target": round(cal_share, 4),
        "protein_share_of_target": round(p_share, 4),
        "goal_protein_alignment": round(goal_p_align, 2),
        "satiety_index": round(satiety_idx, 2),
        "macro_compatibility_score": round(macro_compat, 2),
    }


def build_feature_dataframe(records: list) -> pd.DataFrame:
    """
    Converts list of raw user-food pairs into a fully engineered DataFrame.
    """
    rows = []
    for r in records:
        inter = compute_interaction_features(r)
        merged = {**r, **inter}
        rows.append(merged)
    return pd.DataFrame(rows)
