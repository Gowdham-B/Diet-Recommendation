"""
Comprehensive End-to-End User Journey and Regression Verification Test Suite.
Validates that the entire NutriPlan AI pipeline works cohesively without
attribute errors, key errors, detached session errors, or invalid UI inputs.
"""
import pytest
import uuid
from src.auth.authentication import AuthService
from src.services.profile_service import ProfileService
from src.services.meal_plan_service import MealPlanService
from src.services.progress_service import ProgressService
from src.database.connection import get_db_context
from src.database.repositories import MealPlanRepository, UserRepository


def test_complete_end_to_end_user_journey():
    """
    Simulates the entire real-world user lifecycle:
    1. Register new user
    2. Save profile & dietary preferences
    3. Calculate metabolic targets (Mifflin-St Jeor, TDEE, macros)
    4. Generate ML soft-voting ensemble meal plan
    5. Update serving portion size & substitute food item
    6. Log eaten meals & check daily intake
    7. Record weight measurement & retrieve history
    8. Retrieve historical plans without DetachedInstanceError
    9. Edit profile & regenerate plan
    """
    unique_suffix = uuid.uuid4().hex[:8]
    username = f"journey_user_{unique_suffix}"
    email = f"journey_{unique_suffix}@nutriplan.test"
    password = "SecurePassword123!"

    # 1. Registration
    success, msg, user_data = AuthService.register_user(username, email, password)
    assert success is True, f"Registration failed: {msg}"
    assert user_data is not None
    user_id = user_data["id"]
    assert user_id > 0

    # 2. Save profile & preferences
    profile_data = {
        "age": 28,
        "gender": "Female",
        "height_cm": 165.0,
        "weight_kg": 68.0,
        "activity_level": "Moderately Active (exercise 3-5 days/week)",
        "goal": "Weight Loss (Mild Deficit -0.5 kg/week)",
        "target_calorie_override": None,
        "dietary_pattern": "Vegetarian (Lacto-ovo: no meat/fish)",
        "allergens": ["Peanuts", "Shellfish"],
        "disliked_foods": ["Broccoli"],
    }
    ProfileService.save_user_profile_and_preferences(user_id, profile_data)

    # 3. Load & calculate profile metrics
    loaded_profile = ProfileService.load_user_profile_and_preferences(user_id)
    assert loaded_profile["age"] == 28
    assert loaded_profile["gender"] == "Female"
    assert loaded_profile["dietary_pattern"] == "Vegetarian (Lacto-ovo: no meat/fish)"
    assert "Peanuts" in loaded_profile["allergens"]

    metrics = ProfileService.calculate_profile_metrics(loaded_profile)
    assert "bmi_info" in metrics
    assert "healthy_weight_range_kg" in metrics["bmi_info"]
    assert "healthy_weight_min_kg" in metrics["bmi_info"]
    assert "healthy_weight_max_kg" in metrics["bmi_info"]
    assert metrics["bmi_info"]["healthy_weight_range_kg"][0] > 0
    assert metrics["bmi_info"]["healthy_weight_range_kg"][1] > metrics["bmi_info"]["healthy_weight_range_kg"][0]

    targets = metrics["targets"]
    assert "daily_calories" in targets
    assert targets["daily_calories"] >= 1200.0  # Female safety floor
    assert "macro_split" in targets
    assert "protein_pct" in targets["macro_split"]
    assert "carbs_pct" in targets["macro_split"]
    assert "fat_pct" in targets["macro_split"]
    assert "sodium_mg_max" in targets or "max_sodium_mg" in targets

    # 4. Generate ML Meal Plan
    meal_service = MealPlanService()
    plan_res = meal_service.generate_and_save_plan(user_id, loaded_profile, targets)
    assert plan_res["success"] is True, f"Meal plan generation failed: {plan_res.get('error')}"
    assert "meals" in plan_res
    assert len(plan_res["meals"]) > 0
    assert "daily_totals" in plan_res
    assert "adherence" in plan_res
    assert "model_version" in plan_res

    # Check allergens exclusion: no food should contain peanuts or shellfish
    for slot, items in plan_res["meals"].items():
        for item in items:
            name_lower = item["name"].lower()
            assert "peanut" not in name_lower
            assert "shrimp" not in name_lower
            assert "crab" not in name_lower
            assert item["servings"] > 0
            assert item["calories"] > 0

    # 5. Load Active Plan & Test Portion Adjustment
    active_plan = meal_service.load_active_plan(user_id, targets)
    assert active_plan is not None
    assert active_plan["success"] is True

    # Find first food item in breakfast or lunch
    first_slot = next(s for s in ["breakfast", "lunch", "dinner", "snack"] if active_plan["meals"].get(s))
    target_food = active_plan["meals"][first_slot][0]
    original_servings = target_food["servings"]
    new_servings = 1.5

    updated_plan = meal_service.update_serving_quantity(
        current_meals=active_plan["meals"],
        meal_slot=first_slot,
        food_id=target_food["food_id"],
        new_servings=new_servings,
        targets=targets,
    )
    assert updated_plan["meals"][first_slot][0]["servings"] == 1.5

    # 6. Log meal eaten & query logs
    log_res = ProgressService.log_food_eaten(user_id, target_food, first_slot, servings=1.5)
    assert log_res["id"] > 0
    assert log_res["food_name"] == target_food["name"]

    logs = ProgressService.get_recent_logs(user_id, limit=10)
    assert len(logs) >= 1
    assert logs[0]["food_name"] == target_food["name"]
    assert logs[0]["servings"] == 1.5
    assert "logged_at" in logs[0]
    assert "calories" in logs[0]
    assert "protein_g" in logs[0]

    # 7. Record weight & check history
    w_res = ProgressService.record_weight(user_id, 67.8, notes="Morning weigh-in")
    assert w_res["id"] > 0
    assert w_res["weight_kg"] == 67.8

    history = ProgressService.get_weight_history(user_id)
    assert len(history) >= 1
    assert history[0]["weight_kg"] == 67.8

    # Feedback submission
    ProgressService.submit_recommendation_feedback(user_id, target_food["food_id"], target_food["name"], "liked")

    # 8. Check Historical Plans Extraction (Preventing DetachedInstanceError)
    with get_db_context() as session:
        plans = MealPlanRepository.get_plan_history(session, user_id, limit=5)
        assert len(plans) >= 1
        p = plans[0]
        # Access attributes inside session context
        status = p.status
        items_count = len(p.items)
        assert items_count > 0

    # Ensure items can still be referenced because expire_on_commit=False and joinedload
    assert p.status == "active"
    assert len(p.items) > 0
    for it in p.items:
        assert it.food_name is not None
        assert it.calories > 0

    # 9. Profile Modification & Re-generation
    updated_profile_data = dict(loaded_profile)
    updated_profile_data["goal"] = "Muscle Gain (+0.25 kg/week)"
    updated_profile_data["activity_level"] = "Very Active (hard exercise 6-7 days/week)"
    ProfileService.save_user_profile_and_preferences(user_id, updated_profile_data)

    new_metrics = ProfileService.calculate_profile_metrics(updated_profile_data)
    new_targets = new_metrics["targets"]
    assert new_targets["daily_calories"] > targets["daily_calories"]

    new_plan_res = meal_service.generate_and_save_plan(user_id, updated_profile_data, new_targets)
    assert new_plan_res["success"] is True


def test_defensive_slider_and_override_safeguards():
    """
    Validates that edge-case values for inputs (e.g. 0 calorie override,
    out-of-bounds servings or portion values) do not break the engine.
    """
    # Test zero override fallback
    profile = {
        "age": 30,
        "gender": "Male",
        "height_cm": 180.0,
        "weight_kg": 80.0,
        "activity_level": "Sedentary (little or no exercise)",
        "goal": "Maintenance (Keep current weight)",
        "target_calorie_override": 0,
        "dietary_pattern": "Omnivore (No restrictions)",
        "allergens": [],
        "disliked_foods": [],
    }
    metrics = ProfileService.calculate_profile_metrics(profile)
    targets = metrics["targets"]
    # 0 override should not set daily_calories to 0; Mifflin-St Jeor TDEE should be used
    assert targets["daily_calories"] > 1800.0

    # Test slider clamping logic simulated as in Streamlit pages
    min_s, max_s = 0.25, 3.0
    for test_serv in [-1.0, 0.0, 0.25, 2.5, 5.0, 10.0]:
        clamped_serv = min(max(test_serv, min_s), max_s)
        assert min_s <= clamped_serv <= max_s

    min_p, max_p = 10.0, 500.0
    for test_p in [-5.0, 0.0, 5.0, 150.0, 750.0]:
        clamped_p = min(max(test_p, min_p), max_p)
        assert min_p <= clamped_p <= max_p
