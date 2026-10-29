"""
Eligibility filtering for diet plans: strict allergen exclusions, dietary pattern validation,
and meal slot suitability.
"""
from typing import List, Dict, Any, Set


def filter_eligible_foods(
    all_foods: List[Dict[str, Any]],
    dietary_pattern: str = "Omnivore (No restrictions)",
    allergens: List[str] = None,
    disliked_food_ids: List[str] = None,
    meal_slot: str = None,
) -> List[Dict[str, Any]]:
    """
    Applies hard constraints to food candidates.
    A food is disqualified if it violates allergens, lifestyle restrictions, or dislikes.
    """
    allergens = allergens or []
    disliked_food_ids = disliked_food_ids or []
    
    # Lowercase clean sets
    allergen_set = {a.strip().lower() for a in allergens if a.strip()}
    dislike_set = {d.strip().lower() for d in disliked_food_ids if d.strip()}
    pattern_lower = dietary_pattern.lower()

    eligible = []
    for food in all_foods:
        fid = food.get("food_id", "").lower()
        fname = food.get("name", "").lower()
        if fid in dislike_set or fname in dislike_set or any(d in fname for d in dislike_set if len(d) >= 3):
            continue

        # Check allergens
        food_allergens = food.get("allergens_list", [])
        if not food_allergens and isinstance(food.get("allergens"), str):
            val = food["allergens"].strip()
            if val.lower() not in ["none", ""]:
                food_allergens = [x.strip() for x in val.split(",")]
        
        has_allergen_clash = any(a.lower() in allergen_set for a in food_allergens)
        if has_allergen_clash:
            continue

        # Check dietary patterns
        if "vegan" in pattern_lower and not food.get("is_vegan", False):
            continue
        if "vegetarian" in pattern_lower and not food.get("is_vegetarian", False):
            continue
        if "pescatarian" in pattern_lower and not food.get("is_pescatarian", False):
            continue
        if ("keto" in pattern_lower or "low-carb" in pattern_lower) and not food.get("is_keto_friendly", False):
            continue
        if "gluten-free" in pattern_lower and not food.get("is_gluten_free", True):
            continue
        if "dairy-free" in pattern_lower and not food.get("is_dairy_free", True):
            continue

        # Check meal slot suitability if requested
        if meal_slot:
            slot = meal_slot.strip().lower()
            meals = food.get("suitable_meals_list", [])
            if not meals and isinstance(food.get("suitable_meals"), str):
                meals = [m.strip().lower() for m in food["suitable_meals"].split(",")]
            if meals and slot not in meals:
                continue

        eligible.append(food)

    return eligible
