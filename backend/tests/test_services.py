from dataclasses import dataclass
from secrets import token_hex

import jwt
import pytest

from mycoai_retrieval_backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    require_role,
    verify_password,
)


class TestHashPassword:
    def test_hash_password_produces_valid_hash(self) -> None:
        pw = "my_secure_password_123"
        hashed = hash_password(pw)
        assert hashed != pw
        assert hashed.startswith("$2b$")

    def test_hash_password_is_deterministic_for_same_input(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestVerifyPassword:
    def test_verify_password_matches(self) -> None:
        pw = "correct_horse_battery_staple"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_password_mismatch(self) -> None:
        hashed = hash_password("password123")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self) -> None:
        hashed = hash_password("")
        assert verify_password("", hashed) is True


class TestCreateAccessToken:
    def test_create_access_token_contains_claims(self) -> None:
        token = create_access_token("user-id-123", "owner")
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == "user-id-123"
        assert payload["role"] == "owner"
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload


class TestCreateRefreshToken:
    def test_create_refresh_token_contains_claims(self) -> None:
        token = create_refresh_token("user-id-456")
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == "user-id-456"
        assert payload["type"] == "refresh"
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload


class TestDecodeToken:
    def test_decode_valid_token(self) -> None:
        token = create_access_token("user-x", "user")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-x"
        assert payload["role"] == "user"

    def test_decode_invalid_token_raises(self) -> None:
        with pytest.raises(jwt.DecodeError):
            decode_access_token("not.a.real.token")

    def test_decode_tampered_token_raises(self) -> None:
        token = create_access_token("user-y", "user")
        tampered = token[:-5] + ("AAAAA")
        with pytest.raises(jwt.PyJWTError):
            decode_access_token(tampered)

    def test_decode_expired_token_raises(self) -> None:
        now = 0
        payload = {
            "sub": "expired-user",
            "role": "user",
            "type": "access",
            "iat": now,
            "exp": now - 1,
            "jti": token_hex(16),
        }
        from mycoai_retrieval_backend.core.config import get_settings

        settings = get_settings()
        expired_token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(expired_token)


class TestRequireRole:
    @dataclass
    class FakeUser:
        role: str

    def test_require_role_passes_for_owner(self) -> None:
        user = self.FakeUser(role="owner")
        require_role(user, "owner")

    def test_require_role_raises_for_user(self) -> None:
        user = self.FakeUser(role="user")
        with pytest.raises(PermissionError, match="Missing required role: owner"):
            require_role(user, "owner")

    def test_require_role_passes_for_matching_user_role(self) -> None:
        user = self.FakeUser(role="user")
        require_role(user, "user")

    def test_require_role_raises_for_none_role(self) -> None:
        user = self.FakeUser(role="")
        with pytest.raises(PermissionError, match="Missing required role: owner"):
            require_role(user, "owner")
