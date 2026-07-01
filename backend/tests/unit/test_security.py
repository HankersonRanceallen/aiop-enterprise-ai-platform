"""Unit tests for app/core/security.py — no external dependencies."""
import pytest
from datetime import timedelta

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"

    def test_verify_correct_password(self):
        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses a random salt — same input produces different hashes."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2


class TestJWT:
    def test_access_token_decodes(self):
        token = create_access_token(subject=42)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_refresh_token_decodes(self):
        token = create_refresh_token(subject=99)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "99"
        assert payload["type"] == "refresh"

    def test_expired_token_returns_none(self):
        token = create_access_token(subject=1, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_invalid_token_returns_none(self):
        assert decode_token("not.a.real.token") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token(subject=1)
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_access_token_cannot_be_used_as_refresh(self):
        token = create_access_token(subject=1)
        payload = decode_token(token)
        assert payload["type"] == "access"
        assert payload["type"] != "refresh"
