"""
My Nutrition Page: User dashboard displaying current nutrition targets, active meal plan,
live meal logger, and recent meal intake logs from database.
"""
import streamlit as st
import pandas as pd
from datetime import date
import importlib
import src.services.profile_service
import src.services.meal_plan_service
import src.services.progress_service
importlib.reload(src.services.profile_service)
importlib.reload(src.services.meal_plan_service)
importlib.reload(src.services.progress_service)

from src.auth.authentication import get_current_user
from src.auth.authorization import require_completed_onboarding
from src.services.profile_service import ProfileService
from src.services.meal_plan_service import MealPlanService
from src.services.progress_service import ProgressService


# Check authentication and onboarding status
require_completed_onboarding()

user = get_current_user()
st.title(f"📊 My Nutrition Dashboard")
st.markdown(f"Welcome, **{user['username']}**! Track your daily nutrient fulfillment and record meals eaten.")

profile = ProfileService.load_user_profile_and_preferences(user["id"])
metrics = ProfileService.calculate_profile_metrics(profile)
targets = metrics["targets"]

meal_service = MealPlanService()
active_plan = meal_service.load_active_plan(user["id"], targets)

if not active_plan or not active_plan.get("success"):
    st.info("No active meal plan found in your account.")
    if st.button("🚀 Generate ML Meal Plan Now", type="primary"):
        with st.spinner("Generating..."):
            active_plan = meal_service.generate_and_save_plan(user["id"], profile, targets)
        st.rerun()
    st.stop()

totals = active_plan["daily_totals"]
adherence = active_plan["adherence"]

# Top Metrics Row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Calories Target", f"{targets['daily_calories']:.0f} kcal", f"{adherence['calories_pct']}% of target")
with c2:
    st.metric("Protein Target", f"{targets['protein_g']:.0f} g", f"{adherence['protein_pct']}% of target")
with c3:
    st.metric("Carbs Target", f"{targets['carbs_g']:.0f} g", f"{adherence['carbs_pct']}% of target")
with c4:
    st.metric("Fat Target", f"{targets['fat_g']:.0f} g", f"{adherence['fat_pct']}% of target")

st.markdown("---")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("🍽️ Today's Recommended Meals")
    st.caption(f"Generated via: **{active_plan.get('model_version')}** ({active_plan.get('ensemble_config')})")

    slot_icons = {"breakfast": "🌅 Breakfast", "lunch": "☀️ Lunch", "dinner": "🌙 Dinner", "snack": "🍎 Snack"}
    for slot_k, slot_name in slot_icons.items():
        items = active_plan["meals"].get(slot_k, [])
        with st.expander(f"{slot_name} ({len(items)} items)", expanded=True):
            for it in items:
                col_it1, col_it2, col_it3 = st.columns([3, 2, 2])
                with col_it1:
                    st.write(f"**{it['name']}**")
                    st.caption(f"ML Score: `{it.get('predicted_suitability_score', 0.9):.2f}` | {it.get('serving_unit')}")
                with col_it2:
                    st.write(f"{it['servings']}x ({it['total_weight_g']:.0f}g)")
                    st.caption(f"P: {it['protein_g']:.1f}g | C: {it['carbs_g']:.1f}g")
                with col_it3:
                    st.write(f"**{it['calories']:.0f} kcal**")
                    # Quick log button
                    if st.button("➕ Log Eaten", key=f"quick_log_{slot_k}_{it['food_id']}"):
                        ProgressService.log_food_eaten(user["id"], it, slot_k, it["servings"])
                        st.toast(f"Logged {it['name']} to meal history!")

with col_right:
    st.subheader("📝 Quick Meal Logger")
    st.markdown("Record custom foods consumed today into your database log.")

    all_foods = meal_service.repo.get_all()
    food_names = [f["name"] for f in all_foods]

    with st.form("custom_meal_log_form"):
        sel_food_name = st.selectbox("Food Item", options=food_names)
        sel_slot = st.selectbox("Meal Slot", options=["breakfast", "lunch", "dinner", "snack"])
        serv_mult = st.number_input("Servings Consumed", min_value=0.25, max_value=10.0, value=1.0, step=0.25)

        submit_log = st.form_submit_button("💾 Save Meal Log", type="primary", use_container_width=True)
        if submit_log:
            matched_f = next((f for f in all_foods if f["name"] == sel_food_name), None)
            if matched_f:
                ProgressService.log_food_eaten(user["id"], matched_f, sel_slot, serv_mult)
                st.success(f"Logged {serv_mult}x {sel_food_name}!")
                st.rerun()

    st.markdown("### 📋 Recent Meal Logs (Today)")
    recent_logs = ProgressService.get_recent_logs(user["id"], limit=8)
    if not recent_logs:
        st.info("No meals recorded yet today. Use the Quick Meal Logger above to log your intake.")
    else:
        log_df = pd.DataFrame(recent_logs)[["logged_at", "food_name", "meal_slot", "servings", "calories", "protein_g"]]
        st.dataframe(
            log_df.rename(columns={
                "logged_at": "Timestamp",
                "food_name": "Food Item",
                "meal_slot": "Slot",
                "servings": "Servings",
                "calories": "Calories",
                "protein_g": "Protein (g)",
            }),
            use_container_width=True,
            hide_index=True,
        )
