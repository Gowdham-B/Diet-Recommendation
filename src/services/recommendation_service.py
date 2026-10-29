"""
Recommendation service coordinating food repositories, optimizer execution,
dynamic food substitution, serving adjustments, and real-time nutritional recalculation.
"""
from typing import Dict, Any, List, Optional
from src.data.food_repository import FoodRepository
from src.nutrition.nutrient_calculator import (
    calculate_food_nutrition,
    aggregate_meal_nutrition,
    calculate_target_adherence,
)
from src.recommendation.optimizer import MealPlanOptimizer
from src.recommendation.explanations import explain_food_selection, generate_plan_explanation


class RecommendationService:
    """Manages meal plan generation, real-time adjustments, and substitution logic."""

    def __init__(self, food_repository: Optional[FoodRepository] = None):
        self.repo = food_repository or FoodRepository()
        self.optimizer = MealPlanOptimizer(self.repo.get_all())

    def generate_daily_plan(self, profile_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates an end-to-end personalized meal plan with justifications and adherence.
        """
        profile = profile_metrics["profile"]
        targets = profile_metrics["targets"]
        target_calories = targets["daily_calories"]

        # Run optimizer
        optimization_result = self.optimizer.generate_plan(
            target_calories=target_calories,
            target_macros=targets,
            dietary_pattern=profile["dietary_pattern"],
            allergens=profile.get("allergens", []),
            disliked_food_ids=profile.get("disliked_foods", []),
            meal_targets=targets.get("meal_targets"),
        )

        if not optimization_result["success"]:
            return {
                "success": False,
                "error": optimization_result["error"],
                "meals": {},
                "adherence": {},
            }

        meals = optimization_result["meals"]

        # Annotate each food with an explanation
        for slot, items in meals.items():
            for item in items:
                # Add rationale
                item["rationale"] = explain_food_selection(
                    food=item,
                    goal=profile["goal"],
                    dietary_pattern=profile["dietary_pattern"]
                )

        # Aggregate daily totals and calculate adherence
        all_day_items = []
        meal_summaries = {}
        for slot, items in meals.items():
            meal_summaries[slot] = aggregate_meal_nutrition(items)
            all_day_items.extend(items)

        daily_totals = aggregate_meal_nutrition(all_day_items)
        adherence = calculate_target_adherence(daily_totals, targets)

        # Natural language plan explanation
        plan_explanation = generate_plan_explanation(
            user_goal=profile["goal"],
            dietary_pattern=profile["dietary_pattern"],
            adherence=adherence,
            allergens=profile.get("allergens", []),
        )

        return {
            "success": True,
            "method": optimization_result.get("method", "Optimization"),
            "meals": meals,
            "meal_summaries": meal_summaries,
            "daily_totals": daily_totals,
            "adherence": adherence,
            "explanation": plan_explanation,
            "diagnostics": optimization_result.get("diagnostics", {}),
        }

    def update_serving_quantity(
        self,
        current_meals: Dict[str, List[Dict[str, Any]]],
        meal_slot: str,
        food_id: str,
        new_servings: float,
        targets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Updates serving quantity for a specific food item and recalculates all totals.
        """
        updated_meals = {k: list(v) for k, v in current_meals.items()}
        if meal_slot not in updated_meals:
            return {"meals": current_meals}

        # Locate food in slot
        new_slot_items = []
        for item in updated_meals[meal_slot]:
            if item["food_id"] == food_id:
                raw_food = self.repo.get_by_id(food_id)
                if raw_food:
                    scaled = calculate_food_nutrition(raw_food, servings=new_servings)
                    scaled["rationale"] = item.get("rationale", "")
                    new_slot_items.append(scaled)
                else:
                    new_slot_items.append(item)
            else:
                new_slot_items.append(item)

        updated_meals[meal_slot] = new_slot_items

        # Recalculate totals
        all_day_items = []
        meal_summaries = {}
        for slot, items in updated_meals.items():
            meal_summaries[slot] = aggregate_meal_nutrition(items)
            all_day_items.extend(items)

        daily_totals = aggregate_meal_nutrition(all_day_items)
        adherence = calculate_target_adherence(daily_totals, targets)

        return {
            "meals": updated_meals,
            "meal_summaries": meal_summaries,
            "daily_totals": daily_totals,
            "adherence": adherence,
        }

    def substitute_food(
        self,
        current_meals: Dict[str, List[Dict[str, Any]]],
        meal_slot: str,
        old_food_id: str,
        new_food_id: str,
        targets: Dict[str, Any],
        goal: str = "Maintenance",
        dietary_pattern: str = "Omnivore (No restrictions)",
    ) -> Dict[str, Any]:
        """
        Replaces an existing food item with a new food item from the repository.
        """
        updated_meals = {k: list(v) for k, v in current_meals.items()}
        if meal_slot not in updated_meals:
            return {"meals": current_meals}

        new_raw_food = self.repo.get_by_id(new_food_id)
        if not new_raw_food:
            return {"meals": current_meals}

        new_slot_items = []
        for item in updated_meals[meal_slot]:
            if item["food_id"] == old_food_id:
                scaled = calculate_food_nutrition(new_raw_food, servings=1.0)
                scaled["rationale"] = explain_food_selection(scaled, goal, dietary_pattern)
                new_slot_items.append(scaled)
            else:
                new_slot_items.append(item)

        updated_meals[meal_slot] = new_slot_items

        # Recalculate totals
        all_day_items = []
        meal_summaries = {}
        for slot, items in updated_meals.items():
            meal_summaries[slot] = aggregate_meal_nutrition(items)
            all_day_items.extend(items)

        daily_totals = aggregate_meal_nutrition(all_day_items)
        adherence = calculate_target_adherence(daily_totals, targets)

        return {
            "meals": updated_meals,
            "meal_summaries": meal_summaries,
            "daily_totals": daily_totals,
            "adherence": adherence,
        }
