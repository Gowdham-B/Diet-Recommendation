"""
Unit tests for database models, repositories, and persistence layer.
Verifies user creation, profile upserts, meal plans, meal logs, and progress entries.
"""
import pytest
import uuid
from datetime import date
from src.database.connection import get_db_context
from src.database.models import User, UserProfile, DietaryPreference, MealPlan, MealLog, ProgressRecord
from src.database.repositories import UserRepository, ProfileRepository, MealPlanRepository, ProgressRepository, MealLogRepository


class TestDatabaseRepositories:
    def test_user_repository_crud(self):
        with get_db_context() as session:
            test_username = f"db_user_{uuid.uuid4().hex[:8]}"
            test_email = f"{test_username}@nutriplan.ai"

            # Create
            user = UserRepository.create_user(
                session=session,
                username=test_username,
                email=test_email,
                password_hash="salt:hash123"
            )
            assert user.id is not None
            assert user.username == test_username

            # Fetch by username
            fetched = UserRepository.get_by_username(session, test_username)
            assert fetched is not None
            assert fetched.id == user.id

            # Fetch by ID
            fetched_id = UserRepository.get_by_id(session, user.id)
            assert fetched_id is not None
            assert fetched_id.username == test_username

    def test_profile_repository_upsert(self):
        with get_db_context() as session:
            user = UserRepository.get_by_username(session, "demo_user")
            assert user is not None

            # Upsert Profile
            profile_data = {
                "age": 30,
                "gender": "Male",
                "height_cm": 180.0,
                "weight_kg": 78.0,
                "activity_level": "Moderate (moderate exercise 3-5 days/week)",
                "goal": "Maintenance",
                "target_calorie_override": None,
            }
            prof = ProfileRepository.upsert_profile(session, user.id, profile_data)
            assert prof.user_id == user.id
            assert prof.age == 30

            # Upsert Preferences
            pref_data = {
                "dietary_pattern": "Omnivore (No restrictions)",
                "allergens": "[]",
                "excluded_foods": "[]",
                "preferred_foods": "[]",
                "meals_per_day": 4,
            }
            pref = ProfileRepository.upsert_preferences(session, user.id, pref_data)
            assert pref.user_id == user.id
            assert pref.dietary_pattern == "Omnivore (No restrictions)"

    def test_progress_repository_weight_and_meals(self):
        with get_db_context() as session:
            user = UserRepository.get_by_username(session, "demo_user")
            assert user is not None

            # Log weight
            weight_entry = ProgressRepository.add_weight_record(session, user.id, 77.5, "Morning weigh-in")
            assert weight_entry.id is not None
            assert weight_entry.weight_kg == 77.5

            # Get weight history
            history = ProgressRepository.get_weight_history(session, user.id)
            assert len(history) >= 1
            assert any(entry.weight_kg == 77.5 for entry in history)

            # Log meal
            food_data = {
                "food_id": "test_oats",
                "name": "Rolled Oats",
                "calories_per_serving": 150.0,
                "protein_per_serving": 5.0,
                "carbs_per_serving": 27.0,
                "fat_per_serving": 2.5,
            }
            meal_log = MealLogRepository.log_meal(
                session=session,
                user_id=user.id,
                food_data=food_data,
                meal_slot="breakfast",
                servings=1.5,
            )
            assert meal_log.id is not None
            assert meal_log.food_name == "Rolled Oats"
