"""
Nutrient aggregation and target adherence calculator.
Supports custom serving scales and meal plan recalculation.
"""
from typing import List, Dict, Any


def calculate_food_nutrition(food: Dict[str, Any], servings: float = 1.0) -> Dict[str, Any]:
    """
    Computes scaled nutritional values for a single food item.
    """
    s = max(0.0, float(servings))
    serving_g = food.get("serving_size_g", 100.0) * s
    cal = food.get("calories_per_serving", 0.0) * s
    prot = food.get("protein_per_serving", 0.0) * s
    carbs = food.get("carbs_per_serving", 0.0) * s
    fat = food.get("fat_per_serving", 0.0) * s
    fiber = food.get("fiber_per_serving", 0.0) * s
    sugars = food.get("sugars_per_serving", 0.0) * s
    sodium = food.get("sodium_mg_per_serving", 0.0) * s
    chol = food.get("cholesterol_mg_per_serving", 0.0) * s
    cost = food.get("estimated_cost_usd", 0.0) * s

    return {
        "food_id": food.get("food_id"),
        "name": food.get("name"),
        "servings": round(s, 2),
        "total_weight_g": round(serving_g, 1),
        "serving_unit": food.get("serving_unit"),
        "calories": round(cal, 1),
        "protein_g": round(prot, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "fiber_g": round(fiber, 1),
        "sugars_g": round(sugars, 1),
        "sodium_mg": round(sodium, 1),
        "cholesterol_mg": round(chol, 1),
        "estimated_cost_usd": round(cost, 2),
    }


def aggregate_meal_nutrition(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sums nutritional metrics across a collection of scaled food records.
    """
    totals = {
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
        "sugars_g": 0.0,
        "sodium_mg": 0.0,
        "cholesterol_mg": 0.0,
        "estimated_cost_usd": 0.0,
        "total_weight_g": 0.0,
        "item_count": len(items),
    }
    
    for item in items:
        # Check if already scaled or needs scaling
        cal = item.get("calories", item.get("calories_per_serving", 0.0))
        prot = item.get("protein_g", item.get("protein_per_serving", 0.0))
        carbs = item.get("carbs_g", item.get("carbs_per_serving", 0.0))
        fat = item.get("fat_g", item.get("fat_per_serving", 0.0))
        fiber = item.get("fiber_g", item.get("fiber_per_serving", 0.0))
        sugars = item.get("sugars_g", item.get("sugars_per_serving", 0.0))
        sodium = item.get("sodium_mg", item.get("sodium_mg_per_serving", 0.0))
        chol = item.get("cholesterol_mg", item.get("cholesterol_mg_per_serving", 0.0))
        cost = item.get("estimated_cost_usd", 0.0)
        weight = item.get("total_weight_g", item.get("serving_size_g", 0.0))

        totals["calories"] += cal
        totals["protein_g"] += prot
        totals["carbs_g"] += carbs
        totals["fat_g"] += fat
        totals["fiber_g"] += fiber
        totals["sugars_g"] += sugars
        totals["sodium_mg"] += sodium
        totals["cholesterol_mg"] += chol
        totals["estimated_cost_usd"] += cost
        totals["total_weight_g"] += weight

    return {k: round(v, 1) if k != "estimated_cost_usd" else round(v, 2) for k, v in totals.items()}


def calculate_target_adherence(actual_totals: Dict[str, Any], targets: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes percentage fulfillment of target calories and macros.
    """
    target_cal = targets.get("daily_calories", 2000.0)
    target_prot = targets.get("protein_g", 100.0)
    target_carb = targets.get("carbs_g", 250.0)
    target_fat = targets.get("fat_g", 65.0)
    target_fiber = targets.get("fiber_g", 28.0)

    act_cal = actual_totals.get("calories", 0.0)
    act_prot = actual_totals.get("protein_g", 0.0)
    act_carb = actual_totals.get("carbs_g", 0.0)
    act_fat = actual_totals.get("fat_g", 0.0)
    act_fiber = actual_totals.get("fiber_g", 0.0)

    # Actual calorie ratio distribution
    total_macro_cal = (act_prot * 4.0) + (act_carb * 4.0) + (act_fat * 9.0)
    if total_macro_cal > 0:
        actual_macro_splits = {
            "protein_pct": round(((act_prot * 4.0) / total_macro_cal) * 100.0, 1),
            "carbs_pct": round(((act_carb * 4.0) / total_macro_cal) * 100.0, 1),
            "fat_pct": round(((act_fat * 9.0) / total_macro_cal) * 100.0, 1),
        }
    else:
        actual_macro_splits = {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

    return {
        "calories_pct": round((act_cal / (target_cal + 1e-5)) * 100.0, 1),
        "protein_pct": round((act_prot / (target_prot + 1e-5)) * 100.0, 1),
        "carbs_pct": round((act_carb / (target_carb + 1e-5)) * 100.0, 1),
        "fat_pct": round((act_fat / (target_fat + 1e-5)) * 100.0, 1),
        "fiber_pct": round((act_fiber / (target_fiber + 1e-5)) * 100.0, 1),
        "actual_macro_splits": actual_macro_splits,
        "sodium_warning": actual_totals.get("sodium_mg", 0) > targets.get("max_sodium_mg", 2300),
        "cholesterol_warning": actual_totals.get("cholesterol_mg", 0) > targets.get("max_cholesterol_mg", 300),
    }
