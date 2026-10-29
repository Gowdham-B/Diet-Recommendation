"""
NutriPlan AI: Intelligent Personalized Nutrition & Meal Recommendation System.
Main entry point handling Authentication, Mandatory First-Time Onboarding, and Active Session Routing.
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

from src.auth.authentication import (
    AuthService,
    get_current_user,
    is_authenticated,
    login_session_user,
    logout_session_user,
)
from src.services.profile_service import ProfileService
from src.services.meal_plan_service import MealPlanService
from src.services.progress_service import ProgressService
from src.config.settings import (
    SUPPORTED_DIETARY_PATTERNS,
    SUPPORTED_ALLERGENS,
    NutritionConstants,
)


# Page configuration
st.set_page_config(
    page_title="NutriPlan AI | Intelligent Nutrition System",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Design System
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    st.title("🥗 NutriPlan AI")
    st.caption("Machine Learning-Driven Clinical Nutrition & Optimization")
    st.markdown("---")

    if is_authenticated():
        user = get_current_user()
        st.write(f"Logged in as: **{user['username']}**")
        if st.button("🚪 Log Out", use_container_width=True):
            logout_session_user()
            st.rerun()
    else:
        st.info("Please log in or register to access personalized nutrition features.")


# ==============================================================================
# ROUTE 1: UNAUTHENTICATED USERS (LOGIN & REGISTRATION)
# ==============================================================================
if not is_authenticated():
    st.title("🥗 Welcome to NutriPlan AI")
    st.markdown(
        "A clinically grounded, machine learning-driven nutrition application that predicts food suitability "
        "and optimizes balanced daily meal plans based on your metabolic requirements and lifestyle constraints."
    )

    col_hero, col_auth = st.columns([3, 2])

    with col_hero:
        st.image("https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80", use_container_width=True)
        st.markdown(
            """
            ### Why NutriPlan AI?
            - 🤖 **Ensemble Machine Learning:** Evaluates candidate foods using 4 trained models (Random Forest, Gradient Boosting, MLP, KNN) and Soft Voting / Stacking ensembles.
            - 🔬 **USDA-Verified Ground Truth:** Built on verified food composition from USDA FoodData Central, not synthetic uniform distributions.
            - 🛡️ **Guaranteed Safety Constraints:** Hard exclusion for 6 major allergen classes (Dairy, Gluten, Nuts, Eggs, Soy, Seafood).
            - ⚖️ **Portion Balancing:** Mathematically balances meal portions to hit your clinical calorie and macro goals.
            - 💾 **Persistent Progress Tracking:** Saves your profile, historical plans, and meal logs in a persistent database.
            """
        )

    with col_auth:
        tab_login, tab_register, tab_demo = st.tabs(["🔑 Sign In", "📝 Create Account", "⚡ Quick Demo"])

        with tab_login:
            st.subheader("Account Login")
            with st.form("login_form"):
                login_ident = st.text_input("Username or Email", placeholder="e.g. demo_user")
                login_pass = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if submit_login:
                    success, msg, user_data = AuthService.authenticate_user(login_ident, login_pass)
                    if success:
                        login_session_user(user_data)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with tab_register:
            st.subheader("New User Registration")
            with st.form("register_form"):
                reg_user = st.text_input("Choose Username", placeholder="e.g., alex_nutrition")
                reg_email = st.text_input("Email Address", placeholder="alex@example.com")
                reg_pass = st.text_input("Create Password (min 6 chars)", type="password")
                submit_reg = st.form_submit_button("Create Account", type="primary", use_container_width=True)

                if submit_reg:
                    success, msg, new_user = AuthService.register_user(reg_user, reg_email, reg_pass)
                    if success:
                        st.success(f"{msg} You can now log in.")
                    else:
                        st.error(msg)

        with tab_demo:
            st.subheader("Explore with Demo Account")
            st.markdown("Instantly test the full application using the seeded local demonstration credentials.")
            if st.button("🚀 Log In as 'demo_user'", use_container_width=True, type="secondary"):
                success, msg, user_data = AuthService.authenticate_user("demo_user", "password123")
                if success:
                    login_session_user(user_data)
                    st.success("Authenticated as demo_user!")
                    st.rerun()
                else:
                    st.error("Demo account not found. Run initialize_database.py first.")

    st.stop()


# ==============================================================================
# ROUTE 2: AUTHENTICATED USER — MANDATORY ONBOARDING JOURNEY
# ==============================================================================
user = get_current_user()
has_onboarded = st.session_state.get("has_completed_onboarding", False)

if not has_onboarded:
    st.title(f"👋 Welcome, {user['username']}! Let's Set Up Your Nutrition Profile")
    st.markdown("Complete this short onboarding to calculate your clinical metabolic targets and generate your first personalized meal plan.")

    # Onboarding step tracker in session state
    if "onboarding_step" not in st.session_state:
        st.session_state["onboarding_step"] = 1
    if "onboarding_data" not in st.session_state:
        st.session_state["onboarding_data"] = ProfileService.get_default_profile()

    step = st.session_state["onboarding_step"]
    o_data = st.session_state["onboarding_data"]

    # Step progress bar
    st.progress(step / 4)
    st.caption(f"Onboarding Step {step} of 4")

    # ----------------- STEP 1: PERSONAL STATS -----------------
    if step == 1:
        st.subheader("Step 1: Physical Characteristics & Energy Factors")
        with st.form("onboard_step1_form"):
            c1, c2 = st.columns(2)
            with c1:
                age = st.number_input("Age (years)", min_value=14, max_value=100, value=int(o_data["age"]))
                height_cm = st.number_input("Height (cm)", min_value=100.0, max_value=230.0, value=float(o_data["height_cm"]), step=0.5)
            with c2:
                gender = st.selectbox("Biological Sex (for Mifflin-St Jeor equation)", options=["Male", "Female"], index=0 if o_data["gender"] == "Male" else 1)
                weight_kg = st.number_input("Weight (kg)", min_value=35.0, max_value=250.0, value=float(o_data["weight_kg"]), step=0.5)

            act_options = list(NutritionConstants.ACTIVITY_FACTORS.keys())
            activity_level = st.selectbox("Physical Activity Level", options=act_options, index=2)

            goal_options = list(NutritionConstants.GOAL_CALORIE_ADJUSTMENTS.keys())
            goal = st.selectbox("Primary Fitness & Weight Goal", options=goal_options, index=3)

            next_s1 = st.form_submit_button("Continue to Dietary Preferences ➡️", type="primary")
            if next_s1:
                o_data.update({
                    "age": age,
                    "gender": gender,
                    "height_cm": height_cm,
                    "weight_kg": weight_kg,
                    "activity_level": activity_level,
                    "goal": goal,
                })
                st.session_state["onboarding_data"] = o_data
                st.session_state["onboarding_step"] = 2
                st.rerun()

    # ----------------- STEP 2: DIETARY PREFERENCES -----------------
    elif step == 2:
        st.subheader("Step 2: Dietary Lifestyle & Exclusions")
        with st.form("onboard_step2_form"):
            dietary_pattern = st.selectbox("Dietary Pattern", options=SUPPORTED_DIETARY_PATTERNS, index=0)
            allergens = st.multiselect(
                "Allergies to Strictly Exclude",
                options=SUPPORTED_ALLERGENS,
                default=o_data.get("allergens", []),
                help="Foods with these allergens will be completely excluded from recommendations."
            )

            col_back, col_next = st.columns([1, 4])
            with col_back:
                back_btn = st.form_submit_button("⬅️ Back")
            with col_next:
                next_s2 = st.form_submit_button("Review Nutritional Targets ➡️", type="primary")

            if back_btn:
                st.session_state["onboarding_step"] = 1
                st.rerun()
            if next_s2:
                o_data.update({
                    "dietary_pattern": dietary_pattern,
                    "allergens": allergens,
                })
                st.session_state["onboarding_data"] = o_data
                st.session_state["onboarding_step"] = 3
                st.rerun()

    # ----------------- STEP 3: REVIEW & CONFIRMATION -----------------
    elif step == 3:
        st.subheader("Step 3: Review Your Metabolic Targets")
        metrics = ProfileService.calculate_profile_metrics(o_data)
        bmi_info = metrics["bmi_info"]
        cal_info = metrics["calorie_info"]
        targets = metrics["targets"]

        c_rev1, c_rev2 = st.columns(2)
        with c_rev1:
            st.markdown("#### Physical Profile")
            st.write(f"- **Demographics:** {o_data['gender']}, {o_data['age']} years")
            st.write(f"- **Height & Weight:** {o_data['height_cm']} cm, {o_data['weight_kg']} kg")
            st.write(f"- **BMI:** **{bmi_info['bmi']}** ({bmi_info['category']})")
            st.write(f"- **Activity Level:** {o_data['activity_level']}")
            st.write(f"- **Goal:** **{o_data['goal']}**")
            st.write(f"- **Diet Pattern:** {o_data['dietary_pattern']}")
            if o_data.get("allergens"):
                st.write(f"- **Allergens Excluded:** {', '.join(o_data['allergens'])}")

        with c_rev2:
            st.markdown("#### Clinical Energy Targets")
            st.write(f"- **BMR (Mifflin-St Jeor):** `{metrics['bmr_mifflin']:.0f} kcal/day`")
            st.write(f"- **TDEE:** `{metrics['tdee']:.0f} kcal/day`")
            st.markdown(f"### Target Calories: **{cal_info['target_calories']:.0f} kcal/day**")
            if cal_info.get("was_safety_clamped"):
                st.warning(f"⚠️ Calorie target clamped to safety floor ({cal_info['safety_floor_kcal']:.0f} kcal).")

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Protein", f"{targets['protein_g']:.0f} g")
            with col_m2:
                st.metric("Carbs", f"{targets['carbs_g']:.0f} g")
            with col_m3:
                st.metric("Fat", f"{targets['fat_g']:.0f} g")

        st.markdown("---")
        cb1, cb2 = st.columns([1, 4])
        with cb1:
            if st.button("⬅️ Modify"):
                st.session_state["onboarding_step"] = 2
                st.rerun()
        with cb2:
            if st.button("🚀 Confirm & Run ML Recommendation Engine", type="primary", use_container_width=True):
                st.session_state["onboarding_step"] = 4
                st.rerun()

    # ----------------- STEP 4: RECOMMENDATION GENERATION -----------------
    elif step == 4:
        st.subheader("Step 4: Machine Learning Recommendation Generation")
        with st.spinner("Scoring foods with ML Soft Voting Ensemble & balancing portions..."):
            # 1. Save profile and preferences to database
            ProfileService.save_user_profile_and_preferences(user["id"], o_data)

            # 2. Compute targets
            metrics = ProfileService.calculate_profile_metrics(o_data)

            # 3. Generate ML meal plan and persist to database
            meal_service = MealPlanService()
            plan = meal_service.generate_and_save_plan(user["id"], o_data, metrics["targets"])

            if plan.get("success"):
                st.session_state["has_completed_onboarding"] = True
                st.success("🎉 Onboarding complete! Your personalized plan has been generated and saved.")
                if st.button("👉 View My Nutrition Dashboard", type="primary"):
                    st.rerun()
            else:
                st.error(f"Error generating plan: {plan.get('error')}")
                if st.button("⬅️ Back to Preferences"):
                    st.session_state["onboarding_step"] = 2
                    st.rerun()

    st.stop()


# ==============================================================================
# ROUTE 3: RETURNING AUTHENTICATED USER WITH COMPLETED ONBOARDING
# ==============================================================================
# Load saved profile from database
saved_profile = ProfileService.load_user_profile_and_preferences(user["id"])
if not saved_profile:
    st.session_state["has_completed_onboarding"] = False
    st.rerun()

metrics = ProfileService.calculate_profile_metrics(saved_profile)
meal_service = MealPlanService()
active_plan = meal_service.load_active_plan(user["id"], metrics["targets"])

st.title(f"🥗 Welcome Back, {user['username']}!")
st.markdown("Your active personalized nutrition plan, daily calorie progress, and machine learning recommendations.")

if not active_plan or not active_plan.get("success"):
    st.warning("No active meal plan found in your database. Let's generate one now!")
    if st.button("🔄 Generate ML Meal Plan", type="primary"):
        with st.spinner("Generating..."):
            active_plan = meal_service.generate_and_save_plan(user["id"], saved_profile, metrics["targets"])
        st.rerun()
else:
    totals = active_plan["daily_totals"]
    targets = metrics["targets"]
    adherence = active_plan["adherence"]

    # Top KPI Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(
            label="Daily Calories",
            value=f"{totals['calories']:.0f} kcal",
            delta=f"{totals['calories'] - targets['daily_calories']:+.0f} kcal ({adherence['calories_pct']}%)",
        )
    with c2:
        st.metric(
            label="Protein",
            value=f"{totals['protein_g']:.1f} g",
            delta=f"{totals['protein_g'] - targets['protein_g']:+.1f} g ({adherence['protein_pct']}%)",
        )
    with c3:
        st.metric(
            label="Carbohydrates",
            value=f"{totals['carbs_g']:.1f} g",
            delta=f"{totals['carbs_g'] - targets['carbs_g']:+.1f} g ({adherence['carbs_pct']}%)",
        )
    with c4:
        st.metric(
            label="Healthy Fats",
            value=f"{totals['fat_g']:.1f} g",
            delta=f"{totals['fat_g'] - targets['fat_g']:+.1f} g ({adherence['fat_pct']}%)",
        )
    with c5:
        st.metric(
            label="Est. Daily Cost",
            value=f"${totals['estimated_cost_usd']:.2f}",
            delta="Whole food budget",
        )

    st.markdown("---")

    # Quick Navigation Banner
    col_nav1, col_nav2, col_nav3 = st.columns(3)
    with col_nav1:
        if st.button("🍽️ Customize Meal Plan & Portions", use_container_width=True):
            st.switch_page("pages/2_Meal_Recommendations.py")
    with col_nav2:
        if st.button("📊 View Progress & Meal Logs", use_container_width=True):
            st.switch_page("pages/4_My_Progress.py")
    with col_nav3:
        if st.button("🤖 Inspect ML Model Insights", use_container_width=True):
            st.switch_page("pages/5_Model_Insights.py")

    st.markdown("---")

    # Today's Meals Overview
    st.subheader("🍽️ Active Daily Meal Plan")
    st.caption(f"Engine: **{active_plan.get('model_version', 'Ensemble v1.0')}** ({active_plan.get('ensemble_config')})")

    m_cols = st.columns(4)
    slot_titles = {"breakfast": "🌅 Breakfast", "lunch": "☀️ Lunch", "dinner": "🌙 Dinner", "snack": "🍎 Snack"}

    for idx, (slot_k, slot_name) in enumerate(slot_titles.items()):
        items = active_plan["meals"].get(slot_k, [])
        with m_cols[idx]:
            st.markdown(f"### {slot_name}")
            for it in items:
                st.markdown(f"**{it['name']}**")
                st.caption(
                    f"{it['servings']}x ({it['total_weight_g']:.0f}g) • {it['calories']:.0f} kcal\n"
                    f"ML Score: `{it.get('predicted_suitability_score', 0.95):.2f}`"
                )
            slot_sub = active_plan["meal_summaries"].get(slot_k, {})
            st.markdown(
                f"<div style='background-color:#1e293b;padding:8px;border-radius:6px;font-size:0.85rem;'>"
                f"Subtotal: <b>{slot_sub.get('calories', 0):.0f} kcal</b> | P: <b>{slot_sub.get('protein_g', 0):.1f}g</b>"
                f"</div>",
                unsafe_allow_html=True,
            )
