"""Tests for authentication and security utilities."""

import pytest
from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Password hash/verify tests."""

    def test_hash_and_verify(self):
        raw = "SuperSecret123!"
        hashed = hash_password(raw)
        assert hashed != raw
        assert verify_password(raw, hashed) is True

    def test_wrong_password_rejected(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Each call should produce a different hash (salt)."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


@pytest.mark.unit
class TestJWT:
    """JWT token creation and decoding tests."""

    def test_create_and_decode_token(self):
        token = create_access_token(
            user_id="user-123",
            email="test@example.com",
            org_id="org-456",
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["org_id"] == "org-456"

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_access_token("not.a.valid.token")
