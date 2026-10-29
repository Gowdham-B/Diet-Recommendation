"""
Unit tests for authorization and cross-user data isolation.
Verifies that resource access verification prevents unauthorized data inspection.
"""
import pytest
from src.auth.authorization import verify_user_access


class TestAuthorization:
    def test_verify_user_access_same_user_allowed(self):
        assert verify_user_access(resource_user_id=42, current_user_id=42) is True

    def test_verify_user_access_cross_user_denied(self):
        with pytest.raises(PermissionError, match="Access denied"):
            verify_user_access(resource_user_id=99, current_user_id=42)
