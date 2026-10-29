"""
My Progress Page: Weight tracking trends, historical meal logs, and saved plan history.
"""
import streamlit as st
import pandas as pd
import importlib
import src.services.progress_service
importlib.reload(src.services.progress_service)

from src.auth.authentication import get_current_user
from src.auth.authorization import require_completed_onboarding
from src.services.progress_service import ProgressService
from src.database.connection import get_db_context
from src.database.repositories import MealPlanRepository


require_completed_onboarding()

user = get_current_user()
st.title("📈 My Health & Nutrition Progress")
st.markdown("Track your body weight trajectory over time, inspect historical meal logs, and review saved plans.")

tab_weight, tab_logs, tab_plans = st.tabs(["⚖️ Weight Tracker", "🍽️ Meal Log History", "📜 Saved Plan History"])

# ----------------- TAB 1: WEIGHT TRACKER -----------------
with tab_weight:
    st.subheader("Body Weight Trajectory")

    col_form, col_chart = st.columns([1, 2])

    with col_form:
        with st.form("weight_log_form"):
            st.markdown("#### Record Weight Entry")
            w_input = st.number_input("Weight (kg)", min_value=30.0, max_value=300.0, value=75.0, step=0.1)
            notes_input = st.text_input("Notes (optional)", placeholder="e.g. morning fasting weight")
            submit_w = st.form_submit_button("💾 Save Weight Record", type="primary", use_container_width=True)

            if submit_w:
                ProgressService.record_weight(user["id"], w_input, notes_input)
                st.success(f"Saved weight record: {w_input} kg!")
                st.rerun()

    with col_chart:
        history = ProgressService.get_weight_history(user["id"])
        if not history:
            st.info("No weight logs recorded yet. Add your first weight entry on the left to start tracking.")
        else:
            w_df = pd.DataFrame(history)
            st.markdown(f"**Latest recorded weight:** `{w_df.iloc[-1]['weight_kg']} kg`")
            # Line chart
            chart_data = w_df.set_index("date")["weight_kg"]
            st.line_chart(chart_data)
            with st.expander("View Weight History Table"):
                st.dataframe(w_df, use_container_width=True, hide_index=True)


# ----------------- TAB 2: MEAL LOG HISTORY -----------------
with tab_logs:
    st.subheader("Historical Meal Intake Logs")
    logs = ProgressService.get_recent_logs(user["id"], limit=50)

    if not logs:
        st.info("No meals have been logged yet. Use the Quick Meal Logger on the **My Nutrition** page to record meals.")
    else:
        df_logs = pd.DataFrame(logs)
        st.dataframe(
            df_logs.rename(columns={
                "logged_at": "Timestamp",
                "food_name": "Food Item",
                "meal_slot": "Meal Slot",
                "servings": "Servings",
                "calories": "Calories (kcal)",
                "protein_g": "Protein (g)",
                "carbs_g": "Carbs (g)",
                "fat_g": "Fat (g)",
            }),
            use_container_width=True,
            hide_index=True,
        )


# ----------------- TAB 3: SAVED PLAN HISTORY -----------------
with tab_plans:
    saved_plans_data = []
    with get_db_context() as session:
        plans = MealPlanRepository.get_plan_history(session, user["id"], limit=10)
        for p in plans:
            items_summary = [f"{it.food_name} ({it.servings}x, {it.calories:.0f} kcal)" for it in p.items]
            saved_plans_data.append({
                "status": p.status,
                "plan_name": p.plan_name,
                "created_at": p.created_at.strftime('%Y-%m-%d %H:%M'),
                "model_version": p.model_version,
                "ensemble_config": p.ensemble_config,
                "target_calories": p.target_calories,
                "total_calories": p.total_calories,
                "total_protein_g": p.total_protein_g,
                "total_carbs_g": p.total_carbs_g,
                "total_fat_g": p.total_fat_g,
                "items_summary": ", ".join(items_summary),
            })

    if not saved_plans_data:
        st.info("No saved meal plans in your database.")
    else:
        for p in saved_plans_data:
            badge = "🟢 ACTIVE" if p["status"] == "active" else "⚪ HISTORICAL"
            with st.expander(f"{p['plan_name']} — {p['created_at']} ({badge})"):
                st.write(f"- **Engine Version:** `{p['model_version']}` ({p['ensemble_config']})")
                st.write(f"- **Target Calories:** `{p['target_calories']:.0f} kcal` | **Plan Total:** `{p['total_calories']:.0f} kcal`")
                st.write(f"- **Protein:** `{p['total_protein_g']:.1f}g` | **Carbs:** `{p['total_carbs_g']:.1f}g` | **Fat:** `{p['total_fat_g']:.1f}g`")
                st.write(f"**Items:** {p['items_summary']}")

