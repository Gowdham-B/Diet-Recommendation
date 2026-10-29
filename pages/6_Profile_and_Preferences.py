"""
Profile and Preferences Page: Review, update, and manage demographic attributes,
physiological metrics, metabolic targets, and dietary restrictions.
Offers immediate ML meal plan regeneration upon profile changes to avoid stale plans.
"""
import streamlit as st
import pandas as pd
import importlib
import src.services.profile_service
import src.services.meal_plan_service
importlib.reload(src.services.profile_service)
importlib.reload(src.services.meal_plan_service)

from src.auth.authentication import get_current_user
from src.auth.authorization import require_completed_onboarding
from src.services.profile_service import ProfileService
from src.services.meal_plan_service import MealPlanService
from src.database.connection import get_db_context
from src.database.repositories import MealPlanRepository


# Verify authentication and onboarding completion
require_completed_onboarding()

user = get_current_user()
st.title("⚙️ Profile & Dietary Preferences")
st.markdown(
    "Review and modify your demographic information, fitness goals, and dietary restrictions. "
    "When you update your parameters, your metabolic targets recalculate automatically."
)

current_profile = ProfileService.load_user_profile_and_preferences(user["id"])
if not current_profile:
    st.error("Profile not found. Please complete onboarding first.")
    st.stop()

# Compute initial baseline metrics
current_metrics = ProfileService.calculate_profile_metrics(current_profile)

col_form, col_metrics = st.columns([3, 2], gap="large")

with col_form:
    st.subheader("📝 Edit Personal Attributes")

    with st.form("profile_edit_form"):
        st.markdown("##### 1. Demographics & Body Metrics")
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            age = st.number_input("Age (years)", min_value=16, max_value=100, value=int(current_profile.get("age", 28)))
            gender = st.selectbox(
                "Biological Sex (for metabolic equations)",
                ["Male", "Female"],
                index=0 if current_profile.get("gender") == "Male" else 1,
                help="Used strictly for clinically validated Mifflin-St Jeor & Harris-Benedict BMR formulas."
            )
        with f_c2:
            height_cm = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=float(current_profile.get("height_cm", 175.0)), step=0.5)
            weight_kg = st.number_input("Weight (kg)", min_value=35.0, max_value=250.0, value=float(current_profile.get("weight_kg", 70.0)), step=0.5)

        st.markdown("##### 2. Activity Level & Fitness Goal")
        activity_options = [
            "Sedentary (desk job, little or no exercise)",
            "Lightly active (light exercise 1-3 days/week)",
            "Moderate (moderate exercise 3-5 days/week)",
            "Very active (hard exercise 6-7 days/week)",
            "Extremely active (hard daily training / physical labor)",
        ]
        curr_act = current_profile.get("activity_level", activity_options[2])
        act_idx = activity_options.index(curr_act) if curr_act in activity_options else 2
        activity_level = st.selectbox("Activity Level", activity_options, index=act_idx)

        goal_options = [
            "Weight Loss (Moderate deficit, -20%)",
            "Maintenance (Energy balance)",
            "Muscle Gain (Hypertrophy surplus, +15%)",
            "Endurance Performance (High carbohydrate focus)",
        ]
        curr_goal = current_profile.get("goal", goal_options[1])
        goal_idx = goal_options.index(curr_goal) if curr_goal in goal_options else 1
        goal = st.selectbox("Primary Nutritional Goal", goal_options, index=goal_idx)

        override_cal = st.number_input(
            "Custom Calorie Target Override (kcal, optional)",
            min_value=0,
            max_value=6000,
            value=int(current_profile.get("target_calorie_override") or 0),
            step=50,
            help="Leave at 0 to use scientific Mifflin-St Jeor + TDEE target."
        )

        st.markdown("##### 3. Dietary Patterns & Exclusions")
        pattern_options = [
            "Omnivore (No restrictions)",
            "Vegetarian (Lacto-ovo: no meat/fish)",
            "Vegan (Plant-based only: no animal products)",
            "Pescatarian (Vegetarian + seafood)",
            "Keto (Very low carb, high fat)",
            "Low Carb (Carbs < 130g/day)",
            "Mediterranean (Heart healthy)",
        ]
        curr_pat = current_profile.get("dietary_pattern", pattern_options[0])
        pat_idx = pattern_options.index(curr_pat) if curr_pat in pattern_options else 0
        dietary_pattern = st.selectbox("Dietary Pattern", pattern_options, index=pat_idx)

        common_allergens = [
            "Dairy", "Eggs", "Fish", "Shellfish", "Tree Nuts", "Peanuts", "Wheat / Gluten", "Soy", "Sesame"
        ]
        curr_allergens = [a for a in current_profile.get("allergens", []) if a in common_allergens]
        allergens = st.multiselect(
            "Allergies & Intolerances (Hard Safety Exclusions)",
            common_allergens,
            default=curr_allergens,
            help="Any food containing or flagged with these allergens will be completely eliminated by the safety filter."
        )

        curr_disliked = current_profile.get("disliked_foods", [])
        disliked_text = st.text_input(
            "Excluded / Disliked Foods (comma-separated)",
            value=", ".join(curr_disliked) if isinstance(curr_disliked, list) else str(curr_disliked),
            help="E.g., Mushrooms, Olives, Broccoli"
        )

        submit_save = st.form_submit_button("💾 Save Profile & Update Targets", type="primary", use_container_width=True)

    if submit_save:
        if override_cal > 0 and override_cal < 1000:
            st.error("Custom calorie target override must be at least 1,000 kcal for metabolic safety.")
        else:
            disliked_list = [f.strip() for f in disliked_text.split(",") if f.strip()]
            updated_profile = {
                "age": int(age),
                "gender": gender,
                "height_cm": float(height_cm),
                "weight_kg": float(weight_kg),
                "activity_level": activity_level,
                "goal": goal,
                "target_calorie_override": int(override_cal) if override_cal >= 1000 else None,
                "dietary_pattern": dietary_pattern,
                "allergens": allergens,
                "disliked_foods": disliked_list,
            }

            # Persist profile to DB
            ProfileService.save_user_profile_and_preferences(user["id"], updated_profile)

            # Mark previous active meal plans as historical to prevent stale recommendations
            with get_db_context() as session:
                session.query(MealPlanRepository.model if hasattr(MealPlanRepository, 'model') else None or MealPlanRepository.get_active_plan.__annotations__.get('return')).filter_by(user_id=user["id"], status="active").update({"status": "historical"}) if hasattr(MealPlanRepository, 'archive_active_plans') else None
                # Use raw query or repository method to archive
                from src.database.models import MealPlan
                session.query(MealPlan).filter(MealPlan.user_id == user["id"], MealPlan.status == "active").update({"status": "historical"})

            st.session_state["profile_updated"] = True
            st.success("✅ Profile and dietary preferences updated successfully! Previous recommendations archived as historical.")
            st.rerun()

with col_metrics:
    st.subheader("📊 Dynamic Physiological Metrics")

    # Calculate live updated metrics based on current saved or state
    live_profile = ProfileService.load_user_profile_and_preferences(user["id"])
    metrics = ProfileService.calculate_profile_metrics(live_profile)

    bmi_info = metrics["bmi_info"]
    targets = metrics["targets"]
    cal_info = metrics["calorie_info"]

    hw_min = bmi_info.get("healthy_weight_min_kg", bmi_info.get("healthy_weight_range_kg", (0, 0))[0])
    hw_max = bmi_info.get("healthy_weight_max_kg", bmi_info.get("healthy_weight_range_kg", (0, 0))[1])

    # BMI Card
    st.markdown(
        f"""
        <div style='background-color:#1e293b;padding:16px;border-radius:10px;border-left:5px solid #3b82f6;margin-bottom:14px;'>
            <div style='font-size:0.9rem;color:#94a3b8;'>Body Mass Index (BMI)</div>
            <div style='font-size:1.8rem;font-weight:700;color:#f8fafc;'>{bmi_info['bmi']} <span style='font-size:1.0rem;font-weight:400;color:#38bdf8;'>({bmi_info['category']})</span></div>
            <div style='font-size:0.85rem;color:#cbd5e1;margin-top:4px;'>Healthy Weight Range: <b>{hw_min} - {hw_max} kg</b></div>
        </div>
        """,
        unsafe_allow_html=True
    )


    # Metabolic Energy Card
    st.markdown(
        f"""
        <div style='background-color:#1e293b;padding:16px;border-radius:10px;border-left:5px solid #10b981;margin-bottom:14px;'>
            <div style='font-size:0.9rem;color:#94a3b8;'>Metabolic Rates (Mifflin-St Jeor)</div>
            <div style='display:flex;justify-content:space-between;margin-top:6px;'>
                <div><b>BMR:</b> {metrics['bmr_mifflin']:.0f} kcal/day</div>
                <div><b>TDEE:</b> {metrics['tdee']:.0f} kcal/day</div>
            </div>
            <div style='font-size:0.8rem;color:#94a3b8;margin-top:4px;'>Harris-Benedict Comparison: {metrics['bmr_harris_benedict']:.0f} kcal/day</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Daily Targets Card
    split = targets.get("macro_split") or {}
    ratios = targets.get("macro_ratios") or {}
    p_pct = split.get("protein_pct", int(round(ratios.get("protein", 0.25) * 100)))
    c_pct = split.get("carbs_pct", int(round(ratios.get("carbs", 0.50) * 100)))
    f_pct = split.get("fat_pct", int(round(ratios.get("fat", 0.25) * 100)))
    sodium_max = targets.get("sodium_mg_max", targets.get("max_sodium_mg", 2300.0))

    st.markdown(
        f"""
        <div style='background-color:#1e293b;padding:16px;border-radius:10px;border-left:5px solid #f59e0b;margin-bottom:14px;'>
            <div style='font-size:0.9rem;color:#94a3b8;'>Daily Calorie & Macronutrient Targets</div>
            <div style='font-size:1.6rem;font-weight:700;color:#fbbf24;'>{targets['daily_calories']:.0f} kcal/day</div>
            <div style='font-size:0.85rem;color:#cbd5e1;margin-top:6px;'>
                • <b>Protein:</b> {targets['protein_g']:.0f} g ({p_pct}%)<br>
                • <b>Carbs:</b> {targets['carbs_g']:.0f} g ({c_pct}%)<br>
                • <b>Fat:</b> {targets['fat_g']:.0f} g ({f_pct}%)<br>
                • <b>Fiber:</b> &ge; {targets['fiber_g']:.0f} g &nbsp;|&nbsp; <b>Sodium:</b> &le; {sodium_max:.0f} mg
            </div>
            {"<div style='color:#ef4444;font-size:0.8rem;margin-top:4px;'>⚠️ Calorie target clamped at safety floor.</div>" if cal_info.get('was_safety_clamped') else ""}
        </div>
        """,
        unsafe_allow_html=True
    )


    # Regeneration CTA
    st.markdown("---")
    st.markdown("#### 🔄 Regenerate Plan")
    st.caption("Apply your updated parameters to the ML ensemble recommendation engine to generate a fresh, personalized meal plan.")
    if st.button("🚀 Generate New ML Meal Plan", type="primary", use_container_width=True):
        meal_service = MealPlanService()
        with st.spinner("Generating personalized recommendations using ML ensemble..."):
            plan_res = meal_service.generate_and_save_plan(user["id"], live_profile, targets)
        if plan_res.get("success"):
            st.success("New meal plan generated successfully!")
            st.info("Head over to **Meal Recommendations** or **My Nutrition** in the sidebar to view your plan.")
        else:
            st.error(f"Could not generate plan: {plan_res.get('error', 'Unknown constraint violation')}")
