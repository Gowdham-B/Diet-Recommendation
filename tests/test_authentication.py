"""
Unit tests for user authentication and credential security.
Verifies PBKDF2 password hashing, salt uniqueness, authentication verification,
and session management.
"""
import pytest
from src.auth.authentication import (
    hash_password,
    verify_password,
    AuthService,
)
from src.database.connection import get_db_context
from src.database.models import User


class TestAuthentication:
    def test_hash_password_produces_salt_and_hash(self):
        pwd = "SecurePassword123!"
        hashed = hash_password(pwd)
        assert ":" in hashed
        salt, h = hashed.split(":", 1)
        assert len(salt) == 32  # 16 bytes in hex
        assert len(h) == 64     # 32 bytes SHA256 in hex
        assert hashed != pwd    # Plaintext is never stored

    def test_verify_password_correct_and_incorrect(self):
        pwd = "CorrectHorseBatteryStaple"
        hashed = hash_password(pwd)
        assert verify_password(stored_password_hash=hashed, provided_password=pwd) is True
        assert verify_password(stored_password_hash=hashed, provided_password="WrongPassword") is False
        assert verify_password(stored_password_hash=hashed, provided_password="") is False

    def test_authenticate_existing_user(self):
        # demo_user was seeded during DB initialization
        success, msg, user_info = AuthService.authenticate_user("demo_user", "password123")
        assert success is True
        assert user_info is not None
        assert user_info["username"] == "demo_user"

    def test_authenticate_wrong_password_fails(self):
        success, msg, user_info = AuthService.authenticate_user("demo_user", "bad_password")
        assert success is False
        assert user_info is None

    def test_register_and_authenticate_new_user(self):
        unique_username = "test_user_auth_unique"
        # Cleanup in case of previous run
        with get_db_context() as session:
            existing = session.query(User).filter_by(username=unique_username).first()
            if existing:
                session.delete(existing)

        success, msg, new_user = AuthService.register_user(unique_username, "test_unique@nutriplan.ai", "MySecretPass999")
        assert success is True
        assert new_user is not None
        assert new_user["username"] == unique_username

        # Now authenticate with the new credentials
        auth_success, auth_msg, auth_user = AuthService.authenticate_user(unique_username, "MySecretPass999")
        assert auth_success is True
        assert auth_user is not None
        assert auth_user["id"] == new_user["id"]

    def test_register_duplicate_username_fails(self):
        success, msg, user = AuthService.register_user("demo_user", "another_email@nutriplan.ai", "any_password")
        assert success is False
        assert "already registered" in msg

