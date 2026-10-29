"""
Food ranking and scoring based on nutrient density, category balancing, and dietary goals.
"""
from typing import Dict, Any, List


def calculate_nutrient_density_score(food: Dict[str, Any]) -> float:
    """
    Computes a balanced nutrient density index based on protein, fiber, and micronutrients.
    """
    cal = food.get("calories_per_serving", 1.0)
    if cal <= 5.0:  # e.g., water, black coffee, tea
        return 0.5
    
    protein = food.get("protein_per_serving", 0.0)
    fiber = food.get("fiber_per_serving", 0.0)
    sugar = food.get("sugars_per_serving", 0.0)
    sodium = food.get("sodium_mg_per_serving", 0.0)

    # Moderate density calculation
    scale = 100.0 / cal
    protein_density = min(15.0, protein * scale)
    fiber_density = min(10.0, fiber * scale)

    # Penalties
    sugar_penalty = max(0.0, (sugar * scale) - 15.0) * 0.1
    sodium_penalty = max(0.0, (sodium * scale) - 400.0) * 0.003

    score = (protein_density * 0.3) + (fiber_density * 0.4) + (cal * 0.01) - sugar_penalty - sodium_penalty
    return round(max(0.1, score), 2)


def rank_foods_for_meal(
    candidate_foods: List[Dict[str, Any]],
    target_macro_ratios: Dict[str, float],
    goal: str = "Maintenance",
) -> List[Dict[str, Any]]:
    """
    Ranks eligible foods by their nutritional fit for the user's specific targets.
    """
    ranked = []
    target_p = target_macro_ratios.get("protein", 0.20)
    
    for food in candidate_foods:
        density = calculate_nutrient_density_score(food)
        cal = food.get("calories_per_serving", 1.0)
        prot = food.get("protein_per_serving", 0.0)
        protein_ratio = (prot * 4.0) / (cal + 1e-5)

        alignment_score = density
        # Goal-specific bonuses
        if "muscle" in goal.lower() or target_p >= 0.25:
            if protein_ratio >= 0.25:
                alignment_score += 2.0
        elif "loss" in goal.lower():
            if food.get("fiber_per_serving", 0.0) >= 3.0:
                alignment_score += 1.5

        # Whole food / staple bonus to ensure substantive meal components
        cat = food.get("category", "").lower()
        if cat in ["meat", "grains", "dairy"]:
            alignment_score += 1.0

        item_copy = dict(food)
        item_copy["ranking_score"] = round(alignment_score, 2)
        ranked.append(item_copy)

    ranked.sort(key=lambda x: x["ranking_score"], reverse=True)
    return ranked


def get_balanced_meal_candidates(
    candidates: List[Dict[str, Any]],
    target_macros: Dict[str, float],
    goal: str = "Maintenance",
    max_items: int = 14,
) -> List[Dict[str, Any]]:
    """
    Ensures that the candidate pool for the optimizer contains diverse food categories
    (proteins, grains/starches, vegetables/fruits, and healthy fats).
    """
    ranked = rank_foods_for_meal(candidates, target_macros, goal)
    
    categories = {}
    for f in ranked:
        cat = f.get("category", "other")
        categories.setdefault(cat, []).append(f)

    # Pick top 2-3 from each category to ensure diversity
    balanced_pool = []
    for cat, items in categories.items():
        balanced_pool.extend(items[:3])

    # If still below max_items, fill with top remaining
    remaining = [f for f in ranked if f not in balanced_pool]
    balanced_pool.extend(remaining[: max(0, max_items - len(balanced_pool))])
    
    return balanced_pool
