"""
Unit tests for user progress tracking, weight logging, meal logging, and recommendation feedback.
"""
import pytest
from src.services.progress_service import ProgressService
from src.database.connection import get_db_context
from src.database.repositories import UserRepository


class TestProgressService:
    @pytest.fixture
    def demo_user_id(self):
        with get_db_context() as session:
            user = UserRepository.get_by_username(session, "demo_user")
            return user.id

    def test_record_weight_and_retrieve_history(self, demo_user_id):
        rec = ProgressService.record_weight(demo_user_id, 76.8, "Post-workout weight")
        assert rec["id"] is not None
        assert rec["weight_kg"] == 76.8

        history = ProgressService.get_weight_history(demo_user_id)
        assert len(history) >= 1
        assert any(entry["weight_kg"] == 76.8 for entry in history)

    def test_log_food_eaten_and_fetch_recent_logs(self, demo_user_id):
        food_data = {
            "food_id": "test_apple",
            "name": "Fresh Apple",
            "calories_per_serving": 95.0,
            "protein_per_serving": 0.5,
            "carbs_per_serving": 25.0,
            "fat_per_serving": 0.3,
        }
        log = ProgressService.log_food_eaten(demo_user_id, food_data, "snack", servings=2.0)
        assert log["id"] is not None
        assert log["food_name"] == "Fresh Apple"
        assert log["calories"] == 190.0

        recent = ProgressService.get_recent_meal_logs(demo_user_id, limit=5)
        assert len(recent) >= 1
        assert any(r["food_name"] == "Fresh Apple" for r in recent)

    def test_submit_recommendation_feedback(self, demo_user_id):
        ProgressService.submit_recommendation_feedback(
            user_id=demo_user_id,
            food_id="greek_yogurt",
            food_name="Greek Yogurt",
            feedback_type="liked",
            comment="Great breakfast option"
        )
        # Verify no exception was thrown and transaction committed
