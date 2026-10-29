"""
Authentication service with secure password hashing, user registration, login, and session tracking.
"""
import hashlib
import os
from typing import Optional, Tuple
import streamlit as st
from src.database.connection import get_db_context
from src.database.models import User, UserProfile
from src.database.repositories import UserRepository


def hash_password(password: str) -> str:
    """Secure PBKDF2-HMAC-SHA256 password hashing with 16-byte cryptographic salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    """Verifies provided password against stored PBKDF2 salt:hash."""
    try:
        salt_hex, key_hex = stored_password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        computed_key = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100000)
        return computed_key == key
    except Exception:
        return False


class AuthService:
    """Manages user authentication lifecycle."""

    @staticmethod
    def register_user(username: str, email: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Registers a new user with validation and secure password hashing."""
        clean_user = username.strip().lower()
        clean_email = email.strip().lower()

        if len(clean_user) < 3:
            return False, "Username must be at least 3 characters long.", None
        if "@" not in clean_email or "." not in clean_email:
            return False, "Invalid email address format.", None
        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        with get_db_context() as session:
            if UserRepository.get_by_username(session, clean_user):
                return False, f"Username '{clean_user}' is already registered.", None
            if UserRepository.get_by_email(session, clean_email):
                return False, f"Email '{clean_email}' is already registered.", None

            pw_hash = hash_password(password)
            user = UserRepository.create_user(session, clean_user, clean_email, pw_hash)
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "auth_provider": user.auth_provider,
            }
            return True, "Registration successful!", user_data

    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """Authenticates user credentials against the database."""
        clean_ident = username_or_email.strip().lower()

        with get_db_context() as session:
            user = UserRepository.get_by_username(session, clean_ident)
            if not user:
                user = UserRepository.get_by_email(session, clean_ident)

            if not user:
                return False, "Invalid username or password.", None

            if not verify_password(user.password_hash, password):
                return False, "Invalid username or password.", None

            # Return user info dict
            user_info = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "auth_provider": user.auth_provider,
            }
            return True, "Login successful!", user_info

    @staticmethod
    def check_user_has_profile(user_id: int) -> bool:
        """Determines if user has completed mandatory onboarding."""
        with get_db_context() as session:
            profile = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            return profile is not None


# Streamlit session authentication helpers
def get_current_user() -> Optional[dict]:
    """Returns currently authenticated user from Streamlit session state."""
    return st.session_state.get("authenticated_user")


def is_authenticated() -> bool:
    """Returns True if a user is actively authenticated."""
    return st.session_state.get("authenticated_user") is not None


def login_session_user(user_info: dict) -> None:
    """Sets authenticated user in session state."""
    st.session_state["authenticated_user"] = user_info
    has_profile = AuthService.check_user_has_profile(user_info["id"])
    st.session_state["has_completed_onboarding"] = has_profile


def logout_session_user() -> None:
    """Logs out user and clears sensitive session variables."""
    for key in ["authenticated_user", "has_completed_onboarding", "onboarding_step", "onboarding_data", "meal_plan"]:
        st.session_state.pop(key, None)
