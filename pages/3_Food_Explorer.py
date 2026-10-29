"""
USDA-Verified Food Explorer, Nutrition Search, and Comparative Nutritional Analysis.
"""
import streamlit as st
import pandas as pd
from src.data.validation import validate_atwater_balance
from src.data.food_repository import FoodRepository
from src.auth.authorization import require_authentication

require_authentication()

st.title("🔍 Verified Food Explorer & Comparative Analysis")
st.markdown("Search, inspect, and compare verified food composition records sourced from USDA FoodData Central.")

repo = FoodRepository()
df = repo.dataframe

# Filtering Section
with st.expander("⚙️ Filter Food Catalog", expanded=True):
    col_s, col_cat, col_diet = st.columns([3, 2, 2])
    with col_s:
        search_query = st.text_input("Search foods by name", placeholder="e.g., Apple, Salmon, Oats...")
    with col_cat:
        categories = ["All"] + repo.get_categories()
        selected_category = st.selectbox("Category", options=categories)
    with col_diet:
        diet_filter = st.selectbox(
            "Dietary Tag",
            options=["All", "Vegan", "Vegetarian", "Pescatarian", "Keto-Friendly", "Gluten-Free", "Dairy-Free"]
        )

# Apply filters
filtered_df = df.copy()
if search_query:
    filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(search_query.strip().lower())]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

if diet_filter == "Vegan":
    filtered_df = filtered_df[filtered_df["is_vegan"] == True]
elif diet_filter == "Vegetarian":
    filtered_df = filtered_df[filtered_df["is_vegetarian"] == True]
elif diet_filter == "Pescatarian":
    filtered_df = filtered_df[filtered_df["is_pescatarian"] == True]
elif diet_filter == "Keto-Friendly":
    filtered_df = filtered_df[filtered_df["is_keto_friendly"] == True]
elif diet_filter == "Gluten-Free":
    filtered_df = filtered_df[filtered_df["is_gluten_free"] == True]
elif diet_filter == "Dairy-Free":
    filtered_df = filtered_df[filtered_df["is_dairy_free"] == True]

st.markdown(f"**Found {len(filtered_df)} verified food items:**")

# Catalog Display Table
display_cols = [
    "name", "category", "serving_unit", "calories_per_serving",
    "protein_per_serving", "carbs_per_serving", "fat_per_serving",
    "fiber_per_serving", "estimated_cost_usd", "data_quality_status"
]
rename_map = {
    "name": "Food Name",
    "category": "Category",
    "serving_unit": "Standard Serving",
    "calories_per_serving": "Calories (kcal)",
    "protein_per_serving": "Protein (g)",
    "carbs_per_serving": "Carbs (g)",
    "fat_per_serving": "Fat (g)",
    "fiber_per_serving": "Fiber (g)",
    "estimated_cost_usd": "Est. Cost ($)",
    "data_quality_status": "Quality Status",
}
st.dataframe(
    filtered_df[display_cols].rename(columns=rename_map),
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

# Section 2: Side-by-Side Food Comparison Tool
st.subheader("⚖️ Side-by-Side Food Comparison")
st.markdown("Compare macro density and micronutrient profiles between two foods.")

all_food_names = sorted(df["name"].tolist())
col_a, col_b = st.columns(2)

with col_a:
    food_a_name = st.selectbox("Select Food A", options=all_food_names, index=0)
with col_b:
    food_b_idx = min(1, len(all_food_names) - 1)
    food_b_name = st.selectbox("Select Food B", options=all_food_names, index=food_b_idx)

food_a = df[df["name"] == food_a_name].iloc[0]
food_b = df[df["name"] == food_b_name].iloc[0]

comp_metrics = [
    ("Serving Size", f"{food_a['serving_unit']}", f"{food_b['serving_unit']}"),
    ("Calories (serving)", f"{food_a['calories_per_serving']:.1f} kcal", f"{food_b['calories_per_serving']:.1f} kcal"),
    ("Protein (serving)", f"{food_a['protein_per_serving']:.1f} g", f"{food_b['protein_per_serving']:.1f} g"),
    ("Carbohydrates (serving)", f"{food_a['carbs_per_serving']:.1f} g", f"{food_b['carbs_per_serving']:.1f} g"),
    ("Fat (serving)", f"{food_a['fat_per_serving']:.1f} g", f"{food_b['fat_per_serving']:.1f} g"),
    ("Fiber (serving)", f"{food_a['fiber_per_serving']:.1f} g", f"{food_b['fiber_per_serving']:.1f} g"),
    ("Sodium (serving)", f"{food_a['sodium_mg_per_serving']:.0f} mg", f"{food_b['sodium_mg_per_serving']:.0f} mg"),
    ("Est. Cost", f"${food_a['estimated_cost_usd']:.2f}", f"${food_b['estimated_cost_usd']:.2f}"),
    ("Allergens", f"{food_a['allergens']}", f"{food_b['allergens']}"),
]

comp_df = pd.DataFrame(comp_metrics, columns=["Nutritional Metric", food_a_name, food_b_name])
st.table(comp_df.set_index("Nutritional Metric"))

# Section 3: Serving Size & Atwater Physics Visualizer
st.markdown("---")
st.subheader("🔬 Portion Scaling & Atwater Consistency Verification")
st.markdown("Observe how nutritional values scale with portion mass, and verify caloric physics using the Atwater equation.")

sel_food_name = st.selectbox("Inspect food scaling", options=all_food_names, index=0)
selected_food = df[df["name"] == sel_food_name].iloc[0]
raw_portion = float(selected_food.get("serving_size_g", 100.0))
clamped_portion = min(max(raw_portion, 10.0), 500.0)

portion_grams = st.slider(
    f"Portion Weight for {sel_food_name} (grams)",
    min_value=10.0,
    max_value=500.0,
    value=clamped_portion,
    step=10.0,
)

scale = portion_grams / 100.0
scaled_cal = selected_food["calories_per_100g"] * scale
scaled_p = selected_food["protein_per_100g"] * scale
scaled_c = selected_food["carbs_per_100g"] * scale
scaled_f = selected_food["fat_per_100g"] * scale
scaled_fib = selected_food["fiber_per_100g"] * scale

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
with col_m1:
    st.metric("Total Weight", f"{portion_grams:.0f} g")
with col_m2:
    st.metric("Calories", f"{scaled_cal:.1f} kcal")
with col_m3:
    st.metric("Protein", f"{scaled_p:.1f} g")
with col_m4:
    st.metric("Carbs", f"{scaled_c:.1f} g")
with col_m5:
    st.metric("Fat", f"{scaled_f:.1f} g")

# Atwater Verification
atwater = validate_atwater_balance(scaled_p, scaled_c, scaled_f, scaled_cal)
st.caption(
    f"**Atwater Physical Energy:** Theoretical: `{atwater['theoretical_calories']:.1f} kcal` | "
    f"Recorded: `{atwater['recorded_calories']:.1f} kcal` | "
    f"Difference: `{atwater['percentage_difference']:.1f}%` ({'✅ Physically Valid' if atwater['is_physically_consistent'] else '⚠️ Discrepancy'})"
)
