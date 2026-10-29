"""
Unit tests for Machine Learning inference pipeline.
Verifies scoring foods for user profiles, output bounds, ranking, and error handling.
"""
import pytest
from src.models.inference import FoodSuitabilityInference, DietModelInference
from src.data.food_repository import FoodRepository


class TestInferencePipeline:
    @pytest.fixture
    def inference_engine(self):
        return FoodSuitabilityInference(model_type="ensemble_voting")

    @pytest.fixture
    def sample_user(self):
        return {
            "age": 28,
            "gender": "Male",
            "bmi": 23.5,
            "goal": "Maintenance",
            "dietary_pattern": "Omnivore (No restrictions)",
        }

    @pytest.fixture
    def sample_targets(self):
        return {
            "daily_calories": 2400.0,
            "protein_g": 150.0,
            "carbs_g": 270.0,
            "fat_g": 80.0,
            "tdee": 2400.0,
        }

    def test_score_foods_returns_ranked_probabilities(self, inference_engine, sample_user, sample_targets):
        repo = FoodRepository()
        foods = repo.get_all_foods()[:5]

        scored = inference_engine.score_foods_for_user(sample_user, sample_targets, foods)
        assert len(scored) == len(foods)

        # Verify each food has suitability score in [0.0, 1.0]
        for f in scored:
            assert "predicted_suitability_score" in f
            score = f["predicted_suitability_score"]
            assert 0.0 <= score <= 1.0

        # Verify descending sort order
        scores = [f["predicted_suitability_score"] for f in scored]
        assert scores == sorted(scores, reverse=True)

    def test_score_foods_empty_list_returns_empty(self, inference_engine, sample_user, sample_targets):
        scored = inference_engine.score_foods_for_user(sample_user, sample_targets, [])
        assert scored == []

    def test_diet_model_inference_schema_validation(self):
        engine = DietModelInference()
        # Missing Carbs and Fat
        with pytest.raises(ValueError, match="Inference schema mismatch"):
            engine.predict({"Calories (kcal)": 200, "Protein (g)": 20})
