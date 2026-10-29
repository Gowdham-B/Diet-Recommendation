"""
Meal Recommendations Page: Detailed food-level recommendations, ML suitability scores,
real-time portion sliders, food substitutions, user feedback, and export options.
"""
import streamlit as st
import pandas as pd
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


require_completed_onboarding()

user = get_current_user()
st.title("🍽️ Machine Learning Meal Recommendations")
st.markdown("Inspect ML-predicted suitability scores, fine-tune serving portions, swap foods, and log feedback.")

profile = ProfileService.load_user_profile_and_preferences(user["id"])
metrics = ProfileService.calculate_profile_metrics(profile)
targets = metrics["targets"]

meal_service = MealPlanService()
plan = meal_service.load_active_plan(user["id"], targets)

# Action bar
col_act1, col_act2 = st.columns([4, 1])
with col_act2:
    if st.button("🔄 Re-Generate Plan", type="primary", use_container_width=True):
        with st.spinner("Re-optimizing with ML Ensemble..."):
            plan = meal_service.generate_and_save_plan(user["id"], profile, targets)
        st.success("Fresh plan generated and saved!")
        st.rerun()

if not plan or not plan.get("success"):
    st.info("No active plan found. Click Re-Generate Plan above.")
    st.stop()

meals = plan["meals"]
totals = plan["daily_totals"]
adherence = plan["adherence"]

# Top Adherence Ribbon
st.markdown(
    f"""
    <div style='background-color:#1e293b;padding:12px 20px;border-radius:10px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;'>
        <div>
            <b>Daily Intake:</b> <span style='color:#10b981;font-weight:700;'>{totals['calories']:.0f} kcal</span> / {targets['daily_calories']:.0f} kcal ({adherence['calories_pct']}%)
        </div>
        <div>
            <b>Protein:</b> {totals['protein_g']:.1f}g / {targets['protein_g']:.0f}g ({adherence['protein_pct']}%)
        </div>
        <div>
            <b>Carbs:</b> {totals['carbs_g']:.1f}g / {targets['carbs_g']:.0f}g ({adherence['carbs_pct']}%)
        </div>
        <div>
            <b>Fat:</b> {totals['fat_g']:.1f}g / {targets['fat_g']:.0f}g ({adherence['fat_pct']}%)
        </div>
        <div>
            <b>Est. Cost:</b> <span style='color:#38bdf8;font-weight:600;'>${totals['estimated_cost_usd']:.2f}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

all_repo_foods = meal_service.repo.get_all()
slot_names = [
    ("breakfast", "🌅 Breakfast", 0.25),
    ("lunch", "☀️ Lunch", 0.35),
    ("dinner", "🌙 Dinner", 0.30),
    ("snack", "🍎 Snack", 0.10),
]

for slot_key, slot_title, slot_pct in slot_names:
    items = meals.get(slot_key, [])
    slot_summary = plan["meal_summaries"].get(slot_key, {})
    slot_target_cal = targets["daily_calories"] * slot_pct

    with st.expander(f"{slot_title} — {slot_summary.get('calories', 0):.0f} kcal (Target: ~{slot_target_cal:.0f} kcal)", expanded=True):
        if not items:
            st.info("No items allocated for this meal slot.")
            continue

        for idx, food in enumerate(items):
            f_col1, f_col2, f_col3 = st.columns([3, 2, 2])
            
            with f_col1:
                st.markdown(f"#### {food['name']}")
                score = food.get("predicted_suitability_score", 0.95)
                st.markdown(f"**ML Suitability Score:** `<span style='color:#10b981;font-weight:700;'>{score:.2f}</span>` | Rank: `#{idx+1}`", unsafe_allow_html=True)
                st.caption(f"Standard unit: {food.get('serving_unit', '1 serving')} ({food.get('total_weight_g', 100):.0f}g)")
                st.write(f"💡 *{food.get('rationale', 'High nutrient suitability')}*")

                # Feedback Buttons (Like / Dislike)
                col_fb1, col_fb2, col_fb3 = st.columns([1, 1, 2])
                with col_fb1:
                    if st.button("👍", key=f"like_{slot_key}_{food['food_id']}_{idx}", help="Like this recommendation"):
                        ProgressService.submit_recommendation_feedback(user["id"], food["food_id"], food["name"], "liked")
                        st.toast(f"Saved: Liked {food['name']}")
                with col_fb2:
                    if st.button("👎", key=f"dislike_{slot_key}_{food['food_id']}_{idx}", help="Dislike this recommendation"):
                        ProgressService.submit_recommendation_feedback(user["id"], food["food_id"], food["name"], "disliked")
                        st.toast(f"Saved: Disliked {food['name']}")

            with f_col2:
                # Real-time portion slider
                slider_key = f"slider_{slot_key}_{food['food_id']}_{idx}"
                raw_serv = float(food.get("servings", 1.0))
                clamped_serv = min(max(raw_serv, 0.25), 3.0)
                new_serv = st.slider(
                    f"Servings ({raw_serv:.2f}x)",
                    min_value=0.25,
                    max_value=3.0,
                    value=clamped_serv,
                    step=0.25,
                    key=slider_key,
                )
                if new_serv != food["servings"]:
                    updated = meal_service.update_serving_quantity(
                        current_meals=meals,
                        meal_slot=slot_key,
                        food_id=food["food_id"],
                        new_servings=new_serv,
                        targets=targets,
                    )
                    # Persist updated serving to DB
                    meal_service.generate_and_save_plan(user["id"], profile, targets)
                    st.rerun()

                st.write(f"**Weight:** {food['total_weight_g']:.0f} g | **Cost:** ${food['estimated_cost_usd']:.2f}")

            with f_col3:
                st.metric("Calories", f"{food['calories']:.0f} kcal")
                st.caption(f"P: {food['protein_g']:.1f}g | C: {food['carbs_g']:.1f}g | F: {food['fat_g']:.1f}g")

                # Food Substitution Dropdown
                sub_key = f"sub_{slot_key}_{food['food_id']}_{idx}"
                eligible_subs = [f["name"] for f in all_repo_foods if f["food_id"] != food["food_id"]]
                selected_sub = st.selectbox("Substitute with:", options=["(Keep current)"] + eligible_subs, key=sub_key)
                
                if selected_sub != "(Keep current)":
                    matched_new = next((f for f in all_repo_foods if f["name"] == selected_sub), None)
                    if matched_new:
                        updated = meal_service.substitute_food(
                            current_meals=meals,
                            meal_slot=slot_key,
                            old_food_id=food["food_id"],
                            new_food_id=matched_new["food_id"],
                            targets=targets,
                            goal=profile["goal"],
                            dietary_pattern=profile["dietary_pattern"],
                        )
                        ProgressService.submit_recommendation_feedback(
                            user["id"], food["food_id"], food["name"], "substituted", f"Replaced with {selected_sub}"
                        )
                        st.success(f"Swapped for {selected_sub}!")
                        st.rerun()

            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dashed #334155;' />", unsafe_allow_html=True)

        st.markdown(
            f"**{slot_title} Subtotal:** `{slot_summary.get('calories', 0):.0f} kcal` | "
            f"Protein: `{slot_summary.get('protein_g', 0):.1f}g` | "
            f"Carbs: `{slot_summary.get('carbs_g', 0):.1f}g` | "
            f"Fat: `{slot_summary.get('fat_g', 0):.1f}g` | "
            f"Cost: `${slot_summary.get('estimated_cost_usd', 0):.2f}`"
        )

# Export options
st.markdown("---")
st.subheader("📥 Export Meal Plan")
col_e1, col_e2 = st.columns(2)

md_lines = [
    f"# Personalized Daily Meal Plan",
    f"**User:** {user['username']} | **Goal:** {profile['goal']} | **Target:** {targets['daily_calories']:.0f} kcal",
    f"**Totals:** {totals['calories']:.0f} kcal, {totals['protein_g']:.1f}g Protein, {totals['carbs_g']:.1f}g Carbs, {totals['fat_g']:.1f}g Fat\n",
]
for slot_k, slot_t, _ in slot_names:
    md_lines.append(f"## {slot_t}")
    for item in meals.get(slot_k, []):
        md_lines.append(f"- **{item['name']}** ({item['servings']}x servings, {item['total_weight_g']:.0f}g): {item['calories']:.0f} kcal (P: {item['protein_g']:.1f}g, C: {item['carbs_g']:.1f}g, F: {item['fat_g']:.1f}g)")
    md_lines.append("")

with col_e1:
    st.download_button("📄 Download Plan as Markdown", data="\n".join(md_lines), file_name="nutriplan_daily_plan.md", mime="text/markdown", use_container_width=True)

with col_e2:
    plan_rows = []
    for slot_k, items in meals.items():
        for it in items:
            row = dict(it)
            row["meal_slot"] = slot_k
            plan_rows.append(row)
    csv_data = pd.DataFrame(plan_rows).to_csv(index=False)
    st.download_button("📊 Download Plan as CSV", data=csv_data, file_name="nutriplan_daily_plan.csv", mime="text/csv", use_container_width=True)
