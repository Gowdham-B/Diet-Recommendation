"""
Streamlit session state manager ensuring unified state across multi-page navigation.
"""
from typing import Dict, Any
import streamlit as st
from src.services.profile_service import ProfileService
from src.services.recommendation_service import RecommendationService


def initialize_session_state() -> None:
    """Initializes default profile, services, and meal plans if not already present."""
    if "rec_service" not in st.session_state:
        st.session_state["rec_service"] = RecommendationService()

    if "profile" not in st.session_state:
        st.session_state["profile"] = ProfileService.get_default_profile()

    if "profile_metrics" not in st.session_state:
        st.session_state["profile_metrics"] = ProfileService.calculate_profile_metrics(
            st.session_state["profile"]
        )

    if "meal_plan" not in st.session_state:
        st.session_state["meal_plan"] = st.session_state["rec_service"].generate_daily_plan(
            st.session_state["profile_metrics"]
        )


def refresh_meal_plan() -> None:
    """Recomputes profile metrics and generates a fresh meal plan."""
    st.session_state["profile_metrics"] = ProfileService.calculate_profile_metrics(
        st.session_state["profile"]
    )
    st.session_state["meal_plan"] = st.session_state["rec_service"].generate_daily_plan(
        st.session_state["profile_metrics"]
    )
