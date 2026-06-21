import pytest
from pydantic import ValidationError

from backend.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    FeedbackCreateRequest,
    SpeciesCreateRequest,
    TokenPair,
    UserProfile,
)


class TestAuthRegisterRequest:
    def test_valid_register_request(self) -> None:
        req = AuthRegisterRequest(
            email="test@example.com", password="securepass123", name="Test User"
        )
        assert req.email == "test@example.com"
        assert req.name == "Test User"

    def test_invalid_register_short_password(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(
                email="test@example.com", password="1234567", name="Test"
            )

    def test_invalid_register_bad_email(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(email="not-an-email", password="12345678", name="Test")

    def test_invalid_register_missing_name(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(email="test@example.com", password="12345678")  # type: ignore[arg-type]


class TestAuthLoginRequest:
    def test_valid_login_request(self) -> None:
        req = AuthLoginRequest(email="user@mycoai.dev", password="password123")
        assert req.email == "user@mycoai.dev"

    def test_login_requires_email(self) -> None:
        with pytest.raises(ValidationError):
            AuthLoginRequest(password="password123")  # type: ignore[arg-type]

    def test_login_requires_password(self) -> None:
        with pytest.raises(ValidationError):
            AuthLoginRequest(email="user@mycoai.dev")  # type: ignore[arg-type]


class TestFeedbackCreateRequest:
    def test_feedback_create_validates_description_required(self) -> None:
        with pytest.raises(ValidationError):
            FeedbackCreateRequest(
                retrieval_result_id="result-1",
                feedback_type="wrong_prediction",
            )  # type: ignore[arg-type]

    def test_feedback_create_validates_retrieval_result_id_optional(self) -> None:
        req = FeedbackCreateRequest(
            feedback_type="wrong_prediction",
            description="No result id needed",
        )
        assert req.retrieval_result_id is None
        assert req.feedback_type == "wrong_prediction"

    def test_feedback_create_validates_feedback_type(self) -> None:
        with pytest.raises(ValidationError):
            FeedbackCreateRequest(
                retrieval_result_id="result-1",
                feedback_type="invalid_type",  # type: ignore[arg-type]
                description="Bad type",
            )

    def test_feedback_create_with_all_fields(self) -> None:
        req = FeedbackCreateRequest(
            retrieval_result_id="result-1",
            feedback_type="wrong_prediction",
            suggested_species="Penicillium chrysogenum",
            description="This looks like P. chrysogenum instead",
            query_strain="DTO 148-D1",
            image_id="img-1",
            predicted_species="Penicillium commune",
        )
        assert req.feedback_type == "wrong_prediction"
        assert req.query_strain == "DTO 148-D1"
        assert req.suggested_species == "Penicillium chrysogenum"

    def test_feedback_create_minimal(self) -> None:
        req = FeedbackCreateRequest(
            feedback_type="contribution",
            description="Useful feedback",
        )
        assert req.feedback_type == "contribution"

    def test_feedback_create_valid_feedback_types(self) -> None:
        for ft in ("wrong_prediction", "issue", "contribution"):
            req = FeedbackCreateRequest(
                retrieval_result_id="r",
                feedback_type=ft,  # type: ignore[arg-type]
                description="desc",
            )
            assert req.feedback_type == ft


class TestSpeciesCreateRequest:
    def test_species_create_validates_name_required(self) -> None:
        with pytest.raises(ValidationError):
            SpeciesCreateRequest()  # type: ignore[arg-type]

    def test_species_create_with_name_only(self) -> None:
        req = SpeciesCreateRequest(name="Aspergillus flavus")
        assert req.name == "Aspergillus flavus"
        assert req.description is None

    def test_species_create_with_description(self) -> None:
        req = SpeciesCreateRequest(
            name="Penicillium expansum",
            description="Causes blue mold of apple",
        )
        assert req.name == "Penicillium expansum"
        assert req.description == "Causes blue mold of apple"


class TestTokenPair:
    def test_token_response_structure(self) -> None:
        token = TokenPair(
            access_token="eyJhbGciOiJIUzI1NiJ9.abc123",
            refresh_token="eyJhbGciOiJIUzI1NiJ9.def456",
            token_type="bearer",
            expires_in=3600,
        )
        assert token.access_token == "eyJhbGciOiJIUzI1NiJ9.abc123"
        assert token.refresh_token == "eyJhbGciOiJIUzI1NiJ9.def456"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600

    def test_token_type_defaults_to_bearer(self) -> None:
        token = TokenPair(
            access_token="a",
            refresh_token="r",
            expires_in=60,
        )
        assert token.token_type == "bearer"


class TestUserProfile:
    def test_user_response_structure(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        profile = UserProfile(
            id="550e8400-e29b-41d4-a716-446655440000",
            email="user@mycoai.dev",
            name="Test User",
            role="user",
            is_active=True,
            created_at=now,
        )
        assert profile.id == "550e8400-e29b-41d4-a716-446655440000"
        assert profile.email == "user@mycoai.dev"
        assert profile.role == "user"
        assert profile.is_active is True

    def test_user_profile_role_literals(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        profile = UserProfile(
            id="1",
            email="owner@mycoai.dev",
            name="Owner",
            role="owner",
            is_active=True,
            created_at=now,
        )
        assert profile.role == "owner"


class TestAuthRegisterRequestEdge:
    def test_password_min_length_enforced(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(email="a@b.com", password="a" * 7, name="Test")

    def test_password_exactly_min_length_ok(self) -> None:
        req = AuthRegisterRequest(email="a@b.com", password="a" * 8, name="Test")
        assert req.email == "a@b.com"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuthRegisterRequest(email="a@b.com", password="a" * 8, name="")  # type: ignore[arg-type]
