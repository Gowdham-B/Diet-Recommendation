"""
Transparent explanation generator for meal plans and individual food recommendations.
"""
from typing import Dict, Any, List


def explain_food_selection(food: Dict[str, Any], goal: str, dietary_pattern: str) -> str:
    """
    Generates a personalized, clear justification for selecting this food item.
    """
    name = food.get("name", "Food")
    prot = food.get("protein_g", food.get("protein_per_serving", 0.0))
    fiber = food.get("fiber_g", food.get("fiber_per_serving", 0.0))
    fat = food.get("fat_g", food.get("fat_per_serving", 0.0))
    carbs = food.get("carbs_g", food.get("carbs_per_serving", 0.0))
    cal = food.get("calories", food.get("calories_per_serving", 0.0))

    reasons = []

    if prot >= 15.0:
        reasons.append(f"Provides {prot:.1f}g of high-quality protein to support muscle repair and satiety.")
    elif prot >= 7.0:
        reasons.append(f"Supplies moderate protein ({prot:.1f}g).")

    if fiber >= 3.0:
        reasons.append(f"Rich in dietary fiber ({fiber:.1f}g) promoting gut health and steady glycemic response.")

    if "loss" in goal.lower() and cal <= 120.0 and (prot >= 5.0 or fiber >= 2.0):
        reasons.append("High satiety per calorie, ideal for weight loss.")
    elif "gain" in goal.lower() and (prot >= 15.0 or cal >= 200.0):
        reasons.append("Nutrient-dense building block supporting clean caloric surplus.")
    elif "keto" in dietary_pattern.lower() and fat >= 10.0 and carbs <= 5.0:
        reasons.append("Keto-compliant high-healthy-fat profile with negligible net carbs.")

    if not reasons:
        reasons.append(f"Provides clean micronutrients and balanced energy ({cal:.0f} kcal).")

    return " ".join(reasons)


def generate_plan_explanation(
    user_goal: str,
    dietary_pattern: str,
    adherence: Dict[str, Any],
    allergens: List[str],
) -> Dict[str, Any]:
    """
    Summarizes the entire day's plan strategy, macro balance, and exclusions enforced.
    """
    cal_pct = adherence.get("calories_pct", 100.0)
    prot_pct = adherence.get("protein_pct", 100.0)
    splits = adherence.get("actual_macro_splits", {})

    strategy_text = (
        f"This meal plan was tailored for your '{user_goal}' goal under a '{dietary_pattern}' lifestyle. "
        f"It reaches {cal_pct:.1f}% of your daily energy target, with a macro distribution of "
        f"{splits.get('protein_pct', 0)}% protein, {splits.get('carbs_pct', 0)}% carbs, and {splits.get('fat_pct', 0)}% healthy fats. "
        f"Protein goal is fulfilled at {prot_pct:.1f}%."
    )

    allergen_text = (
        f"Strict exclusion of allergens: {', '.join(allergens)}."
        if allergens else "No allergen exclusions requested."
    )

    disclaimer = (
        "Educational & Wellness Notice: This system uses USDA standard reference data and Mifflin-St Jeor formulas. "
        "It provides nutritional estimates for planning and education, not clinical medical advice. "
        "Consult a registered dietitian or physician for individual medical medical conditions."
    )

    return {
        "strategy_summary": strategy_text,
        "allergen_status": allergen_text,
        "disclaimer": disclaimer,
    }
