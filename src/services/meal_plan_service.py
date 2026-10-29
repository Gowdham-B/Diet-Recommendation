"""
Meal plan service coordinating ML recommendation generation, database persistence,
serving size modifications, and food substitutions.
"""
from typing import Dict, Any, List, Optional
from src.data.food_repository import FoodRepository
from src.recommendation.generation import MLRecommendationPipeline
from src.nutrition.nutrient_calculator import calculate_food_nutrition, aggregate_meal_nutrition, calculate_target_adherence
from src.recommendation.explanations import explain_food_selection, generate_plan_explanation
from src.database.connection import get_db_context
from src.database.repositories import MealPlanRepository


class MealPlanService:
    """Manages meal plan generation, DB persistence, and interactive modifications."""

    def __init__(self, food_repository: Optional[FoodRepository] = None):
        self.repo = food_repository or FoodRepository()
        self.pipeline = MLRecommendationPipeline(self.repo)

    def generate_and_save_plan(
        self,
        user_id: int,
        user_profile: Dict[str, Any],
        user_targets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Runs ML recommendation pipeline and persists the resulting plan to the database.
        """
        plan_result = self.pipeline.generate_personalized_plan(user_profile, user_targets)
        if not plan_result.get("success"):
            return plan_result

        meals = plan_result["meals"]
        totals = plan_result["daily_totals"]

        # Persist to database
        with get_db_context() as session:
            db_plan = MealPlanRepository.save_plan(
                session=session,
                user_id=user_id,
                target_calories=user_targets["daily_calories"],
                target_protein=user_targets["protein_g"],
                target_carbs=user_targets["carbs_g"],
                target_fat=user_targets["fat_g"],
                total_calories=totals["calories"],
                total_protein=totals["protein_g"],
                total_carbs=totals["carbs_g"],
                total_fat=totals["fat_g"],
                meals_dict=meals,
                model_version=plan_result.get("model_version", "Ensemble v1.0"),
                ensemble_config=plan_result.get("ensemble_config", "Soft Voting (RF + HistGB + MLP + KNN)"),
            )
            plan_result["plan_id"] = db_plan.id

        return plan_result

    def load_active_plan(self, user_id: int, user_targets: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieves user's currently active saved plan from the database."""
        with get_db_context() as session:
            db_plan = MealPlanRepository.get_active_plan(session, user_id)
            if not db_plan:
                return None

            meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
            for it in db_plan.items:
                item_dict = {
                    "food_id": it.food_id,
                    "name": it.food_name,
                    "meal_slot": it.meal_slot,
                    "servings": it.servings,
                    "total_weight_g": it.total_weight_g,
                    "serving_unit": it.serving_unit,
                    "calories": it.calories,
                    "protein_g": it.protein_g,
                    "carbs_g": it.carbs_g,
                    "fat_g": it.fat_g,
                    "fiber_g": it.fiber_g,
                    "sodium_mg": it.sodium_mg,
                    "estimated_cost_usd": it.estimated_cost_usd,
                    "predicted_suitability_score": it.predicted_suitability_score,
                    "rationale": it.rationale,
                }
                meals.setdefault(it.meal_slot, []).append(item_dict)

            # Re-aggregate
            all_day_items = []
            meal_summaries = {}
            for slot, items in meals.items():
                meal_summaries[slot] = aggregate_meal_nutrition(items)
                all_day_items.extend(items)

            daily_totals = aggregate_meal_nutrition(all_day_items)
            adherence = calculate_target_adherence(daily_totals, user_targets)

            return {
                "success": True,
                "plan_id": db_plan.id,
                "model_version": db_plan.model_version,
                "ensemble_config": db_plan.ensemble_config,
                "created_at": db_plan.created_at,
                "meals": meals,
                "meal_summaries": meal_summaries,
                "daily_totals": daily_totals,
                "adherence": adherence,
            }

    def update_serving_quantity(
        self,
        current_meals: Dict[str, List[Dict[str, Any]]],
        meal_slot: str,
        food_id: str,
        new_servings: float,
        targets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Updates serving multiplier on food item and dynamically recalculates slot and daily totals."""
        updated_meals = {k: list(v) for k, v in current_meals.items()}
        if meal_slot not in updated_meals:
            return {"meals": current_meals}

        new_slot_items = []
        for item in updated_meals[meal_slot]:
            if item["food_id"] == food_id:
                raw_food = self.repo.get_by_id(food_id)
                if raw_food:
                    scaled = calculate_food_nutrition(raw_food, servings=new_servings)
                    scaled["predicted_suitability_score"] = item.get("predicted_suitability_score", 0.9)
                    scaled["rationale"] = item.get("rationale", "")
                    new_slot_items.append(scaled)
                else:
                    new_slot_items.append(item)
            else:
                new_slot_items.append(item)

        updated_meals[meal_slot] = new_slot_items

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
        """Substitutes an existing food item with another eligible food item and recalculates."""
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
                scaled["predicted_suitability_score"] = 0.92  # High match
                scaled["rationale"] = explain_food_selection(scaled, goal, dietary_pattern)
                new_slot_items.append(scaled)
            else:
                new_slot_items.append(item)

        updated_meals[meal_slot] = new_slot_items

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
