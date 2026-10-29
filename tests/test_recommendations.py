"""
Unit tests for the core MLRecommendationPipeline.
Verifies ensemble scoring integration, safety eligibility filters, slot distribution,
and provenance tracking.
"""
import pytest
from src.recommendation.generation import MLRecommendationPipeline
from src.data.food_repository import FoodRepository
from src.services.profile_service import ProfileService


class TestRecommendationsPipeline:
    @pytest.fixture
    def pipeline(self):
        return MLRecommendationPipeline(FoodRepository())

    @pytest.fixture
    def default_user_and_targets(self):
        profile = ProfileService.get_default_profile()
        metrics = ProfileService.calculate_profile_metrics(profile)
        return profile, metrics["targets"]

    def test_pipeline_generates_valid_meal_plan(self, pipeline, default_user_and_targets):
        profile, targets = default_user_and_targets
        result = pipeline.generate_personalized_plan(profile, targets)

        assert result["success"] is True
        assert "meals" in result
        assert "daily_totals" in result
        assert "model_version" in result
        assert "ensemble_config" in result

        # Check all 4 meal slots are populated
        for slot in ["breakfast", "lunch", "dinner", "snack"]:
            assert slot in result["meals"]
            assert len(result["meals"][slot]) >= 1

    def test_strict_allergen_hard_constraint(self, pipeline, default_user_and_targets):
        profile, targets = default_user_and_targets
        profile["allergens"] = ["Dairy", "Eggs"]

        result = pipeline.generate_personalized_plan(profile, targets)
        assert result["success"] is True

        for slot, foods in result["meals"].items():
            for food in foods:
                allergens = [a.lower() for a in food.get("allergens_list", [])]
                assert "dairy" not in allergens, f"Dairy found in {food['name']}"
                assert "eggs" not in allergens, f"Eggs found in {food['name']}"

    def test_empty_candidate_set_fails_gracefully(self, pipeline, default_user_and_targets):
        profile, targets = default_user_and_targets
        # Impossible constraints: exclude all foods
        repo = FoodRepository()
        all_food_names = [f["name"] for f in repo.get_all_foods()]
        profile["disliked_foods"] = all_food_names

        result = pipeline.generate_personalized_plan(profile, targets)
        assert result["success"] is False
        assert "No foods" in result["error"]
