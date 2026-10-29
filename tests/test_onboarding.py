"""
Unit tests for the first-time user onboarding journey.
Verifies onboarding validation, mandatory parameter verification, and profile completion states.
"""
import pytest
import uuid
from src.services.profile_service import ProfileService
from src.database.connection import get_db_context
from src.database.repositories import UserRepository, ProfileRepository


class TestOnboardingWorkflow:
    def test_default_onboarding_profile_validity(self):
        default_prof = ProfileService.get_default_profile()
        assert default_prof["age"] > 0
        assert default_prof["height_cm"] > 0
        assert default_prof["weight_kg"] > 0

        # Calculate metrics from default profile
        metrics = ProfileService.calculate_profile_metrics(default_prof)
        assert metrics["bmi_info"]["bmi"] > 15.0
        assert metrics["tdee"] > 1000.0
        assert metrics["targets"]["daily_calories"] >= 1200.0

    def test_onboarding_persistence_and_retrieval(self):
        unique_user = f"onboard_u_{uuid.uuid4().hex[:8]}"
        with get_db_context() as session:
            user = UserRepository.create_user(
                session=session,
                username=unique_user,
                email=f"{unique_user}@nutriplan.ai",
                password_hash="dummy_hash"
            )
            user_id = user.id


        # Profile does not exist yet before onboarding
        initial = ProfileService.load_user_profile_and_preferences(user_id)
        assert initial is None

        # User completes onboarding
        completed_data = {
            "age": 25,
            "gender": "Female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "activity_level": "Moderate (moderate exercise 3-5 days/week)",
            "goal": "Weight Loss (Moderate deficit, -20%)",
            "dietary_pattern": "Vegetarian (Lacto-ovo: no meat/fish)",
            "allergens": ["Peanuts"],
            "disliked_foods": ["Mushrooms"],
        }
        ProfileService.save_user_profile_and_preferences(user_id, completed_data)

        # Profile now exists
        loaded = ProfileService.load_user_profile_and_preferences(user_id)
        assert loaded is not None
        assert loaded["age"] == 25
        assert loaded["gender"] == "Female"
        assert loaded["dietary_pattern"] == "Vegetarian (Lacto-ovo: no meat/fish)"
        assert "Peanuts" in loaded["allergens"]
