"""
Unit and integration tests for recommendation pipeline and SciPy HiGHS MILP optimizer.
"""
import pytest
from src.services.profile_service import ProfileService
from src.services.recommendation_service import RecommendationService


@pytest.fixture
def rec_service():
    return RecommendationService()


class TestRecommendationAndOptimizer:
    def test_default_plan_generation_success(self, rec_service):
        profile = ProfileService.get_default_profile()
        metrics = ProfileService.calculate_profile_metrics(profile)

        plan = rec_service.generate_daily_plan(metrics)
        assert plan["success"] is True
        assert "breakfast" in plan["meals"]
        assert "lunch" in plan["meals"]
        assert "dinner" in plan["meals"]
        assert "snack" in plan["meals"]

        # Calorie adherence within reasonable bounds
        target_cal = metrics["targets"]["daily_calories"]
        actual_cal = plan["daily_totals"]["calories"]
        assert abs(actual_cal - target_cal) / target_cal <= 0.15

    def test_allergen_hard_constraint_enforcement(self, rec_service):
        profile = ProfileService.get_default_profile()
        profile["allergens"] = ["Dairy", "Eggs", "Nuts / Peanuts"]
        metrics = ProfileService.calculate_profile_metrics(profile)

        plan = rec_service.generate_daily_plan(metrics)
        assert plan["success"] is True

        # Verify no allergen leaks
        all_items = []
        for slot in ["breakfast", "lunch", "dinner", "snack"]:
            all_items.extend(plan["meals"][slot])

        for it in all_items:
            raw = rec_service.repo.get_by_id(it["food_id"])
            if raw:
                allergens = [a.lower() for a in raw.get("allergens_list", [])]
                assert "dairy" not in allergens
                assert "eggs" not in allergens
                assert "nuts / peanuts" not in allergens

    def test_serving_quantity_update_recalculates_totals(self, rec_service):
        profile = ProfileService.get_default_profile()
        metrics = ProfileService.calculate_profile_metrics(profile)
        plan = rec_service.generate_daily_plan(metrics)

        # Get first breakfast item
        b_items = plan["meals"]["breakfast"]
        assert len(b_items) > 0
        first_item = b_items[0]
        old_cal = first_item["calories"]
        old_serv = first_item["servings"]

        # Double its serving
        new_serv = old_serv * 2.0
        updated = rec_service.update_serving_quantity(
            current_meals=plan["meals"],
            meal_slot="breakfast",
            food_id=first_item["food_id"],
            new_servings=new_serv,
            targets=metrics["targets"],
        )

        updated_first = updated["meals"]["breakfast"][0]
        assert updated_first["servings"] == round(new_serv, 2)
        assert pytest.approx(updated_first["calories"], 1.0) == old_cal * 2.0
        # Ensure daily total increased
        assert updated["daily_totals"]["calories"] > plan["daily_totals"]["calories"]

    def test_infeasible_constraint_handling(self, rec_service):
        # Exclude everything
        all_fids = [f["food_id"] for f in rec_service.repo.get_all()]
        profile = ProfileService.get_default_profile()
        profile["disliked_foods"] = all_fids

        metrics = ProfileService.calculate_profile_metrics(profile)
        plan = rec_service.generate_daily_plan(metrics)
        assert plan["success"] is False
        assert "No foods in database match" in plan["error"]
