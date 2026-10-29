"""
End-to-end Machine Learning-driven recommendation generation pipeline.
Ranks candidate foods using the trained ML ensemble, enforces hard safety constraints,
and constructs balanced 4-meal daily plans with portion scaling.
"""
from typing import Dict, Any, List, Optional
from src.data.food_repository import FoodRepository
from src.recommendation.eligibility import filter_eligible_foods
from src.models.inference import FoodSuitabilityInference
from src.nutrition.nutrient_calculator import calculate_food_nutrition, aggregate_meal_nutrition, calculate_target_adherence
from src.recommendation.explanations import explain_food_selection, generate_plan_explanation


class MLRecommendationPipeline:
    """Orchestrates ML inference scoring, safety filtering, and daily meal allocation."""

    def __init__(self, food_repository: Optional[FoodRepository] = None, model_type: str = "ensemble_voting"):
        self.repo = food_repository or FoodRepository()
        self.ml_inference = FoodSuitabilityInference(model_type=model_type)
        self.model_type = model_type

    def generate_personalized_plan(
        self,
        user_profile: Dict[str, Any],
        user_targets: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes the 9-step ML recommendation pipeline.
        """
        target_calories = user_targets["daily_calories"]

        # 1. Hard Eligibility Filtering (Allergens & Dietary Exclusions)
        all_foods = self.repo.get_all()
        eligible_foods = filter_eligible_foods(
            all_foods=all_foods,
            dietary_pattern=user_profile.get("dietary_pattern", "Omnivore (No restrictions)"),
            allergens=user_profile.get("allergens", []),
            disliked_food_ids=user_profile.get("disliked_foods", []),
        )

        if len(eligible_foods) < 4:
            return {
                "success": False,
                "error": "No foods in database match your dietary restrictions and allergen exclusions. Please relax some filters.",
                "meals": {},
            }

        # 2. Machine Learning Suitability Scoring & Ranking
        scored_foods = self.ml_inference.score_foods_for_user(
            user_profile=user_profile,
            user_targets=user_targets,
            candidate_foods=eligible_foods,
        )

        # 3. Meal Slot Candidate Grouping
        slot_shares = {
            "breakfast": (0.25, 2),
            "lunch": (0.35, 3),
            "dinner": (0.30, 3),
            "snack": (0.10, 1),
        }

        meals = {"breakfast": [], "lunch": [], "dinner": [], "snack": []}
        used_fids = set()

        for slot, (share, target_count) in slot_shares.items():
            slot_cal_target = target_calories * share
            
            # Find eligible foods suitable for this meal slot
            slot_cands = [
                f for f in scored_foods
                if slot in [m.lower() for m in f.get("suitable_meals_list", [])]
            ]
            if len(slot_cands) < target_count:
                slot_cands = scored_foods

            # Pick top-ranked by ML suitability score without duplicates across the day
            chosen = []
            for f in slot_cands:
                fid = f["food_id"]
                if fid in used_fids:
                    continue
                chosen.append(f)
                used_fids.add(fid)
                if len(chosen) >= target_count:
                    break

            if not chosen:
                chosen = slot_cands[:target_count]

            # 4. Portion Balancing to match slot target calories
            current_slot_cal = sum(f.get("calories_per_serving", 100.0) for f in chosen)
            scaling_factor = slot_cal_target / (current_slot_cal + 1e-5)
            # Clamp serving scale between 0.6x and 2.0x
            scaling_factor = max(0.6, min(2.0, scaling_factor))

            for f in chosen:
                scaled = calculate_food_nutrition(f, servings=round(scaling_factor, 2))
                scaled["predicted_suitability_score"] = f.get("predicted_suitability_score", 0.95)
                scaled["rationale"] = explain_food_selection(
                    food=scaled,
                    goal=user_profile["goal"],
                    dietary_pattern=user_profile["dietary_pattern"],
                )
                meals[slot].append(scaled)

        # 5. Aggregate daily totals & compute adherence
        all_day_items = []
        meal_summaries = {}
        for slot, items in meals.items():
            meal_summaries[slot] = aggregate_meal_nutrition(items)
            all_day_items.extend(items)

        daily_totals = aggregate_meal_nutrition(all_day_items)
        adherence = calculate_target_adherence(daily_totals, user_targets)

        # 6. Natural Language Summary
        plan_explanation = generate_plan_explanation(
            user_goal=user_profile["goal"],
            dietary_pattern=user_profile["dietary_pattern"],
            adherence=adherence,
            allergens=user_profile.get("allergens", []),
        )

        return {
            "success": True,
            "model_version": "Ensemble v1.0",
            "ensemble_config": "Soft Voting Ensemble (Random Forest + HistGB + MLP + KNN)",
            "meals": meals,
            "meal_summaries": meal_summaries,
            "daily_totals": daily_totals,
            "adherence": adherence,
            "explanation": plan_explanation,
        }
