"""
Authorization and access control guards for Streamlit pages.
Prevents unauthenticated or un-onboarded access and prevents cross-user data leakage.
"""
import streamlit as st
from src.auth.authentication import is_authenticated, get_current_user


def require_authentication():
    """
    Page guard: halts execution if user is not authenticated.
    Displays clear login prompt and navigation link.
    """
    if not is_authenticated():
        st.warning("🔒 Authentication required. Please log in to access this page.")
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("👉 Go to Login"):
                st.switch_page("app.py")
        st.stop()


def require_completed_onboarding():
    """
    Page guard: halts execution if user has not completed initial onboarding.
    Directs new users to complete their profile first.
    """
    require_authentication()
    if not st.session_state.get("has_completed_onboarding", False):
        st.info("📋 Welcome! Please complete your initial profile onboarding first to generate personalized plans.")
        if st.button("🚀 Start Onboarding Now", type="primary"):
            st.switch_page("app.py")
        st.stop()


def verify_user_access(resource_user_id: int, current_user_id: int) -> bool:
    """Verifies that the requested resource belongs strictly to the authenticated user."""
    if resource_user_id != current_user_id:
        raise PermissionError(f"Access denied: Resource user ID {resource_user_id} does not match current user {current_user_id}.")
    return True
